from app.services.parser import extract_job_requirements, parse_resume_content
from app.services.scoring import calculate_ats_score
from app.services.synonyms import normalize_text


def test_score_bounds_and_determinism():
    job_text = """
    Software Engineer
    Required:
    - 3+ years experience with Python and FastAPI
    - Bachelor's degree in Computer Science
    - Experience with Docker and PostgreSQL
    """
    resume_text = """
    Jane Doe
    Summary: Software Engineer with 4 years experience.
    Skills: Python, FastAPI, Docker, PostgreSQL
    Experience:
    Software Engineer at Acme (2020 - Present)
    - Developed backend services using Python and FastAPI.
    - Optimized database queries for PostgreSQL.
    Education:
    Bachelor of Science in Computer Science
    """
    norm_job = normalize_text(job_text)
    norm_resume = normalize_text(resume_text)

    parsed_job = extract_job_requirements(norm_job)
    parsed_resume = parse_resume_content(norm_resume)

    score1, tier1, _, cat1, _, _, _ = calculate_ats_score(parsed_job, parsed_resume, norm_resume, norm_job)
    score2, tier2, _, cat2, _, _, _ = calculate_ats_score(parsed_job, parsed_resume, norm_resume, norm_job)

    # 1. Determinism
    assert score1 == score2
    assert tier1 == tier2
    assert [c.score for c in cat1] == [c.score for c in cat2]

    # 2. Score bounds
    assert 0.0 <= score1 <= 100.0
    for cat in cat1:
        assert 0.0 <= cat.score <= cat.max_score


def test_repeated_keywords_do_not_inflate_score():
    job_text = "Looking for a Python developer with SQL experience."
    resume_normal = "Experience:\n- Built software with Python and SQL."
    resume_stuffed = "Experience:\n- Python Python Python Python Python SQL SQL SQL SQL SQL."

    norm_job = normalize_text(job_text)
    norm_normal = normalize_text(resume_normal)
    norm_stuffed = normalize_text(resume_stuffed)

    parsed_job = extract_job_requirements(norm_job)
    parsed_normal = parse_resume_content(norm_normal)
    parsed_stuffed = parse_resume_content(norm_stuffed)

    _, _, _, cats_normal, _, _, _ = calculate_ats_score(parsed_job, parsed_normal, norm_normal, norm_job)
    _, _, _, cats_stuffed, _, _, _ = calculate_ats_score(parsed_job, parsed_stuffed, norm_stuffed, norm_job)

    kw_normal = next(c for c in cats_normal if c.category_id == "keyword_coverage")
    kw_stuffed = next(c for c in cats_stuffed if c.category_id == "keyword_coverage")

    # The keyword coverage score must be identical because repeated keywords don't get double points
    assert kw_normal.score == kw_stuffed.score


def test_missing_keywords_lower_score():
    job_text = """
    Required Qualifications:
    - Proficient in Python, Kubernetes, Redis, GraphQL, and Terraform
    - Bachelor's degree in Computer Science
    """
    resume_with_all = """
    Skills: Python, Kubernetes, Redis, GraphQL, Terraform
    Experience: Built cloud systems using Kubernetes and Terraform.
    Education: Bachelor of Science in Computer Science
    """
    resume_with_few = """
    Skills: Python
    Experience: Built small scripts with Python.
    Education: Bachelor of Science in Computer Science
    """

    norm_job = normalize_text(job_text)
    norm_all = normalize_text(resume_with_all)
    norm_few = normalize_text(resume_with_few)

    pj = extract_job_requirements(norm_job)
    p_all = parse_resume_content(norm_all)
    p_few = parse_resume_content(norm_few)

    score_all, _, _, _, _, _, _ = calculate_ats_score(pj, p_all, norm_all, norm_job)
    score_few, _, _, _, _, missing_few, _ = calculate_ats_score(pj, p_few, norm_few, norm_job)

    assert score_all > score_few
    missing_skill_names = [m.requirement for m in missing_few]
    assert "kubernetes" in missing_skill_names or "terraform" in missing_skill_names


def test_experience_evidence_scoring():
    job_text = "Senior Engineer needed with 5+ years experience."
    resume_no_metrics = """
    Work Experience:
    - Helped build web features for clients.
    """
    resume_rich_metrics = """
    Work Experience:
    Senior Engineer (2018 - Present) - 6 years of experience
    - Architected microservices reducing latency by 40% across 500k active users.
    - Automated CI/CD pipelines saving $120k annually.
    - Spearheaded team of 8 engineers delivering 15 projects.
    """

    norm_job = normalize_text(job_text)
    norm_low = normalize_text(resume_no_metrics)
    norm_high = normalize_text(resume_rich_metrics)

    pj = extract_job_requirements(norm_job)
    p_low = parse_resume_content(norm_low)
    p_high = parse_resume_content(norm_high)

    _, _, _, cats_low, _, _, _ = calculate_ats_score(pj, p_low, norm_low, norm_job)
    _, _, _, cats_high, _, _, _ = calculate_ats_score(pj, p_high, norm_high, norm_job)

    exp_low = next(c for c in cats_low if c.category_id == "experience_evidence")
    exp_high = next(c for c in cats_high if c.category_id == "experience_evidence")

    assert exp_high.score > exp_low.score
