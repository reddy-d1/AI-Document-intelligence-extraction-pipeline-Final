import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.main import app as fastapi_app
from app.core.database import Base, get_db
import app.models  # Ensure all ORM models are registered with Base.metadata

# Single shared SQLite in-memory engine across test session with StaticPool
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database tables exist for all test runs"""
    Base.metadata.create_all(bind=test_engine)
    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def auto_reset_db():
    """Ensure clean table state before each test function"""
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def client_fixture():
    """TestClient fixture for API testing"""
    return TestClient(fastapi_app)


client = TestClient(fastapi_app)
app = fastapi_app


