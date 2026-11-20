from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.schemas import AnalysisResponse


ProgressStatus = Literal["pending", "in_progress", "completed", "failed", "skipped"]
SessionStatus = Literal["pending", "running", "completed", "failed"]


class AnalysisProgressEvent(BaseModel):
    event_id: int
    layer_id: str
    step_id: str
    status: ProgressStatus
    progress_percent: int = Field(default=0, ge=0, le=100)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AnalysisProgressStep(BaseModel):
    step_id: str
    label: str
    status: ProgressStatus = "pending"
    progress_percent: int = Field(default=0, ge=0, le=100)
    details: dict[str, Any] = Field(default_factory=dict)


class AnalysisProgressLayer(BaseModel):
    layer_id: str
    label: str
    status: ProgressStatus = "pending"
    steps: list[AnalysisProgressStep]


class AnalysisSessionSnapshot(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: str
    duration_ms: Optional[int] = None
    active_layer_id: Optional[str] = None
    layers: list[AnalysisProgressLayer]
    events: list[AnalysisProgressEvent]
    result: Optional[AnalysisResponse] = None
    report_available: bool = False
    error_code: Optional[str] = None


class AnalysisSessionCreated(BaseModel):
    session_id: str
    created_at: str
    layers: list[AnalysisProgressLayer]


class AnalysisSessionFailureRequest(BaseModel):
    error_code: str = "ANALYSIS_FAILED"
