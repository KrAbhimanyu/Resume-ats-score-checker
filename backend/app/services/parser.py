import re
from typing import Callable, Dict, List, Set, Tuple, Optional, Any
from app.models.analysis_progress import ProgressStatus
from app.services.synonyms import (
    DEFAULT_SYNONYM_MAP,
    find_term_in_text,
    normalize_resume_text,
    normalize_text,
)


SECTION_HEADINGS = {
    "experience": (
        "work experience", "professional experience", "employment history", "experience", "work history",
    ),
    "education": (
        "education", "academic background", "academic qualifications", "academic credentials",
        "qualifications", "academic history",
    ),
    "skills": (
        "technical skills", "core competencies", "skills & technologies", "skills and technologies",
        "skills", "technologies",
    ),
    "projects": ("projects", "personal projects", "key projects", "academic projects"),
    "certifications": (
        "certifications", "certificates", "licenses", "courses & certifications",
        "courses and certifications",
    ),
    "summary": (
        "professional summary", "summary", "profile", "about me", "career objective", "objective",
    ),
}


def _heading_pattern(headings: Tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(heading) for heading in sorted(headings, key=len, reverse=True))
    return re.compile(
        rf"(?im)^[ \t]*(?:[-*#|]+\s*)?(?:{alternatives})[ \t]*:?[ \t]*$"
    )


SECTION_PATTERNS = {
    section: _heading_pattern(headings)
    for section, headings in SECTION_HEADINGS.items()
}

METRIC_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\$\s*\d+(?:,\d{3})*(?:\.\d+)?(?:[kmb]\b)?|"
    r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:k|m|million|billion|users?|customers?|requests?|"
    r"transactions?|percent|hours?|days?|weeks?|months?|years?|teams?|features?|employees?)\b)",
    re.IGNORECASE,
)

# Strong action verbs signaling hands-on practical experience
ACTION_VERBS = {
    "accelerated", "achieved", "analyzed", "architected", "automated", "built", "collaborated",
    "configured", "consolidated", "constructed", "created", "decreased", "delivered", "deployed",
    "designed", "developed", "devised", "directed", "documented", "drove", "engineered",
    "established", "executed", "expanded", "formulated", "guided", "implemented", "improved",
    "increased", "initiated", "innovated", "installed", "integrated", "investigated", "launched",
    "led", "maintained", "managed", "mentored", "migrated", "modernized", "negotiated",
    "optimized", "orchestrated", "organized", "oversaw", "partnered", "pioneered", "planned",
    "programmed", "reduced", "refactored", "resolved", "restructured", "revamped", "scaled",
    "simplified", "spearheaded", "standardized", "streamlined", "strengthened", "supervised",
    "tested", "trained", "transformed", "upgraded", "utilized", "validated"
}

# Degrees and education levels
DEGREE_KEYWORDS = {
    "bachelor": ["bachelor", "bachelors", "b.s.", "bs", "b.a.", "ba", "b.tech", "btech", "b.e.", "undergraduate"],
    "master": ["master", "masters", "m.s.", "ms", "m.a.", "ma", "m.tech", "mtech", "mba", "postgraduate"],
    "phd": ["ph.d.", "phd", "doctorate", "doctoral"],
    "associate": ["associate", "associates", "a.s.", "a.a."],
    "diploma": ["diploma", "higher secondary"],
}

# Common technical stop words to ignore when extracting job keywords
STOPWORDS = {
    "the", "and", "or", "in", "to", "for", "with", "a", "an", "is", "are", "as", "at", "by",
    "from", "on", "that", "this", "be", "will", "of", "our", "we", "you", "your", "must",
    "have", "has", "working", "work", "job", "role", "candidate", "candidates", "looking",
    "join", "team", "responsibilities", "requirements", "qualifications", "preferred", "plus",
    "ability", "skills", "experience", "years", "year", "degree", "field", "related", "equal",
    "opportunity", "employer", "salary", "benefits", "position", "full", "time", "part",
    "strong", "good", "excellent", "proven", "track", "record", "knowledge", "understanding"
}


def segment_sections(text: str, preserve_case: bool = False) -> Dict[str, str]:
    """
    Identifies and segments resume or job description into logical sections.
    """
    extracted = normalize_resume_text(text)
    normalized = extracted if preserve_case else normalize_text(extracted)
    positions: List[Tuple[int, int, str]] = []

    for sec_name, pattern in SECTION_PATTERNS.items():
        for m in pattern.finditer(normalized):
            positions.append((m.start(), m.end(), sec_name))

    positions.sort(key=lambda item: item[0])

    sections: Dict[str, str] = {}
    if not positions:
        # No standard headings found - entire document is general body
        sections["general"] = normalized
        return sections

    # Capture leading text before first section heading (often summary or contact)
    if positions[0][0] > 0:
        sections["header"] = normalized[:positions[0][0]].strip()

    for index, (_, heading_end, section_name) in enumerate(positions):
        body_end = positions[index + 1][0] if index + 1 < len(positions) else len(normalized)
        section_content = normalized[heading_end:body_end].strip()
        if section_name in sections and section_content:
            sections[section_name] = f"{sections[section_name]}\n{section_content}".strip()
        else:
            sections[section_name] = section_content

    return sections


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"(?:https?://|www\.|linkedin\.com|github\.com)", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)
_ADDRESS_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\d{1,6}\s+[\w .'-]+\b"
    r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|suite|apt|unit|postal|zip)\b",
    re.IGNORECASE,
)
_CONTACT_LABEL_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:e-?mail|phone|mobile|telephone|location|address|contact|"
    r"linkedin|github|portfolio|website|url)\b",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(
    r"^\s*(?:[-*]\s*)?[\w .,/()&-]{0,80}\b(?:19|20)\d{2}\s*(?:-|–|to|present|current)\s*(?:(?:19|20)\d{2}|present|current)?\s*$",
    re.IGNORECASE,
)
_ROLE_TITLE_RE = re.compile(
    r"^\s*(?:(?:senior|junior|lead|staff|principal|associate)\s+)?"
    r"(?:(?:software|data|full[- ]stack|frontend|front[- ]end|backend|back[- ]end|"
    r"product|devops|project|program|engineering|business|systems|security)\s+)?"
    r"(?:engineer|developer|analyst|manager|director|consultant|administrator|architect|designer)\b",
    re.IGNORECASE,
)
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s*")
_WEAK_ACHIEVEMENT_START_RE = re.compile(
    r"^(?:worked\s+on|working\s+on|assisted\s+(?:with|in)|helped\s+(?:with|to)|"
    r"supported|responsible\s+for|was\s+responsible\s+for|duties\s+included|"
    r"handled|involved\s+in|participated\s+in|contributed\s+to|tasked\s+with|assigned\s+to)\b",
    re.IGNORECASE,
)


def is_contact_or_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if (
        _EMAIL_RE.search(stripped)
        or _URL_RE.search(stripped)
        or _PHONE_RE.search(stripped)
        or _ADDRESS_RE.search(stripped)
    ):
        return True
    if _CONTACT_LABEL_RE.search(stripped):
        return True
    normalized = normalize_text(stripped)
    return any(pattern.fullmatch(normalized) for pattern in SECTION_PATTERNS.values())


def extract_achievement_bullets(sections: Dict[str, str]) -> List[str]:
    """Return original experience/project statements, excluding contact and heading lines."""
    candidates: List[str] = []
    for section_name in ("experience", "projects"):
        last_candidate_index: Optional[int] = None
        for line in sections.get(section_name, "").splitlines():
            is_table_row = " | " in line
            for segment in re.split(r"\s+\|\s+", line):
                original_line = segment.strip()
                if (
                    is_contact_or_heading(original_line)
                    or _DATE_ONLY_RE.fullmatch(original_line)
                    or _ROLE_TITLE_RE.match(original_line)
                ):
                    last_candidate_index = None
                    continue
                clean_line = _BULLET_PREFIX_RE.sub("", original_line).strip()
                words = clean_line.split()
                if len(words) < 4:
                    continue

                is_bulleted = bool(_BULLET_PREFIX_RE.match(original_line))
                first_word = re.sub(r"^[^\w]+|[^\w]+$", "", words[0].lower())
                is_achievement_statement = (
                    first_word in ACTION_VERBS
                    or bool(_WEAK_ACHIEVEMENT_START_RE.match(clean_line))
                )
                if is_bulleted or is_achievement_statement:
                    candidates.append(original_line)
                    last_candidate_index = len(candidates) - 1
                elif not is_table_row and last_candidate_index is not None and len(words) >= 3:
                    candidates[last_candidate_index] = (
                        f"{candidates[last_candidate_index]} {original_line}"
                    )

    seen: Set[str] = set()
    deduped: List[str] = []
    for bullet in candidates:
        if bullet.casefold() not in seen:
            seen.add(bullet.casefold())
            deduped.append(bullet)
    return deduped


def count_experience_entries(sections: Dict[str, str]) -> int:
    """Count role or date heading lines without double-counting paired headings."""
    lines = [line.strip() for line in sections.get("experience", "").splitlines() if line.strip()]
    role_lines = [
        line for line in lines
        if _ROLE_TITLE_RE.match(_BULLET_PREFIX_RE.sub("", line))
    ]
    if role_lines:
        return len(role_lines)
    return sum(bool(_DATE_ONLY_RE.match(line)) for line in lines)


def extract_job_requirements(
    job_text: str,
    progress_callback: Callable[
        [str, str, ProgressStatus, Dict[str, Any]], None
    ] | None = None,
) -> Dict[str, Any]:
    """
    Parses a job description to extract:
    - Mandatory / Required requirements
    - Preferred / Desired requirements
    - Key domain keywords / skills
    - Experience years required
    - Education degrees required
    """
    if progress_callback:
        progress_callback(
            "keyword_matching",
            "job_keyword_extraction",
            "in_progress",
            {},
        )
    norm_job = normalize_text(job_text)
    lines = [line.strip() for line in norm_job.split("\n") if line.strip()]

    mandatory_reqs: List[str] = []
    preferred_reqs: List[str] = []
    current_mode: str = "general"  # "required", "preferred", "general"

    # Keywords signaling section transitions
    req_headers = re.compile(
        r"(?:minimum|basic|required|mandatory|must\s+have|what\s+you(?:'ll|\s+will)\s+need|qualifications)",
        re.IGNORECASE,
    )
    pref_headers = re.compile(
        r"(?:preferred|desired|nice\s+to\s+have|bonus|plus|advantageous)",
        re.IGNORECASE,
    )

    for line in lines:
        lower_line = line.lower()
        if pref_headers.search(lower_line) and len(line) < 60:
            current_mode = "preferred"
            continue
        elif req_headers.search(lower_line) and len(line) < 60:
            current_mode = "required"
            continue

        # Check if line looks like a requirement bullet
        is_bullet = line.startswith(("-", "*", "•", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
        if is_bullet or len(line) < 120:
            clean_item = re.sub(r"^[-*•\d.)\s]+", "", line).strip()
            if len(clean_item) > 10 and not any(h in clean_item.lower() for h in ["about us", "who we are", "equal opportunity"]):
                if current_mode == "required":
                    mandatory_reqs.append(clean_item)
                elif current_mode == "preferred":
                    preferred_reqs.append(clean_item)
                else:
                    # If unspecified, treat as mandatory if it has "must", "required", or "have"
                    if re.search(r"\b(?:must|required|minimum)\b", clean_item):
                        mandatory_reqs.append(clean_item)
                    elif re.search(r"\b(?:preferred|plus|bonus)\b", clean_item):
                        preferred_reqs.append(clean_item)
                    else:
                        mandatory_reqs.append(clean_item)

    # Extract target skills from predefined knowledge base & job text
    job_skills: Set[str] = set()
    for canonical in DEFAULT_SYNONYM_MAP.keys():
        matched, _ = find_term_in_text(canonical, norm_job)
        if matched:
            job_skills.add(canonical)

    # Extract required years of experience (e.g., '5+ years', '3-5 years', 'at least 4 years')
    exp_matches = re.findall(
        r"(?:(\d+)(?:\s*(?:-|to)\s*(\d+))?|\bat\s+least\s+(\d+)|\bmin(?:imum)?\s+(\d+))\s*\+?\s*years?(?:\s+of)?\s+experience",
        norm_job,
        re.IGNORECASE,
    )
    required_years: Optional[int] = None
    if exp_matches:
        numbers = []
        for match in exp_matches:
            for num in match:
                if num and num.isdigit():
                    numbers.append(int(num))
        if numbers:
            # Use the minimum stated requirement
            required_years = min(numbers)

    # Extract degree requirement
    required_degrees: Set[str] = set()
    for level, keywords in DEGREE_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", norm_job) for kw in keywords):
            required_degrees.add(level)

    # Extract top general keywords (multi-word phrases & single tech terms)
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-\+\.#/]{2,}\b", norm_job)
    filtered_keywords: Set[str] = set()
    for w in words:
        wl = w.lower()
        if wl not in STOPWORDS and len(wl) > 2 and not wl.isdigit():
            filtered_keywords.add(wl)

    result = {
        "mandatory_requirements": mandatory_reqs[:20],
        "preferred_requirements": preferred_reqs[:15],
        "job_skills": sorted(list(job_skills)),
        "required_years": required_years,
        "required_degrees": sorted(list(required_degrees)),
        "job_keywords": filtered_keywords,
    }
    if progress_callback:
        progress_callback(
            "keyword_matching",
            "job_keyword_extraction",
            "completed",
            {
                "job_keywords": sorted(filtered_keywords),
                "job_requirement_count": len(mandatory_reqs[:20])
                + len(preferred_reqs[:15]),
            },
        )
    return result


def parse_resume_content(
    resume_text: str,
    progress_callback: Callable[
        [str, str, ProgressStatus, Dict[str, Any]], None
    ] | None = None,
) -> Dict[str, Any]:
    """
    Parses resume text to extract:
    - Detected sections
    - Action verbs and achievement metrics
    - Years of experience indicators
    - Degrees and education
    - Skills identified
    - Word and formatting metrics
    """
    if progress_callback:
        for section_name in (
            "summary",
            "experience",
            "education",
            "skills",
            "projects",
            "certifications",
        ):
            progress_callback(
                "section_detection",
                f"{section_name}_section",
                "in_progress",
                {},
            )

    norm_resume = normalize_text(resume_text)
    sections = segment_sections(norm_resume)
    original_sections = segment_sections(resume_text, preserve_case=True)

    if progress_callback:
        for section_name in (
            "summary",
            "experience",
            "education",
            "skills",
            "projects",
            "certifications",
        ):
            section_text = sections.get(section_name, "")
            progress_callback(
                "section_detection",
                f"{section_name}_section",
                "completed",
                {
                    "section_found": bool(section_text.strip()),
                    "word_count": len(section_text.split()),
                },
            )

        progress_callback(
            "experience_impact",
            "experience_extraction",
            "in_progress",
            {},
        )
        progress_callback(
            "experience_impact",
            "achievement_bullets",
            "in_progress",
            {},
        )
    achievement_bullets = extract_achievement_bullets(original_sections)
    experience_entries_count = count_experience_entries(original_sections)
    if progress_callback:
        progress_callback(
            "experience_impact",
            "experience_extraction",
            "completed",
            {"experience_entries_count": experience_entries_count},
        )
        progress_callback(
            "experience_impact",
            "achievement_bullets",
            "completed",
            {"achievement_bullets_count": len(achievement_bullets)},
        )

    # 1. Action verbs count only when they appear in extracted experience/project statements.
    if progress_callback:
        progress_callback(
            "experience_impact",
            "action_verb_analysis",
            "in_progress",
            {},
        )
    tokens = re.findall(r"\b[a-z]+\b", norm_resume)
    unique_tokens = set(tokens)
    achievement_tokens = re.findall(
        r"\b[a-z]+\b", "\n".join(achievement_bullets).lower()
    )
    action_verbs_found = set(achievement_tokens).intersection(ACTION_VERBS)
    if progress_callback:
        progress_callback(
            "experience_impact",
            "action_verb_analysis",
            "completed",
            {
                "action_verbs": sorted(action_verbs_found),
                "action_verb_count": len(action_verbs_found),
            },
        )

    # 2. Metrics and quantified results (percentages, currencies, counts, scaling metrics)
    if progress_callback:
        progress_callback(
            "experience_impact",
            "quantified_achievements",
            "in_progress",
            {},
        )
    metrics_matches = [
        match.group(0)
        for match in METRIC_PATTERN.finditer("\n".join(achievement_bullets))
    ]
    quantified_achievements_count = sum(
        bool(METRIC_PATTERN.search(bullet)) for bullet in achievement_bullets
    )
    if progress_callback:
        progress_callback(
            "experience_impact",
            "quantified_achievements",
            "completed",
            {"quantified_achievements_count": quantified_achievements_count},
        )

    # 3. Resume years of experience evidence
    exp_year_matches = re.findall(
        r"(?:(\d+)\s*\+?\s*years?(?:\s+of)?\s+experience|\b(20\d\d|19\d\d)\s*(?:-|to|–|present|current)\s*(20\d\d|present|current))",
        norm_resume,
        re.IGNORECASE,
    )

    # 4. Degrees identified in resume
    degrees_found: Set[str] = set()
    for level, keywords in DEGREE_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", norm_resume) for kw in keywords):
            degrees_found.add(level)

    # 5. Skills identified in resume
    if progress_callback:
        progress_callback(
            "keyword_matching",
            "skills_extraction",
            "in_progress",
            {},
        )
    skills_found: Set[str] = set()
    for canonical in DEFAULT_SYNONYM_MAP.keys():
        matched, _ = find_term_in_text(canonical, norm_resume)
        if matched:
            skills_found.add(canonical)
    if progress_callback:
        progress_callback(
            "keyword_matching",
            "skills_extraction",
            "completed",
            {"skills_identified": sorted(skills_found)},
        )

    # 6. Structural metrics
    has_experience_sec = bool(sections.get("experience"))
    has_education_sec = bool(sections.get("education"))
    has_skills_sec = bool(sections.get("skills"))
    word_count = len(tokens)
    bullet_count = len(achievement_bullets)

    return {
        "sections": sections,
        "action_verbs": sorted(list(action_verbs_found)),
        "metrics_found": metrics_matches,
        "experience_indicators": exp_year_matches,
        "degrees_found": sorted(list(degrees_found)),
        "skills_found": sorted(list(skills_found)),
        "has_experience_section": has_experience_sec,
        "has_education_section": has_education_sec,
        "has_skills_section": has_skills_sec,
        "word_count": word_count,
        "bullet_count": bullet_count,
        "experience_entries_count": experience_entries_count,
        "quantified_achievements_count": quantified_achievements_count,
        "achievement_bullets": achievement_bullets,
        "raw_tokens": unique_tokens,
    }
