from typing import Dict, List, Any, Tuple
from app.config import settings
from app.models.schemas import CategoryScore, RequirementMatch, MissingRequirement
from app.services.synonyms import find_term_in_text


def calculate_ats_score(
    parsed_job: Dict[str, Any],
    parsed_resume: Dict[str, Any],
    norm_resume_text: str,
    norm_job_text: str,
) -> Tuple[float, str, str, List[CategoryScore], List[RequirementMatch], List[MissingRequirement], List[str]]:
    """
    Deterministic, explainable scoring engine calculating match score from 0 to 100.

    Category allocations:
    1. Job-relevant keyword coverage: 35 points
    2. Required and preferred skills match: 25 points
    3. Relevant experience evidence: 20 points
    4. Education and qualifications: 10 points
    5. Document structure and readability: 10 points
    """
    matched_reqs: List[RequirementMatch] = []
    missing_reqs: List[MissingRequirement] = []
    keywords_found_set: set = set()

    # =========================================================================
    # 1. Job-Relevant Keyword Coverage (Max 35 points)
    # =========================================================================
    job_keywords: List[str] = sorted(list(parsed_job.get("job_keywords", set())))
    matched_kw_count = 0

    if job_keywords:
        for kw in job_keywords:
            matched, matched_term = find_term_in_text(kw, norm_resume_text)
            if matched:
                matched_kw_count += 1
                keywords_found_set.add(matched_term or kw)

        # Keyword coverage ratio - avoids repeating credit
        kw_ratio = matched_kw_count / len(job_keywords)
        kw_score = round(kw_ratio * settings.WEIGHT_KEYWORD_COVERAGE, 2)
    else:
        # Fallback if job description has minimal distinct keywords
        kw_score = settings.WEIGHT_KEYWORD_COVERAGE
        kw_ratio = 1.0

    kw_percentage = round((kw_score / settings.WEIGHT_KEYWORD_COVERAGE) * 100, 1)
    kw_category = CategoryScore(
        category_id="keyword_coverage",
        category_name="Job-Relevant Keyword Coverage",
        score=min(settings.WEIGHT_KEYWORD_COVERAGE, max(0.0, kw_score)),
        max_score=settings.WEIGHT_KEYWORD_COVERAGE,
        percentage=kw_percentage,
        explanation=(
            f"Matched {matched_kw_count} out of {len(job_keywords)} key terms from the job description "
            f"({kw_percentage}% coverage). Repeated occurrences in the resume do not artificially inflate the score."
        ),
        details={
            "total_job_keywords": len(job_keywords),
            "matched_keywords_count": matched_kw_count,
            "keyword_match_rate": kw_percentage,
        },
    )

    # =========================================================================
    # 2. Required and Preferred Skills Match (Max 25 points)
    # =========================================================================
    mandatory_reqs: List[str] = parsed_job.get("mandatory_requirements", [])
    preferred_reqs: List[str] = parsed_job.get("preferred_requirements", [])
    job_skills: List[str] = parsed_job.get("job_skills", [])

    # Evaluate individual job skills first
    matched_skills = []
    missing_skills = []

    for skill in job_skills:
        matched, matched_term = find_term_in_text(skill, norm_resume_text)
        if matched:
            matched_skills.append(skill)
            keywords_found_set.add(matched_term or skill)
            matched_reqs.append(
                RequirementMatch(
                    requirement=skill,
                    category="skill",
                    matched_terms=[matched_term or skill],
                    evidence_strength="strong" if skill in parsed_resume.get("sections", {}).get("skills", "") or skill in parsed_resume.get("sections", {}).get("experience", "") else "moderate",
                    is_mandatory=True,
                )
            )
        else:
            missing_skills.append(skill)
            missing_reqs.append(
                MissingRequirement(
                    requirement=skill,
                    category="skill",
                    importance="mandatory",
                    reason=f"Skill '{skill}' or recognized synonyms not found in resume.",
                    is_evidenced_elsewhere=False,
                )
            )

    # Also evaluate bullet requirements if extracted
    mandatory_bullet_matches = 0
    for req in mandatory_reqs:
        matched, matched_term = find_term_in_text(req, norm_resume_text)
        if not matched:
            # Check individual tokens
            req_words = [w for w in req.lower().split() if len(w) > 3 and w not in ["with", "have", "must", "experience"]]
            sub_matches = [w for w in req_words if find_term_in_text(w, norm_resume_text)[0]]
            if len(sub_matches) >= max(1, len(req_words) // 2):
                mandatory_bullet_matches += 1
                matched_reqs.append(
                    RequirementMatch(
                        requirement=req,
                        category="experience",
                        matched_terms=sub_matches,
                        evidence_strength="moderate",
                        is_mandatory=True,
                    )
                )
            else:
                missing_reqs.append(
                    MissingRequirement(
                        requirement=req,
                        category="experience",
                        importance="mandatory",
                        reason="Mandatory job requirement does not appear clearly in resume text.",
                        is_evidenced_elsewhere=len(sub_matches) > 0,
                    )
                )
        else:
            mandatory_bullet_matches += 1

    # Calculate skill score
    total_evaluable_skills = len(job_skills)
    if total_evaluable_skills > 0:
        skill_ratio = len(matched_skills) / total_evaluable_skills
    elif mandatory_reqs:
        skill_ratio = mandatory_bullet_matches / max(1, len(mandatory_reqs))
    else:
        skill_ratio = kw_ratio

    # Preferred requirements bonus / allocation
    pref_score_ratio = 1.0
    if preferred_reqs:
        pref_matches = 0
        for pref in preferred_reqs:
            matched, _ = find_term_in_text(pref, norm_resume_text)
            if matched:
                pref_matches += 1
        pref_score_ratio = pref_matches / len(preferred_reqs)
        skills_points = (skill_ratio * 18.0) + (pref_score_ratio * 7.0)
    else:
        skills_points = skill_ratio * settings.WEIGHT_SKILLS_MATCH

    skills_score = round(min(settings.WEIGHT_SKILLS_MATCH, max(0.0, skills_points)), 2)
    skills_percentage = round((skills_score / settings.WEIGHT_SKILLS_MATCH) * 100, 1)

    skills_category = CategoryScore(
        category_id="skills_match",
        category_name="Required and Preferred Skills Match",
        score=skills_score,
        max_score=settings.WEIGHT_SKILLS_MATCH,
        percentage=skills_percentage,
        explanation=(
            f"Matched {len(matched_skills)} of {len(job_skills)} target core skills. "
            f"{'Preferred skills were also evaluated.' if preferred_reqs else 'Evaluated against primary core qualifications.'}"
        ),
        details={
            "target_skills_count": len(job_skills),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "mandatory_requirements_evaluated": len(mandatory_reqs),
        },
    )

    # =========================================================================
    # 3. Relevant Experience Evidence (Max 20 points)
    # =========================================================================
    exp_points = 0.0
    exp_details = {}

    # Section presence (5 pts)
    has_exp = parsed_resume.get("has_experience_section", False)
    if has_exp:
        exp_points += 5.0
        exp_details["experience_section_present"] = True
    else:
        exp_details["experience_section_present"] = False

    # Action verbs diversity (5 pts)
    verbs = parsed_resume.get("action_verbs", [])
    if len(verbs) >= 5:
        exp_points += 5.0
    elif len(verbs) >= 3:
        exp_points += 3.5
    elif len(verbs) >= 1:
        exp_points += 2.0
    exp_details["action_verbs_count"] = len(verbs)

    # Quantified impact / metrics (5 pts)
    metrics = parsed_resume.get("metrics_found", [])
    if len(metrics) >= 3:
        exp_points += 5.0
    elif len(metrics) >= 1:
        exp_points += 3.0
    exp_details["quantified_metrics_count"] = len(metrics)

    # Experience duration alignment (5 pts)
    req_years = parsed_job.get("required_years")
    if req_years:
        exp_details["required_years"] = req_years
        # Check if resume mentions matching years
        matched_exp_years = False
        for exp_tuple in parsed_resume.get("experience_indicators", []):
            if any(num.isdigit() and int(num) >= req_years for num in exp_tuple if num):
                matched_exp_years = True
                break
        if matched_exp_years:
            exp_points += 5.0
            exp_details["duration_match"] = "full"
        else:
            exp_points += 2.5
            exp_details["duration_match"] = "unconfirmed_or_partial"
    else:
        # Default full points if job does not mandate specific years but timeline indicators exist
        if parsed_resume.get("experience_indicators"):
            exp_points += 5.0
            exp_details["duration_match"] = "timeline_present"
        else:
            exp_points += 3.5
            exp_details["duration_match"] = "not_specified"

    exp_score = round(min(settings.WEIGHT_EXPERIENCE_EVIDENCE, max(0.0, exp_points)), 2)
    exp_percentage = round((exp_score / settings.WEIGHT_EXPERIENCE_EVIDENCE) * 100, 1)

    exp_category = CategoryScore(
        category_id="experience_evidence",
        category_name="Relevant Experience Evidence",
        score=exp_score,
        max_score=settings.WEIGHT_EXPERIENCE_EVIDENCE,
        percentage=exp_percentage,
        explanation=(
            f"Experience section: {'Found' if has_exp else 'Missing/Unlabeled'}. "
            f"Action verbs identified: {len(verbs)}. "
            f"Quantified achievements / metrics: {len(metrics)}."
        ),
        details=exp_details,
    )

    # =========================================================================
    # 4. Education and Qualifications (Max 10 points)
    # =========================================================================
    edu_points = 0.0
    has_edu_sec = parsed_resume.get("has_education_section", False)
    if has_edu_sec:
        edu_points += 4.0

    res_degrees = parsed_resume.get("degrees_found", [])
    job_degrees = parsed_job.get("required_degrees", [])

    if job_degrees:
        # Check degree alignment
        matched_degrees = [deg for deg in job_degrees if deg in res_degrees]
        if matched_degrees:
            edu_points += 6.0
        elif res_degrees:
            edu_points += 4.0
        else:
            edu_points += 1.0
    else:
        # If job has no explicit degree requirement, having a degree listed earns full points
        if res_degrees:
            edu_points += 6.0
        elif has_edu_sec:
            edu_points += 4.0
        else:
            edu_points += 2.0

    edu_score = round(min(settings.WEIGHT_EDUCATION_MATCH, max(0.0, edu_points)), 2)
    edu_percentage = round((edu_score / settings.WEIGHT_EDUCATION_MATCH) * 100, 1)

    edu_category = CategoryScore(
        category_id="education_qualifications",
        category_name="Education and Qualifications",
        score=edu_score,
        max_score=settings.WEIGHT_EDUCATION_MATCH,
        percentage=edu_percentage,
        explanation=(
            f"Education section: {'Present' if has_edu_sec else 'Missing/Unlabeled'}. "
            f"Detected degrees: {', '.join(res_degrees) if res_degrees else 'None explicitly listed'}."
        ),
        details={
            "education_section_present": has_edu_sec,
            "degrees_found": res_degrees,
            "required_degrees": job_degrees,
        },
    )

    # =========================================================================
    # 5. Document Structure and Readability (Max 10 points)
    # =========================================================================
    struct_points = 0.0
    sections = parsed_resume.get("sections", {})

    # Section organization (4 pts)
    recognized_secs = [s for s in ["experience", "education", "skills", "projects", "summary"] if s in sections]
    if len(recognized_secs) >= 3:
        struct_points += 4.0
    elif len(recognized_secs) >= 2:
        struct_points += 2.5
    elif len(recognized_secs) >= 1:
        struct_points += 1.5

    # Word count / content depth (3 pts)
    wc = parsed_resume.get("word_count", 0)
    if 250 <= wc <= 1500:
        struct_points += 3.0
    elif 150 <= wc < 250 or 1500 < wc <= 2500:
        struct_points += 2.0
    else:
        struct_points += 1.0

    # Bullet / structured items (3 pts)
    bullets = parsed_resume.get("bullet_count", 0)
    if bullets >= 5:
        struct_points += 3.0
    elif bullets >= 2:
        struct_points += 2.0
    else:
        struct_points += 1.0

    struct_score = round(min(settings.WEIGHT_STRUCTURE_READABILITY, max(0.0, struct_points)), 2)
    struct_percentage = round((struct_score / settings.WEIGHT_STRUCTURE_READABILITY) * 100, 1)

    struct_category = CategoryScore(
        category_id="document_structure",
        category_name="Document Structure and Readability",
        score=struct_score,
        max_score=settings.WEIGHT_STRUCTURE_READABILITY,
        percentage=struct_percentage,
        explanation=(
            f"Identified {len(recognized_secs)} standard resume sections ({', '.join(recognized_secs)}). "
            f"Word count is {wc} words with {bullets} bulleted entries."
        ),
        details={
            "recognized_sections": recognized_secs,
            "word_count": wc,
            "bullet_count": bullets,
        },
    )

    # =========================================================================
    # Calculate Overall Score
    # =========================================================================
    category_scores = [kw_category, skills_category, exp_category, edu_category, struct_category]
    total_raw_score = sum(c.score for c in category_scores)
    overall_score = round(min(100.0, max(0.0, total_raw_score)), 1)

    # Determine descriptive match tier
    if overall_score >= 85.0:
        match_tier = "Exceptional Match"
    elif overall_score >= 70.0:
        match_tier = "Strong Match"
    elif overall_score >= 55.0:
        match_tier = "Good Match"
    elif overall_score >= 40.0:
        match_tier = "Fair Match"
    else:
        match_tier = "Low Match"

    summary = (
        f"Your resume achieved an Estimated Resume–Job Match Score of {overall_score}/100 ({match_tier}). "
        f"Keyword coverage scored {kw_score}/{settings.WEIGHT_KEYWORD_COVERAGE}, and core skills matched "
        f"{skills_score}/{settings.WEIGHT_SKILLS_MATCH}."
    )

    sorted_keywords_found = sorted(list(keywords_found_set))
    return overall_score, match_tier, summary, category_scores, matched_reqs, missing_reqs, sorted_keywords_found
