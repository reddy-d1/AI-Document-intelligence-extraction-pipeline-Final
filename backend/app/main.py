import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Register all ORM models with Base.metadata
from app.api.v1.router import api_router

# Configure Application Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("doc_intelligence")

tags_metadata = [
    {
        "name": "Authentication",
        "description": "JWT authentication, login, and bearer token management endpoints.",
    },
    {
        "name": "Documents",
        "description": "Document upload, processing pipeline orchestrator, full-text search, OCR, entity extraction, validation, and export.",
    },
    {
        "name": "Analytics",
        "description": "Aggregated pipeline summary metrics, document type breakdown, and time series trends.",
    },
    {
        "name": "Health Checks",
        "description": "Deep system health monitoring (Database, Redis, Storage disk, and Celery).",
    },
]

# Initialize FastAPI Application
app = FastAPI(
    title="AI Document Intelligence & Extraction Pipeline API",
    description="""
## Enterprise AI-Powered Document Intelligence Engine

An end-to-end multi-modal document extraction and intelligence platform featuring:
* **Multi-Format Ingestion**: PDF, PNG, JPG, DOCX, and TIFF upload up to 20MB.
* **Computer Vision Preprocessing**: OpenCV deskewing and CLAHE contrast enhancement.
* **Dual OCR Engine**: PyMuPDF native vector text stream parser with fallback to Tesseract image OCR.
* **LLM Classification & Entity Extraction**: Anthropic Claude 3.5 Sonnet structured key-value extraction for Invoices, Contracts, Forms, Reports, Receipts, and POs.
* **Rule Validation Engine**: Pluggable cross-field arithmetic checks, date logic, and duplicate detection.
* **Human-in-the-Loop (HITL) Review**: Interactive split-screen document viewer with field-level confidence scoring badges and manual correction endpoints.
* **Versioned Exports**: Versioned JSON (`schema_version: "1.0.0"`), CSV download, and batch ZIP package generation.
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

# Auto-create database tables on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.warning(f"Database auto-migration notice on startup: {str(e)}")

# Mount API v1 router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health Checks"])
def root():
    """Root endpoint to confirm API service status"""
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "health_check": "/api/v1/health/deep"
    }


@app.get("/health", tags=["Health Checks"])
def health_check():
    """Basic service healthcheck endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }

