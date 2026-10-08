"""SQLAlchemy model for GenerationJob."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, index=True)
    event_name = Column(String(255), nullable=False, index=True)
    certificate_title = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    issue_date = Column(String(10), nullable=False)  # ISO date string YYYY-MM-DD
    description = Column(String(1000), nullable=True)

    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED, index=True)

    total_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # One-to-many: one job has many certificates
    certificates = relationship(
        "Certificate",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def progress_percentage(self) -> float:
        if self.total_count == 0:
            return 0.0
        return round((self.completed_count / self.total_count) * 100, 1)
