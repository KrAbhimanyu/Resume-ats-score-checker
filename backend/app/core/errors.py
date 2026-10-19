from fastapi import Request, status
from fastapi.responses import JSONResponse


class ATSCheckerException(Exception):
    """Base exception for ATS Checker domain errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "BAD_REQUEST", details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class FileValidationError(ATSCheckerException):
    """Raised when file extension, MIME type, or signature check fails."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILE_TYPE",
            details=details,
        )


class FileSizeExceededError(ATSCheckerException):
    """Raised when uploaded file exceeds size limits."""

    def __init__(self, message: str, max_size_bytes: int, actual_size_bytes: int):
        super().__init__(
            message=message,
            status_code=413,
            error_code="FILE_TOO_LARGE",
            details={"max_size_bytes": max_size_bytes, "actual_size_bytes": actual_size_bytes},
        )


class ExtractionError(ATSCheckerException):
    """Raised when document cannot be extracted (corrupted, password protected)."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="EXTRACTION_FAILED",
            details=details,
        )


class EmptyDocumentError(ATSCheckerException):
    """Raised when document produces no readable text or is empty."""

    def __init__(self, message: str = "The resume file does not contain any readable text.", details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="EMPTY_RESUME",
            details=details,
        )


class EmptyJobDescriptionError(ATSCheckerException):
    """Raised when job description is empty or whitespace only."""

    def __init__(self, message: str = "Job description cannot be empty.", details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPTY_JOB_DESCRIPTION",
            details=details,
        )


async def ats_exception_handler(request: Request, exc: ATSCheckerException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
