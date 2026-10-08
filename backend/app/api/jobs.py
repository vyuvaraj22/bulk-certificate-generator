"""
API routes for certificate generation jobs.

Routes:
  POST   /api/jobs                          – Create a new generation job
  GET    /api/jobs                          – List all jobs
  GET    /api/jobs/{job_id}                 – Get job status
  GET    /api/jobs/{job_id}/certificates    – List certificates for a job
  GET    /api/jobs/{job_id}/download        – Download all successful PDFs as ZIP
  POST   /api/jobs/{job_id}/retry-failed    – Retry failed certificates
"""

import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.certificate import CertificateStatus
from app.schemas.schemas import (
    CertificateListResponse,
    JobCreateRequest,
    JobCreatedResponse,
    JobListItem,
    JobStatusResponse,
    RetryResponse,
)
from app.services.job_service import (
    create_job,
    get_job,
    get_job_certificates,
    get_job_status_response,
    list_jobs,
    mark_failed_certificates_for_retry,
)
from app.workers.certificate_worker import submit_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new certificate generation job",
    description=(
        "Accepts job details and a list of recipients. "
        "Validates input, persists the job, then starts background PDF generation. "
        "Returns immediately with the job ID — poll GET /api/jobs/{job_id} for progress."
    ),
)
def create_generation_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
) -> JobCreatedResponse:
    job = create_job(
        db=db,
        event_name=request.event_name,
        certificate_title=request.certificate_title,
        organization=request.organization,
        issue_date=str(request.issue_date),
        recipients=request.recipients,
        description=request.description,
    )

    # Submit to background worker — does not block
    submit_job(job.id)

    return JobCreatedResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
        completed=0,
        successful=0,
        failed=0,
    )


@router.get(
    "",
    response_model=list[JobListItem],
    summary="List all generation jobs",
)
def list_generation_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[JobListItem]:
    return list_jobs(db, status=status_filter, search=search, skip=skip, limit=limit)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and progress",
)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    result = get_job_status_response(db, job_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id!r} not found"},
        )
    return result


@router.get(
    "/{job_id}/certificates",
    response_model=CertificateListResponse,
    summary="List certificates for a job with search/filter/pagination",
)
def list_job_certificates(
    job_id: str,
    cert_status: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CertificateListResponse:
    result = get_job_certificates(
        db,
        job_id=job_id,
        status=cert_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id!r} not found"},
        )
    return result


@router.post(
    "/{job_id}/retry-failed",
    response_model=RetryResponse,
    summary="Retry all failed certificates in a job",
    description=(
        "Resets all FAILED certificates to PENDING and re-submits the job to the "
        "background worker. Successful certificates are not re-generated."
    ),
)
def retry_failed_certificates(
    job_id: str, db: Session = Depends(get_db)
) -> RetryResponse:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id!r} not found"},
        )

    retried_count = mark_failed_certificates_for_retry(db, job_id)

    if retried_count == 0:
        return RetryResponse(
            job_id=job_id,
            retried_count=0,
            message="No failed certificates to retry.",
        )

    # Re-submit the job to the background worker
    submit_job(job_id)

    return RetryResponse(
        job_id=job_id,
        retried_count=retried_count,
        message=f"Retrying {retried_count} failed certificate(s).",
    )


@router.get(
    "/{job_id}/download",
    summary="Download all successful certificates as a ZIP archive",
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP file download"},
        404: {"description": "Job not found or no successful certificates"},
    },
)
def download_job_certificates(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Streams a ZIP file containing all successfully generated PDFs.
    Does not require writing the ZIP to disk — streams directly from memory.
    """
    from app.models.certificate import Certificate

    job = get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id!r} not found"},
        )

    successful_certs = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job_id,
            Certificate.status == CertificateStatus.SUCCESS,
            Certificate.file_path.isnot(None),
        )
        .all()
    )

    if not successful_certs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NO_CERTIFICATES",
                "message": "No successful certificates available for download.",
            },
        )

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in successful_certs:
            pdf_path = Path(cert.file_path)
            if pdf_path.exists():
                zf.write(pdf_path, arcname=pdf_path.name)
            else:
                logger.warning("Missing PDF for certificate %s: %s", cert.id, cert.file_path)

    zip_buffer.seek(0)

    event_slug = job.event_name.replace(" ", "_")[:40]
    zip_filename = f"certificates_{event_slug}_{job_id[:8]}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
