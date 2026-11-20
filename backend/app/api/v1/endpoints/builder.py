import io
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, Response, status, Depends
from fastapi.responses import StreamingResponse

from app.core.errors import EmptyJobDescriptionError, EmptyDocumentError
from app.core.security import read_upload_file
from app.models.builder_schemas import (
    TargetMode,
    TargetedAnalysisRequest,
    TargetedAnalysisResponse,
    ExportResumeRequest,
    StructuredResume,
    ResumeAIRequest,
    ResumeAIResponse,
    ResumeDocumentInput,
    ResumeDocumentOutput,
)
from app.db.database import database, utc_now
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user
from app.services.business_billing import run_charged_ai_operation
from app.services.resume_ai import generate_resume_content
from app.services.extractor import extract_resume_text
from app.services.builder_service import (
    analyze_targeted_resume,
    generate_docx_resume,
    generate_pdf_resume,
    RESUME_TEMPLATE_PALETTES,
)

router = APIRouter()


def _enforce_resume_ai_rate_limit(user_id: str) -> None:
    operation = "resume_ai"
    limit = 5
    window_seconds = 900
    rate_key = hashlib.sha256(f"resume-ai:{user_id}".encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with database(immediate=True) as connection:
        row = connection.execute(
            "SELECT window_started_at, attempts FROM auth_rate_limits WHERE rate_key=? AND operation=?",
            (rate_key, operation),
        ).fetchone()
        if row:
            try:
                window_started = datetime.fromisoformat(row["window_started_at"])
            except ValueError:
                window_started = now - timedelta(seconds=window_seconds + 1)
            if (now - window_started).total_seconds() < window_seconds:
                if row["attempts"] >= limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many resume AI requests. Try again after the rate limit window.",
                        headers={"Retry-After": str(window_seconds)},
                    )
                connection.execute(
                    "UPDATE auth_rate_limits SET attempts=attempts+1 WHERE rate_key=? AND operation=?",
                    (rate_key, operation),
                )
                return
        connection.execute(
            "INSERT INTO auth_rate_limits(rate_key, operation, window_started_at, attempts) "
            "VALUES (?, ?, ?, 1) ON CONFLICT(rate_key, operation) DO UPDATE SET "
            "window_started_at=excluded.window_started_at, attempts=1",
            (rate_key, operation, now.isoformat()),
        )


@router.post("/ai", response_model=ResumeAIResponse, summary="Generate grounded resume writing suggestions")
async def resume_ai_endpoint(
    payload: ResumeAIRequest,
    user: dict = Depends(current_user),
) -> ResumeAIResponse:
    _enforce_resume_ai_rate_limit(user["id"])
    return await run_charged_ai_operation(
        user["id"],
        "resume_writing",
        lambda: generate_resume_content(payload),
    )


@router.get("/resumes", response_model=List[ResumeDocumentOutput], summary="List saved resume documents")
async def list_resume_documents(
    document_type: str,
    user: dict = Depends(current_user),
) -> List[ResumeDocumentOutput]:
    if document_type not in {"profile", "version"}:
        raise HTTPException(status_code=400, detail="Document type must be 'profile' or 'version'.")
    with database() as connection:
        rows = connection.execute(
            "SELECT id, document_type, name, document_json, created_at, updated_at "
            "FROM resume_builder_documents WHERE user_id=? AND document_type=? ORDER BY updated_at DESC",
            (user["id"], document_type),
        ).fetchall()
    documents = []
    for row in rows:
        try:
            document = json.loads(reveal_text(row["document_json"]))
            if not isinstance(document, dict):
                raise ValueError("Stored resume document is not a JSON object")
            documents.append(ResumeDocumentOutput(
                id=row["id"],
                document_type=row["document_type"],
                name=reveal_text(row["name"]),
                document=document,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail="A saved resume document could not be read.") from exc
    return documents


@router.put("/resumes/{document_id}", response_model=ResumeDocumentOutput, summary="Save a resume document")
async def save_resume_document(
    document_id: str,
    payload: ResumeDocumentInput,
    user: dict = Depends(current_user),
) -> ResumeDocumentOutput:
    if document_id != payload.id:
        raise HTTPException(status_code=400, detail="Resume document ID does not match the request.")
    now = utc_now()
    encoded_document = json.dumps(payload.document, ensure_ascii=False, separators=(",", ":"))
    with database(immediate=True) as connection:
        existing = connection.execute(
            "SELECT created_at, user_id FROM resume_builder_documents WHERE id=?",
            (document_id,),
        ).fetchone()
        if existing and existing["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Resume document was not found.")
        created_at = existing["created_at"] if existing else now
        if existing:
            connection.execute(
                "UPDATE resume_builder_documents SET document_type=?, name=?, document_json=?, updated_at=? "
                "WHERE id=? AND user_id=?",
                (
                    payload.document_type, protect_text(payload.name), protect_text(encoded_document),
                    now, document_id, user["id"],
                ),
            )
        else:
            connection.execute(
                "INSERT INTO resume_builder_documents "
                "(id, user_id, document_type, name, document_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id, user["id"], payload.document_type, protect_text(payload.name),
                    protect_text(encoded_document), created_at, now,
                ),
            )
    return ResumeDocumentOutput(
        id=document_id, document_type=payload.document_type, name=payload.name,
        document=payload.document, created_at=created_at, updated_at=now,
    )


@router.delete("/resumes/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a saved resume document")
async def delete_resume_document(document_id: str, user: dict = Depends(current_user)) -> Response:
    with database(immediate=True) as connection:
        connection.execute(
            "DELETE FROM resume_builder_documents WHERE id=? AND user_id=?",
            (document_id, user["id"]),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        content = await read_upload_file(resume_file)
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
    template_parts = payload.template_id.split("-")
    valid_families = {
        "essential", "modern", "qa", "professional", "academic", "technical",
        "creative", "healthcare", "finance", "marketing", "sales", "hr",
        "operations", "executive",
    }
    if (
        len(template_parts) != 3
        or template_parts[0] != "ats"
        or template_parts[1] not in valid_families
        or template_parts[2] not in RESUME_TEMPLATE_PALETTES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown resume template. Choose a template from the ATS template catalog.",
        )
    if payload.international_format not in {"us", "uk", "eu", "india", "japan"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported international format.",
        )

    if format_clean == "docx":
        docx_bytes = generate_docx_resume(
            payload.resume,
            template_id=payload.template_id,
            international_format=payload.international_format,
            font_family=payload.font_family,
            section_order=payload.section_order,
            hidden_sections=payload.hidden_sections,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.docx"',
                "Content-Length": str(len(docx_bytes)),
            },
        )
    elif format_clean == "pdf":
        pdf_bytes = generate_pdf_resume(
            payload.resume,
            template_id=payload.template_id,
            international_format=payload.international_format,
            font_family=payload.font_family,
            section_order=payload.section_order,
            hidden_sections=payload.hidden_sections,
        )
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
