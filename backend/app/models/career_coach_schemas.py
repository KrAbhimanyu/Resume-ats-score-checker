from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CoachConsentInput(BaseModel):
    enabled: bool


class CareerGoalInput(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    target_role: str = Field(..., min_length=2, max_length=160)
    goal_type: str = Field(..., pattern="^(short_term|long_term)$")
    target_date: Optional[date] = None
    status: str = Field(default="active", pattern="^(active|completed|paused|archived)$")
    progress: float = Field(default=0, ge=0, le=100)


class CareerGoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    target_role: Optional[str] = Field(default=None, min_length=2, max_length=160)
    goal_type: Optional[str] = Field(default=None, pattern="^(short_term|long_term)$")
    target_date: Optional[date] = None
    status: Optional[str] = Field(default=None, pattern="^(active|completed|paused|archived)$")
    progress: Optional[float] = Field(default=None, ge=0, le=100)


class CareerRoadmapRequest(BaseModel):
    resume_id: Optional[str] = Field(default=None, max_length=80)
    goal_id: Optional[str] = Field(default=None, max_length=80)
    target_role: str = Field(..., min_length=2, max_length=160)
    current_role: str = Field(default="", max_length=160)
    industry: str = Field(default="", max_length=120)
    experience_level: str = Field(default="", max_length=80)
    interests: List[str] = Field(default_factory=list, max_length=15)
    job_description: str = Field(default="", max_length=20_000)
    customization: str = Field(default="", max_length=2000)


class CareerChatInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    roadmap_id: Optional[str] = Field(default=None, max_length=80)


class CareerAction(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    detail: str = Field(..., min_length=2, max_length=1200)
    timeframe: str = Field(..., min_length=1, max_length=80)
    category: str = Field(..., min_length=1, max_length=80)
    priority: str = Field(..., pattern="^(high|medium|low)$")


class CareerPath(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    rationale: str = Field(..., min_length=2, max_length=1000)
    transition_steps: List[str] = Field(default_factory=list, max_length=8)


class CareerMilestoneSuggestion(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    description: str = Field(..., min_length=2, max_length=1200)
    weeks_from_now: int = Field(..., ge=0, le=104)


class CareerRoadmapContent(BaseModel):
    summary: str = Field(..., min_length=2, max_length=2000)
    career_paths: List[CareerPath] = Field(default_factory=list, max_length=6)
    next_roles: List[str] = Field(default_factory=list, max_length=8)
    growth_insights: List[str] = Field(default_factory=list, max_length=8)
    strengths: List[str] = Field(default_factory=list, max_length=12)
    development_areas: List[str] = Field(default_factory=list, max_length=12)
    action_plan: List[CareerAction] = Field(default_factory=list, max_length=20)
    daily_tasks: List[str] = Field(default_factory=list, max_length=14)
    milestones: List[CareerMilestoneSuggestion] = Field(default_factory=list, max_length=24)


class CareerRoadmapUpdate(CareerRoadmapContent):
    pass


class CareerMilestoneInput(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    description: str = Field(default="", max_length=1200)
    due_date: Optional[date] = None


class CareerMilestoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    description: Optional[str] = Field(default=None, max_length=1200)
    due_date: Optional[date] = None
    status: Optional[str] = Field(default=None, pattern="^(planned|in_progress|completed)$")
