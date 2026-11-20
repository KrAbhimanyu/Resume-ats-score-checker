import re
import uuid
from typing import List, Dict, Any, Optional, Tuple, Set

from app.models.schemas import (
    StrengthItem,
    BulletImprovement,
    JobSkillAlignment,
    ActionVerbCategory,
    MetricGuidanceItem,
    ChecklistItem,
    ResumeImprovementAssistant,
    BulletImprovementResponse,
    RequirementMatch,
    MissingRequirement,
)
from app.services.synonyms import DEFAULT_SYNONYM_MAP, find_term_in_text, normalize_text
from app.services.parser import ACTION_VERBS, extract_achievement_bullets

# Weak / passive starter patterns with specific issues and replacement verbs
WEAK_STARTER_RULES: List[Tuple[re.Pattern, str, str, str]] = [
    (
        re.compile(r"^(?:worked\s+on|working\s+on)\b", re.IGNORECASE),
        "Starts with passive phrasing 'worked on' which diminishes individual ownership and decisive contribution.",
        "Engineered",
        "Tested / Developed",
    ),
    (
        re.compile(r"^(?:assisted\s+(?:with|in)|helped\s+(?:with|to)|supported)\b", re.IGNORECASE),
        "Uses supportive phrasing ('assisted with' / 'helped with') that obscures your specific technical execution.",
        "Collaborated to deliver",
        "Co-developed",
    ),
    (
        re.compile(r"^(?:responsible\s+for|was\s+responsible\s+for|duties\s+included)\b", re.IGNORECASE),
        "Reads like a passive job description duty ('responsible for') rather than an accomplishment statement.",
        "Spearheaded",
        "Managed",
    ),
    (
        re.compile(r"^(?:handled|handled\s+all)\b", re.IGNORECASE),
        "Uses generic verb 'handled' which conveys routine administration instead of technical skill.",
        "Orchestrated",
        "Resolved",
    ),
    (
        re.compile(r"^(?:involved\s+in|participated\s+in|contributed\s+to)\b", re.IGNORECASE),
        "Phrasing ('involved in' / 'participated in') downplays leadership and tangible outcomes.",
        "Executed",
        "Delivered",
    ),
    (
        re.compile(r"^(?:tasked\s+with|assigned\s+to)\b", re.IGNORECASE),
        "Conveys passive assignment ('tasked with') rather than proactive execution.",
        "Spearheaded",
        "Implemented",
    ),
    (
        re.compile(r"^(?:did|made|tried\s+to)\b", re.IGNORECASE),
        "Vague, colloquial verb lacks professional technical weight.",
        "Authored",
        "Engineered",
    ),
]

# Action verbs mapped by category
CATEGORIZED_ACTION_VERBS: List[ActionVerbCategory] = [
    ActionVerbCategory(
        category_name="Technical & Architecture",
        verbs=[
            "Architected",
            "Engineered",
            "Automated",
            "Refactored",
            "Deployed",
            "Configured",
            "Integrated",
            "Modernized",
        ],
    ),
    ActionVerbCategory(
        category_name="Leadership & Ownership",
        verbs=[
            "Spearheaded",
            "Orchestrated",
            "Directed",
            "Guided",
            "Championed",
            "Mentored",
            "Pioneered",
            "Standardized",
        ],
    ),
    ActionVerbCategory(
        category_name="Performance & Optimization",
        verbs=[
            "Optimized",
            "Accelerated",
            "Streamlined",
            "Scaled",
            "Reduced",
            "Consolidated",
            "Maximized",
            "Transformed",
        ],
    ),
    ActionVerbCategory(
        category_name="Testing, Analysis & Quality",
        verbs=[
            "Tested",
            "Validated",
            "Audited",
            "Analyzed",
            "Diagnosed",
            "Formulated",
            "Investigated",
            "Resolved",
        ],
    ),
]

# Guiding questions to help users recall verified metrics
METRIC_GUIDANCE_ITEMS: List[MetricGuidanceItem] = [
    MetricGuidanceItem(
        metric_type="Scale & Traffic",
        guiding_question="How many daily active users, concurrent requests, database records, or endpoints did this service support?",
        example_pattern="Scaled [service] to handle [add verified count, e.g., 50k+ daily active users] with zero downtime.",
    ),
    MetricGuidanceItem(
        metric_type="Speed & Latency",
        guiding_question="By how much did your query optimization, caching layer, or refactoring reduce response times or page load speeds?",
        example_pattern="Reduced API response latency by [add verified %, e.g., 35%] via Redis caching and database indexing.",
    ),
    MetricGuidanceItem(
        metric_type="Time & Productivity",
        guiding_question="How many hours per sprint or days per release cycle did your automated script or CI/CD pipeline save?",
        example_pattern="Automated testing and deployment workflows, saving [add verified hours, e.g., 6 hours per sprint] for the development team.",
    ),
    MetricGuidanceItem(
        metric_type="Quality & Reliability",
        guiding_question="Did your unit tests, linting rules, or monitoring reduce production defect rates or customer support escalations?",
        example_pattern="Elevated automated test coverage to [add verified %, e.g., 85%], reducing production defect escalations by [add verified %].",
    ),
    MetricGuidanceItem(
        metric_type="Financial / Resource Efficiency",
        guiding_question="Did you optimize cloud instances, reduce database storage overhead, or consolidate third-party licenses?",
        example_pattern="Lowered monthly cloud infrastructure expenditures by [add verified $, e.g., $800/month] through container consolidation.",
    ),
]


def extract_candidate_bullets(sections: Dict[str, str]) -> List[str]:
    """
    Extract only experience/project achievement statements, keeping their original wording.
    """
    return extract_achievement_bullets(sections)


def analyze_bullet_point(
    bullet_text: str,
    target_skills: Optional[List[str]] = None,
) -> Tuple[bool, List[str], str, str, Optional[str], List[str]]:
    """
    Deterministically analyzes a single bullet point for weaknesses and crafts a structured rewrite.
    Returns:
        (is_weak, issues_list, suggested_rewrite, what_to_add, recommended_action_verb, detected_skills)
    """
    clean_text = bullet_text.strip()
    # Strip any leading bullet markers
    clean_text = re.sub(r"^[-*•–—\u2022\u25cf\d.)]+\s*", "", clean_text).strip()
    if not extract_achievement_bullets({"experience": clean_text}):
        issues = ["This text is not a recognizable experience or project achievement statement."]
        return (
            True,
            issues,
            "No achievement rewrite generated. Provide an experience or project achievement statement.",
            "Contact details, headings, role titles, and dates are not rewritten as achievements.",
            None,
            [],
        )

    issues: List[str] = []
    weak_starter_matched = False
    chosen_verb: Optional[str] = None

    # 1. Check for weak/passive opener
    for pattern, explanation, _, _ in WEAK_STARTER_RULES:
        m = pattern.search(clean_text)
        if m:
            weak_starter_matched = True
            issues.append(explanation)
            break

    # 2. Check for metrics / quantified outcomes
    has_metrics = bool(
        re.search(
            r"(?:\b\d+(?:\.\d+)?%|\$\s*\d+(?:,\d+)*(?:\.\d+)?[kmb]?|\b\d+\s*(?:k|million|users|customers|requests|transactions|percent|hours|days|weeks|teams?)\b)",
            clean_text,
            re.IGNORECASE,
        )
    )
    if not has_metrics:
        issues.append("Lacks quantifiable business impact or measurable results (e.g., latency reduction, users served, percentage improvement).")

    # 3. Check for technical skills / tools in the bullet
    detected_skills: List[str] = []
    clean_lower = clean_text.lower()
    for canonical in DEFAULT_SYNONYM_MAP.keys():
        matched, _ = find_term_in_text(canonical, clean_lower)
        if matched:
            detected_skills.append(canonical)

    if not detected_skills:
        issues.append("Lacks mention of specific technical tools, frameworks, databases, or methodologies used.")

    # 4. Check for brevity
    words = clean_text.split()
    if len(words) < 8 and not weak_starter_matched:
        issues.append("Very brief; lacks sufficient detail about your role, methodology, or technical scope.")

    is_weak = len(issues) > 0

    # Report an action verb only when it is already present in the source.
    first_word = words[0].lower() if words else ""
    first_word_clean = re.sub(r"[^a-z]", "", first_word)
    if not chosen_verb:
        if first_word_clean in ACTION_VERBS:
            chosen_verb = words[0].capitalize()

    if not has_metrics:
        suggested_rewrite = f"{clean_text} [add verified result, if applicable]"
        what_to_add = (
            "Add only your actual contribution and a measurable outcome you can verify. "
            "Do not add tools, technologies, or results you did not use or achieve."
        )
    else:
        suggested_rewrite = clean_text
        what_to_add = (
            "Verify that every responsibility, tool, and metric in the original statement is accurate."
        )

    return is_weak, issues, suggested_rewrite, what_to_add, chosen_verb, detected_skills


def improve_single_bullet(
    bullet_text: str,
    target_skills: Optional[List[str]] = None,
) -> BulletImprovementResponse:
    """
    Endpoint helper for improving an individual arbitrary resume bullet point.
    """
    if not bullet_text or not bullet_text.strip():
        return BulletImprovementResponse(
            original_text=bullet_text,
            is_weak=True,
            issues=["Input bullet point is empty."],
            suggested_rewrite="No achievement rewrite generated. Provide an experience or project achievement statement.",
            what_to_add="Only submit a statement describing work you actually performed.",
            recommended_action_verbs=[],
        )

    is_weak, issues, rewrite, what_to_add, chosen_verb, _ = analyze_bullet_point(
        bullet_text=bullet_text,
        target_skills=target_skills,
    )

    recommended_verbs = [chosen_verb] if chosen_verb else []
    for cat in CATEGORIZED_ACTION_VERBS:
        for v in cat.verbs[:2]:
            if v not in recommended_verbs:
                recommended_verbs.append(v)
            if len(recommended_verbs) >= 4:
                break
        if len(recommended_verbs) >= 4:
            break

    return BulletImprovementResponse(
        original_text=bullet_text.strip(),
        is_weak=is_weak,
        issues=issues if issues else ["No major structural weaknesses detected."],
        suggested_rewrite=rewrite,
        what_to_add=what_to_add,
        recommended_action_verbs=recommended_verbs,
    )


def generate_improvement_assistant(
    parsed_job: Dict[str, Any],
    parsed_resume: Dict[str, Any],
    norm_resume_text: str,
    norm_job_text: str,
    matched_reqs: List[RequirementMatch],
    missing_reqs: List[MissingRequirement],
) -> ResumeImprovementAssistant:
    """
    Constructs the complete Resume Improvement Assistant payload.
    Deterministic, rule-based, local, and grounded in the candidate's actual document.
    """
    # =========================================================================
    # 1. Resume Strengths
    # =========================================================================
    strengths: List[StrengthItem] = []

    # Check sections
    sections = parsed_resume.get("sections", {})
    standard_secs = [s for s in ["experience", "skills", "education"] if s in sections]
    if len(standard_secs) == 3:
        strengths.append(
            StrengthItem(
                title="Well-Structured Core Sections",
                description="Your resume features clear, standard headings for Experience, Skills, and Education, which facilitates parsing across ATS screening filters.",
                category="structure",
            )
        )
    elif len(standard_secs) >= 2:
        strengths.append(
            StrengthItem(
                title="Established Section Hierarchy",
                description=f"Identified clear sections for {', '.join(standard_secs).title()}, organizing your career timeline effectively.",
                category="structure",
            )
        )

    # Check action verbs
    action_verbs = parsed_resume.get("action_verbs", [])
    if len(action_verbs) >= 4:
        sample_verbs = ", ".join([v.capitalize() for v in action_verbs[:4]])
        strengths.append(
            StrengthItem(
                title="Strong Action Verb Usage",
                description=f"Detected {len(action_verbs)} assertive action verbs (e.g., {sample_verbs}), demonstrating active ownership of accomplishments.",
                category="clarity",
            )
        )
    elif len(action_verbs) > 0:
        sample_verbs = ", ".join([v.capitalize() for v in action_verbs[:2]])
        strengths.append(
            StrengthItem(
                title="Active Voice Foundation",
                description=f"Used positive active verbs including {sample_verbs} to describe responsibilities.",
                category="clarity",
            )
        )

    # Check metrics
    metrics = parsed_resume.get("metrics_found", [])
    if len(metrics) >= 2:
        sample_metrics = ", ".join(metrics[:3])
        strengths.append(
            StrengthItem(
                title="Evidence of Quantifiable Impact",
                description=f"Included {len(metrics)} measurable performance indicators ({sample_metrics}), giving tangible credibility to your achievements.",
                category="metrics",
            )
        )

    # Check matched technical skills
    job_skills = set(parsed_job.get("job_skills", []))
    resume_skills = set(parsed_resume.get("skills_found", []))
    matched_skills_list = sorted(list(job_skills.intersection(resume_skills)))

    if matched_skills_list:
        sample_matched = ", ".join(matched_skills_list[:4])
        strengths.append(
            StrengthItem(
                title="Core Technical Alignment",
                description=f"Directly matched {len(matched_skills_list)} key competencies requested in the job description: {sample_matched}.",
                category="skills",
            )
        )

    # Check academic qualifications
    degrees = parsed_resume.get("degrees_found", [])
    if degrees:
        strengths.append(
            StrengthItem(
                title="Clear Academic Foundation",
                description=f"Identified recognized educational credentials ({', '.join(degrees).title()}), meeting baseline qualification requirements.",
                category="qualifications",
            )
        )

    # Fallback to ensure at least 2 strengths
    if len(strengths) < 2:
        word_count = parsed_resume.get("word_count", 0)
        strengths.append(
            StrengthItem(
                title="Concise Document Length",
                description=f"Document contains {word_count} words, presenting an approachable overview for initial screening.",
                category="formatting",
            )
        )

    # =========================================================================
    # 2. Weak or Vague Resume Bullet Points & Rewrites
    # =========================================================================
    candidate_bullets = parsed_resume.get("achievement_bullets")
    if candidate_bullets is None:
        candidate_bullets = extract_candidate_bullets(sections)
    bullet_improvements: List[BulletImprovement] = []
    bullet_counter = 1

    for raw_bullet in candidate_bullets:
        is_weak, issues, rewrite, what_to_add, chosen_verb, det_skills = analyze_bullet_point(
            bullet_text=raw_bullet,
            target_skills=matched_skills_list,
        )
        if is_weak:
            bullet_improvements.append(
                BulletImprovement(
                    id=f"bi-{bullet_counter}",
                    original_text=raw_bullet,
                    issue="; ".join(issues),
                    suggested_rewrite=rewrite,
                    what_to_add=what_to_add,
                    action_verb=chosen_verb,
                    detected_skills=det_skills,
                )
            )
            bullet_counter += 1
            if len(bullet_improvements) >= 6:
                break

    # If no weak bullets were found in the resume, provide a foundational model
    if not bullet_improvements and candidate_bullets:
        # Take the first bullet and provide an optimization model
        sample_b = candidate_bullets[0]
        _, _, rewrite, what_to_add, chosen_verb, det_skills = analyze_bullet_point(sample_b, matched_skills_list)
        bullet_improvements.append(
            BulletImprovement(
                id="bi-1",
                original_text=sample_b,
                issue="Strong foundation; can be further elevated by tightening technical methods and ensuring verified metrics are front-and-center.",
                suggested_rewrite=rewrite,
                what_to_add=what_to_add,
                action_verb=chosen_verb,
                detected_skills=det_skills,
            )
        )

    # =========================================================================
    # 3. Job-Description Skill Alignment
    # =========================================================================
    missing_skills_list = sorted(list(job_skills.difference(resume_skills)))

    # Identify weakly evidenced skills: mentioned in skills section or general text,
    # but not found in any experience bullet points
    exp_text = sections.get("experience", "").lower()
    weakly_evidenced: List[str] = []
    for skill in matched_skills_list:
        if skill not in exp_text:
            weakly_evidenced.append(skill)

    skill_alignment = JobSkillAlignment(
        matched_skills=matched_skills_list,
        missing_from_resume_skills=missing_skills_list,
        weakly_evidenced_skills=weakly_evidenced,
        ethical_guidance=(
            "Important: Only add skills and experiences you truthfully possess. "
            "For genuine skill gaps, highlight transferable background or pursue targeted learning "
            "rather than misrepresenting qualifications."
        ),
    )

    # =========================================================================
    # 4. Recommended Action Verbs
    # =========================================================================
    recommended_verbs = CATEGORIZED_ACTION_VERBS

    # =========================================================================
    # 5. Suggestions for Adding Measurable Achievements
    # =========================================================================
    metric_guidance = METRIC_GUIDANCE_ITEMS

    # =========================================================================
    # 6. Prioritized Improvement Checklist
    # =========================================================================
    checklist: List[ChecklistItem] = []
    check_counter = 1

    # Check 1: Missing core skills
    if missing_skills_list:
        sample_missing = ", ".join(missing_skills_list[:3])
        checklist.append(
            ChecklistItem(
                id=f"chk-{check_counter}",
                title=f"Review missing job skills: {sample_missing}",
                description=(
                    f"Evaluate whether you have hands-on experience with {sample_missing}. "
                    "If you do, integrate them into your Work Experience with concrete project context. "
                    "If you do not, do not fabricate; emphasize adjacent transferable strengths."
                ),
                priority="high",
                completed=False,
            )
        )
        check_counter += 1

    # Check 2: Weak bullet points
    if bullet_improvements:
        checklist.append(
            ChecklistItem(
                id=f"chk-{check_counter}",
                title=f"Upgrade {len(bullet_improvements)} weak resume bullet points",
                description=(
                    "Convert passive phrases (e.g., 'worked on', 'assisted with') into assertive "
                    "Action + Task + Method + [Verified Result] statements."
                ),
                priority="high",
                completed=False,
            )
        )
        check_counter += 1

    # Check 3: Quantifiable metrics
    if len(metrics) < 2:
        checklist.append(
            ChecklistItem(
                id=f"chk-{check_counter}",
                title="Incorporate verified quantifiable achievements",
                description=(
                    "Add at least 2 measurable results (e.g., % latency drop, team size, users supported, or hours saved) "
                    "to provide concrete proof of your impact."
                ),
                priority="high",
                completed=False,
            )
        )
        check_counter += 1

    # Check 4: Weakly evidenced skills
    if weakly_evidenced:
        sample_weak = ", ".join(weakly_evidenced[:3])
        checklist.append(
            ChecklistItem(
                id=f"chk-{check_counter}",
                title=f"Back up mentioned skills ({sample_weak}) with project proof",
                description=(
                    f"You listed {sample_weak} in your skills section. Add specific bullet points "
                    "under Work Experience showing how you deployed or leveraged these tools in production."
                ),
                priority="medium",
                completed=False,
            )
        )
        check_counter += 1

    # Check 5: Action verb diversity
    checklist.append(
        ChecklistItem(
            id=f"chk-{check_counter}",
            title="Diversify action verbs across experience bullets",
            description=(
                "Ensure every bullet begins with a distinct, past-tense power verb (e.g., 'Architected', 'Modernized', 'Automated') "
                "avoiding repetitive verbs."
            ),
            priority="medium",
            completed=False,
        )
    )
    check_counter += 1

    # Check 6: Section clarity & formatting
    checklist.append(
        ChecklistItem(
            id=f"chk-{check_counter}",
            title="Perform final ATS readability & formatting check",
            description=(
                "Confirm that your document uses standard single-column formatting, clear section headings, "
                "and clean bullet points without complex graphic tables or text boxes."
            ),
            priority="low",
            completed=False,
        )
    )

    return ResumeImprovementAssistant(
        strengths=strengths,
        bullet_improvements=bullet_improvements,
        skill_alignment=skill_alignment,
        recommended_verbs=recommended_verbs,
        metric_guidance=metric_guidance,
        improvement_checklist=checklist,
    )
