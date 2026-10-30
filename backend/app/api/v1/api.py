from fastapi import APIRouter
from app.api.v1.endpoints import health, analyze, assistant, builder

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(analyze.router, tags=["Analysis"])
api_router.include_router(assistant.router, tags=["Resume Assistant"])
api_router.include_router(builder.router, prefix="/builder", tags=["Targeted Resume Builder"])
