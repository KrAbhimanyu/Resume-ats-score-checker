import os
import pytest
from app.core.errors import (
    FileValidationError,
    FileSizeExceededError,
    ExtractionError,
    EmptyDocumentError,
)
from app.core.security import validate_file_signature, validate_file_size
from app.services.extractor import extract_resume_text, extract_text_from_pdf, extract_text_from_docx


def test_extract_text_from_valid_pdf(fixtures_dir):
    pdf_path = os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.pdf")
    with open(pdf_path, "rb") as f:
        content = f.read()

    text, ext, warnings = extract_resume_text("senior_software_engineer.pdf", content)
    assert ext == ".pdf"
    assert "python" in text
    assert "fastapi" in text
    assert "react" in text
    assert len(text) > 100


def test_extract_text_from_valid_docx(fixtures_dir):
    docx_path = os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.docx")
    with open(docx_path, "rb") as f:
        content = f.read()

    text, ext, warnings = extract_resume_text("senior_software_engineer.docx", content)
    assert ext == ".docx"
    assert "python" in text
    assert "fastapi" in text
    assert "react" in text
    assert len(text) > 100


def test_magic_bytes_spoofing_rejected():
    fake_pdf = b"This is just plain text masquerading as a PDF document."
    with pytest.raises(FileValidationError) as exc_info:
        extract_resume_text("fake.pdf", fake_pdf)
    assert "signature" in exc_info.value.message.lower() or "magic" in exc_info.value.message.lower()


def test_fake_docx_zip_structure_rejected():
    fake_docx = b"PK\x03\x04SomeDummyZipContentWithoutWordXml"
    with pytest.raises(FileValidationError):
        extract_resume_text("fake.docx", fake_docx)


def test_unsupported_extension_rejected():
    with pytest.raises(FileValidationError):
        extract_resume_text("document.txt", b"plain text")

    with pytest.raises(FileValidationError):
        extract_resume_text("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00")


def test_corrupted_pdf_rejected(fixtures_dir):
    corrupt_path = os.path.join(fixtures_dir, "sample_resumes", "corrupt_file.pdf")
    with open(corrupt_path, "rb") as f:
        content = f.read()

    with pytest.raises(ExtractionError):
        extract_resume_text("corrupt.pdf", content)


def test_empty_resume_rejected(fixtures_dir):
    empty_path = os.path.join(fixtures_dir, "sample_resumes", "empty_resume.pdf")
    with open(empty_path, "rb") as f:
        content = f.read()

    with pytest.raises(EmptyDocumentError):
        extract_resume_text("empty.pdf", content)


def test_minimal_resume_rejected(fixtures_dir):
    minimal_path = os.path.join(fixtures_dir, "sample_resumes", "minimal_resume.docx")
    with open(minimal_path, "rb") as f:
        content = f.read()

    with pytest.raises(EmptyDocumentError) as exc_info:
        extract_resume_text("minimal.docx", content)
    assert "insufficient" in exc_info.value.message.lower()


def test_file_size_exceeded():
    oversized = b"%PDF-" + b"0" * (6 * 1024 * 1024)  # 6 MB (limit is 5 MB)
    with pytest.raises(FileSizeExceededError):
        validate_file_size(len(oversized))
