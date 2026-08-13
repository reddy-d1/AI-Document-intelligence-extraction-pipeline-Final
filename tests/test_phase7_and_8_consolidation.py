import os
import io
import sys
import zipfile
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


def generate_consolidated_pdf() -> bytes:
    """Generate invoice PDF for consolidation test"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "INVOICE", fontsize=24)
    page.insert_text((50, 140), "Invoice Number: INV-2026-FINAL", fontsize=12)
    page.insert_text((50, 160), "Vendor: Acme System Corp", fontsize=12)
    page.insert_text((50, 180), "Subtotal: $3,000.00", fontsize=12)
    page.insert_text((50, 200), "Tax: $300.00", fontsize=12)
    page.insert_text((50, 220), "Total Amount: $3,300.00", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_auth_and_token_issuance():
    """Test POST /api/v1/auth/token JWT token creation"""
    res = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@docintel.ai", "password": "password"}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_full_pipeline_orchestrator_and_exports():
    """Test POST /process orchestrator, GET /status, JSON export, CSV export, and Batch ZIP export"""
    pdf_bytes = generate_consolidated_pdf()

    # 1. Upload
    res_up = client.post("/api/v1/documents/upload", files={"file": ("acme_final.pdf", pdf_bytes, "application/pdf")})
    assert res_up.status_code == 201
    doc_id = res_up.json()["id"]

    # 2. Test POST /api/v1/documents/{id}/process (Full pipeline orchestrator)
    res_proc = client.post(f"/api/v1/documents/{doc_id}/process")
    assert res_proc.status_code == 200
    proc_doc = res_proc.json()
    assert proc_doc["status"] in ["validated", "needs_review"]

    # 3. Test GET /api/v1/documents/{id}/status
    res_stat = client.get(f"/api/v1/documents/{doc_id}/status")
    assert res_stat.status_code == 200
    stat_data = res_stat.json()
    assert stat_data["progress_percentage"] >= 95

    # 4. Test GET /api/v1/documents/{id}/export (JSON format)
    res_exp_json = client.get(f"/api/v1/documents/{doc_id}/export?format=json")
    assert res_exp_json.status_code == 200
    exp_json = res_exp_json.json()
    assert exp_json["schema_version"] == "1.0.0"
    assert exp_json["metadata"]["id"] == doc_id
    assert "extracted_fields" in exp_json

    # 5. Test GET /api/v1/documents/{id}/export?format=csv
    res_exp_csv = client.get(f"/api/v1/documents/{doc_id}/export?format=csv")
    assert res_exp_csv.status_code == 200
    assert "text/csv" in res_exp_csv.headers["content-type"]
    assert "document_id,filename,upload_date" in res_exp_csv.text

    # 6. Test POST /api/v1/documents/batch-export
    res_batch = client.post(
        "/api/v1/documents/batch-export",
        json={"document_ids": [doc_id], "format": "json", "as_zip": True}
    )
    assert res_batch.status_code == 200
    assert "application/zip" in res_batch.headers["content-type"]
    
    zip_bytes = res_batch.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        filenames = z.namelist()
        assert len(filenames) == 1
        assert filenames[0].endswith(".json")


if __name__ == "__main__":
    setup_module()
    test_auth_and_token_issuance()
    test_full_pipeline_orchestrator_and_exports()
    print("All Phase 7 & 8 integration tests passed successfully!")
