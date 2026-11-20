import io
import os
from reportlab.pdfgen import canvas
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

    quality_report = data["quality_report"]
    assert 0.0 <= quality_report["readability_score"] <= 100.0
    assert 0.0 <= quality_report["impact_score"] <= 100.0
    assert quality_report["section_analysis"]
    assert quality_report["ats_compatibility_checks"]
    assert quality_report["professional_summary_draft"]
    section_results = {item["name"]: item["found"] for item in quality_report["section_analysis"]}
    assert section_results["Experience"] is True
    assert data["improvement_assistant"]["bullet_improvements"]
    assert all(
        "@" not in item["original_text"]
        for item in data["improvement_assistant"]["bullet_improvements"]
    )

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
    section_results = {item["name"]: item["found"] for item in data["quality_report"]["section_analysis"]}
    assert section_results["Experience"] is True


def _create_pdf(lines: list[str]) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    for index, line in enumerate(lines):
        pdf.drawString(40, 780 - index * 24, line)
    pdf.save()
    return output.getvalue()


def test_analyze_spaced_pdf_headings_and_contact_details(client: TestClient, sample_fullstack_job):
    content = _create_pdf([
        "Jordan Example",
        "Email: jordan@example.com | Phone: +1 (415) 555-0134",
        "W o r k  E x p e r i e n c e",
        "- Email: jordan@example.com | Phone: +1 (415) 555-0134",
        "- Built internal reporting tools used by multiple departments.",
        "S k i l l s",
        "Python SQL reporting collaboration data quality systems",
        "E d u c a t i o n",
        "Bachelor of Science in Information Systems at Example University",
        "Additional coursework included database systems, software design, communication, and team collaboration.",
    ])
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("spaced.pdf", content, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )

    assert response.status_code == 200
    data = response.json()
    sections = {item["name"]: item["found"] for item in data["quality_report"]["section_analysis"]}
    assert sections["Experience"] is True
    assert sections["Skills"] is True
    assert sections["Education"] is True
    assert not any("heading" in warning.lower() for warning in data["document_metadata"]["extraction_warnings"])
    suggestions = data["improvement_assistant"]["bullet_improvements"]
    assert suggestions
    assert all("@" not in item["original_text"] for item in suggestions)
    assert all("+1 (415)" not in item["original_text"] for item in suggestions)


def test_analyze_warns_when_no_standard_headings_are_detected(client: TestClient, sample_fullstack_job):
    content = _create_pdf([
        "Jordan Example",
        "Jordan is a software professional with a background in product delivery and team collaboration.",
        "Built and maintained internal reporting tools for several departments.",
        "Experienced in documenting processes, coordinating work, and supporting reliable releases.",
        "Completed relevant coursework in systems design, databases, and software development.",
    ])
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("no-headings.pdf", content, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )

    assert response.status_code == 200
    warnings = response.json()["document_metadata"]["extraction_warnings"]
    assert any("no supported resume section headings" in warning.lower() for warning in warnings)


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


def _assert_live_analysis_progress(
    client: TestClient,
    filename: str,
    content: bytes,
    content_type: str,
    job_description: str,
    expected_file_type: str,
) -> None:
    created = client.post("/api/v1/analyze/session")
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    response = client.post(
        "/api/v1/analyze",
        headers={"X-Analysis-Session-Id": session_id},
        files={"resume_file": (filename, content, content_type)},
        data={"job_description": job_description},
    )
    assert response.status_code == 200

    snapshot_response = client.get(
        "/api/v1/analyze/session",
        headers={"X-Analysis-Session-Id": session_id},
    )
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["status"] == "completed"
    assert snapshot["report_available"] is True
    assert [layer["layer_id"] for layer in snapshot["layers"]] == [
        "resume_parsing",
        "section_detection",
        "keyword_matching",
        "experience_impact",
        "ats_recommendations",
    ]
    assert all(
        step["status"] in {"completed", "skipped"}
        and step["progress_percent"] == 100
        for layer in snapshot["layers"]
        for step in layer["steps"]
    )

    events = snapshot["events"]
    event_details = {
        (event["layer_id"], event["step_id"], event["status"]): event["details"]
        for event in events
    }
    assert event_details[("resume_parsing", "validate_file", "completed")]["file_type"] == expected_file_type
    assert event_details[("resume_parsing", "normalize_text", "completed")]["word_count"] > 30
    assert event_details[("resume_parsing", "page_word_count", "completed")]["word_count"] == (
        snapshot["result"]["document_metadata"]["word_count"]
    )
    page_count = event_details.get(
        ("resume_parsing", "extract_text", "completed"),
        {},
    ).get("pages_total")
    if expected_file_type == ".pdf":
        assert page_count and page_count > 0
    else:
        assert "DOCX" in event_details[
            ("resume_parsing", "page_word_count", "in_progress")
        ]["explanation"]
    assert event_details[("section_detection", "experience_section", "completed")]["section_found"]
    assert event_details[("keyword_matching", "skills_extraction", "completed")]["skills_identified"]
    assert event_details[("keyword_matching", "job_keyword_extraction", "completed")]["job_keywords"]
    assert event_details[("keyword_matching", "matched_keywords", "completed")]["matched_keywords"]
    assert isinstance(
        event_details[("keyword_matching", "missing_keywords", "completed")]["missing_keywords"],
        list,
    )
    assert "experience_entries_count" in event_details[
        ("experience_impact", "experience_extraction", "completed")
    ]
    assert "achievement_bullets_count" in event_details[
        ("experience_impact", "achievement_bullets", "completed")
    ]
    assert "action_verbs" in event_details[
        ("experience_impact", "action_verb_analysis", "completed")
    ]
    assert "quantified_achievements_count" in event_details[
        ("experience_impact", "quantified_achievements", "completed")
    ]
    assert "impact_score" in event_details[
        ("experience_impact", "evidence_quality", "completed")
    ]
    assert "overall_score" in event_details[("ats_recommendations", "ats_score", "completed")]
    assert "category_scores" in event_details[
        ("ats_recommendations", "section_scoring", "completed")
    ]
    assert snapshot["result"]["overall_score"] == response.json()["overall_score"]

    stream_response = client.get(
        "/api/v1/analyze/session/events",
        headers={"X-Analysis-Session-Id": session_id},
    )
    assert stream_response.status_code == 200
    assert stream_response.headers["content-type"].startswith("text/event-stream")
    assert "event: progress" in stream_response.text
    assert "data:" in stream_response.text


def test_live_progress_never_contains_resume_prose_or_contact_details(
    client: TestClient,
    sample_fullstack_job: str,
) -> None:
    private_email = "jordan@example.com"
    private_marker = "UNIQUE_RESUME_SENTINEL"
    resume = _create_pdf([
        "Jordan Example",
        f"Email: {private_email}",
        "Summary",
        f"{private_marker} senior software engineer with experience designing cloud data platforms and dependable services.",
        "Experience",
        "Built and maintained secure data systems, automated deployments, and improved service reliability for global teams.",
        "Education",
        "Bachelor of Science in Computer Science from Example University with coursework in databases and software architecture.",
        "Skills",
        "Python SQL cloud architecture automation testing communication systems engineering databases teamwork operations services delivery leadership.",
    ])
    session_id = client.post("/api/v1/analyze/session").json()["session_id"]
    response = client.post(
        "/api/v1/analyze",
        headers={"X-Analysis-Session-Id": session_id},
        files={"resume_file": ("private.pdf", resume, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 200
    snapshot = client.get(
        "/api/v1/analyze/session",
        headers={"X-Analysis-Session-Id": session_id},
    ).json()
    serialized_progress = str(snapshot["events"])
    assert private_email not in serialized_progress
    assert private_marker not in serialized_progress
    assert "Jordan Example" not in serialized_progress


def test_progress_session_remains_queryable_during_document_processing(
    sample_senior_pdf: bytes,
    sample_fullstack_job: str,
    monkeypatch,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app.api.v1.endpoints import analyze as analyze_endpoint
    from app.main import app

    extraction_ready = Event()
    release_extraction = Event()
    original_extract = analyze_endpoint.extract_resume_text

    def pause_after_extraction(filename, content, progress_callback=None):
        result = original_extract(filename, content, progress_callback)
        extraction_ready.set()
        if not release_extraction.wait(timeout=5):
            raise RuntimeError("The live progress test did not release document processing.")
        return result

    monkeypatch.setattr(analyze_endpoint, "extract_resume_text", pause_after_extraction)

    with TestClient(app) as live_client:
        session_id = live_client.post("/api/v1/analyze/session").json()["session_id"]
        request = {
            "headers": {"X-Analysis-Session-Id": session_id},
            "files": {"resume_file": ("resume.pdf", sample_senior_pdf, "application/pdf")},
            "data": {"job_description": sample_fullstack_job},
        }
        with ThreadPoolExecutor(max_workers=2) as executor:
            analysis_future = executor.submit(live_client.post, "/api/v1/analyze", **request)
            try:
                assert extraction_ready.wait(timeout=5)
                snapshot_future = executor.submit(
                    live_client.get,
                    "/api/v1/analyze/session",
                    headers={"X-Analysis-Session-Id": session_id},
                )
                snapshot_response = snapshot_future.result(timeout=3)
                assert snapshot_response.status_code == 200
                snapshot = snapshot_response.json()
                assert snapshot["status"] == "running"
                assert next(
                    step["status"]
                    for layer in snapshot["layers"]
                    if layer["layer_id"] == "resume_parsing"
                    for step in layer["steps"]
                    if step["step_id"] == "extract_text"
                ) == "completed"
                assert all(
                    layer["status"] == "pending"
                    for layer in snapshot["layers"]
                    if layer["layer_id"] != "resume_parsing"
                )
            finally:
                release_extraction.set()
            assert analysis_future.result(timeout=15).status_code == 200


def test_progress_session_marks_pipeline_validation_failures(
    client: TestClient,
    sample_fullstack_job: str,
) -> None:
    session_id = client.post("/api/v1/analyze/session").json()["session_id"]
    response = client.post(
        "/api/v1/analyze",
        headers={"X-Analysis-Session-Id": session_id},
        files={"resume_file": ("resume.txt", b"unsupported file content", "text/plain")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 400

    snapshot = client.get(
        "/api/v1/analyze/session",
        headers={"X-Analysis-Session-Id": session_id},
    ).json()
    assert snapshot["status"] == "failed"
    assert snapshot["error_code"] == "INVALID_FILE_TYPE"
    validation_step = next(
        step
        for layer in snapshot["layers"]
        if layer["layer_id"] == "resume_parsing"
        for step in layer["steps"]
        if step["step_id"] == "validate_file"
    )
    assert validation_step["status"] == "failed"


def test_live_progress_tracks_real_pdf_pipeline(
    client: TestClient,
    sample_senior_pdf: bytes,
    sample_fullstack_job: str,
) -> None:
    _assert_live_analysis_progress(
        client,
        "senior_software_engineer.pdf",
        sample_senior_pdf,
        "application/pdf",
        sample_fullstack_job,
        ".pdf",
    )


def test_live_progress_tracks_real_docx_pipeline(
    client: TestClient,
    sample_senior_docx: bytes,
    sample_fullstack_job: str,
) -> None:
    _assert_live_analysis_progress(
        client,
        "senior_software_engineer.docx",
        sample_senior_docx,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        sample_fullstack_job,
        ".docx",
    )
