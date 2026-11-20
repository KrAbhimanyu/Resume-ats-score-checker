import io
import re
from typing import Any, Callable, Tuple, List
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader
from pypdf.errors import PdfReadError, FileNotDecryptedError

from app.core.errors import ExtractionError, EmptyDocumentError, FileValidationError
from app.core.security import validate_file_size, validate_file_signature, safe_temp_file
from app.models.analysis_progress import ProgressStatus
from app.services.synonyms import normalize_resume_text, normalize_text


ProgressCallback = Callable[[str, ProgressStatus, dict[str, Any]], None]


def extract_text_from_pdf(
    content: bytes,
    progress_callback: ProgressCallback | None = None,
) -> Tuple[str, List[str]]:
    """
    Safely extracts readable text from PDF bytes using pypdf.
    Handles encryption, corruption, and identifies scanned documents.
    """
    warnings: List[str] = []
    text_chunks: List[str] = []

    try:
        pdf_stream = io.BytesIO(content)
        reader = PdfReader(pdf_stream)

        if reader.is_encrypted:
            try:
                # Attempt empty password decryption in case of default permissions
                decrypted = reader.decrypt("")
                if not decrypted:
                    raise ExtractionError(
                        "The PDF document is password-protected. Please upload an unlocked document."
                    )
            except Exception:
                raise ExtractionError(
                    "The PDF document is password-protected or encrypted. Please remove password protection."
                )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ExtractionError("The PDF document does not contain any pages.")

        if progress_callback:
            progress_callback(
                "extract_text",
                "in_progress",
                {"pages_total": total_pages, "pages_processed": 0, "pages_failed": 0},
            )

        pages_failed = 0
        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
            except Exception:
                pages_failed += 1
                warnings.append(
                    f"Warning: Could not extract text from page {page_idx + 1}."
                )
            if progress_callback:
                progress_callback(
                    "extract_text",
                    "in_progress",
                    {
                        "pages_total": total_pages,
                        "pages_processed": page_idx + 1,
                        "pages_failed": pages_failed,
                    },
                )
        if progress_callback:
            progress_callback(
                "extract_text",
                "completed",
                {
                    "pages_total": total_pages,
                    "pages_processed": total_pages,
                    "pages_failed": pages_failed,
                },
            )

    except (PdfReadError, FileNotDecryptedError):
        raise ExtractionError("Unable to read the PDF document.")
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError("An unexpected error occurred while parsing the PDF.")

    full_text = "\n".join(text_chunks).strip()

    # Heuristic for scanned image PDFs: multiple pages but virtually no text
    words = re.findall(r"\b\w+\b", full_text)
    if total_pages > 0 and len(words) < 20:
        warnings.append(
            "Document appears to be a scanned image or contains vector artwork with minimal readable text. "
            "Standard ATS systems cannot parse scanned resumes without OCR. "
            "Please use a text-based PDF or DOCX file for best results."
        )

    return full_text, warnings


def extract_text_from_docx(
    content: bytes,
    progress_callback: ProgressCallback | None = None,
) -> Tuple[str, List[str]]:
    """
    Safely extracts readable text from DOCX bytes including paragraphs and tables.
    """
    warnings: List[str] = []
    text_chunks: List[str] = []

    # Use safe_temp_file to ensure python-docx reads a complete, valid archive cleanly
    with safe_temp_file(content, suffix=".docx") as temp_path:
        try:
            doc = docx.Document(temp_path)

            # 1. Extract paragraphs
            has_multicolumn_table = False
            for block in doc.iter_inner_content():
                if isinstance(block, Paragraph):
                    if block.text and block.text.strip():
                        text_chunks.append(block.text.strip())
                    continue
                if not isinstance(block, Table):
                    continue

                for row in block.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    # Deduplicate adjacent identical merged cells
                    unique_cells = []
                    for c in row_cells:
                        if not unique_cells or unique_cells[-1] != c:
                            unique_cells.append(c)
                    if unique_cells:
                        text_chunks.append(" | ".join(unique_cells))
                        has_multicolumn_table = has_multicolumn_table or len(unique_cells) > 1

            if has_multicolumn_table:
                warnings.append(
                    "DOCX table-based layout detected. Table cell order was preserved, but review the original "
                    "document because visual column relationships cannot be verified from extracted text."
                )

            # Extract header/footer content not already present in the document body.
            for section in doc.sections:
                for part in (section.header, section.footer):
                    for paragraph in part.paragraphs:
                        if paragraph.text and paragraph.text.strip() and paragraph.text.strip() not in text_chunks:
                            text_chunks.append(paragraph.text.strip())

        except Exception:
            raise ExtractionError("Unable to read the DOCX document.")

    full_text = "\n".join(text_chunks).strip()
    return full_text, warnings


def extract_resume_text(
    filename: str,
    content: bytes,
    progress_callback: ProgressCallback | None = None,
) -> Tuple[str, str, List[str]]:
    """
    Orchestrates validation and text extraction for an uploaded resume.
    Returns: (cleaned_text, normalized_ext, warnings)
    Raises: FileSizeExceededError, FileValidationError, ExtractionError, EmptyDocumentError.
    """
    if progress_callback:
        progress_callback("validate_file", "in_progress", {})

    # 1. Validate file size
    validate_file_size(len(content))

    # 2. Validate magic bytes and extension
    file_type = validate_file_signature(filename, content)
    if progress_callback:
        progress_callback(
            "validate_file",
            "completed",
            {"file_type": file_type, "file_size_bytes": len(content)},
        )

    # 3. Extract text based on file format
    if progress_callback:
        progress_callback("extract_text", "in_progress", {"file_type": file_type})

    page_details: dict[str, Any] = {}

    def extraction_progress(
        step_id: str,
        status: ProgressStatus,
        details: dict[str, Any],
    ) -> None:
        page_details.update(
            {
                key: value
                for key, value in details.items()
                if key in {"pages_total", "pages_processed", "pages_failed"}
            }
        )
        if progress_callback:
            progress_callback(step_id, status, details)

    if file_type == ".pdf":
        raw_text, warnings = extract_text_from_pdf(content, extraction_progress)
    elif file_type == ".docx":
        raw_text, warnings = extract_text_from_docx(content, extraction_progress)
    else:
        raise FileValidationError(f"Unsupported format: {file_type}")

    # 4. Check for empty or sparse document
    if progress_callback:
        progress_callback(
            "page_word_count",
            "in_progress",
            {
                **page_details,
                **(
                    {"explanation": "DOCX files do not provide a reliable rendered page count."}
                    if file_type == ".docx"
                    else {}
                ),
            },
        )
    words = re.findall(r"\b\w+\b", raw_text)
    if not raw_text or len(words) < 30:
        raise EmptyDocumentError(
            message="The uploaded document contains insufficient readable text (at least 30 words required). "
            "Ensure the document contains selectable, non-scanned text.",
            details={"word_count": len(words), "character_count": len(raw_text)},
        )

    if progress_callback:
        progress_callback("normalize_text", "in_progress", {})
    clean_text = normalize_resume_text(raw_text)
    word_count = len(re.findall(r"\b[a-z]+\b", normalize_text(clean_text)))
    if progress_callback:
        progress_callback(
            "page_word_count",
            "completed",
            {
                **page_details,
                "word_count": word_count,
                **(
                    {"explanation": "DOCX files do not provide a reliable rendered page count."}
                    if file_type == ".docx"
                    else {}
                ),
            },
        )
        progress_callback(
            "normalize_text",
            "completed",
            {
                "file_type": file_type,
                "word_count": word_count,
            },
        )
    return clean_text, file_type, warnings
