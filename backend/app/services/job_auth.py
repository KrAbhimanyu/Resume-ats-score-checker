import hashlib
import hmac
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings
from app.db.database import database, utc_now
from app.models.job_schemas import AuthResponse, UserSummary


bearer_scheme = HTTPBearer(auto_error=False)
_PASSWORD_ITERATIONS = 310_000


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _issue_session(user: dict[str, Any]) -> AuthResponse:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.JOB_SESSION_TTL_HOURS
    )
    with database() as connection:
        connection.execute(
            "DELETE FROM auth_sessions WHERE expires_at <= ?", (utc_now(),)
        )
        connection.execute(
            "INSERT INTO auth_sessions(token_hash, user_id, expires_at, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                hashlib.sha256(token.encode("ascii")).hexdigest(),
                user["id"],
                expires_at.isoformat(),
                utc_now(),
            ),
        )
    return AuthResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user=UserSummary(
            id=user["id"], email=user["email"], created_at=user["created_at"]
        ),
    )


def register_user(email: str, password: str) -> AuthResponse:
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": _hash_password(password),
        "created_at": utc_now(),
    }
    try:
        with database() as connection:
            connection.execute(
                "INSERT INTO users(id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user["id"], user["email"], user["password_hash"], user["created_at"]),
            )
    except Exception as exc:
        if "UNIQUE constraint failed: users.email" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from exc
        raise
    return _issue_session(user)


def login_user(email: str, password: str) -> AuthResponse:
    with database() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()
    if row is None or not _verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_session(dict(row))


def _verify_google_id_token(credential: str) -> dict[str, Any]:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured on the backend.",
        )

    try:
        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in token is invalid, expired, or signed for a different audience.",
        ) from exc

    issuer = str(payload.get("iss") or "")
    if issuer not in {"https://accounts.google.com", "accounts.google.com"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in token issuer is not trusted.",
        )

    email = str(payload.get("email") or "").strip().lower()
    if not email or payload.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email must be verified before sign-in is allowed.",
        )

    google_sub = str(payload.get("sub") or "").strip()
    if not google_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in token is missing the stable subject identifier.",
        )

    payload["normalized_email"] = email
    payload["normalized_sub"] = google_sub
    return payload


def login_google_user(credential: str) -> AuthResponse:
    payload = _verify_google_id_token(credential)
    email = str(payload.get("normalized_email") or "").strip().lower()
    google_sub = str(payload.get("normalized_sub") or "").strip()
    display_name = str(payload.get("name") or email.split("@", 1)[0]).strip() or email
    avatar_url = str(payload.get("picture") or "").strip()

    with database() as connection:
        existing = connection.execute(
            "SELECT id, email, password_hash, created_at, auth_provider, google_sub, display_name, avatar_url "
            "FROM users WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()

        if existing is None:
            user_id = str(uuid.uuid4())
            password_hash = _hash_password(secrets.token_urlsafe(32))
            try:
                connection.execute(
                    "INSERT INTO users(id, email, password_hash, created_at, auth_provider, google_sub, display_name, avatar_url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        email,
                        password_hash,
                        utc_now(),
                        "google",
                        google_sub,
                        display_name,
                        avatar_url,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "google_sub" in str(exc) or "ux_users_google_sub" in str(exc):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This Google account is already linked to a different user.",
                    ) from exc
                raise
            row = connection.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The Google account could not be linked to a user record.",
                )
            return _issue_session(dict(row))

        if existing["auth_provider"] == "google":
            if existing["google_sub"] and existing["google_sub"] != google_sub:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This Google account is already linked to another account.",
                )
            connection.execute(
                "UPDATE users SET google_sub=?, display_name=?, avatar_url=? WHERE id=?",
                (google_sub, display_name, avatar_url, existing["id"]),
            )
            row = connection.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id = ?",
                (existing["id"],),
            ).fetchone()
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email already belongs to a password-based account. Please sign in with your password to link Google securely.",
            )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Google account could not be linked to a user record.",
        )
    return _issue_session(dict(row))


def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to access job intelligence.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_hash = hashlib.sha256(credentials.credentials.encode("ascii")).hexdigest()
    now = utc_now()
    with database() as connection:
        row = connection.execute(
            """
            SELECT u.id, u.email, u.created_at
            FROM auth_sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dict(row)


def revoke_session(credentials: Optional[HTTPAuthorizationCredentials]) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return
    token_hash = hashlib.sha256(credentials.credentials.encode("ascii")).hexdigest()
    with database() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
