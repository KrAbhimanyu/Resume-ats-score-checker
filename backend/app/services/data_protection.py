from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.config import settings


_ENCRYPTED_PREFIX = "fernet:v1:"


def _cipher() -> Fernet:
    key = settings.JOB_DATA_ENCRYPTION_KEY.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume and private career data storage is disabled until JOB_DATA_ENCRYPTION_KEY is configured.",
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JOB_DATA_ENCRYPTION_KEY must be a valid Fernet key.",
        ) from exc


def protect_text(value: str) -> str:
    if not value:
        return ""
    token = _cipher().encrypt(value.encode("utf-8")).decode("ascii")
    return _ENCRYPTED_PREFIX + token


def reveal_text(value: str | None) -> str:
    if not value:
        return ""
    if not value.startswith(_ENCRYPTED_PREFIX):
        return value
    try:
        return _cipher().decrypt(value[len(_ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored career data could not be decrypted. Verify the configured data encryption key.",
        ) from exc
