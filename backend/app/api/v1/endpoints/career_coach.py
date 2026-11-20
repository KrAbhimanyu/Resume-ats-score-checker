import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging_config import logger
from app.db.database import database, utc_now
from app.models.career_coach_schemas import (
    CareerChatInput,
    CareerGoalInput,
    CareerGoalUpdate,
    CareerMilestoneInput,
    CareerMilestoneUpdate,
    CareerRoadmapRequest,
    CareerRoadmapUpdate,
    CoachConsentInput,
)
from app.services.career_coach_ai import answer_career_question, generate_roadmap
from app.services.business_billing import run_charged_ai_operation
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user
from app.services.job_matching import match_resume_to_job
from app.services.parser import parse_resume_content


router = APIRouter()


def _decode_json(value: Optional[str], *, expected: type = dict) -> Any:
    try:
        decoded = json.loads(reveal_text(value))
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Stored career coach data is not valid JSON")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored career coaching data could not be read.",
        ) from exc
    if not isinstance(decoded, expected):
        logger.error("Stored career coach data has an unexpected structure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored career coaching data has an invalid structure.",
        )
    return decoded


def _date_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, date) else str(value)


def _consent_enabled(connection: Any, user_id: str) -> bool:
    row = connection.execute(
        "SELECT ai_data_consent FROM career_coach_settings WHERE user_id=?",
        (user_id,),
    ).fetchone()
    return bool(row and row["ai_data_consent"])


def _require_ai_consent(user_id: str) -> None:
    with database() as connection:
        if not _consent_enabled(connection, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enable AI profile sharing in Career Coach settings before requesting personalized AI guidance.",
            )


def _goal_row(row: Any) -> dict[str, Any]:
    goal = _decode_json(row["goal_json"])
    goal.update({
        "id": row["id"],
        "goal_type": row["goal_type"],
        "status": row["status"],
        "progress": row["progress"],
        "target_date": row["target_date"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    })
    return goal


def _milestone_row(row: Any) -> dict[str, Any]:
    milestone = _decode_json(row["milestone_json"])
    milestone.update({
        "id": row["id"],
        "status": row["status"],
        "due_date": row["due_date"],
        "sort_order": row["sort_order"],
        "completed_at": row["completed_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    })
    return milestone


def _roadmap_row(connection: Any, row: Any) -> dict[str, Any]:
    stored = _decode_json(row["roadmap_json"])
    milestone_rows = connection.execute(
        "SELECT * FROM career_coach_milestones WHERE roadmap_id=? AND user_id=? "
        "ORDER BY sort_order, created_at",
        (row["id"], row["user_id"]),
    ).fetchall()
    return {
        "id": row["id"],
        "goal_id": row["goal_id"],
        "content": stored["content"],
        "readiness": stored["readiness"],
        "readiness_method": stored["readiness_method"],
        "market_sample": stored.get("market_sample"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "milestones": [_milestone_row(item) for item in milestone_rows],
    }


def _user_resume(connection: Any, user_id: str, resume_id: Optional[str]) -> Optional[dict[str, Any]]:
    if resume_id:
        row = connection.execute(
            "SELECT id, title, resume_text FROM resume_profiles WHERE id=? AND user_id=?",
            (resume_id, user_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Resume profile not found.")
    else:
        row = connection.execute(
            "SELECT id, title, resume_text FROM resume_profiles WHERE user_id=? "
            "ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    text = reveal_text(row["resume_text"])
    return {
        "id": row["id"],
        "title": row["title"],
        "text": text,
        "evidence": parse_resume_content(text),
    }


def _redact_resume_identifiers(text: str) -> str:
    redacted = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[redacted email]",
        text,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(r"\b(?:https?://|www\.)\S+", "[redacted link]", redacted, flags=re.IGNORECASE)
    return re.sub(
        r"(?<!\w)(?=(?:[\s().+-]*\d){10,})\+?[\d\s().-]{10,}(?!\w)",
        "[redacted phone]",
        redacted,
    )


def _profile_context(
    connection: Any,
    user_id: str,
    *,
    resume_id: Optional[str] = None,
    goal_id: Optional[str] = None,
    target_role: str = "",
    current_role: str = "",
    industry: str = "",
    experience_level: str = "",
    interests: Optional[list[str]] = None,
    job_description: str = "",
    customization: str = "",
) -> dict[str, Any]:
    resume = _user_resume(connection, user_id, resume_id)
    preference_row = connection.execute(
        "SELECT preferences_json FROM search_preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()
    preferences = (
        _decode_json(preference_row["preferences_json"])
        if preference_row else {}
    )
    skill_rows = connection.execute(
        "SELECT skill, status FROM skill_progress WHERE user_id=? ORDER BY updated_at DESC LIMIT 40",
        (user_id,),
    ).fetchall()
    application_rows = connection.execute(
        "SELECT title, status, updated_at FROM applications WHERE user_id=? "
        "ORDER BY updated_at DESC LIMIT 10",
        (user_id,),
    ).fetchall()
    target_company_rows = connection.execute(
        "SELECT saved.entity_id, saved.company_name, profile.profile_json, profile.retrieved_at "
        "FROM saved_target_companies AS saved LEFT JOIN company_profile_cache AS profile "
        "ON profile.entity_id=saved.entity_id WHERE saved.user_id=? "
        "ORDER BY saved.created_at DESC LIMIT 10",
        (user_id,),
    ).fetchall()
    saved_target_companies = []
    for row in target_company_rows:
        company_profile = json.loads(row["profile_json"]) if row["profile_json"] else None
        saved_target_companies.append({
            "entity_id": row["entity_id"],
            "company_name": row["company_name"],
            "profile": {
                "description": company_profile.get("description"),
                "industry": company_profile.get("industry", []),
                "headquarters": company_profile.get("headquarters", []),
                "source": "Wikidata",
                "source_url": f"https://www.wikidata.org/wiki/{row['entity_id']}",
                "retrieved_at": row["retrieved_at"],
            } if company_profile else None,
        })
    goal_rows = connection.execute(
        "SELECT * FROM career_coach_goals WHERE user_id=? AND status!='archived' "
        "ORDER BY updated_at DESC LIMIT 8",
        (user_id,),
    ).fetchall()
    goals = []
    for row in goal_rows:
        goal = _goal_row(row)
        goal["description"] = goal.get("description", "")[:500]
        goals.append(goal)
    selected_goal = None
    if goal_id:
        goal_row = connection.execute(
            "SELECT * FROM career_coach_goals WHERE id=? AND user_id=?",
            (goal_id, user_id),
        ).fetchone()
        if goal_row is None:
            raise HTTPException(status_code=404, detail="Career goal not found.")
        selected_goal = _goal_row(goal_row)
    market_sample = _market_sample(connection, target_role, resume)
    return {
        "resume": {
            "title": resume["title"],
            "text": _redact_resume_identifiers(resume["text"])[:18_000],
            "evidence": {
                "skills": resume["evidence"]["skills_found"][:60],
                "sections": sorted(resume["evidence"]["sections"].keys()),
                "experience_indicators": resume["evidence"]["experience_indicators"][:20],
                "degrees": resume["evidence"]["degrees_found"],
            },
        } if resume else None,
        "saved_job_preferences": {
            "preferred_titles": preferences.get("preferred_titles", [])[:20],
            "industries": preferences.get("industries", [])[:20],
            "career_goals": preferences.get("career_goals", "")[:2000],
        },
        "skill_progress": [
            {"skill": row["skill"], "status": row["status"]}
            for row in skill_rows
        ],
        "application_history": [
            {"role": row["title"], "status": row["status"], "updated_at": row["updated_at"]}
            for row in application_rows
        ],
        "saved_target_companies": saved_target_companies,
        "saved_goals": goals,
        "selected_goal": selected_goal,
        "target_role": target_role,
        "current_role": current_role,
        "industry": industry,
        "experience_level": experience_level,
        "interests": interests or [],
        "job_description": job_description[:20_000],
        "customization": customization,
        "market_sample": market_sample,
    }


def _market_sample(
    connection: Any,
    target_role: str,
    resume: Optional[dict[str, Any]],
) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    now = utc_now()
    rows = connection.execute(
        "SELECT title, description FROM jobs WHERE visibility='public' "
        "AND posted_at IS NOT NULL AND posted_at>=? "
        "AND (expires_at IS NULL OR expires_at>?) "
        "ORDER BY posted_at DESC LIMIT 250",
        (cutoff, now),
    ).fetchall()
    skills = resume["evidence"]["skills_found"][:20] if resume else []
    related = 0
    skill_counts = {skill: 0 for skill in skills}
    for row in rows:
        listing = f"{row['title']} {row['description']}".casefold()
        if target_role and target_role.casefold() in listing:
            related += 1
        for skill in skills:
            if re.search(rf"(?<!\w){re.escape(skill.casefold())}(?!\w)", listing):
                skill_counts[skill] += 1
    frequent_skills = sorted(
        ({"skill": skill, "listing_count": count} for skill, count in skill_counts.items() if count),
        key=lambda item: (-item["listing_count"], item["skill"].casefold()),
    )[:10]
    return {
        "source": "configured authorized job listings stored in this installation's Career Platform",
        "observation_window_days": 30,
        "sample_size": len(rows),
        "target_role_mentions": related,
        "profile_skills_in_sample": frequent_skills,
        "limitation": "A limited, provider- and search-dependent sample; not a complete labor-market forecast.",
    }


def _readiness(
    resume: Optional[dict[str, Any]],
    job_description: str,
    interests: list[str],
    target_role: str,
) -> tuple[Optional[float], str, dict[str, Any]]:
    if resume is None:
        return None, "unavailable", {
            "message": "Save a resume to calculate a profile-based readiness indicator.",
        }
    if job_description.strip():
        match = match_resume_to_job(
            resume["text"],
            job_description,
            job_title=target_role or None,
        )
        quality_score = _profile_completeness(resume["evidence"], bool(interests or target_role))
        combined_score = round(float(match["score"]) * 0.8 + quality_score * 0.2, 1)
        return combined_score, "deterministic_job_match_with_profile_quality", {
            "message": (
                "A deterministic indicator combining an 80% resume/job evidence comparison "
                "with a 20% resume profile-completeness measure. It is not a hiring prediction."
            ),
            "resume_job_match_score": match["score"],
            "resume_quality_score": quality_score,
            "missing_required_skills": match["missing_required_skills"][:20],
            "qualification_gaps": match["qualification_gaps"][:10],
            "factors": match["factors"],
        }
    evidence = resume["evidence"]
    sections = evidence["sections"]
    score = _profile_completeness(evidence, bool(interests or target_role))
    return float(score), "resume_profile_completeness", {
        "message": (
            "Profile completeness indicator based on documented skills, experience, education, "
            "summary, and a stated career direction. It does not evaluate fit for a particular role."
        ),
        "documented_skills": len(evidence["skills_found"]),
        "documented_sections": sorted(sections.keys()),
    }


def _profile_completeness(evidence: dict[str, Any], has_career_direction: bool) -> float:
    sections = evidence["sections"]
    score = 15
    score += 25 if evidence["skills_found"] else 0
    score += 25 if evidence["has_experience_section"] else 0
    score += 15 if evidence["has_education_section"] else 0
    score += 10 if "summary" in sections else 0
    score += 10 if has_career_direction else 0
    return float(score)


def _insert_milestone(
    connection: Any,
    *,
    user_id: str,
    roadmap_id: str,
    title: str,
    description: str,
    due_date: Optional[str],
    sort_order: int,
) -> dict[str, Any]:
    milestone_id = str(uuid.uuid4())
    now = utc_now()
    data = {"title": title, "description": description}
    connection.execute(
        "INSERT INTO career_coach_milestones(id, user_id, roadmap_id, milestone_json, status, "
        "due_date, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, 'planned', ?, ?, ?, ?)",
        (
            milestone_id, user_id, roadmap_id, protect_text(json.dumps(data, ensure_ascii=False)),
            due_date, sort_order, now, now,
        ),
    )
    row = connection.execute(
        "SELECT * FROM career_coach_milestones WHERE id=? AND user_id=?",
        (milestone_id, user_id),
    ).fetchone()
    return _milestone_row(row)


def _sync_goal_progress(connection: Any, user_id: str, roadmap_id: str) -> None:
    roadmap = connection.execute(
        "SELECT goal_id FROM career_coach_roadmaps WHERE id=? AND user_id=?",
        (roadmap_id, user_id),
    ).fetchone()
    if roadmap is None or roadmap["goal_id"] is None:
        return
    counts = connection.execute(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed "
        "FROM career_coach_milestones WHERE roadmap_id=? AND user_id=?",
        (roadmap_id, user_id),
    ).fetchone()
    if counts["total"]:
        progress = round(100 * (counts["completed"] or 0) / counts["total"], 1)
        connection.execute(
            "UPDATE career_coach_goals SET progress=?, updated_at=? WHERE id=? AND user_id=?",
            (progress, utc_now(), roadmap["goal_id"], user_id),
        )


@router.get("/coach/state", tags=["Career Coach"])
def get_coach_state(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    user_id = user["id"]
    with database() as connection:
        goals = connection.execute(
            "SELECT * FROM career_coach_goals WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        roadmaps = connection.execute(
            "SELECT * FROM career_coach_roadmaps WHERE user_id=? ORDER BY updated_at DESC LIMIT 12",
            (user_id,),
        ).fetchall()
        messages = connection.execute(
            "SELECT id, role, content, created_at FROM career_coach_messages "
            "WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT 30",
            (user_id,),
        ).fetchall()
        consent = _consent_enabled(connection, user_id)
        roadmap_data = [_roadmap_row(connection, row) for row in roadmaps]
    return {
        "ai_data_consent": consent,
        "goals": [_goal_row(row) for row in goals],
        "roadmaps": roadmap_data,
        "messages": [
            {
                "id": row["id"],
                "role": row["role"],
                "content": reveal_text(row["content"]),
                "created_at": row["created_at"],
            }
            for row in reversed(messages)
        ],
    }


@router.put("/coach/consent", tags=["Career Coach"])
def set_coach_consent(
    payload: CoachConsentInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, bool]:
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO career_coach_settings(user_id, ai_data_consent, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET ai_data_consent=excluded.ai_data_consent, "
            "updated_at=excluded.updated_at",
            (user["id"], int(payload.enabled), utc_now()),
        )
    return {"ai_data_consent": payload.enabled}


@router.post("/coach/goals", status_code=status.HTTP_201_CREATED, tags=["Career Coach"])
def create_career_goal(
    payload: CareerGoalInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    goal_id = str(uuid.uuid4())
    now = utc_now()
    data = payload.model_dump(mode="json", exclude={"goal_type", "status", "progress", "target_date"})
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO career_coach_goals(id, user_id, goal_json, goal_type, status, progress, "
            "target_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                goal_id, user["id"], protect_text(json.dumps(data, ensure_ascii=False)),
                payload.goal_type, payload.status, payload.progress,
                payload.target_date.isoformat() if payload.target_date else None, now, now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM career_coach_goals WHERE id=? AND user_id=?",
            (goal_id, user["id"]),
        ).fetchone()
        return _goal_row(row)


@router.patch("/coach/goals/{goal_id}", tags=["Career Coach"])
def update_career_goal(
    goal_id: str,
    payload: CareerGoalUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    changes = payload.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one career goal field to update.")
    with database(immediate=True) as connection:
        row = connection.execute(
            "SELECT * FROM career_coach_goals WHERE id=? AND user_id=?",
            (goal_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Career goal not found.")
        data = _decode_json(row["goal_json"])
        goal_type = changes.pop("goal_type", row["goal_type"])
        goal_status = changes.pop("status", row["status"])
        progress = changes.pop("progress", row["progress"])
        target_date = changes.pop(
            "target_date",
            date.fromisoformat(row["target_date"]) if row["target_date"] else None,
        )
        if goal_status == "completed" and "progress" not in payload.model_fields_set:
            progress = 100
        data.update(changes)
        now = utc_now()
        connection.execute(
            "UPDATE career_coach_goals SET goal_json=?, goal_type=?, status=?, progress=?, target_date=?, "
            "updated_at=? WHERE id=? AND user_id=?",
            (
                protect_text(json.dumps(data, ensure_ascii=False)), goal_type, goal_status,
                progress, _date_text(target_date), now, goal_id, user["id"],
            ),
        )
        updated = connection.execute(
            "SELECT * FROM career_coach_goals WHERE id=? AND user_id=?",
            (goal_id, user["id"]),
        ).fetchone()
        return _goal_row(updated)


@router.post("/coach/roadmaps/generate", status_code=status.HTTP_201_CREATED, tags=["Career Coach"])
async def create_career_roadmap(
    payload: CareerRoadmapRequest,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    with database() as connection:
        context = _profile_context(
            connection,
            user["id"],
            resume_id=payload.resume_id,
            goal_id=payload.goal_id,
            target_role=payload.target_role,
            current_role=payload.current_role,
            industry=payload.industry,
            experience_level=payload.experience_level,
            interests=payload.interests,
            job_description=payload.job_description,
            customization=payload.customization,
        )
    content = await run_charged_ai_operation(
        user["id"], "career_roadmap", lambda: generate_roadmap(context)
    )
    with database() as connection:
        resume = _user_resume(connection, user["id"], payload.resume_id)
    readiness_score, readiness_method, readiness_detail = _readiness(
        resume,
        payload.job_description,
        payload.interests,
        payload.target_role,
    )
    roadmap_id = str(uuid.uuid4())
    now = utc_now()
    stored = {
        "content": content.model_dump(mode="json"),
        "readiness": {
            "score": readiness_score,
            "detail": readiness_detail,
        },
        "readiness_method": readiness_method,
        "market_sample": context["market_sample"],
    }
    with database(immediate=True) as connection:
        if payload.goal_id:
            goal = connection.execute(
                "SELECT id FROM career_coach_goals WHERE id=? AND user_id=?",
                (payload.goal_id, user["id"]),
            ).fetchone()
            if goal is None:
                raise HTTPException(status_code=404, detail="Career goal not found.")
        connection.execute(
            "INSERT INTO career_coach_roadmaps(id, user_id, goal_id, roadmap_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                roadmap_id, user["id"], payload.goal_id,
                protect_text(json.dumps(stored, ensure_ascii=False)), now, now,
            ),
        )
        for index, milestone in enumerate(content.milestones):
            due = (datetime.now(timezone.utc) + timedelta(days=7 * milestone.weeks_from_now)).date()
            _insert_milestone(
                connection,
                user_id=user["id"],
                roadmap_id=roadmap_id,
                title=milestone.title,
                description=milestone.description,
                due_date=due.isoformat(),
                sort_order=index,
            )
        row = connection.execute(
            "SELECT * FROM career_coach_roadmaps WHERE id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()
        return _roadmap_row(connection, row)


@router.put("/coach/roadmaps/{roadmap_id}", tags=["Career Coach"])
def update_career_roadmap(
    roadmap_id: str,
    payload: CareerRoadmapUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database(immediate=True) as connection:
        row = connection.execute(
            "SELECT * FROM career_coach_roadmaps WHERE id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Career roadmap not found.")
        stored = _decode_json(row["roadmap_json"])
        stored["content"] = payload.model_dump(mode="json")
        connection.execute(
            "UPDATE career_coach_roadmaps SET roadmap_json=?, updated_at=? WHERE id=? AND user_id=?",
            (
                protect_text(json.dumps(stored, ensure_ascii=False)),
                utc_now(), roadmap_id, user["id"],
            ),
        )
        updated = connection.execute(
            "SELECT * FROM career_coach_roadmaps WHERE id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()
        return _roadmap_row(connection, updated)


@router.post(
    "/coach/roadmaps/{roadmap_id}/milestones",
    status_code=status.HTTP_201_CREATED,
    tags=["Career Coach"],
)
def create_career_milestone(
    roadmap_id: str,
    payload: CareerMilestoneInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    with database(immediate=True) as connection:
        exists = connection.execute(
            "SELECT id FROM career_coach_roadmaps WHERE id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="Career roadmap not found.")
        count = connection.execute(
            "SELECT COUNT(*) AS total FROM career_coach_milestones WHERE roadmap_id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()["total"]
        if count >= 50:
            raise HTTPException(status_code=422, detail="A roadmap can contain at most 50 milestones.")
        milestone = _insert_milestone(
            connection,
            user_id=user["id"],
            roadmap_id=roadmap_id,
            title=payload.title,
            description=payload.description,
            due_date=payload.due_date.isoformat() if payload.due_date else None,
            sort_order=count,
        )
        _sync_goal_progress(connection, user["id"], roadmap_id)
        return milestone


@router.patch("/coach/milestones/{milestone_id}", tags=["Career Coach"])
def update_career_milestone(
    milestone_id: str,
    payload: CareerMilestoneUpdate,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    changes = payload.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one milestone field to update.")
    with database(immediate=True) as connection:
        row = connection.execute(
            "SELECT * FROM career_coach_milestones WHERE id=? AND user_id=?",
            (milestone_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Career milestone not found.")
        data = _decode_json(row["milestone_json"])
        status_value = changes.pop("status", row["status"])
        due_date = changes.pop("due_date", date.fromisoformat(row["due_date"]) if row["due_date"] else None)
        data.update(changes)
        completed_at = (
            row["completed_at"] or utc_now()
            if status_value == "completed"
            else None
        )
        connection.execute(
            "UPDATE career_coach_milestones SET milestone_json=?, status=?, due_date=?, completed_at=?, "
            "updated_at=? WHERE id=? AND user_id=?",
            (
                protect_text(json.dumps(data, ensure_ascii=False)), status_value,
                _date_text(due_date), completed_at, utc_now(),
                milestone_id, user["id"],
            ),
        )
        _sync_goal_progress(connection, user["id"], row["roadmap_id"])
        updated = connection.execute(
            "SELECT * FROM career_coach_milestones WHERE id=? AND user_id=?",
            (milestone_id, user["id"]),
        ).fetchone()
        return _milestone_row(updated)


@router.post("/coach/chat", tags=["Career Coach"])
async def chat_with_career_coach(
    payload: CareerChatInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, str]:
    _require_ai_consent(user["id"])
    with database() as connection:
        context = _profile_context(connection, user["id"])
        if payload.roadmap_id:
            roadmap = connection.execute(
                "SELECT * FROM career_coach_roadmaps WHERE id=? AND user_id=?",
                (payload.roadmap_id, user["id"]),
            ).fetchone()
            if roadmap is None:
                raise HTTPException(status_code=404, detail="Career roadmap not found.")
            saved_roadmap = _roadmap_row(connection, roadmap)
            context["selected_roadmap"] = {
                "summary": saved_roadmap["content"]["summary"],
                "career_paths": saved_roadmap["content"]["career_paths"][:3],
                "next_roles": saved_roadmap["content"]["next_roles"][:5],
                "action_plan": saved_roadmap["content"]["action_plan"][:6],
                "milestones": [
                    {
                        "title": item["title"],
                        "status": item["status"],
                        "due_date": item["due_date"],
                    }
                    for item in saved_roadmap["milestones"][:8]
                ],
            }
        previous = connection.execute(
            "SELECT role, content FROM career_coach_messages WHERE user_id=? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 8",
            (user["id"],),
        ).fetchall()
        context["recent_conversation"] = [
            {"role": row["role"], "content": reveal_text(row["content"])[:1000]}
            for row in reversed(previous)
        ]
    context["latest_user_message"] = payload.message
    answer = await run_charged_ai_operation(
        user["id"], "career_coach", lambda: answer_career_question(context)
    )
    now = utc_now()
    with database(immediate=True) as connection:
        connection.executemany(
            "INSERT INTO career_coach_messages(id, user_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (str(uuid.uuid4()), user["id"], "user", protect_text(payload.message), now),
                (str(uuid.uuid4()), user["id"], "assistant", protect_text(answer), now),
            ],
        )
    return {"response": answer, "created_at": now}
