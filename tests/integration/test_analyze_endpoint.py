import os
from fastapi.testclient import TestClient


def test_analyze_valid_pdf_success(client: TestClient, sample_senior_pdf, sample_fullstack_job):
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("senior_software_engineer.pdf", sample_senior_pdf, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 200
    data = response.json()

    # Core response assertions
    assert "overall_score" in data
    assert 0.0 <= data["overall_score"] <= 100.0
    assert data["score_label"] == "Estimated Resume–Job Match Score"
    assert data["match_tier"] in ["Exceptional Match", "Strong Match", "Good Match", "Fair Match", "Low Match"]

    # Category scores check (must have all 5 categories)
    cat_scores = data["category_scores"]
    assert len(cat_scores) == 5
    cat_ids = {c["category_id"] for c in cat_scores}
    expected_cats = {
        "keyword_coverage",
        "skills_match",
        "experience_evidence",
        "education_qualifications",
        "document_structure",
    }
    assert cat_ids == expected_cats

    # Verify document metadata
    meta = data["document_metadata"]
    assert meta["filename"] == "senior_software_engineer.pdf"
    assert meta["file_type"] == ".pdf"
    assert meta["word_count"] > 50

    # Verify recommendations exist
    assert len(data["recommendations"]) > 0

    # Verify disclaimer is present
    assert "Estimated Resume–Job Match Score" in data["limitations_disclaimer"]


def test_analyze_valid_docx_success(client: TestClient, sample_senior_docx, sample_fullstack_job):
    response = client.post(
        "/api/v1/analyze",
        files={
            "resume_file": (
                "senior_software_engineer.docx",
                sample_senior_docx,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] >= 60.0
    assert data["document_metadata"]["file_type"] == ".docx"


def test_analyze_empty_job_description_rejected(client: TestClient, sample_senior_pdf):
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("resume.pdf", sample_senior_pdf, "application/pdf")},
        data={"job_description": ""},
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert err["code"] == "EMPTY_JOB_DESCRIPTION"


def test_analyze_whitespace_job_description_rejected(client: TestClient, sample_senior_pdf):
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("resume.pdf", sample_senior_pdf, "application/pdf")},
        data={"job_description": "     \n\t  "},
    )
    assert response.status_code == 400


def test_analyze_empty_resume_rejected(client: TestClient, fixtures_dir, sample_fullstack_job):
    empty_pdf_path = os.path.join(fixtures_dir, "sample_resumes", "empty_resume.pdf")
    with open(empty_pdf_path, "rb") as f:
        content = f.read()

    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("empty.pdf", content, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 422
    err = response.json()["error"]
    assert err["code"] == "EMPTY_RESUME"


def test_analyze_corrupt_pdf_rejected(client: TestClient, fixtures_dir, sample_fullstack_job):
    corrupt_pdf_path = os.path.join(fixtures_dir, "sample_resumes", "corrupt_file.pdf")
    with open(corrupt_pdf_path, "rb") as f:
        content = f.read()

    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("corrupt.pdf", content, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code in [400, 422]


def test_analyze_unsupported_file_extension(client: TestClient, sample_fullstack_job):
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("resume.txt", b"Some plain text resume content.", "text/plain")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"
