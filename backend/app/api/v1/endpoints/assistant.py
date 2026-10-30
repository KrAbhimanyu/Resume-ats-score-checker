from fastapi import APIRouter, HTTPException, status
from app.models.schemas import BulletImprovementRequest, BulletImprovementResponse
from app.services.assistant import improve_single_bullet

router = APIRouter()


@router.post(
    "/improve-bullet",
    response_model=BulletImprovementResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze and improve a single resume bullet point",
    description="Evaluates an individual resume bullet point for passive tone, missing metrics, and vagueness, generating a grounded rewrite.",
)
async def improve_bullet_endpoint(
    payload: BulletImprovementRequest,
) -> BulletImprovementResponse:
    if not payload.bullet_text or not payload.bullet_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bullet text cannot be empty or whitespace.",
        )

    return improve_single_bullet(
        bullet_text=payload.bullet_text,
        target_skills=payload.target_skills,
    )

