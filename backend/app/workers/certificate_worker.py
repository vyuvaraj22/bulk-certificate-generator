"""
Background certificate generation worker.

Design decisions:
- We use FastAPI's BackgroundTasks + Python's ThreadPoolExecutor for simplicity.
  Each job runs in a background thread so the API returns immediately.
- Each recipient is processed independently inside the thread; a single
  failure does NOT stop the batch (try/except per certificate).
- The architecture is intentionally simple for this assignment.
  To scale to distributed workers, replace `_run_job` with a Celery task
  and submit via `celery_app.send_task("workers.process_job", args=[job_id])`.
  The service layer and database schema stay the same.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import CERTIFICATES_DIR
from app.database import SessionLocal
from app.models.certificate import Certificate, CertificateStatus
from app.models.job import GenerationJob, JobStatus
from app.services.certificate_service import generate_certificate_pdf
from app.utils.helpers import safe_filename

logger = logging.getLogger(__name__)

# Single-thread executor keeps concurrency simple.
# Increase max_workers to generate multiple jobs concurrently.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cert-worker")


def submit_job(job_id: str) -> None:
    """
    Submit a job for background processing.

    This is the only public interface — the API layer calls this after creating
    the job in the database, then returns the job_id to the client immediately.
    """
    _executor.submit(_run_job, job_id)
    logger.info("Job %s submitted to background worker", job_id)


def _run_job(job_id: str) -> None:
    """
    Worker function: generates certificates for every PENDING recipient in a job.

    Opens its own database session (each thread needs a separate session in SQLite).
    Updates job status and per-certificate status throughout.
    """
    db: Session = SessionLocal()
    try:
        job: GenerationJob | None = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error("Worker: job %s not found", job_id)
            return

        # Mark job as PROCESSING
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()

        # Fetch only PENDING certificates (allows partial retry)
        pending_certs: list[Certificate] = (
            db.query(Certificate)
            .filter(
                Certificate.job_id == job_id,
                Certificate.status == CertificateStatus.PENDING,
            )
            .all()
        )

        logger.info("Job %s: processing %d certificates", job_id, len(pending_certs))

        for cert in pending_certs:
            _process_one_certificate(db, job, cert)

        # Determine final job status
        db.refresh(job)
        if job.failed_count == 0:
            job.status = JobStatus.COMPLETED
        elif job.success_count == 0:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS

        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            "Job %s finished: %d succeeded, %d failed",
            job_id,
            job.success_count,
            job.failed_count,
        )

    except Exception:
        logger.exception("Unexpected error in worker for job %s", job_id)
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            logger.exception("Failed to mark job %s as FAILED", job_id)
    finally:
        db.close()


def _process_one_certificate(
    db: Session, job: GenerationJob, cert: Certificate
) -> None:
    """
    Generate a single PDF certificate for one recipient.

    Success or failure is recorded independently so other certificates continue.
    """
    cert.status = CertificateStatus.PROCESSING
    db.commit()

    try:
        filename = safe_filename(cert.certificate_id, cert.recipient_name)
        job_dir = CERTIFICATES_DIR / job.id
        output_path = job_dir / filename

        generate_certificate_pdf(
            output_path=output_path,
            recipient_name=cert.recipient_name,
            certificate_id=cert.certificate_id,
            event_name=job.event_name,
            certificate_title=job.certificate_title,
            organization=job.organization,
            issue_date=job.issue_date,
            description=job.description,
        )

        # Success
        cert.status = CertificateStatus.SUCCESS
        cert.file_path = str(output_path)
        cert.completed_at = datetime.utcnow()
        cert.error_message = None

        job.success_count += 1
        job.completed_count += 1

    except Exception as exc:
        # Failure — log but continue with next certificate
        logger.error(
            "Certificate generation failed for %s (job %s): %s",
            cert.certificate_id,
            job.id,
            exc,
        )
        cert.status = CertificateStatus.FAILED
        cert.error_message = str(exc)
        cert.completed_at = datetime.utcnow()
        cert.file_path = None

        job.failed_count += 1
        job.completed_count += 1

    finally:
        db.commit()
