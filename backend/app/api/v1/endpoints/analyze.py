import time
from fastapi import APIRouter, UploadFile, File, Form, status
from app.core.errors import EmptyJobDescriptionError
from app.core.logging_config import logger
from app.models.schemas import AnalysisResponse, DocumentMetadata
from app.services.extractor import extract_resume_text
from app.services.parser import extract_job_requirements, parse_resume_content
from app.services.scoring import calculate_ats_score
from app.services.recommender import generate_recommendations
from app.services.synonyms import normalize_text

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze resume against a job description",
    description="Uploads a PDF or DOCX resume, validates security constraints, parses content, and calculates an ATS match score.",
)
async def analyze_resume(
    resume_file: UploadFile = File(..., description="Resume document file (.pdf or .docx)"),
    job_description: str = Form(default="", description="Target job description text"),
) -> AnalysisResponse:
    start_time = time.time()

    # 1. Validate Job Description
    if not job_description or not job_description.strip():
        raise EmptyJobDescriptionError("Job description cannot be empty.")
    if len(job_description.strip().split()) < 5:
        raise EmptyJobDescriptionError("Job description contains insufficient content (at least 5 words required).")

    # 2. Read resume file content into memory
    content = await resume_file.read()

    # 3. Safely validate and extract resume text
    # Rejects invalid formats, signature mismatches, corrupted files, empty files
    clean_resume_text, file_type, extraction_warnings = extract_resume_text(
        filename=resume_file.filename or "uploaded_document",
        content=content,
    )

    # 4. Parse Job Description and Resume entities
    norm_job = normalize_text(job_description)
    parsed_job = extract_job_requirements(norm_job)
    parsed_resume = parse_resume_content(clean_resume_text)

    # 5. Calculate Deterministic ATS Match Score across 5 categories
    (
        overall_score,
        match_tier,
        summary,
        category_scores,
        matched_reqs,
        missing_reqs,
        keywords_found,
    ) = calculate_ats_score(
        parsed_job=parsed_job,
        parsed_resume=parsed_resume,
        norm_resume_text=clean_resume_text,
        norm_job_text=norm_job,
    )

    # 6. Generate Contextual Recommendations
    recommendations = generate_recommendations(
        parsed_job=parsed_job,
        parsed_resume=parsed_resume,
        missing_reqs=missing_reqs,
        category_scores=category_scores,
    )

    # 7. Safe Logging (Strict privacy guarantee: NEVER log document text or PII)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"Analysis completed in {duration_ms}ms | File: {resume_file.filename} | Type: {file_type} | Size: {len(content)}B | "
        f"Words: {parsed_resume['word_count']} | Score: {overall_score}/100 ({match_tier})"
    )

    # 8. Build and return structured response
    doc_metadata = DocumentMetadata(
        filename=resume_file.filename or "uploaded_document",
        file_type=file_type,
        file_size_bytes=len(content),
        character_count=len(clean_resume_text),
        word_count=parsed_resume["word_count"],
        extraction_warnings=extraction_warnings,
    )

    return AnalysisResponse(
        overall_score=overall_score,
        score_label="Estimated Resume–Job Match Score",
        match_tier=match_tier,
        summary=summary,
        category_scores=category_scores,
        matched_requirements=matched_reqs,
        missing_requirements=missing_reqs,
        keywords_found=keywords_found,
        recommendations=recommendations,
        document_metadata=doc_metadata,
    )
