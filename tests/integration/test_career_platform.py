import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import settings
from app.db.database import reset_migration_cache_for_tests
from app.main import app


@pytest.fixture
def career_client(tmp_path, monkeypatch):
    database_file = tmp_path / "career-platform.sqlite3"
    monkeypatch.setattr(settings, "JOB_DATABASE_PATH", str(database_file))
    monkeypatch.setattr(settings, "JOB_DATA_ENCRYPTION_KEY", "")
    reset_migration_cache_for_tests()
    with TestClient(app) as client:
        yield client, database_file
    reset_migration_cache_for_tests()


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/career/auth/register",
        json={"email": email, "password": "secure-password-123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_resume_storage_requires_encryption_and_is_user_scoped(career_client):
    client, database_file = career_client
    headers = _register(client, "candidate@example.com")
    resume_text = (
        "Senior software engineer with Python, FastAPI, SQL, and cloud experience. "
        "Designed reliable services, improved application performance, mentored teams, "
        "built secure APIs, and delivered measurable customer outcomes across several "
        "production projects with cross-functional engineering partners."
    )

    unavailable = client.post(
        "/api/v1/career/profile/resumes",
        headers=headers,
        json={"title": "Primary", "resume_text": resume_text},
    )
    assert unavailable.status_code == 503

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "JOB_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    try:
        saved = client.post(
            "/api/v1/career/profile/resumes",
            headers=headers,
            json={"title": "Primary", "resume_text": resume_text},
        )
        assert saved.status_code == 201
        resume_id = saved.json()["id"]

        with sqlite3.connect(database_file) as connection:
            stored_value = connection.execute(
                "SELECT resume_text FROM resume_profiles WHERE id=?", (resume_id,)
            ).fetchone()[0]
        assert resume_text not in stored_value
        assert stored_value.startswith("fernet:v1:")

        another_user = _register(client, "other@example.com")
        denied = client.get(
            f"/api/v1/career/profile/resumes/{resume_id}", headers=another_user
        )
        assert denied.status_code == 404

        retrieved = client.get(
            f"/api/v1/career/profile/resumes/{resume_id}", headers=headers
        )
        assert retrieved.status_code == 200
        assert retrieved.json()["resume_text"] == resume_text
    finally:
        monkeypatch.undo()


def test_application_status_history_and_interviews_are_persisted(career_client, monkeypatch):
    client, database_file = career_client
    monkeypatch.setattr(settings, "JOB_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    headers = _register(client, "tracker@example.com")

    created = client.post(
        "/api/v1/career/applications",
        headers=headers,
        json={
            "title": "Backend Engineer",
            "company_name": "Example Co",
            "status": "saved",
            "notes": "Reach out to the hiring manager next week.",
        },
    )
    assert created.status_code == 201
    application_id = created.json()["id"]
    assert created.json()["notes"] == "Reach out to the hiring manager next week."

    changed = client.patch(
        f"/api/v1/career/applications/{application_id}",
        headers=headers,
        json={"status": "applied", "note": "Submitted through the company portal."},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "applied"

    history = client.get(
        f"/api/v1/career/applications/{application_id}/history", headers=headers
    )
    assert history.status_code == 200
    assert history.json()[-1]["note"] == "Submitted through the company portal."

    schedule = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    interview = client.post(
        "/api/v1/career/interviews",
        headers=headers,
        json={
            "application_id": application_id,
            "scheduled_at": schedule,
            "timezone": "UTC",
            "interview_type": "technical",
            "interviewer_details": "Two engineering interviewers",
            "preparation_notes": "Review system design examples.",
        },
    )
    assert interview.status_code == 201
    interview_id = interview.json()["id"]
    assert interview.json()["preparation_notes"] == "Review system design examples."

    upcoming = client.get("/api/v1/career/interviews", headers=headers)
    assert upcoming.status_code == 200
    assert upcoming.json()[0]["id"] == interview_id
    assert upcoming.json()[0]["interviewer_details"] == "Two engineering interviewers"

    with sqlite3.connect(database_file) as connection:
        saved_notes = connection.execute(
            "SELECT notes FROM applications WHERE id=?", (application_id,)
        ).fetchone()[0]
        interviewer_notes = connection.execute(
            "SELECT preparation_notes FROM interviews WHERE id=?", (interview_id,)
        ).fetchone()[0]
    assert saved_notes.startswith("fernet:v1:")
    assert interviewer_notes.startswith("fernet:v1:")

    preferences = client.put(
        "/api/v1/career/profile/preferences",
        headers=headers,
        json={"interview_reminder_hours": [24, 1]},
    )
    assert preferences.status_code == 200
    rescheduled_at = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    rescheduled = client.patch(
        f"/api/v1/career/interviews/{interview_id}",
        headers=headers,
        json={"scheduled_at": rescheduled_at},
    )
    assert rescheduled.status_code == 200
    assert rescheduled.json()["scheduled_at"] == rescheduled_at
    reminders = client.get("/api/v1/career/reminders", headers=headers)
    related = [item for item in reminders.json()["reminders"] if item["interview_id"] == interview_id]
    assert sum(item["status"] == "completed" for item in related) == 2
    assert sum(item["status"] == "scheduled" for item in related) == 2


def test_job_matching_and_approved_tailoring_create_an_exportable_version(career_client, monkeypatch):
    client, _ = career_client
    monkeypatch.setattr(settings, "JOB_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    headers = _register(client, "tailoring@example.com")
    resume_text = (
        "Alex Candidate\nProfessional Summary\nSenior backend engineer with Python, FastAPI, SQL, AWS, "
        "and cloud service experience.\nSkills\nPython FastAPI SQL AWS Docker\nExperience\n"
        "Backend Engineer at Example Co\n- Worked on secure APIs and database services.\n"
        "- Built resilient cloud applications for production teams.\nEducation\n"
        "Bachelor of Science in Computer Science"
    )
    resume = client.post(
        "/api/v1/career/profile/resumes",
        headers=headers,
        json={"title": "Original", "resume_text": resume_text},
    )
    assert resume.status_code == 201

    job = client.post(
        "/api/v1/career/jobs",
        headers=headers,
        json={
            "title": "Backend Engineer",
            "company_name": "Example Co",
            "description": (
                "Backend Engineer. Required skills: Python, FastAPI, SQL, and AWS. "
                "Responsibilities include building secure APIs and reliable database services."
            ),
        },
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    match = client.post(
        "/api/v1/career/jobs/match",
        headers=headers,
        json={"job_id": job_id},
    )
    assert match.status_code == 200
    assert 0 <= match.json()["score"] <= 100
    assert "technical_skills" in match.json()["factors"]

    review = client.post(
        f"/api/v1/career/jobs/job/{job_id}/tailor",
        headers=headers,
    )
    assert review.status_code == 201
    summary_change = next(change for change in review.json()["changes"] if change["section"] == "summary")
    assert summary_change["is_accepted"] is False

    approved = client.patch(
        f"/api/v1/career/tailoring/{review.json()['id']}",
        headers=headers,
        json={"changes": [{"id": summary_change["id"], "is_accepted": True}]},
    )
    assert approved.status_code == 200
    version = client.post(
        f"/api/v1/career/tailoring/{review.json()['id']}/save-version",
        headers=headers,
    )
    assert version.status_code == 201
    assert version.json()["source_resume_id"] == resume.json()["id"]

    exported = client.post(
        "/api/v1/builder/export",
        headers=headers,
        json={"format": "pdf", "resume": version.json()["structured_resume"]},
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/pdf"


def test_provider_status_reports_disabled_integrations_without_credentials(career_client):
    client, _ = career_client
    headers = _register(client, "providers@example.com")

    response = client.get("/api/v1/career/providers", headers=headers)

    assert response.status_code == 200
    assert all(not provider["enabled"] for provider in response.json())
