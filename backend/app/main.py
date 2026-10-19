from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.config import settings
from app.core.errors import ATSCheckerException, ats_exception_handler
from app.core.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (Debug: {settings.DEBUG})")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-oriented API for calculating explainable, deterministic ATS Resume match scores. "
        "Evaluates keyword coverage, skills alignment, experience metrics, education, and formatting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# Security: Explicit CORS Configuration
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Error Handlers
# ------------------------------------------------------------------------------
app.add_exception_handler(ATSCheckerException, ats_exception_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the error safely without including request body/resume text
    logger.error(f"Unhandled server error: {exc.__class__.__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during processing. Please try again.",
            }
        },
    )


# ------------------------------------------------------------------------------
# Register V1 Endpoints
# ------------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect or information on root."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_PREFIX}/health",
    }
