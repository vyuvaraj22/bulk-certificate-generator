"""
API routes for individual certificates.

Routes:
  GET /api/certificates/{cert_db_id}          – Get certificate metadata
  GET /api/certificates/{cert_db_id}/download – Download the certificate PDF
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import CertificateResponse
from app.services.job_service import get_certificate
from app.utils.helpers import resolve_certificate_path
from app.config import CERTIFICATES_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certificates", tags=["Certificates"])


@router.get(
    "/{cert_db_id}",
    response_model=CertificateResponse,
    summary="Get certificate metadata by database ID",
)
def get_certificate_metadata(
    cert_db_id: str, db: Session = Depends(get_db)
) -> CertificateResponse:
    cert = get_certificate(db, cert_db_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CERTIFICATE_NOT_FOUND", "message": "Certificate not found"},
        )
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


@router.get(
    "/{cert_db_id}/download",
    summary="Download the generated PDF for a certificate",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF download"},
        404: {"description": "Certificate not found or PDF file missing"},
    },
)
def download_certificate(cert_db_id: str, db: Session = Depends(get_db)) -> FileResponse:
    """
    Returns the generated PDF file for a successful certificate.

    Security:
    - Validates that the file path is within CERTIFICATES_DIR (prevents path traversal).
    - Does not expose raw filesystem paths in error messages.
    """
    cert = get_certificate(db, cert_db_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CERTIFICATE_NOT_FOUND", "message": "Certificate not found"},
        )

    if not cert.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_READY",
                "message": "Certificate PDF has not been generated yet.",
            },
        )

    pdf_path = Path(cert.file_path)

    # Security: prevent path traversal
    try:
        resolve_certificate_path(CERTIFICATES_DIR, pdf_path.name)
    except ValueError:
        logger.warning("Path traversal attempt for certificate %s", cert_db_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access denied"},
        )

    if not pdf_path.exists():
        logger.error("PDF file missing for certificate %s: %s", cert_db_id, cert.file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": "Certificate PDF file not found"},
        )

    safe_name = Path(cert.file_path).name
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )
