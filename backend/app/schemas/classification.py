from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import DocumentType, DocumentStatus


class ClassificationLLMResult(BaseModel):
    document_type: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""


class ClassificationOverrideRequest(BaseModel):
    override_type: DocumentType
    reasoning: Optional[str] = "User manual classification override"


class ClassificationResponse(BaseModel):
    id: str
    document_id: str
    predicted_type: DocumentType
    confidence_score: float
    model_used: str
    classified_at: datetime
    status: DocumentStatus

    class Config:
        from_attributes = True
