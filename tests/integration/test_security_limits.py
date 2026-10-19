import logging
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.core.security import safe_temp_file


def test_oversized_upload_rejected(client: TestClient, sample_fullstack_job):
    # Create 6 MB payload (exceeding 5 MB limit)
    large_pdf_header = b"%PDF-1.4\n"
    large_payload = large_pdf_header + b"0" * (6 * 1024 * 1024)

    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("huge_resume.pdf", large_payload, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 413
    err = response.json()["error"]
    assert err["code"] == "FILE_TOO_LARGE"


def test_file_extension_spoofing_rejected(client: TestClient, sample_fullstack_job):
    # Malicious file: executable content with .pdf extension
    fake_exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("malicious.pdf", fake_exe_content, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert err["code"] == "INVALID_FILE_TYPE"


def test_temp_file_cleanup_on_success():
    created_path = None
    with safe_temp_file(b"test temporary content", suffix=".docx") as path:
        created_path = path
        assert os.path.exists(created_path)

    # After exiting context, file MUST be deleted
    assert not os.path.exists(created_path)


def test_temp_file_cleanup_on_exception():
    created_path = None
    try:
        with safe_temp_file(b"test temporary content", suffix=".docx") as path:
            created_path = path
            assert os.path.exists(created_path)
            raise RuntimeError("Simulated processing error")
    except RuntimeError:
        pass

    # File MUST be deleted even after exception
    assert not os.path.exists(created_path)


def test_privacy_no_resume_text_in_logs(client: TestClient, caplog, sample_senior_pdf, sample_fullstack_job):
    caplog.set_level(logging.INFO, logger="ats_checker")

    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("senior_software_engineer.pdf", sample_senior_pdf, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 200

    log_text = caplog.text
    # Log must contain operational metrics:
    assert "Analysis completed in" in log_text
    assert "senior_software_engineer.pdf" in log_text

    # Log must NOT contain personal resume sentences or PII
    assert "alex.morgan.fictional@example.com" not in log_text
    assert "Architected and deployed microservices backend" not in log_text
