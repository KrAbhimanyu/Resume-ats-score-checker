from app.services.parser import extract_job_requirements, parse_resume_content
from app.services.quality import generate_resume_quality_report


def test_quality_report_covers_sections_writing_scores_and_ats_checks():
    resume = """Jordan Example
jordan@example.com
Professional Summary
Python engineer focused on reliable API development.
Skills
Python, FastAPI, SQL
Experience
- Built Python APIs with FastAPI for 120 users.
- Improved the the deployment workflow.
- Coordinated release planning with product and operations partners to align implementation priorities.
- Documented deployment procedures for engineering teams.
Education
Bachelor of Science
"""
    parsed_resume = parse_resume_content(resume)
    parsed_job = extract_job_requirements("Python and FastAPI engineer with API development experience.")

    report = generate_resume_quality_report(resume, parsed_resume, parsed_job)

    assert {section.name for section in report.section_analysis} >= {
        "Professional summary",
        "Experience",
        "Skills",
        "Education",
    }
    assert 0 <= report.readability_score <= 100
    assert "using" in report.readability_explanation
    assert 0 <= report.impact_score <= 100
    assert any(issue.category == "Repeated word" for issue in report.grammar_issues)
    assert {check.title for check in report.ats_compatibility_checks} == {
        "Standard section headings",
        "Readable text extraction",
        "Simple bullet structure",
        "Job requirement evidence",
    }
    assert "Python" in report.professional_summary_draft


def test_quality_report_handles_missing_sections_without_claiming_visual_layout():
    resume = "A short plain-text resume without headings."
    parsed_resume = parse_resume_content(resume)
    parsed_job = extract_job_requirements("Experienced analyst with SQL reporting skills.")

    report = generate_resume_quality_report(resume, parsed_resume, parsed_job)

    assert report.impact_score == 0
    assert any(not section.found for section in report.section_analysis)
    assert any("cannot confirm visual layout" in check.detail for check in report.ats_compatibility_checks)
    assert any("heading" in finding.lower() for finding in report.formatting_findings)


def test_contact_details_do_not_count_as_metrics_or_achievement_impact():
    resume = """Jordan Example
Email: jordan@example.com
Phone: +1 (415) 555-0134
Professional Summary
An experienced coordinator who communicates clearly with technical and business teams.
Work Experience
- Email: jordan@example.com | Phone: +1 (415) 555-0134
- Responsible for coordinating weekly handoffs between engineering and operations teams.
"""
    parsed_resume = parse_resume_content(resume)
    parsed_job = extract_job_requirements("Seeking an experienced coordinator for engineering operations.")
    report = generate_resume_quality_report(resume, parsed_resume, parsed_job)

    assert parsed_resume["metrics_found"] == []
    assert parsed_resume["bullet_count"] == 1
    assert report.impact_score == 0
    assert 0 <= report.readability_score <= 100
    assert "summary or achievement statement" in report.readability_explanation


def test_unmeasured_achievement_does_not_receive_impact_credit_from_dates_or_phone():
    resume = """Jordan Example
Phone: +1 415 555 0134
Work Experience
Software Engineer (2020 - 2024)
- Responsible for supporting application releases and reviewing deployment documentation.
"""
    parsed_resume = parse_resume_content(resume)
    parsed_job = extract_job_requirements("Seeking an engineer for application release work.")
    report = generate_resume_quality_report(resume, parsed_resume, parsed_job)

    assert parsed_resume["bullet_count"] == 1
    assert parsed_resume["metrics_found"] == []
    assert report.impact_score == 0


def test_action_verb_evidence_comes_only_from_experience_and_project_statements():
    resume = """Professional Summary
    Architected, optimized, designed, built, and managed reliable data products.
    Work Experience
    Data Analyst
    - Prepared weekly reports for business partners.
    """

    parsed_resume = parse_resume_content(resume)

    assert parsed_resume["bullet_count"] == 1
    assert parsed_resume["action_verbs"] == []
