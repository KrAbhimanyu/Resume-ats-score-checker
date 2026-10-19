from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns current service status and API version.",
)
async def get_health() -> HealthResponse:
    """Return service status, version, and server timestamp."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        service=settings.APP_NAME,
    )
