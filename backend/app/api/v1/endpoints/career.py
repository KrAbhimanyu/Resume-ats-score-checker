import asyncio
import hashlib
import json
import re
import smtplib
import ssl
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from statistics import median
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings
from app.core.logging_config import logger
from app.db.database import database, utc_now
from app.models.builder_schemas import StructuredResume
from app.models.job_schemas import (
    ApplicationCreate,
    ApplicationDraftSaveInput,
    ApplicationUpdate,
    AuthResponse,
    DraftRequest,
    GoogleAuthRequest,
    InterviewInput,
    InterviewUpdate,
    JobCreate,
    JobDescriptionInput,
    JobSearchRequest,
    JobUrlInput,
    LoginRequest,
    MatchRequest,
    RegisterRequest,
    ReminderInput,
    ReminderUpdate,
    ResumeProfileInput,
    SearchPreferences,
    SkillProgressInput,
    TailoringApprovalRequest,
)
from app.services.data_protection import protect_text, reveal_text
from app.services.career_data import (
    json_dump,
    persist_private_job,
    persist_provider_job,
    user_application,
    user_resume,
    visible_job,
)
from app.services.job_auth import (
    bearer_scheme,
    current_user,
    login_google_user,
    login_user,
    register_user,
    revoke_session,
)
from app.services.job_matching import analyze_job_description, match_resume_to_job
from app.services.job_providers import provider_status, search_authorized_providers
from app.services.job_tailoring import (
    apply_approved_changes,
    create_tailoring_review,
    serialize_resume,
)
from app.services.parser import parse_resume_content
from app.services.extractor import extract_resume_text
from app.core.security import read_upload_file
from app.services.resume_ai import rank_job_candidates_with_ai
from app.services.career_coach_ai import answer_career_question
from app.services.business_billing import run_charged_ai_operation


router = APIRouter()
_APPLICATION_STATUSES = {
    "saved", "applied", "shortlisted", "assessment", "interview", "offer", "rejected", "withdrawn"
}
_FINAL_APPLICATION_STATUSES = {"offer", "rejected", "withdrawn"}


def _utc_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail="A timezone-aware date and time is required.")
    return value.astimezone(timezone.utc).isoformat()


def _json_value(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _parse_resume_for_storage(resume_text: str) -> dict[str, Any]:
    parsed = parse_resume_content(resume_text)
    parsed.pop("raw_tokens", None)
    return parsed


def _serialize_job(job: dict[str, Any]) -> dict[str, Any]:
    result = dict(job)
    result["experience_level"] = _infer_experience_level(
        f"{result.get('title', '')} {result.get('description', '')}"
    )
    salary_min = result.get("salary_min")
    salary_max = result.get("salary_max")
    result["salary"] = (
        {
            "minimum": salary_min,
            "maximum": salary_max,
            "currency": result.get("salary_currency"),
            "period": result.get("salary_period") or "unspecified",
            "source": result.get("source_label"),
            "verified_employer_provided": _json_value(result.get("raw_json"), {}).get(
                "salary_is_predicted"
            ) in (0, "0", False) or _json_value(result.get("raw_json"), {}).get("salary_provided") is True,
            "classification": "listing_reported; source verification varies",
        }
        if salary_min is not None and salary_max is not None else None
    )
    result.pop("raw_json", None)
    result.pop("raw", None)
    return result


def _infer_experience_level(text: str) -> Optional[str]:
    value = text.casefold()
    if re.search(r"\b(intern(ship)?|fresher|new graduate|recent graduate)\b", value):
        return "fresher"
    if re.search(r"\b(entry[- ]level|junior|early career|0\s*[-–]\s*2\s+years?)\b", value):
        return "entry_level"
    if re.search(r"\b(mid[- ]level|intermediate|2\s*[-–]\s*5\s+years?)\b", value):
        return "intermediate"
    if re.search(r"\b(senior|staff|principal|lead|director|head of|5\+?\s+years?)\b", value):
        return "experienced"
    return None


def _matches_job_filters(job: dict[str, Any], payload: JobSearchRequest) -> bool:
    if payload.company and payload.company.casefold() not in str(job.get("company_name") or "").casefold():
        return False
    if payload.remote_type and job.get("remote_type") != payload.remote_type:
        return False
    if payload.employment_type and payload.employment_type.casefold() not in str(job.get("employment_type") or "").casefold():
        return False
    if payload.experience_level and _infer_experience_level(
        f"{job.get('title', '')} {job.get('description', '')}"
    ) != payload.experience_level:
        return False
    if payload.salary_min is not None or payload.salary_max is not None:
        if (job.get("salary_currency") or "").upper() != (payload.salary_currency or "").upper():
            return False
        if payload.salary_min is not None and (
            job.get("salary_max") is None or job["salary_max"] < payload.salary_min
        ):
            return False
        if payload.salary_max is not None and (
            job.get("salary_min") is None or job["salary_min"] > payload.salary_max
        ):
            return False
    return True


def _insert_search_event(user_id: str, query: dict[str, Any], result_count: int) -> None:
    with database() as connection:
        connection.execute(
            "INSERT INTO job_search_events(id, user_id, query_json, result_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, protect_text(json_dump(query)), result_count, utc_now()),
        )


def _create_application_event(
    connection: Any,
    application_id: str,
    user_id: str,
    from_status: Optional[str],
    to_status: str,
    note: str = "",
) -> None:
    connection.execute(
        "INSERT INTO application_events(id, application_id, user_id, from_status, to_status, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), application_id, user_id, from_status, to_status, protect_text(note), utc_now()),
    )


def _schedule_reminder(
    connection: Any,
    user_id: str,
    *,
    reminder_type: str,
    due_at: str,
    message: str,
    application_id: Optional[str] = None,
    interview_id: Optional[str] = None,
    email_requested: bool = False,
) -> None:
    now = utc_now()
    email_status = (
        "queued" if email_requested and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL
        else "not_configured" if email_requested
        else "not_requested"
    )
    connection.execute(
        "INSERT INTO reminders(id, user_id, application_id, interview_id, reminder_type, due_at, message, "
        "email_requested, email_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), user_id, application_id, interview_id, reminder_type,
            due_at, protect_text(message), int(email_requested), email_status, now, now,
        ),
    )


def _application_preferences(connection: Any, user_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT preferences_json FROM search_preferences WHERE user_id=?", (user_id,)
    ).fetchone()
    return _json_value(reveal_text(row["preferences_json"]), {}) if row else {}


def _schedule_application_follow_up(
    connection: Any,
    user_id: str,
    application_id: str,
    company_name: str,
    applied_at: str,
) -> None:
    preferences = _application_preferences(connection, user_id)
    days = preferences.get("application_follow_up_days", 7)
    try:
        days = max(1, min(60, int(days)))
        due_at = datetime.fromisoformat(applied_at) + timedelta(days=days)
    except (ValueError, TypeError):
        days = 7
        due_at = datetime.now(timezone.utc) + timedelta(days=7)
    _schedule_reminder(
        connection, user_id, reminder_type="follow_up",
        due_at=due_at.astimezone(timezone.utc).isoformat(),
        message=f"Follow up on your application to {company_name}.",
        application_id=application_id,
        email_requested=bool(preferences.get("email_reminders")),
    )


def _rate(value: int, total: int) -> dict[str, Any]:
    return {
        "rate_percent": round(100 * value / total, 1) if total else None,
        "numerator": value,
        "denominator": total,
        "message": None if total >= 5 else "Insufficient data; at least 5 completed applications are recommended.",
    }


def _enforce_auth_rate_limit(
    request: Request,
    operation: str,
    limit: int,
    window_seconds: int,
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    rate_key = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
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
                        status_code=429,
                        detail="Too many authentication attempts. Try again after the rate limit window.",
                        headers={"Retry-After": str(window_seconds)},
                    )
                connection.execute(
                    "UPDATE auth_rate_limits SET attempts=attempts+1 WHERE rate_key=? AND operation=?",
                    (rate_key, operation),
                )
                return
        connection.execute(
            "INSERT INTO auth_rate_limits(rate_key, operation, window_started_at, attempts) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(rate_key, operation) DO UPDATE SET window_started_at=excluded.window_started_at, attempts=1",
            (rate_key, operation, now.isoformat()),
        )


def _application_analytics(connection: Any, user_id: str) -> dict[str, Any]:
    applications = [
        dict(row) for row in connection.execute(
            "SELECT id, title, company_name, location, status, applied_at, created_at FROM applications WHERE user_id=?",
            (user_id,),
        ).fetchall()
    ]
    events = connection.execute(
        "SELECT application_id, to_status, created_at FROM application_events WHERE user_id=? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    events_by_application: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_application[event["application_id"]].append(dict(event))
    completed = [
        item for item in applications
        if item["status"] in _FINAL_APPLICATION_STATUSES and item["applied_at"]
    ]
    interview_outcomes = [
        item for item in completed
        if any(event["to_status"] in {"interview", "offer"} for event in events_by_application[item["id"]])
    ]
    interview_final = [
        item for item in completed
        if any(event["to_status"] in {"interview", "offer"} for event in events_by_application[item["id"]])
        and item["status"] in {"offer", "rejected"}
    ]
    responses = [item for item in completed if item["status"] in {"offer", "rejected"}]
    offers = sum(item["status"] == "offer" for item in interview_final)
    rejection_count = sum(item["status"] == "rejected" for item in responses)
    response_days = []
    for item in responses:
        try:
            applied = datetime.fromisoformat(item["applied_at"])
            outcomes = [
                datetime.fromisoformat(event["created_at"])
                for event in events_by_application[item["id"]]
                if event["to_status"] in {"offer", "rejected"}
            ]
            if outcomes:
                delta = min(outcomes) - applied
                if delta.total_seconds() >= 0:
                    response_days.append(delta.total_seconds() / 86400)
        except ValueError:
            continue

    counts = Counter(item["status"] for item in applications)
    by_role: Counter[str] = Counter()
    by_company: Counter[str] = Counter()
    by_location: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    for item in applications:
        by_role[item["title"]] += 1
        by_company[item["company_name"]] += 1
        if item["location"]:
            by_location[item["location"]] += 1
        if item["applied_at"]:
            by_month[item["applied_at"][:7]] += 1

    def grouped_performance(group_key: str) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in applications:
            groups[item[group_key] or "Unspecified"].append(item)
        summaries = []
        for name, records in groups.items():
            outcomes = [
                item for item in records
                if item["status"] in _FINAL_APPLICATION_STATUSES and item["applied_at"]
            ]
            responded = [item for item in outcomes if item["status"] in {"offer", "rejected"}]
            interviewed = [
                item for item in outcomes
                if any(event["to_status"] in {"interview", "offer"} for event in events_by_application[item["id"]])
            ]
            interview_outcomes = [
                item for item in interviewed if item["status"] in {"offer", "rejected"}
            ]
            summaries.append({
                "name": name,
                "applications": len(records),
                "completed_outcomes": len(outcomes),
                "application_to_interview": _rate(len(interviewed), len(outcomes)),
                "overall_response_rate": _rate(len(responded), len(outcomes)),
                "interview_to_offer": _rate(
                    sum(item["status"] == "offer" for item in interview_outcomes),
                    len(interview_outcomes),
                ),
            })
        return sorted(summaries, key=lambda group: (-group["applications"], group["name"].casefold()))[:20]

    return {
        "applications_by_status": dict(counts),
        "applications_by_role": dict(by_role.most_common(20)),
        "applications_by_company": dict(by_company.most_common(20)),
        "applications_by_location": dict(by_location.most_common(20)),
        "applications_by_month": dict(sorted(by_month.items())),
        "completed_outcome_sample_size": len(responses),
        "application_to_interview": _rate(len(interview_outcomes), len(completed)),
        "interview_to_offer": _rate(offers, len(interview_final)),
        "overall_response_rate": _rate(len(responses), len(completed)),
        "rejection_rate": _rate(rejection_count, len(responses)),
        "average_response_time_days": round(sum(response_days) / len(response_days), 1) if response_days else None,
        "response_time_sample_size": len(response_days),
        "rate_definitions": {
            "pending_excluded": ["saved", "applied", "shortlisted", "assessment", "interview"],
            "completed_outcomes": ["offer", "rejected", "withdrawn"],
            "overall_response_denominator": "All applications in offer, rejected, or withdrawn status with an applied date; pending statuses, including shortlisted, are excluded. Withdrawn is a completed outcome but not an employer response.",
            "application_to_interview_denominator": "All applications in offer, rejected, or withdrawn status with an applied date; pending statuses are excluded.",
            "interview_to_offer_denominator": "Applications with an interview-history event and a completed offer/rejected outcome.",
        },
        "performance_by_role": grouped_performance("title"),
        "performance_by_company": grouped_performance("company_name"),
    }


def _send_reminder_email(recipient: str, subject: str, body: str) -> None:
    if not all((settings.SMTP_HOST, settings.SMTP_FROM_EMAIL)):
        raise RuntimeError("SMTP is not configured.")
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=ssl.create_default_context()
        ) as server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)


def process_due_reminders() -> int:
    now = utc_now()
    due_emails: list[tuple[str, str, str, str]] = []
    with database() as connection:
        reminders = connection.execute(
            """
            SELECT r.*, u.email,
                CASE
                    WHEN r.reminder_type='interview' THEN COALESCE(np.in_app_interviews, 1)
                    WHEN r.reminder_type='job_deadline' THEN COALESCE(np.in_app_deadlines, 1)
                    ELSE COALESCE(np.in_app_applications, 1)
                END AS in_app_enabled,
                CASE
                    WHEN r.reminder_type='interview' THEN COALESCE(np.email_interviews, 1)
                    WHEN r.reminder_type='job_deadline' THEN COALESCE(np.email_deadlines, 1)
                    ELSE COALESCE(np.email_applications, 1)
                END AS email_enabled
            FROM reminders r JOIN users u ON u.id=r.user_id
            LEFT JOIN career_notification_preferences np ON np.user_id=r.user_id
            WHERE r.status IN ('scheduled', 'snoozed')
              AND COALESCE(r.snoozed_until, r.due_at) <= ?
            """,
            (now,),
        ).fetchall()
        for reminder in reminders:
            connection.execute(
                "UPDATE reminders SET status='triggered', updated_at=? WHERE id=?",
                (now, reminder["id"]),
            )
            if reminder["in_app_enabled"]:
                connection.execute(
                    "INSERT INTO notifications(id, user_id, reminder_id, message, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), reminder["user_id"], reminder["id"], reminder["message"], now),
                )
            if reminder["email_requested"] and not reminder["email_enabled"]:
                connection.execute(
                    "UPDATE reminders SET email_status='disabled_by_user', updated_at=? WHERE id=?",
                    (now, reminder["id"]),
                )
            elif reminder["email_requested"] and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL:
                connection.execute(
                    "UPDATE reminders SET email_status='pending' WHERE id=?", (reminder["id"],)
                )
                due_emails.append((
                    reminder["id"], reminder["email"], reveal_text(reminder["message"]), reminder["reminder_type"]
                ))
            elif reminder["email_requested"]:
                connection.execute(
                    "UPDATE reminders SET email_status='not_configured' WHERE id=?", (reminder["id"],)
                )
    for reminder_id, email, body, reminder_type in due_emails:
        try:
            _send_reminder_email(email, "Career platform reminder", body)
        except Exception as exc:
            logger.error(f"Reminder email delivery failed ({exc.__class__.__name__}).")
            email_status = "failed"
        else:
            email_status = "sent"
        with database() as connection:
            connection.execute(
                "UPDATE reminders SET email_status=?, updated_at=? WHERE id=?",
                (email_status, utc_now(), reminder_id),
            )
    return len(due_emails)


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, tags=["Career Platform - Authentication"])
def register(payload: RegisterRequest, request: Request) -> AuthResponse:
    _enforce_auth_rate_limit(request, "register", 5, 3600)
    return register_user(payload.email, payload.password)


@router.post("/auth/login", response_model=AuthResponse, tags=["Career Platform - Authentication"])
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    _enforce_auth_rate_limit(request, "login", 10, 900)
    return login_user(payload.email, payload.password)


@router.post("/auth/google", response_model=AuthResponse, tags=["Career Platform - Authentication"])
def google_login(payload: GoogleAuthRequest, request: Request) -> AuthResponse:
    _enforce_auth_rate_limit(request, "google_login", 10, 900)
    return login_google_user(payload.credential)


@router.get("/auth/me", tags=["Career Platform - Authentication"])
def me(user: dict[str, str] = Depends(current_user)) -> dict[str, str]:
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["Career Platform - Authentication"])
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    _user: dict[str, str] = Depends(current_user),
) -> None:
    revoke_session(credentials)


@router.get("/profile/preferences", tags=["Career Platform - Profile"])
def get_preferences(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT preferences_json, updated_at FROM search_preferences WHERE user_id=?",
            (user["id"],),
        ).fetchone()
    return {"preferences": _json_value(reveal_text(row["preferences_json"]), {}) if row else {}, "updated_at": row["updated_at"] if row else None}


@router.put("/profile/preferences", tags=["Career Platform - Profile"])
def put_preferences(
    payload: SearchPreferences,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO search_preferences(user_id, preferences_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET preferences_json=excluded.preferences_json, updated_at=excluded.updated_at",
            (user["id"], protect_text(payload.model_dump_json()), now),
        )
    return {"preferences": payload.model_dump(), "updated_at": now}


def _save_resume(user_id: str, title: str, resume_text: str) -> dict[str, Any]:
    if len(resume_text.split()) < 30:
        raise HTTPException(status_code=422, detail="Resume text must contain at least 30 words.")
    parsed = _parse_resume_for_storage(resume_text)
    now = utc_now()
    profile_id = str(uuid.uuid4())
    with database() as connection:
        connection.execute("UPDATE resume_profiles SET is_primary=0 WHERE user_id=?", (user_id,))
        connection.execute(
            "INSERT INTO resume_profiles(id, user_id, title, resume_text, parsed_json, is_primary, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                profile_id, user_id, title.strip(), protect_text(resume_text),
                protect_text(json_dump(parsed)), now, now,
            ),
        )
    return {
        "id": profile_id, "title": title.strip(), "skills": parsed["skills_found"],
        "degrees": parsed["degrees_found"], "is_primary": True, "created_at": now,
    }


@router.post("/profile/resumes", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Profile"])
def save_resume_text(
    payload: ResumeProfileInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    return _save_resume(user["id"], payload.title, payload.resume_text)


@router.post("/profile/resumes/upload", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Profile"])
async def upload_resume(
    resume_file: UploadFile = File(...),
    title: str = Query(default="Primary resume", min_length=1, max_length=100),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    content = await read_upload_file(resume_file)
    resume_text, _, _ = extract_resume_text(resume_file.filename or "resume.docx", content)
    return _save_resume(user["id"], title, resume_text)


@router.get("/profile/resumes", tags=["Career Platform - Profile"])
def list_resumes(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT id, title, parsed_json, is_primary, created_at, updated_at FROM resume_profiles WHERE user_id=? ORDER BY is_primary DESC, updated_at DESC",
            (user["id"],),
        ).fetchall()
    return [
        {
            "id": row["id"], "title": row["title"], "is_primary": bool(row["is_primary"]),
            "skills": _json_value(reveal_text(row["parsed_json"]), {}).get("skills_found", []),
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }
        for row in rows
    ]


@router.get("/profile/resumes/{resume_id}", tags=["Career Platform - Profile"])
def get_resume_profile(
    resume_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        resume = user_resume(connection, user["id"], resume_id)
    return {
        "id": resume["id"],
        "title": resume["title"],
        "resume_text": resume["resume_text"],
        "parsed": resume["parsed"],
        "structured_resume": _json_value(resume.get("structured_json"), None),
        "is_primary": bool(resume["is_primary"]),
        "created_at": resume["created_at"],
        "updated_at": resume["updated_at"],
    }


@router.delete("/profile/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Career Platform - Profile"])
def delete_resume(resume_id: str, user: dict[str, str] = Depends(current_user)) -> None:
    with database() as connection:
        cursor = connection.execute(
            "DELETE FROM resume_profiles WHERE id=? AND user_id=?", (resume_id, user["id"])
        )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Resume profile was not found.")


@router.get("/providers", tags=["Career Platform - Job Providers"])
def list_providers(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    return provider_status()


@router.post("/discover", tags=["Career Platform - Job Discovery"])
def discover_jobs(
    payload: JobSearchRequest,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    response = search_authorized_providers(
        payload.query, payload.location, payload.country, payload.page, payload.page_size
    )
    persisted: list[dict[str, Any]] = []
    filtered_jobs = [job for job in response["jobs"] if _matches_job_filters(job, payload)]
    if payload.sort_by == "salary_high":
        filtered_jobs.sort(
            key=lambda job: job.get("salary_max") if job.get("salary_max") is not None else -1,
            reverse=True,
        )
    elif payload.sort_by == "salary_low":
        filtered_jobs.sort(
            key=lambda job: job.get("salary_min") if job.get("salary_min") is not None else float("inf")
        )
    elif payload.sort_by == "company":
        filtered_jobs.sort(key=lambda job: str(job.get("company_name") or "").casefold())
    else:
        filtered_jobs.sort(key=lambda job: job.get("posted_at") or "", reverse=True)
    with database() as connection:
        for job in filtered_jobs:
            job_id = persist_provider_job(connection, job)
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            persisted.append(_serialize_job(dict(row)))
    _insert_search_event(
        user["id"],
        payload.model_dump(exclude_none=True),
        len(persisted),
    )
    return {
        "jobs": persisted,
        "count": len(persisted),
        "page": payload.page,
        "page_size": payload.page_size,
        "has_more": response["has_more"],
        "providers": response["providers"],
        "warnings": response["warnings"],
        "data_is_live_provider_output": True,
    }


@router.post("/jobs", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Job Discovery"])
def create_manual_job(
    payload: JobCreate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        job_id = persist_private_job(connection, user["id"], payload.model_dump())
        job = visible_job(connection, job_id, user["id"])
    return _serialize_job(job)


@router.post("/jobs/analyze", tags=["Career Platform - Job Analysis"])
def analyze_job(
    payload: JobDescriptionInput,
    _user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    return analyze_job_description(
        payload.description,
        title=payload.title,
        company_name=payload.company_name,
        location=payload.location,
        source=payload.source,
    )


@router.post("/jobs/analyze-url", tags=["Career Platform - Job Analysis"])
def analyze_authorized_job_url(
    payload: JobUrlInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    url = payload.url
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE original_url=? AND visibility='public'", (url,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="This URL is not part of an authorized imported feed. Paste the job description instead; external pages are not scraped.",
            )
        job = dict(row)
    return {
        "job": _serialize_job(job),
        "analysis": analyze_job_description(
            job["description"], title=job["title"], company_name=job["company_name"],
            location=job["location"], source=job["source_label"],
        ),
        "source_url": job["source_url"],
    }


@router.get("/jobs/recommendations", tags=["Career Platform - Recommendations"])
async def recommendations(
    limit: int = Query(default=30, ge=1, le=100),
    use_ai: bool = Query(default=False),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        resume = user_resume(connection, user["id"])
        prefs_row = connection.execute(
            "SELECT preferences_json FROM search_preferences WHERE user_id=?", (user["id"],)
        ).fetchone()
        preferences = _json_value(reveal_text(prefs_row["preferences_json"]), {}) if prefs_row else {}
        jobs = connection.execute(
            "SELECT * FROM jobs WHERE visibility='public' AND availability!='expired' ORDER BY posted_at DESC LIMIT 1000"
        ).fetchall()
        saved = {
            row["job_id"] for row in connection.execute(
                "SELECT job_id FROM saved_jobs WHERE user_id=?", (user["id"],)
            ).fetchall()
        }
        dismissed = {
            row["job_id"] for row in connection.execute(
                "SELECT job_id FROM job_recommendations WHERE user_id=? AND state='dismissed'",
                (user["id"],),
            ).fetchall()
        }
        scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
        seen_listings: set[tuple[str, str, str]] = set()
        for row in jobs:
            job = dict(row)
            if job["id"] in saved or job["id"] in dismissed:
                continue
            listing_identity = tuple(
                str(job.get(field) or "").strip().casefold()
                for field in ("title", "company_name", "location")
            )
            if listing_identity in seen_listings:
                continue
            seen_listings.add(listing_identity)
            match = match_resume_to_job(
                resume["resume_text"], job["description"],
                job_title=job["title"], job_location=job.get("remote_type") or job["location"],
                preferred_locations=preferences.get("preferred_locations", []),
                work_modes=preferences.get("work_modes", []),
            )
            title_preferences = preferences.get("preferred_titles", [])
            if title_preferences:
                title_score = 100 if any(
                    title.casefold() in job["title"].casefold()
                    for title in title_preferences
                ) else 0
                match["factors"]["preferred_title"] = {
                    "weight": 0.1, "score": title_score, "preference": title_preferences
                }
            salary_floor = preferences.get("salary_min")
            salary_ceiling = preferences.get("salary_max")
            salary_currency = preferences.get("salary_currency")
            if (salary_floor is not None or salary_ceiling is not None) and (
                job.get("salary_min") is not None or job.get("salary_max") is not None
            ):
                salary_score = None
                currency_matches = (
                    (job.get("salary_currency") or "").upper() == (salary_currency or "").upper()
                )
                enough_salary_data = (
                    (salary_floor is None or job.get("salary_max") is not None)
                    and (salary_ceiling is None or job.get("salary_min") is not None)
                )
                if currency_matches and enough_salary_data:
                    salary_score = 100 if (
                        (salary_floor is None or job["salary_max"] >= salary_floor)
                        and (salary_ceiling is None or job["salary_min"] <= salary_ceiling)
                    ) else 0
                match["factors"]["salary_expectation"] = {
                    "weight": 0.05, "score": salary_score,
                    "currency": job.get("salary_currency"), "salary_minimum": salary_floor,
                    "salary_maximum": salary_ceiling,
                    "note": "Compared only when both sides disclose the same currency.",
                }
            preferred_level = preferences.get("experience_level")
            if preferred_level:
                level = _infer_experience_level(f"{job['title']} {job['description']}")
                match["factors"]["experience_level_preference"] = {
                    "weight": 0.05,
                    "score": 100 if level == preferred_level else 0 if level else None,
                    "preferred": preferred_level,
                    "listing_level": level,
                    "note": "Level is inferred only from explicit title or description wording.",
                }
            preferred_employment = preferences.get("employment_types", [])
            if preferred_employment and job.get("employment_type"):
                employment_score = 100 if any(
                    item.casefold() in job["employment_type"].casefold()
                    for item in preferred_employment
                ) else 0
                match["factors"]["employment_preference"] = {
                    "weight": 0.05, "score": employment_score,
                    "preferred": preferred_employment,
                }
            raw_job = _json_value(job.get("raw_json"), {})
            preferred_industries = preferences.get("industries", [])
            job_industry = raw_job.get("category") or ""
            if preferred_industries and job_industry:
                industry_score = 100 if any(
                    item.casefold() in job_industry.casefold()
                    for item in preferred_industries
                ) else 0
                match["factors"]["industry_preference"] = {
                    "weight": 0.05, "score": industry_score,
                    "source_value": job_industry,
                }
            career_goals = preferences.get("career_goals", "")
            if career_goals:
                goal_terms = {
                    token.casefold() for token in career_goals.split() if len(token) > 3
                }
                posting_terms = {
                    token.casefold() for token in f"{job['title']} {job['description']}".split()
                    if len(token) > 3
                }
                match["factors"]["career_goal_alignment"] = {
                    "weight": 0.05,
                    "score": round(100 * len(goal_terms & posting_terms) / len(goal_terms), 1) if goal_terms else None,
                    "matched_terms": sorted(goal_terms & posting_terms),
                }
            scores = [
                (factor["score"], factor["weight"])
                for factor in match["factors"].values()
                if factor.get("score") is not None
            ]
            match["score"] = round(
                sum(value * weight for value, weight in scores) / sum(weight for _, weight in scores), 1
            ) if scores else 0.0
            job["raw"] = raw_job
            job = _serialize_job(job)
            job["raw"] = None
            explanation = {
                "score": match["score"],
                "factors": match["factors"],
                "matched_skills": [item["skill"] for item in match["matched_skills"]],
                "missing_required_skills": match["missing_required_skills"],
                "reason": (
                    f"{len(match['matched_skills'])} required skills have resume evidence; "
                    f"{len(match['missing_required_skills'])} required skills were not found."
                ),
            }
            scored.append((match["score"], job, explanation))
            connection.execute(
                """
                INSERT INTO job_recommendations(user_id, job_id, resume_id, score, explanation_json, state, first_recommended_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                ON CONFLICT(user_id, job_id) DO UPDATE SET
                    resume_id=excluded.resume_id, score=excluded.score,
                    explanation_json=excluded.explanation_json, updated_at=excluded.updated_at
                WHERE job_recommendations.state='active'
                """,
                (
                    user["id"], job["id"], resume["id"], match["score"],
                    protect_text(json_dump(explanation)), utc_now(), utc_now(),
                ),
            )
        rec_rows = connection.execute(
            "SELECT job_id FROM job_recommendations WHERE user_id=? AND state='active' ORDER BY score DESC, first_recommended_at DESC",
            (user["id"],),
        ).fetchall()
        rank = {row["job_id"]: index for index, row in enumerate(rec_rows)}
        scored.sort(key=lambda item: (-item[0], rank.get(item[1]["id"], 10**9)))
    selected = scored[:limit]
    if use_ai and selected:
        ai_candidates = [job for _, job, _ in selected[:30]]
        ai_ranked_ids = await run_charged_ai_operation(
            user["id"],
            "job_recommendation_rerank",
            lambda: rank_job_candidates_with_ai(
                resume["resume_text"], preferences, ai_candidates
            ),
        )
        ai_order = {job_id: index for index, job_id in enumerate(ai_ranked_ids)}
        deterministic_order = {
            item[1]["id"]: index for index, item in enumerate(selected)
        }
        selected.sort(
            key=lambda item: ai_order.get(
                item[1]["id"], len(ai_order) + deterministic_order[item[1]["id"]]
            )
        )
    return {
        "resume_id": resume["id"],
        "recommendation_method": "ai_reranked" if use_ai and selected else "deterministic_evidence_match",
        "recommendations": [
            {"job": job, "match": match} for _, job, match in selected
        ],
    }


@router.post("/jobs/{job_id}/save", status_code=status.HTTP_200_OK, tags=["Career Platform - Saved Jobs"])
def save_job(job_id: str, user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        visible_job(connection, job_id, user["id"])
        connection.execute(
            "INSERT OR IGNORE INTO saved_jobs(user_id, job_id, saved_at) VALUES (?, ?, ?)",
            (user["id"], job_id, utc_now()),
        )
        connection.execute(
            "UPDATE job_recommendations SET state='saved', updated_at=? WHERE user_id=? AND job_id=?",
            (utc_now(), user["id"], job_id),
        )
        return {"saved": True, "job_id": job_id}


@router.delete("/jobs/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT, tags=["Career Platform - Saved Jobs"])
def unsave_job(job_id: str, user: dict[str, str] = Depends(current_user)) -> None:
    with database() as connection:
        connection.execute(
            "DELETE FROM saved_jobs WHERE user_id=? AND job_id=?", (user["id"], job_id)
        )


@router.post("/jobs/{job_id}/dismiss", tags=["Career Platform - Recommendations"])
def dismiss_job(job_id: str, user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        visible_job(connection, job_id, user["id"])
        connection.execute(
            """
            INSERT INTO job_recommendations(user_id, job_id, score, explanation_json, state, first_recommended_at, updated_at)
            VALUES (?, ?, 0, '{}', 'dismissed', ?, ?)
            ON CONFLICT(user_id, job_id) DO UPDATE SET state='dismissed', updated_at=excluded.updated_at
            """,
            (user["id"], job_id, utc_now(), utc_now()),
        )
    return {"dismissed": True, "job_id": job_id}


@router.get("/jobs/saved", tags=["Career Platform - Saved Jobs"])
def saved_jobs(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT j.*, s.saved_at FROM saved_jobs s JOIN jobs j ON j.id=s.job_id
            WHERE s.user_id=? ORDER BY s.saved_at DESC
            """,
            (user["id"],),
        ).fetchall()
        return [_serialize_job(visible_job(connection, row["id"], user["id"]) | {"saved_at": row["saved_at"]}) for row in rows]


@router.get("/jobs/job/{job_id}", tags=["Career Platform - Job Discovery"])
def job_detail(job_id: str, user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        job = visible_job(connection, job_id, user["id"])
        saved = connection.execute(
            "SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?", (user["id"], job_id)
        ).fetchone()
    return {**_serialize_job(job), "is_saved": saved is not None}


@router.get("/jobs/job/{job_id}/similar", tags=["Career Platform - Recommendations"])
def similar_jobs(
    job_id: str,
    limit: int = Query(default=10, ge=1, le=30),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        target = visible_job(connection, job_id, user["id"])
        target_analysis = analyze_job_description(target["description"])
        target_skills = {
            skill.casefold()
            for skill in target_analysis["requirements"]["required_skills"]
            + target_analysis["requirements"]["preferred_skills"]
        }
        target_terms = {
            token.casefold()
            for token in re.findall(r"[a-z0-9+#.]+", target["title"])
            if len(token) > 2
        }
        candidates = connection.execute(
            "SELECT * FROM jobs WHERE visibility='public' AND id!=? AND availability!='expired' "
            "ORDER BY posted_at DESC LIMIT 1000",
            (job_id,),
        ).fetchall()
        scored: list[dict[str, Any]] = []
        seen_listings: set[tuple[str, str, str]] = set()
        for row in candidates:
            candidate = dict(row)
            listing_identity = tuple(
                str(candidate.get(field) or "").strip().casefold()
                for field in ("title", "company_name", "location")
            )
            if listing_identity in seen_listings:
                continue
            seen_listings.add(listing_identity)
            analysis = analyze_job_description(candidate["description"])
            candidate_skills = {
                skill.casefold()
                for skill in analysis["requirements"]["required_skills"]
                + analysis["requirements"]["preferred_skills"]
            }
            shared_skills = sorted(target_skills & candidate_skills)
            candidate_terms = {
                token.casefold()
                for token in re.findall(r"[a-z0-9+#.]+", candidate["title"])
                if len(token) > 2
            }
            shared_title_terms = target_terms & candidate_terms
            skill_similarity = (
                len(shared_skills) / len(target_skills | candidate_skills)
                if target_skills or candidate_skills else 0
            )
            title_similarity = (
                len(shared_title_terms) / len(target_terms | candidate_terms)
                if target_terms or candidate_terms else 0
            )
            similarity = round(
                100 * (0.8 * skill_similarity + 0.2 * title_similarity), 1
            )
            if similarity <= 0:
                continue
            scored.append({
                "job": _serialize_job(candidate),
                "similarity_score": similarity,
                "shared_skills": shared_skills,
                "reason": (
                    f"Shares {len(shared_skills)} extracted skill(s)"
                    + (f" and {len(shared_title_terms)} role term(s)." if shared_title_terms else ".")
                ),
            })
    scored.sort(
        key=lambda item: (item["similarity_score"], item["job"].get("posted_at") or ""),
        reverse=True,
    )
    return {
        "based_on": {"id": target["id"], "title": target["title"]},
        "method": "deterministic_skill_and_title_similarity",
        "jobs": scored[:limit],
    }


@router.get("/market/demand", tags=["Career Platform - Market Intelligence"])
def market_demand(
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=10, ge=3, le=25),
    _user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    skill_postings: Counter[str] = Counter()
    role_postings: Counter[str] = Counter()
    industry_postings: Counter[str] = Counter()
    source_postings: Counter[str] = Counter()
    with database() as connection:
        rows = connection.execute(
            "SELECT title, description, source, source_label, raw_json FROM jobs "
            "WHERE visibility='public' AND availability!='expired' AND posted_at IS NOT NULL "
            "AND datetime(posted_at)>=datetime(?)",
            (cutoff,),
        ).fetchall()
    for row in rows:
        analysis = analyze_job_description(row["description"])
        skill_postings.update({
            skill.casefold(): 1 for skill in (
                analysis["requirements"]["required_skills"]
                + analysis["requirements"]["preferred_skills"]
            )
        })
        role_postings[row["title"].strip()] += 1
        source_postings[row["source_label"] or row["source"]] += 1
        category = _json_value(row["raw_json"], {}).get("category")
        if category:
            industry_postings[str(category)] += 1
    return {
        "window_days": days,
        "sample_size": len(rows),
        "skills": [{"name": name, "postings": count} for name, count in skill_postings.most_common(limit)],
        "roles": [{"name": name, "postings": count} for name, count in role_postings.most_common(limit)],
        "industries": [{"name": name, "postings": count} for name, count in industry_postings.most_common(limit)],
        "sources": [{"name": name, "postings": count} for name, count in source_postings.most_common()],
        "disclaimer": "Counts reflect only dated, non-expired listings retrieved from configured authorized providers; they are not a complete labor-market census.",
    }


@router.post("/jobs/job/{job_id}/tailor", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Resume Tailoring"])
def create_job_tailoring_review(
    job_id: str,
    resume_id: Optional[str] = Query(default=None),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        job = visible_job(connection, job_id, user["id"])
        resume = user_resume(connection, user["id"], resume_id)
        analysis = create_tailoring_review(
            resume["resume_text"], job["title"], job["description"], job.get("location")
        )
        session_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO tailoring_sessions(id, user_id, job_id, resume_id, analysis_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'review', ?, ?)",
            (session_id, user["id"], job_id, resume["id"], protect_text(json_dump(analysis)), now, now),
        )
    return {"id": session_id, "job": _serialize_job(job), **analysis, "created_at": now}


@router.get("/tailoring/{session_id}", tags=["Career Platform - Resume Tailoring"])
def get_tailoring_review(
    session_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM tailoring_sessions WHERE id=? AND user_id=?", (session_id, user["id"])
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Tailoring review was not found.")
    return {"id": row["id"], "status": row["status"], **_json_value(reveal_text(row["analysis_json"]), {})}


@router.patch("/tailoring/{session_id}", tags=["Career Platform - Resume Tailoring"])
def update_tailoring_review(
    session_id: str,
    payload: TailoringApprovalRequest,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM tailoring_sessions WHERE id=? AND user_id=?", (session_id, user["id"])
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Tailoring review was not found.")
        if row["status"] == "saved":
            raise HTTPException(status_code=409, detail="This review has already been saved as a resume version.")
        analysis = _json_value(reveal_text(row["analysis_json"]), {})
        changes_by_id = {change["id"]: change for change in analysis.get("changes", [])}
        for update in payload.changes:
            change = changes_by_id.get(update.id)
            if change is None:
                raise HTTPException(status_code=422, detail=f"Unknown suggested change '{update.id}'.")
            change["is_accepted"] = update.is_accepted
            if update.proposed_text is not None:
                change["proposed_text"] = update.proposed_text
        now = utc_now()
        connection.execute(
            "UPDATE tailoring_sessions SET analysis_json=?, updated_at=? WHERE id=? AND user_id=?",
            (protect_text(json_dump(analysis)), now, session_id, user["id"]),
        )
    return {"id": session_id, "status": "review", **analysis}


@router.post("/tailoring/{session_id}/save-version", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Resume Tailoring"])
def save_tailored_resume_version(
    session_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        session = connection.execute(
            "SELECT * FROM tailoring_sessions WHERE id=? AND user_id=?", (session_id, user["id"])
        ).fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="Tailoring review was not found.")
        if session["status"] == "saved":
            raise HTTPException(status_code=409, detail="This tailoring review has already been saved.")
        analysis = _json_value(reveal_text(session["analysis_json"]), {})
        if not any(change.get("is_accepted") for change in analysis.get("changes", [])):
            raise HTTPException(status_code=422, detail="Approve at least one edit before saving a tailored version.")
        tailored_resume = apply_approved_changes(analysis)
        resume_text = serialize_resume(tailored_resume)
        parsed = _parse_resume_for_storage(resume_text)
        original = user_resume(connection, user["id"], session["resume_id"])
        job = visible_job(connection, session["job_id"], user["id"])
        now = utc_now()
        version_id = str(uuid.uuid4())
        version_title = f"Targeted: {job['title']} at {job['company_name']}"[:100]
        connection.execute(
            "INSERT INTO resume_profiles(id, user_id, title, resume_text, parsed_json, structured_json, is_primary, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                version_id, user["id"], version_title, protect_text(resume_text),
                protect_text(json_dump(parsed)), protect_text(tailored_resume.model_dump_json()), now, now,
            ),
        )
        connection.execute(
            "UPDATE tailoring_sessions SET status='saved', updated_at=? WHERE id=?",
            (now, session_id),
        )
    return {
        "id": version_id, "title": version_title, "source_resume_id": original["id"],
        "job_id": job["id"], "structured_resume": tailored_resume.model_dump(mode="json"),
        "saved_at": now, "export_formats": ["pdf", "docx"],
    }


@router.get("/jobs/matches", tags=["Career Platform - Matching"])
def match_history(
    limit: int = Query(default=30, ge=1, le=100),
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM job_matches WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()
    return [
        {
            "id": row["id"], "job_id": row["job_id"], "resume_id": row["resume_id"],
            "score": row["score"], "result": _json_value(reveal_text(row["result_json"]), {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.post("/jobs/match", tags=["Career Platform - Matching"])
def match_job(
    payload: MatchRequest,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        if payload.resume_id:
            resume = user_resume(connection, user["id"], payload.resume_id)
            resume_text = resume["resume_text"]
            resume_id = resume["id"]
        elif payload.resume_text:
            resume_text = payload.resume_text
            resume_id = None
        else:
            resume = user_resume(connection, user["id"])
            resume_text = resume["resume_text"]
            resume_id = resume["id"]
        job_id = payload.job_id
        job = visible_job(connection, job_id, user["id"]) if job_id else None
        description = payload.description or (job or {}).get("description", "")
        preferences_row = connection.execute(
            "SELECT preferences_json FROM search_preferences WHERE user_id=?", (user["id"],)
        ).fetchone()
        preferences = _json_value(reveal_text(preferences_row["preferences_json"]), {}) if preferences_row else {}
        result = match_resume_to_job(
            resume_text, description,
            job_title=(job or {}).get("title"),
            job_location=(job or {}).get("remote_type") or (job or {}).get("location"),
            preferred_locations=preferences.get("preferred_locations", []),
            work_modes=preferences.get("work_modes", []),
        )
        match_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO job_matches(id, user_id, resume_id, job_id, job_fingerprint, score, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                match_id, user["id"], resume_id, job_id, result["job_fingerprint"],
                result["score"], protect_text(json_dump(result)), utc_now(),
            ),
        )
    return {"id": match_id, **result}


@router.get("/skills/progress", tags=["Career Platform - Skill Gaps"])
def list_skill_progress(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT skill, status, note, updated_at FROM skill_progress WHERE user_id=? ORDER BY skill",
            (user["id"],),
        ).fetchall()
    return [{**dict(row), "note": reveal_text(row["note"])} for row in rows]


@router.put("/skills/{skill}/progress", tags=["Career Platform - Skill Gaps"])
def update_skill_progress(
    skill: str,
    payload: SkillProgressInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    skill = skill.strip()
    if not skill or len(skill) > 100:
        raise HTTPException(status_code=422, detail="Skill must be 1-100 characters.")
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO skill_progress(user_id, skill, status, note, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, skill) DO UPDATE SET status=excluded.status, note=excluded.note, updated_at=excluded.updated_at",
            (user["id"], skill, payload.status, protect_text(payload.note), now),
        )
    return {"skill": skill, **payload.model_dump(), "updated_at": now, "source": "user_self_assessment"}


@router.get("/companies/{company_name}/research", tags=["Career Platform - Company Research"])
def research_company(
    company_name: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    name = company_name.strip()
    with database() as connection:
        public_jobs = connection.execute(
            "SELECT * FROM jobs WHERE company_name=? COLLATE NOCASE AND visibility='public' ORDER BY posted_at DESC LIMIT 50",
            (name,),
        ).fetchall()
        own_applications = connection.execute(
            "SELECT title, location, original_url, description, updated_at FROM applications WHERE user_id=? AND company_name=? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 30",
            (user["id"], name),
        ).fetchall()
        own_private_jobs = connection.execute(
            "SELECT * FROM jobs WHERE company_name=? COLLATE NOCASE AND owner_user_id=? AND visibility='private'",
            (name, user["id"]),
        ).fetchall()
        company = connection.execute(
            "SELECT industry, website, updated_at FROM companies WHERE name=? COLLATE NOCASE",
            (name,),
        ).fetchone()
    if not public_jobs and not own_applications and not own_private_jobs:
        raise HTTPException(status_code=404, detail="No job or application records are available for this company.")
    postings = [dict(job) for job in public_jobs] + [dict(job) for job in own_private_jobs]
    skills: Counter[str] = Counter()
    for job in postings:
        if job["visibility"] == "private":
            job["description"] = reveal_text(job["description"])
        extracted = analyze_job_description(
            job["description"], title=job["title"], company_name=job["company_name"],
            location=job["location"], source=job["source_label"],
        )
        skills.update(extracted["requirements"]["required_skills"])
    salary_entries = [
        {
            "min": job["salary_min"], "max": job["salary_max"],
            "currency": job["salary_currency"], "period": job["salary_period"] or "unspecified",
            "source": job["source_label"], "source_url": job["source_url"],
            "verified_employer_provided": _json_value(job["raw_json"], {}).get("salary_is_predicted")
            in (0, "0", False),
        }
        for job in postings if job.get("salary_min") is not None and job.get("salary_max") is not None
    ]
    return {
        "company": name,
        "overview": None,
        "official_website": company["website"] if company else None,
        "industry": company["industry"] if company else None,
        "products_and_services": [],
        "locations": sorted({job["location"] for job in postings if job.get("location")}),
        "relevant_jobs": [
            {
                "title": job["title"], "location": job["location"], "url": job["original_url"],
                "source": job["source_label"], "posted_at": job["posted_at"],
                "availability": job["availability"],
            }
            for job in postings
        ],
        "commonly_requested_skills": [
            {"skill": skill, "count": count} for skill, count in skills.most_common(20)
        ],
        "interview_preparation_topics": [
            skill for skill, _ in skills.most_common(12)
        ],
        "salary_listings": salary_entries,
        "recent_developments": [],
        "sources": [
            {
                "url": job["source_url"], "listing_url": job["original_url"],
                "source": job["source_label"], "last_updated": job["updated_at"],
            }
            for job in postings
        ],
        "limitations": [
            "No independent company-news or corporate-profile source is configured.",
            "Company context is limited to authorized job listings and your own application records.",
            "No salary estimate is produced when postings do not disclose salary.",
        ],
        "last_updated": max((job["updated_at"] for job in postings), default=None),
    }


@router.get("/salary/intelligence", tags=["Career Platform - Salary Intelligence"])
def salary_intelligence(
    role: str = Query(..., min_length=2, max_length=120),
    location: str = Query(default="", max_length=120),
    currency: Optional[str] = Query(default=None, min_length=3, max_length=3),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT j.title, j.company_name, j.location, j.salary_min, j.salary_max,
                j.salary_currency, j.salary_period, j.source_label, j.source_url, j.original_url,
                j.raw_json, j.updated_at
            FROM jobs j
            WHERE (j.visibility='public' OR j.owner_user_id=?)
              AND j.salary_min IS NOT NULL AND j.salary_max IS NOT NULL
              AND j.title LIKE ? COLLATE NOCASE
              AND (?='' OR j.location LIKE ? COLLATE NOCASE)
              AND (? IS NULL OR j.salary_currency=? COLLATE NOCASE)
            ORDER BY j.updated_at DESC LIMIT 1000
            """,
            (user["id"], f"%{role}%", location, f"%{location}%", currency, currency),
        ).fetchall()
    by_currency: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_currency[(row["salary_currency"] or "unknown", row["salary_period"] or "unspecified")].append(dict(row))
    groups = []
    for (unit, period), records in by_currency.items():
        midpoint = [(item["salary_min"] + item["salary_max"]) / 2 for item in records]
        sizes = len(records)
        groups.append({
            "currency": unit, "reporting_period": period, "sample_size": sizes,
            "minimum": min(item["salary_min"] for item in records),
            "median": median(midpoint),
            "maximum": max(item["salary_max"] for item in records),
            "confidence": "higher" if sizes >= 20 else "moderate" if sizes >= 5 else "low",
            "data_limitations": "Descriptive statistics over listing-reported ranges only; not a market-wide estimate.",
            "source_urls": sorted({item["source_url"] for item in records}),
            "observations": [
                {
                    "job_title": item["title"], "company": item["company_name"],
                    "location": item["location"], "minimum": item["salary_min"],
                    "maximum": item["salary_max"], "source": item["source_label"],
                    "source_url": item["original_url"],
                    "verified_employer_provided": _json_value(item["raw_json"], {}).get("salary_is_predicted")
                    in (0, "0", False),
                    "last_updated": item["updated_at"],
                }
                for item in records[:100]
            ],
        })
    return {
        "role": role, "location": location or None, "groups": groups,
        "sample_size": len(rows),
        "message": None if rows else "No authorized job listings with disclosed salary data match this search.",
    }


@router.get("/applications", tags=["Career Platform - Applications"])
def list_applications(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    q: str = Query(default="", max_length=160),
    sort: str = Query(default="updated_at", pattern="^(updated_at|applied_at|company_name|title)$"),
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    if status_filter and status_filter not in _APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown application status.")
    allowed_sort = {"updated_at", "applied_at", "company_name", "title"}
    order_column = sort if sort in allowed_sort else "updated_at"
    query = "SELECT * FROM applications WHERE user_id=?"
    parameters: list[Any] = [user["id"]]
    if status_filter:
        query += " AND status=?"
        parameters.append(status_filter)
    if q.strip():
        query += " AND (title LIKE ? COLLATE NOCASE OR company_name LIKE ? COLLATE NOCASE)"
        parameters.extend([f"%{q.strip()}%", f"%{q.strip()}%"])
    query += f" ORDER BY {order_column} DESC LIMIT 500"
    with database() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [
        {
            **dict(row),
            "description": reveal_text(row["description"]),
            "notes": reveal_text(row["notes"]),
        }
        for row in rows
    ]


@router.post("/applications", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Applications"])
def create_application(
    payload: ApplicationCreate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    job = None
    with database() as connection:
        if payload.job_id:
            job = visible_job(connection, payload.job_id, user["id"])
        if payload.resume_version_id:
            resume = connection.execute(
                "SELECT id FROM resume_profiles WHERE id=? AND user_id=?",
                (payload.resume_version_id, user["id"]),
            ).fetchone()
            if resume is None:
                raise HTTPException(status_code=404, detail="Selected resume version was not found.")
        application_id = str(uuid.uuid4())
        now = utc_now()
        state = payload.status.value
        applied_at = _utc_datetime(payload.applied_at) if payload.applied_at else (
            now if state != "saved" else None
        )
        connection.execute(
            """
            INSERT INTO applications(id, user_id, job_id, title, company_name, location, original_url,
                description, source, salary_json, status, applied_at, resume_version_id, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id, user["id"], payload.job_id,
                (job or {}).get("title", payload.title),
                (job or {}).get("company_name", payload.company_name),
                (job or {}).get("location", payload.location),
                (job or {}).get("original_url", payload.original_url),
                protect_text((job or {}).get("description", payload.description)),
                (job or {}).get("source", "manual"),
                json_dump({
                    "minimum": (job or {}).get("salary_min"),
                    "maximum": (job or {}).get("salary_max"),
                    "currency": (job or {}).get("salary_currency"),
                    "period": (job or {}).get("salary_period"),
                    "source": (job or {}).get("source_label"),
                }),
                state, applied_at, payload.resume_version_id, protect_text(payload.notes), now, now,
            ),
        )
        _create_application_event(connection, application_id, user["id"], None, state)
        if state == "applied" and applied_at:
            _schedule_application_follow_up(
                connection, user["id"], application_id, (job or {}).get("company_name", payload.company_name), applied_at
            )
        return user_application(connection, application_id, user["id"])


@router.get("/applications/analytics", tags=["Career Platform - Analytics"])
def application_analytics(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        return _application_analytics(connection, user["id"])


@router.get("/applications/{application_id}/history", tags=["Career Platform - Applications"])
def application_history(application_id: str, user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        user_application(connection, application_id, user["id"])
        rows = connection.execute(
            "SELECT id, from_status, to_status, note, created_at FROM application_events "
            "WHERE application_id=? AND user_id=? ORDER BY created_at",
            (application_id, user["id"]),
        ).fetchall()
    return [
        {**dict(row), "note": reveal_text(row["note"])}
        for row in rows
    ]


@router.patch("/applications/{application_id}", tags=["Career Platform - Applications"])
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_unset=True)
    status_note = changes.pop("note", "")
    if "notes" in changes and changes["notes"] is not None:
        changes["notes"] = protect_text(changes["notes"])
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one application change.")
    with database() as connection:
        existing = user_application(connection, application_id, user["id"])
        resume_version_id = changes.get("resume_version_id")
        if resume_version_id:
            resume = connection.execute(
                "SELECT id FROM resume_profiles WHERE id=? AND user_id=?",
                (resume_version_id, user["id"]),
            ).fetchone()
            if resume is None:
                raise HTTPException(status_code=404, detail="Selected resume version was not found.")
        next_status = changes.get("status")
        if next_status is not None:
            next_status = next_status.value
            changes["status"] = next_status
            if next_status != existing["status"]:
                _create_application_event(
                    connection, application_id, user["id"], existing["status"], next_status, status_note
                )
            if next_status != "saved" and not existing["applied_at"] and "applied_at" not in changes:
                changes["applied_at"] = utc_now()
            if next_status == "applied" and existing["status"] != "applied":
                applied_at = changes.get("applied_at") or existing["applied_at"] or utc_now()
                _schedule_application_follow_up(
                    connection, user["id"], application_id, existing["company_name"], applied_at
                )
            if next_status in _FINAL_APPLICATION_STATUSES:
                connection.execute(
                    "UPDATE reminders SET status='completed', updated_at=? "
                    "WHERE application_id=? AND user_id=? AND reminder_type='follow_up' "
                    "AND status IN ('scheduled','snoozed')",
                    (utc_now(), application_id, user["id"]),
                )
        elif "notes" in changes and status_note.strip():
            _create_application_event(
                connection,
                application_id,
                user["id"],
                existing["status"],
                existing["status"],
                status_note,
            )
        if isinstance(changes.get("applied_at"), datetime):
            changes["applied_at"] = _utc_datetime(changes["applied_at"])
        assignments = ", ".join(f"{key}=?" for key in changes)
        connection.execute(
            f"UPDATE applications SET {assignments}, updated_at=? WHERE id=? AND user_id=?",
            [*changes.values(), utc_now(), application_id, user["id"]],
        )
        return user_application(connection, application_id, user["id"])


@router.post("/applications/{application_id}/draft", tags=["Career Platform - Applications"])
@router.post("/applications/{application_id}/follow-up-draft", tags=["Career Platform - Applications"], include_in_schema=False)
async def application_draft(
    application_id: str,
    payload: DraftRequest,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    if payload.draft_type == "follow_up":
        draft_type = "recruiter_follow_up"
    else:
        draft_type = payload.draft_type
    with database() as connection:
        consent = connection.execute(
            "SELECT ai_data_consent FROM career_coach_settings WHERE user_id=?",
            (user["id"],),
        ).fetchone()
        if consent is None or not consent["ai_data_consent"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enable AI profile sharing in Career Coach settings before generating application drafts.",
            )
        application = user_application(connection, application_id, user["id"])
        resume = None
        if application.get("resume_version_id"):
            resume = user_resume(connection, user["id"], application["resume_version_id"])
        elif draft_type != "application_assistant":
            resume = user_resume(connection, user["id"])

    if draft_type == "interview_follow_up":
        with database() as connection:
            interview = connection.execute(
                "SELECT id FROM interviews WHERE application_id=? AND user_id=? LIMIT 1",
                (application_id, user["id"]),
            ).fetchone()
        if interview is None:
            raise HTTPException(
                status_code=409,
                detail="Schedule or record an interview for this application before drafting an interview follow-up.",
            )

    redacted_resume = ""
    resume_evidence: dict[str, Any] = {}
    if resume:
        redacted_resume = resume["resume_text"]
        redacted_resume = re.sub(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            "[redacted email]",
            redacted_resume,
            flags=re.IGNORECASE,
        )
        redacted_resume = re.sub(
            r"(?<!\w)(?=(?:[\s().+-]*\d){10,})\+?[\d\s().-]{10,}(?!\w)",
            "[redacted phone]",
            redacted_resume,
        )
        redacted_resume = redacted_resume[:16_000]
        parsed = resume.get("parsed", {})
        resume_evidence = {
            "skills": parsed.get("skills_found", [])[:50],
            "degrees": parsed.get("degrees_found", [])[:10],
            "experience_indicators": parsed.get("experience_indicators", [])[:10],
            "verified_metrics": parsed.get("metrics_found", [])[:20],
        }

    task_instructions = {
        "application_assistant": "Give concise, actionable guidance for the next application step. Do not write a cover letter unless asked.",
        "cover_letter": "Write an editable tailored cover letter based only on the supplied resume evidence and job description. Do not invent credentials, experience, achievements, or metrics.",
        "application_email": "Write a concise professional initial job application email. Mention only supported qualifications, and do not claim a file was attached.",
        "recruiter_follow_up": "Write a polite recruiter follow-up email about the recorded application. Do not imply the recruiter has replied or invent a previous conversation.",
        "interview_follow_up": "Write a professional post-interview thank-you email. Do not invent topics discussed, interviewers, or outcomes.",
    }
    subject = {
        "application_assistant": f"Application guidance: {application['title']}",
        "cover_letter": f"Application for {application['title']}",
        "application_email": f"Application for {application['title']}",
        "recruiter_follow_up": f"Following up: {application['title']} application",
        "interview_follow_up": f"Thank you: {application['title']} interview",
    }[draft_type]
    answer = await run_charged_ai_operation(
        user["id"],
        "application_draft",
        lambda: answer_career_question({
        "question": (
            f"{task_instructions[draft_type]} Return only the draft or guidance, without enclosing "
            "it in JSON or markdown fences. Keep it editable, transparent about missing information, "
            "and suitable for the user to review before sending."
        ),
        "application": {
            "role": application["title"],
            "company": application["company_name"],
            "location": application["location"],
            "status": application["status"],
            "description": application["description"][:20_000],
            "user_notes": application["notes"][:4_000],
        },
        "resume_evidence": resume_evidence,
        "resume_text": redacted_resume,
        "user_instructions": payload.instructions.strip(),
        }),
    )
    return {
        "application_id": application_id,
        "draft_type": draft_type,
        "subject": subject,
        "body": answer,
        "editable": True,
        "automatic_sending": False,
        "review_required": True,
    }


@router.get(
    "/applications/{application_id}/drafts",
    tags=["Career Platform - Applications"],
)
def list_application_drafts(
    application_id: str,
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    with database() as connection:
        user_application(connection, application_id, user["id"])
        rows = connection.execute(
            "SELECT id, resume_profile_id, draft_type, subject, body, created_at, updated_at "
            "FROM application_drafts WHERE application_id=? AND user_id=? "
            "ORDER BY updated_at DESC LIMIT 50",
            (application_id, user["id"]),
        ).fetchall()
    return [
        {
            **dict(row),
            "subject": reveal_text(row["subject"]),
            "body": reveal_text(row["body"]),
        }
        for row in rows
    ]


@router.post(
    "/applications/{application_id}/drafts",
    status_code=status.HTTP_201_CREATED,
    tags=["Career Platform - Applications"],
)
def save_application_draft(
    application_id: str,
    payload: ApplicationDraftSaveInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    draft_id = str(uuid.uuid4())
    now = utc_now()
    with database(immediate=True) as connection:
        application = user_application(connection, application_id, user["id"])
        resume_profile_id = application.get("resume_version_id")
        if not resume_profile_id:
            resume = connection.execute(
                "SELECT id FROM resume_profiles WHERE user_id=? "
                "ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
                (user["id"],),
            ).fetchone()
            resume_profile_id = resume["id"] if resume else None
            if resume_profile_id:
                connection.execute(
                    "UPDATE applications SET resume_version_id=?, updated_at=? WHERE id=? AND user_id=?",
                    (resume_profile_id, now, application_id, user["id"]),
                )
        connection.execute(
            "INSERT INTO application_drafts(id, user_id, application_id, resume_profile_id, draft_type, "
            "subject, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                draft_id,
                user["id"],
                application_id,
                resume_profile_id,
                payload.draft_type,
                protect_text(payload.subject.strip()),
                protect_text(payload.body.strip()),
                now,
                now,
            ),
        )
    return {
        "id": draft_id,
        "application_id": application_id,
        "resume_profile_id": resume_profile_id,
        "draft_type": payload.draft_type,
        "subject": payload.subject.strip(),
        "body": payload.body.strip(),
        "created_at": now,
        "updated_at": now,
    }


@router.put(
    "/applications/{application_id}/drafts/{draft_id}",
    tags=["Career Platform - Applications"],
)
def update_application_draft(
    application_id: str,
    draft_id: str,
    payload: ApplicationDraftSaveInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    now = utc_now()
    with database(immediate=True) as connection:
        user_application(connection, application_id, user["id"])
        cursor = connection.execute(
            "UPDATE application_drafts SET draft_type=?, subject=?, body=?, updated_at=? "
            "WHERE id=? AND application_id=? AND user_id=?",
            (
                payload.draft_type,
                protect_text(payload.subject.strip()),
                protect_text(payload.body.strip()),
                now,
                draft_id,
                application_id,
                user["id"],
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved application draft was not found.")
        row = connection.execute(
            "SELECT id, resume_profile_id, draft_type, subject, body, created_at, updated_at "
            "FROM application_drafts WHERE id=? AND application_id=? AND user_id=?",
            (draft_id, application_id, user["id"]),
        ).fetchone()
    return {
        **dict(row),
        "application_id": application_id,
        "subject": reveal_text(row["subject"]),
        "body": reveal_text(row["body"]),
    }


@router.delete(
    "/applications/{application_id}/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Career Platform - Applications"],
)
def delete_application_draft(
    application_id: str,
    draft_id: str,
    user: dict[str, str] = Depends(current_user),
) -> None:
    with database(immediate=True) as connection:
        user_application(connection, application_id, user["id"])
        cursor = connection.execute(
            "DELETE FROM application_drafts WHERE id=? AND application_id=? AND user_id=?",
            (draft_id, application_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved application draft was not found.")


@router.get("/applications/priorities", tags=["Career Platform - Applications"])
def application_priorities(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    with database() as connection:
        preferences = _application_preferences(connection, user["id"])
        rows = connection.execute(
            """
            SELECT a.id, a.title, a.company_name, a.location, a.status, a.applied_at,
                a.updated_at, a.notes, j.expires_at, j.availability,
                r.score AS recommendation_score
            FROM applications a
            LEFT JOIN jobs j ON j.id=a.job_id
            LEFT JOIN job_recommendations r ON r.job_id=a.job_id AND r.user_id=a.user_id
            WHERE a.user_id=?
            ORDER BY a.updated_at DESC LIMIT 500
            """,
            (user["id"],),
        ).fetchall()
    preferred_titles = [
        value.casefold() for value in preferences.get("preferred_titles", [])
        if isinstance(value, str)
    ]
    preferred_locations = [
        value.casefold() for value in preferences.get("preferred_locations", [])
        if isinstance(value, str)
    ]
    items = []
    for row in rows:
        if row["status"] in _FINAL_APPLICATION_STATUSES:
            continue
        score = 0
        factors = []
        status_weight = {
            "interview": 20,
            "shortlisted": 18,
            "assessment": 16,
            "applied": 12,
            "saved": 8,
        }.get(row["status"], 0)
        if status_weight:
            score += status_weight
            factors.append({"factor": "Application stage", "points": status_weight, "evidence": row["status"]})

        recommendation_score = row["recommendation_score"]
        if recommendation_score is not None:
            normalized_match = float(recommendation_score)
            if normalized_match > 1:
                normalized_match /= 100
            match_points = round(max(0, min(1, normalized_match)) * 25)
            if match_points:
                score += match_points
                factors.append({
                    "factor": "Recorded resume/job match",
                    "points": match_points,
                    "evidence": "Existing saved job recommendation score",
                })

        role_text = (row["title"] or "").casefold()
        if any(title in role_text or role_text in title for title in preferred_titles if title):
            score += 12
            factors.append({"factor": "Role preference", "points": 12, "evidence": "Matches saved preferred titles"})

        location_text = (row["location"] or "").casefold()
        if any(location in location_text or location_text in location for location in preferred_locations if location):
            score += 8
            factors.append({"factor": "Location preference", "points": 8, "evidence": "Matches saved preferred locations"})

        deadline = None
        days_remaining = None
        if row["expires_at"]:
            try:
                deadline = datetime.fromisoformat(row["expires_at"])
                if deadline.tzinfo is None or deadline.utcoffset() is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                days_remaining = (deadline.astimezone(timezone.utc) - now).total_seconds() / 86400
            except ValueError:
                deadline = None
        if deadline and days_remaining is not None:
            if days_remaining < 0:
                factors.append({"factor": "Listing deadline", "points": 0, "evidence": "Source deadline has passed"})
            else:
                deadline_points = 35 if days_remaining <= 7 else 20 if days_remaining <= 30 else 8
                score += deadline_points
                factors.append({
                    "factor": "Listing deadline",
                    "points": deadline_points,
                    "evidence": f"Source deadline: {deadline.astimezone(timezone.utc).isoformat()}",
                })
        if row["availability"] == "expired":
            factors.append({"factor": "Listing availability", "points": 0, "evidence": "Listing source marks it expired"})

        items.append({
            "application_id": row["id"],
            "title": row["title"],
            "company_name": row["company_name"],
            "location": row["location"],
            "status": row["status"],
            "priority_score": min(100, score),
            "factors": factors,
            "deadline": deadline.astimezone(timezone.utc).isoformat() if deadline else None,
            "listing_availability": row["availability"],
            "updated_at": row["updated_at"],
            "notes": reveal_text(row["notes"]),
        })
    items.sort(key=lambda item: (-item["priority_score"], item["deadline"] or "9999", item["updated_at"]))
    return {
        "items": items,
        "method": "Transparent heuristic using recorded application stage, saved resume/job recommendation score, saved role and location preferences, and listing deadlines where the source provides them. No deadline is inferred.",
        "generated_at": utc_now(),
    }


@router.get("/interviews", tags=["Career Platform - Interviews"])
def list_interviews(
    upcoming_only: bool = True,
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    with database() as connection:
        sql = """
            SELECT i.*, a.title, a.company_name FROM interviews i
            JOIN applications a ON a.id=i.application_id
            WHERE i.user_id=?
        """
        params: list[Any] = [user["id"]]
        if upcoming_only:
            sql += " AND i.scheduled_at>=? AND i.status='scheduled'"
            params.append(utc_now())
        sql += " ORDER BY i.scheduled_at LIMIT 500"
        rows = connection.execute(sql, params).fetchall()
    return [
        {
            **dict(row),
            "meeting_url": reveal_text(row["meeting_url"]),
            "interviewer_details": reveal_text(row["interviewer_details"]),
            "preparation_notes": reveal_text(row["preparation_notes"]),
        }
        for row in rows
    ]


@router.post("/interviews", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Interviews"])
def create_interview(
    payload: InterviewInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    interview_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        application = user_application(connection, payload.application_id, user["id"])
        connection.execute(
            """
            INSERT INTO interviews(id, user_id, application_id, scheduled_at, timezone, interview_type,
                meeting_url, interviewer_details, preparation_notes, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
            """,
            (
                interview_id, user["id"], payload.application_id,
                _utc_datetime(payload.scheduled_at), payload.timezone, payload.interview_type,
                protect_text(payload.meeting_url or ""), protect_text(payload.interviewer_details),
                protect_text(payload.preparation_notes), now, now,
            ),
        )
        connection.execute(
            "UPDATE applications SET status='interview', updated_at=? WHERE id=? AND user_id=? AND status IN ('applied','assessment')",
            (now, payload.application_id, user["id"]),
        )
        if application["status"] != "interview":
            _create_application_event(
                connection, payload.application_id, user["id"], application["status"],
                "interview",
            )
        connection.execute(
            "INSERT INTO interview_events(id, interview_id, user_id, event_type, event_json, created_at) "
            "VALUES (?, ?, ?, 'scheduled', ?, ?)",
            (str(uuid.uuid4()), interview_id, user["id"], protect_text(json_dump({"scheduled_at": _utc_datetime(payload.scheduled_at), "timezone": payload.timezone})), now),
        )
        preferences = _application_preferences(connection, user["id"])
        for hours in preferences.get("interview_reminder_hours", [24, 1]):
            try:
                due_at = payload.scheduled_at.astimezone(timezone.utc) - timedelta(hours=int(hours))
            except (TypeError, ValueError):
                continue
            if due_at > datetime.now(timezone.utc):
                _schedule_reminder(
                    connection, user["id"], reminder_type="interview",
                    due_at=due_at.isoformat(),
                    message=f"Interview reminder: {application['title']} at {application['company_name']}.",
                    application_id=payload.application_id,
                    interview_id=interview_id,
                    email_requested=bool(preferences.get("email_reminders")),
                )
        result = dict(connection.execute("SELECT * FROM interviews WHERE id=?", (interview_id,)).fetchone())
        result["meeting_url"] = reveal_text(result["meeting_url"])
        result["interviewer_details"] = reveal_text(result["interviewer_details"])
        result["preparation_notes"] = reveal_text(result["preparation_notes"])
        return result


@router.patch("/interviews/{interview_id}", tags=["Career Platform - Interviews"])
def update_interview(
    interview_id: str,
    payload: InterviewUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide an interview update.")
    event_changes = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in changes.items()
    }
    if "scheduled_at" in changes and changes["scheduled_at"] is not None:
        changes["scheduled_at"] = _utc_datetime(changes["scheduled_at"])
    for key in ("meeting_url", "interviewer_details", "preparation_notes"):
        if key in changes and changes[key] is not None:
            changes[key] = protect_text(changes[key])
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM interviews WHERE id=? AND user_id=?", (interview_id, user["id"])
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview was not found.")
        if row["status"] in {"completed", "cancelled"}:
            raise HTTPException(status_code=409, detail="Completed or cancelled interviews cannot be changed.")
        assignments = ", ".join(f"{key}=?" for key in changes)
        connection.execute(
            f"UPDATE interviews SET {assignments}, updated_at=? WHERE id=? AND user_id=?",
            [*changes.values(), utc_now(), interview_id, user["id"]],
        )
        event_type = (
            "rescheduled" if "scheduled_at" in changes
            else changes.get("status", "updated")
        )
        connection.execute(
            "INSERT INTO interview_events(id, interview_id, user_id, event_type, event_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()), interview_id, user["id"], event_type,
                protect_text(json_dump({
                    "before": {"scheduled_at": row["scheduled_at"], "status": row["status"]},
                    "changes": event_changes,
                })),
                utc_now(),
            ),
        )
        if "scheduled_at" in changes and changes.get("status") not in {"completed", "cancelled"}:
            connection.execute(
                "UPDATE reminders SET status='completed', updated_at=? "
                "WHERE interview_id=? AND user_id=? AND reminder_type='interview' "
                "AND status IN ('scheduled','snoozed')",
                (utc_now(), interview_id, user["id"]),
            )
            preferences = _application_preferences(connection, user["id"])
            application = user_application(connection, row["application_id"], user["id"])
            new_schedule = datetime.fromisoformat(changes["scheduled_at"])
            for hours in preferences.get("interview_reminder_hours", [24, 1]):
                try:
                    due_at = new_schedule.astimezone(timezone.utc) - timedelta(hours=int(hours))
                except (TypeError, ValueError):
                    continue
                if due_at > datetime.now(timezone.utc):
                    _schedule_reminder(
                        connection, user["id"], reminder_type="interview",
                        due_at=due_at.isoformat(),
                        message=f"Interview reminder: {application['title']} at {application['company_name']}.",
                        application_id=row["application_id"],
                        interview_id=interview_id,
                        email_requested=bool(preferences.get("email_reminders")),
                    )
        if changes.get("status") in {"completed", "cancelled"}:
            connection.execute(
                "UPDATE reminders SET status='completed', updated_at=? "
                "WHERE interview_id=? AND user_id=? AND status IN ('scheduled','snoozed')",
                (utc_now(), interview_id, user["id"]),
            )
        result = dict(connection.execute("SELECT * FROM interviews WHERE id=?", (interview_id,)).fetchone())
        result["meeting_url"] = reveal_text(result["meeting_url"])
        result["interviewer_details"] = reveal_text(result["interviewer_details"])
        result["preparation_notes"] = reveal_text(result["preparation_notes"])
        return result


@router.get("/interviews/{interview_id}/history", tags=["Career Platform - Interviews"])
def interview_history(
    interview_id: str,
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    with database() as connection:
        interview = connection.execute(
            "SELECT id FROM interviews WHERE id=? AND user_id=?", (interview_id, user["id"])
        ).fetchone()
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview was not found.")
        rows = connection.execute(
            "SELECT event_type, event_json, created_at FROM interview_events "
            "WHERE interview_id=? AND user_id=? ORDER BY created_at",
            (interview_id, user["id"]),
        ).fetchall()
    return [
        {"event_type": row["event_type"], "details": _json_value(reveal_text(row["event_json"]), {}), "created_at": row["created_at"]}
        for row in rows
    ]


@router.get("/reminders", tags=["Career Platform - Reminders"])
def list_reminders(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    process_due_reminders()
    with database() as connection:
        reminders = connection.execute(
            "SELECT * FROM reminders WHERE user_id=? ORDER BY due_at DESC LIMIT 500",
            (user["id"],),
        ).fetchall()
        notifications = connection.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    return {
        "reminders": [{**dict(row), "message": reveal_text(row["message"])} for row in reminders],
        "notifications": [{**dict(row), "message": reveal_text(row["message"])} for row in notifications],
        "email_delivery_configured": bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL),
    }


@router.post("/reminders", status_code=status.HTTP_201_CREATED, tags=["Career Platform - Reminders"])
def create_reminder(
    payload: ReminderInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    reminder_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        if payload.application_id:
            user_application(connection, payload.application_id, user["id"])
        if payload.interview_id:
            row = connection.execute(
                "SELECT id FROM interviews WHERE id=? AND user_id=?",
                (payload.interview_id, user["id"]),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Interview was not found.")
        if payload.job_id:
            job = visible_job(connection, payload.job_id, user["id"])
            if not job.get("expires_at"):
                raise HTTPException(
                    status_code=422,
                    detail="This provider has not supplied a reliable application deadline.",
                )
            try:
                deadline = datetime.fromisoformat(job["expires_at"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="The provider deadline is invalid.") from exc
            due_at = datetime.fromisoformat(_utc_datetime(payload.due_at))
            if deadline <= datetime.now(timezone.utc):
                raise HTTPException(status_code=409, detail="The listed application deadline has passed.")
            if due_at > deadline:
                raise HTTPException(status_code=422, detail="A deadline reminder cannot be scheduled after the listed deadline.")
            duplicate = connection.execute(
                "SELECT id FROM reminders WHERE user_id=? AND job_id=? AND reminder_type='job_deadline' "
                "AND status IN ('scheduled', 'snoozed', 'triggered')",
                (user["id"], payload.job_id),
            ).fetchone()
            if duplicate:
                raise HTTPException(status_code=409, detail="A deadline reminder already exists for this job.")
        connection.execute(
            """
            INSERT INTO reminders(id, user_id, application_id, interview_id, job_id, reminder_type,
                due_at, message, email_requested, email_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reminder_id, user["id"], payload.application_id, payload.interview_id,
                payload.job_id, payload.reminder_type, _utc_datetime(payload.due_at), protect_text(payload.message),
                int(payload.email_requested),
                "queued" if payload.email_requested and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL else
                "not_configured" if payload.email_requested else "not_requested",
                now, now,
            ),
        )
        result = dict(connection.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone())
        result["message"] = reveal_text(result["message"])
        return result


@router.patch("/reminders/{reminder_id}", tags=["Career Platform - Reminders"])
def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide a reminder update.")
    if "snoozed_until" in changes and changes["snoozed_until"] is not None:
        changes["snoozed_until"] = _utc_datetime(changes["snoozed_until"])
    if changes.get("status") == "completed":
        changes["snoozed_until"] = None
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM reminders WHERE id=? AND user_id=?", (reminder_id, user["id"])
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Reminder was not found.")
        if row["status"] in {"completed", "triggered"}:
            raise HTTPException(status_code=409, detail="This reminder is already complete.")
        assignments = ", ".join(f"{key}=?" for key in changes)
        connection.execute(
            f"UPDATE reminders SET {assignments}, updated_at=? WHERE id=? AND user_id=?",
            [*changes.values(), utc_now(), reminder_id, user["id"]],
        )
        result = dict(connection.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone())
        result["message"] = reveal_text(result["message"])
        return result


@router.get("/analytics/search", tags=["Career Platform - Analytics"])
def search_analytics(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        events = connection.execute(
            "SELECT query_json, result_count, created_at FROM job_search_events WHERE user_id=? ORDER BY created_at",
            (user["id"],),
        ).fetchall()
        saved_count = connection.execute(
            "SELECT COUNT(*) AS count FROM saved_jobs WHERE user_id=?", (user["id"],)
        ).fetchone()["count"]
        application_count = connection.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE user_id=? AND status!='saved'",
            (user["id"],),
        ).fetchone()["count"]
        matches = connection.execute(
            "SELECT score, result_json FROM job_matches WHERE user_id=? ORDER BY created_at DESC LIMIT 1000",
            (user["id"],),
        ).fetchall()
    missing: Counter[str] = Counter()
    for row in matches:
        missing.update(_json_value(reveal_text(row["result_json"]), {}).get("missing_required_skills", []))
    average_score = sum(row["score"] for row in matches) / len(matches) if matches else None
    daily: Counter[str] = Counter(row["created_at"][:10] for row in events)
    return {
        "jobs_discovered": sum(row["result_count"] for row in events),
        "search_count": len(events),
        "jobs_saved": saved_count,
        "jobs_applied": application_count,
        "applications": _application_analytics_for_response(user["id"]),
        "average_compatibility_score": round(average_score, 1) if average_score is not None else None,
        "missing_skills": dict(missing.most_common(20)),
        "activity_by_day": dict(sorted(daily.items())),
        "match_sample_size": len(matches),
        "insufficient_data": len(matches) < 5,
    }


def _application_analytics_for_response(user_id: str) -> dict[str, Any]:
    with database() as connection:
        return _application_analytics(connection, user_id)


@router.get("/analytics", tags=["Career Platform - Analytics"])
def full_analytics(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    search = search_analytics(user)
    return {
        "job_search": search,
        "application_success": search["applications"],
        "generated_at": utc_now(),
        "source": "persisted user job search, match, saved job, and application records",
    }


@router.get("/notifications", tags=["Career Platform - Reminders"])
def list_notifications(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    return [{**dict(row), "message": reveal_text(row["message"])} for row in rows]


async def reminder_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(process_due_reminders)
        except Exception as exc:
            logger.error(f"Reminder worker iteration failed ({exc.__class__.__name__}).")
        await asyncio.sleep(60)
