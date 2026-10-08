"""Application configuration using environment variables with sensible defaults."""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/certificates.db")

# File storage
CERTIFICATES_DIR = Path(os.getenv("CERTIFICATES_DIR", str(BASE_DIR / "generated_certificates")))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", str(BASE_DIR / "templates")))

# Ensure directories exist
CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Upload limits
MAX_CSV_SIZE_BYTES = int(os.getenv("MAX_CSV_SIZE_BYTES", str(5 * 1024 * 1024)))  # 5MB
MAX_RECIPIENTS_PER_JOB = int(os.getenv("MAX_RECIPIENTS_PER_JOB", "1000"))

# App settings
APP_TITLE = "Bulk Certificate Generator"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Generate bulk certificates for events, courses, and workshops."

# CORS origins (comma-separated in env var)
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")
