"""
Tests for the certificate generation job API.

Covers:
1. Job creation
2. Input validation
3. Certificate generation (PDF produced)
4. Job status / progress lifecycle
5. Independent certificate failure (one fail doesn't stop others)
6. Certificate retrieval
7. Retry failed certificates
8. ZIP download
"""

import io
import time
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import make_job_payload


# ─────────────────────────────────────────────
# 1. Test: Job creation
# ─────────────────────────────────────────────

class TestJobCreation:
    def test_create_job_returns_202(self, client):
        payload = make_job_payload()
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 202, response.text

    def test_create_job_response_shape(self, client):
        payload = make_job_payload()
        response = client.post("/api/jobs", json=payload)
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ("QUEUED", "PROCESSING")
        assert data["total"] == len(payload["recipients"])

    def test_create_job_with_multiple_recipients(self, client):
        recipients = [
            {"name": f"Person {i}", "email": f"p{i}@example.com", "certificate_id": f"C-{i:03d}"}
            for i in range(1, 11)
        ]
        payload = make_job_payload(recipients=recipients)
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 202
        assert response.json()["total"] == 10

    def test_create_job_stored_in_database(self, client):
        payload = make_job_payload()
        create_response = client.post("/api/jobs", json=payload)
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["event_name"] == payload["event_name"]
        assert data["organization"] == payload["organization"]


# ─────────────────────────────────────────────
# 2. Test: Input validation
# ─────────────────────────────────────────────

class TestInputValidation:
    def test_missing_name_rejected(self, client):
        payload = make_job_payload(
            recipients=[{"name": "", "email": "a@b.com", "certificate_id": "C-1"}]
        )
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_invalid_email_rejected(self, client):
        payload = make_job_payload(
            recipients=[{"name": "John Doe", "email": "not-an-email", "certificate_id": "C-1"}]
        )
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_certificate_id_rejected(self, client):
        payload = make_job_payload(
            recipients=[{"name": "John Doe", "email": "john@example.com", "certificate_id": ""}]
        )
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_duplicate_certificate_ids_rejected(self, client):
        payload = make_job_payload(
            recipients=[
                {"name": "John Doe", "email": "john@example.com", "certificate_id": "CERT-1"},
                {"name": "Jane Doe", "email": "jane@example.com", "certificate_id": "CERT-1"},
            ]
        )
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_event_name_rejected(self, client):
        payload = make_job_payload()
        payload["event_name"] = ""
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_empty_recipients_rejected(self, client):
        payload = make_job_payload(recipients=[])
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422

    def test_invalid_issue_date_rejected(self, client):
        payload = make_job_payload(issue_date="not-a-date")
        response = client.post("/api/jobs", json=payload)
        assert response.status_code == 422


# ─────────────────────────────────────────────
# 3. Test: Certificate generation (PDF produced)
# ─────────────────────────────────────────────

class TestCertificateGeneration:
    def test_pdf_is_generated(self, client, tmp_path):
        """
        We patch CERTIFICATES_DIR so PDFs are written to tmp_path.
        We also run the worker synchronously by waiting for completion.
        """
        payload = make_job_payload(
            recipients=[
                {"name": "Alice Test", "email": "alice@test.com", "certificate_id": "T-001"}
            ]
        )

        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            assert response.status_code == 202
            job_id = response.json()["job_id"]

            # Wait for background worker
            for _ in range(30):
                time.sleep(0.2)
                status_resp = client.get(f"/api/jobs/{job_id}")
                if status_resp.json()["status"] in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                    break

            # Verify PDF exists
            job_dir = tmp_path / job_id
            pdfs = list(job_dir.glob("*.pdf"))
            assert len(pdfs) >= 1

    def test_pdf_has_valid_header(self, client, tmp_path):
        """Verify the generated file starts with the PDF magic bytes."""
        payload = make_job_payload(
            recipients=[
                {"name": "Bob Gen", "email": "bob@gen.com", "certificate_id": "G-001"}
            ]
        )
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            for _ in range(30):
                time.sleep(0.2)
                st = client.get(f"/api/jobs/{job_id}").json()["status"]
                if st in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                    break

            job_dir = tmp_path / job_id
            pdfs = list(job_dir.glob("*.pdf"))
            assert pdfs, "No PDF generated"
            assert pdfs[0].read_bytes()[:4] == b"%PDF"


# ─────────────────────────────────────────────
# 4. Test: Job status / progress lifecycle
# ─────────────────────────────────────────────

class TestJobStatusLifecycle:
    def test_job_not_found_returns_404(self, client):
        response = client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_job_reaches_completed_status(self, client, tmp_path):
        payload = make_job_payload()
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            final_status = None
            for _ in range(30):
                time.sleep(0.3)
                st = client.get(f"/api/jobs/{job_id}").json()["status"]
                if st in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                    final_status = st
                    break

            assert final_status in ("COMPLETED", "COMPLETED_WITH_ERRORS")

    def test_progress_counters_are_accurate(self, client, tmp_path):
        recipients = [
            {"name": f"User{i}", "email": f"u{i}@example.com", "certificate_id": f"PC-{i}"}
            for i in range(1, 4)
        ]
        payload = make_job_payload(recipients=recipients)
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                data = client.get(f"/api/jobs/{job_id}").json()
                if data["status"] in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                    break

            assert data["total"] == 3
            assert data["completed"] == data["successful"] + data["failed"]


# ─────────────────────────────────────────────
# 5. Test: Independent certificate failure
# ─────────────────────────────────────────────

class TestIndependentFailure:
    def test_one_failure_does_not_stop_others(self, client, tmp_path):
        """
        Patch generate_certificate_pdf to raise on the first call only.
        Verify that remaining certificates still succeed.
        """
        from app.services import certificate_service

        call_count = 0
        original = certificate_service.generate_certificate_pdf

        def patched_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated generation failure")
            return original(*args, **kwargs)

        recipients = [
            {"name": f"Person{i}", "email": f"p{i}@test.com", "certificate_id": f"F-{i}"}
            for i in range(1, 4)
        ]
        payload = make_job_payload(recipients=recipients)

        with (
            patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path),
            patch(
                "app.workers.certificate_worker.generate_certificate_pdf",
                side_effect=patched_generate,
            ),
        ):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                data = client.get(f"/api/jobs/{job_id}").json()
                if data["status"] in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                    break

        assert data["failed"] >= 1
        assert data["successful"] >= 1
        assert data["status"] == "COMPLETED_WITH_ERRORS"


# ─────────────────────────────────────────────
# 6. Test: Certificate retrieval
# ─────────────────────────────────────────────

class TestCertificateRetrieval:
    def test_list_certificates_for_job(self, client, tmp_path):
        payload = make_job_payload()
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                if client.get(f"/api/jobs/{job_id}").json()["status"] in (
                    "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"
                ):
                    break

            certs_response = client.get(f"/api/jobs/{job_id}/certificates")
            assert certs_response.status_code == 200
            data = certs_response.json()
            assert data["total"] == len(payload["recipients"])

    def test_download_certificate_pdf(self, client, tmp_path):
        payload = make_job_payload(
            recipients=[{"name": "Download Test", "email": "dl@test.com", "certificate_id": "DL-1"}]
        )
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            response = client.post("/api/jobs", json=payload)
            job_id = response.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                if client.get(f"/api/jobs/{job_id}").json()["status"] in (
                    "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"
                ):
                    break

            certs = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]
            success_certs = [c for c in certs if c["status"] == "SUCCESS"]
            assert success_certs, "No successful certificates found"

            cert_db_id = success_certs[0]["id"]
            dl_response = client.get(f"/api/certificates/{cert_db_id}/download")
            assert dl_response.status_code == 200
            assert dl_response.headers["content-type"] == "application/pdf"
            assert dl_response.content[:4] == b"%PDF"


# ─────────────────────────────────────────────
# 7. Test: Retry failed certificates
# ─────────────────────────────────────────────

class TestRetryFailed:
    def test_retry_resets_failed_certs(self, client, tmp_path):
        from app.services import certificate_service

        call_count = 0
        original = certificate_service.generate_certificate_pdf

        def fail_first(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Forced failure")
            return original(*args, **kwargs)

        payload = make_job_payload(
            recipients=[
                {"name": "Retry User", "email": "retry@test.com", "certificate_id": "R-1"},
                {"name": "OK User", "email": "ok@test.com", "certificate_id": "R-2"},
            ]
        )

        with (
            patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path),
            patch(
                "app.workers.certificate_worker.generate_certificate_pdf",
                side_effect=fail_first,
            ),
        ):
            resp = client.post("/api/jobs", json=payload)
            job_id = resp.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                if client.get(f"/api/jobs/{job_id}").json()["status"] in (
                    "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"
                ):
                    break

        # Now retry — the mock is gone, so retry should succeed
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            retry_resp = client.post(f"/api/jobs/{job_id}/retry-failed")
            assert retry_resp.status_code == 200
            assert retry_resp.json()["retried_count"] >= 1

    def test_retry_on_job_with_no_failures(self, client, tmp_path):
        payload = make_job_payload(
            recipients=[{"name": "Success User", "email": "su@test.com", "certificate_id": "S-1"}]
        )
        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            resp = client.post("/api/jobs", json=payload)
            job_id = resp.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                if client.get(f"/api/jobs/{job_id}").json()["status"] in (
                    "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"
                ):
                    break

            retry_resp = client.post(f"/api/jobs/{job_id}/retry-failed")
            assert retry_resp.status_code == 200
            assert retry_resp.json()["retried_count"] == 0


# ─────────────────────────────────────────────
# 8. Test: ZIP download
# ─────────────────────────────────────────────

class TestZipDownload:
    def test_zip_contains_successful_pdfs(self, client, tmp_path):
        recipients = [
            {"name": f"Zip User{i}", "email": f"z{i}@test.com", "certificate_id": f"Z-{i}"}
            for i in range(1, 4)
        ]
        payload = make_job_payload(recipients=recipients)

        with patch("app.workers.certificate_worker.CERTIFICATES_DIR", tmp_path):
            resp = client.post("/api/jobs", json=payload)
            job_id = resp.json()["job_id"]

            for _ in range(30):
                time.sleep(0.3)
                if client.get(f"/api/jobs/{job_id}").json()["status"] in (
                    "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"
                ):
                    break

            zip_resp = client.get(f"/api/jobs/{job_id}/download")
            assert zip_resp.status_code == 200
            assert "zip" in zip_resp.headers["content-type"]

            # Verify it's a valid ZIP with PDFs
            zf = zipfile.ZipFile(io.BytesIO(zip_resp.content))
            names = zf.namelist()
            assert all(n.endswith(".pdf") for n in names)
            assert len(names) >= 1

    def test_zip_download_on_nonexistent_job(self, client):
        response = client.get("/api/jobs/nonexistent/download")
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Miscellaneous
# ─────────────────────────────────────────────

class TestHealthAndDashboard:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_dashboard_stats(self, client):
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "total_certificates" in data
