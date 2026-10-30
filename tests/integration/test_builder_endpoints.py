import io
from fastapi.testclient import TestClient
from pypdf import PdfReader
import docx

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

