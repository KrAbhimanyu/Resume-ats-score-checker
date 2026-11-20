import re
from typing import Dict, List, Set, Tuple, Optional


_SPACED_HEADING_KEYS = {
    "professional summary",
    "summary",
    "profile",
    "about me",
    "career objective",
    "objective",
    "work experience",
    "professional experience",
    "employment history",
    "experience",
    "work history",
    "technical skills",
    "core competencies",
    "skills and technologies",
    "skills technologies",
    "skills",
    "technologies",
    "education",
    "academic background",
    "academic qualifications",
    "academic credentials",
    "academic history",
    "qualifications",
    "projects",
    "personal projects",
    "key projects",
    "academic projects",
    "certifications",
    "certificates",
    "licenses",
    "courses and certifications",
}
_SPACED_HEADING_TEXT = {
    re.sub(r"[^a-z]", "", heading): heading.title()
    for heading in _SPACED_HEADING_KEYS
}


def _restore_spaced_headings(text: str) -> str:
    lines: List[str] = []
    for line in text.splitlines(keepends=True):
        words = re.findall(r"[A-Za-z]+", line)
        compact = "".join(words).lower()
        single_letter_ratio = sum(len(word) == 1 for word in words) / max(1, len(words))
        if (
            len(words) >= 5
            and single_letter_ratio >= 0.7
            and compact in _SPACED_HEADING_TEXT
        ):
            match = re.search(r"[A-Za-z].*[A-Za-z]", line)
            if match:
                line = line[:match.start()] + _SPACED_HEADING_TEXT[compact] + line[match.end():]
        lines.append(line)
    return "".join(lines)


def normalize_resume_text(text: str) -> str:
    """Normalize extracted layout while preserving case and line-level structure."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace("\u00a0", " ").replace("\u200b", "")
    cleaned = _restore_spaced_headings(cleaned)
    cleaned = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25CF]", "- ", cleaned)
    cleaned = re.sub(r"[\u2013\u2014]", "-", cleaned)

    lines: List[str] = []
    for line in cleaned.split("\n"):
        if re.fullmatch(r"\s*(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?\s*", line, re.IGNORECASE):
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# Canonical key -> list of synonyms, aliases, or alternate spellings
DEFAULT_SYNONYM_MAP: Dict[str, List[str]] = {
    "python": ["python3", "python 3", "py"],
    "javascript": ["js", "ecmascript", "es6", "es2015", "es2020"],
    "typescript": ["ts"],
    "react": ["reactjs", "react.js", "react js"],
    "node.js": ["nodejs", "node js", "node"],
    "vue.js": ["vuejs", "vue.js", "vue"],
    "angular": ["angularjs", "angular 2+"],
    "c++": ["cpp", "cplusplus", "c plus plus"],
    "c#": ["csharp", "c sharp", "dotnet c#"],
    ".net": [".net core", "asp.net", "dotnet"],
    "golang": ["go", "go language", "go lang"],
    "postgresql": ["postgres", "psql", "postgre sql"],
    "mysql": ["my-sql"],
    "mongodb": ["mongo", "nosql mongo"],
    "sql": ["relational database", "rdbms", "sql query", "sql queries"],
    "nosql": ["document store", "non-relational"],
    "docker": ["containerization", "containers", "dockerized"],
    "kubernetes": ["k8s", "container orchestration"],
    "ci/cd": ["continuous integration", "continuous deployment", "cicd", "ci cd", "deployment pipeline"],
    "aws": ["amazon web services", "amazon cloud"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "azure cloud"],
    "rest api": ["restful api", "restful apis", "restful web services", "rest apis", "rest endpoints"],
    "graphql": ["graph ql"],
    "machine learning": ["ml", "deep learning", "predictive modeling"],
    "artificial intelligence": ["ai", "generative ai", "genai", "llm"],
    "natural language processing": ["nlp", "text analytics"],
    "agile": ["scrum", "kanban", "sprint planning"],
    "git": ["github", "gitlab", "bitbucket", "version control"],
    "unit testing": ["automated testing", "test driven development", "tdd", "unit tests", "integration tests"],
    "microservices": ["microservice architecture", "distributed systems", "service-oriented architecture"],
    "fastapi": ["fast api"],
    "django": ["django rest framework", "drf"],
    "flask": ["python flask"],
    "spring boot": ["springboot", "spring-boot", "spring framework"],
    "html": ["html5"],
    "css": ["css3", "sass", "scss", "tailwind", "bootstrap"],
    "devops": ["sre", "site reliability engineering", "infrastructure as code", "iac"],
    "terraform": ["iac terraform", "hashicorp terraform"],
    "kafka": ["apache kafka", "event streaming", "message broker"],
    "redis": ["in-memory cache", "caching", "redis cache"],
    "linux": ["unix", "ubuntu", "debian", "redhat", "centos"],
    "data science": ["data analysis", "data analytics", "statistical analysis"],
    "power bi": ["powerbi", "microsoft power bi"],
    "tableau": ["tableau software", "tableau desktop"],
    "excel": ["ms excel", "spreadsheets", "advanced excel"],
}


def normalize_text(text: str) -> str:
    """
    Normalizes text for robust semantic comparison.
    - Converts to lowercase.
    - Normalizes various Unicode spaces, bullet points, and dashes.
    - Replaces consecutive whitespaces with single space.
    """
    if not text:
        return ""
    # Replace non-breaking spaces and unusual whitespace
    cleaned = text.replace("\u00a0", " ").replace("\u200b", " ")
    cleaned = _restore_spaced_headings(cleaned)
    # Normalize bullet points and dashes
    cleaned = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25CF]", " - ", cleaned)
    cleaned = re.sub(r"[\u2013\u2014]", "-", cleaned)
    # Lowercase
    cleaned = cleaned.lower()
    # Normalize spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def build_synonym_lookup(custom_map: Optional[Dict[str, List[str]]] = None) -> Dict[str, Set[str]]:
    """
    Builds a reverse lookup mapping from any synonym or variation to its canonical keyword,
    plus maps canonical keywords to all their accepted variations.
    """
    combined: Dict[str, List[str]] = dict(DEFAULT_SYNONYM_MAP)
    if custom_map:
        for k, v in custom_map.items():
            if k in combined:
                combined[k] = list(set(combined[k] + v))
            else:
                combined[k] = v

    lookup: Dict[str, Set[str]] = {}
    for canonical, variations in combined.items():
        all_forms = set([canonical.lower()] + [v.lower() for v in variations])
        for form in all_forms:
            lookup[form] = all_forms
    return lookup


_GLOBAL_SYNONYM_LOOKUP = build_synonym_lookup()


def find_term_in_text(term: str, text: str, synonym_map: Optional[Dict[str, Set[str]]] = None) -> Tuple[bool, Optional[str]]:
    """
    Checks if a target term (or any of its known synonyms) is present in the text.
    Uses regex word boundaries to prevent substring false-positives (e.g. 'c' in 'cloud' or 'go' in 'good').
    Returns (matched: bool, matched_form: Optional[str]).
    """
    if not term or not text:
        return False, None

    normalized_term = term.strip().lower()
    lookup = synonym_map or _GLOBAL_SYNONYM_LOOKUP

    # Target variants to search for
    variants = lookup.get(normalized_term, {normalized_term})

    for variant in variants:
        # Create regex pattern with word boundaries.
        # Escape special characters (e.g. c++, c#, .net, ci/cd)
        pattern = create_word_boundary_regex(variant)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(0)

    return False, None


def create_word_boundary_regex(phrase: str) -> str:
    """
    Creates a regex pattern for a phrase that safely handles non-alphanumeric
    terminators like C++, C#, .NET, and CI/CD while ensuring boundary safety.
    """
    escaped = re.escape(phrase.strip().lower())
    # If phrase starts with alphanumeric, prepend \b
    prefix = r"\b" if phrase[0].isalnum() else r"(?:^|\s)"
    # If phrase ends with alphanumeric, append \b
    suffix = r"\b" if phrase[-1].isalnum() else r"(?:$|\s|[.,;])"
    return prefix + escaped + suffix
