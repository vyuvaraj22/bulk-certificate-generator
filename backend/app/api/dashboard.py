"""
API routes for dashboard and CSV utilities.

Routes:
  GET  /api/dashboard          – Aggregate statistics
  POST /api/csv/validate       – Validate an uploaded CSV before job creation
  GET  /api/csv/template       – Download the CSV template
"""

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import MAX_CSV_SIZE_BYTES, MAX_RECIPIENTS_PER_JOB
from app.database import get_db
from app.schemas.schemas import (
    CSVValidationResponse,
    DashboardStats,
    RecipientInput,
    RecipientValidationError,
)
from app.services.job_service import get_dashboard_stats

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Dashboard & Utilities"])


@router.get(
    "/api/dashboard",
    response_model=DashboardStats,
    summary="Get dashboard aggregate statistics",
)
def dashboard_stats(db: Session = Depends(get_db)) -> DashboardStats:
    return get_dashboard_stats(db)


@router.post(
    "/api/csv/validate",
    response_model=CSVValidationResponse,
    summary="Validate a CSV file of recipients before job creation",
)
async def validate_csv(file: UploadFile = File(...)) -> CSVValidationResponse:
    """
    Accepts a CSV file and validates each row.

    Expected columns: name, email, certificate_id

    Returns a list of valid recipients and validation errors per invalid row.
    Enforces size and row limits.
    """
    # Size guard
    contents = await file.read()
    if len(contents) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "CSV_TOO_LARGE",
                "message": f"CSV file must be under {MAX_CSV_SIZE_BYTES // 1024 // 1024} MB",
            },
        )

    # Decode
    try:
        text = contents.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ENCODING", "message": "CSV must be UTF-8 encoded"},
        )

    reader = csv.DictReader(io.StringIO(text))

    required_columns = {"name", "email", "certificate_id"}
    if not reader.fieldnames or not required_columns.issubset(
        {c.strip().lower() for c in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_COLUMNS",
                "message": f"CSV must have columns: {', '.join(sorted(required_columns))}",
            },
        )

    valid_recipients: list[RecipientInput] = []
    errors: list[RecipientValidationError] = []
    seen_ids: set[str] = set()
    row_number = 0

    for row_number, row in enumerate(reader, start=1):
        if row_number > MAX_RECIPIENTS_PER_JOB:
            errors.append(
                RecipientValidationError(
                    row=row_number,
                    field="row",
                    message=f"Exceeded maximum of {MAX_RECIPIENTS_PER_JOB} recipients",
                )
            )
            break

        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip()
        cert_id = (row.get("certificate_id") or "").strip()

        try:
            recipient = RecipientInput(name=name, email=email, certificate_id=cert_id)
        except ValidationError as exc:
            for err in exc.errors():
                field = err["loc"][0] if err["loc"] else "row"
                errors.append(
                    RecipientValidationError(
                        row=row_number,
                        field=str(field),
                        message=err["msg"],
                    )
                )
            continue

        # Duplicate check within file
        if cert_id in seen_ids:
            errors.append(
                RecipientValidationError(
                    row=row_number,
                    field="certificate_id",
                    message=f"Duplicate certificate ID: {cert_id!r}",
                )
            )
            continue

        seen_ids.add(cert_id)
        valid_recipients.append(recipient)

    total = row_number
    invalid = len({e.row for e in errors})
    valid = total - invalid

    return CSVValidationResponse(
        total=total,
        valid=valid,
        invalid=invalid,
        errors=errors,
        recipients=valid_recipients,
    )


@router.get(
    "/api/csv/template",
    summary="Download the CSV import template",
    responses={200: {"content": {"text/csv": {}}, "description": "CSV template file"}},
)
def download_csv_template() -> StreamingResponse:
    """Returns a ready-to-use CSV template with example rows."""
    content = (
        "name,email,certificate_id\n"
        "John Doe,john@example.com,CERT-001\n"
        "Jane Smith,jane@example.com,CERT-002\n"
    )
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="certificate_template.csv"'},
    )
