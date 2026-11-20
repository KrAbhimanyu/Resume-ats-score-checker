import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.config import settings
from app.core.errors import ATSCheckerException, ats_exception_handler
from app.core.logging_config import logger
from app.core.security import UPLOAD_REQUEST_PATHS, UploadBodyLimitMiddleware
from app.db.database import migrate
from app.api.v1.endpoints.career import reminder_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for startup and shutdown."""
    migrate()
    reminder_task = asyncio.create_task(reminder_worker())
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (Debug: {settings.DEBUG})")
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Explainable ATS analysis and authenticated job intelligence, matching, and application management. "
        "Career-platform scores use transparent deterministic resume evidence; job listings are sourced from configured providers."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    UploadBodyLimitMiddleware,
    maximum_body_bytes=settings.MAX_UPLOAD_SIZE_BYTES + 256 * 1024,
    upload_paths=UPLOAD_REQUEST_PATHS,
)

# ------------------------------------------------------------------------------
# Security: Explicit CORS Configuration
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Error Handlers
# ------------------------------------------------------------------------------
app.add_exception_handler(ATSCheckerException, ats_exception_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Avoid logging exception messages that may contain document-derived data.
    logger.error(f"Unhandled server error: {exc.__class__.__name__}")
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
