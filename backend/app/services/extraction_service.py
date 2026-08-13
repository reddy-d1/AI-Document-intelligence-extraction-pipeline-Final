import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.processing_log import ProcessingLog
from app.models.enums import DocumentStatus, DataType, ProcessingStage
from app.services.extraction import extract_entities_with_llm

logger = logging.getLogger(__name__)


def infer_data_type(field_name: str, field_value: Any) -> DataType:
    """Infer DataType enum based on field_name and value type"""
    name_lower = field_name.lower()
    
    if isinstance(field_value, (list, dict)):
        return DataType.JSON
    elif isinstance(field_value, bool):
        return DataType.BOOLEAN
    elif "in_words" in name_lower or "text" in name_lower or "address" in name_lower or "description" in name_lower or "name" in name_lower or "number" in name_lower or "holder" in name_lower or "period" in name_lower or "code" in name_lower:
        return DataType.STRING
    elif "amount" in name_lower or "price" in name_lower or "tax" in name_lower or "subtotal" in name_lower or "value" in name_lower:
        return DataType.CURRENCY
    elif "date" in name_lower:
        return DataType.DATE
    elif "count" in name_lower or "quantity" in name_lower or isinstance(field_value, (int, float)):
        return DataType.NUMBER
    
    return DataType.STRING



def run_document_extraction(document_id: str, db: Session) -> List[ExtractedField]:
    """Run entity extraction for a document, store ExtractedField DB records, and update status"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    start_time = datetime.now(timezone.utc)
    log_entry = ProcessingLog(
        document_id=document_id,
        stage=ProcessingStage.EXTRACTION,
        status="started",
        started_at=start_time
    )
    db.add(log_entry)
    db.commit()

    # Execute extraction
    raw_entities = extract_entities_with_llm(doc.document_type, doc.raw_text or "")
    field_conf = raw_entities.pop("_field_confidence", {})

    # Clear existing ExtractedField records if re-extracting
    db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete()

    created_fields: List[ExtractedField] = []

    for field_name, value in raw_entities.items():
        if value is None:
            continue

        conf_score = float(field_conf.get(field_name, 0.85))
        data_type = infer_data_type(field_name, value)
        
        # Format list/dict into JSON string for value field
        if isinstance(value, (list, dict)):
            val_str = json.dumps(value, ensure_ascii=False)
        else:
            val_str = str(value)

        field_obj = ExtractedField(
            document_id=document_id,
            field_name=field_name,
            field_value=val_str,
            confidence_score=round(conf_score, 4),
            data_type=data_type,
            is_validated=False
        )
        db.add(field_obj)
        created_fields.append(field_obj)

    # Save full ground-truth nested JSON on Document model
    doc.raw_extraction_json = json.dumps(raw_entities, ensure_ascii=False)

    # Update document status to EXTRACTED
    doc.status = DocumentStatus.EXTRACTED
    log_entry.status = "completed"
    log_entry.completed_at = datetime.now(timezone.utc)

    db.commit()

    for f in created_fields:
        db.refresh(f)

    return created_fields


def correct_extracted_field(
    document_id: str,
    field_id: str,
    new_value: str,
    notes: Optional[str],
    db: Session
) -> ExtractedField:
    """Human-in-the-loop (HITL) correction for an extracted field value"""
    field_obj = db.query(ExtractedField).filter(
        ExtractedField.id == field_id,
        ExtractedField.document_id == document_id
    ).first()

    if not field_obj:
        raise ValueError(f"ExtractedField '{field_id}' for Document '{document_id}' not found")

    field_obj.field_value = new_value
    field_obj.confidence_score = 1.0  # User verified
    field_obj.is_validated = True
    field_obj.validation_notes = notes or "Manually corrected by reviewer"

    db.commit()
    db.refresh(field_obj)
    return field_obj
