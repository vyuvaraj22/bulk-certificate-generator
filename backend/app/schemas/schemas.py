"""Pydantic schemas for request/response validation."""

import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.certificate import CertificateStatus
from app.models.job import JobStatus


# ─────────────────────────────────────────────
# Recipient schemas
# ─────────────────────────────────────────────

class RecipientInput(BaseModel):
    """A single recipient in a job creation request."""

    name: str = Field(..., min_length=2, max_length=150, description="Full name of the recipient")
    email: EmailStr = Field(..., description="Valid email address")
    certificate_id: str = Field(
        ..., min_length=1, max_length=100, description="Unique certificate identifier"
    )

    @field_validator("name")
    @classmethod
    def name_must_be_reasonable(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Name must contain at least one letter")
        return v

    @field_validator("certificate_id")
    @classmethod
    def certificate_id_no_special(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Certificate ID cannot be blank")
        return v


class RecipientValidationError(BaseModel):
    """Validation error for a single recipient row."""

    row: int
    field: str
    message: str


class RecipientValidationResult(BaseModel):
    """Result of validating a list of recipients before job creation."""

    total: int
    valid: int
    invalid: int
    errors: List[RecipientValidationError]


# ─────────────────────────────────────────────
# Job creation schemas
# ─────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    """Request body for creating a new certificate generation job."""

    event_name: str = Field(
        ..., min_length=2, max_length=255, description="Event or course name"
    )
    certificate_title: str = Field(
        ..., min_length=2, max_length=255, description="Title printed on the certificate"
    )
    organization: str = Field(
        ..., min_length=2, max_length=255, description="Issuing organisation"
    )
    issue_date: date = Field(..., description="Date of issue (YYYY-MM-DD)")
    description: Optional[str] = Field(
        None, max_length=1000, description="Optional description or subtitle"
    )
    recipients: List[RecipientInput] = Field(
        ..., min_length=1, description="List of recipients (at least one required)"
    )

    @model_validator(mode="after")
    def check_unique_certificate_ids(self) -> "JobCreateRequest":
        ids = [r.certificate_id for r in self.recipients]
        duplicates = {cid for cid in ids if ids.count(cid) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate certificate IDs found: {', '.join(sorted(duplicates))}"
            )
        return self


# ─────────────────────────────────────────────
# Job response schemas
# ─────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    """Job status returned by GET /api/jobs/{job_id}."""

    job_id: str
    event_name: str
    certificate_title: str
    organization: str
    issue_date: str
    description: Optional[str]
    status: JobStatus
    total: int
    completed: int
    successful: int
    failed: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Summary row for the jobs list page."""

    job_id: str
    event_name: str
    certificate_title: str
    organization: str
    issue_date: str
    status: JobStatus
    total: int
    successful: int
    failed: int
    progress_percentage: float
    created_at: datetime

    model_config = {"from_attributes": True}


class JobCreatedResponse(BaseModel):
    """Immediate response after a job is accepted."""

    job_id: str
    status: JobStatus
    total: int
    completed: int
    successful: int
    failed: int
    message: str = "Job accepted. Certificate generation started in the background."


# ─────────────────────────────────────────────
# Certificate response schemas
# ─────────────────────────────────────────────

class CertificateResponse(BaseModel):
    """A single certificate record."""

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    certificate_id: str
    status: CertificateStatus
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CertificateListResponse(BaseModel):
    """Paginated list of certificates for a job."""

    total: int
    page: int
    page_size: int
    certificates: List[CertificateResponse]


# ─────────────────────────────────────────────
# Dashboard statistics schema
# ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Aggregate statistics for the dashboard."""

    total_jobs: int
    total_certificates: int
    total_successful: int
    total_failed: int
    recent_jobs: List[JobListItem]


# ─────────────────────────────────────────────
# Error response schema
# ─────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ─────────────────────────────────────────────
# Retry response schema
# ─────────────────────────────────────────────

class RetryResponse(BaseModel):
    job_id: str
    retried_count: int
    message: str


# ─────────────────────────────────────────────
# CSV validation schema
# ─────────────────────────────────────────────

class CSVValidationResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    errors: List[RecipientValidationError]
    recipients: List[RecipientInput]  # valid recipients parsed
