import logging
from datetime import datetime, timezone
from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.validation_result import ValidationResult
from app.models.processing_log import ProcessingLog
from app.models.enums import DocumentStatus, ValidationSeverity, ProcessingStage
from app.services.validation.rules import validation_registry, RuleEvaluationOutput

logger = logging.getLogger(__name__)


def run_document_validation(document_id: str, db: Session) -> List[ValidationResult]:
    """Run all registered validation rules against a document and store results"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    start_time = datetime.now(timezone.utc)
    log_entry = ProcessingLog(
        document_id=document_id,
        stage=ProcessingStage.VALIDATION,
        status="started",
        started_at=start_time
    )
    db.add(log_entry)
    db.commit()

    # Load extracted fields map
    fields = db.query(ExtractedField).filter(ExtractedField.document_id == document_id).all()
    field_map: Dict[str, ExtractedField] = {f.field_name: f for f in fields}

    # Clear previous ValidationResult entries for this document
    db.query(ValidationResult).filter(ValidationResult.document_id == document_id).delete()

    created_results: List[ValidationResult] = []
    has_error_failure = False

    rules = validation_registry.get_rules()
    for rule in rules:
        try:
            eval_outputs: List[RuleEvaluationOutput] = rule.evaluate(doc, field_map, db)
            for out in eval_outputs:
                if not out.passed and out.severity == ValidationSeverity.ERROR:
                    has_error_failure = True

                res_obj = ValidationResult(
                    document_id=document_id,
                    field_id=out.field_id,
                    rule_name=out.rule_name,
                    passed=out.passed,
                    severity=out.severity,
                    message=out.message
                )
                db.add(res_obj)
                created_results.append(res_obj)
        except Exception as e:
            logger.exception(f"Error evaluating rule '{rule.name}' for document {document_id}: {str(e)}")

    # Status routing: if any ERROR severity rule failed -> needs_review, else -> validated
    if has_error_failure:
        doc.status = DocumentStatus.NEEDS_REVIEW
        logger.warning(f"Document {document_id} failed ERROR severity validation rules; status set to needs_review.")
    else:
        doc.status = DocumentStatus.VALIDATED
        logger.info(f"Document {document_id} passed validation; status set to validated.")

    log_entry.status = "completed"
    log_entry.completed_at = datetime.now(timezone.utc)
    db.commit()

    for r in created_results:
        db.refresh(r)

    return created_results


def get_grouped_validation_results(document_id: str, db: Session) -> dict:
    """Retrieve validation results for a document grouped by severity"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document '{document_id}' not found")

    results = db.query(ValidationResult).filter(ValidationResult.document_id == document_id).all()

    errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
    warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
    info = [r for r in results if r.severity == ValidationSeverity.INFO]
    passed_count = sum(1 for r in results if r.passed)
    failed_count = sum(1 for r in results if not r.passed)

    return {
        "document_id": document_id,
        "status": doc.status,
        "total_rules": len(results),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "errors": errors,
        "warnings": warnings,
        "info": info
    }
