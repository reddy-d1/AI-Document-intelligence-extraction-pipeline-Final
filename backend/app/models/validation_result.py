import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import ValidationSeverity


class ValidationResult(Base, TimestampMixin):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    field_id = Column(String(36), ForeignKey("extracted_fields.id", ondelete="SET NULL"), nullable=True)

    rule_name = Column(String(255), nullable=False)
    passed = Column(Boolean, nullable=False)
    severity = Column(SQLEnum(ValidationSeverity), default=ValidationSeverity.ERROR, nullable=False)
    message = Column(Text, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="validation_results")
    field = relationship("ExtractedField", back_populates="validation_results")

    def __repr__(self):
        return f"<ValidationResult rule={self.rule_name} passed={self.passed} severity={self.severity}>"
