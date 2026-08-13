import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app
from app.core.database import Base, get_db
from app.core.security import validate_file_magic_bytes, mask_sensitive_log_data

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


def test_deep_healthcheck_endpoint():
    """Test GET /api/v1/health/deep endpoint"""
    res = client.get("/api/v1/health/deep")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "redis" in data


def test_magic_bytes_and_log_masking():
    """Test validate_file_magic_bytes and mask_sensitive_log_data"""
    pdf_header = b"%PDF-1.4 header bytes"
    assert validate_file_magic_bytes(pdf_header) is True

    fake_header = b"BAD_EXEC_HEADER"
    assert validate_file_magic_bytes(fake_header) is False

    raw_log = "User SSN is 123-45-6789 and API key is sk-ant-api03-abcdef1234567890qwertyuiop"
    masked_log = mask_sensitive_log_data(raw_log)
    assert "***-**-****" in masked_log
    assert "123-45-6789" not in masked_log


if __name__ == "__main__":
    setup_module()
    test_deep_healthcheck_endpoint()
    test_magic_bytes_and_log_masking()
    print("All Phase 14 Production readiness tests passed successfully!")
