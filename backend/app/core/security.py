import os
import tempfile
import zipfile
from contextlib import contextmanager
from typing import Generator
from app.config import settings
from app.core.errors import FileSizeExceededError, FileValidationError


PDF_MAGIC_BYTES = b"%PDF-"
ZIP_MAGIC_BYTES = b"PK\x03\x04"


def validate_file_size(size_bytes: int) -> None:
    """Validate that the uploaded file does not exceed the configured maximum size."""
    if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        raise FileSizeExceededError(
            message=f"Uploaded file size ({size_bytes} bytes) exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes ({settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB).",
            max_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
            actual_size_bytes=size_bytes,
        )


def validate_file_signature(filename: str, content: bytes) -> str:
    """
    Validates file extension and binary magic bytes to prevent file extension spoofing.
    Returns normalized file extension (e.g. '.pdf' or '.docx').
    """
    if not filename or "." not in filename:
        raise FileValidationError(
            message="Uploaded file must have a valid extension (.pdf or .docx).",
            details={"filename": filename},
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            message=f"Unsupported file format '{ext}'. Only .pdf and .docx files are supported.",
            details={"allowed_extensions": settings.ALLOWED_EXTENSIONS, "received_extension": ext},
        )

    if not content or len(content) < 4:
        raise FileValidationError(
            message="Uploaded file is empty or too small to be a valid document.",
            details={"file_size": len(content) if content else 0},
        )

    if ext == ".pdf":
        # Standard PDF files start with %PDF- (usually in the first 1024 bytes)
        if PDF_MAGIC_BYTES not in content[:1024]:
            raise FileValidationError(
                message="File content does not match standard PDF file signature (magic bytes).",
                details={"expected": "%PDF-", "extension": ext},
            )
        return ".pdf"

    elif ext == ".docx":
        # DOCX is an OpenXML ZIP archive starting with PK\x03\x04
        if not content.startswith(ZIP_MAGIC_BYTES):
            raise FileValidationError(
                message="File content does not match standard DOCX/ZIP file signature (magic bytes).",
                details={"expected": "PK\\x03\\x04", "extension": ext},
            )
        # Verify internal DOCX structure (must contain [Content_Types].xml or word/document.xml)
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    namelist = zf.namelist()
                    if not any(name.startswith("word/") or name == "[Content_Types].xml" for name in namelist):
                        raise FileValidationError(
                            message="Uploaded file has a ZIP header but lacks standard Word document structure.",
                            details={"extension": ext},
                        )
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except zipfile.BadZipFile:
            raise FileValidationError(
                message="Corrupted or invalid DOCX archive.",
                details={"extension": ext},
            )
        return ".docx"

    raise FileValidationError(f"Unsupported file format: {ext}")


@contextmanager
def safe_temp_file(content: bytes, suffix: str) -> Generator[str, None, None]:
    """
    Context manager that safely writes bytes to a secure temporary file
    and guarantees its deletion upon exit, even on exception.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = tmp.name
    try:
        tmp.write(content)
        tmp.flush()
        tmp.close()
        yield tmp_path
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
