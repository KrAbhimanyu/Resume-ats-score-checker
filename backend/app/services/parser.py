import re
from typing import Dict, List, Set, Tuple, Optional, Any
from app.services.synonyms import DEFAULT_SYNONYM_MAP, find_term_in_text, normalize_text


# Standard resume section regexes
SECTION_PATTERNS = {
    "experience": re.compile(
        r"(?:^|\n)(?:\s*(?:work\s+experience|professional\s+experience|employment\s+history|experience|work\s+history))\b",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"(?:^|\n)(?:\s*(?:education|academic\s+background|academic\s+credentials|qualifications|academic\s+history))\b",
        re.IGNORECASE,
    ),
    "skills": re.compile(
        r"(?:^|\n)(?:\s*(?:technical\s+skills|core\s+competencies|skills\s*(?:&|and)\s*technologies|skills|technologies))\b",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"(?:^|\n)(?:\s*(?:projects|personal\s+projects|key\s+projects|academic\s+projects))\b",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"(?:^|\n)(?:\s*(?:certifications|licenses|courses\s*(?:&|and)\s*certifications))\b",
        re.IGNORECASE,
    ),
    "summary": re.compile(
        r"(?:^|\n)(?:\s*(?:professional\s+summary|summary|profile|about\s+me|career\s+objective|objective))\b",
        re.IGNORECASE,
    ),
}

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


def segment_sections(text: str) -> Dict[str, str]:
    """
    Identifies and segments resume or job description into logical sections.
    """
    normalized = normalize_text(text)
    positions: List[Tuple[int, str]] = []

    for sec_name, pattern in SECTION_PATTERNS.items():
        for m in pattern.finditer(normalized):
            positions.append((m.start(), sec_name))

    positions.sort(key=lambda x: x[0])

    sections: Dict[str, str] = {}
    if not positions:
        # No standard headings found - entire document is general body
        sections["general"] = normalized
        return sections

    # Capture leading text before first section heading (often summary or contact)
    if positions[0][0] > 0:
        sections["header"] = normalized[:positions[0][0]].strip()

    for i in range(len(positions)):
        start_idx = positions[i][0]
        sec_name = positions[i][1]
        end_idx = positions[i + 1][0] if i + 1 < len(positions) else len(normalized)
        section_content = normalized[start_idx:end_idx].strip()
        sections[sec_name] = section_content

    return sections


def extract_job_requirements(job_text: str) -> Dict[str, Any]:
    """
    Parses a job description to extract:
    - Mandatory / Required requirements
    - Preferred / Desired requirements
    - Key domain keywords / skills
    - Experience years required
    - Education degrees required
    """
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

    return {
        "mandatory_requirements": mandatory_reqs[:20],
        "preferred_requirements": preferred_reqs[:15],
        "job_skills": sorted(list(job_skills)),
        "required_years": required_years,
        "required_degrees": sorted(list(required_degrees)),
        "job_keywords": filtered_keywords,
    }


def parse_resume_content(resume_text: str) -> Dict[str, Any]:
    """
    Parses resume text to extract:
    - Detected sections
    - Action verbs and achievement metrics
    - Years of experience indicators
    - Degrees and education
    - Skills identified
    - Word and formatting metrics
    """
    norm_resume = normalize_text(resume_text)
    sections = segment_sections(norm_resume)

    # 1. Action verbs count
    tokens = re.findall(r"\b[a-z]+\b", norm_resume)
    unique_tokens = set(tokens)
    action_verbs_found = unique_tokens.intersection(ACTION_VERBS)

    # 2. Metrics and quantified results (percentages, currencies, counts, scaling metrics)
    metrics_matches = re.findall(
        r"(?:\b\d+(?:\.\d+)?%|\$\s*\d+(?:,\d+)*(?:\.\d+)?[kmb]?|\b\d+\s*(?:k|million|billion|users|customers|requests|transactions|percent)\b)",
        norm_resume,
        re.IGNORECASE,
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
    skills_found: Set[str] = set()
    for canonical in DEFAULT_SYNONYM_MAP.keys():
        matched, _ = find_term_in_text(canonical, norm_resume)
        if matched:
            skills_found.add(canonical)

    # 6. Structural metrics
    has_experience_sec = "experience" in sections
    has_education_sec = "education" in sections
    has_skills_sec = "skills" in sections
    word_count = len(tokens)
    bullet_count = len(re.findall(r"(?:^|\n)\s*-\s+", norm_resume))

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
        "raw_tokens": unique_tokens,
    }
