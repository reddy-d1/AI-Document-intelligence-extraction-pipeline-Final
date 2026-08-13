import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, utc_now
from app.models.enums import ProcessingStage


class ProcessingLog(Base, TimestampMixin):
    __tablename__ = "processing_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)

    stage = Column(SQLEnum(ProcessingStage), nullable=False)
    status = Column(String(50), nullable=False)  # started | completed | failed
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="processing_logs")

    def __repr__(self):
        return f"<ProcessingLog doc_id={self.document_id} stage={self.stage} status={self.status}>"
