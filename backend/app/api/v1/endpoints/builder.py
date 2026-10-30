import io
import json
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.core.errors import EmptyJobDescriptionError, EmptyDocumentError
from app.models.builder_schemas import (
    TargetMode,
    TargetedAnalysisRequest,
    TargetedAnalysisResponse,
    ExportResumeRequest,
    StructuredResume,
)
from app.services.extractor import extract_resume_text
from app.services.builder_service import (
    analyze_targeted_resume,
    generate_docx_resume,
    generate_pdf_resume,
)

router = APIRouter()


@router.post(
    "/analyze-and-plan",
    response_model=TargetedAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze resume against target company and role",
    description="Extracts resume text, performs company- and role-specific gap analysis, and generates an approved draft resume.",
)
async def analyze_and_plan_endpoint(
    resume_file: Optional[UploadFile] = File(default=None, description="Optional uploaded resume file (.pdf or .docx)"),
    resume_text: Optional[str] = Form(default=None, description="Optional pre-extracted resume text"),
    target_mode: str = Form(default=TargetMode.FAANG_BIG_TECH.value),
    company_name: str = Form(...),
    industry: Optional[str] = Form(default=None),
    job_title: str = Form(...),
    job_description: Optional[str] = Form(default=""),
    sections_to_improve: Optional[str] = Form(default="summary,skills,experience,projects"),
) -> TargetedAnalysisResponse:
    # 1. Resolve Resume Text
    clean_text = ""
    if resume_file is not None:
        content = await resume_file.read()
        extracted_text, _, _ = extract_resume_text(
            filename=resume_file.filename or "resume",
            content=content,
        )
        clean_text = extracted_text
    elif resume_text and resume_text.strip():
        clean_text = resume_text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either resume_file or resume_text must be provided.",
        )

    if len(clean_text.split()) < 15:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume text contains insufficient content (at least 15 words required).",
        )

    # 2. Parse Mode
    try:
        mode_enum = TargetMode(target_mode)
    except ValueError:
        mode_enum = TargetMode.ANY_COMPANY

    # 3. Parse Sections
    sections_list = [s.strip() for s in (sections_to_improve or "").split(",") if s.strip()]
    if not sections_list:
        sections_list = ["summary", "skills", "experience", "projects"]

    # 4. Execute Analysis & Plan
    return analyze_targeted_resume(
        resume_text=clean_text,
        target_mode=mode_enum,
        company_name=company_name.strip(),
        job_title=job_title.strip(),
        industry=industry.strip() if industry else None,
        job_description=job_description or "",
        sections_to_improve=sections_list,
    )


@router.post(
    "/analyze-and-plan-json",
    response_model=TargetedAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze resume against target via JSON payload",
    description="JSON endpoint for targeted gap analysis with pre-extracted text.",
)
async def analyze_and_plan_json_endpoint(
    payload: TargetedAnalysisRequest,
) -> TargetedAnalysisResponse:
    if len(payload.resume_text.split()) < 15:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume text contains insufficient content (at least 15 words required).",
        )

    return analyze_targeted_resume(
        resume_text=payload.resume_text,
        target_mode=payload.target_mode,
        company_name=payload.company_name.strip(),
        job_title=payload.job_title.strip(),
        industry=payload.industry.strip() if payload.industry else None,
        job_description=payload.job_description or "",
        sections_to_improve=payload.sections_to_improve,
    )


@router.post(
    "/export",
    summary="Export structured resume to PDF or DOCX",
    description="Generates an ATS-compliant, single-column PDF or Microsoft Word document from the approved structured resume.",
)
async def export_resume_endpoint(
    payload: ExportResumeRequest,
) -> Response:
    format_clean = payload.format.lower().strip()
    safe_name = "".join(c for c in (payload.filename or "targeted_resume") if c.isalnum() or c in ("-", "_")) or "targeted_resume"

    if format_clean == "docx":
        docx_bytes = generate_docx_resume(payload.resume)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.docx"',
                "Content-Length": str(len(docx_bytes)),
            },
        )
    elif format_clean == "pdf":
        pdf_bytes = generate_pdf_resume(payload.resume)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{payload.format}'. Supported formats are 'pdf' and 'docx'.",
        )
