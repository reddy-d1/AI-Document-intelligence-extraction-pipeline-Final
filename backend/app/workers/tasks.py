import logging
from datetime import datetime, timezone
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.document import Document
from app.models.processing_log import ProcessingLog
from app.models.enums import DocumentStatus, ProcessingStage
from app.services.preprocessing import preprocess_document
from app.services.ocr_service import process_document_ocr
from app.services.classification_service import run_document_classification
from app.services.extraction_service import run_document_extraction
from app.services.validation_service import run_document_validation

logger = logging.getLogger(__name__)


@celery_app.task(name="preprocess_document_task")
def preprocess_document_task(document_id: str):
    """Celery background task for document preprocessing"""
    db = SessionLocal()
    start_time = datetime.now(timezone.utc)

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found for preprocessing")
            return {"status": "error", "message": "Document not found"}

        doc.status = DocumentStatus.PROCESSING
        log_entry = ProcessingLog(
            document_id=document_id,
            stage=ProcessingStage.PREPROCESSING,
            status="started",
            started_at=start_time
        )
        db.add(log_entry)
        db.commit()

        result = preprocess_document(document_id, doc.file_path, settings.STORAGE_DIR)

        doc.page_count = result["page_count"]
        doc.status = DocumentStatus.PREPROCESSED

        log_entry.status = "completed"
        log_entry.completed_at = datetime.now(timezone.utc)
        db.commit()

        run_ocr_task.delay(document_id)
        return {"status": "success", "document_id": document_id, "page_count": result["page_count"]}

    except Exception as e:
        logger.exception(f"Error preprocessing document {document_id}: {str(e)}")
        db.rollback()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            err_log = ProcessingLog(
                document_id=document_id,
                stage=ProcessingStage.PREPROCESSING,
                status="failed",
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                error_message=str(e)
            )
            db.add(err_log)
            db.commit()

        return {"status": "failed", "document_id": document_id, "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="run_ocr_task")
def run_ocr_task(document_id: str):
    """Celery background task for OCR and raw text extraction"""
    db = SessionLocal()
    start_time = datetime.now(timezone.utc)

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found for OCR")
            return {"status": "error", "message": "Document not found"}

        log_entry = ProcessingLog(
            document_id=document_id,
            stage=ProcessingStage.OCR,
            status="started",
            started_at=start_time
        )
        db.add(log_entry)
        db.commit()

        ocr_result = process_document_ocr(document_id, doc.file_path, settings.STORAGE_DIR)
        doc.raw_text = ocr_result.raw_text

        if ocr_result.confidence < 0.60:
            doc.status = DocumentStatus.NEEDS_REVIEW
            logger.warning(f"Document {document_id} OCR confidence ({ocr_result.confidence}) < 0.60; flagged for review.")
        else:
            doc.status = DocumentStatus.OCR_COMPLETE

        log_entry.status = "completed"
        log_entry.completed_at = datetime.now(timezone.utc)
        db.commit()

        if doc.status != DocumentStatus.NEEDS_REVIEW:
            run_classification_task.delay(document_id)

        return {"status": "success", "document_id": document_id, "confidence": ocr_result.confidence}

    except Exception as e:
        logger.exception(f"Error during OCR for document {document_id}: {str(e)}")
        db.rollback()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            err_log = ProcessingLog(
                document_id=document_id,
                stage=ProcessingStage.OCR,
                status="failed",
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                error_message=str(e)
            )
            db.add(err_log)
            db.commit()

        return {"status": "failed", "document_id": document_id, "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="run_classification_task")
def run_classification_task(document_id: str):
    """Celery background task for LLM classification"""
    db = SessionLocal()
    try:
        classification = run_document_classification(document_id, db)
        doc = db.query(Document).filter(Document.id == document_id).first()

        if doc and doc.status != DocumentStatus.NEEDS_REVIEW:
            run_extraction_task.delay(document_id)

        return {
            "status": "success",
            "document_id": document_id,
            "predicted_type": classification.predicted_type.value,
            "confidence": classification.confidence_score
        }
    except Exception as e:
        logger.exception(f"Error classifying document {document_id}: {str(e)}")
        db.rollback()
        return {"status": "failed", "document_id": document_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="run_extraction_task")
def run_extraction_task(document_id: str):
    """Celery background task for LLM entity extraction"""
    db = SessionLocal()
    try:
        fields = run_document_extraction(document_id, db)
        run_validation_task.delay(document_id)
        return {
            "status": "success",
            "document_id": document_id,
            "extracted_fields_count": len(fields)
        }
    except Exception as e:
        logger.exception(f"Error extracting entities for document {document_id}: {str(e)}")
        db.rollback()
        return {"status": "failed", "document_id": document_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="run_validation_task")
def run_validation_task(document_id: str):
    """Celery background task for rule validation engine"""
    db = SessionLocal()
    try:
        results = run_document_validation(document_id, db)
        return {
            "status": "success",
            "document_id": document_id,
            "validation_results_count": len(results)
        }
    except Exception as e:
        logger.exception(f"Error validating document {document_id}: {str(e)}")
        db.rollback()
        return {"status": "failed", "document_id": document_id, "error": str(e)}
    finally:
        db.close()
