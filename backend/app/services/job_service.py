"""
Job service: business logic for creating, querying, and managing generation jobs.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import GenerationJob, JobStatus
from app.schemas.schemas import (
    CertificateListResponse,
    CertificateResponse,
    DashboardStats,
    JobCreatedResponse,
    JobListItem,
    JobStatusResponse,
    RecipientInput,
)
from app.utils.helpers import generate_uuid, safe_filename

logger = logging.getLogger(__name__)


def create_job(
    db: Session,
    event_name: str,
    certificate_title: str,
    organization: str,
    issue_date: str,
    recipients: list[RecipientInput],
    description: Optional[str] = None,
) -> GenerationJob:
    """
    Persist a new GenerationJob and its Certificate records (status=PENDING).
    Returns the created GenerationJob ORM object.
    """
    job_id = generate_uuid()

    job = GenerationJob(
        id=job_id,
        event_name=event_name,
        certificate_title=certificate_title,
        organization=organization,
        issue_date=str(issue_date),
        description=description,
        status=JobStatus.QUEUED,
        total_count=len(recipients),
        completed_count=0,
        success_count=0,
        failed_count=0,
    )
    db.add(job)
    db.flush()  # Get the job.id before creating certificates

    for recipient in recipients:
        cert = Certificate(
            id=generate_uuid(),
            job_id=job_id,
            recipient_name=recipient.name,
            recipient_email=str(recipient.email),
            certificate_id=recipient.certificate_id,
            status=CertificateStatus.PENDING,
        )
        db.add(cert)

    db.commit()
    db.refresh(job)
    logger.info("Created job %s with %d recipients", job_id, len(recipients))
    return job


def get_job(db: Session, job_id: str) -> Optional[GenerationJob]:
    """Retrieve a job by ID, or return None if not found."""
    return db.query(GenerationJob).filter(GenerationJob.id == job_id).first()


def get_job_status_response(db: Session, job_id: str) -> Optional[JobStatusResponse]:
    """Build a JobStatusResponse from the database, or None if the job doesn't exist."""
    job = get_job(db, job_id)
    if not job:
        return None
    return _job_to_status_response(job)


def _job_to_status_response(job: GenerationJob) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        event_name=job.event_name,
        certificate_title=job.certificate_title,
        organization=job.organization,
        issue_date=job.issue_date,
        description=job.description,
        status=job.status,
        total=job.total_count,
        completed=job.completed_count,
        successful=job.success_count,
        failed=job.failed_count,
        progress_percentage=job.progress_percentage,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def list_jobs(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[JobListItem]:
    """Return a list of jobs, optionally filtered by status or search term."""
    query = db.query(GenerationJob).order_by(GenerationJob.created_at.desc())

    if status:
        query = query.filter(GenerationJob.status == status)

    if search:
        like = f"%{search}%"
        query = query.filter(GenerationJob.event_name.ilike(like))

    jobs = query.offset(skip).limit(limit).all()

    return [
        JobListItem(
            job_id=j.id,
            event_name=j.event_name,
            certificate_title=j.certificate_title,
            organization=j.organization,
            issue_date=j.issue_date,
            status=j.status,
            total=j.total_count,
            successful=j.success_count,
            failed=j.failed_count,
            progress_percentage=j.progress_percentage,
            created_at=j.created_at,
        )
        for j in jobs
    ]


def get_job_certificates(
    db: Session,
    job_id: str,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Optional[CertificateListResponse]:
    """
    Return paginated certificates for a job.
    Returns None if the job doesn't exist.
    """
    job = get_job(db, job_id)
    if not job:
        return None

    query = db.query(Certificate).filter(Certificate.job_id == job_id)

    if status:
        query = query.filter(Certificate.status == status)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Certificate.recipient_name.ilike(like))
            | (Certificate.recipient_email.ilike(like))
            | (Certificate.certificate_id.ilike(like))
        )

    total = query.count()
    offset = (page - 1) * page_size
    certs = query.offset(offset).limit(page_size).all()

    return CertificateListResponse(
        total=total,
        page=page,
        page_size=page_size,
        certificates=[_cert_to_response(c) for c in certs],
    )


def _cert_to_response(cert: Certificate) -> CertificateResponse:
    return CertificateResponse(
        id=cert.id,
        job_id=cert.job_id,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        certificate_id=cert.certificate_id,
        status=cert.status,
        error_message=cert.error_message,
        created_at=cert.created_at,
        completed_at=cert.completed_at,
    )


def get_certificate(db: Session, certificate_db_id: str) -> Optional[Certificate]:
    """Retrieve a certificate record by its database UUID."""
    return db.query(Certificate).filter(Certificate.id == certificate_db_id).first()


def get_dashboard_stats(db: Session) -> DashboardStats:
    """Compute aggregate statistics for the dashboard."""
    from sqlalchemy import func

    total_jobs = db.query(func.count(GenerationJob.id)).scalar() or 0
    total_certs = db.query(func.count(Certificate.id)).scalar() or 0
    total_successful = (
        db.query(func.count(Certificate.id))
        .filter(Certificate.status == CertificateStatus.SUCCESS)
        .scalar()
        or 0
    )
    total_failed = (
        db.query(func.count(Certificate.id))
        .filter(Certificate.status == CertificateStatus.FAILED)
        .scalar()
        or 0
    )

    recent_jobs = list_jobs(db, limit=10)

    return DashboardStats(
        total_jobs=total_jobs,
        total_certificates=total_certs,
        total_successful=total_successful,
        total_failed=total_failed,
        recent_jobs=recent_jobs,
    )


def mark_failed_certificates_for_retry(db: Session, job_id: str) -> int:
    """
    Reset all FAILED certificates in a job back to PENDING so the worker can retry them.
    Returns the number of certificates reset.
    """
    failed = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.FAILED)
        .all()
    )
    count = len(failed)
    for cert in failed:
        cert.status = CertificateStatus.PENDING
        cert.error_message = None
        cert.completed_at = None
        cert.file_path = None

    if count > 0:
        job = get_job(db, job_id)
        if job:
            job.status = JobStatus.QUEUED
            job.failed_count = 0
            # Adjust completed_count to exclude the failed ones being retried
            job.completed_count = max(0, job.completed_count - count)

    db.commit()
    logger.info("Reset %d failed certificates for job %s for retry", count, job_id)
    return count
