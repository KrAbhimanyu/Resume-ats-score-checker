import ast
import io
import json
import operator
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.db.database import database, utc_now
from app.models.learning_academy_schemas import (
    CodingExerciseSubmission,
    LearningAssessmentInput,
    LearningAssistantInput,
    LearningEvidenceInput,
    LearningProjectInput,
    LearningRoadmapEditInput,
    LearningRoadmapInput,
)
from app.services.career_coach_ai import answer_career_question
from app.services.business_billing import run_charged_ai_operation
from app.services.career_data import user_resume
from app.services.data_protection import protect_text, reveal_text
from app.services.job_auth import current_user
from app.services.learning_catalog import EXERCISES, RESOURCES, TRACKS
from app.services.parser import parse_resume_content


router = APIRouter()

_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_SAFE_COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}
_SAFE_BUILTINS = {
    "len": len,
    "sum": sum,
    "min": min,
    "max": max,
    "sorted": sorted,
    "set": set,
    "abs": abs,
}


def _safe_binary(operation: type[ast.operator], left: Any, right: Any) -> Any:
    if operation is ast.Add and isinstance(left, (str, list, tuple)) and isinstance(right, type(left)):
        if len(left) + len(right) > 10_000:
            raise ValueError("This result is too large for the exercise evaluator.")
    if operation is ast.Mult:
        if isinstance(left, (str, list, tuple)) and type(right) is int:
            if len(left) * max(0, right) > 10_000:
                raise ValueError("This result is too large for the exercise evaluator.")
        if isinstance(right, (str, list, tuple)) and type(left) is int:
            if len(right) * max(0, left) > 10_000:
                raise ValueError("This result is too large for the exercise evaluator.")
    if (
        operation in {ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.FloorDiv}
        and type(left) in {int, float}
        and type(right) in {int, float}
        and (abs(left) > 1_000_000 or abs(right) > 1_000_000)
    ):
        raise ValueError("Numeric values exceed the exercise evaluator limit.")
    result = _SAFE_BINOPS[operation](left, right)
    if type(result) in {int, float} and abs(result) > 1_000_000_000:
        raise ValueError("Numeric result exceeds the exercise evaluator limit.")
    return result


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _track(track_id: str) -> dict[str, Any]:
    track = TRACKS.get(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Learning track was not found.")
    return track


def _require_ai_consent(user_id: str) -> None:
    with database() as connection:
        row = connection.execute(
            "SELECT ai_data_consent FROM career_coach_settings WHERE user_id=?",
            (user_id,),
        ).fetchone()
    if row is None or not row["ai_data_consent"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enable AI profile sharing in Career Coach settings before using personalized learning AI.",
        )


def _learner_context(connection: Any, user_id: str) -> dict[str, Any]:
    resume_row = connection.execute(
        "SELECT id FROM resume_profiles WHERE user_id=? ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    resume_evidence: dict[str, Any] = {
        "skills": [],
        "sections": [],
        "experience_indicators": [],
        "degrees": [],
    }
    if resume_row:
        resume = user_resume(connection, user_id, resume_row["id"])
        parsed = parse_resume_content(resume["resume_text"])
        resume_evidence = {
            "skills": parsed["skills_found"][:60],
            "sections": sorted(parsed["sections"].keys()),
            "experience_indicators": parsed["experience_indicators"][:20],
            "degrees": parsed["degrees_found"],
        }
    preference_row = connection.execute(
        "SELECT preferences_json FROM search_preferences WHERE user_id=?",
        (user_id,),
    ).fetchone()
    preferences = json.loads(reveal_text(preference_row["preferences_json"])) if preference_row else {}
    skill_rows = connection.execute(
        "SELECT skill, status FROM skill_progress WHERE user_id=? ORDER BY updated_at DESC LIMIT 100",
        (user_id,),
    ).fetchall()
    return {
        "resume_evidence": resume_evidence,
        "career_goals": preferences.get("career_goals", "")[:2000],
        "preferred_roles": preferences.get("preferred_titles", [])[:20],
        "skills_in_progress": [
            {"skill": row["skill"], "status": row["status"]}
            for row in skill_rows
        ],
    }


def _activity_ids(track: dict[str, Any]) -> list[str]:
    return [lesson["id"] for lesson in track["lessons"]] + list(track["exercise_ids"])


def _assessment_score(connection: Any, user_id: str, track_id: str) -> Optional[float]:
    row = connection.execute(
        "SELECT score FROM academy_assessments WHERE user_id=? AND track_id=? "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id, track_id),
    ).fetchone()
    return float(row["score"]) if row else None


def _track_progress(connection: Any, user_id: str, track: dict[str, Any]) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT activity_id, status, score, completed_at FROM academy_activity_progress "
        "WHERE user_id=? AND track_id=?",
        (user_id, track["id"]),
    ).fetchall()
    completed = {row["activity_id"] for row in rows if row["status"] == "completed"}
    required = _activity_ids(track)
    score = _assessment_score(connection, user_id, track["id"])
    return {
        "track_id": track["id"],
        "completed_activities": len(completed.intersection(required)),
        "total_activities": len(required),
        "percent": round(100 * len(completed.intersection(required)) / len(required)) if required else 0,
        "assessment_score": score,
        "certificate_eligible": bool(
            required
            and len(completed.intersection(required)) == len(required)
            and score is not None
            and score >= 70
        ),
        "completed_ids": sorted(completed),
    }


def _recommended_tracks(
    learner: dict[str, Any],
    requested_skills: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    profile_skills = {
        item.casefold()
        for item in learner["resume_evidence"]["skills"]
    }
    skill_status = {
        item["skill"].casefold(): item["status"]
        for item in learner["skills_in_progress"]
    }
    requested = {item.casefold() for item in (requested_skills or [])}
    recommendations = []
    for track in TRACKS.values():
        track_skills = {item.casefold() for item in track["skills"]}
        direct_gaps = sorted(requested.intersection(track_skills))
        existing_learning = sorted(
            skill for skill in track_skills
            if skill_status.get(skill) in {"not_started", "learning"}
        )
        evidenced = sorted(track_skills.intersection(profile_skills))
        preference_text = " ".join(learner["preferred_roles"] + [learner["career_goals"]]).casefold()
        goal_matches = sum(1 for skill in track_skills if skill in preference_text)
        relevance = len(direct_gaps) * 5 + len(existing_learning) * 2 + goal_matches * 2
        if not recommendations and not direct_gaps and not existing_learning and not goal_matches:
            relevance = 1
        recommendations.append({
            "track_id": track["id"],
            "title": track["title"],
            "category": track["category"],
            "matched_gap_skills": direct_gaps,
            "skills_to_develop": existing_learning or direct_gaps or sorted(track_skills - profile_skills),
            "profile_evidence": evidenced,
            "relevance_score": relevance,
        })
    return sorted(recommendations, key=lambda item: (-item["relevance_score"], item["title"]))


def _evaluate_expression(node: ast.AST, variables: dict[str, Any], budget: list[int]) -> Any:
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("Submission exceeded the safe evaluation limit.")
    if isinstance(node, ast.Constant) and type(node.value) in {str, int, float, bool, type(None)}:
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValueError(f"Unknown name '{node.id}'.")
        return variables[node.id]
    if isinstance(node, ast.List):
        return [_evaluate_expression(item, variables, budget) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_evaluate_expression(item, variables, budget) for item in node.elts)
    if isinstance(node, ast.Set):
        return {_evaluate_expression(item, variables, budget) for item in node.elts}
    if isinstance(node, ast.Dict):
        return {
            _evaluate_expression(key, variables, budget): _evaluate_expression(value, variables, budget)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Subscript):
        value = _evaluate_expression(node.value, variables, budget)
        key = _evaluate_expression(node.slice, variables, budget)
        return value[key]
    if isinstance(node, ast.Slice):
        lower = _evaluate_expression(node.lower, variables, budget) if node.lower else None
        upper = _evaluate_expression(node.upper, variables, budget) if node.upper else None
        step = _evaluate_expression(node.step, variables, budget) if node.step else None
        return slice(lower, upper, step)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
        return _safe_binary(
            type(node.op),
            _evaluate_expression(node.left, variables, budget),
            _evaluate_expression(node.right, variables, budget),
        )
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_expression(node.operand, variables, budget)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub) and type(value) in {int, float}:
            return -value
    if isinstance(node, ast.BoolOp):
        values = [_evaluate_expression(item, variables, budget) for item in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    if isinstance(node, ast.Compare):
        left = _evaluate_expression(node.left, variables, budget)
        for operation, comparator in zip(node.ops, node.comparators):
            if type(operation) not in _SAFE_COMPARE:
                raise ValueError("This comparison operator is not supported.")
            right = _evaluate_expression(comparator, variables, budget)
            if not _SAFE_COMPARE[type(operation)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        branch = node.body if _evaluate_expression(node.test, variables, budget) else node.orelse
        return _evaluate_expression(branch, variables, budget)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _SAFE_BUILTINS:
        if node.keywords:
            raise ValueError("Keyword arguments are not supported in this exercise.")
        arguments = [_evaluate_expression(item, variables, budget) for item in node.args]
        return _SAFE_BUILTINS[node.func.id](*arguments)
    if isinstance(node, ast.ListComp) and len(node.generators) == 1:
        generator = node.generators[0]
        if generator.is_async or not isinstance(generator.target, ast.Name) or generator.ifs:
            if generator.is_async or not isinstance(generator.target, ast.Name):
                raise ValueError("This comprehension form is not supported.")
        iterable = _evaluate_expression(generator.iter, variables, budget)
        result = []
        for item in iterable:
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError("Submission exceeded the safe evaluation limit.")
            local = dict(variables)
            local[generator.target.id] = item
            if generator.ifs and not all(
                _evaluate_expression(condition, local, budget) for condition in generator.ifs
            ):
                continue
            result.append(_evaluate_expression(node.elt, local, budget))
        return result
    raise ValueError(f"Unsupported syntax: {type(node).__name__}.")


def _run_restricted_case(
    function: ast.FunctionDef,
    arguments: list[Any],
) -> Any:
    parameters = [argument.arg for argument in function.args.args]
    if len(arguments) != len(parameters):
        raise ValueError("Exercise case does not match the function signature.")
    if len(function.body) != 1 or not isinstance(function.body[0], ast.Return) or function.body[0].value is None:
        raise ValueError("Use one function containing a single return expression.")
    return _evaluate_expression(
        function.body[0].value,
        dict(zip(parameters, arguments)),
        [5000],
    )


def _evaluate_submission(exercise: dict[str, Any], code: str) -> dict[str, Any]:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return {"passed": False, "score": 0, "error": f"Syntax error on line {exc.lineno or '?'}."}
    if len(list(ast.walk(tree))) > 300:
        return {"passed": False, "score": 0, "error": "Submission is too complex for this exercise."}
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return {"passed": False, "score": 0, "error": "Submit exactly one function definition."}
    function = tree.body[0]
    expected_name = exercise["signature"].split("(")[0].removeprefix("def ")
    if function.name != expected_name:
        return {"passed": False, "score": 0, "error": f"Define the required function '{expected_name}'."}
    if (
        function.decorator_list or function.args.vararg or function.args.kwarg
        or function.args.defaults or function.args.kw_defaults
        or function.args.posonlyargs or function.args.kwonlyargs
        or any(argument.annotation is not None for argument in function.args.args)
    ):
        return {"passed": False, "score": 0, "error": "Decorators, annotations, defaults, and variadic arguments are not supported."}
    outcomes = []
    for case_number, case in enumerate(exercise["cases"], start=1):
        try:
            actual = _run_restricted_case(function, case["args"])
            passed = actual == case["expected"] and type(actual) is type(case["expected"])
            outcomes.append({"case": case_number, "passed": passed})
        except (ArithmeticError, KeyError, TypeError, ValueError, IndexError) as exc:
            outcomes.append({"case": case_number, "passed": False, "feedback": str(exc)[:180]})
    passed_count = sum(1 for result in outcomes if result["passed"])
    score = round(100 * passed_count / len(outcomes)) if outcomes else 0
    return {
        "passed": passed_count == len(outcomes),
        "score": score,
        "passed_cases": passed_count,
        "total_cases": len(outcomes),
        "cases": outcomes,
        "evaluation_mode": "restricted AST interpreter; submitted code is not executed by Python",
        "limits": "Only a single return-expression function, selected expressions, comprehensions, and safe built-ins are supported.",
    }


def _record_activity(
    connection: Any,
    user_id: str,
    track_id: str,
    activity_id: str,
    *,
    score: Optional[float] = None,
    result: Optional[dict[str, Any]] = None,
) -> None:
    now = utc_now()
    connection.execute(
        "INSERT INTO academy_activity_progress(user_id, activity_id, track_id, status, score, result_json, started_at, completed_at, updated_at) "
        "VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, activity_id) DO UPDATE SET status='completed', score=excluded.score, "
        "result_json=excluded.result_json, completed_at=excluded.completed_at, updated_at=excluded.updated_at",
        (
            user_id, activity_id, track_id, score,
            _json_text(result) if result is not None else None,
            now, now, now,
        ),
    )


def _add_skill_evidence(
    connection: Any,
    user_id: str,
    skill: str,
    *,
    description: str,
    assessment_id: Optional[str] = None,
) -> None:
    now = utc_now()
    connection.execute(
        "INSERT INTO academy_skill_evidence(id, user_id, skill, evidence_type, evidence_description, "
        "verification_status, assessment_id, created_at, updated_at) "
        "VALUES (?, ?, ?, 'platform_assessment', ?, 'assessment_verified', ?, ?, ?)",
        (str(uuid.uuid4()), user_id, skill, protect_text(description), assessment_id, now, now),
    )


@router.get("/dashboard", tags=["Learning Academy"])
def academy_dashboard(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    with database() as connection:
        learner = _learner_context(connection, user["id"])
        tracks = []
        for track in TRACKS.values():
            tracks.append({
                "id": track["id"],
                "title": track["title"],
                "category": track["category"],
                "level": track["level"],
                "skills": track["skills"],
                "summary": track["summary"],
                "progress": _track_progress(connection, user["id"], track),
            })
        assessments = connection.execute(
            "SELECT id, track_id, score, created_at FROM academy_assessments "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user["id"],),
        ).fetchall()
        evidence = connection.execute(
            "SELECT id, skill, evidence_type, evidence_description, evidence_url, verification_status, created_at "
            "FROM academy_skill_evidence WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
        projects = connection.execute(
            "SELECT id, title, created_at, updated_at FROM academy_projects "
            "WHERE user_id=? ORDER BY updated_at DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
        certificates = connection.execute(
            "SELECT id, track_id, serial_number, issued_at, score FROM academy_certificates "
            "WHERE user_id=? ORDER BY issued_at DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
        recommendations = _recommended_tracks(learner)
    return {
        "tracks": tracks,
        "recommendations": recommendations,
        "resources": [{"id": key, **value} for key, value in RESOURCES.items()],
        "skill_progress": learner["skills_in_progress"],
        "resume_skill_evidence": learner["resume_evidence"]["skills"],
        "assessments": [dict(row) for row in assessments],
        "evidence": [
            {
                **dict(row),
                "evidence_description": reveal_text(row["evidence_description"]),
            }
            for row in evidence
        ],
        "projects": [dict(row) for row in projects],
        "certificates": [dict(row) for row in certificates],
        "certificate_notice": "Academy certificates confirm completion of specified platform activities only. They are not external or accredited professional certifications.",
    }


@router.get("/tracks/{track_id}", tags=["Learning Academy"])
def get_track(track_id: str, user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    track = _track(track_id)
    with database() as connection:
        progress = _track_progress(connection, user["id"], track)
        activity_rows = connection.execute(
            "SELECT activity_id, completed_at, result_json FROM academy_activity_progress "
            "WHERE user_id=? AND track_id=? AND status='completed'",
            (user["id"], track_id),
        ).fetchall()
        assessment = connection.execute(
            "SELECT id, score, result_json, created_at FROM academy_assessments "
            "WHERE user_id=? AND track_id=? ORDER BY created_at DESC LIMIT 1",
            (user["id"], track_id),
        ).fetchone()
    completed = {row["activity_id"]: row for row in activity_rows}
    lessons = [
        {
            **lesson,
            "completed_at": completed[lesson["id"]]["completed_at"] if lesson["id"] in completed else None,
        }
        for lesson in track["lessons"]
    ]
    exercises = [
        {
            **EXERCISES[exercise_id],
            "completed_at": completed[exercise_id]["completed_at"] if exercise_id in completed else None,
            "saved_result": (
                json.loads(reveal_text(completed[exercise_id]["result_json"]))
                if exercise_id in completed and completed[exercise_id]["result_json"]
                else None
            ),
        }
        for exercise_id in track["exercise_ids"]
    ]
    assessment_result = None
    if assessment:
        assessment_result = {
            "id": assessment["id"],
            "score": assessment["score"],
            "result": json.loads(reveal_text(assessment["result_json"])),
            "created_at": assessment["created_at"],
        }
    return {
        **track,
        "lessons": lessons,
        "exercises": exercises,
        "resources": [RESOURCES[item] for item in track["resources"]],
        "certifications": [RESOURCES[item] for item in track["certifications"]],
        "assessment": {
            "passing_score": 70,
            "questions": [
                {
                    "id": question["id"],
                    "prompt": question["prompt"],
                    "options": question["options"],
                }
                for question in track["assessment"]["questions"]
            ],
        },
        "progress": progress,
        "latest_assessment": assessment_result,
    }


@router.post("/tracks/{track_id}/lessons/{lesson_id}/complete", tags=["Learning Academy"])
def complete_lesson(
    track_id: str,
    lesson_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    track = _track(track_id)
    if not any(item["id"] == lesson_id for item in track["lessons"]):
        raise HTTPException(status_code=404, detail="Lesson was not found in this learning track.")
    with database() as connection:
        _record_activity(connection, user["id"], track_id, lesson_id)
        return _track_progress(connection, user["id"], track)


@router.post("/tracks/{track_id}/assessment", tags=["Learning Academy"])
def submit_assessment(
    track_id: str,
    payload: LearningAssessmentInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    track = _track(track_id)
    questions = track["assessment"]["questions"]
    expected_ids = {question["id"] for question in questions}
    if set(payload.answers) != expected_ids:
        raise HTTPException(status_code=422, detail="Answer every assessment question exactly once.")
    results = [
        {
            "question_id": question["id"],
            "correct": payload.answers[question["id"]] == question["answer"],
            "explanation": question["explanation"],
        }
        for question in questions
    ]
    correct = sum(1 for item in results if item["correct"])
    score = round(100 * correct / len(questions)) if questions else 0
    result = {
        "score": score,
        "correct_answers": correct,
        "question_count": len(questions),
        "passed": score >= 70,
        "results": results,
        "evidence_label": "Academy knowledge assessment; not an external certification or independent professional verification.",
    }
    assessment_id = str(uuid.uuid4())
    with database() as connection:
        connection.execute(
            "INSERT INTO academy_assessments(id, user_id, track_id, answers_json, result_json, score, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                assessment_id, user["id"], track_id,
                protect_text(_json_text(payload.answers)),
                protect_text(_json_text(result)),
                score, utc_now(),
            ),
        )
        if score >= 70:
            for skill in track["skills"]:
                _add_skill_evidence(
                    connection,
                    user["id"],
                    skill,
                    description=f"Passed the {track['title']} knowledge assessment with a score of {score}%. Platform-based evidence only.",
                    assessment_id=assessment_id,
                )
                connection.execute(
                    "INSERT INTO skill_progress(user_id, skill, status, note, updated_at) "
                    "VALUES (?, ?, 'practiced', ?, ?) ON CONFLICT(user_id, skill) DO UPDATE SET "
                    "status=CASE WHEN skill_progress.status='not_started' THEN 'practiced' ELSE skill_progress.status END, "
                    "note=excluded.note, updated_at=excluded.updated_at",
                    (
                        user["id"], skill,
                        protect_text("Passed an Academy knowledge assessment. This is platform evidence only, not a professional certification."),
                        utc_now(),
                    ),
                )
    return {"id": assessment_id, **result}


@router.post("/tracks/{track_id}/exercises/{exercise_id}", tags=["Learning Academy"])
def submit_coding_exercise(
    track_id: str,
    exercise_id: str,
    payload: CodingExerciseSubmission,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    track = _track(track_id)
    exercise = EXERCISES.get(exercise_id)
    if exercise is None or exercise["track_id"] != track_id or exercise_id not in track["exercise_ids"]:
        raise HTTPException(status_code=404, detail="Coding exercise was not found in this learning track.")
    evaluation = _evaluate_submission(exercise, payload.code)
    with database() as connection:
        if evaluation.get("passed"):
            _record_activity(connection, user["id"], track_id, exercise_id, score=evaluation["score"], result=evaluation)
            _add_skill_evidence(
                connection,
                user["id"],
                "Python",
                description=f"Passed all cases in the {exercise['title']} restricted-interpreter coding exercise.",
            )
            connection.execute(
                "INSERT INTO skill_progress(user_id, skill, status, note, updated_at) "
                "VALUES (?, 'Python', 'practiced', ?, ?) "
                "ON CONFLICT(user_id, skill) DO UPDATE SET "
                "status=CASE WHEN skill_progress.status='not_started' THEN 'practiced' ELSE skill_progress.status END, "
                "note=excluded.note, updated_at=excluded.updated_at",
                (
                    user["id"],
                    protect_text("Passed a restricted Academy coding exercise; this is platform evidence only."),
                    utc_now(),
                ),
            )
    return evaluation


@router.get("/roadmaps", tags=["Learning Academy"])
def list_learning_roadmaps(
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT id, target_role, roadmap_json, created_at, updated_at FROM academy_roadmaps "
            "WHERE user_id=? ORDER BY updated_at DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "target_role": row["target_role"],
            "roadmap": json.loads(reveal_text(row["roadmap_json"])),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


@router.post("/roadmaps", tags=["Learning Academy"])
async def generate_learning_roadmap(
    payload: LearningRoadmapInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    selected_ids = payload.track_ids or list(TRACKS)
    if len(set(selected_ids)) != len(selected_ids):
        raise HTTPException(status_code=422, detail="Choose each learning track once.")
    selected_tracks = [_track(track_id) for track_id in selected_ids]
    with database() as connection:
        learner = _learner_context(connection, user["id"])
    known_skills = list(dict.fromkeys(
        learner["resume_evidence"]["skills"]
        + [item["skill"] for item in learner["skills_in_progress"]]
        + payload.skills_to_develop
    ))[:100]
    recommendations = _recommended_tracks(learner, payload.skills_to_develop)
    recommendation_by_id = {item["track_id"]: item for item in recommendations}
    sequence = [
        {
            "track_id": track["id"],
            "title": track["title"],
            "category": track["category"],
            "skills": track["skills"],
            "reason": (
                "Matches the supplied skill gap."
                if recommendation_by_id[track["id"]]["matched_gap_skills"]
                else "Relevant to the supplied career goal and profile evidence."
            ),
            "lessons": [
                {"id": lesson["id"], "title": lesson["title"], "minutes": lesson["minutes"]}
                for lesson in track["lessons"]
            ],
            "resources": [RESOURCES[item] for item in track["resources"]],
        }
        for track in selected_tracks
    ]
    ai_context = {
        "task": "Create a realistic learning sequence using only the actual academy tracks and resources in the context. Do not invent courses, credentials, dates, guarantees, or proficiency.",
        "target_role": payload.target_role,
        "career_goal": payload.goal,
        "known_skill_evidence": known_skills,
        "skills_to_develop": payload.skills_to_develop,
        "available_tracks": [
            {"id": track["id"], "title": track["title"], "skills": track["skills"], "summary": track["summary"]}
            for track in selected_tracks
        ],
        "latest_user_message": (
            "Personalize the order and pacing of the listed learning tracks for the target role. "
            "Use the known evidence and mark unverified skills as learning goals. Mention any gaps in available learning content. "
            f"Target role: {payload.target_role}. Goal: {payload.goal}. "
            f"Available lessons and resources: {_json_text(sequence)}"
        ),
    }
    ai_guidance = await run_charged_ai_operation(
        user["id"], "learning_assistant", lambda: answer_career_question(ai_context)
    )
    now = utc_now()
    roadmap = {
        "target_role": payload.target_role,
        "goal": payload.goal,
        "skills_to_develop": payload.skills_to_develop,
        "ai_guidance": ai_guidance,
        "sequence": sequence,
        "personalization_method": "AI guidance grounded in candidate skill evidence and the curated catalog. Track and resource identifiers are catalog-validated.",
        "generated_at": now,
    }
    roadmap_id = str(uuid.uuid4())
    with database() as connection:
        connection.execute(
            "INSERT INTO academy_roadmaps(id, user_id, target_role, roadmap_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (roadmap_id, user["id"], payload.target_role, protect_text(_json_text(roadmap)), now, now),
        )
    return {"id": roadmap_id, "roadmap": roadmap, "created_at": now, "updated_at": now}


@router.patch("/roadmaps/{roadmap_id}", tags=["Learning Academy"])
def edit_learning_roadmap(
    roadmap_id: str,
    payload: LearningRoadmapEditInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    if len(set(payload.track_ids)) != len(payload.track_ids):
        raise HTTPException(status_code=422, detail="Choose each learning track once.")
    selected_tracks = [_track(track_id) for track_id in payload.track_ids]
    sequence = [
        {
            "track_id": track["id"],
            "title": track["title"],
            "category": track["category"],
            "skills": track["skills"],
            "reason": "Selected in the learner-edited roadmap.",
            "lessons": [
                {"id": lesson["id"], "title": lesson["title"], "minutes": lesson["minutes"]}
                for lesson in track["lessons"]
            ],
            "resources": [RESOURCES[item] for item in track["resources"]],
        }
        for track in selected_tracks
    ]
    now = utc_now()
    with database() as connection:
        row = connection.execute(
            "SELECT roadmap_json, created_at FROM academy_roadmaps "
            "WHERE id=? AND user_id=?",
            (roadmap_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Learning roadmap was not found.")
        roadmap = json.loads(reveal_text(row["roadmap_json"]))
        roadmap.update({
            "target_role": payload.target_role,
            "goal": payload.goal,
            "skills_to_develop": payload.skills_to_develop,
            "sequence": sequence,
            "personalization_method": (
                "Learner-edited roadmap using validated tracks and lessons from the Academy catalog. "
                "The saved AI guidance is from the original generation; generate a new roadmap to refresh it."
            ),
        })
        connection.execute(
            "UPDATE academy_roadmaps SET target_role=?, roadmap_json=?, updated_at=? "
            "WHERE id=? AND user_id=?",
            (
                payload.target_role, protect_text(_json_text(roadmap)), now,
                roadmap_id, user["id"],
            ),
        )
    return {
        "id": roadmap_id,
        "target_role": payload.target_role,
        "roadmap": roadmap,
        "created_at": row["created_at"],
        "updated_at": now,
    }


@router.get("/assistant/history", tags=["Learning Academy"])
def learning_assistant_history(
    limit: int = Query(default=30, ge=1, le=100),
    user: dict[str, str] = Depends(current_user),
) -> list[dict[str, str]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT role, content, created_at FROM academy_chat_messages "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()
    return [
        {"role": row["role"], "content": reveal_text(row["content"]), "created_at": row["created_at"]}
        for row in reversed(rows)
    ]


@router.post("/assistant", tags=["Learning Academy"])
async def learning_assistant(
    payload: LearningAssistantInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    track = _track(payload.track_id) if payload.track_id else None
    with database() as connection:
        learner = _learner_context(connection, user["id"])
        recent = connection.execute(
            "SELECT role, content FROM academy_chat_messages WHERE user_id=? "
            "ORDER BY created_at DESC LIMIT 10",
            (user["id"],),
        ).fetchall()
    context = {
        "task": "Act as a learning assistant. Explain concepts, ask a focused question when useful, and suggest practice only from the actual academy content.",
        "candidate_evidence": learner,
        "selected_track": {
            "title": track["title"],
            "lessons": [{"id": lesson["id"], "title": lesson["title"], "content": lesson["content"]} for lesson in track["lessons"]],
            "resources": [RESOURCES[item] for item in track["resources"]],
        } if track else None,
        "recent_conversation": [
            {"role": row["role"], "content": reveal_text(row["content"])}
            for row in reversed(recent)
        ],
        "latest_user_message": payload.message,
    }
    answer = await run_charged_ai_operation(
        user["id"], "learning_assistant", lambda: answer_career_question(context)
    )
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO academy_chat_messages(id, user_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
            (str(uuid.uuid4()), user["id"], protect_text(payload.message), now),
        )
        connection.execute(
            "INSERT INTO academy_chat_messages(id, user_id, role, content, created_at) VALUES (?, ?, 'assistant', ?, ?)",
            (str(uuid.uuid4()), user["id"], protect_text(answer), now),
        )
    return {"response": answer, "created_at": now}


@router.post("/projects/evaluate", tags=["Learning Academy"])
async def evaluate_learning_project(
    payload: LearningProjectInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    description = payload.description.strip()
    checks = [
        ("problem_and_users", bool(re.search(r"\b(problem|user|customer|need|goal|objective)\b", description, re.I))),
        ("technical_approach", bool(re.search(r"\b(built|implemented|designed|developed|configured|technology|api|database|model|framework)\b", description, re.I))),
        ("individual_contribution", bool(re.search(r"\b(i|my|implemented|created|designed|developed|led)\b", description, re.I))),
        ("validation", bool(re.search(r"\b(test|tested|validation|validated|measure|metric|evaluation|experiment)\b", description, re.I))),
        ("outcome_or_learning", bool(re.search(r"\b(result|outcome|impact|improved|reduced|increased|learned|lesson)\b", description, re.I))),
    ]
    criteria = [
        {
            "criterion": name.replace("_", " "),
            "score": 2 if present else 0,
            "maximum": 2,
            "evidence_found": present,
            "feedback": (
                "Describe the supporting evidence explicitly."
                if not present else
                "A matching detail appears in the supplied description; verify it is accurate."
            ),
        }
        for name, present in checks
    ]
    rubric_score = sum(item["score"] for item in criteria)
    project_context = {
        "task": "Review only the submitted project description. Do not claim to have inspected a repository, website, code, tests, or deployment. Distinguish evidence in the description from missing details. Give practical next steps and do not invent impact.",
        "project_title": payload.title,
        "project_description": description,
        "user_supplied_skills": payload.skills,
        "url_provided": bool(payload.project_url),
        "transparent_rubric": criteria,
        "latest_user_message": (
            "Provide a concise project review: strengths supported by the text, unclear or missing evidence, "
            "and three practical improvements. Explain that this review is based on the description only."
        ),
    }
    ai_feedback = await run_charged_ai_operation(
        user["id"], "project_evaluation", lambda: answer_career_question(project_context)
    )
    evaluation = {
        "rubric_score": rubric_score,
        "maximum_score": len(criteria) * 2,
        "criteria": criteria,
        "ai_feedback": ai_feedback,
        "evaluation_scope": "Description-only review. The platform did not access, run, or verify the submitted work or URL.",
        "created_at": utc_now(),
    }
    project_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO academy_projects(id, user_id, title, description, project_url, evaluation_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id, user["id"], payload.title,
                protect_text(description), str(payload.project_url) if payload.project_url else None,
                protect_text(_json_text(evaluation)), now, now,
            ),
        )
        for skill in dict.fromkeys(payload.skills):
            _add_skill_evidence(
                connection,
                user["id"],
                skill,
                description=f"User-submitted project: {payload.title}. Project evidence is self-submitted and has not been independently reviewed.",
            )
    return {"id": project_id, "title": payload.title, "evaluation": evaluation, "created_at": now}


@router.get("/projects", tags=["Learning Academy"])
def list_learning_projects(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT id, title, description, project_url, evaluation_json, created_at, updated_at "
            "FROM academy_projects WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "description": reveal_text(row["description"]),
            "project_url": row["project_url"],
            "evaluation": json.loads(reveal_text(row["evaluation_json"])),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


@router.post("/skills/evidence", status_code=status.HTTP_201_CREATED, tags=["Learning Academy"])
def submit_skill_evidence(
    payload: LearningEvidenceInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    evidence_id = str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO academy_skill_evidence(id, user_id, skill, evidence_type, evidence_description, "
            "evidence_url, verification_status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'user_submitted', ?, ?)",
            (
                evidence_id, user["id"], payload.skill.strip(), payload.evidence_type,
                protect_text(payload.description.strip()),
                str(payload.evidence_url) if payload.evidence_url else None,
                now, now,
            ),
        )
        connection.execute(
            "INSERT INTO skill_progress(user_id, skill, status, note, updated_at) "
            "VALUES (?, ?, 'practiced', ?, ?) "
            "ON CONFLICT(user_id, skill) DO UPDATE SET "
            "status=CASE WHEN skill_progress.status='not_started' THEN 'practiced' ELSE skill_progress.status END, "
            "note=excluded.note, updated_at=excluded.updated_at",
            (
                user["id"], payload.skill.strip(),
                protect_text("User-submitted evidence. Not independently verified by the platform."),
                now,
            ),
        )
    return {
        "id": evidence_id,
        "skill": payload.skill.strip(),
        "evidence_type": payload.evidence_type,
        "evidence_url": str(payload.evidence_url) if payload.evidence_url else None,
        "verification_status": "user_submitted",
        "notice": "External evidence is recorded for your portfolio; the platform has not verified its authenticity or awarded external credit.",
        "created_at": now,
    }


@router.post("/tracks/{track_id}/certificate", status_code=status.HTTP_201_CREATED, tags=["Learning Academy"])
def issue_learning_certificate(
    track_id: str,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    track = _track(track_id)
    with database() as connection:
        progress = _track_progress(connection, user["id"], track)
        if not progress["certificate_eligible"]:
            raise HTTPException(
                status_code=409,
                detail="Complete every lesson and coding activity and pass the track assessment with at least 70% to earn this platform certificate.",
            )
        row = connection.execute(
            "SELECT id, track_id, serial_number, issued_at, score FROM academy_certificates "
            "WHERE user_id=? AND track_id=? ORDER BY issued_at DESC LIMIT 1",
            (user["id"], track_id),
        ).fetchone()
        if row:
            return {**dict(row), "track_title": track["title"], "certificate_type": "platform_completion"}
        latest_score = progress["assessment_score"]
        certificate_id = str(uuid.uuid4())
        serial = f"ACADEMY-{uuid.uuid4().hex[:16].upper()}"
        issued_at = utc_now()
        connection.execute(
            "INSERT INTO academy_certificates(id, user_id, track_id, serial_number, issued_at, score) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (certificate_id, user["id"], track_id, serial, issued_at, latest_score),
        )
    return {
        "id": certificate_id,
        "track_id": track_id,
        "track_title": track["title"],
        "serial_number": serial,
        "issued_at": issued_at,
        "score": latest_score,
        "certificate_type": "platform_completion",
        "accreditation_notice": "This certificate records completion of platform lessons, exercises, and assessment only. It is not an external, accredited, or professional certification.",
    }


@router.get("/certificates/{serial_number}/download", tags=["Learning Academy"])
def download_learning_certificate(
    serial_number: str,
    user: dict[str, str] = Depends(current_user),
) -> Response:
    with database() as connection:
        row = connection.execute(
            "SELECT certificate.track_id, certificate.serial_number, certificate.issued_at, certificate.score, "
            "users.email FROM academy_certificates AS certificate JOIN users "
            "ON users.id=certificate.user_id WHERE certificate.serial_number=? AND certificate.user_id=?",
            (serial_number, user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Learning completion certificate was not found.")
    track = _track(row["track_id"])
    issued_date = datetime.fromisoformat(row["issued_at"].replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d")
    stream = io.BytesIO()
    page = landscape(A4)
    document = canvas.Canvas(stream, pagesize=page)
    width, height = page
    document.setTitle(f"Platform Completion Certificate - {track['title']}")
    document.setStrokeColorRGB(0.18, 0.28, 0.55)
    document.setLineWidth(3)
    document.rect(28, 28, width - 56, height - 56)
    document.setFillColorRGB(0.12, 0.2, 0.38)
    document.setFont("Helvetica-Bold", 26)
    document.drawCentredString(width / 2, height - 105, "PLATFORM COMPLETION CERTIFICATE")
    document.setFillColorRGB(0.2, 0.2, 0.2)
    document.setFont("Helvetica", 15)
    document.drawCentredString(width / 2, height - 155, "This confirms that")
    document.setFont("Helvetica-Bold", 22)
    document.drawCentredString(width / 2, height - 195, str(row["email"])[:100])
    document.setFont("Helvetica", 15)
    document.drawCentredString(width / 2, height - 235, "completed the platform learning track")
    document.setFont("Helvetica-Bold", 20)
    document.drawCentredString(width / 2, height - 272, track["title"][:90])
    document.setFont("Helvetica", 12)
    document.drawCentredString(width / 2, height - 310, f"Assessment score: {row['score']:.0f}%   |   Issued: {issued_date}")
    document.setFont("Helvetica", 10)
    document.drawCentredString(width / 2, 83, f"Serial: {row['serial_number']}")
    document.drawCentredString(width / 2, 64, "Platform activity record only. Not accredited and not an external professional certification.")
    document.save()
    stream.seek(0)
    return Response(
        content=stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{row["serial_number"]}.pdf"'},
    )
