from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class LearningAssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: Dict[str, str] = Field(..., min_length=1, max_length=20)


class LearningRoadmapInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_role: str = Field(..., min_length=2, max_length=160)
    skills_to_develop: List[str] = Field(default_factory=list, max_length=30)
    track_ids: List[str] = Field(default_factory=list, max_length=8)
    goal: str = Field(default="", max_length=2000)


class LearningRoadmapEditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_role: str = Field(..., min_length=2, max_length=160)
    skills_to_develop: List[str] = Field(default_factory=list, max_length=30)
    track_ids: List[str] = Field(..., min_length=1, max_length=8)
    goal: str = Field(default="", max_length=2000)


class LearningAssistantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=2, max_length=4000)
    track_id: Optional[str] = Field(default=None, max_length=80)


class CodingExerciseSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=12_000)


class LearningProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=160)
    description: str = Field(..., min_length=40, max_length=12_000)
    skills: List[str] = Field(default_factory=list, max_length=20)
    project_url: Optional[HttpUrl] = None


class LearningEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(..., min_length=1, max_length=100)
    evidence_type: str = Field(..., pattern="^(portfolio|project|external_certificate)$")
    description: str = Field(..., min_length=20, max_length=2000)
    evidence_url: Optional[HttpUrl] = None

    @model_validator(mode="after")
    def require_evidence_reference(self) -> "LearningEvidenceInput":
        if self.evidence_type in {"portfolio", "project"} and not self.evidence_url:
            raise ValueError("Provide a public portfolio or project URL for this evidence type.")
        return self
