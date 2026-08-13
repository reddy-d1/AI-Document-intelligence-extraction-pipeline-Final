from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.enums import DocumentStatus, DocumentType


class DocumentCreateResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    upload_date: datetime
    status: DocumentStatus
    message: str = "Document uploaded successfully. Processing queued."


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    file_type: str
    upload_date: datetime
    uploaded_by: Optional[str] = None
    status: DocumentStatus
    document_type: DocumentType
    page_count: int
    raw_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentTextResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    raw_text: Optional[str] = None
    page_count: int


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
