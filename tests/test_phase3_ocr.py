import os
import io
import sys
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import fitz  # PyMuPDF

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.core.database import Base, get_db
from app.services.ocr_service import process_document_ocr, extract_native_pdf_text

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


def generate_searchable_pdf_bytes() -> bytes:
    """Generate a 2-page PDF document containing searchable vector text"""
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 100), "PURCHASE ORDER #PO-2026-999", fontsize=20)
    page1.insert_text((50, 140), "Vendor Name: Global Supplies LLC", fontsize=12)
    page1.insert_text((50, 160), "Line Item 1: Industrial Printing Paper x 100", fontsize=12)
    page1.insert_text((50, 180), "Subtotal: $4,500.00 | Tax: $450.00 | Total: $4,950.00", fontsize=12)
    
    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 100), "AUTHORIZATION SIGNATURES", fontsize=16)
    page2.insert_text((50, 130), "Approved by Finance Director John Doe on 2026-08-11.", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_phase3_ocr_pipeline():
    """Test full OCR extraction, JSON metadata creation, and text endpoints"""
    pdf_bytes = generate_searchable_pdf_bytes()

    # 1. Upload document
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("purchase_order.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # 2. Trigger OCR endpoint
    res_ocr = client.post(f"/api/v1/documents/{doc_id}/ocr")
    assert res_ocr.status_code == 200
    text_data = res_ocr.json()
    assert text_data["document_id"] == doc_id
    assert "PURCHASE ORDER #PO-2026-999" in text_data["raw_text"]
    assert "Global Supplies LLC" in text_data["raw_text"]
    assert text_data["status"] == "ocr_complete"

    # 3. Verify GET /api/v1/documents/{id}/text endpoint
    res_get_text = client.get(f"/api/v1/documents/{doc_id}/text")
    assert res_get_text.status_code == 200
    assert res_get_text.json()["raw_text"] == text_data["raw_text"]

    # 4. Check bounding box JSON file saved to disk
    res_doc = client.get(f"/api/v1/documents/{doc_id}").json()
    doc_dir = os.path.dirname(res_doc["file_path"])
    json_path = os.path.join(doc_dir, "ocr_data.json")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        ocr_json = json.load(f)
    assert ocr_json["confidence"] >= 0.90
    assert len(ocr_json["pages"]) == 2
    assert len(ocr_json["pages"][0]["word_boxes"]) > 0


if __name__ == "__main__":
    setup_module()
    test_phase3_ocr_pipeline()
    print("All Phase 3 OCR integration tests passed successfully!")
