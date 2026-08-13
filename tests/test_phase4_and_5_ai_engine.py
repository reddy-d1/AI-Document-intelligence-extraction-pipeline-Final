import os
import io
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fitz  # PyMuPDF

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.core.database import Base, get_db

# Set up SQLite in-memory database engine for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module():
    """Create clean database tables for testing"""
    Base.metadata.create_all(bind=test_engine)


def generate_invoice_pdf_bytes() -> bytes:
    """Generate a sample invoice PDF in memory"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "INVOICE", fontsize=24)
    page.insert_text((50, 140), "Invoice Number: INV-2026-8888", fontsize=12)
    page.insert_text((50, 160), "Invoice Date: 2026-08-11", fontsize=12)
    page.insert_text((50, 180), "Vendor: TechCorp Solutions Inc.", fontsize=12)
    page.insert_text((50, 200), "Subtotal: $2,000.00 | Tax: $200.00 | Total Amount: $2,200.00", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_phase4_and_5_ai_engine():
    """Test full classification, extraction, and field correction pipeline"""
    pdf_bytes = generate_invoice_pdf_bytes()

    # 1. Upload
    res_upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("techcorp_invoice.pdf", pdf_bytes, "application/pdf")}
    )
    assert res_upload.status_code == 201
    doc_id = res_upload.json()["id"]

    # 2. Run OCR to populate raw_text
    res_ocr = client.post(f"/api/v1/documents/{doc_id}/ocr")
    assert res_ocr.status_code == 200
    assert "INVOICE" in res_ocr.json()["raw_text"]

    # 3. Test POST /api/v1/documents/{id}/classify
    res_cls = client.post(f"/api/v1/documents/{doc_id}/classify")
    assert res_cls.status_code == 200
    cls_data = res_cls.json()
    assert cls_data["predicted_type"] == "invoice"
    assert cls_data["confidence_score"] >= 0.70

    # 4. Test POST /api/v1/documents/{id}/classification/override
    res_override = client.post(
        f"/api/v1/documents/{doc_id}/classification/override",
        json={"override_type": "invoice", "reasoning": "User confirmed invoice"}
    )
    assert res_override.status_code == 200
    assert res_override.json()["predicted_type"] == "invoice"
    assert res_override.json()["confidence_score"] == 1.0

    # 5. Test POST /api/v1/documents/{id}/extract
    res_ext = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert res_ext.status_code == 200
    ext_data = res_ext.json()
    assert ext_data["document_id"] == doc_id
    assert ext_data["extracted_fields_count"] >= 1

    # 6. Test GET /api/v1/documents/{id}/fields
    res_fields = client.get(f"/api/v1/documents/{doc_id}/fields")
    assert res_fields.status_code == 200
    fields_list = res_fields.json()
    assert len(fields_list) > 0

    field_id = fields_list[0]["id"]
    old_value = fields_list[0]["field_value"]

    # 7. Test PATCH /api/v1/documents/{id}/fields/{field_id} (HITL correction)
    res_patch = client.patch(
        f"/api/v1/documents/{doc_id}/fields/{field_id}",
        json={"field_value": "INV-2026-CORRECTED", "validation_notes": "Corrected by QA"}
    )
    assert res_patch.status_code == 200
    patch_data = res_patch.json()
    assert patch_data["field_value"] == "INV-2026-CORRECTED"
    assert patch_data["is_validated"] is True
    assert patch_data["confidence_score"] == 1.0


if __name__ == "__main__":
    setup_module()
    test_phase4_and_5_ai_engine()
    print("All Phase 4 & 5 AI engine integration tests passed successfully!")
