import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, utc_now
from app.models.enums import DocumentType


class DocumentClassification(Base, TimestampMixin):
    __tablename__ = "document_classifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    predicted_type = Column(SQLEnum(DocumentType), nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    model_used = Column(String(255), nullable=False)
    classified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="classification")

    def __repr__(self):
        return f"<DocumentClassification doc_id={self.document_id} type={self.predicted_type} score={self.confidence_score}>"
