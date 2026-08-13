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


def generate_analytics_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "INVOICE", fontsize=24)
    page.insert_text((50, 140), "Invoice Number: INV-2026-STAT", fontsize=12)
    page.insert_text((50, 160), "Vendor: Analytics Corp", fontsize=12)
    page.insert_text((50, 180), "Subtotal: $2,000.00", fontsize=12)
    page.insert_text((50, 200), "Tax: $200.00", fontsize=12)
    page.insert_text((50, 220), "Total Amount: $2,200.00", fontsize=12)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def test_analytics_summary_and_timeseries_endpoints():
    """Test GET /api/v1/analytics/summary and GET /api/v1/analytics/timeseries"""
    pdf_bytes = generate_analytics_pdf()

    # Upload & process a document
    res_up = client.post("/api/v1/documents/upload", files={"file": ("stat_inv.pdf", pdf_bytes, "application/pdf")})
    doc_id = res_up.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # 1. Test GET /api/v1/analytics/summary
    res_sum = client.get("/api/v1/analytics/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_documents"] >= 1
    assert "status_counts" in sum_data
    assert "document_type_counts" in sum_data

    # 2. Test GET /api/v1/analytics/timeseries
    res_ts = client.get("/api/v1/analytics/timeseries?days=14")
    assert res_ts.status_code == 200
    ts_data = res_ts.json()
    assert len(ts_data["data_points"]) == 14


if __name__ == "__main__":
    setup_module()
    test_analytics_summary_and_timeseries_endpoints()
    print("All Phase 11 Analytics Dashboard integration tests passed successfully!")
