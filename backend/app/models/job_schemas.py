import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Enter a valid email address.")
        return email


class LoginRequest(RegisterRequest):
    password: str = Field(..., min_length=1, max_length=256)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=20, max_length=8192)


class UserSummary(BaseModel):
    id: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserSummary


class ResumeProfileInput(BaseModel):
    title: str = Field(default="Primary resume", min_length=1, max_length=100)
    resume_text: str = Field(..., min_length=100, max_length=100_000)


class SearchPreferences(BaseModel):
    preferred_titles: List[str] = Field(default_factory=list, max_length=20)
    preferred_locations: List[str] = Field(default_factory=list, max_length=20)
    work_modes: List[str] = Field(default_factory=list, max_length=3)
    employment_types: List[str] = Field(default_factory=list, max_length=8)
    industries: List[str] = Field(default_factory=list, max_length=20)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    experience_level: Optional[str] = Field(
        default=None, pattern="^(fresher|entry_level|intermediate|experienced)$"
    )
    career_goals: str = Field(default="", max_length=2000)
    application_follow_up_days: int = Field(default=7, ge=1, le=60)
    interview_reminder_hours: List[int] = Field(default_factory=lambda: [24, 1], max_length=8)
    email_reminders: bool = False

    @field_validator("work_modes")
    @classmethod
    def validate_work_modes(cls, value: List[str]) -> List[str]:
        allowed = {"remote", "hybrid", "on_site"}
        invalid = set(value) - allowed
        if invalid:
            raise ValueError(f"Unsupported work mode: {sorted(invalid)[0]}")
        return value

    @field_validator("salary_currency")
    @classmethod
    def normalize_currency(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_salary_range(self) -> "SearchPreferences":
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        if (self.salary_min is not None or self.salary_max is not None) and not self.salary_currency:
            raise ValueError("Choose a salary currency when saving salary expectations.")
        return self

    @field_validator("interview_reminder_hours")
    @classmethod
    def validate_reminder_intervals(cls, value: List[int]) -> List[int]:
        if any(hour < 0 or hour > 720 for hour in value):
            raise ValueError("Interview reminder hours must be between 0 and 720.")
        return sorted(set(value), reverse=True)


class JobSearchRequest(BaseModel):
    query: str = Field(default="", max_length=160)
    country: str = Field(default="gb", min_length=2, max_length=2)
    location: str = Field(default="", max_length=120)
    company: str = Field(default="", max_length=120)
    remote_type: Optional[str] = Field(default=None, pattern="^(remote|hybrid|on_site)$")
    employment_type: Optional[str] = Field(default=None, max_length=80)
    experience_level: Optional[str] = Field(
        default=None, pattern="^(fresher|entry_level|intermediate|experienced)$"
    )
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    sort_by: str = Field(default="newest", pattern="^(newest|salary_high|salary_low|company)$")
    page: int = Field(default=1, ge=1, le=50)
    page_size: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobSearchRequest":
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        if (self.salary_min is not None or self.salary_max is not None) and not self.salary_currency:
            raise ValueError("Choose a salary currency when filtering by salary.")
        return self

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.lower()

    @field_validator("salary_currency")
    @classmethod
    def normalize_search_currency(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class JobDescriptionInput(BaseModel):
    description: str = Field(..., min_length=30, max_length=100_000)
    title: Optional[str] = Field(default=None, max_length=200)
    company_name: Optional[str] = Field(default=None, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    original_url: Optional[str] = Field(default=None, max_length=2048)
    source: str = Field(default="user_provided", max_length=40)

    @field_validator("original_url")
    @classmethod
    def validate_http_url(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("Job URL must use HTTP or HTTPS.")
        return value


class JobUrlInput(BaseModel):
    url: str = Field(..., min_length=9, max_length=2048)

    @field_validator("url")
    @classmethod
    def require_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("Only HTTPS URLs from imported authorized feeds can be analyzed.")
        return value


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(default="", max_length=200)
    country: Optional[str] = Field(default=None, max_length=2)
    remote_type: Optional[str] = Field(default=None, pattern="^(remote|hybrid|on_site)$")
    employment_type: Optional[str] = Field(default=None, max_length=80)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    salary_period: Optional[str] = Field(default=None, max_length=30)
    description: str = Field(..., min_length=30, max_length=100_000)
    original_url: Optional[str] = Field(default=None, max_length=2048)
    posted_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobCreate":
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        return self


class MatchRequest(BaseModel):
    job_id: Optional[str] = None
    description: Optional[str] = Field(default=None, min_length=30, max_length=100_000)
    resume_id: Optional[str] = None
    resume_text: Optional[str] = Field(default=None, min_length=100, max_length=100_000)

    @model_validator(mode="after")
    def validate_inputs(self) -> "MatchRequest":
        if not self.job_id and not self.description:
            raise ValueError("Provide either a saved job_id or a job description.")
        return self


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationCreate(BaseModel):
    job_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(default="", max_length=200)
    original_url: Optional[str] = Field(default=None, max_length=2048)
    description: str = Field(default="", max_length=100_000)
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_at: Optional[datetime] = None
    resume_version_id: Optional[str] = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=10_000)


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = Field(default=None, max_length=10_000)
    applied_at: Optional[datetime] = None
    resume_version_id: Optional[str] = Field(default=None, max_length=200)
    note: str = Field(default="", max_length=2000)

    model_config = ConfigDict(extra="forbid")


class InterviewInput(BaseModel):
    application_id: str
    scheduled_at: datetime
    timezone: str = Field(..., min_length=1, max_length=64)
    interview_type: str = Field(..., min_length=1, max_length=80)
    meeting_url: Optional[str] = Field(default=None, max_length=2048)
    interviewer_details: str = Field(default="", max_length=2000)
    preparation_notes: str = Field(default="", max_length=10_000)

    @field_validator("scheduled_at")
    @classmethod
    def require_aware_interview_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Interview time must include a timezone offset.")
        return value


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    interview_type: Optional[str] = Field(default=None, min_length=1, max_length=80)
    meeting_url: Optional[str] = Field(default=None, max_length=2048)
    interviewer_details: Optional[str] = Field(default=None, max_length=2000)
    preparation_notes: Optional[str] = Field(default=None, max_length=10_000)
    status: Optional[str] = Field(default=None, pattern="^(scheduled|completed|cancelled)$")


class ReminderInput(BaseModel):
    application_id: Optional[str] = None
    interview_id: Optional[str] = None
    job_id: Optional[str] = None
    reminder_type: str = Field(..., pattern="^(follow_up|interview|job_deadline|custom)$")
    due_at: datetime
    message: str = Field(..., min_length=1, max_length=1000)
    email_requested: bool = False

    @model_validator(mode="after")
    def validate_reference(self) -> "ReminderInput":
        references = [self.application_id, self.interview_id, self.job_id]
        if sum(reference is not None for reference in references) != 1:
            raise ValueError("A reminder must be linked to exactly one application, interview, or job.")
        if self.job_id and self.reminder_type != "job_deadline":
            raise ValueError("Job reminders must use the job_deadline type.")
        if self.reminder_type == "job_deadline" and not self.job_id:
            raise ValueError("A job deadline reminder must reference a job.")
        return self

    @field_validator("due_at")
    @classmethod
    def require_aware_reminder_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Reminder time must include a timezone offset.")
        return value


class ReminderUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(completed|snoozed)$")
    snoozed_until: Optional[datetime] = None

    @model_validator(mode="after")
    def require_snooze_date(self) -> "ReminderUpdate":
        if self.status == "snoozed" and self.snoozed_until is None:
            raise ValueError("Provide snoozed_until when snoozing a reminder.")
        return self

    @field_validator("snoozed_until")
    @classmethod
    def require_aware_snooze_time(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Snooze time must include a timezone offset.")
        return value


class CompanyInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry: Optional[str] = Field(default=None, max_length=120)
    website: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("Company website must use HTTP or HTTPS.")
        return value


class SkillProgressInput(BaseModel):
    status: str = Field(..., pattern="^(not_started|learning|practiced|proficient)$")
    note: str = Field(default="", max_length=1000)


class DraftRequest(BaseModel):
    application_id: str
    draft_type: str = Field(
        ...,
        pattern="^(application_assistant|cover_letter|application_email|recruiter_follow_up|interview_follow_up|follow_up)$",
    )
    instructions: str = Field(default="", max_length=2000)


class ApplicationDraftSaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_type: str = Field(
        ...,
        pattern="^(application_assistant|cover_letter|application_email|recruiter_follow_up|interview_follow_up)$",
    )
    subject: str = Field(default="", max_length=300)
    body: str = Field(..., min_length=1, max_length=20_000)


class TailoringChangeInput(BaseModel):
    id: str = Field(..., min_length=1, max_length=80)
    is_accepted: bool
    proposed_text: Optional[str] = Field(default=None, max_length=4000)


class TailoringApprovalRequest(BaseModel):
    changes: List[TailoringChangeInput] = Field(..., min_length=1, max_length=100)


class ApiMessage(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None
