from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.enums import DocumentStatus, DocumentType, ValidationSeverity


class ExportDocumentMetadata(BaseModel):
    id: str
    filename: str
    file_type: str
    upload_date: datetime
    status: DocumentStatus
    page_count: int


class ExportClassification(BaseModel):
    document_type: DocumentType
    confidence_score: float
    model_used: str
    classified_at: datetime


class ExportValidationError(BaseModel):
    rule_name: str
    severity: ValidationSeverity
    message: str


class ExportValidationSummary(BaseModel):
    status: DocumentStatus
    total_rules: int
    passed_count: int
    failed_count: int
    errors: List[ExportValidationError] = Field(default_factory=list)
    warnings: List[ExportValidationError] = Field(default_factory=list)


class ExportProcessingMetadata(BaseModel):
    ocr_method: str = "tesseract_ocr"
    processing_stages: List[Dict[str, Any]] = Field(default_factory=list)


class StructuredDocumentExport(BaseModel):
    schema_version: str = "1.0.0"
    exported_at: datetime
    metadata: ExportDocumentMetadata
    classification: ExportClassification
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    validation_summary: ExportValidationSummary
    processing_metadata: ExportProcessingMetadata


class BatchExportRequest(BaseModel):
    document_ids: Optional[List[str]] = None
    format: str = "json"  # "json" | "csv"
    as_zip: bool = True
