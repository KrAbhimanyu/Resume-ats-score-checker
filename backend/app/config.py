from typing import List, Union, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "Resume ATS Score Checker API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    JOB_DATABASE_PATH: str = "backend/data/job-intelligence.sqlite3"
    JOB_DATA_ENCRYPTION_KEY: str = ""
    JOB_SESSION_TTL_HOURS: int = Field(default=720, ge=1, le=8760)
    JOB_MATCH_WEIGHT_SKILLS: float = Field(default=0.40, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_EXPERIENCE: float = Field(default=0.20, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_RESPONSIBILITIES: float = Field(default=0.15, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_EDUCATION: float = Field(default=0.10, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_CERTIFICATIONS: float = Field(default=0.05, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_KEYWORDS: float = Field(default=0.10, ge=0, allow_inf_nan=False)
    JOB_MATCH_WEIGHT_LOCATION: float = Field(default=0.05, ge=0, allow_inf_nan=False)
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    ADZUNA_COMMERCIAL_USE_CONFIRMED: bool = False
    ADZUNA_COUNTRIES: str = "gb"
    ADZUNA_MIN_INTERVAL_SECONDS: float = 1.0
    JOB_SEARCH_CACHE_SECONDS: int = 600
    CAREER_BOARD_PERMISSION_CONFIRMED: bool = False
    GREENHOUSE_BOARD_TOKENS: str = ""
    LEVER_SITE_NAMES: str = ""
    COMPANY_BOARD_MIN_INTERVAL_SECONDS: float = 1.0
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    RESUME_AI_API_KEY: str = ""
    RESUME_AI_MODEL: str = "gpt-4o-mini"
    RESUME_AI_TIMEOUT_SECONDS: int = Field(default=45, ge=5, le=180)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173"
    BUSINESS_CHECKOUT_SUCCESS_URL: str = ""
    BUSINESS_CHECKOUT_CANCEL_URL: str = ""
    BUSINESS_ADMIN_EMAILS: str = ""

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

    @field_validator("ADZUNA_COMMERCIAL_USE_CONFIRMED", mode="before")
    @classmethod
    def parse_adzuna_confirmation(cls, value: Any) -> bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    @field_validator("CAREER_BOARD_PERMISSION_CONFIRMED", mode="before")
    @classmethod
    def parse_board_permission_confirmation(cls, value: Any) -> bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
