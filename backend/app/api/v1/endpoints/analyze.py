import asyncio
import os
import time
from typing import Any
from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.errors import ATSCheckerException, EmptyJobDescriptionError
from app.core.logging_config import logger
from app.core.security import read_upload_file
from app.models.analysis_progress import (
    AnalysisProgressEvent,
    AnalysisSessionFailureRequest,
    AnalysisSessionCreated,
    AnalysisSessionSnapshot,
    ProgressStatus,
)
from app.models.schemas import AnalysisResponse, DocumentMetadata
from app.services.analysis_sessions import (
    AnalysisSessionNotFound,
    complete_analysis_session,
    create_analysis_session,
    fail_analysis_session,
    load_analysis_session,
    load_events_after,
    record_progress,
)
from app.services.extractor import extract_resume_text
from app.services.parser import extract_job_requirements, parse_resume_content
from app.services.scoring import calculate_ats_score
from app.services.recommender import generate_recommendations
from app.services.assistant import generate_improvement_assistant
from app.services.quality import generate_resume_quality_report
from app.services.synonyms import normalize_text

router = APIRouter()

SESSION_HEADER = "X-Analysis-Session-Id"


@router.post(
    "/analyze/session",
    response_model=AnalysisSessionCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resumable analysis progress session",
)
async def create_analysis_progress_session() -> AnalysisSessionCreated:
    return create_analysis_session()


@router.get(
    "/analyze/session",
    response_model=AnalysisSessionSnapshot,
    summary="Get analysis session status and replayable progress",
)
async def get_analysis_progress_session(
    analysis_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> AnalysisSessionSnapshot:
    if not analysis_session_id:
        raise HTTPException(status_code=400, detail="An analysis session ID is required.")
    try:
        return load_analysis_session(analysis_session_id)
    except AnalysisSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="Analysis session was not found or has expired.") from exc


@router.post(
    "/analyze/session/fail",
    response_model=AnalysisSessionSnapshot,
    summary="Record an interrupted analysis session",
)
async def fail_analysis_progress_session(
    failure: AnalysisSessionFailureRequest = Body(default=AnalysisSessionFailureRequest()),
    analysis_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> AnalysisSessionSnapshot:
    if not analysis_session_id:
        raise HTTPException(status_code=400, detail="An analysis session ID is required.")
    try:
        fail_analysis_session(analysis_session_id, failure.error_code)
        return load_analysis_session(analysis_session_id)
    except AnalysisSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="Analysis session was not found or has expired.") from exc


@router.get(
    "/analyze/session/events",
    summary="Stream live analysis progress events",
)
async def stream_analysis_progress(
    analysis_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
    after_id: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    if not analysis_session_id:
        raise HTTPException(status_code=400, detail="An analysis session ID is required.")
    try:
        snapshot = load_analysis_session(analysis_session_id)
    except AnalysisSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="Analysis session was not found or has expired.") from exc

    last_id = after_id
    if last_event_id and last_event_id.isdigit():
        last_id = max(last_id, int(last_event_id))

    async def stream_events():
        nonlocal last_id
        last_heartbeat = time.monotonic()
        while True:
            try:
                events = load_events_after(analysis_session_id, last_id)
                for event in events:
                    yield (
                        f"id: {event.event_id}\n"
                        "event: progress\n"
                        f"data: {event.model_dump_json()}\n\n"
                    )
                    last_id = event.event_id
                current = load_analysis_session(analysis_session_id)
            except AnalysisSessionNotFound:
                return
            if current.status in ("completed", "failed"):
                return
            if time.monotonic() - last_heartbeat >= 15:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


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
    analysis_session_id: str | None = Header(default=None, alias=SESSION_HEADER),
) -> AnalysisResponse:
    start_time = time.perf_counter()

    def report_progress(
        layer_id: str,
        step_id: str,
        step_status: ProgressStatus,
        details: dict[str, Any] | None = None,
    ) -> AnalysisProgressEvent | None:
        if not analysis_session_id:
            return None
        return record_progress(
            analysis_session_id,
            layer_id,
            step_id,
            step_status,
            details,
        )

    try:
        report_progress("resume_parsing", "validate_file", "in_progress")
        if not job_description or not job_description.strip():
            raise EmptyJobDescriptionError("Job description cannot be empty.")
        if len(job_description.strip().split()) < 5:
            raise EmptyJobDescriptionError(
                "Job description contains insufficient content (at least 5 words required)."
            )
        content = await read_upload_file(resume_file)
        file_name = resume_file.filename or "uploaded_document"
        report_progress(
            "resume_parsing",
            "validate_file",
            "completed",
            {
                "file_type": os.path.splitext(file_name)[1].lower(),
                "file_size_bytes": len(content),
            },
        )

        def extraction_progress(
            step_id: str,
            step_status: ProgressStatus,
            details: dict[str, Any],
        ) -> None:
            report_progress("resume_parsing", step_id, step_status, details)

        clean_resume_text, file_type, extraction_warnings = await asyncio.to_thread(
            extract_resume_text,
            filename=file_name,
            content=content,
            progress_callback=extraction_progress if analysis_session_id else None,
        )
        if file_type == ".docx":
            report_progress(
                "resume_parsing",
                "extract_text",
                "completed",
                {"file_type": file_type},
            )

        def parsing_progress(
            layer_id: str,
            step_id: str,
            step_status: ProgressStatus,
            details: dict[str, Any],
        ) -> None:
            report_progress(layer_id, step_id, step_status, details)

        parsed_resume = await asyncio.to_thread(
            parse_resume_content,
            clean_resume_text,
            progress_callback=parsing_progress if analysis_session_id else None,
        )
        if "general" in parsed_resume.get("sections", {}):
            extraction_warnings.append(
                "No supported resume section headings were recognized. Review the extracted text and confirm "
                "that section titles and content were read in the intended order."
            )
        elif (
            not parsed_resume.get("achievement_bullets")
            and any(parsed_resume.get("sections", {}).get(section) for section in ("experience", "projects"))
        ):
            extraction_warnings.append(
                "Experience or project content was detected, but no achievement statements could be isolated. "
                "Review the original document, especially if it uses columns, tables, or text boxes."
            )
        norm_job = normalize_text(job_description)
        parsed_job = await asyncio.to_thread(
            extract_job_requirements,
            norm_job,
            progress_callback=parsing_progress if analysis_session_id else None,
        )
        report_progress(
            "experience_impact",
            "evidence_quality",
            "in_progress",
            {},
        )
        report_progress("ats_recommendations", "ats_score", "in_progress", {})
        report_progress("ats_recommendations", "section_scoring", "in_progress", {})
        (
            overall_score,
            match_tier,
            summary,
            category_scores,
            matched_reqs,
            missing_reqs,
            keywords_found,
        ) = await asyncio.to_thread(
            calculate_ats_score,
            parsed_job=parsed_job,
            parsed_resume=parsed_resume,
            norm_resume_text=clean_resume_text,
            norm_job_text=norm_job,
            progress_callback=parsing_progress if analysis_session_id else None,
        )
        report_progress(
            "ats_recommendations",
            "ats_score",
            "completed",
            {
                "overall_score": overall_score,
                "matched_requirement_count": len(matched_reqs),
                "missing_requirement_count": len(missing_reqs),
            },
        )
        report_progress(
            "ats_recommendations",
            "section_scoring",
            "completed",
            {
                "category_scores": [
                    {
                        "category_id": score.category_id,
                        "score": score.score,
                        "max_score": score.max_score,
                    }
                    for score in category_scores
                ]
            },
        )

        quality_report = await asyncio.to_thread(
            generate_resume_quality_report,
            resume_text=clean_resume_text,
            parsed_resume=parsed_resume,
            parsed_job=parsed_job,
        )
        report_progress(
            "experience_impact",
            "evidence_quality",
            "completed",
            {
                "impact_score": quality_report.impact_score,
                "quality_score": quality_report.readability_score,
            },
        )

        report_progress(
            "ats_recommendations",
            "recommendation_generation",
            "in_progress",
            {},
        )
        recommendations = await asyncio.to_thread(
            generate_recommendations,
            parsed_job=parsed_job,
            parsed_resume=parsed_resume,
            missing_reqs=missing_reqs,
            category_scores=category_scores,
        )
        improvement_assistant = await asyncio.to_thread(
            generate_improvement_assistant,
            parsed_job=parsed_job,
            parsed_resume=parsed_resume,
            norm_resume_text=clean_resume_text,
            norm_job_text=norm_job,
            matched_reqs=matched_reqs,
            missing_reqs=missing_reqs,
        )
        report_progress(
            "ats_recommendations",
            "recommendation_generation",
            "completed",
            {
                "recommendations_count": len(recommendations),
                "rewrite_suggestions_count": len(
                    improvement_assistant.bullet_improvements
                )
            },
        )

        report_progress("ats_recommendations", "final_report", "in_progress", {})
        duration_ms = round((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Analysis completed in {duration_ms}ms | Type: {file_type} | Size: {len(content)}B | "
            f"Words: {parsed_resume['word_count']} | Score: {overall_score}/100 ({match_tier})"
        )

        doc_metadata = DocumentMetadata(
            filename=file_name,
            file_type=file_type,
            file_size_bytes=len(content),
            character_count=len(clean_resume_text),
            word_count=parsed_resume["word_count"],
            extraction_warnings=extraction_warnings,
        )
        result = AnalysisResponse(
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
            quality_report=quality_report,
            improvement_assistant=improvement_assistant,
        )
        if analysis_session_id:
            duration_ms = round((time.perf_counter() - start_time) * 1000)
            complete_analysis_session(
                analysis_session_id,
                result,
                duration_ms,
                {
                    "overall_score": overall_score,
                    "category_scores": [
                        {
                            "category_id": score.category_id,
                            "score": score.score,
                            "max_score": score.max_score,
                        }
                        for score in category_scores
                    ],
                    "recommendations_count": len(recommendations),
                },
            )

        return result
    except AnalysisSessionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="Analysis session was not found or has expired.",
        ) from exc
    except Exception as exc:
        if analysis_session_id:
            error_code = exc.error_code if isinstance(exc, ATSCheckerException) else "ANALYSIS_FAILED"
            fail_analysis_session(analysis_session_id, error_code)
        raise
