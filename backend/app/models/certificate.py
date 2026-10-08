"""SQLAlchemy model for Certificate."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=False, index=True)

    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    certificate_id = Column(String(100), nullable=False, index=True)

    status = Column(
        Enum(CertificateStatus),
        nullable=False,
        default=CertificateStatus.PENDING,
        index=True,
    )

    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Many-to-one: many certificates belong to one job
    job = relationship("GenerationJob", back_populates="certificates")
