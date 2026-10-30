from fastapi.testclient import TestClient


def test_analyze_endpoint_returns_improvement_assistant(client: TestClient, sample_senior_pdf, sample_fullstack_job):
    response = client.post(
        "/api/v1/analyze",
        files={"resume_file": ("senior_software_engineer.pdf", sample_senior_pdf, "application/pdf")},
        data={"job_description": sample_fullstack_job},
    )
    assert response.status_code == 200
    data = response.json()

    # Core response assertions preserved
    assert "overall_score" in data
    assert "improvement_assistant" in data
    assistant = data["improvement_assistant"]
    assert assistant is not None

    # Check strengths
    assert len(assistant["strengths"]) > 0
    strength_titles = [s["title"] for s in assistant["strengths"]]
    assert any("Action Verb" in t or "Structure" in t or "Technical" in t for t in strength_titles)

    # Check bullet improvements
    assert len(assistant["bullet_improvements"]) > 0
    for bi in assistant["bullet_improvements"]:
        assert "original_text" in bi
        assert "suggested_rewrite" in bi
        assert "issue" in bi
        assert "what_to_add" in bi
        assert "[add verified result" in bi["suggested_rewrite"] or "." in bi["suggested_rewrite"]

    # Check skill alignment
    alignment = assistant["skill_alignment"]
    assert len(alignment["matched_skills"]) > 0
    assert "truthfully possess" in alignment["ethical_guidance"]

    # Check action verbs
    assert len(assistant["recommended_verbs"]) >= 3

    # Check metric guidance
    assert len(assistant["metric_guidance"]) >= 3
    for mg in assistant["metric_guidance"]:
        assert "[add verified" in mg["example_pattern"]

    # Check checklist
    assert len(assistant["improvement_checklist"]) >= 3
    priorities = [chk["priority"] for chk in assistant["improvement_checklist"]]
    assert "high" in priorities


def test_improve_bullet_endpoint_valid_vague(client: TestClient):
    payload = {
        "bullet_text": "Worked on API testing.",
        "target_skills": ["Postman", "FastAPI", "Python"],
    }
    response = client.post("/api/v1/improve-bullet", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_weak"] is True
    assert len(data["issues"]) > 0
    assert any("worked on" in iss.lower() for iss in data["issues"])
    assert "[add verified result" in data["suggested_rewrite"]
    assert len(data["recommended_action_verbs"]) > 0


def test_improve_bullet_endpoint_empty_rejected(client: TestClient):
    payload = {"bullet_text": ""}
    response = client.post("/api/v1/improve-bullet", json=payload)
    # Pydantic validates min_length=3 -> 422
    assert response.status_code == 422


def test_improve_bullet_endpoint_whitespace_rejected(client: TestClient):
    payload = {"bullet_text": "   "}
    response = client.post("/api/v1/improve-bullet", json=payload)
    assert response.status_code in [400, 422]

