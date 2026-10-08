"""Utility helpers: safe filenames, UUID generation, path validation."""

import re
import uuid
from pathlib import Path


def generate_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def safe_filename(certificate_id: str, recipient_name: str) -> str:
    """
    Build a safe filename from certificate ID and recipient name.

    Example: CERT-001_John_Doe.pdf

    Rules:
    - Replace any non-alphanumeric characters (except hyphens) with underscores.
    - Collapse consecutive underscores.
    - Remove leading/trailing underscores from each component.
    - Ensure the filename does not exceed 200 characters (excluding extension).
    """
    def sanitize(text: str) -> str:
        text = re.sub(r"[^\w\-]", "_", text)  # keep word chars and hyphens
        text = re.sub(r"_+", "_", text)       # collapse underscores
        return text.strip("_")

    safe_id = sanitize(certificate_id)
    safe_name = sanitize(recipient_name)

    filename = f"{safe_id}_{safe_name}"
    # Truncate to 200 chars to avoid OS path limits
    if len(filename) > 200:
        filename = filename[:200]

    return f"{filename}.pdf"


def resolve_certificate_path(directory: Path, filename: str) -> Path:
    """
    Safely resolve a certificate file path, preventing path traversal.

    Raises ValueError if the resolved path escapes the intended directory.
    """
    resolved = (directory / filename).resolve()
    if not str(resolved).startswith(str(directory.resolve())):
        raise ValueError(f"Path traversal detected for filename: {filename!r}")
    return resolved


def generate_certificate_id_sequence(prefix: str, count: int, start: int = 1) -> list[str]:
    """
    Generate sequential certificate IDs.

    Example: generate_certificate_id_sequence("CERT-2026", 3) ->
    ["CERT-2026-0001", "CERT-2026-0002", "CERT-2026-0003"]
    """
    return [f"{prefix}-{str(i).zfill(4)}" for i in range(start, start + count)]
