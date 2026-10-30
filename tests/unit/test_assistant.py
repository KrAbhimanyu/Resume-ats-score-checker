from app.services.assistant import (
    analyze_bullet_point,
    improve_single_bullet,
    generate_improvement_assistant,
    extract_candidate_bullets,
)
from app.models.schemas import RequirementMatch, MissingRequirement


def test_clear_vs_vague_bullet_points():
    # Vague bullet starting with passive "worked on"
    vague_bullet = "Worked on API testing."
    is_weak, issues, rewrite, what_to_add, verb, det_skills = analyze_bullet_point(vague_bullet)

    assert is_weak is True
    assert any("worked on" in iss.lower() for iss in issues)
    assert any("quantifiable" in iss.lower() for iss in issues)
    assert "[add verified result" in rewrite
    assert "tested" in rewrite.lower() or "validated" in rewrite.lower() or "engineered" in rewrite.lower()

    # Clear, well-evidenced bullet with strong verb and metric
    clear_bullet = "Architected and deployed microservices backend using Python, FastAPI, and PostgreSQL serving 100k daily users."
    is_weak_c, issues_c, rewrite_c, what_to_add_c, verb_c, det_skills_c = analyze_bullet_point(clear_bullet)

    # Has metrics (100k) and technical skills (Python, FastAPI, PostgreSQL)
    assert "python" in [s.lower() for s in det_skills_c]
    assert "fastapi" in [s.lower() for s in det_skills_c]
    assert "postgresql" in [s.lower() for s in det_skills_c]
    assert verb_c == "Architected"


def test_assisted_with_passive_bullet():
    bullet = "Assisted with customer support tickets and bug reporting."
    is_weak, issues, rewrite, what_to_add, verb, _ = analyze_bullet_point(bullet)

    assert is_weak is True
    assert any("assisted with" in iss.lower() or "supportive" in iss.lower() for iss in issues)
    assert "[add verified result" in rewrite
    assert "Add the specific technology" in what_to_add or "quantify" in what_to_add.lower()


def test_responsible_for_bullet():
    bullet = "Responsible for managing Docker containers and deployment scripts."
    is_weak, issues, rewrite, what_to_add, verb, det_skills = analyze_bullet_point(bullet)

    assert is_weak is True
    assert any("responsible for" in iss.lower() for iss in issues)
    assert "docker" in [s.lower() for s in det_skills]
    # Rewrite should keep docker and add measurable result
    assert "docker" in rewrite.lower()
    assert "[add verified result" in rewrite


def test_measurable_achievement_placeholder_never_invents_fake_numbers():
    bullet = "Built REST endpoints with FastAPI."
    resp = improve_single_bullet(bullet)

    assert resp.is_weak is True
    # Must use placeholder and NOT invent a fake percentage like "27%" or fake number
    assert "[add verified result" in resp.suggested_rewrite
    assert not any(fake in resp.suggested_rewrite for fake in ["45%", "$10,000", "200k users", "50%"])
    assert "verify" in resp.what_to_add.lower() or "truthfully" in resp.what_to_add.lower()


def test_empty_and_malformed_bullet():
    empty_resp = improve_single_bullet("")
    assert empty_resp.is_weak is True
    assert "empty" in empty_resp.issues[0].lower()

    whitespace_resp = improve_single_bullet("   \n\t  ")
    assert whitespace_resp.is_weak is True
    assert "empty" in whitespace_resp.issues[0].lower()


def test_job_description_alignment_and_ethical_guidance():
    parsed_job = {
        "job_skills": ["python", "fastapi", "react", "kubernetes", "aws"],
        "job_keywords": {"python", "fastapi", "react", "kubernetes", "aws", "docker"},
    }
    parsed_resume = {
        "sections": {
            "skills": "python, fastapi, react",
            "experience": "Engineered microservices using Python and FastAPI serving 50k users.",
            "education": "Bachelor of Science in Computer Science",
        },
        "action_verbs": ["engineered"],
        "metrics_found": ["50k users"],
        "degrees_found": ["bachelor"],
        "skills_found": ["python", "fastapi", "react"],
        "word_count": 150,
        "bullet_count": 2,
    }
    norm_resume = "engineered microservices using python and fastapi serving 50k users."
    norm_job = "looking for engineer with python, fastapi, react, kubernetes, aws experience."

    matched_reqs = [
        RequirementMatch(
            requirement="python",
            category="skill",
            matched_terms=["python"],
            evidence_strength="strong",
            is_mandatory=True,
        )
    ]
    missing_reqs = [
        MissingRequirement(
            requirement="kubernetes",
            category="skill",
            importance="mandatory",
            reason="Skill kubernetes not found in resume.",
            is_evidenced_elsewhere=False,
        )
    ]

    assistant = generate_improvement_assistant(
        parsed_job=parsed_job,
        parsed_resume=parsed_resume,
        norm_resume_text=norm_resume,
        norm_job_text=norm_job,
        matched_reqs=matched_reqs,
        missing_reqs=missing_reqs,
    )

    # 1. Strengths
    assert len(assistant.strengths) >= 2
    strength_categories = [s.category for s in assistant.strengths]
    assert "skills" in strength_categories or "metrics" in strength_categories

    # 2. Skill alignment
    alignment = assistant.skill_alignment
    assert "python" in alignment.matched_skills
    assert "fastapi" in alignment.matched_skills
    assert "react" in alignment.matched_skills
    assert "kubernetes" in alignment.missing_from_resume_skills
    assert "aws" in alignment.missing_from_resume_skills
    # React is in skills section but not in experience text:
    assert "react" in alignment.weakly_evidenced_skills
    # Ethical guidance
    assert "truthfully possess" in alignment.ethical_guidance
    assert "misrepresenting qualifications" in alignment.ethical_guidance

    # 3. Action verbs
    assert len(assistant.recommended_verbs) == 4

    # 4. Metric guidance
    assert len(assistant.metric_guidance) == 5
    for item in assistant.metric_guidance:
        assert "[add verified" in item.example_pattern

    # 5. Checklist
    assert len(assistant.improvement_checklist) >= 3
    priorities = [c.priority for c in assistant.improvement_checklist]
    assert "high" in priorities

