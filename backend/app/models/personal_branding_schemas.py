from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


BrandTone = Literal[
    "professional",
    "technical",
    "executive",
    "entry_level",
    "experienced",
    "concise",
]

BrandContentType = Literal[
    "linkedin_headline",
    "linkedin_about",
    "linkedin_experience",
    "linkedin_skills",
    "profile_optimization",
    "branding_guidance",
    "professional_bio",
    "portfolio_project",
    "linkedin_post",
]


class PersonalBrandProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personal_name: str = Field(default="", max_length=120)
    current_role: str = Field(default="", max_length=160)
    target_roles: List[str] = Field(default_factory=list, max_length=15)
    industry: str = Field(default="", max_length=120)
    skills: List[str] = Field(default_factory=list, max_length=60)
    about: str = Field(default="", max_length=5000)
    experience: List[str] = Field(default_factory=list, max_length=20)
    projects: List[str] = Field(default_factory=list, max_length=20)
    linkedin_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    github_username: str = Field(default="", max_length=39, pattern=r"^$|^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
    tone: BrandTone = "professional"

    @field_validator("target_roles", "skills", "experience", "projects")
    @classmethod
    def bound_profile_items(cls, values: List[str]) -> List[str]:
        if any(len(value) > 3000 for value in values):
            raise ValueError("Each profile item must be no more than 3000 characters.")
        return values


class PersonalBrandGenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: BrandContentType
    tone: BrandTone = "professional"
    target_role: str = Field(default="", max_length=160)
    platform: str = Field(default="", max_length=80)
    job_description: str = Field(default="", max_length=12000)
    source_text: str = Field(default="", max_length=12000)
    custom_instructions: str = Field(default="", max_length=2000)


class PersonalBrandVersionEditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=160)
    content: str = Field(..., min_length=1, max_length=20000)

    @field_validator("title")
    @classmethod
    def require_nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Version name cannot be blank.")
        return value

    @field_validator("content")
    @classmethod
    def require_nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Version content cannot be blank.")
        return value


class PersonalBrandVersionCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: BrandContentType
    title: str = Field(..., min_length=1, max_length=160)
    tone: BrandTone = "professional"
    content: str = Field(..., min_length=1, max_length=20000)

    @field_validator("title")
    @classmethod
    def require_nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Version name cannot be blank.")
        return value

    @field_validator("content")
    @classmethod
    def require_nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Version content cannot be blank.")
        return value


class PersonalBrandAnalyticsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["linkedin", "github", "portfolio"]
    activity_date: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    title: str = Field(..., min_length=1, max_length=160)
    impressions: int = Field(default=0, ge=0, le=1_000_000_000)
    reactions: int = Field(default=0, ge=0, le=1_000_000_000)
    comments: int = Field(default=0, ge=0, le=1_000_000_000)
    clicks: int = Field(default=0, ge=0, le=1_000_000_000)
    followers: int = Field(default=0, ge=0, le=1_000_000_000)

    @field_validator("title")
    @classmethod
    def require_nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Activity name cannot be blank.")
        return value


class PortfolioExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_approved_profile: bool = Field(..., strict=True)
    theme: Literal["minimal", "classic", "midnight"] = "minimal"
    accent_color: str = Field(default="#4F46E5", pattern=r"^#[0-9A-Fa-f]{6}$")
