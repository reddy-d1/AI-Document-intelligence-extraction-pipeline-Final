import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_classification import DocumentClassification
from app.models.processing_log import ProcessingLog
from app.models.enums import DocumentStatus, DocumentType, ProcessingStage
from app.services.classification import classify_document_text

logger = logging.getLogger(__name__)


def run_document_classification(document_id: str, db: Session) -> DocumentClassification:
    """Run document classification, persist DB record, and update Document status"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    start_time = datetime.now(timezone.utc)
    log_entry = ProcessingLog(
        document_id=document_id,
        stage=ProcessingStage.CLASSIFICATION,
        status="started",
        started_at=start_time
    )
    db.add(log_entry)
    db.commit()

    # Execute classification service
    cls_result = classify_document_text(doc.raw_text or "")
    
    # Map string type to DocumentType enum safely
    try:
        predicted_type_enum = DocumentType(cls_result.document_type.lower())
    except ValueError:
        predicted_type_enum = DocumentType.OTHER

    # Upsert DocumentClassification record
    classification = db.query(DocumentClassification).filter(
        DocumentClassification.document_id == document_id
    ).first()

    now = datetime.now(timezone.utc)
    if classification:
        classification.predicted_type = predicted_type_enum
        classification.confidence_score = cls_result.confidence
        classification.model_used = "claude-3-5-sonnet"
        classification.classified_at = now
    else:
        classification = DocumentClassification(
            document_id=document_id,
            predicted_type=predicted_type_enum,
            confidence_score=cls_result.confidence,
            model_used="claude-3-5-sonnet",
            classified_at=now
        )
        db.add(classification)

    # Update Document document_type
    doc.document_type = predicted_type_enum

    # Confidence routing: if confidence < 0.70 mark as needs_review
    if cls_result.confidence < 0.70:
        doc.status = DocumentStatus.NEEDS_REVIEW
        logger.warning(f"Document {document_id} classification confidence {cls_result.confidence} < 0.70; status = needs_review.")
    else:
        doc.status = DocumentStatus.CLASSIFIED

    log_entry.status = "completed"
    log_entry.completed_at = now
    db.commit()
    db.refresh(classification)

    return classification


def override_document_classification(
    document_id: str,
    override_type: DocumentType,
    reasoning: str,
    db: Session
) -> DocumentClassification:
    """Manual user override for document classification type"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    classification = db.query(DocumentClassification).filter(
        DocumentClassification.document_id == document_id
    ).first()

    now = datetime.now(timezone.utc)
    if classification:
        classification.predicted_type = override_type
        classification.confidence_score = 1.0  # User manual override
        classification.model_used = f"user_override ({reasoning})"
        classification.classified_at = now
    else:
        classification = DocumentClassification(
            document_id=document_id,
            predicted_type=override_type,
            confidence_score=1.0,
            model_used=f"user_override ({reasoning})",
            classified_at=now
        )
        db.add(classification)

    doc.document_type = override_type
    doc.status = DocumentStatus.CLASSIFIED

    db.commit()
    db.refresh(classification)
    return classification
