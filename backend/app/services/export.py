import os
import io
import json
import csv
import zipfile
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.document_classification import DocumentClassification
from app.models.validation_result import ValidationResult
from app.models.processing_log import ProcessingLog
from app.models.enums import ValidationSeverity, DocumentStatus, DocumentType
from app.schemas.export import (
    StructuredDocumentExport,
    ExportDocumentMetadata,
    ExportClassification,
    ExportValidationSummary,
    ExportValidationError,
    ExportProcessingMetadata,
)

logger = logging.getLogger(__name__)


def build_structured_export(document_id: str, db: Session) -> StructuredDocumentExport:
    """Build clean, versioned (schema_version=1.0.0) structured JSON export"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    cls = db.query(DocumentClassification).filter(DocumentClassification.document_id == document_id).first()
    fields = db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()
    validations = db.query(ValidationResult).filter(ValidationResult.document_id == document_id).all()
    logs = db.query(ProcessingLog).filter(ProcessingLog.document_id == document_id).all()

    # 1. Metadata
    meta = ExportDocumentMetadata(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        upload_date=doc.upload_date,
        status=doc.status,
        page_count=doc.page_count
    )

    # 2. Classification
    classification = ExportClassification(
        document_type=cls.predicted_type if cls else doc.document_type,
        confidence_score=cls.confidence_score if cls else 1.0,
        model_used=cls.model_used if cls else "manual",
        classified_at=cls.classified_at if cls else doc.upload_date
    )

    # 3. Extracted Fields (nested dict)
    extracted_nested: Dict[str, Any] = {}
    for f in fields:
        val = f.field_value
        if f.data_type.value == "json" and val:
            try:
                val = json.loads(val)
            except Exception:
                pass
        extracted_nested[f.field_name] = {
            "value": val,
            "confidence": f.confidence_score,
            "data_type": f.data_type.value,
            "is_validated": f.is_validated
        }

    # 4. Validation Summary
    errors = [
        ExportValidationError(rule_name=v.rule_name, severity=v.severity, message=v.message)
        for v in validations if v.severity == ValidationSeverity.ERROR and not v.passed
    ]
    warnings = [
        ExportValidationError(rule_name=v.rule_name, severity=v.severity, message=v.message)
        for v in validations if v.severity == ValidationSeverity.WARNING and not v.passed
    ]
    passed_cnt = sum(1 for v in validations if v.passed)
    failed_cnt = sum(1 for v in validations if not v.passed)

    val_summary = ExportValidationSummary(
        status=doc.status,
        total_rules=len(validations),
        passed_count=passed_cnt,
        failed_count=failed_cnt,
        errors=errors,
        warnings=warnings
    )

    # 5. Processing Metadata
    proc_logs = [
        {
            "stage": l.stage.value,
            "status": l.status,
            "started_at": l.started_at.isoformat() if l.started_at else None,
            "completed_at": l.completed_at.isoformat() if l.completed_at else None,
            "error": l.error_message
        }
        for l in logs
    ]

    proc_meta = ExportProcessingMetadata(
        ocr_method="pytesseract_or_native_pdf",
        processing_stages=proc_logs
    )

    return StructuredDocumentExport(
        schema_version="1.0.0",
        exported_at=datetime.now(timezone.utc),
        metadata=meta,
        classification=classification,
        extracted_fields=extracted_nested,
        validation_summary=val_summary,
        processing_metadata=proc_meta
    )


def export_to_csv(document_id: str, db: Session) -> str:
    """Flatten document metadata and extracted fields into CSV text"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    fields = db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "document_id", "filename", "upload_date", "document_type", "status",
        "field_name", "field_value", "confidence_score", "data_type", "is_validated"
    ])

    if not fields:
        writer.writerow([doc.id, doc.filename, doc.upload_date, doc.document_type.value, doc.status.value, "", "", "", "", ""])
    else:
        for f in fields:
            writer.writerow([
                doc.id, doc.filename, doc.upload_date, doc.document_type.value, doc.status.value,
                f.field_name, f.field_value, f.confidence_score, f.data_type.value, f.is_validated
            ])

    return output.getvalue()


def build_batch_zip_export(document_ids: List[str], db: Session) -> bytes:
    """Build in-memory ZIP file containing JSON exports for multiple documents"""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc_id in document_ids:
            try:
                export_data = build_structured_export(doc_id, db)
                filename_clean = export_data.metadata.filename.replace(" ", "_")
                entry_name = f"{filename_clean}_{doc_id[:8]}.json"
                zip_file.writestr(entry_name, export_data.model_dump_json(indent=2))
            except Exception as e:
                logger.warning(f"Error packaging document {doc_id} for batch export: {str(e)}")

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
