import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.db.database import utc_now
from app.services.data_protection import protect_text, reveal_text


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def row_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _company_id(connection: Any, name: str, industry: str | None = None) -> str:
    row = connection.execute(
        "SELECT id FROM companies WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    now = utc_now()
    if row:
        company_id = row["id"]
        if industry:
            connection.execute(
                "UPDATE companies SET industry=COALESCE(industry, ?), updated_at=? WHERE id=?",
                (industry, now, company_id),
            )
        return company_id
    company_id = str(uuid.uuid4())
    connection.execute(
        "INSERT INTO companies(id, name, industry, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (company_id, name, industry, now, now),
    )
    return company_id


def persist_provider_job(connection: Any, job: dict[str, Any]) -> str:
    now = utc_now()
    category = (job.get("raw") or {}).get("category")
    company_id = _company_id(connection, job["company_name"], category) if job.get("company_name") else None
    existing = connection.execute(
        "SELECT id FROM jobs WHERE source=? AND source_job_id=?",
        (job["source"], str(job["source_job_id"])),
    ).fetchone()
    if existing is None and job.get("original_url"):
        existing = connection.execute(
            "SELECT id FROM jobs WHERE visibility='public' "
            "AND rtrim(original_url, '/')=rtrim(?, '/') COLLATE NOCASE LIMIT 1",
            (job["original_url"].strip(),),
        ).fetchone()
    job_id = existing["id"] if existing else str(uuid.uuid4())
    fields = (
        job.get("title", ""),
        job.get("company_name", ""),
        job.get("location"),
        job.get("country"),
        job.get("remote_type"),
        job.get("employment_type"),
        job.get("salary_min"),
        job.get("salary_max"),
        job.get("salary_currency"),
        job.get("salary_period"),
        job.get("description", ""),
        job.get("original_url", ""),
        job.get("posted_at"),
        job.get("expires_at"),
        job.get("availability", "unknown"),
        job.get("source_label", job["source"]),
        job.get("source_url", ""),
        json_dump(job.get("raw", {})),
    )
    if existing:
        connection.execute(
            """
            UPDATE jobs SET company_id=?, title=?, company_name=?, location=?, country=?, remote_type=?,
                employment_type=?, salary_min=?, salary_max=?, salary_currency=?, salary_period=?,
                description=?, original_url=?, posted_at=?, expires_at=?, availability=?, source_label=?,
                source_url=?, raw_json=?, updated_at=? WHERE id=?
            """,
            (company_id, *fields, now, job_id),
        )
    else:
        connection.execute(
            """
            INSERT INTO jobs(id, source, source_job_id, company_id, owner_user_id, visibility,
                title, company_name, location, country, remote_type, employment_type,
                salary_min, salary_max, salary_currency, salary_period, description, original_url,
                posted_at, expires_at, availability, source_label, source_url, raw_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, 'public', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, job["source"], str(job["source_job_id"]), company_id, *fields, now, now),
        )
    if job.get("salary_min") is not None and job.get("salary_max") is not None and job.get("salary_currency"):
        connection.execute(
            """
            INSERT INTO salary_observations(id, job_id, source, minimum, maximum, currency, period, observed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, source) DO UPDATE SET minimum=excluded.minimum,
                maximum=excluded.maximum, currency=excluded.currency, period=excluded.period,
                observed_at=excluded.observed_at
            """,
            (
                str(uuid.uuid4()), job_id, job["source"], job["salary_min"],
                job["salary_max"], job["salary_currency"],
                job.get("salary_period") or "unspecified", now,
            ),
        )
    return job_id


def persist_private_job(connection: Any, user_id: str, payload: dict[str, Any]) -> str:
    url = payload.get("original_url") or ""
    fingerprint = hashlib.sha256(
        f"{user_id}|{url.casefold()}|{payload['company_name'].casefold()}|{payload['title'].casefold()}".encode("utf-8")
    ).hexdigest()
    duplicate = connection.execute(
        "SELECT id FROM jobs WHERE owner_user_id=? AND source='user_entry' AND source_job_id=?",
        (user_id, fingerprint),
    ).fetchone()
    if duplicate:
        return duplicate["id"]
    job_id = str(uuid.uuid4())
    now = utc_now()
    posted_at = payload.get("posted_at")
    if isinstance(posted_at, datetime):
        posted_at = posted_at.astimezone(timezone.utc).isoformat() if posted_at.tzinfo else posted_at.isoformat()
    currency = payload.get("salary_currency")
    connection.execute(
        """
        INSERT INTO jobs(id, source, source_job_id, owner_user_id, visibility, title, company_name,
            location, country, remote_type, employment_type, salary_min, salary_max,
            salary_currency, salary_period, description, original_url, posted_at, availability,
            source_label, source_url, raw_json, created_at, updated_at)
        VALUES (?, 'user_entry', ?, ?, 'private', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unknown',
            'User provided', ?, '{}', ?, ?)
        """,
        (
            job_id, fingerprint, user_id, payload["title"].strip(), payload["company_name"].strip(),
            payload.get("location") or None, payload.get("country"), payload.get("remote_type"),
            payload.get("employment_type"), payload.get("salary_min"), payload.get("salary_max"),
            currency.upper() if currency else None, payload.get("salary_period"),
            protect_text(payload["description"]), url, posted_at, url, now, now,
        ),
    )
    return job_id


def visible_job(connection: Any, job_id: str, user_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM jobs WHERE id=? AND (visibility='public' OR owner_user_id=?)",
        (job_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting was not found.")
    job = dict(row)
    if job.get("expires_at"):
        try:
            if datetime.fromisoformat(job["expires_at"]) <= datetime.now(timezone.utc):
                job["availability"] = "expired"
                connection.execute(
                    "UPDATE jobs SET availability='expired', updated_at=? WHERE id=?",
                    (utc_now(), job_id),
                )
        except ValueError:
            job["availability"] = "unknown"
    job["raw"] = json.loads(job.pop("raw_json") or "{}")
    if job["visibility"] == "private":
        job["description"] = reveal_text(job["description"])
    return job


def user_resume(connection: Any, user_id: str, resume_id: str | None = None) -> dict[str, Any]:
    if resume_id:
        row = connection.execute(
            "SELECT * FROM resume_profiles WHERE id=? AND user_id=?", (resume_id, user_id)
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT * FROM resume_profiles WHERE user_id=? ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save a resume to your account before using personalized recommendations.",
        )
    result = dict(row)
    result["resume_text"] = reveal_text(result["resume_text"])
    result["parsed_json"] = reveal_text(result["parsed_json"])
    if result.get("structured_json"):
        result["structured_json"] = reveal_text(result["structured_json"])
    result["parsed"] = json.loads(result.pop("parsed_json"))
    return result


def user_application(connection: Any, application_id: str, user_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM applications WHERE id=? AND user_id=?", (application_id, user_id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application was not found.")
    result = dict(row)
    result["description"] = reveal_text(result.get("description"))
    result["notes"] = reveal_text(result.get("notes"))
    return result
