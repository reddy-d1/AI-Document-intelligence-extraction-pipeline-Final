import uuid
from sqlalchemy import Column, String, Text, Float, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import DataType


class ExtractedField(Base, TimestampMixin):
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    
    field_name = Column(String(255), index=True, nullable=False)
    field_value = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)
    data_type = Column(SQLEnum(DataType), default=DataType.STRING, nullable=False)
    bounding_box = Column(JSON, nullable=True)
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_notes = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="extracted_fields")
    validation_results = relationship("ValidationResult", back_populates="field", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExtractedField id={self.id} name={self.field_name} value={self.field_value} confidence={self.confidence_score}>"
