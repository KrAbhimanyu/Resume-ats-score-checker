import hashlib
import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from app.config import settings
from app.services.parser import extract_job_requirements, parse_resume_content
from app.services.synonyms import find_term_in_text, normalize_text


_WEIGHTS = {
    "technical_skills": "JOB_MATCH_WEIGHT_SKILLS",
    "experience_relevance": "JOB_MATCH_WEIGHT_EXPERIENCE",
    "responsibility_alignment": "JOB_MATCH_WEIGHT_RESPONSIBILITIES",
    "education": "JOB_MATCH_WEIGHT_EDUCATION",
    "certifications": "JOB_MATCH_WEIGHT_CERTIFICATIONS",
    "keyword_coverage": "JOB_MATCH_WEIGHT_KEYWORDS",
    "location": "JOB_MATCH_WEIGHT_LOCATION",
}


def _weight(name: str) -> float:
    return max(0.0, float(getattr(settings, _WEIGHTS[name])))


def clean_job_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style)\b.*?</\1\s*>", " ", value or "")
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        key = clean.casefold()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def analyze_job_description(
    description: str,
    *,
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    location: Optional[str] = None,
    source: str = "user_provided",
) -> Dict[str, Any]:
    clean = clean_job_text(description)
    parsed = extract_job_requirements(normalize_text(clean))
    lines = [line.strip(" \t-*•") for line in clean.splitlines() if line.strip()]
    inferred_title = title.strip() if title and title.strip() else None
    inferred_company = company_name.strip() if company_name and company_name.strip() else None
    if not inferred_title and lines and len(lines[0]) <= 120:
        inferred_title = lines[0]
    required_skills = list(parsed["job_skills"])
    preferred_lines = list(parsed["preferred_requirements"])
    preferred_skills = [
        skill
        for skill in required_skills
        if any(find_term_in_text(skill, line)[0] for line in preferred_lines)
    ]
    required_skills = [skill for skill in required_skills if skill not in preferred_skills]
    responsibilities = [
        line
        for line in lines
        if re.match(r"^(?:[-*•]|\d+[.)])\s*", line)
        or re.search(r"\b(responsibilit|you will|you'll|what you will do|role includes)\b", line, re.I)
    ][:30]
    qualifications = _unique(parsed["mandatory_requirements"] + parsed["preferred_requirements"])[:30]
    salary = extract_salary_range(clean)

    return {
        "analysis_method": "deterministic_rules",
        "facts": {
            "title": {"value": inferred_title, "source": "user_input" if title else "description_heading"},
            "company": {"value": inferred_company, "source": "user_input" if company_name else None},
            "location": {"value": location, "source": "user_input" if location else None},
            "salary": salary,
            "required_experience_years": parsed["required_years"],
        },
        "requirements": {
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "education_levels": parsed["required_degrees"],
            "keywords": sorted(parsed["job_keywords"])[:80],
        },
        "interpretations": {
            "source": source,
            "note": "Skill and section extraction is a deterministic text heuristic; verify requirements against the original posting.",
            "confidence": "heuristic",
        },
    }


def extract_salary_range(text: str) -> Optional[Dict[str, Any]]:
    patterns = [
        (r"(?i)(?:₹|INR\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*(?:₹|INR\s*)?([\d,]+(?:\.\d+)?)\s*(lpa|lakhs?|per\s+annum|yearly|annual)?", "INR"),
        (r"(?i)(?:\$\s*|USD\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*(?:\$\s*|USD\s*)?([\d,]+(?:\.\d+)?)\s*(k|per\s+year|yearly|annual)?", "USD"),
        (r"(?i)(?:£\s*|GBP\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*(?:£\s*|GBP\s*)?([\d,]+(?:\.\d+)?)\s*(k|per\s+year|yearly|annual)?", "GBP"),
        (r"(?i)(?:€\s*|EUR\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*(?:€\s*|EUR\s*)?([\d,]+(?:\.\d+)?)\s*(k|per\s+year|yearly|annual)?", "EUR"),
    ]
    for pattern, currency in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        minimum, maximum = (float(part.replace(",", "")) for part in match.group(1, 2))
        unit = (match.group(3) or "").lower()
        multiplier = 100_000 if currency == "INR" and unit.startswith(("lakh", "lpa")) else 1_000 if unit == "k" else 1
        return {
            "minimum": minimum * multiplier,
            "maximum": maximum * multiplier,
            "currency": currency,
            "period": "year" if unit in {"lpa", "lakh", "lakhs", "per annum", "yearly", "annual", "k"} else "unspecified",
            "source": "job_description",
            "verified_employer_provided": False,
        }
    return None


def _evidence_excerpt(text: str, term: str) -> Optional[str]:
    for line in text.splitlines():
        if find_term_in_text(term, line)[0]:
            return line.strip()[:260]
    return None


def _years_evidence(resume: Dict[str, Any]) -> Optional[int]:
    values: list[int] = []
    for match in resume.get("experience_indicators", []):
        explicit, start, end = match
        if explicit and explicit.isdigit():
            values.append(int(explicit))
        elif start and start.isdigit():
            end_year = int(end) if end and end.isdigit() else datetime.now(timezone.utc).year
            values.append(max(0, end_year - int(start)))
    return max(values) if values else None


def match_resume_to_job(
    resume_text: str,
    job_description: str,
    *,
    job_title: Optional[str] = None,
    job_location: Optional[str] = None,
    preferred_locations: Optional[list[str]] = None,
    work_modes: Optional[list[str]] = None,
) -> Dict[str, Any]:
    resume_text = normalize_text(resume_text)
    job_text = normalize_text(clean_job_text(job_description))
    parsed_resume = parse_resume_content(resume_text)
    parsed_job = extract_job_requirements(job_text)
    required_skills = list(parsed_job["job_skills"])
    preferred_lines = parsed_job["preferred_requirements"]
    preferred_skills = [
        skill for skill in required_skills
        if any(find_term_in_text(skill, line)[0] for line in preferred_lines)
    ]
    required_skills = [skill for skill in required_skills if skill not in preferred_skills]

    matched: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    missing_required: list[str] = []
    missing_preferred: list[str] = []
    matched_required = 0
    for skill in required_skills:
        evidence = _evidence_excerpt(resume_text, skill)
        if evidence:
            matched_required += 1
            if find_term_in_text(skill, parsed_resume.get("sections", {}).get("experience", ""))[0]:
                matched.append({"skill": skill, "evidence": evidence, "evidence_source": "resume"})
            else:
                partial.append({"skill": skill, "evidence": evidence, "evidence_source": "resume"})
        else:
            missing_required.append(skill)
    for skill in preferred_skills:
        evidence = _evidence_excerpt(resume_text, skill)
        if evidence:
            matched.append({"skill": skill, "evidence": evidence, "evidence_source": "resume", "preference": "preferred"})
        else:
            missing_preferred.append(skill)

    skill_score = 100 * matched_required / len(required_skills) if required_skills else None
    experience_section = parsed_resume.get("sections", {}).get("experience", "")
    experience_skill_count = sum(find_term_in_text(skill, experience_section)[0] for skill in required_skills)
    experience_score = (
        100 * experience_skill_count / len(required_skills) if required_skills else None
    )
    responsibility_requirements = parsed_job["mandatory_requirements"][:20]
    responsibility_hits = [
        requirement for requirement in responsibility_requirements
        if find_term_in_text(requirement, experience_section)[0]
        or sum(
            find_term_in_text(token, experience_section)[0]
            for token in requirement.split()
            if len(token) > 4
        ) >= max(1, len([token for token in requirement.split() if len(token) > 4]) // 2)
    ]
    responsibility_score = (
        100 * len(responsibility_hits) / len(responsibility_requirements)
        if responsibility_requirements else None
    )
    education_levels = parsed_job["required_degrees"]
    education_score = (
        100 if set(education_levels).intersection(parsed_resume["degrees_found"]) else 0
    ) if education_levels else None
    certification_requested = bool(re.search(r"\b(certification|certified|license|licensed)\b", job_text))
    certification_section = parsed_resume.get("sections", {}).get("certifications", "")
    certification_score = (
        100 if certification_section and find_term_in_text("certification", certification_section)[0] else 0
    ) if certification_requested else None

    keywords = sorted(parsed_job["job_keywords"])
    keyword_matches = [keyword for keyword in keywords if find_term_in_text(keyword, resume_text)[0]]
    keyword_score = 100 * len(keyword_matches) / len(keywords) if keywords else None

    location_score: Optional[float] = None
    if job_location and preferred_locations:
        location_score = 100 if any(
            location.casefold() in job_location.casefold() or job_location.casefold() in location.casefold()
            for location in preferred_locations
        ) else 0
    elif job_location and work_modes and "remote" in work_modes and "remote" in job_location.casefold():
        location_score = 100

    factors = {
        "technical_skills": {"weight": _weight("technical_skills"), "score": skill_score, "matched": matched_required, "total": len(required_skills)},
        "experience_relevance": {"weight": _weight("experience_relevance"), "score": experience_score, "matched": experience_skill_count, "total": len(required_skills)},
        "responsibility_alignment": {"weight": _weight("responsibility_alignment"), "score": responsibility_score, "matched": len(responsibility_hits), "total": len(responsibility_requirements)},
        "education": {"weight": _weight("education"), "score": education_score, "required": education_levels, "evidenced": parsed_resume["degrees_found"]},
        "certifications": {"weight": _weight("certifications"), "score": certification_score},
        "keyword_coverage": {"weight": _weight("keyword_coverage"), "score": keyword_score, "matched": len(keyword_matches), "total": len(keywords)},
        "location": {"weight": _weight("location"), "score": location_score, "location": job_location},
    }
    weighted = [
        (factor["score"], factor["weight"])
        for factor in factors.values()
        if factor["score"] is not None
    ]
    active_weight = sum(weight for _, weight in weighted)
    score = round(sum(value * weight for value, weight in weighted) / active_weight, 1) if active_weight else 0.0
    experience_requirement = parsed_job["required_years"]
    years_evidence = _years_evidence(parsed_resume)
    experience_gap = (
        max(0, experience_requirement - years_evidence)
        if experience_requirement is not None and years_evidence is not None
        else None
    )
    return {
        "score": score,
        "score_label": "Evidence-based resume-job compatibility estimate",
        "method": "deterministic_weighted_factors_v1",
        "factors": factors,
        "matched_skills": matched,
        "partially_matched_skills": partial,
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "experience_gaps": {
            "required_years": experience_requirement,
            "years_evidenced": years_evidence,
            "years_gap": experience_gap,
            "relevant_experience_evidence": responsibility_hits,
        },
        "qualification_gaps": [
            f"Degree level not evidenced: {', '.join(education_levels)}"
        ] if education_score == 0 else [],
        "keyword_coverage": {
            "matched": keyword_matches,
            "missing": [keyword for keyword in keywords if keyword not in keyword_matches],
            "percentage": round(keyword_score, 1) if keyword_score is not None else None,
        },
        "recommendations": [
            f"If you have genuine experience with {skill}, add specific evidence in a relevant resume section."
            for skill in missing_required[:10]
        ] + [
            "Use quantified outcomes only when you can verify the underlying figures."
        ],
        "disclaimer": "This estimate reflects text evidence and does not predict ATS selection, interviews, or hiring outcomes.",
        "job_title": job_title,
        "resume_fingerprint": hashlib.sha256(resume_text.encode("utf-8")).hexdigest(),
        "job_fingerprint": hashlib.sha256(job_text.encode("utf-8")).hexdigest(),
    }
