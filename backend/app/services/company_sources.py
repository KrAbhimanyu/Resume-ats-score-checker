import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status

from app.core.logging_config import logger


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_ATTRIBUTION = "https://www.wikidata.org/wiki/"
WIKIDATA_API_DOCUMENTATION = "https://www.wikidata.org/w/api.php"
_ENTITY_PATTERN = re.compile(r"^Q[1-9][0-9]{0,11}$")


def _wikidata_json(params: dict[str, str]) -> dict[str, Any]:
    url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ResumeATSCareerPlatform/1.0 (+https://github.com/KrAbhimanyu/resume-ats-score-checker)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read(3_000_001).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Wikidata response must be an object")
        return payload
    except urllib.error.HTTPError as exc:
        logger.error("Wikidata API returned HTTP %s", exc.code)
        if exc.code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Wikidata rate limit reached. Wait before searching or refreshing company profiles.",
                headers={"Retry-After": exc.headers.get("Retry-After", "60") if exc.headers else "60"},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Company profile data is temporarily unavailable from Wikidata.",
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.error("Wikidata API connection failed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the public company profile source. Try again later.",
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        logger.error("Wikidata API returned invalid data: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Wikidata returned an invalid company profile response.",
        ) from exc


def search_companies(query: str, limit: int = 10) -> list[dict[str, Any]]:
    clean_query = query.strip()
    if len(clean_query) < 2:
        raise HTTPException(status_code=422, detail="Enter at least two characters to search for a company.")
    payload = _wikidata_json({
        "action": "wbsearchentities",
        "search": clean_query[:160],
        "language": "en",
        "uselang": "en",
        "type": "item",
        "limit": str(max(1, min(limit, 15))),
        "format": "json",
    })
    entities = payload.get("search", [])
    if not isinstance(entities, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Wikidata returned an invalid company search response.",
        )
    retrieved_at = datetime.now(timezone.utc).isoformat()
    organization_description = re.compile(
        r"\b(company|corporation|corporate|business|enterprise|firm|brand|bank|airline|"
        r"manufacturer|retailer|publisher|studio|agency|organization|organisation|"
        r"subsidiary|multinational|nonprofit|non-profit|university|employer|"
        r"conglomerate|platform|streaming|software|technology|telecommunications|"
        r"telecom|automaker|automotive|media group|search engine)\b",
        re.IGNORECASE,
    )
    return [
        {
            "entity_id": item["id"],
            "name": item.get("label") or item["id"],
            "description": item.get("description"),
            "source": "Wikidata",
            "source_url": item.get("concepturi") or f"{WIKIDATA_ATTRIBUTION}{item['id']}",
            "retrieved_at": retrieved_at,
        }
        for item in entities
        if isinstance(item, dict) and isinstance(item.get("id"), str)
        and _ENTITY_PATTERN.fullmatch(item["id"])
        and isinstance(item.get("description"), str)
        and organization_description.search(item["description"])
    ]


def _claim_values(claims: dict[str, Any], property_id: str) -> list[dict[str, Any]]:
    values = []
    for statement in claims.get(property_id, []):
        data_value = statement.get("mainsnak", {}).get("datavalue", {}).get("value")
        if data_value is None:
            continue
        qualifier_dates = []
        for qualifier in statement.get("qualifiers", {}).get("P585", []):
            qualifier_value = qualifier.get("datavalue", {}).get("value", {})
            if isinstance(qualifier_value, dict) and isinstance(qualifier_value.get("time"), str):
                qualifier_dates.append(qualifier_value["time"].lstrip("+"))
        values.append({"value": data_value, "as_of": max(qualifier_dates) if qualifier_dates else None})
    return values


def _entity_ids(values: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(
        value["value"]["id"]
        for value in values
        if isinstance(value.get("value"), dict)
        and isinstance(value["value"].get("id"), str)
        and _ENTITY_PATTERN.fullmatch(value["value"]["id"])
    ))


def _labels(entity_ids: list[str]) -> dict[str, str]:
    if not entity_ids:
        return {}
    payload = _wikidata_json({
        "action": "wbgetentities",
        "ids": "|".join(entity_ids[:50]),
        "languages": "en",
        "props": "labels",
        "format": "json",
    })
    entities = payload.get("entities", {})
    if not isinstance(entities, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Wikidata returned invalid company category labels.",
        )
    return {
        entity_id: entity.get("labels", {}).get("en", {}).get("value", entity_id)
        for entity_id, entity in entities.items()
        if isinstance(entity, dict)
    }


def company_profile(entity_id: str, *, name_hint: Optional[str] = None) -> dict[str, Any]:
    if not _ENTITY_PATTERN.fullmatch(entity_id):
        raise HTTPException(status_code=422, detail="The company entity ID is invalid.")
    payload = _wikidata_json({
        "action": "wbgetentities",
        "ids": entity_id,
        "languages": "en",
        "props": "labels|descriptions|claims|sitelinks",
        "format": "json",
    })
    entity = payload.get("entities", {}).get(entity_id)
    if not isinstance(entity, dict) or "missing" in entity:
        raise HTTPException(status_code=404, detail="Company entity was not found in Wikidata.")
    labels = entity.get("labels", {})
    name = labels.get("en", {}).get("value") or name_hint or entity_id
    claims = entity.get("claims", {})
    industry_claims = _claim_values(claims, "P452")
    headquarters_claims = _claim_values(claims, "P159")
    related_entity_ids = list(dict.fromkeys(
        _entity_ids(industry_claims) + _entity_ids(headquarters_claims)
    ))
    related_labels = _labels(related_entity_ids)
    website_values = _claim_values(claims, "P856")
    employees_values = _claim_values(claims, "P1128")
    inception_values = _claim_values(claims, "P571")
    employee_claim = employees_values[-1] if employees_values else None
    employee_value = employee_claim.get("value") if employee_claim else None
    employee_count = None
    if isinstance(employee_value, dict):
        try:
            employee_count = float(str(employee_value.get("amount", "")).lstrip("+"))
        except ValueError:
            employee_count = None
    elif isinstance(employee_value, (int, float)):
        employee_count = float(employee_value)
    description = entity.get("descriptions", {}).get("en", {}).get("value")
    sitelinks = entity.get("sitelinks", {})
    wikipedia = sitelinks.get("enwiki", {})
    wikidata_url = f"{WIKIDATA_ATTRIBUTION}{entity_id}"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    return {
        "entity_id": entity_id,
        "name": name,
        "description": description,
        "industry": [
            {"name": related_labels.get(entity_link, entity_link), "entity_id": entity_link}
            for entity_link in _entity_ids(industry_claims)
        ],
        "headquarters": [
            {"name": related_labels.get(entity_link, entity_link), "entity_id": entity_link}
            for entity_link in _entity_ids(headquarters_claims)
        ],
        "employee_count": employee_count,
        "employee_count_as_of": employee_claim.get("as_of") if employee_claim else None,
        "inception_dates": [
            {"date": item["value"].get("time"), "precision": item["value"].get("precision")}
            for item in inception_values
            if isinstance(item.get("value"), dict)
        ],
        "official_websites": [
            item["value"] for item in website_values if isinstance(item.get("value"), str)
        ],
        "wikipedia_url": (
            f"https://{wikipedia.get('url')}"
            if isinstance(wikipedia, dict) and isinstance(wikipedia.get("url"), str)
            else None
        ),
        "source": "Wikidata",
        "source_url": wikidata_url,
        "source_modified_at": entity.get("modified"),
        "retrieved_at": retrieved_at,
        "unavailable_fields": [
            "Company culture and employee sentiment",
            "Company interview experiences and question records",
            "Company-specific compensation not disclosed in available listings",
        ],
    }
