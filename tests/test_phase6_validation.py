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
from app.models.extracted_field import ExtractedField
from app.models.enums import DataType

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


def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def generate_valid_invoice_pdf(inv_num: str = "INV-2026-9001") -> bytes:
    """Generate invoice PDF where subtotal + tax = total"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "INVOICE", fontsize=24)
    page.insert_text((50, 140), f"Invoice Number: {inv_num}", fontsize=12)
    page.insert_text((50, 160), "Vendor: Delta Services LLC", fontsize=12)
    page.insert_text((50, 180), "Subtotal: $1,000.00", fontsize=12)
    page.insert_text((50, 200), "Tax: $100.00", fontsize=12)
    page.insert_text((50, 220), "Total Amount: $1,100.00", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_phase6_validation_engine_passed():
    """Test valid invoice passing all rules and advancing to validated status"""
    reset_db()
    pdf_bytes = generate_valid_invoice_pdf("INV-2026-9001")

    # 1. Upload & Pipeline steps
    res_up = client.post("/api/v1/documents/upload", files={"file": ("delta_inv.pdf", pdf_bytes, "application/pdf")})
    doc_id = res_up.json()["id"]

    client.post(f"/api/v1/documents/{doc_id}/ocr")
    client.post(f"/api/v1/documents/{doc_id}/classify")
    client.post(f"/api/v1/documents/{doc_id}/extract")

    # 2. Trigger validation
    res_val = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["status"] == "validated"
    assert val_data["passed_count"] >= 1
    assert len(val_data["errors"]) == 0

    # 3. Retrieve grouped results
    res_grouped = client.get(f"/api/v1/documents/{doc_id}/validation")
    assert res_grouped.status_code == 200
    assert res_grouped.json()["status"] == "validated"


def test_phase6_validation_arithmetic_failure():
    """Test arithmetic mismatch triggering error severity and needs_review routing"""
    reset_db()
    pdf_bytes = generate_valid_invoice_pdf("INV-2026-9002")

    res_up = client.post("/api/v1/documents/upload", files={"file": ("bad_math_inv.pdf", pdf_bytes, "application/pdf")})
    doc_id = res_up.json()["id"]

    client.post(f"/api/v1/documents/{doc_id}/ocr")
    client.post(f"/api/v1/documents/{doc_id}/classify")
    client.post(f"/api/v1/documents/{doc_id}/extract")

    # Update total_amount field to mismatched value 5000.00 via API route
    res_fields = client.get(f"/api/v1/documents/{doc_id}/fields")
    fields = res_fields.json()
    total_f = next((f for f in fields if f["field_name"] == "total_amount"), None)
    if total_f:
        client.patch(f"/api/v1/documents/{doc_id}/fields/{total_f['id']}", json={"field_value": "5000.00"})


    # Trigger validation
    res_val = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["status"] == "needs_review"
    assert len(val_data["errors"]) > 0
    assert any("Arithmetic mismatch" in err["message"] for err in val_data["errors"])


if __name__ == "__main__":
    reset_db()
    test_phase6_validation_engine_passed()
    test_phase6_validation_arithmetic_failure()
    print("All Phase 6 Validation Engine integration tests passed successfully!")
