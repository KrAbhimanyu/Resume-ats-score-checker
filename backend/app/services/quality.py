import re
from typing import Any, Dict, List

from app.models.schemas import GrammarIssue, QualityCheck, ResumeQualityReport, SectionQuality
from app.services.parser import ACTION_VERBS, METRIC_PATTERN, is_contact_or_heading


SECTION_LABELS = {
    "summary": "Professional summary",
    "experience": "Experience",
    "skills": "Skills",
    "education": "Education",
    "projects": "Projects",
    "certifications": "Certifications",
}

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s*")

def _count_syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ye")):
        count -= 1
    return max(1, count)


def _readability(text: str) -> tuple[float, str, str]:
    lines = [
        _BULLET_PREFIX_RE.sub("", line).strip()
        for line in text.splitlines()
        if line.strip() and not is_contact_or_heading(line)
    ]
    sentences = [
        sentence.strip()
        for line in lines
        for sentence in re.split(r"[.!?]+", line)
        if sentence.strip()
    ]
    words = re.findall(r"\b[\w'-]+\b", text)
    if not sentences or not words:
        return 0.0, "Not enough text", "A readability estimate needs readable summary or achievement text."

    sentence_count = len(sentences)
    content = " ".join(sentences)
    words = re.findall(r"\b[\w'-]+\b", content)
    word_count = len(words)
    if word_count < 30 or sentence_count < 3:
        return (
            0.0,
            "Not enough text",
            f"Readability estimate withheld: found {word_count} words across {sentence_count} "
            "summary or achievement statement(s); at least 30 words and 3 statements are needed "
            "for this heuristic.",
        )
    syllables = sum(_count_syllables(word) for word in words)
    score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllables / word_count)
    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 60:
        label = "Generally easy to read"
    elif score >= 40:
        label = "Moderately complex"
    else:
        label = "Difficult to scan"
    detail = (
        f"Estimated Flesch Reading Ease: {score}/100 using {word_count} words across "
        f"{sentence_count} summary or achievement statement(s). Fragments are treated as separate "
        "statements; this is a text-only heuristic, not a writing-grade judgment."
    )
    return score, label, detail


def _grammar_issues(text: str) -> List[GrammarIssue]:
    issues: List[GrammarIssue] = []
    seen = set()
    text = "\n".join(
        line for line in text.splitlines()
        if not is_contact_or_heading(line)
    )

    def add(category: str, excerpt: str, suggestion: str) -> None:
        key = (category, excerpt.lower())
        if key not in seen:
            seen.add(key)
            issues.append(GrammarIssue(category=category, excerpt=excerpt[:120], suggestion=suggestion))

    for match in re.finditer(r"\b([A-Za-z]+)\s+\1\b", text, re.IGNORECASE):
        add("Repeated word", match.group(0), f"Check whether “{match.group(1)}” was typed twice.")
    for match in re.finditer(r"\s+([,.;:!?])", text):
        add("Punctuation spacing", match.group(0), "Remove the space before the punctuation mark.")
    for match in re.finditer(r"[!?]{2,}|\.{4,}", text):
        add("Punctuation", match.group(0), "Use standard resume punctuation consistently.")
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        if len(words) > 35:
            add(
                "Long sentence",
                " ".join(words[:12]) + "…",
                "Consider splitting this sentence into concise accomplishment-focused statements.",
            )
    return issues[:30]


def generate_resume_quality_report(
    resume_text: str,
    parsed_resume: Dict[str, Any],
    parsed_job: Dict[str, Any],
) -> ResumeQualityReport:
    sections = parsed_resume.get("sections", {})
    section_analysis: List[SectionQuality] = []
    for section, label in SECTION_LABELS.items():
        content = sections.get(section, "")
        words = re.findall(r"\b[\w'-]+\b", content)
        findings: List[str] = []
        if not content:
            if section in {"experience", "skills", "education"}:
                findings.append(f"No standard {label.lower()} heading or content was detected.")
        elif section == "experience":
            if parsed_resume.get("bullet_count", 0) == 0:
                findings.append("Use concise bullet points so accomplishments are easy to scan.")
            if not parsed_resume.get("metrics_found"):
                findings.append("Add verified scope or outcome metrics where available.")
        elif section == "summary" and len(words) > 90:
            findings.append("Consider shortening this section to a concise, role-focused introduction.")
        elif section == "skills" and len(words) > 80:
            findings.append("Group relevant skills under clear labels and prioritize job-related skills.")
        section_analysis.append(
            SectionQuality(
                name=label,
                found=bool(content),
                word_count=len(words),
                findings=findings,
            )
        )

    grammar_issues = _grammar_issues(resume_text)
    formatting_findings: List[str] = []
    present_core_sections = sum(
        bool(sections.get(section))
        for section in ("experience", "education", "skills")
    )
    if present_core_sections < 3:
        formatting_findings.append("Use recognizable Experience, Education, and Skills headings where applicable.")
    if parsed_resume.get("bullet_count", 0) == 0:
        formatting_findings.append(
            "No experience or project achievement statements were extracted; use simple text bullets where applicable."
        )
    if not re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", resume_text, re.IGNORECASE):
        formatting_findings.append("No email address was detected in extracted text; verify that contact details are present.")
    if len(re.findall(r"[^\n]{140,}", resume_text)) > 0:
        formatting_findings.append("Some lines are very long; check that the source document is easy to scan.")
    if not formatting_findings:
        formatting_findings.append("Standard headings and readable text structure were detected.")

    ats_checks = [
        QualityCheck(
            title="Standard section headings",
            status="pass" if present_core_sections >= 2 else "review",
            detail=f"Detected {present_core_sections} of 3 core headings: Experience, Education, and Skills.",
        ),
        QualityCheck(
            title="Readable text extraction",
            status="pass" if parsed_resume.get("word_count", 0) >= 100 else "review",
            detail=f"Extracted {parsed_resume.get('word_count', 0)} words. Text extraction cannot confirm visual layout.",
        ),
        QualityCheck(
            title="Simple bullet structure",
            status="pass" if parsed_resume.get("bullet_count", 0) > 0 else "review",
            detail=(
                f"Detected {parsed_resume.get('bullet_count', 0)} experience/project achievement statement(s); "
                "tables, columns, and graphics cannot be fully verified from extracted text."
            ),
        ),
        QualityCheck(
            title="Job requirement evidence",
            status="pass" if parsed_job.get("job_skills") else "review",
            detail=f"Matched job-related skills: {len(set(parsed_job.get('job_skills', [])) & set(parsed_resume.get('skills_found', [])))}.",
        ),
    ]

    bullets = parsed_resume.get("achievement_bullets", [])
    quantified_bullets = sum(bool(METRIC_PATTERN.search(bullet)) for bullet in bullets)
    action_bullets = sum(
        bool(re.match(r"^\W*(\w+)", _BULLET_PREFIX_RE.sub("", bullet).lower()))
        and re.match(r"^\W*(\w+)", _BULLET_PREFIX_RE.sub("", bullet).lower()).group(1) in ACTION_VERBS
        for bullet in bullets
    )
    if bullets:
        metric_ratio = quantified_bullets / len(bullets)
        verb_ratio = action_bullets / len(bullets)
        impact_score = round(100 * (0.5 * metric_ratio + 0.5 * verb_ratio), 1)
    else:
        impact_score = 0.0
    impact_explanation = (
        f"Estimated impact score {impact_score}/100, based only on extracted bullets: "
        f"{quantified_bullets}/{len(bullets)} include a numeric signal and "
        f"{action_bullets}/{len(bullets)} start with a recognized action verb. "
        "Numbers are not evidence of truth; verify every claim."
    )

    readability_text = "\n".join(
        [
            *(
                line for line in sections.get("summary", "").splitlines()
                if not is_contact_or_heading(line)
            ),
            *bullets,
        ]
    )
    readability_score, readability_label, readability_explanation = _readability(readability_text)
    quality_checks = [
        QualityCheck(
            title="Resume sections",
            status="pass" if present_core_sections == 3 else "attention",
            detail=f"{present_core_sections}/3 core sections detected. Add missing sections only when they reflect your background.",
        ),
        QualityCheck(
            title="Grammar pattern review",
            status="pass" if not grammar_issues else "attention",
            detail=f"{len(grammar_issues)} possible writing pattern(s) flagged for human review; no automatic edits were made.",
        ),
        QualityCheck(
            title="Achievement evidence",
            status="pass" if quantified_bullets > 0 else "attention",
            detail=f"{quantified_bullets} bullet(s) contain numeric outcome or scope signals. Add only verified metrics.",
        ),
        QualityCheck(
            title="Job-specific alignment",
            status="pass" if set(parsed_job.get("job_skills", [])) & set(parsed_resume.get("skills_found", [])) else "review",
            detail="Compare matched and missing requirements below; never add a skill you do not have.",
        ),
    ]

    job_skills = set(parsed_job.get("job_skills", []))
    matched_skills = sorted(job_skills & set(parsed_resume.get("skills_found", [])))[:5]
    if matched_skills:
        display_names = {
            "aws": "AWS",
            "ci/cd": "CI/CD",
            "fastapi": "FastAPI",
            "javascript": "JavaScript",
            "postgresql": "PostgreSQL",
            "python": "Python",
            "rest api": "REST API",
            "sql": "SQL",
        }
        skill_names = [display_names.get(skill, skill.title()) for skill in matched_skills]
        summary_draft = (
            f"Targeting [target role], with resume-documented skills in {', '.join(skill_names)}. "
            "Add a verified specialization and measurable achievement before use."
        )
    else:
        summary_draft = (
            "Targeting [target role], with verified strengths in [resume-documented skills]. "
            "Add one measurable achievement before use."
        )

    return ResumeQualityReport(
        section_analysis=section_analysis,
        formatting_findings=formatting_findings,
        grammar_issues=grammar_issues,
        readability_score=readability_score,
        readability_label=readability_label,
        readability_explanation=readability_explanation,
        impact_score=impact_score,
        impact_explanation=impact_explanation,
        ats_compatibility_checks=ats_checks,
        quality_assurance_checks=quality_checks,
        professional_summary_draft=summary_draft,
    )
