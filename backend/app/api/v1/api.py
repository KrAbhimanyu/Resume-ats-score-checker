from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    analyze,
    assistant,
    builder,
    business,
    career,
    career_coach,
    company_intelligence,
    learning_academy,
    personal_branding,
    premium_career,
    salary_intelligence,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(analyze.router, tags=["Analysis"])
api_router.include_router(assistant.router, tags=["Resume Assistant"])
api_router.include_router(builder.router, prefix="/builder", tags=["Targeted Resume Builder"])
api_router.include_router(business.router, prefix="/career")
api_router.include_router(career.router, prefix="/career", tags=["Career Platform"])
api_router.include_router(career_coach.router, prefix="/career", tags=["Career Coach"])
api_router.include_router(company_intelligence.router, prefix="/career")
api_router.include_router(learning_academy.router, prefix="/career/academy")
api_router.include_router(personal_branding.router, prefix="/career")
api_router.include_router(salary_intelligence.router, prefix="/career")
api_router.include_router(premium_career.router, prefix="/career")
