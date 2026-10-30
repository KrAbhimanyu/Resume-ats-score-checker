import io
import docx
from pypdf import PdfReader

from app.models.builder_schemas import (
    TargetMode,
    StructuredResume,
    ContactInfo,
    ExperienceItem,
    EducationItem,
)
from app.services.builder_service import (
    analyze_targeted_resume,
    parse_text_to_structured_resume,
    generate_docx_resume,
    generate_pdf_resume,
    match_role_profile,
    COMPANY_PROFILES,
)

SAMPLE_RESUME_TEXT = """Alex Morgan - Software Engineer
Email: alex.morgan@example.com | Phone: 555-0199 | Location: Seattle, WA | LinkedIn: linkedin.com/in/alexmorgan
Professional Summary
Software engineer with 4 years of experience building reliable web services and APIs.
Technical Skills
Languages: Python, TypeScript, SQL
Frameworks: FastAPI, React, Docker
Work Experience
Software Engineer - CloudTech (2021 - Present)
- Built REST APIs using Python, FastAPI, and PostgreSQL.
- Worked on API testing with Postman.
- Assisted with Docker deployment scripts.
Education
Bachelor of Science in Computer Science - State University (2017 - 2021)
"""


def test_faang_mode_with_job_description_priority():
    job_desc = """
    Google - Senior Software Engineer
    Minimum Qualifications:
    - 4+ years of software engineering experience
    - Proficiency in Python, FastAPI, and Kubernetes
    - Experience in distributed systems architecture and microservices
    - Strong understanding of unit testing and CI/CD pipelines
    """

    res = analyze_targeted_resume(
        resume_text=SAMPLE_RESUME_TEXT,
        target_mode=TargetMode.FAANG_BIG_TECH,
        company_name="Google",
        job_title="Software Engineer",
        job_description=job_desc,
    )

    assert res.target_mode == "faang_big_tech"
    assert res.company_name == "Google"
    assert res.has_job_description is True
    assert "Job Description" in res.guidance_source

    # Matched skills
    matched_names = [m.name for m in res.matched_skills]
    assert "python" in matched_names
    assert "fastapi" in matched_names

    # Missing skills from JD
    missing_names = [m.name for m in res.missing_requirements]
    assert "kubernetes" in missing_names or "ci/cd" in missing_names

    # Proposed rewrites
    assert len(res.proposed_changes) > 0
    # Must contain verified result placeholder
    assert any("[add verified result" in p.proposed_text for p in res.proposed_changes)


def test_any_company_mode_without_job_description():
    res = analyze_targeted_resume(
        resume_text=SAMPLE_RESUME_TEXT,
        target_mode=TargetMode.ANY_COMPANY,
        company_name="Acme Health Tech",
        industry="Healthcare",
        job_title="Backend Engineer",
        job_description="",
    )

    assert res.target_mode == "any_company"
    assert res.company_name == "Acme Health Tech"
    assert res.has_job_description is False
    assert "General Role-Specific Guidance" in res.guidance_source

    # Evaluates backend profile expectations
    matched_names = [m.name for m in res.matched_skills]
    assert "python" in matched_names


def test_sdet_qa_automation_role_expectations():
    sdet_profile = match_role_profile("SDET - Test Automation Lead")
    assert "sdet" in sdet_profile["canonical_title"].lower()
    assert "unit testing" in sdet_profile["essential_skills"]
    assert "rest api" in sdet_profile["essential_skills"]

    res = analyze_targeted_resume(
        resume_text=SAMPLE_RESUME_TEXT,
        target_mode=TargetMode.FAANG_BIG_TECH,
        company_name="Amazon",
        job_title="SDET",
        job_description="",
    )

    # Missing or weak automation requirements identified
    all_req_names = [m.name for m in res.missing_requirements + res.weakly_evidenced]
    assert any(s in all_req_names for s in ["ci/cd", "unit testing", "selenium", "playwright"])


def test_structured_resume_extraction():
    sr = parse_text_to_structured_resume(SAMPLE_RESUME_TEXT)

    assert "Alex Morgan" in sr.contact_info.full_name
    assert sr.contact_info.email == "alex.morgan@example.com"
    assert sr.contact_info.phone == "555-0199"
    assert "python" in [s.lower() for s in sr.skills.get("Languages", [])]
    assert len(sr.experience) >= 1
    assert "CloudTech" in sr.experience[0].company
    assert len(sr.experience[0].bullets) >= 2
    assert "Bachelor of Science" in sr.education[0].degree


def test_docx_export_generation_and_readability():
    sr = parse_text_to_structured_resume(SAMPLE_RESUME_TEXT)
    docx_bytes = generate_docx_resume(sr)

    assert len(docx_bytes) > 1000
    # Must be valid DOCX that python-docx can open
    doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "Alex Morgan" in full_text
    assert "alex.morgan@example.com" in full_text
    assert "CloudTech" in full_text
    assert "State University" in full_text


def test_pdf_export_generation_and_readability():
    sr = parse_text_to_structured_resume(SAMPLE_RESUME_TEXT)
    pdf_bytes = generate_pdf_resume(sr)

    assert len(pdf_bytes) > 1000
    # Must be valid PDF that pypdf can read
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    page1_text = reader.pages[0].extract_text()
    assert "Alex Morgan" in page1_text
    assert "alex.morgan@example.com" in page1_text
    assert "CloudTech" in page1_text
