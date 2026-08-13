import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, utc_now
from app.models.enums import DocumentStatus, DocumentType


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    upload_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED, index=True, nullable=False)
    document_type = Column(SQLEnum(DocumentType), default=DocumentType.OTHER, index=True, nullable=False)
    page_count = Column(Integer, default=1, nullable=False)
    raw_text = Column(Text, nullable=True)
    raw_extraction_json = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    classification = relationship("DocumentClassification", back_populates="document", uselist=False, cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="document", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document id={self.id} filename={self.filename} status={self.status} type={self.document_type}>"
