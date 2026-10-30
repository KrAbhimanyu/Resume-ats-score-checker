from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Current service health status")
    version: str = Field(..., description="API semantic version")
    timestamp: str = Field(..., description="Server timestamp")
    service: str = Field(default="Resume ATS Score Checker", description="Service identifier")


class CategoryScore(BaseModel):
    """Detailed score breakdown for a specific evaluation category."""
    category_id: str = Field(..., description="Machine-readable category identifier")
    category_name: str = Field(..., description="Human-readable category label")
    score: float = Field(..., ge=0.0, description="Points earned in this category")
    max_score: float = Field(..., gt=0.0, description="Maximum possible points for this category")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Normalized score percentage")
    explanation: str = Field(..., description="Transparent breakdown of how this score was calculated")
    details: Dict[str, Any] = Field(default_factory=dict, description="Granular breakdown metrics")


class RequirementMatch(BaseModel):
    """A requirement from the job description matched in the resume."""
    requirement: str = Field(..., description="Requirement phrase or skill from job description")
    category: str = Field(..., description="Requirement classification: skill, experience, education, or keyword")
    matched_terms: List[str] = Field(default_factory=list, description="Keywords or synonyms detected in resume")
    evidence_strength: str = Field(..., description="Strength of evidence: strong, moderate, or weak")
    is_mandatory: bool = Field(default=False, description="Whether requirement was identified as mandatory")


class MissingRequirement(BaseModel):
    """A job requirement not found or weakly evidenced in the resume."""
    requirement: str = Field(..., description="Unmatched requirement phrase or skill")
    category: str = Field(..., description="Requirement classification: skill, experience, education, or keyword")
    importance: str = Field(..., description="Importance level: mandatory, preferred, or general")
    reason: str = Field(..., description="Explanation why requirement is missing or weak")
    is_evidenced_elsewhere: bool = Field(
        default=False,
        description="True if term or synonym was seen in general text but lacks strong context/experience evidence",
    )


class Recommendation(BaseModel):
    """Actionable improvement recommendation grounded in resume and job description."""
    id: str = Field(..., description="Unique recommendation ID")
    category: str = Field(..., description="Target category: keywords, skills, experience, education, formatting")
    title: str = Field(..., description="Short actionable headline")
    description: str = Field(..., description="Detailed, contextual guidance on how to improve")
    action_type: str = Field(
        ...,
        description="Action type: add_missing_keyword, strengthen_evidence, improve_formatting, add_metrics, education_clarity",
    )
    priority: str = Field(..., description="Priority: high, medium, or low")


class DocumentMetadata(BaseModel):
    """Extracted resume document metadata and parsing status."""
    filename: str = Field(..., description="Original filename uploaded")
    file_type: str = Field(..., description="Normalized document type (.pdf or .docx)")
    file_size_bytes: int = Field(..., description="File size in bytes")
    character_count: int = Field(..., description="Total readable characters extracted")
    word_count: int = Field(..., description="Total word count extracted")
    extraction_warnings: List[str] = Field(default_factory=list, description="Parser warnings (e.g., scanned PDF/OCR hint)")


# =============================================================================
# Resume Improvement Assistant Schemas
# =============================================================================

class StrengthItem(BaseModel):
    """Identified strength in candidate's existing resume."""
    title: str = Field(..., description="Short title of the identified strength")
    description: str = Field(..., description="Contextual observation of what is working well")
    category: str = Field(..., description="Category: formatting, skills, metrics, structure, clarity")


class BulletImprovement(BaseModel):
    """Personalized improvement for a weak or vague resume bullet point."""
    id: str = Field(..., description="Unique bullet improvement identifier")
    original_text: str = Field(..., description="Original bullet text extracted from resume")
    issue: str = Field(..., description="Explanation of why this bullet point could be improved")
    suggested_rewrite: str = Field(
        ...,
        description="Stronger rewritten version following Action + Task + Method + [Measurable Result Placeholder]",
    )
    what_to_add: str = Field(..., description="Specific verified information or metric the candidate should add")
    action_verb: Optional[str] = Field(default=None, description="Recommended active verb for this bullet")
    detected_skills: List[str] = Field(default_factory=list, description="Skills detected in this bullet")


class JobSkillAlignment(BaseModel):
    """Job-description skill alignment analysis."""
    matched_skills: List[str] = Field(default_factory=list, description="Skills found in both resume and job description")
    missing_from_resume_skills: List[str] = Field(
        default_factory=list,
        description="Skills required or preferred in job description but not found in resume",
    )
    weakly_evidenced_skills: List[str] = Field(
        default_factory=list,
        description="Skills mentioned in resume without active bullet context or proof",
    )
    ethical_guidance: str = Field(
        default=(
            "Important: Only add skills and experiences you truthfully possess. "
            "For genuine skill gaps, highlight transferable background or pursue targeted learning "
            "rather than misrepresenting qualifications."
        ),
        description="Ethical guidance clearly distinguishing missing from resume vs skill not possessed",
    )


class ActionVerbCategory(BaseModel):
    """Group of strong action verbs categorized by impact type."""
    category_name: str = Field(..., description="e.g. Technical & Engineering, Leadership, Optimization")
    verbs: List[str] = Field(..., description="List of strong action verbs in this category")


class MetricGuidanceItem(BaseModel):
    """Prompting question and pattern to help candidates unearth verified metrics."""
    metric_type: str = Field(..., description="e.g., Scale & Traffic, Efficiency & Time, Quality & Reliability")
    guiding_question: str = Field(..., description="Question to prompt candidate's real memory of verified outcomes")
    example_pattern: str = Field(..., description="Example format with [add verified result] placeholder")


class ChecklistItem(BaseModel):
    """Prioritized resume improvement checklist item."""
    id: str = Field(..., description="Unique checklist identifier")
    title: str = Field(..., description="Actionable checklist title")
    description: str = Field(..., description="Specific guidance on completing this improvement")
    priority: str = Field(..., description="Priority: high, medium, or low")
    completed: bool = Field(default=False, description="Whether item has been addressed")


class ResumeImprovementAssistant(BaseModel):
    """Complete personalized resume improvement assistant payload."""
    strengths: List[StrengthItem] = Field(default_factory=list, description="Identified resume strengths")
    bullet_improvements: List[BulletImprovement] = Field(
        default_factory=list,
        description="Weak or vague bullet points paired with actionable rewrite suggestions",
    )
    skill_alignment: JobSkillAlignment = Field(..., description="Job-description skill alignment analysis")
    recommended_verbs: List[ActionVerbCategory] = Field(
        default_factory=list,
        description="Curated action verbs categorized by impact type",
    )
    metric_guidance: List[MetricGuidanceItem] = Field(
        default_factory=list,
        description="Practical prompts and templates for adding verified metrics",
    )
    improvement_checklist: List[ChecklistItem] = Field(
        default_factory=list,
        description="Prioritized actionable improvement checklist",
    )


class BulletImprovementRequest(BaseModel):
    """Request payload to improve an arbitrary resume bullet point."""
    bullet_text: str = Field(..., min_length=3, max_length=1000, description="Resume bullet text to analyze and rewrite")
    target_skills: Optional[List[str]] = Field(
        default=None,
        description="Optional list of target skills or technologies to incorporate if applicable",
    )


class BulletImprovementResponse(BaseModel):
    """Response payload for on-the-fly bullet improvement."""
    original_text: str = Field(..., description="Original input text")
    is_weak: bool = Field(..., description="Whether the bullet point is weak or vague")
    issues: List[str] = Field(default_factory=list, description="Identified issues with the bullet point")
    suggested_rewrite: str = Field(..., description="Suggested rewrite following Action + Task + Method + [Metric]")
    what_to_add: str = Field(..., description="What specific information the user should add")
    recommended_action_verbs: List[str] = Field(default_factory=list, description="Recommended strong action verbs")


class AnalysisResponse(BaseModel):
    """Complete structured ATS analysis response."""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall match score from 0 to 100")
    score_label: str = Field(default="Estimated Resume–Job Match Score", description="Score label")
    match_tier: str = Field(..., description="Descriptive match tier (e.g. Exceptional, Strong, Good, Fair, Low)")
    summary: str = Field(..., description="High-level summary of analysis findings")
    category_scores: List[CategoryScore] = Field(..., description="Breakdown across all 5 evaluation categories")
    matched_requirements: List[RequirementMatch] = Field(..., description="Requirements successfully evidenced in resume")
    missing_requirements: List[MissingRequirement] = Field(..., description="Requirements missing or weakly evidenced")
    keywords_found: List[str] = Field(default_factory=list, description="Unique relevant keywords extracted from resume")
    recommendations: List[Recommendation] = Field(..., description="Targeted actionable suggestions for the candidate")
    document_metadata: DocumentMetadata = Field(..., description="Information on parsed resume document")
    improvement_assistant: Optional[ResumeImprovementAssistant] = Field(
        default=None,
        description="Personalized resume improvement suggestions, bullet rewrites, and skill alignment",
    )
    limitations_disclaimer: str = Field(
        default=(
            "This score is an Estimated Resume–Job Match Score calculated via deterministic heuristic analysis. "
            "It does not represent a proprietary employer ATS system, a hiring guarantee, or an interview prediction. "
            "Use these insights as practical guidelines to ensure your qualifications are clearly represented."
        ),
        description="Explicit disclaimer clarifying the heuristic nature and limitations of this scoring engine",
    )
