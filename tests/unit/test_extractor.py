import io
import os
import docx
import pytest
from reportlab.pdfgen import canvas
from app.core.errors import (
    FileValidationError,
    FileSizeExceededError,
    ExtractionError,
    EmptyDocumentError,
)
from app.core.security import validate_file_signature, validate_file_size
from app.services.extractor import extract_resume_text, extract_text_from_pdf, extract_text_from_docx
from app.services.parser import parse_resume_content
from app.services.synonyms import normalize_resume_text


def test_extract_text_from_valid_pdf(fixtures_dir):
    pdf_path = os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.pdf")
    with open(pdf_path, "rb") as f:
        content = f.read()

    text, ext, warnings = extract_resume_text("senior_software_engineer.pdf", content)
    assert ext == ".pdf"
    assert "python" in text.lower()
    assert "fastapi" in text.lower()
    assert "react" in text.lower()
    assert len(text) > 100
    parsed = parse_resume_content(text)
    assert parsed["sections"]["experience"]
    assert parsed["sections"]["skills"]
    assert parsed["bullet_count"] == 6


def test_pdf_with_artificially_spaced_headings_is_recovered():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    lines = [
        "Jordan Example",
        "jordan@example.com",
        "W o r k  E x p e r i e n c e",
        "- Built internal reporting tools used by multiple departments",
        "across several regional offices.",
        "S k i l l s",
        "Python SQL reporting collaboration data quality systems",
        "E d u c a t i o n",
        "Bachelor of Science in Information Systems at Example University",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(40, 780 - index * 24, line)
    pdf.save()

    text, ext, warnings = extract_resume_text("spaced-headings.pdf", buffer.getvalue())
    parsed = parse_resume_content(text)

    assert ext == ".pdf"
    assert parsed["sections"]["experience"]
    assert parsed["sections"]["skills"]
    assert parsed["sections"]["education"]
    assert parsed["bullet_count"] == 1
    assert parsed["achievement_bullets"] == [
        "- Built internal reporting tools used by multiple departments across several regional offices."
    ]


def test_pdf_with_standard_headings_and_bullets_is_parsed():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    lines = [
        "Jordan Example",
        "jordan@example.com | +1 (415) 555-0134",
        "Professional Summary",
        "Data analyst focused on clear reporting and reliable insights.",
        "Work Experience",
        "Data Analyst - Example Co (2022 - Present)",
        "- Built reporting tools used by 12 teams.",
        "Skills",
        "SQL, Python, Tableau",
        "Education",
        "Bachelor of Science in Statistics",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(40, 780 - index * 24, line)
    pdf.save()

    text, ext, warnings = extract_resume_text("standard-headings.pdf", buffer.getvalue())
    parsed = parse_resume_content(text)

    assert ext == ".pdf"
    assert parsed["sections"]["experience"]
    assert parsed["sections"]["skills"]
    assert parsed["sections"]["education"]
    assert parsed["bullet_count"] == 1
    assert parsed["achievement_bullets"] == ["- Built reporting tools used by 12 teams."]
    assert not warnings


def test_spaced_heading_with_zero_width_extraction_artifacts_is_recovered():
    text = normalize_resume_text("W\u200bo\u200br\u200bk\u00a0E\u00a0x\u00a0p\u00a0e\u00a0r\u00a0i\u00a0e\u00a0n\u00a0c\u00a0e")

    assert text == "Work Experience"


def test_contact_details_are_not_extracted_as_achievement_bullets():
    resume = """Jordan Example
Email: jordan@example.com | Phone: +1 (415) 555-0134
Location: 123 Market Street, San Francisco, CA
Work Experience
- Designed and maintained internal reporting systems for 12 teams.
"""
    parsed = parse_resume_content(resume)

    assert parsed["bullet_count"] == 1
    assert parsed["achievement_bullets"] == [
        "- Designed and maintained internal reporting systems for 12 teams."
    ]
    assert parsed["metrics_found"] == ["12 teams"]


@pytest.mark.parametrize(
    ("heading", "section"),
    [
        ("Professional Summary", "summary"),
        ("Summary", "summary"),
        ("Profile", "summary"),
        ("Work Experience", "experience"),
        ("Experience", "experience"),
        ("Employment History", "experience"),
        ("Skills", "skills"),
        ("Technical Skills", "skills"),
        ("Core Competencies", "skills"),
        ("Education", "education"),
        ("Academic Qualifications", "education"),
        ("Projects", "projects"),
        ("Personal Projects", "projects"),
        ("Certifications", "certifications"),
        ("Certificates", "certifications"),
    ],
)
def test_common_heading_variations_are_recognized(heading, section):
    parsed = parse_resume_content(f"{heading.upper()}:\nContent for the selected resume section.")

    assert parsed["sections"][section] == "content for the selected resume section."


def test_page_number_lines_are_removed_from_extracted_text():
    text = normalize_resume_text("Work Experience\nBuilt internal tools.\nPage 2 of 3\n2\nEducation")

    assert "Built internal tools." in text
    assert "Page 2 of 3" not in text
    assert not any(line.strip() == "2" for line in text.splitlines())


def test_docx_table_content_is_extracted_and_ordered(tmp_path):
    document = docx.Document()
    document.add_paragraph("Jordan Example")
    document.add_paragraph("Work Experience")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Software Engineer"
    table.cell(0, 1).text = "- Built internal reporting tools used by 12 teams."
    document.add_paragraph("Education")
    document.add_paragraph("Bachelor of Science in Information Systems at Example University")
    document.add_paragraph(
        "Additional coursework included data structures, database systems, software design, and technical communication."
    )
    output = io.BytesIO()
    document.save(output)

    text, ext, warnings = extract_resume_text("table-resume.docx", output.getvalue())
    parsed = parse_resume_content(text)

    assert ext == ".docx"
    assert "Software Engineer" in text
    assert "Built internal reporting tools" in text
    assert parsed["sections"]["experience"]
    assert parsed["bullet_count"] == 1
    assert any("table-based layout" in warning.lower() for warning in warnings)


def test_extract_text_from_valid_docx(fixtures_dir):
    docx_path = os.path.join(fixtures_dir, "sample_resumes", "senior_software_engineer.docx")
    with open(docx_path, "rb") as f:
        content = f.read()

    text, ext, warnings = extract_resume_text("senior_software_engineer.docx", content)
    assert ext == ".docx"
    assert "python" in text.lower()
    assert "fastapi" in text.lower()
    assert "react" in text.lower()
    assert len(text) > 100
    parsed = parse_resume_content(text)
    assert parsed["sections"]["experience"]
    assert parsed["sections"]["skills"]
    assert parsed["sections"]["education"]
    assert parsed["bullet_count"] == 6


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
