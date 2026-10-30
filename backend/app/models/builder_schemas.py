from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class TargetMode(str, Enum):
    FAANG_BIG_TECH = "faang_big_tech"
    ANY_COMPANY = "any_company"


class ContactInfo(BaseModel):
    full_name: str = Field(default="Candidate Name", description="Applicant full name")
    email: Optional[str] = Field(default=None, description="Contact email address")
    phone: Optional[str] = Field(default=None, description="Contact telephone number")
    location: Optional[str] = Field(default=None, description="City, State / Country or Remote")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL or handle")
    github: Optional[str] = Field(default=None, description="GitHub or portfolio URL")


class ExperienceItem(BaseModel):
    id: str = Field(default="", description="Unique identifier for experience entry")
    title: str = Field(..., description="Job title / role")
    company: str = Field(..., description="Company or organization name")
    location: Optional[str] = Field(default=None, description="Location or Remote")
    start_date: Optional[str] = Field(default=None, description="Employment start date")
    end_date: Optional[str] = Field(default="Present", description="Employment end date")
    bullets: List[str] = Field(default_factory=list, description="Bullet accomplishment points")


class ProjectItem(BaseModel):
    id: str = Field(default="", description="Unique identifier for project entry")
    title: str = Field(..., description="Project title")
    technologies: List[str] = Field(default_factory=list, description="Key technologies used")
    bullets: List[str] = Field(default_factory=list, description="Project accomplishment bullets")


class EducationItem(BaseModel):
    id: str = Field(default="", description="Unique identifier for education entry")
    degree: str = Field(..., description="Degree or qualification name")
    institution: str = Field(..., description="University, college or school")
    location: Optional[str] = Field(default=None, description="Location")
    graduation_date: Optional[str] = Field(default=None, description="Graduation year / date")
    details: Optional[str] = Field(default=None, description="Relevant coursework, honors, GPA")


class StructuredResume(BaseModel):
    """Clean structured resume schema suitable for rendering, editing, and exporting."""
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = Field(default="", description="Professional summary paragraph")
    skills: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "Languages": [],
            "Frameworks & Libraries": [],
            "Cloud, Tools & Databases": [],
            "Testing & Methodologies": [],
        },
        description="Categorized technical and domain skills",
    )
    experience: List[ExperienceItem] = Field(default_factory=list, description="Work history entries")
    projects: List[ProjectItem] = Field(default_factory=list, description="Key projects")
    education: List[EducationItem] = Field(default_factory=list, description="Academic qualifications")
    certifications: List[str] = Field(default_factory=list, description="Licenses and certifications")


class RequirementGapItem(BaseModel):
    """An individual skill or requirement evaluated against the target."""
    name: str = Field(..., description="Skill or requirement term")
    category: str = Field(default="skill", description="skill, tool, methodology, experience, qualification")
    status: str = Field(..., description="matched, missing, weakly_evidenced")
    reason: str = Field(..., description="Explanation of evaluation")
    evidence_source: str = Field(..., description="job_description, company_guidance, general_role_guidance")
    actionable_guidance: str = Field(..., description="Actionable recommendation for candidate")
    requires_user_confirmation: bool = Field(
        default=False,
        description="True if term is missing and candidate must confirm they truthfully possess it before adding",
    )


class ProposedChange(BaseModel):
    """A suggested upgrade comparing original text vs proposed targeted text."""
    id: str = Field(..., description="Unique change ID")
    section: str = Field(..., description="summary, skills, experience, projects, certifications, ordering")
    target_item_id: Optional[str] = Field(default=None, description="Identifier of experience/project item if applicable")
    bullet_index: Optional[int] = Field(default=None, description="Index of bullet within item if applicable")
    original_text: str = Field(..., description="Original text from resume")
    proposed_text: str = Field(..., description="Proposed targeted rewritten text")
    rationale: str = Field(..., description="Why this change improves alignment with the target")
    evidence_source: str = Field(..., description="Source of requirement (job_description, company, general_guidance)")
    what_to_verify: str = Field(..., description="What the candidate must verify or metric placeholder to fill")
    is_accepted: bool = Field(default=True, description="Whether the user accepts this proposed change")


class TargetedAnalysisRequest(BaseModel):
    """Request payload for analyzing against a target company and role."""
    resume_text: str = Field(..., min_length=30, description="Extracted resume text")
    target_mode: TargetMode = Field(default=TargetMode.FAANG_BIG_TECH)
    company_name: str = Field(..., min_length=1, max_length=100, description="Target company name")
    industry: Optional[str] = Field(default=None, description="Target industry (e.g. Fintech, Healthcare, E-commerce)")
    job_title: str = Field(..., min_length=1, max_length=100, description="Target job title / role")
    job_description: Optional[str] = Field(default="", description="Optional actual job description text")
    sections_to_improve: List[str] = Field(
        default_factory=lambda: ["summary", "skills", "experience", "projects"],
        description="Sections selected for improvement",
    )


class TargetedAnalysisResponse(BaseModel):
    """Complete targeted upgrade gap analysis, proposed rewrites, and draft resume."""
    target_mode: str
    company_name: str
    industry: Optional[str] = None
    job_title: str
    has_job_description: bool
    guidance_source: str
    summary_overview: str
    matched_skills: List[RequirementGapItem] = Field(default_factory=list)
    missing_requirements: List[RequirementGapItem] = Field(default_factory=list)
    weakly_evidenced: List[RequirementGapItem] = Field(default_factory=list)
    structure_feedback: List[str] = Field(default_factory=list)
    prioritized_improvements: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_changes: List[ProposedChange] = Field(default_factory=list)
    draft_resume: StructuredResume
    disclaimer: str = Field(
        default=(
            "Company-specific guidance is compiled from general public engineering culture insights and heuristic best practices. "
            "It does not represent confidential employer hiring algorithms, proprietary scoring systems, or official company guarantees. "
            "All recommendations should be verified by the candidate for truthfulness."
        )
    )


class ExportResumeRequest(BaseModel):
    """Request payload for exporting a structured resume."""
    format: str = Field(default="pdf", description="pdf or docx")
    resume: StructuredResume
    filename: Optional[str] = Field(default="targeted_resume")

