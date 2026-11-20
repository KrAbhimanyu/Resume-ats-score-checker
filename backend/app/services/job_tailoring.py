import re
from typing import Any

from app.models.builder_schemas import StructuredResume
from app.services.builder_service import parse_text_to_structured_resume, segment_sections_preserving_case
from app.services.job_matching import match_resume_to_job
from app.services.parser import parse_resume_content


_SAFE_VERB_RULES = (
    (re.compile(r"^worked\s+on\b", re.I), "Developed"),
    (re.compile(r"^working\s+on\b", re.I), "Developing"),
    (re.compile(r"^responsible\s+for\b", re.I), "Managed"),
    (re.compile(r"^assisted\s+with\b", re.I), "Contributed to"),
    (re.compile(r"^helped\s+with\b", re.I), "Contributed to"),
    (re.compile(r"^handled\b", re.I), "Managed"),
)


def _structured_resume(text: str) -> StructuredResume:
    return parse_text_to_structured_resume(text)


def _safe_bullet_suggestion(text: str) -> str | None:
    clean = re.sub(r"^[-*•\d.)\s]+", "", text.strip())
    for pattern, replacement in _SAFE_VERB_RULES:
        if pattern.search(clean):
            candidate = pattern.sub(replacement, clean, count=1)
            if candidate != clean:
                return candidate
    return None


def _serialize_resume(resume: StructuredResume) -> str:
    contact = resume.contact_info
    lines = [contact.full_name]
    details = [contact.email, contact.phone, contact.location, contact.linkedin, contact.github]
    lines.append(" | ".join(value for value in details if value))
    if resume.summary:
        lines.extend(["", "Professional Summary", resume.summary])
    if resume.skills:
        lines.append("")
        lines.append("Technical Skills")
        for category, values in resume.skills.items():
            lines.append(f"{category}: {', '.join(values)}")
    if resume.experience:
        lines.extend(["", "Work Experience"])
        for entry in resume.experience:
            lines.append(f"{entry.title} - {entry.company}")
            lines.extend(f"- {bullet}" for bullet in entry.bullets)
    if resume.projects:
        lines.extend(["", "Projects"])
        for project in resume.projects:
            lines.append(project.title)
            lines.extend(f"- {bullet}" for bullet in project.bullets)
    if resume.education:
        lines.extend(["", "Education"])
        lines.extend(f"{item.degree} - {item.institution}" for item in resume.education)
    if resume.certifications:
        lines.extend(["", "Certifications", *resume.certifications])
    return "\n".join(line for line in lines if line is not None).strip()


def create_tailoring_review(
    resume_text: str,
    job_title: str,
    job_description: str,
    job_location: str | None,
) -> dict[str, Any]:
    match = match_resume_to_job(
        resume_text, job_description, job_title=job_title, job_location=job_location
    )
    parsed = parse_resume_content(resume_text)
    original_sections = segment_sections_preserving_case(resume_text)
    evidenced_skills = parsed["skills_found"]
    summary = (
        f"Professional targeting {job_title} opportunities, with resume-documented evidence in "
        f"{', '.join(evidenced_skills[:5])}."
        if evidenced_skills
        else f"Professional targeting {job_title} opportunities; review the experience below and add a summary using only verified qualifications."
    )
    changes: list[dict[str, Any]] = [{
        "id": "summary-evidence-based",
        "section": "summary",
        "original_text": original_sections.get("summary", ""),
        "proposed_text": summary,
        "rationale": "Uses only skills detected in the source resume and states the target role as an objective.",
        "what_to_verify": "Confirm every listed skill and the summary accurately represent your experience.",
        "is_accepted": False,
    }]
    for index, line in enumerate(original_sections.get("experience", "").splitlines()):
        suggestion = _safe_bullet_suggestion(line)
        if suggestion:
            changes.append({
                "id": f"experience-verb-{index}",
                "section": "experience",
                "original_text": line.strip(),
                "proposed_text": suggestion,
                "rationale": "A concise action-verb edit based on the exact source bullet; no new metrics or skills are added.",
                "what_to_verify": "Confirm the action verb reflects your actual contribution.",
                "is_accepted": False,
            })
    return {
        "job_title": job_title,
        "match": match,
        "missing_skills": match["missing_required_skills"],
        "matched_skills": [item["skill"] for item in match["matched_skills"]],
        "section_recommendations": [
            "Prioritize resume-evidenced skills that also appear in the job posting.",
            "Keep unsupported requirements out of the resume unless you can verify them.",
        ],
        "changes": changes,
        "draft_resume": _structured_resume(resume_text).model_dump(mode="json"),
        "status": "review",
        "method": "deterministic_local_rules",
        "disclaimer": "Suggestions are rule-based rather than generative AI. Review every proposed edit; no missing skills or achievements are inserted.",
    }


def apply_approved_changes(analysis: dict[str, Any]) -> StructuredResume:
    resume = StructuredResume.model_validate(analysis["draft_resume"])
    for change in analysis["changes"]:
        if not change.get("is_accepted"):
            continue
        text = change.get("proposed_text")
        if not isinstance(text, str) or not text.strip():
            continue
        if change["section"] == "summary":
            resume.summary = text.strip()
        elif change["section"] == "experience":
            original = change.get("original_text", "").strip()
            for entry in resume.experience:
                for index, bullet in enumerate(entry.bullets):
                    if bullet.strip() == original:
                        entry.bullets[index] = text.strip()
                        break
    return resume


serialize_resume = _serialize_resume
