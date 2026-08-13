import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.preprocessing import preprocess_document
from app.services.ocr_service import process_document_ocr
from app.services.classification_service import run_document_classification
from app.services.extraction_service import run_document_extraction
from app.services.validation_service import run_document_validation

logger = logging.getLogger(__name__)

STATUS_PROGRESS_MAP: Dict[DocumentStatus, int] = {
    DocumentStatus.UPLOADED: 20,
    DocumentStatus.PROCESSING: 30,
    DocumentStatus.PREPROCESSED: 40,
    DocumentStatus.OCR_COMPLETE: 60,
    DocumentStatus.CLASSIFIED: 80,
    DocumentStatus.EXTRACTED: 90,
    DocumentStatus.VALIDATED: 100,
    DocumentStatus.NEEDS_REVIEW: 95,
    DocumentStatus.FAILED: 100,
}


def calculate_pipeline_status(doc: Document) -> Dict[str, Any]:
    """Calculate progress percentage and status info for frontend progress bars"""
    progress_pct = STATUS_PROGRESS_MAP.get(doc.status, 0)
    
    stage_info = {
        DocumentStatus.UPLOADED: "Uploaded",
        DocumentStatus.PROCESSING: "Preprocessing Image",
        DocumentStatus.PREPROCESSED: "Image Preprocessed",
        DocumentStatus.OCR_COMPLETE: "OCR Text Extracted",
        DocumentStatus.CLASSIFIED: "Document Classified",
        DocumentStatus.EXTRACTED: "Entities Extracted",
        DocumentStatus.VALIDATED: "Validation Complete",
        DocumentStatus.NEEDS_REVIEW: "Needs Human Review",
        DocumentStatus.FAILED: "Processing Failed",
    }.get(doc.status, doc.status.value)

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "progress_percentage": progress_pct,
        "current_stage": stage_info,
        "page_count": doc.page_count,
        "document_type": doc.document_type
    }


def run_full_pipeline(document_id: str, db: Session) -> Document:
    """Run full pipeline synchronously (preprocess -> OCR -> classify -> extract -> validate)"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    logger.info(f"Starting full pipeline orchestrator for document {document_id}")

    # 1. Preprocessing
    preprocess_document(document_id, doc.file_path, storage_dir=None)
    doc.status = DocumentStatus.PREPROCESSED
    db.commit()

    # 2. OCR
    ocr_res = process_document_ocr(document_id, doc.file_path)
    doc.raw_text = ocr_res.raw_text
    doc.status = DocumentStatus.OCR_COMPLETE
    db.commit()

    # 3. Classification
    run_document_classification(document_id, db)
    
    # 4. Extraction
    run_document_extraction(document_id, db)
    
    # 5. Validation
    run_document_validation(document_id, db)

    db.refresh(doc)
    logger.info(f"Full pipeline orchestration finished for document {document_id} with status {doc.status}")
    return doc


def run_full_pipeline_background(document_id: str):
    """Background tasks wrapper that opens its own DB session for async execution"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        run_full_pipeline(document_id, db)
    except Exception as e:
        logger.error(f"Background pipeline execution error for {document_id}: {str(e)}")
    finally:
        db.close()

