from typing import List, Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "Resume ATS Score Checker API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Security & CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # File Upload Limits
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB conservative limit
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx"]
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",  # Often sent by browsers for binary formats
    ]

    # Analysis Engine Scoring Weights
    WEIGHT_KEYWORD_COVERAGE: float = 35.0
    WEIGHT_SKILLS_MATCH: float = 25.0
    WEIGHT_EXPERIENCE_EVIDENCE: float = 20.0
    WEIGHT_EDUCATION_MATCH: float = 10.0
    WEIGHT_STRUCTURE_READABILITY: float = 10.0

    @field_validator("DEBUG", mode="before")
    @classmethod
    def assemble_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on", "debug")
        return bool(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
