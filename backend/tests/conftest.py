"""
pytest configuration and shared fixtures.

Uses an in-memory SQLite database so tests never touch the real DB.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from sqlalchemy.pool import StaticPool

# ── In-memory test database ───────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Dependency override that uses the test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test function."""
    from app.models import job, certificate  # noqa: F401 – ensure models are registered

    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI TestClient with the real database overridden to use in-memory SQLite.
    Each test gets a fresh database.
    """
    app.dependency_overrides[get_db] = override_get_db

    # Create tables for this test
    from app.models import job, certificate  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    from app.workers import certificate_worker
    original_session = certificate_worker.SessionLocal
    certificate_worker.SessionLocal = TestingSessionLocal

    with TestClient(app) as c:
        yield c

    certificate_worker.SessionLocal = original_session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


# ── Shared payload helpers ────────────────────────────────────────────────────

def make_job_payload(
    event_name: str = "Python Workshop",
    certificate_title: str = "Certificate of Completion",
    organization: str = "Test Org",
    issue_date: str = "2026-10-08",
    recipients=None,
):
    if recipients is None:
        recipients = [
            {"name": "Alice Smith", "email": "alice@example.com", "certificate_id": "CERT-001"},
            {"name": "Bob Jones", "email": "bob@example.com", "certificate_id": "CERT-002"},
        ]
    return {
        "event_name": event_name,
        "certificate_title": certificate_title,
        "organization": organization,
        "issue_date": issue_date,
        "recipients": recipients,
    }
