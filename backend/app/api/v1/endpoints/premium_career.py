import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.database import database, utc_now
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user


router = APIRouter()

_DEFAULT_NOTIFICATION_PREFERENCES = {
    "in_app_applications": True,
    "in_app_interviews": True,
    "in_app_deadlines": True,
    "email_applications": True,
    "email_interviews": True,
    "email_deadlines": True,
}
_DEFAULT_CAREER_SCORE_WEIGHTS = {
    "resume_profile": 20,
    "career_direction": 20,
    "skills": 20,
    "opportunity_activity": 20,
    "learning_or_milestones": 20,
}


class NotificationPreferencesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_app_applications: bool
    in_app_interviews: bool
    in_app_deadlines: bool
    email_applications: bool
    email_interviews: bool
    email_deadlines: bool


class CareerScoreWeightsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_profile: int = Field(ge=0, le=100)
    career_direction: int = Field(ge=0, le=100)
    skills: int = Field(ge=0, le=100)
    opportunity_activity: int = Field(ge=0, le=100)
    learning_or_milestones: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def require_total_weight(self) -> "CareerScoreWeightsInput":
        if sum(self.model_dump().values()) != 100:
            raise ValueError("Career score weights must add up to 100.")
        return self


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(reveal_text(value))
    return parsed if isinstance(parsed, dict) else {}


def _notification_preferences(connection: Any, user_id: str) -> dict[str, bool]:
    row = connection.execute(
        "SELECT * FROM career_notification_preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if row is None:
        return dict(_DEFAULT_NOTIFICATION_PREFERENCES)
    return {key: bool(row[key]) for key in _DEFAULT_NOTIFICATION_PREFERENCES}


def _save_achievements(connection: Any, user_id: str, now: str) -> None:
    first_resume = connection.execute(
        "SELECT MIN(created_at) AS occurred_at FROM resume_profiles WHERE user_id=?", (user_id,)
    ).fetchone()["occurred_at"]
    first_saved_job = connection.execute(
        "SELECT MIN(saved_at) AS occurred_at FROM saved_jobs WHERE user_id=?", (user_id,)
    ).fetchone()["occurred_at"]
    first_application = connection.execute(
        "SELECT MIN(created_at) AS occurred_at FROM applications "
        "WHERE user_id=? AND status!='saved'",
        (user_id,),
    ).fetchone()["occurred_at"]
    learning = connection.execute(
        "SELECT completed_at FROM academy_activity_progress "
        "WHERE user_id=? AND status='completed' AND completed_at IS NOT NULL "
        "ORDER BY completed_at LIMIT 5",
        (user_id,),
    ).fetchall()
    first_milestone = connection.execute(
        "SELECT MIN(completed_at) AS occurred_at FROM career_coach_milestones "
        "WHERE user_id=? AND status='completed' AND completed_at IS NOT NULL",
        (user_id,),
    ).fetchone()["occurred_at"]
    candidates = [
        ("resume_created", "Resume ready", "Saved a resume profile.", first_resume),
        ("job_saved", "Opportunity saved", "Saved a real job listing.", first_saved_job),
        ("application_tracked", "Application tracked", "Recorded an application in the tracker.", first_application),
        ("learning_completed", "Learning milestone", "Completed a platform learning activity.", learning[0]["completed_at"] if learning else None),
        ("learning_five", "Learning momentum", "Completed five or more platform learning activities.", learning[4]["completed_at"] if len(learning) >= 5 else None),
        ("milestone_completed", "Milestone reached", "Completed a career roadmap milestone.", first_milestone),
    ]
    for key, title, description, occurred_at in candidates:
        if occurred_at:
            connection.execute(
                "INSERT OR IGNORE INTO career_achievements"
                "(user_id, achievement_key, title, description, evidence, awarded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, key, title, description, description, occurred_at or now),
            )


def _career_streak(dates: set[str], today: datetime) -> dict[str, int]:
    current_day = today.date()
    if current_day.isoformat() not in dates and (current_day - timedelta(days=1)).isoformat() not in dates:
        current = 0
    else:
        check_day = current_day if current_day.isoformat() in dates else current_day - timedelta(days=1)
        current = 0
        while check_day.isoformat() in dates:
            current += 1
            check_day -= timedelta(days=1)
    longest = 0
    run = 0
    previous = None
    for day_text in sorted(dates):
        day = datetime.fromisoformat(day_text).date()
        if day > current_day:
            continue
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    return {"current_days": current, "longest_days": longest}


@router.get("/command-center", tags=["Premium Career Command Center"])
def get_command_center(
    timeline_offset: int = Query(default=0, ge=0, le=10_000),
    timeline_limit: int = Query(default=50, ge=1, le=100),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    user_id = user["id"]
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    with database(immediate=True) as connection:
        _save_achievements(connection, user_id, now.isoformat())
        resume_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resume_profiles WHERE user_id=?", (user_id,)
        ).fetchone()["count"]
        primary_resume = connection.execute(
            "SELECT title, parsed_json, updated_at FROM resume_profiles "
            "WHERE user_id=? ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        preferences_row = connection.execute(
            "SELECT preferences_json FROM search_preferences WHERE user_id=?", (user_id,)
        ).fetchone()
        preferences = _json_object(preferences_row["preferences_json"]) if preferences_row else {}
        score_preferences_row = connection.execute(
            "SELECT weights_json FROM career_score_preferences WHERE user_id=?",
            (user_id,),
        ).fetchone()
        score_weights = (
            {**_DEFAULT_CAREER_SCORE_WEIGHTS, **_json_object(score_preferences_row["weights_json"])}
            if score_preferences_row else dict(_DEFAULT_CAREER_SCORE_WEIGHTS)
        )
        skill_count = connection.execute(
            "SELECT COUNT(*) AS count FROM skill_progress WHERE user_id=?", (user_id,)
        ).fetchone()["count"]
        completed_learning = connection.execute(
            "SELECT COUNT(*) AS count FROM academy_activity_progress "
            "WHERE user_id=? AND status='completed'",
            (user_id,),
        ).fetchone()["count"]
        completed_milestones = connection.execute(
            "SELECT COUNT(*) AS count FROM career_coach_milestones "
            "WHERE user_id=? AND status='completed'",
            (user_id,),
        ).fetchone()["count"]
        active_goals = connection.execute(
            "SELECT COUNT(*) AS count FROM career_coach_goals "
            "WHERE user_id=? AND status='active'",
            (user_id,),
        ).fetchone()["count"]
        total_applications = connection.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE user_id=? AND status!='saved'",
            (user_id,),
        ).fetchone()["count"]
        saved_job_count = connection.execute(
            "SELECT COUNT(*) AS count FROM saved_jobs WHERE user_id=?", (user_id,)
        ).fetchone()["count"]
        skill_evidence = connection.execute(
            "SELECT COUNT(DISTINCT lower(skill)) AS total, "
            "COUNT(DISTINCT CASE WHEN verification_status='assessment_verified' "
            "THEN lower(skill) END) AS verified "
            "FROM academy_skill_evidence WHERE user_id=?",
            (user_id,),
        ).fetchone()
        certificates = connection.execute(
            "SELECT COUNT(DISTINCT track_id) AS count FROM academy_certificates WHERE user_id=?",
            (user_id,),
        ).fetchone()["count"]
        recent_opportunities = connection.execute(
            """
            SELECT j.id, j.title, j.company_name, j.location, j.original_url, j.source_label,
                j.remote_type, j.employment_type, j.salary_min, j.salary_max, j.salary_currency,
                r.score, r.updated_at
            FROM job_recommendations r
            JOIN jobs j ON j.id=r.job_id
            WHERE r.user_id=? AND r.state='active' AND j.availability!='expired'
            ORDER BY r.score DESC, r.updated_at DESC LIMIT 6
            """,
            (user_id,),
        ).fetchall()
        achievement_rows = connection.execute(
            "SELECT achievement_key, title, description, evidence, awarded_at "
            "FROM career_achievements WHERE user_id=? ORDER BY awarded_at DESC",
            (user_id,),
        ).fetchall()
        in_app_notifications = connection.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id=? AND read_at IS NULL",
            (user_id,),
        ).fetchone()["count"]
        notification_rows = connection.execute(
            "SELECT id, message, created_at, read_at FROM notifications "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 8",
            (user_id,),
        ).fetchall()

        timeline: list[dict[str, str]] = []
        timeline_queries = [
            (
                "SELECT title, updated_at AS occurred_at FROM resume_profiles "
                "WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
                ("resume", "Resume updated"),
            ),
            (
                "SELECT result_count, created_at AS occurred_at FROM job_search_events "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("search", "Job search"),
            ),
            (
                "SELECT j.title, j.company_name, s.saved_at AS occurred_at "
                "FROM saved_jobs s JOIN jobs j ON j.id=s.job_id "
                "WHERE s.user_id=? ORDER BY s.saved_at DESC LIMIT 50",
                ("saved_job", "Saved job"),
            ),
            (
                "SELECT title, company_name, status, created_at AS occurred_at "
                "FROM applications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("application", "Application recorded"),
            ),
            (
                "SELECT to_status, created_at AS occurred_at FROM application_events "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("application_status", "Application status changed"),
            ),
            (
                "SELECT status, milestone_json, completed_at AS occurred_at "
                "FROM career_coach_milestones WHERE user_id=? AND completed_at IS NOT NULL "
                "ORDER BY completed_at DESC LIMIT 50",
                ("milestone", "Career milestone completed"),
            ),
            (
                "SELECT track_id, activity_id, completed_at AS occurred_at "
                "FROM academy_activity_progress WHERE user_id=? AND status='completed' "
                "AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 50",
                ("learning", "Learning activity completed"),
            ),
            (
                "SELECT skill, status, updated_at AS occurred_at FROM skill_progress "
                "WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
                ("skill", "Skill progress updated"),
            ),
            (
                "SELECT i.interview_type, i.status, i.created_at AS occurred_at, "
                "a.title, a.company_name FROM interviews i "
                "JOIN applications a ON a.id=i.application_id "
                "WHERE i.user_id=? ORDER BY i.created_at DESC LIMIT 50",
                ("interview", "Interview tracked"),
            ),
            (
                "SELECT goal_json, goal_type, created_at AS occurred_at FROM career_coach_goals "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("goal", "Career goal created"),
            ),
            (
                "SELECT track_id, score, issued_at AS occurred_at FROM academy_certificates "
                "WHERE user_id=? ORDER BY issued_at DESC LIMIT 50",
                ("certificate", "Platform learning certificate issued"),
            ),
            (
                "SELECT track_id, score, created_at AS occurred_at FROM academy_assessments "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("assessment", "Learning assessment completed"),
            ),
            (
                "SELECT title, created_at AS occurred_at FROM academy_projects "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("project", "Learning project recorded"),
            ),
            (
                "SELECT content_type, title, created_at AS occurred_at FROM personal_brand_versions "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                ("portfolio", "Professional content created"),
            ),
            (
                "SELECT platform, title, activity_date AS occurred_at FROM personal_brand_analytics "
                "WHERE user_id=? ORDER BY activity_date DESC LIMIT 50",
                ("brand_activity", "Professional brand activity recorded"),
            ),
        ]
        timeline_fetch_limit = timeline_offset + timeline_limit + 1
        for sql, (kind, label) in timeline_queries:
            sql = sql.replace("LIMIT 50", f"LIMIT {timeline_fetch_limit}")
            for row in connection.execute(sql, (user_id,)).fetchall():
                occurred = row["occurred_at"]
                if not occurred:
                    continue
                item_title = label
                detail = ""
                if kind == "resume":
                    detail = str(row["title"])
                elif kind == "search":
                    detail = f"{row['result_count']} listing results"
                elif kind == "saved_job":
                    detail = f"{row['title']} · {row['company_name']}"
                elif kind == "application":
                    detail = f"{row['title']} · {row['company_name']} · {row['status']}"
                elif kind == "application_status":
                    detail = f"Status: {row['to_status']}"
                elif kind == "milestone":
                    milestone = _json_object(row["milestone_json"])
                    detail = str(milestone.get("title") or label)
                elif kind == "learning":
                    detail = f"{row['track_id']} · {row['activity_id']}"
                elif kind == "skill":
                    detail = f"{row['skill']} · {row['status']}"
                elif kind == "interview":
                    detail = f"{row['title']} · {row['company_name']} · {row['interview_type']} · {row['status']}"
                elif kind == "goal":
                    goal = _json_object(row["goal_json"])
                    detail = f"{goal.get('title', label)} · {row['goal_type']}"
                elif kind == "certificate":
                    detail = f"{row['track_id']} · platform-issued, not externally accredited"
                elif kind == "assessment":
                    detail = f"{row['track_id']} · score {row['score']}"
                elif kind == "project":
                    detail = str(row["title"])
                elif kind == "portfolio":
                    detail = f"{row['content_type']} · {row['title']}"
                elif kind == "brand_activity":
                    detail = f"{row['platform']} · {row['title']} · user reported"
                timeline.append({
                    "type": kind,
                    "title": item_title,
                    "detail": detail,
                    "occurred_at": str(occurred),
                })
        timeline.extend(
            {
                "type": "achievement",
                "title": str(row["title"]),
                "detail": str(row["evidence"]),
                "occurred_at": str(row["awarded_at"]),
            }
            for row in sorted(
                achievement_rows,
                key=lambda achievement: achievement["awarded_at"],
                reverse=True,
            )[:timeline_fetch_limit]
        )
        career_day_rows = connection.execute(
            """
            SELECT substr(updated_at, 1, 10) AS activity_day FROM resume_profiles WHERE user_id=?
            UNION SELECT substr(saved_at, 1, 10) FROM saved_jobs WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM applications WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM application_events WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM job_search_events WHERE user_id=?
            UNION SELECT substr(updated_at, 1, 10) FROM skill_progress WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM interviews WHERE user_id=?
            UNION SELECT substr(completed_at, 1, 10) FROM career_coach_milestones
                WHERE user_id=? AND completed_at IS NOT NULL
            UNION SELECT substr(completed_at, 1, 10) FROM academy_activity_progress
                WHERE user_id=? AND status='completed' AND completed_at IS NOT NULL
            UNION SELECT substr(issued_at, 1, 10) FROM academy_certificates WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM academy_assessments WHERE user_id=?
            UNION SELECT substr(created_at, 1, 10) FROM academy_projects WHERE user_id=?
            UNION SELECT substr(activity_date, 1, 10) FROM personal_brand_analytics WHERE user_id=?
            """,
            (user_id,) * 13,
        ).fetchall()
        activity_dates = {row["activity_day"] for row in career_day_rows if row["activity_day"]}
        learning_day_rows = connection.execute(
            "SELECT DISTINCT substr(completed_at, 1, 10) AS activity_day "
            "FROM academy_activity_progress WHERE user_id=? AND status='completed' "
            "AND completed_at IS NOT NULL",
            (user_id,),
        ).fetchall()
        learning_dates = {row["activity_day"] for row in learning_day_rows if row["activity_day"]}

        goals = connection.execute(
            "SELECT goal_json, goal_type, progress, target_date, updated_at "
            "FROM career_coach_goals WHERE user_id=? AND status='active' "
            "ORDER BY updated_at DESC LIMIT 5",
            (user_id,),
        ).fetchall()
        open_milestones = connection.execute(
            "SELECT milestone_json, status, due_date FROM career_coach_milestones "
            "WHERE user_id=? AND status!='completed' ORDER BY due_date IS NULL, due_date LIMIT 5",
            (user_id,),
        ).fetchall()
        latest_roadmap = connection.execute(
            "SELECT roadmap_json, updated_at FROM career_coach_roadmaps "
            "WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        notification_preferences = _notification_preferences(connection, user_id)

    timeline.sort(key=lambda item: item["occurred_at"], reverse=True)
    timeline_has_more = len(timeline) > timeline_offset + timeline_limit
    timeline = timeline[timeline_offset:timeline_offset + timeline_limit]

    resume_skills: list[str] = []
    resume_sections: list[str] = []
    if primary_resume:
        parsed = _json_object(primary_resume["parsed_json"])
        resume_skills = parsed.get("skills_found", []) if isinstance(parsed.get("skills_found"), list) else []
        parsed_sections = parsed.get("sections", {})
        resume_sections = sorted(parsed_sections.keys()) if isinstance(parsed_sections, dict) else []
    coach_recommendation: dict[str, Any] = {}
    if latest_roadmap:
        roadmap_data = _json_object(latest_roadmap["roadmap_json"])
        content = roadmap_data.get("content", {})
        if isinstance(content, dict):
            coach_recommendation = {
                "summary": content.get("summary", ""),
                "action_plan": content.get("action_plan", [])[:5],
                "updated_at": latest_roadmap["updated_at"],
            }
    has_career_direction = bool(preferences.get("preferred_titles") or preferences.get("career_goals"))
    career_score_factors = [
        {"key": "resume_profile", "factor": "Resume profile", "weight": score_weights["resume_profile"], "points": score_weights["resume_profile"] if resume_count else 0, "evidence": f"{resume_count} saved resume(s)"},
        {"key": "career_direction", "factor": "Career direction", "weight": score_weights["career_direction"], "points": score_weights["career_direction"] if has_career_direction else 0, "evidence": "Saved role or career goal" if has_career_direction else "No saved target role or career goal"},
        {"key": "skills", "factor": "Skills tracked", "weight": score_weights["skills"], "points": score_weights["skills"] if skill_count or resume_skills else 0, "evidence": f"{skill_count} tracked skill(s), {len(resume_skills)} resume skill(s)"},
        {"key": "opportunity_activity", "factor": "Opportunity activity", "weight": score_weights["opportunity_activity"], "points": score_weights["opportunity_activity"] if total_applications or saved_job_count else 0, "evidence": f"{total_applications} application(s), {saved_job_count} saved job(s)"},
        {"key": "learning_or_milestones", "factor": "Learning or milestones", "weight": score_weights["learning_or_milestones"], "points": score_weights["learning_or_milestones"] if completed_learning or completed_milestones else 0, "evidence": f"{completed_learning} learning completion(s), {completed_milestones} milestone(s)"},
    ]
    career_score = sum(factor["points"] for factor in career_score_factors)

    verified_evidence_count = int(skill_evidence["verified"] or 0)
    verified_skill_points = min(100, verified_evidence_count * 20)
    certificate_points = min(100 - verified_skill_points, certificates * 10)
    trust_score = verified_skill_points + certificate_points
    trust_factors = [
        {"factor": "Assessment-verified skills", "count": verified_evidence_count, "points": verified_skill_points},
        {"factor": "Platform learning certificates", "count": certificates, "points": certificate_points},
        {"factor": "User-submitted evidence", "count": int(skill_evidence["total"] or 0) - verified_evidence_count, "points": 0},
    ]
    utc_today = datetime.fromisoformat(today).replace(tzinfo=timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "profile": {
            "resume_count": resume_count,
            "primary_resume_title": primary_resume["title"] if primary_resume else None,
            "documented_skills": len(resume_skills),
            "top_skills": resume_skills[:12],
            "documented_sections": resume_sections,
            "target_roles": preferences.get("preferred_titles", []),
            "career_goals": preferences.get("career_goals", ""),
        },
        "career_score": {
            "value": career_score,
            "maximum": 100,
            "label": "Career workspace completeness",
            "factors": career_score_factors,
            "weights": score_weights,
            "disclaimer": "A transparent measure of saved career profile and activity evidence, not employability, performance, or hiring likelihood.",
        },
        "professional_trust": {
            "value": trust_score,
            "maximum": 100,
            "label": "Evidence traceability indicator",
            "factors": trust_factors,
            "disclaimer": "Counts only platform assessment-verified evidence and platform-issued learning certificates. User-submitted credentials are not independently verified; platform certificates are not external accreditation.",
        },
        "progress": {
            "saved_jobs": saved_job_count,
            "applications": total_applications,
            "tracked_skills": skill_count,
            "resume_skills": len(resume_skills),
            "completed_learning": completed_learning,
            "completed_milestones": completed_milestones,
            "active_goals": active_goals,
            "unread_notifications": in_app_notifications,
            "career_streak": _career_streak(activity_dates, utc_today),
            "learning_streak": _career_streak(learning_dates, utc_today),
        },
        "achievements": [dict(row) for row in achievement_rows],
        "goals": [
            {
                **_json_object(row["goal_json"]),
                "goal_type": row["goal_type"],
                "progress": row["progress"],
                "target_date": row["target_date"],
                "updated_at": row["updated_at"],
            }
            for row in goals
        ],
        "career_coach": coach_recommendation,
        "milestones": [
            {
                **_json_object(row["milestone_json"]),
                "status": row["status"],
                "due_date": row["due_date"],
            }
            for row in open_milestones
        ],
        "opportunities": [
            {
                "id": row["id"],
                "title": row["title"],
                "company_name": row["company_name"],
                "location": row["location"],
                "url": row["original_url"],
                "source": row["source_label"],
                "remote_type": row["remote_type"],
                "employment_type": row["employment_type"],
                "salary_min": row["salary_min"],
                "salary_max": row["salary_max"],
                "salary_currency": row["salary_currency"],
                "match_score": row["score"],
                "updated_at": row["updated_at"],
            }
            for row in recent_opportunities
        ],
        "timeline": timeline,
        "timeline_has_more": timeline_has_more,
        "notification_preferences": notification_preferences,
        "notifications": [
            {
                "message": reveal_text(row["message"]),
                "id": row["id"],
                "created_at": row["created_at"],
                "read": row["read_at"] is not None,
            }
            for row in notification_rows
        ],
    }


@router.patch(
    "/command-center/notifications/{notification_id}/read",
    tags=["Premium Career Command Center"],
)
def mark_notification_read(
    notification_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, bool]:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE notifications SET read_at=? WHERE id=? AND user_id=? AND read_at IS NULL",
            (utc_now(), notification_id, user["id"]),
        )
        if cursor.rowcount == 0:
            exists = connection.execute(
                "SELECT id FROM notifications WHERE id=? AND user_id=?",
                (notification_id, user["id"]),
            ).fetchone()
            if exists is None:
                raise HTTPException(status_code=404, detail="Notification was not found.")
    return {"read": True}


@router.put("/command-center/career-score-weights", tags=["Premium Career Command Center"])
def update_career_score_weights(
    payload: CareerScoreWeightsInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, dict[str, int]]:
    weights = payload.model_dump()
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO career_score_preferences(user_id, weights_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET weights_json=excluded.weights_json, "
            "updated_at=excluded.updated_at",
            (
                user["id"],
                protect_text(json.dumps(weights, separators=(",", ":"))),
                utc_now(),
            ),
        )
    return {"weights": weights}


@router.get("/command-center/notification-preferences", tags=["Premium Career Command Center"])
def get_notification_preferences(user: dict[str, str] = Depends(current_user)) -> dict[str, bool]:
    with database() as connection:
        return _notification_preferences(connection, user["id"])


@router.put("/command-center/notification-preferences", tags=["Premium Career Command Center"])
def update_notification_preferences(
    payload: NotificationPreferencesInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, bool]:
    values = payload.model_dump()
    with database(immediate=True) as connection:
        connection.execute(
            """
            INSERT INTO career_notification_preferences(
                user_id, in_app_applications, in_app_interviews, in_app_deadlines,
                email_applications, email_interviews, email_deadlines, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                in_app_applications=excluded.in_app_applications,
                in_app_interviews=excluded.in_app_interviews,
                in_app_deadlines=excluded.in_app_deadlines,
                email_applications=excluded.email_applications,
                email_interviews=excluded.email_interviews,
                email_deadlines=excluded.email_deadlines,
                updated_at=excluded.updated_at
            """,
            (
                user["id"],
                int(values["in_app_applications"]),
                int(values["in_app_interviews"]),
                int(values["in_app_deadlines"]),
                int(values["email_applications"]),
                int(values["email_interviews"]),
                int(values["email_deadlines"]),
                utc_now(),
            ),
        )
    return values
