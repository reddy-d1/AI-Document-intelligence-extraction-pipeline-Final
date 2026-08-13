from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.enums import ValidationSeverity, DocumentStatus


class ValidationResultResponse(BaseModel):
    id: str
    document_id: str
    field_id: Optional[str] = None
    rule_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationGroupedResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    total_rules: int
    passed_count: int
    failed_count: int
    errors: List[ValidationResultResponse]
    warnings: List[ValidationResultResponse]
    info: List[ValidationResultResponse]
