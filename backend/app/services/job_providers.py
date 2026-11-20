import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from app.config import settings
from app.db.database import database, utc_now
from app.services.job_matching import clean_job_text


ADZUNA_ATTRIBUTION = "https://developer.adzuna.com/overview"
GREENHOUSE_ATTRIBUTION = "https://docs.greenhouse.io/job-board.html"
LEVER_ATTRIBUTION = "https://github.com/lever/postings-api"
_CACHE_TTL_SECONDS = 600
_provider_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


class JobProviderError(Exception):
    def __init__(self, provider: str, code: str, message: str):
        super().__init__(message)
        self.provider = provider
        self.code = code


def _http_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ResumeCareerPlatform/1.0 (authorized job feed client)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200:
                raise JobProviderError("provider", "http_error", f"Provider returned HTTP {response.status}.")
            return json.loads(response.read(5_000_001).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        code = "rate_limited" if exc.code == 429 else "provider_http_error"
        raise JobProviderError("provider", code, f"Provider returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JobProviderError("provider", "provider_unavailable", "Could not retrieve valid job data from provider.") from exc


def _cache_key(provider: str, params: dict[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{provider}:{payload}".encode("utf-8")).hexdigest()


def _fetch_cached(provider: str, params: dict[str, Any], fetch: Callable[[], list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], bool]:
    key = _cache_key(provider, params)
    with _locks_guard:
        lock = _provider_locks.setdefault(provider, threading.Lock())
    with lock:
        return _fetch_cached_locked(provider, key, fetch)


def _reserve_provider_slot(provider: str) -> None:
    minimum_interval = (
        settings.ADZUNA_MIN_INTERVAL_SECONDS
        if provider == "adzuna" else settings.COMPANY_BOARD_MIN_INTERVAL_SECONDS
    )
    while True:
        wait_seconds = 0.0
        with database(immediate=True) as connection:
            row = connection.execute(
                "SELECT last_attempt_at FROM provider_syncs WHERE provider=?", (provider,)
            ).fetchone()
            last_attempt = row["last_attempt_at"] if row else None
            wait_seconds = 0.0
            if last_attempt:
                try:
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_attempt)).total_seconds()
                    wait_seconds = minimum_interval - elapsed
                except ValueError:
                    wait_seconds = 0.0
            if wait_seconds <= 0:
                now = utc_now()
                connection.execute(
                    "INSERT INTO provider_syncs(provider, last_attempt_at, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(provider) DO UPDATE SET last_attempt_at=excluded.last_attempt_at, updated_at=excluded.updated_at",
                    (provider, now, now),
                )
                return
        time.sleep(wait_seconds)


def _fetch_cached_locked(provider: str, key: str, fetch: Callable[[], list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], bool]:
    now = datetime.now(timezone.utc)
    with database() as connection:
        row = connection.execute(
            "SELECT response_json, expires_at FROM provider_search_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row:
            try:
                if datetime.fromisoformat(row["expires_at"]) > now:
                    return json.loads(row["response_json"]), True
            except (ValueError, json.JSONDecodeError):
                connection.execute("DELETE FROM provider_search_cache WHERE cache_key = ?", (key,))
    _reserve_provider_slot(provider)
    try:
        jobs = fetch()
    except JobProviderError as exc:
        with database() as connection:
            connection.execute(
                "INSERT INTO provider_syncs(provider, last_error_at, last_error_code, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(provider) DO UPDATE SET "
                "last_error_at=excluded.last_error_at, last_error_code=excluded.last_error_code, updated_at=excluded.updated_at",
                (provider, utc_now(), exc.code, utc_now()),
            )
        raise
    with database() as connection:
        connection.execute(
            "INSERT INTO provider_search_cache(cache_key, provider, response_json, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(cache_key) DO UPDATE SET "
            "response_json=excluded.response_json, expires_at=excluded.expires_at, created_at=excluded.created_at",
            (
                key,
                provider,
                json.dumps(jobs, ensure_ascii=False),
                (now + timedelta(seconds=settings.JOB_SEARCH_CACHE_SECONDS)).isoformat(),
                now.isoformat(),
            ),
        )
        connection.execute(
            "INSERT INTO provider_syncs(provider, last_success_at, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(provider) DO UPDATE SET last_success_at=excluded.last_success_at, last_error_code=NULL, updated_at=excluded.updated_at",
            (provider, now.isoformat(), now.isoformat()),
        )
    return jobs, False


def provider_status() -> list[dict[str, Any]]:
    adzuna_ready = bool(
        settings.ADZUNA_APP_ID
        and settings.ADZUNA_APP_KEY
        and settings.ADZUNA_COMMERCIAL_USE_CONFIRMED
    )
    board_permission = settings.CAREER_BOARD_PERMISSION_CONFIRMED
    greenhouse_boards = _parse_named_values(settings.GREENHOUSE_BOARD_TOKENS)
    lever_sites = _parse_named_values(settings.LEVER_SITE_NAMES)
    return [
        {
            "provider": "adzuna",
            "enabled": adzuna_ready,
            "reason": None if adzuna_ready else "Requires API credentials and confirmation of commercial-use rights.",
            "attribution_url": ADZUNA_ATTRIBUTION,
        },
        {
            "provider": "greenhouse",
            "enabled": bool(board_permission and greenhouse_boards),
            "reason": None if board_permission and greenhouse_boards else "Requires configured employer board tokens and permission to use their listings.",
            "attribution_url": GREENHOUSE_ATTRIBUTION,
        },
        {
            "provider": "lever",
            "enabled": bool(board_permission and lever_sites),
            "reason": None if board_permission and lever_sites else "Requires configured employer site names and permission to use their listings.",
            "attribution_url": LEVER_ATTRIBUTION,
        },
    ]


def _parse_named_values(value: str) -> list[tuple[str, Optional[str]]]:
    entries: list[tuple[str, Optional[str]]] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if ":" in raw:
            key, label = raw.split(":", 1)
            entries.append((key.strip(), label.strip() or None))
        else:
            entries.append((raw, None))
    return entries


def _provider_datetime(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _remote_type(value: str) -> Optional[str]:
    text = value.casefold()
    if re.search(r"\b(no|not|never)\s+remote\b", text):
        return None
    if re.search(r"\bhybrid\b", text):
        return "hybrid"
    if re.search(r"\b(remote|work from home|work-from-home|fully distributed)\b", text):
        return "remote"
    if re.search(r"\b(on[- ]site|in[- ]office|office[- ]based)\b", text):
        return "on_site"
    return None


def _employment_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    clean = re.sub(r"[_\s]+", "-", clean_job_text(value).strip().lower())
    return clean or None


def _parse_salary_text(value: str) -> tuple[float | None, float | None, str | None]:
    match = re.search(r"(?i)(₹|INR|\$|USD|£|GBP|€|EUR)?\s*([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*([\d,]+(?:\.\d+)?)\s*(k|lpa|lakhs?)?", value or "")
    if not match:
        return None, None, None
    symbol, low, high, unit = match.groups()
    currency = {"₹": "INR", "$": "USD", "£": "GBP", "€": "EUR"}.get(symbol, symbol.upper() if symbol else None)
    factor = 100_000 if (unit or "").lower().startswith(("lpa", "lakh")) else 1000 if (unit or "").lower() == "k" else 1
    return float(low.replace(",", "")) * factor, float(high.replace(",", "")) * factor, currency


def _normalize_job(
    provider: str,
    provider_id: str | int,
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    source_url: str,
    posted_at: str | None,
    *,
    country: str | None = None,
    remote_type: str | None = None,
    employment_type: str | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    salary_currency: str | None = None,
    salary_period: str | None = None,
    expires_at: str | None = None,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_title = clean_job_text(title)[:200] or "Untitled posting"
    clean_location = clean_job_text(location)[:200] or None
    clean_description = clean_job_text(description)[:100_000]
    deadline = _provider_datetime(expires_at)
    return {
        "source": provider,
        "source_job_id": str(provider_id),
        "title": clean_title,
        "company_name": clean_job_text(company)[:200] or "Company not specified",
        "location": clean_location,
        "country": country,
        "remote_type": remote_type or _remote_type(f"{clean_title} {clean_location or ''} {clean_description}"),
        "employment_type": _employment_type(employment_type),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_currency,
        "salary_period": salary_period or ("unspecified" if salary_min is not None else None),
        "description": clean_description,
        "original_url": url,
        "posted_at": posted_at,
        "expires_at": deadline,
        "availability": "expired" if deadline and datetime.fromisoformat(deadline) <= datetime.now(timezone.utc) else "unknown",
        "source_label": provider.title(),
        "source_url": source_url,
        "raw": raw or {},
    }


def _search_adzuna(query: str, location: str, country: str, page: int, page_size: int) -> list[dict[str, Any]]:
    if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY or not settings.ADZUNA_COMMERCIAL_USE_CONFIRMED:
        raise JobProviderError("adzuna", "not_configured", "Adzuna requires credentials and confirmed commercial-use permission.")
    configured_countries = {item.strip().lower() for item in settings.ADZUNA_COUNTRIES.split(",") if item.strip()}
    if country not in configured_countries:
        raise JobProviderError("adzuna", "country_not_configured", f"Adzuna country '{country}' is not enabled in ADZUNA_COUNTRIES.")
    params = urllib.parse.urlencode({
        "app_id": settings.ADZUNA_APP_ID,
        "app_key": settings.ADZUNA_APP_KEY,
        "results_per_page": page_size,
        "what": query,
        "where": location,
        "content-type": "application/json",
    })
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?{params}"
    payload = _http_json(url)
    results = payload.get("results", [])
    jobs = []
    for item in results:
        job_url = item.get("redirect_url")
        if not job_url or not str(job_url).startswith("https://"):
            continue
        jobs.append(_normalize_job(
            "adzuna", item.get("id"), item.get("title", ""),
            (item.get("company") or {}).get("display_name", ""),
            (item.get("location") or {}).get("display_name", ""),
            item.get("description", ""), job_url, ADZUNA_ATTRIBUTION,
            item.get("created"),
            country=country,
            employment_type=(item.get("contract_time") or item.get("contract_type")),
            salary_min=item.get("salary_min"), salary_max=item.get("salary_max"),
            salary_currency=item.get("salary_currency"),
            expires_at=item.get("expires_at") or item.get("application_deadline"),
            raw={
                "category": (item.get("category") or {}).get("label"),
                "salary_is_predicted": item.get("salary_is_predicted"),
            },
        ))
    return jobs


def _search_greenhouse(query: str, location: str, page: int, page_size: int) -> list[dict[str, Any]]:
    if not settings.CAREER_BOARD_PERMISSION_CONFIRMED:
        raise JobProviderError("greenhouse", "permission_required", "Confirm permission to use configured employer job boards.")
    jobs = []
    for board_token, company_label in _parse_named_values(settings.GREENHOUSE_BOARD_TOKENS):
        safe_token = urllib.parse.quote(board_token, safe="")
        payload = _http_json(f"https://boards-api.greenhouse.io/v1/boards/{safe_token}/jobs?content=true")
        for item in payload.get("jobs", []):
            title = item.get("title", "")
            place = (item.get("location") or {}).get("name", "")
            if query and query.casefold() not in title.casefold() and query.casefold() not in item.get("content", "").casefold():
                continue
            if location and location.casefold() not in place.casefold():
                continue
            url = item.get("absolute_url", "")
            if not url.startswith("https://"):
                continue
            jobs.append(_normalize_job(
                "greenhouse", item.get("id"), title, company_label or board_token, place,
                item.get("content", ""), url, GREENHOUSE_ATTRIBUTION,
                item.get("updated_at"),
                expires_at=item.get("application_deadline") or item.get("expires_at"),
                raw={"board_token": board_token},
            ))
    start = (page - 1) * page_size
    return jobs[start:start + page_size]


def _search_lever(query: str, location: str, page: int, page_size: int) -> list[dict[str, Any]]:
    if not settings.CAREER_BOARD_PERMISSION_CONFIRMED:
        raise JobProviderError("lever", "permission_required", "Confirm permission to use configured employer job boards.")
    jobs = []
    for site, company_label in _parse_named_values(settings.LEVER_SITE_NAMES):
        endpoint = "https://api.eu.lever.co" if site.startswith("eu/") else "https://api.lever.co"
        site_name = site[3:] if site.startswith("eu/") else site
        payload = _http_json(f"{endpoint}/v0/postings/{urllib.parse.quote(site_name, safe='')}?mode=json")
        if not isinstance(payload, list):
            raise JobProviderError("lever", "invalid_response", "Lever returned an unexpected response.")
        for item in payload:
            title = item.get("text", "")
            place = (item.get("categories") or {}).get("location", "")
            if query and query.casefold() not in title.casefold() and query.casefold() not in item.get("descriptionPlain", "").casefold():
                continue
            if location and location.casefold() not in place.casefold():
                continue
            url = item.get("hostedUrl", "")
            if not url.startswith("https://"):
                continue
            low, high, currency = _parse_salary_text(item.get("salaryRange", ""))
            jobs.append(_normalize_job(
                "lever", item.get("id"), title, company_label or site_name, place,
                item.get("descriptionPlain") or item.get("description", ""), url,
                LEVER_ATTRIBUTION, item.get("createdAt"),
                expires_at=item.get("expiresAt") or item.get("applicationDeadline"),
                salary_min=low, salary_max=high, salary_currency=currency,
                raw={"site": site, "salary_provided": bool(item.get("salaryRange"))},
            ))
    start = (page - 1) * page_size
    return jobs[start:start + page_size]


_SEARCHERS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "adzuna": _search_adzuna,
    "greenhouse": _search_greenhouse,
    "lever": _search_lever,
}


def search_authorized_providers(
    query: str, location: str, country: str, page: int, page_size: int
) -> dict[str, Any]:
    result: dict[str, Any] = {"jobs": [], "providers": [], "warnings": [], "has_more": False}
    for provider in provider_status():
        if not provider["enabled"]:
            result["providers"].append({**provider, "status": "not_configured"})
            continue
        searcher = _SEARCHERS[provider["provider"]]
        params = {
            "query": query, "location": location, "country": country,
            "page": page, "page_size": page_size,
        }
        try:
            jobs, cached = _fetch_cached(
                provider["provider"],
                params,
                lambda: searcher(query, location, country, page, page_size)
                if provider["provider"] == "adzuna"
                else searcher(query, location, page, page_size),
            )
            result["jobs"].extend(jobs)
            result["has_more"] = result["has_more"] or len(jobs) >= page_size
            result["providers"].append({**provider, "status": "ok", "cached": cached})
        except JobProviderError as exc:
            result["providers"].append({
                **provider, "status": "error", "error_code": exc.code, "message": str(exc)
            })
            result["warnings"].append(str(exc))
    unique_jobs: dict[str, dict[str, Any]] = {}
    identities: dict[str, str] = {}
    for job in result["jobs"]:
        url_key = str(job.get("original_url") or "").split("#", 1)[0].split("?", 1)[0].rstrip("/").casefold()
        signature = "|".join(
            str(job.get(field) or "").strip().casefold()
            for field in ("title", "company_name", "location")
        )
        identity = identities.get(url_key) if url_key else None
        identity = identity or identities.get(signature) or url_key or signature
        existing = unique_jobs.get(identity)
        if existing is None or (
            sum(value is not None for value in (job.get("salary_min"), job.get("expires_at"), job.get("posted_at")))
            > sum(value is not None for value in (existing.get("salary_min"), existing.get("expires_at"), existing.get("posted_at")))
        ):
            unique_jobs[identity] = job
        if url_key:
            identities[url_key] = identity
        identities[signature] = identity
    result["jobs"] = sorted(
        (job for job in unique_jobs.values() if job.get("availability") != "expired"),
        key=lambda job: job.get("posted_at") or "",
        reverse=True,
    )
    return result
