import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.db.database import database, utc_now
from app.models.salary_intelligence_schemas import (
    SalaryCalculatorInput,
    SalaryEstimateInput,
    SalaryGrowthInput,
    SalaryNegotiationInput,
    SalaryOfferExplainInput,
    SalaryOfferInput,
    SalaryOfferComparisonInput,
    SalaryReadinessInput,
)
from app.services.career_coach_ai import answer_career_question
from app.services.business_billing import run_charged_ai_operation
from app.services.data_protection import protect_text, reveal_text
from app.services.extractor import extract_resume_text
from app.services.job_auth import current_user
from app.core.security import read_upload_file
from app.services.parser import parse_resume_content


router = APIRouter()
_FINANCIAL_TERMS = re.compile(
    r"\b(?:salary|compensation|ctc|base pay|fixed pay|variable pay|bonus|equity|stock|"
    r"allowance|benefit|insurance|retirement|pension|provident fund|deduction|tax|"
    r"joining bonus|sign[- ]on|notice period|clawback|vesting|relocation)\b",
    re.IGNORECASE,
)


def _offer_record(row: Any) -> dict[str, Any]:
    try:
        offer = json.loads(reveal_text(row["offer_json"]))
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A saved offer record could not be read.",
        ) from exc
    annual_total = sum(
        float(offer.get(key, 0))
        for key in ("annual_base", "annual_variable", "annual_bonus", "annual_equity")
    )
    return {
        "id": row["id"],
        **offer,
        "annual_total": annual_total,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _comparison_record(row: Any) -> dict[str, Any]:
    try:
        offer_ids = json.loads(row["offer_ids_json"])
        offers = json.loads(reveal_text(row["offers_snapshot_json"]))
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A saved offer comparison could not be read.",
        ) from exc
    comparable = len(offers) == 2 and offers[0].get("currency") == offers[1].get("currency")
    difference = (
        round(float(offers[0].get("annual_total", 0)) - float(offers[1].get("annual_total", 0)), 2)
        if comparable else None
    )
    return {
        "id": row["id"],
        "title": row["title"],
        "offer_ids": offer_ids,
        "offers": offers,
        "same_currency": comparable,
        "annual_total_difference": difference,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _comparison_offers(connection: Any, offer_ids: list[str], user_id: str) -> list[dict[str, Any]]:
    offers = []
    for offer_id in offer_ids:
        row = connection.execute(
            "SELECT * FROM salary_offers WHERE id=? AND user_id=?",
            (offer_id, user_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="A selected saved salary offer was not found.")
        offers.append(_offer_record(row))
    return offers


def _clean_offer(payload: SalaryOfferInput) -> dict[str, Any]:
    result = payload.model_dump()
    result["currency"] = result["currency"].upper()
    for key in ("name", "company", "role", "location", "conditions", "growth_notes"):
        result[key] = result[key].strip()
    result["benefits"] = list(dict.fromkeys(
        benefit.strip() for benefit in result["benefits"] if benefit.strip()
    ))
    if not any(result[key] for key in ("annual_base", "annual_variable", "annual_bonus", "annual_equity")):
        raise HTTPException(status_code=422, detail="Enter at least one compensation component.")
    return result


def _consent_enabled(user_id: str) -> bool:
    with database() as connection:
        row = connection.execute(
            "SELECT ai_data_consent FROM career_coach_settings WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return bool(row and row["ai_data_consent"])


def _require_ai_consent(user_id: str) -> None:
    if not _consent_enabled(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enable AI profile sharing in Career Coach settings before requesting personalized salary guidance.",
        )


def _resume_evidence(user_id: str) -> dict[str, Any]:
    with database() as connection:
        row = connection.execute(
            "SELECT resume_text FROM resume_profiles WHERE user_id=? "
            "ORDER BY is_primary DESC, updated_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        return {}
    parsed = parse_resume_content(reveal_text(row["resume_text"]))
    return {
        "skills_found": parsed["skills_found"][:50],
        "degrees_found": parsed["degrees_found"][:10],
        "experience_indicators": parsed["experience_indicators"][:10],
        "metrics_found": parsed["metrics_found"][:20],
    }


def _raw_metadata(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


@router.get("/salary/offers", tags=["Career Platform - Salary Intelligence"])
def list_salary_offers(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM salary_offers WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    return [_offer_record(row) for row in rows]


@router.post(
    "/salary/offers",
    status_code=status.HTTP_201_CREATED,
    tags=["Career Platform - Salary Intelligence"],
)
def create_salary_offer(
    payload: SalaryOfferInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    offer_id = str(uuid.uuid4())
    offer = _clean_offer(payload)
    now = utc_now()
    with database(immediate=True) as connection:
        connection.execute(
            "INSERT INTO salary_offers(id, user_id, offer_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (offer_id, user["id"], protect_text(json.dumps(offer, ensure_ascii=False)), now, now),
        )
        row = connection.execute(
            "SELECT * FROM salary_offers WHERE id=? AND user_id=?",
            (offer_id, user["id"]),
        ).fetchone()
    return _offer_record(row)


@router.put("/salary/offers/{offer_id}", tags=["Career Platform - Salary Intelligence"])
def update_salary_offer(
    offer_id: str,
    payload: SalaryOfferInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    offer = _clean_offer(payload)
    now = utc_now()
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "UPDATE salary_offers SET offer_json=?, updated_at=? WHERE id=? AND user_id=?",
            (protect_text(json.dumps(offer, ensure_ascii=False)), now, offer_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved salary offer not found.")
        row = connection.execute(
            "SELECT * FROM salary_offers WHERE id=? AND user_id=?",
            (offer_id, user["id"]),
        ).fetchone()
    return _offer_record(row)


@router.delete(
    "/salary/offers/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Career Platform - Salary Intelligence"],
)
def delete_salary_offer(
    offer_id: str,
    user: dict[str, str] = Depends(current_user),
) -> None:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "DELETE FROM salary_offers WHERE id=? AND user_id=?",
            (offer_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved salary offer not found.")


@router.get("/salary/comparisons", tags=["Career Platform - Salary Intelligence"])
def list_salary_offer_comparisons(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            "SELECT * FROM salary_offer_comparisons WHERE user_id=? ORDER BY updated_at DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    return [_comparison_record(row) for row in rows]


@router.post(
    "/salary/comparisons",
    status_code=status.HTTP_201_CREATED,
    tags=["Career Platform - Salary Intelligence"],
)
def create_salary_offer_comparison(
    payload: SalaryOfferComparisonInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    comparison_id = str(uuid.uuid4())
    now = utc_now()
    with database(immediate=True) as connection:
        offers = _comparison_offers(connection, payload.offer_ids, user["id"])
        connection.execute(
            "INSERT INTO salary_offer_comparisons"
            "(id, user_id, title, offer_ids_json, offers_snapshot_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                comparison_id,
                user["id"],
                payload.title,
                json.dumps(payload.offer_ids),
                protect_text(json.dumps(offers, ensure_ascii=False)),
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM salary_offer_comparisons WHERE id=? AND user_id=?",
            (comparison_id, user["id"]),
        ).fetchone()
    return _comparison_record(row)


@router.put("/salary/comparisons/{comparison_id}", tags=["Career Platform - Salary Intelligence"])
def update_salary_offer_comparison(
    comparison_id: str,
    payload: SalaryOfferComparisonInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    now = utc_now()
    with database(immediate=True) as connection:
        offers = _comparison_offers(connection, payload.offer_ids, user["id"])
        cursor = connection.execute(
            "UPDATE salary_offer_comparisons SET title=?, offer_ids_json=?, offers_snapshot_json=?, updated_at=? "
            "WHERE id=? AND user_id=?",
            (
                payload.title,
                json.dumps(payload.offer_ids),
                protect_text(json.dumps(offers, ensure_ascii=False)),
                now,
                comparison_id,
                user["id"],
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved salary comparison not found.")
        row = connection.execute(
            "SELECT * FROM salary_offer_comparisons WHERE id=? AND user_id=?",
            (comparison_id, user["id"]),
        ).fetchone()
    return _comparison_record(row)


@router.delete(
    "/salary/comparisons/{comparison_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Career Platform - Salary Intelligence"],
)
def delete_salary_offer_comparison(
    comparison_id: str,
    user: dict[str, str] = Depends(current_user),
) -> None:
    with database(immediate=True) as connection:
        cursor = connection.execute(
            "DELETE FROM salary_offer_comparisons WHERE id=? AND user_id=?",
            (comparison_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved salary comparison not found.")


@router.get("/salary/benchmarks", tags=["Career Platform - Salary Intelligence"])
def salary_benchmarks(
    role: str = Query(..., min_length=2, max_length=120),
    location: str = Query(default="", max_length=120),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    company: str = Query(default="", max_length=120),
    experience_level: str = Query(default="", max_length=80),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    clauses = [
        "(j.visibility='public' OR j.owner_user_id=?)",
        "j.salary_min IS NOT NULL",
        "j.salary_max IS NOT NULL",
        "j.title LIKE ? COLLATE NOCASE",
    ]
    params: list[Any] = [user["id"], f"%{role}%"]
    for column, value in (
        ("location", location),
        ("salary_currency", currency or ""),
        ("company_name", company),
        ("experience_level", experience_level),
    ):
        if value:
            clauses.append(f"j.{column} LIKE ? COLLATE NOCASE")
            params.append(f"%{value}%")
    with database() as connection:
        rows = connection.execute(
            "SELECT j.title, j.company_name, j.location, j.experience_level, "
            "j.salary_min, j.salary_max, j.salary_currency, j.salary_period, "
            "j.source_label, j.source_url, j.original_url, j.raw_json, j.updated_at "
            "FROM jobs j WHERE " + " AND ".join(clauses) +
            " ORDER BY j.updated_at DESC LIMIT 1000",
            params,
        ).fetchall()
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        key = (item["salary_currency"] or "unknown", item["salary_period"] or "unspecified")
        groups.setdefault(key, []).append(item)
    samples = []
    for (unit, period), records in groups.items():
        midpoints = sorted((item["salary_min"] + item["salary_max"]) / 2 for item in records)
        middle = len(midpoints) // 2
        median_value = (
            midpoints[middle]
            if len(midpoints) % 2
            else (midpoints[middle - 1] + midpoints[middle]) / 2
        )
        observations = []
        for item in records[:100]:
            metadata = _raw_metadata(item["raw_json"])
            predicted = metadata.get("salary_is_predicted")
            observations.append({
                "role": item["title"],
                "company": item["company_name"],
                "location": item["location"],
                "experience_level": item["experience_level"],
                "minimum": item["salary_min"],
                "maximum": item["salary_max"],
                "currency": item["salary_currency"],
                "reporting_period": item["salary_period"] or "unspecified",
                "source": item["source_label"],
                "source_url": item["original_url"],
                "source_updated_at": item["updated_at"],
                "salary_is_predicted": (
                    None if predicted is None else predicted not in (0, "0", False)
                ),
            })
        samples.append({
            "currency": unit,
            "reporting_period": period,
            "sample_size": len(records),
            "minimum": min(item["salary_min"] for item in records),
            "median_of_listing_midpoints": median_value,
            "maximum": max(item["salary_max"] for item in records),
            "sample_strength": "higher" if len(records) >= 20 else "moderate" if len(records) >= 5 else "low",
            "observations": observations,
        })
    return {
        "filters": {
            "role": role, "location": location or None, "currency": currency,
            "company": company or None, "experience_level": experience_level or None,
        },
        "sample_size": len(rows),
        "samples": samples,
        "data_as_of": max((row["updated_at"] for row in rows), default=None),
        "message": None if rows else "No authorized listings with disclosed salary match these filters.",
        "limitations": [
            "These are descriptive statistics from authorized job listings, not a market-wide estimate.",
            "Currencies and reporting periods are kept separate; no currency conversion or tax adjustment is applied.",
            "Predicted salary labels follow the provider metadata where it is available.",
        ],
    }


@router.post("/salary/estimate", tags=["Career Platform - Salary Intelligence"])
async def estimate_salary(
    payload: SalaryEstimateInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    benchmark = salary_benchmarks(
        role=payload.role,
        location=payload.location,
        currency=payload.currency,
        company=payload.company,
        experience_level=payload.experience_level,
        user=user,
    )
    if not benchmark["samples"]:
        return {
            "estimate_available": False,
            "benchmarks": benchmark,
            "guidance": None,
            "message": "No estimate is available because there are no matching authorized salary listings.",
        }
    sample_context = [
        {
            "currency": sample["currency"],
            "reporting_period": sample["reporting_period"],
            "sample_size": sample["sample_size"],
            "minimum": sample["minimum"],
            "median_of_listing_midpoints": sample["median_of_listing_midpoints"],
            "maximum": sample["maximum"],
            "observations": sample["observations"][:20],
        }
        for sample in benchmark["samples"]
    ]
    response = await run_charged_ai_operation(
        user["id"],
        "salary_guidance",
        lambda: answer_career_question({
        "question": (
            "Interpret the supplied source-linked salary listing sample for the requested role. "
            "Do not invent a salary, benchmark, currency conversion, employer fact, or probability. "
            "Use only the exact values and currencies supplied; distinguish listing evidence from "
            "a market-wide estimate and explain sample limitations. Provide cautious compensation "
            "positioning and note relevant experience and skills only as context. Do not output "
            "any numbers, dates, percentages, currency amounts, or compensation ranges; reference "
            "the displayed listing statistics without repeating them."
        ),
        "salary_estimation_context": {
            "target": payload.model_dump(),
            "resume_evidence": _resume_evidence(user["id"]),
            "listing_samples": sample_context,
        },
        }),
    )
    return {
        "estimate_available": True,
        "benchmarks": benchmark,
        "guidance": response,
        "method": "AI interpretation grounded in the matched listing observations; numeric range is computed only from reported source data.",
        "notice": "This is an indicative interpretation, not a verified market-wide estimate or guaranteed offer.",
    }


@router.post("/salary/calculate", tags=["Career Platform - Salary Intelligence"])
def calculate_salary(
    payload: SalaryCalculatorInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    annual_cash = payload.annual_fixed + payload.annual_variable + payload.annual_bonus
    annual_total = annual_cash + payload.annual_equity
    annual_tax_assumption = annual_cash * payload.annual_tax_rate_percent / 100
    monthly_gross = annual_cash / 12
    monthly_tax = annual_tax_assumption / 12
    monthly_take_home = monthly_gross - monthly_tax - payload.monthly_deductions
    return {
        "currency": payload.currency.upper(),
        "annual_components": {
            "fixed": payload.annual_fixed,
            "variable": payload.annual_variable,
            "bonus": payload.annual_bonus,
            "equity": payload.annual_equity,
        },
        "annual_total_compensation": annual_total,
        "annual_cash_compensation": annual_cash,
        "monthly_gross": monthly_gross,
        "assumptions": {
            "annual_tax_rate_percent": payload.annual_tax_rate_percent,
            "monthly_deductions": payload.monthly_deductions,
            "tax_notice": "Illustrative user-configured rate only; this is not a current tax-rule calculation or tax advice.",
            "monthly_notice": "Monthly gross is an annualized cash-compensation equivalent; actual payment timing may differ.",
            "equity_notice": "Equity is included only as user-entered annualized value; it may not be liquid or guaranteed.",
        },
        "estimated_monthly_take_home": monthly_take_home,
        "calculated_at": utc_now(),
    }


@router.post("/salary/growth-scenario", tags=["Career Platform - Salary Intelligence"])
def salary_growth_scenario(
    payload: SalaryGrowthInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    rate = payload.annual_growth_rate_percent / 100
    rows = [
        {
            "year": year,
            "illustrative_annual_compensation": round(payload.current_annual_compensation * ((1 + rate) ** year), 2),
        }
        for year in range(payload.years + 1)
    ]
    return {
        "currency": payload.currency.upper(),
        "annual_growth_rate_percent": payload.annual_growth_rate_percent,
        "scenario": rows,
        "notice": "A mathematical scenario based only on the growth rate you entered; not a prediction or guarantee.",
    }


@router.post("/salary/readiness", tags=["Career Platform - Salary Intelligence"])
def salary_readiness(
    payload: SalaryReadinessInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    factors = [
        ("Written offer reviewed", payload.has_written_offer, 20),
        ("Relevant sourced benchmark", payload.has_reliable_benchmark, 25),
        ("Documented impact examples", payload.has_documented_impact, 20),
        ("Target and walk-away floor", payload.has_target_and_floor, 20),
        ("Total compensation reviewed", payload.has_reviewed_total_compensation, 15),
    ]
    score = sum(weight for _, complete, weight in factors if complete)
    return {
        "score": score,
        "label": "Negotiation preparation checklist, not a prediction of negotiation success.",
        "factors": [
            {"factor": title, "complete": complete, "weight": weight}
            for title, complete, weight in factors
        ],
        "next_steps": [
            title for title, complete, _ in factors if not complete
        ],
    }


@router.post("/salary/offers/analyze", tags=["Career Platform - Salary Intelligence"])
async def analyze_offer_letter(
    offer_file: UploadFile = File(...),
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    content = await read_upload_file(offer_file)
    extracted_text, file_type, warnings = extract_resume_text(
        offer_file.filename or "offer-letter.docx", content
    )
    if len(extracted_text) > 30_000:
        raise HTTPException(status_code=413, detail="Offer document text exceeds the 30,000 character limit.")
    relevant_lines = [
        line.strip()[:500]
        for line in extracted_text.splitlines()
        if _FINANCIAL_TERMS.search(line)
    ][:100]
    return {
        "filename": offer_file.filename or "offer-letter",
        "file_type": file_type,
        "financial_terms_found": relevant_lines,
        "extracted_text": extracted_text,
        "warnings": warnings,
        "notice": "Extracted text is for your review. Verify every amount and condition against the original offer; the document is not stored.",
    }


@router.post("/salary/offers/explain", tags=["Career Platform - Salary Intelligence"])
async def explain_offer_terms(
    payload: SalaryOfferExplainInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    response = await run_charged_ai_operation(
        user["id"],
        "salary_guidance",
        lambda: answer_career_question({
        "question": (
            "Explain the compensation, benefits, conditions, and terminology stated in this offer "
            "letter text. Use only terms that appear in the supplied text, distinguish direct "
            "evidence from interpretation, flag ambiguous clauses for employer or legal review, "
            "and do not give tax or legal advice. Do not invent amounts or terms."
        ),
        "offer_letter_text": payload.extracted_text,
        }),
    )
    return {
        "explanation": response,
        "notice": "AI explanation based only on extracted text; verify all details with the employer and a qualified adviser where needed.",
        "generated_at": utc_now(),
    }


@router.post("/salary/negotiation-guidance", tags=["Career Platform - Salary Intelligence"])
async def salary_negotiation_guidance(
    payload: SalaryNegotiationInput,
    user: dict[str, str] = Depends(current_user),
) -> dict[str, Any]:
    _require_ai_consent(user["id"])
    benchmark = salary_benchmarks(
        role=payload.role,
        location=payload.location,
        currency=payload.currency,
        company=payload.company,
        experience_level="",
        user=user,
    )
    benchmark_context = [
        {
            "currency": sample["currency"],
            "reporting_period": sample["reporting_period"],
            "sample_size": sample["sample_size"],
            "minimum": sample["minimum"],
            "median_of_listing_midpoints": sample["median_of_listing_midpoints"],
            "maximum": sample["maximum"],
            "observations": sample["observations"][:10],
        }
        for sample in benchmark["samples"]
    ]
    context = {
        "question": (
            f"Create a {payload.request_type.replace('_', ' ')} for salary negotiations. "
            "Use only facts and amounts provided below, including cited listing benchmarks if any. "
            "Do not invent market facts, leverage, or promised outcomes. Never suggest a specific "
            "compensation amount unless the user provided it or it appears in the supplied benchmark "
            "data. Make it respectful, editable, and transparent about unknowns."
        ),
        "salary_context": {
            **payload.model_dump(),
            "currency": payload.currency.upper(),
            "benchmarks": benchmark_context,
            "benchmark_notice": (
                "Benchmarks are disclosed authorized listings, not market-wide data."
                if benchmark_context else
                "No matching disclosed salary listings are available; do not claim a market rate."
            ),
        },
        "resume_evidence": _resume_evidence(user["id"]),
    }
    response = await run_charged_ai_operation(
        user["id"], "salary_guidance", lambda: answer_career_question(context)
    )
    return {
        "guidance": response,
        "generated_at": utc_now(),
        "notice": "AI-generated draft based only on the details you supplied; review and personalize before use. Outcomes are not guaranteed.",
    }
