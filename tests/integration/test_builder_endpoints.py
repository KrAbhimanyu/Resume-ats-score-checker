import io
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader
import docx

from app.api.v1.endpoints.builder import _enforce_resume_ai_rate_limit
from app.models.builder_schemas import StructuredResume, ContactInfo, ExperienceItem


def test_builder_analyze_and_plan_multipart(client: TestClient, sample_senior_pdf):
    response = client.post(
        "/api/v1/builder/analyze-and-plan",
        files={"resume_file": ("senior.pdf", sample_senior_pdf, "application/pdf")},
        data={
            "target_mode": "faang_big_tech",
            "company_name": "Google",
            "job_title": "Senior Software Engineer",
            "job_description": "We are seeking a Senior Software Engineer with deep Python, FastAPI, and Kubernetes experience.",
            "sections_to_improve": "summary,skills,experience",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["target_mode"] == "faang_big_tech"
    assert data["company_name"] == "Google"
    assert data["has_job_description"] is True
    assert len(data["matched_skills"]) > 0
    assert len(data["proposed_changes"]) > 0
    assert data["draft_resume"]["contact_info"]["full_name"] != ""


def test_builder_analyze_and_plan_json(client: TestClient):
    payload = {
        "resume_text": "Alex Morgan - Senior Engineer with 6 years experience in Python, FastAPI, PostgreSQL, and Docker. Built microservices serving 50k users.",
        "target_mode": "any_company",
        "company_name": "Fintech Solutions",
        "industry": "Finance",
        "job_title": "Backend Developer",
        "job_description": "",
        "sections_to_improve": ["summary", "skills", "experience"],
    }
    response = client.post("/api/v1/builder/analyze-and-plan-json", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["target_mode"] == "any_company"
    assert data["company_name"] == "Fintech Solutions"
    assert data["has_job_description"] is False
    assert len(data["prioritized_improvements"]) > 0


def test_resume_ai_requires_authentication(client: TestClient):
    response = client.post(
        "/api/v1/builder/ai",
        json={
            "operation": "summary",
            "resume": {
                "contact_info": {"full_name": "Candidate"},
                "summary": "",
                "skills": {},
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
            },
            "source_text": "",
            "target_role": "Software Engineer",
            "job_description": "",
            "industry": "Technology",
            "experience_level": "Experienced",
            "tone": "professional",
        },
    )
    assert response.status_code == 401


def test_resume_ai_rate_limit_is_enforced():
    user_id = str(uuid.uuid4())
    for _ in range(5):
        _enforce_resume_ai_rate_limit(user_id)

    with pytest.raises(HTTPException) as error:
        _enforce_resume_ai_rate_limit(user_id)

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "900"


def test_builder_export_docx_endpoint(client: TestClient):
    resume_payload = {
        "format": "docx",
        "filename": "custom_resume",
        "resume": {
            "contact_info": {
                "full_name": "Jane Developer",
                "email": "jane@example.com",
                "phone": "555-123-4567",
                "location": "New York, NY",
                "linkedin": "linkedin.com/in/janedev",
                "github": "github.com/janedev",
            },
            "summary": "Targeted software engineer specializing in backend systems.",
            "skills": {
                "Languages": ["Python", "SQL"],
                "Frameworks & Libraries": ["FastAPI", "React"],
            },
            "experience": [
                {
                    "id": "exp-1",
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "bullets": ["Engineered REST APIs using FastAPI, serving 10k users."],
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
        },
    }

    response = client.post("/api/v1/builder/export", json=resume_payload)
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers["content-type"]
    assert "attachment; filename=\"custom_resume.docx\"" in response.headers["content-disposition"]

    # Verify binary docx content
    doc = docx.Document(io.BytesIO(response.content))
    assert any("Jane Developer" in p.text for p in doc.paragraphs)


def test_builder_export_respects_template_locale_and_custom_sections(client: TestClient):
    response = client.post(
        "/api/v1/builder/export",
        json={
            "format": "docx",
            "template_id": "ats-healthcare-teal",
            "international_format": "uk",
            "resume": {
                "contact_info": {"full_name": "Jane Example"},
                "summary": "Healthcare analyst with verified experience.",
                "skills": {"Clinical": ["Research"]},
                "experience": [{
                    "id": "exp-1",
                    "title": "Analyst",
                    "company": "Example Hospital",
                    "start_date": "2024-01",
                    "end_date": "2025-02",
                    "bullets": ["Reviewed records."],
                }],
                "projects": [],
                "education": [],
                "certifications": [],
                "custom_sections": {"Publications": ["Published a peer-reviewed paper."]},
            },
        },
    )
    assert response.status_code == 200
    paragraphs = [paragraph.text for paragraph in docx.Document(io.BytesIO(response.content)).paragraphs]
    assert any("2024-01 - 2025-02" in paragraph for paragraph in paragraphs)
    assert "PUBLICATIONS" in paragraphs
    assert any("Published a peer-reviewed paper." in paragraph for paragraph in paragraphs)


def test_builder_export_rejects_unknown_template(client: TestClient):
    response = client.post(
        "/api/v1/builder/export",
        json={
            "format": "pdf",
            "template_id": "unknown-theme",
            "resume": {
                "contact_info": {"full_name": "Test"},
                "skills": {},
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
            },
        },
    )
    assert response.status_code == 400
    assert "Unknown resume template" in response.json()["detail"]


def test_builder_export_pdf_endpoint(client: TestClient):
    resume_payload = {
        "format": "pdf",
        "filename": "custom_resume",
        "resume": {
            "contact_info": {
                "full_name": "Jane Developer",
                "email": "jane@example.com",
            },
            "summary": "Targeted software engineer specializing in backend systems.",
            "skills": {"Languages": ["Python"]},
            "experience": [
                {
                    "id": "exp-1",
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "bullets": ["Engineered REST APIs using FastAPI."],
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
        },
    }

    response = client.post("/api/v1/builder/export", json=resume_payload)
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment; filename=\"custom_resume.pdf\"" in response.headers["content-disposition"]

    # Verify binary pdf content
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) >= 1
    assert "Jane Developer" in reader.pages[0].extract_text()


def test_builder_export_unsupported_format(client: TestClient):
    resume_payload = {
        "format": "txt",
        "resume": {
            "contact_info": {"full_name": "Test"},
            "summary": "Summary",
            "skills": {},
            "experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
        },
    }
    response = client.post("/api/v1/builder/export", json=resume_payload)
    assert response.status_code == 400
