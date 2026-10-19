import io
import re
from typing import Tuple, List
import docx
from pypdf import PdfReader
from pypdf.errors import PdfReadError, FileNotDecryptedError

from app.core.errors import ExtractionError, EmptyDocumentError, FileValidationError
from app.core.security import validate_file_size, validate_file_signature, safe_temp_file
from app.services.synonyms import normalize_text


def extract_text_from_pdf(content: bytes) -> Tuple[str, List[str]]:
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

        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
            except Exception as e:
                warnings.append(f"Warning: Could not extract text from page {page_idx + 1}: {str(e)}")

    except (PdfReadError, FileNotDecryptedError) as e:
        raise ExtractionError(f"Unable to read PDF document: {str(e)}")
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Unexpected error while parsing PDF: {str(e)}")

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


def extract_text_from_docx(content: bytes) -> Tuple[str, List[str]]:
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
            for para in doc.paragraphs:
                if para.text and para.text.strip():
                    text_chunks.append(para.text.strip())

            # 2. Extract tables (resumes frequently put skills/columns in tables)
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    # Deduplicate adjacent identical merged cells
                    unique_cells = []
                    for c in row_cells:
                        if not unique_cells or unique_cells[-1] != c:
                            unique_cells.append(c)
                    if unique_cells:
                        text_chunks.append(" | ".join(unique_cells))

            # 3. Extract header/footer if present
            for section in doc.sections:
                if section.header and section.header.paragraphs:
                    for hp in section.header.paragraphs:
                        if hp.text and hp.text.strip():
                            text_chunks.append(hp.text.strip())

        except Exception as e:
            raise ExtractionError(f"Unable to read DOCX document: {str(e)}")

    full_text = "\n".join(text_chunks).strip()
    return full_text, warnings


def extract_resume_text(filename: str, content: bytes) -> Tuple[str, str, List[str]]:
    """
    Orchestrates validation and text extraction for an uploaded resume.
    Returns: (cleaned_text, normalized_ext, warnings)
    Raises: FileSizeExceededError, FileValidationError, ExtractionError, EmptyDocumentError.
    """
    # 1. Validate file size
    validate_file_size(len(content))

    # 2. Validate magic bytes and extension
    file_type = validate_file_signature(filename, content)

    # 3. Extract text based on file format
    if file_type == ".pdf":
        raw_text, warnings = extract_text_from_pdf(content)
    elif file_type == ".docx":
        raw_text, warnings = extract_text_from_docx(content)
    else:
        raise FileValidationError(f"Unsupported format: {file_type}")

    # 4. Check for empty or sparse document
    words = re.findall(r"\b\w+\b", raw_text)
    if not raw_text or len(words) < 30:
        raise EmptyDocumentError(
            message="The uploaded document contains insufficient readable text (at least 30 words required). "
            "Ensure the document contains selectable, non-scanned text.",
            details={"word_count": len(words), "character_count": len(raw_text)},
        )

    clean_text = normalize_text(raw_text)
    return clean_text, file_type, warnings
