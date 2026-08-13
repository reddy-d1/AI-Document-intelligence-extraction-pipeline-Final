import os
import io
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import fitz  # PyMuPDF

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.core.database import Base, get_db
from app.services.preprocessing import preprocess_document

from sqlalchemy.pool import StaticPool

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


def generate_sample_pdf_bytes() -> bytes:
    """Generate a 2-page sample PDF in memory"""
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 100), "INVOICE #INV-2026-001", fontsize=20)
    page1.insert_text((50, 140), "Vendor: Acme Global Inc.", fontsize=12)
    page1.insert_text((50, 160), "Total Amount: $1,500.00", fontsize=12)
    
    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 100), "INVOICE TERMS & CONDITIONS", fontsize=16)
    page2.insert_text((50, 130), "Payment due within 30 days.", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_upload_and_preprocess_pipeline():
    """Test full upload, preprocessing, and metadata retrieval pipeline"""
    pdf_bytes = generate_sample_pdf_bytes()

    # 1. Test POST /api/v1/documents/upload
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample_invoice.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    doc_id = data["id"]
    assert data["filename"] == "sample_invoice.pdf"
    assert data["status"] == "uploaded"

    # 2. Test GET /api/v1/documents/{id}
    res_get = client.get(f"/api/v1/documents/{doc_id}")
    assert res_get.status_code == 200
    doc_data = res_get.json()
    assert doc_data["id"] == doc_id
    assert os.path.exists(doc_data["file_path"])

    # 3. Synchronously run preprocessing engine
    storage_dir = os.path.dirname(os.path.dirname(doc_data["file_path"]))
    prep_res = preprocess_document(doc_id, doc_data["file_path"], storage_dir)
    assert prep_res["page_count"] == 2

    # Check generated page images under storage/{doc_id}/processed/
    page1_img = os.path.join(prep_res["processed_dir"], "page_1.png")
    page2_img = os.path.join(prep_res["processed_dir"], "page_2.png")
    assert os.path.exists(page1_img)
    assert os.path.exists(page2_img)

    # 4. Test GET /api/v1/documents/{id}/image endpoint
    res_img = client.get(f"/api/v1/documents/{doc_id}/image?page=1")
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "image/png"
    assert len(res_img.content) > 0

    # 5. Test GET /api/v1/documents (listing endpoint)
    res_list = client.get("/api/v1/documents?page=1&page_size=10")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == doc_id for item in list_data["items"])


def test_upload_validation_errors():
    """Test file type and file size validation errors"""
    # Bad file extension (.exe)
    res_bad_type = client.post(
        "/api/v1/documents/upload",
        files={"file": ("malicious.exe", b"binary content", "application/octet-stream")}
    )
    assert res_bad_type.status_code == 400
    assert "Unsupported file type" in res_bad_type.json()["detail"]

    # File size too large (> 20MB)
    large_payload = b"0" * (20 * 1024 * 1024 + 100)
    res_large = client.post(
        "/api/v1/documents/upload",
        files={"file": ("oversized.pdf", large_payload, "application/pdf")}
    )
    assert res_large.status_code == 413
    assert "exceeds 20MB limit" in res_large.json()["detail"]


if __name__ == "__main__":
    setup_module()
    test_upload_and_preprocess_pipeline()
    test_upload_validation_errors()
    print("All Phase 2 integration tests passed successfully!")
