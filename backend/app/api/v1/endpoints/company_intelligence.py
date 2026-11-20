import json
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import database, utc_now
from app.models.company_intelligence_schemas import (
    CompanyCompareInput,
    CompanyResearchAssistantInput,
    CompanyRoleOptimizeInput,
    SaveTargetCompanyInput,
)
from app.services.career_data import user_resume, visible_job
from app.services.career_coach_ai import answer_career_question
from app.services.business_billing import run_charged_ai_operation
from app.services.company_sources import company_profile, search_companies
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user
from app.services.job_matching import analyze_job_description
from app.services.job_tailoring import create_tailoring_review
from app.services.parser import parse_resume_content


router = APIRouter()
_ENTITY_PATTERN = re.compile(r"^Q[1-9][0-9]{0,11}$")


def _cached_profile(entity_id: str, *, name_hint: Optional[str] = None) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT profile_json, retrieved_at FROM company_profile_cache WHERE entity_id=?",
            (entity_id,),
        ).fetchone()
    if row:
        try:
            retrieved_at = datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00"))
            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
        except ValueError:
            retrieved_at = datetime.min.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - retrieved_at < timedelta(hours=24):
            profile = json.loads(row["profile_json"])
            profile["retrieved_at"] = row["retrieved_at"]
            return profile
    profile = company_profile(entity_id, name_hint=name_hint)
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO company_profile_cache(entity_id, company_name, profile_json, retrieved_at, source_modified_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(entity_id) DO UPDATE SET "
            "company_name=excluded.company_name, profile_json=excluded.profile_json, "
            "retrieved_at=excluded.retrieved_at, source_modified_at=excluded.source_modified_at",
            (
                entity_id, profile["name"],
                json.dumps(profile, ensure_ascii=False, separators=(",", ":")),
                profile["retrieved_at"], profile.get("source_modified_at"),
            ),
        )
    return profile


def _company_listings(connection: Any, company_name: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT id, title, company_name, location, description, original_url, source, source_label, "
        "source_url, salary_min, salary_max, salary_currency, salary_period, posted_at, updated_at, raw_json, "
        "availability, visibility FROM jobs WHERE company_name=? COLLATE NOCASE "
        "AND visibility='public' AND availability!='expired' "
        "ORDER BY posted_at DESC, updated_at DESC LIMIT 300",
        (company_name.strip(),),
    ).fetchall()
    return [dict(row) for row in rows]


def _market_evidence(
    listings: list[dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    observed_at = now or datetime.now(timezone.utc)
    cutoff = observed_at - timedelta(days=90)
    windows = Counter()
    skills: Counter[str] = Counter()
    relevant = []
    salary_records = []
    for job in listings:
        posted = None
        if job.get("posted_at"):
            try:
                posted = datetime.fromisoformat(job["posted_at"].replace("Z", "+00:00"))
                if posted.tzinfo is None:
                    posted = posted.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                posted = None
        if posted and cutoff <= posted <= observed_at:
            window_index = min(2, (observed_at - posted).days // 30)
            windows[f"days_{window_index * 30 + 1}_{(window_index + 1) * 30}"] += 1
            relevant.append(job)
        if (
            job.get("visibility") == "public"
            and posted
            and cutoff <= posted <= observed_at
            and job.get("availability") != "expired"
        ):
            analysis = analyze_job_description(
                job.get("description", ""),
                title=job.get("title"),
                company_name=job.get("company_name"),
                source=job.get("source_label", "authorized job listing"),
            )
            skills.update(analysis["requirements"]["required_skills"])
        if (
            job.get("visibility") == "public"
            and job.get("salary_min") is not None
            and job.get("salary_max") is not None
            and job.get("salary_currency")
        ):
            salary_source_data = json.loads(job.get("raw_json") or "{}")
            reported_prediction = salary_source_data.get("salary_is_predicted")
            salary_records.append({
                "role": job["title"],
                "minimum": job["salary_min"],
                "maximum": job["salary_max"],
                "currency": job["salary_currency"],
                "period": job.get("salary_period") or "unspecified",
                "source": job["source_label"],
                "source_url": job["original_url"],
                "source_provider_url": job["source_url"],
                "salary_source_type": (
                    "provider-predicted"
                    if reported_prediction in (1, "1", True)
                    else "employer-reported"
                    if reported_prediction in (0, "0", False)
                    else "not specified by provider"
                ),
                "posted_at": job.get("posted_at"),
                "retrieved_at": job["updated_at"],
            })
    return {
        "sample_size": len(relevant),
        "observation_window_days": 90,
        "listing_counts_by_period": [
            {"period": period, "count": windows.get(period, 0)}
            for period in ("days_1_30", "days_31_60", "days_61_90")
        ],
        "recent_openings": [
            {
                "job_id": job["id"],
                "title": job["title"],
                "location": job["location"],
                "url": job["original_url"],
                "source": job["source_label"],
                "source_url": job["source_url"],
                "posted_at": job["posted_at"],
                "retrieved_at": job["updated_at"],
                "availability": job["availability"],
            }
            for job in relevant[:50]
        ],
        "commonly_requested_skills": [
            {"skill": skill, "listing_count": count}
            for skill, count in skills.most_common(30)
        ],
        "salary_listings": salary_records[:100],
        "source": "authorized provider listings already retrieved by this installation",
        "retrieved_at": utc_now(),
        "limitation": (
            "This is a provider- and search-dependent sample, not the company's full hiring record. "
            "Only posted dates explicitly supplied by sources are counted."
        ),
    }


def _company_record(
    profile: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    with database() as connection:
        listings = _company_listings(connection, profile["name"])
        own_applications = connection.execute(
            "SELECT title, status, updated_at FROM applications WHERE user_id=? "
            "AND company_name=? COLLATE NOCASE ORDER BY updated_at DESC LIMIT 20",
            (user_id, profile["name"]),
        ).fetchall()
        saved = connection.execute(
            "SELECT 1 FROM saved_target_companies WHERE user_id=? AND entity_id=?",
            (user_id, profile["entity_id"]),
        ).fetchone()
    market = _market_evidence(listings)
    application_history = [
        {"role": item["title"], "status": item["status"], "last_updated": item["updated_at"]}
        for item in own_applications
    ]
    all_sources = [{
        "name": "Wikidata",
        "url": profile["source_url"],
        "source_modified_at": profile.get("source_modified_at"),
        "retrieved_at": profile["retrieved_at"],
    }]
    all_sources.extend({
        "name": item["source"],
        "url": item["source_url"],
        "listing_url": item["url"],
        "retrieved_at": item["retrieved_at"],
        "posted_at": item["posted_at"],
    } for item in market["recent_openings"])
    return {
        "company": profile["name"],
        "entity_id": profile["entity_id"],
        "profile": profile,
        "hiring": market,
        "career_growth": {
            "available_role_progression_evidence": [],
            "message": (
                "Role progression is not inferred from job titles. Review the current source-attributed "
                "job openings and required skills; no verified company promotion framework is available."
            ),
        },
        "culture": {
            "status": "unavailable",
            "message": "No authorized company-culture or employee-sentiment source is configured.",
            "source": None,
        },
        "employee_reviews": {
            "status": "unavailable",
            "message": "No authorized employee-review provider is configured; no ratings or review summaries are fabricated.",
            "source": None,
        },
        "interview_experiences": {
            "status": "unavailable",
            "message": "No authorized interview-experience or question database is configured.",
            "source": None,
        },
        "interview_preparation": {
            "status": "listing_based_topics",
            "topics": [item["skill"] for item in market["commonly_requested_skills"][:12]],
            "message": (
                "Topics are extracted from retrieved job descriptions; these are not confirmed interview questions "
                "or a verified company interview process."
            ),
            "sources": [
                {"url": item["url"], "provider_url": item["source_url"], "retrieved_at": item["retrieved_at"]}
                for item in market["recent_openings"][:20]
            ],
        },
        "application_history": application_history,
        "saved": bool(saved),
        "sources": all_sources,
        "last_updated": max(
            [profile["retrieved_at"], *(item["retrieved_at"] for item in market["recent_openings"])],
        ),
    }


@router.get("/companies/search", tags=["Company Intelligence"])
def company_search(
    q: str = Query(..., min_length=2, max_length=160),
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    del user
    return search_companies(q)


@router.get("/companies/profile/{entity_id}", tags=["Company Intelligence"])
def get_company_profile(
    entity_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    return _company_record(_cached_profile(entity_id), user["id"])


@router.get("/companies/saved", tags=["Company Intelligence"])
def list_saved_companies(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT entity_id, company_name, created_at FROM saved_target_companies "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post(
    "/companies/saved",
    status_code=status.HTTP_201_CREATED,
    tags=["Company Intelligence"],
)
def save_company(
    payload: SaveTargetCompanyInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    profile = _cached_profile(payload.entity_id, name_hint=payload.company_name)
    now = utc_now()
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO saved_target_companies(user_id, entity_id, company_name, created_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(user_id, entity_id) DO UPDATE SET "
            "company_name=excluded.company_name",
            (user["id"], profile["entity_id"], profile["name"], now),
        )
    return {
        "entity_id": profile["entity_id"],
        "company_name": profile["name"],
        "created_at": now,
    }


@router.delete("/companies/saved/{entity_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Company Intelligence"])
def remove_saved_company(
    entity_id: str,
    user: dict[str, str] = Depends(current_user),
) -> None:
    if not _ENTITY_PATTERN.fullmatch(entity_id):
        raise HTTPException(status_code=422, detail="The company entity ID is invalid.")
    with database() as connection:
        connection.execute(
            "DELETE FROM saved_target_companies WHERE user_id=? AND entity_id=?",
            (user["id"], entity_id),
        )


@router.post("/companies/compare", tags=["Company Intelligence"])
def compare_companies(
    payload: CompanyCompareInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    companies = [
        _company_record(_cached_profile(entity_id), user["id"])
        for entity_id in payload.entity_ids
    ]
    return {
        "companies": companies,
        "comparison_fields": [
            "industry", "headquarters", "employee_count", "recent_openings",
            "listing-based skills", "disclosed salaries",
        ],
        "limitations": [
            "Company culture, employee reviews, interview experiences, and validated career progression are unavailable without an authorized source.",
            "Hiring counts, skill counts, and salary observations reflect only the available authorized listing sample.",
        ],
        "compared_at": utc_now(),
    }


def _require_company_ai_consent(user_id: str) -> None:
    with database() as connection:
        consent = connection.execute(
            "SELECT ai_data_consent FROM career_coach_settings WHERE user_id=?",
            (user_id,),
        ).fetchone()
    if consent is None or not consent["ai_data_consent"]:
        raise HTTPException(
            status_code=403,
            detail="Enable AI profile sharing in the Career Coach before requesting personalized company strategy.",
        )


@router.post("/companies/research-assistant", tags=["Company Intelligence"])
async def company_research_assistant(
    payload: CompanyResearchAssistantInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_company_ai_consent(user["id"])
    profile = _cached_profile(payload.entity_id, name_hint=payload.company_name)
    company = _company_record(profile, user["id"])
    with database() as connection:
        resume = user_resume(connection, user["id"])
        career_preferences = connection.execute(
            "SELECT preferences_json FROM search_preferences WHERE user_id=?",
            (user["id"],),
        ).fetchone()
        skills = connection.execute(
            "SELECT skill, status FROM skill_progress WHERE user_id=? ORDER BY updated_at DESC LIMIT 30",
            (user["id"],),
        ).fetchall()
    parsed_resume = parse_resume_content(resume["resume_text"])
    preferences = (
        json.loads(reveal_text(career_preferences["preferences_json"]))
        if career_preferences else {}
    )
    context = {
        "task": "Produce a company-specific career and application strategy using only these sourced facts.",
        "company_profile": {
            "name": profile["name"],
            "description": profile["description"],
            "industry": profile["industry"],
            "headquarters": profile["headquarters"],
            "employee_count": profile["employee_count"],
            "official_websites": profile["official_websites"],
        },
        "company_sources": [
            {"name": "Wikidata", "url": profile["source_url"], "source_modified_at": profile["source_modified_at"], "retrieved_at": profile["retrieved_at"]},
            *[
                {"name": item["source"], "url": item["url"], "retrieved_at": item["retrieved_at"]}
                for item in company["hiring"]["recent_openings"][:15]
            ],
        ],
        "available_job_openings": company["hiring"]["recent_openings"][:15],
        "skills_from_job_listings": company["hiring"]["commonly_requested_skills"][:20],
        "disclosed_company_salary_listings": company["hiring"]["salary_listings"][:20],
        "employee_reviews": company["employee_reviews"],
        "interview_experiences": company["interview_experiences"],
        "role_title": payload.role_title,
        "user_supplied_job_description": payload.job_description[:12_000],
        "candidate_profile": {
            "resume_skills": parsed_resume["skills_found"][:50],
            "resume_sections": sorted(parsed_resume["sections"].keys()),
            "experience_indicators": parsed_resume["experience_indicators"][:15],
            "degrees": parsed_resume["degrees_found"],
            "skill_progress": [{"skill": row["skill"], "status": row["status"]} for row in skills],
            "career_goals": preferences.get("career_goals", "")[:1000],
        },
        "latest_user_message": (
            f"Research the career opportunities at {profile['name']}"
            f"{' for the ' + payload.role_title + ' role' if payload.role_title else ''}. "
            "Provide sourced company context, an application strategy personalized to the evidence-based candidate profile, "
            "and explain data gaps. Never invent hiring trends, salaries, culture, reviews, or interview questions."
        ),
    }
    response = await run_charged_ai_operation(
        user["id"], "company_research", lambda: answer_career_question(context)
    )
    return {
        "company": profile["name"],
        "response": response,
        "sources": context["company_sources"],
        "generated_at": utc_now(),
        "disclaimer": "AI synthesis is based only on the supplied sources and profile; it does not represent the employer or guarantee outcomes.",
    }


@router.post("/companies/role/optimize", tags=["Company Intelligence"])
def optimize_resume_for_company_role(
    payload: CompanyRoleOptimizeInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database() as connection:
        resume = user_resume(connection, user["id"], payload.resume_id)
        job = visible_job(connection, payload.job_id, user["id"])
        if job["company_name"].casefold() != payload.company_name.casefold():
            raise HTTPException(
                status_code=422,
                detail="Choose a job listing that belongs to the selected company.",
            )
        if job["title"].casefold() != payload.role_title.casefold():
            raise HTTPException(
                status_code=422,
                detail="The target role must match the selected company listing.",
            )
        if len(job["description"].strip()) < 30:
            raise HTTPException(status_code=422, detail="The selected job description is too short to analyze.")
        review = create_tailoring_review(
            resume["resume_text"],
            payload.role_title,
            job["description"],
            job.get("location"),
        )
        session_id = str(uuid.uuid4())
        now = utc_now()
        connection.execute(
            "INSERT INTO tailoring_sessions(id, user_id, job_id, resume_id, analysis_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'review', ?, ?)",
            (session_id, user["id"], job["id"], resume["id"], protect_text(json.dumps(review)), now, now),
        )
    return {
        "id": session_id,
        "company": payload.company_name,
        "role_title": payload.role_title,
        "analysis": review,
        "job_source": {
            "name": job["source_label"],
            "url": job["original_url"],
            "provider_url": job["source_url"],
            "posted_at": job["posted_at"],
            "retrieved_at": job["updated_at"],
        },
        "specialization": (
            "FAANG-style evidence-based review for this major technology employer. "
            "Prioritize role-relevant technical evidence and clearly described outcomes only when present in the resume; "
            "no proprietary hiring score or unsupported achievement is added."
            if re.search(
                r"\b(?:amazon|apple|facebook|google|meta(?: platforms)?|netflix)\b",
                payload.company_name,
                re.IGNORECASE,
            )
            else (
                "Uses the actual company role requirements and deterministic resume evidence. "
                "No confidential company ranking or proprietary hiring algorithm is implied."
            )
        ),
    }
