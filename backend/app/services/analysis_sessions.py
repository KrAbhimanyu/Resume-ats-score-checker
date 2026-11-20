import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.db.database import database, utc_now
from app.models.analysis_progress import (
    AnalysisProgressEvent,
    AnalysisProgressLayer,
    AnalysisProgressStep,
    AnalysisSessionCreated,
    AnalysisSessionSnapshot,
    ProgressStatus,
)
from app.models.schemas import AnalysisResponse
from app.services.data_protection import protect_text, reveal_text


ANALYSIS_LAYERS: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "resume_parsing",
        "Resume Parsing",
        (
            ("validate_file", "Validate file and request"),
            ("extract_text", "Extract PDF or DOCX text"),
            ("page_word_count", "Count pages and words"),
            ("normalize_text", "Normalize extracted text"),
        ),
    ),
    (
        "section_detection",
        "Section Detection",
        (
            ("summary_section", "Detect Summary"),
            ("experience_section", "Detect Experience"),
            ("education_section", "Detect Education"),
            ("skills_section", "Detect Skills"),
            ("projects_section", "Detect Projects"),
            ("certifications_section", "Detect Certifications"),
        ),
    ),
    (
        "keyword_matching",
        "Skills and Keyword Matching",
        (
            ("skills_extraction", "Extract resume skills"),
            ("job_keyword_extraction", "Extract job description keywords"),
            ("matched_keywords", "Match keywords"),
            ("missing_keywords", "Identify missing keywords"),
        ),
    ),
    (
        "experience_impact",
        "Experience and Impact Analysis",
        (
            ("experience_extraction", "Extract experience entries"),
            ("achievement_bullets", "Detect achievement bullets"),
            ("action_verb_analysis", "Analyze action verbs"),
            ("quantified_achievements", "Find quantified achievements"),
            ("evidence_quality", "Evaluate evidence quality"),
        ),
    ),
    (
        "ats_recommendations",
        "ATS Scoring and Recommendations",
        (
            ("ats_score", "Calculate ATS score"),
            ("section_scoring", "Calculate section-wise scores"),
            ("recommendation_generation", "Generate recommendations"),
            ("final_report", "Generate final report"),
        ),
    ),
)

_SESSION_TTL = timedelta(hours=24)
_SAFE_DETAIL_KEYS = {
    "file_type",
    "file_size_bytes",
    "word_count",
    "pages_total",
    "pages_processed",
    "pages_failed",
    "sections_detected",
    "skills_identified",
    "job_keywords",
    "matched_keywords",
    "missing_keywords",
    "action_verbs",
    "section_word_counts",
    "experience_entries_count",
    "achievement_bullets_count",
    "quantified_achievements_count",
    "action_verb_count",
    "section_found",
    "job_requirement_count",
    "matched_keyword_count",
    "missing_keyword_count",
    "matched_requirement_count",
    "missing_requirement_count",
    "quality_check_count",
    "quality_score",
    "impact_score",
    "recommendations_count",
    "rewrite_suggestions_count",
    "overall_score",
    "category_scores",
    "report_storage",
    "explanation",
}
_SAFE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_.+-]{1,64}$")
_SAFE_TERM_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+#/-]{0,63}$")
_RESULT_CACHE: dict[str, tuple[datetime, AnalysisResponse]] = {}


class AnalysisSessionNotFound(Exception):
    pass


def _session_hash(session_id: str) -> str:
    if not session_id or len(session_id) > 100:
        raise AnalysisSessionNotFound
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def _clean_details(details: dict[str, Any] | None) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in (details or {}).items():
        if key not in _SAFE_DETAIL_KEYS:
            continue
        if key in {
            "sections_detected",
            "skills_identified",
            "job_keywords",
            "matched_keywords",
            "missing_keywords",
            "action_verbs",
        } and isinstance(value, list):
            cleaned[key] = [
                item[:64]
                for item in value
                if isinstance(item, str)
                and _SAFE_TERM_PATTERN.fullmatch(item)
                and "@" not in item
                and "://" not in item
            ][:80]
        elif key == "section_word_counts" and isinstance(value, dict):
            cleaned[key] = {
                name: count
                for name, count in value.items()
                if isinstance(name, str)
                and _SAFE_TOKEN_PATTERN.fullmatch(name)
                and isinstance(count, int)
                and count >= 0
            }
        elif key == "category_scores" and isinstance(value, list):
            cleaned[key] = [
                {
                    "category_id": item["category_id"],
                    "score": item["score"],
                    "max_score": item["max_score"],
                }
                for item in value
                if isinstance(item, dict)
                and isinstance(item.get("category_id"), str)
                and _SAFE_TOKEN_PATTERN.fullmatch(item["category_id"])
                and isinstance(item.get("score"), (int, float))
                and isinstance(item.get("max_score"), (int, float))
            ][:20]
        elif key == "explanation" and isinstance(value, str):
            cleaned[key] = value[:240]
        elif isinstance(value, (bool, int, float)):
            cleaned[key] = value
        elif key in {"file_type", "report_storage"} and isinstance(value, str):
            cleaned[key] = value[:32]
    return cleaned


def _event_progress(
    status: ProgressStatus,
    step_id: str,
    details: dict[str, Any],
) -> int:
    if status in ("completed", "skipped"):
        return 100
    if status == "in_progress" and step_id == "extract_text":
        pages_total = details.get("pages_total")
        pages_processed = details.get("pages_processed")
        if (
            isinstance(pages_total, int)
            and pages_total > 0
            and isinstance(pages_processed, int)
        ):
            return round(min(pages_total, max(0, pages_processed)) / pages_total * 100)
    return 0


def create_analysis_session() -> AnalysisSessionCreated:
    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(32)
    session_hash = _session_hash(session_id)
    created_at = now.isoformat()
    expires_at = (now + _SESSION_TTL).isoformat()

    with database(immediate=True) as connection:
        connection.execute(
            "DELETE FROM ats_analysis_progress_sessions WHERE expires_at <= ?",
            (created_at,),
        )
        connection.execute(
            """
            INSERT INTO ats_analysis_progress_sessions
                (session_hash, status, created_at, updated_at, expires_at)
            VALUES (?, 'pending', ?, ?, ?)
            """,
            (session_hash, created_at, created_at, expires_at),
        )
    for cached_hash, (cached_expiry, _) in list(_RESULT_CACHE.items()):
        if cached_expiry <= now:
            _RESULT_CACHE.pop(cached_hash, None)

    layers = [
        AnalysisProgressLayer(
            layer_id=layer_id,
            label=label,
            steps=[
                AnalysisProgressStep(step_id=step_id, label=step_label)
                for step_id, step_label in steps
            ],
        )
        for layer_id, label, steps in ANALYSIS_LAYERS
    ]
    return AnalysisSessionCreated(session_id=session_id, created_at=created_at, layers=layers)


def record_progress(
    session_id: str,
    layer_id: str,
    step_id: str,
    status: ProgressStatus,
    details: dict[str, Any] | None = None,
    progress_percent: int | None = None,
) -> AnalysisProgressEvent:
    known_steps = {
        (known_layer, known_step)
        for known_layer, _, steps in ANALYSIS_LAYERS
        for known_step, _ in steps
    }
    if (layer_id, step_id) not in known_steps:
        raise ValueError("Unknown analysis progress step.")

    session_hash = _session_hash(session_id)
    now = utc_now()
    safe_details = _clean_details(details)
    if progress_percent is None:
        if status in ("completed", "skipped"):
            progress_percent = 100
        elif status == "in_progress" and step_id == "extract_text" and details:
            pages_total = details.get("pages_total")
            pages_processed = details.get("pages_processed")
            if (
                isinstance(pages_total, int)
                and pages_total > 0
                and isinstance(pages_processed, int)
            ):
                progress_percent = round(
                    min(pages_total, max(0, pages_processed)) / pages_total * 100
                )
            else:
                progress_percent = 0
        else:
            progress_percent = 0
    progress_percent = min(100, max(0, progress_percent))
    with database(immediate=True) as connection:
        session = connection.execute(
            """
            SELECT status, expires_at FROM ats_analysis_progress_sessions
            WHERE session_hash = ?
            """,
            (session_hash,),
        ).fetchone()
        if session is None or session["expires_at"] <= now:
            raise AnalysisSessionNotFound
        if session["status"] in ("completed", "failed"):
            raise ValueError("Analysis session is already complete.")

        cursor = connection.execute(
            """
            INSERT INTO ats_analysis_progress_events
                (session_hash, layer_id, step_id, status, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_hash, layer_id, step_id, status, json.dumps(safe_details), now),
        )
        error_code = "ANALYSIS_FAILED" if status == "failed" else None
        connection.execute(
            """
            UPDATE ats_analysis_progress_sessions
            SET status = ?, updated_at = ?, error_code = COALESCE(?, error_code)
            WHERE session_hash = ?
            """,
            (
                "failed" if status == "failed" else "running",
                now,
                error_code,
                session_hash,
            ),
        )
        return AnalysisProgressEvent(
            event_id=cursor.lastrowid,
            layer_id=layer_id,
            step_id=step_id,
            status=status,
            progress_percent=progress_percent,
            details=safe_details,
            created_at=now,
        )


def fail_analysis_session(session_id: str, error_code: str = "ANALYSIS_FAILED") -> None:
    session_hash = _session_hash(session_id)
    normalized_code = error_code if re.fullmatch(r"[A-Z0-9_]{1,50}", error_code) else "ANALYSIS_FAILED"
    now = utc_now()

    with database(immediate=True) as connection:
        session = connection.execute(
            """
            SELECT status, expires_at FROM ats_analysis_progress_sessions
            WHERE session_hash = ?
            """,
            (session_hash,),
        ).fetchone()
        if session is None or session["expires_at"] <= now or session["status"] in ("completed", "failed"):
            return

        latest_in_progress = connection.execute(
            """
            SELECT event.layer_id, event.step_id
            FROM ats_analysis_progress_events AS event
            WHERE event.session_hash = ? AND event.status = 'in_progress'
              AND NOT EXISTS (
                  SELECT 1 FROM ats_analysis_progress_events AS newer
                  WHERE newer.session_hash = event.session_hash
                    AND newer.layer_id = event.layer_id
                    AND newer.step_id = event.step_id
                    AND newer.id > event.id
              )
            ORDER BY event.id DESC
            LIMIT 1
            """,
            (session_hash,),
        ).fetchone()
        if latest_in_progress is None:
            first_pending = connection.execute(
                """
                SELECT layer_id, step_id
                FROM (
                    SELECT layer_id, step_id, MAX(id) AS latest_id
                    FROM ats_analysis_progress_events
                    WHERE session_hash = ?
                    GROUP BY layer_id, step_id
                ) AS latest
                JOIN ats_analysis_progress_events AS event ON event.id = latest.latest_id
                WHERE event.status IN ('pending', 'in_progress')
                ORDER BY event.id
                LIMIT 1
                """,
                (session_hash,),
            ).fetchone()
            latest_in_progress = first_pending

        if latest_in_progress is not None:
            connection.execute(
                """
                INSERT INTO ats_analysis_progress_events
                    (session_hash, layer_id, step_id, status, details_json, created_at)
                VALUES (?, ?, ?, 'failed', ?, ?)
                """,
                (
                    session_hash,
                    latest_in_progress["layer_id"],
                    latest_in_progress["step_id"],
                    json.dumps({"explanation": "The analysis could not be completed."}),
                    now,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO ats_analysis_progress_events
                    (session_hash, layer_id, step_id, status, details_json, created_at)
                VALUES (?, 'resume_parsing', 'validate_file', 'failed', ?, ?)
                """,
                (
                    session_hash,
                    json.dumps({"explanation": "The upload request did not complete."}),
                    now,
                ),
            )
        connection.execute(
            """
            UPDATE ats_analysis_progress_sessions
            SET status = 'failed', updated_at = ?, error_code = ?
            WHERE session_hash = ?
            """,
            (now, normalized_code, session_hash),
        )


def complete_analysis_session(
    session_id: str,
    result: AnalysisResponse,
    duration_ms: int,
    details: dict[str, Any] | None = None,
) -> AnalysisProgressEvent:
    session_hash = _session_hash(session_id)
    created_at = utc_now()
    result_json = result.model_dump_json()
    encryption_configured = bool(settings.JOB_DATA_ENCRYPTION_KEY.strip())
    protected_result = protect_text(result_json) if encryption_configured else None

    with database(immediate=True) as connection:
        session = connection.execute(
            """
            SELECT status, expires_at FROM ats_analysis_progress_sessions
            WHERE session_hash = ?
            """,
            (session_hash,),
        ).fetchone()
        if session is None or session["expires_at"] <= created_at:
            raise AnalysisSessionNotFound
        if session["status"] in ("completed", "failed"):
            raise ValueError("Analysis session is already complete.")
        cache_expiry = datetime.fromisoformat(session["expires_at"])

        cursor = connection.execute(
            """
            INSERT INTO ats_analysis_progress_events
                (session_hash, layer_id, step_id, status, details_json, created_at)
            VALUES (?, 'ats_recommendations', 'final_report', 'completed', ?, ?)
            """,
            (
                session_hash,
                json.dumps(
                    _clean_details({
                        **(details or {}),
                        "report_storage": "encrypted_database"
                        if encryption_configured
                        else "process_memory",
                    })
                ),
                created_at,
            ),
        )
        connection.execute(
            """
            UPDATE ats_analysis_progress_sessions
            SET status = 'completed', updated_at = ?, duration_ms = ?, result_json = ?
            WHERE session_hash = ?
            """,
            (created_at, max(0, duration_ms), protected_result, session_hash),
        )
    if not encryption_configured:
        _RESULT_CACHE[session_hash] = (cache_expiry, result)
    return AnalysisProgressEvent(
        event_id=cursor.lastrowid,
        layer_id="ats_recommendations",
        step_id="final_report",
        status="completed",
        progress_percent=100,
        details=_clean_details({
            **(details or {}),
            "report_storage": "encrypted_database"
            if encryption_configured
            else "process_memory",
        }),
        created_at=created_at,
    )


def load_analysis_session(session_id: str) -> AnalysisSessionSnapshot:
    session_hash = _session_hash(session_id)
    now = datetime.now(timezone.utc).isoformat()
    with database() as connection:
        row = connection.execute(
            """
            SELECT status, created_at, expires_at, duration_ms, error_code, result_json
            FROM ats_analysis_progress_sessions WHERE session_hash = ?
            """,
            (session_hash,),
        ).fetchone()
        if row is None or row["expires_at"] <= now:
            raise AnalysisSessionNotFound

        event_rows = connection.execute(
            """
            SELECT id, layer_id, step_id, status, details_json, created_at
            FROM ats_analysis_progress_events
            WHERE session_hash = ?
            ORDER BY id
            """,
            (session_hash,),
        ).fetchall()

    events = [
        AnalysisProgressEvent(
            event_id=event["id"],
            layer_id=event["layer_id"],
            step_id=event["step_id"],
            status=event["status"],
            progress_percent=_event_progress(
                event["status"],
                event["step_id"],
                json.loads(event["details_json"]),
            ),
            details=json.loads(event["details_json"]),
            created_at=event["created_at"],
        )
        for event in event_rows
    ]
    latest_by_step = {(event.layer_id, event.step_id): event for event in events}
    layers: list[AnalysisProgressLayer] = []
    active_layer_id = None
    for layer_id, label, steps in ANALYSIS_LAYERS:
        progress_steps = []
        statuses: list[str] = []
        for step_id, step_label in steps:
            event = latest_by_step.get((layer_id, step_id))
            step_status: ProgressStatus = event.status if event else "pending"
            step_details = event.details if event else {}
            statuses.append(step_status)
            progress_steps.append(
                AnalysisProgressStep(
                    step_id=step_id,
                    label=step_label,
                    status=step_status,
                    progress_percent=event.progress_percent if event else 0,
                    details=step_details,
                )
            )
        if "failed" in statuses:
            layer_status: ProgressStatus = "failed"
        elif "in_progress" in statuses:
            layer_status = "in_progress"
            active_layer_id = active_layer_id or layer_id
        elif all(status in ("completed", "skipped") for status in statuses):
            layer_status = "completed"
        else:
            layer_status = "pending"
        layers.append(
            AnalysisProgressLayer(
                layer_id=layer_id,
                label=label,
                status=layer_status,
                steps=progress_steps,
            )
        )

    result = None
    if row["result_json"]:
        result = AnalysisResponse.model_validate_json(reveal_text(row["result_json"]))
    else:
        cached_result = _RESULT_CACHE.get(session_hash)
        if cached_result and cached_result[0] > datetime.now(timezone.utc):
            result = cached_result[1]
        elif cached_result:
            _RESULT_CACHE.pop(session_hash, None)

    duration_ms = row["duration_ms"]
    if duration_ms is None and row["status"] in ("pending", "running"):
        started = datetime.fromisoformat(row["created_at"])
        duration_ms = max(
            0,
            round(
                (
                    datetime.now(timezone.utc)
                    - started.astimezone(timezone.utc)
                ).total_seconds()
                * 1000
            ),
        )

    return AnalysisSessionSnapshot(
        session_id=session_id,
        status=row["status"],
        created_at=row["created_at"],
        duration_ms=duration_ms,
        active_layer_id=active_layer_id,
        layers=layers,
        events=events,
        result=result,
        report_available=result is not None,
        error_code=row["error_code"],
    )


def load_events_after(session_id: str, event_id: int) -> list[AnalysisProgressEvent]:
    session_hash = _session_hash(session_id)
    now = utc_now()
    with database() as connection:
        session = connection.execute(
            """
            SELECT expires_at FROM ats_analysis_progress_sessions
            WHERE session_hash = ?
            """,
            (session_hash,),
        ).fetchone()
        if session is None or session["expires_at"] <= now:
            raise AnalysisSessionNotFound
        rows = connection.execute(
            """
            SELECT id, layer_id, step_id, status, details_json, created_at
            FROM ats_analysis_progress_events
            WHERE session_hash = ? AND id > ?
            ORDER BY id
            """,
            (session_hash, max(0, event_id)),
        ).fetchall()
    return [
        AnalysisProgressEvent(
            event_id=row["id"],
            layer_id=row["layer_id"],
            step_id=row["step_id"],
            status=row["status"],
            progress_percent=_event_progress(
                row["status"],
                row["step_id"],
                json.loads(row["details_json"]),
            ),
            details=json.loads(row["details_json"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
