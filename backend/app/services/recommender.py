import uuid
from typing import List, Dict, Any
from app.models.schemas import Recommendation, MissingRequirement


def generate_recommendations(
    parsed_job: Dict[str, Any],
    parsed_resume: Dict[str, Any],
    missing_reqs: List[MissingRequirement],
    category_scores: List[Any],
) -> List[Recommendation]:
    """
    Generates grounded, actionable improvement recommendations tailored to the specific
    resume and job description. Distinguishes genuinely missing skills from weakly evidenced skills.
    Never encourages misrepresentation or dishonest qualification claims.
    """
    recommendations: List[Recommendation] = []
    rec_counter = 1

    # 1. Missing Core Skills (High Priority)
    genuinely_missing = [req for req in missing_reqs if req.category == "skill" and not req.is_evidenced_elsewhere]
    weakly_evidenced = [req for req in missing_reqs if req.category == "skill" and req.is_evidenced_elsewhere]

    if genuinely_missing:
        sample_skills = [m.requirement for m in genuinely_missing[:4]]
        skills_str = ", ".join(sample_skills)
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="skills",
                title=f"Address Missing Core Skills: {skills_str}",
                description=(
                    f"The job description highlights '{skills_str}' as essential qualifications. "
                    "If you have experience in these areas, clearly add them to your Skills section and "
                    "detail relevant projects. If you do not possess these skills, avoid fabricating them; "
                    "instead, highlight transferable background in closely related technologies."
                ),
                action_type="add_missing_keyword",
                priority="high",
            )
        )
        rec_counter += 1

    # 2. Weakly Evidenced Skills (Medium Priority)
    if weakly_evidenced:
        sample_weak = [m.requirement for m in weakly_evidenced[:3]]
        weak_str = ", ".join(sample_weak)
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="skills",
                title=f"Strengthen Context for Mentioned Skills: {weak_str}",
                description=(
                    f"The skills '{weak_str}' appear mentioned in your document, but lack detailed "
                    "accomplishment bullets in your Work Experience or Projects sections. Provide concrete "
                    "context demonstrating how you applied these tools and what outcomes you delivered."
                ),
                action_type="strengthen_evidence",
                priority="medium",
            )
        )
        rec_counter += 1

    # 3. Quantifiable Impact & Metrics
    metrics_count = len(parsed_resume.get("metrics_found", []))
    if metrics_count < 2:
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="experience",
                title="Add Quantifiable Metrics and Results",
                description=(
                    f"Your resume currently features {metrics_count} quantified achievements. "
                    "Recruiters and screening systems favor evidence-backed impact. Add specific numbers, "
                    "percentages, cost reductions, team sizes, or latency improvements to your bullet points "
                    "(e.g., 'Reduced API latency by 45%', 'Scaled service to handle 10k daily users')."
                ),
                action_type="add_metrics",
                priority="high" if metrics_count == 0 else "medium",
            )
        )
        rec_counter += 1

    # 4. Action Verbs & Active Voice
    verbs_count = len(parsed_resume.get("action_verbs", []))
    if verbs_count < 4:
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="formatting",
                title="Lead Experience Bullets with Strong Action Verbs",
                description=(
                    "Begin each bullet point with an assertive, past-tense action verb (e.g., 'Architected', "
                    "'Engineered', 'Streamlined', 'Delivered') instead of passive phrasing like 'Responsible for' "
                    "or 'Assisted with'."
                ),
                action_type="strengthen_evidence",
                priority="medium",
            )
        )
        rec_counter += 1

    # 5. Section Organization & Standard Headings
    if not parsed_resume.get("has_experience_section"):
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="formatting",
                title="Adopt Standard 'Work Experience' Section Header",
                description=(
                    "An explicit 'Work Experience' or 'Professional Experience' heading was not detected. "
                    "Use standard, clear section headers to ensure automated ATS parsers index your career history correctly."
                ),
                action_type="improve_formatting",
                priority="high",
            )
        )
        rec_counter += 1

    if not parsed_resume.get("has_education_section"):
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="education",
                title="Add Clear 'Education' Section",
                description=(
                    "Include a clearly formatted 'Education' section specifying your degree, major/field, "
                    "institution name, and graduation year."
                ),
                action_type="education_clarity",
                priority="medium",
            )
        )
        rec_counter += 1

    # 6. Resume Word Count / Depth
    word_count = parsed_resume.get("word_count", 0)
    if word_count < 250:
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="formatting",
                title="Expand Resume Depth and Detail",
                description=(
                    f"Your resume has only {word_count} words. Elaborate on your specific technical contributions, "
                    "technologies used, and problem-solving examples to give ATS parsers sufficient text to evaluate."
                ),
                action_type="improve_formatting",
                priority="medium",
            )
        )
        rec_counter += 1

    # If all is well, provide general polish recommendation
    if not recommendations:
        recommendations.append(
            Recommendation(
                id=f"rec-{rec_counter}",
                category="formatting",
                title="Strong Match: Fine-tune Target Tailoring",
                description=(
                    "Your resume strongly aligns with the target job description. Ensure that your most relevant "
                    "achievements and technical tools appear within the top half of your first page."
                ),
                action_type="strengthen_evidence",
                priority="low",
            )
        )

    return recommendations
