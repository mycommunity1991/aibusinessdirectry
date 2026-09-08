import sys
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import API_PREFIX


def _parse_comma_separated_or_json_list(v: Any) -> list[str]:
    """
    Parses a comma-separated string (e.g. "a,b,c"), a JSON array string
    (e.g. '["a", "b"]'), or an already-a-list value into a `list[str]`.

    Shared by `ALLOWED_ORIGINS` and `APPLE_OAUTH_CLIENT_IDS`, which both
    accept the same env-var shapes.
    """
    if isinstance(v, str):
        if v.strip() == "":
            return []
        if v.startswith("[") and v.endswith("]"):
            import json

            try:
                loaded = json.loads(v)
                if isinstance(loaded, list):
                    return [str(item).strip() for item in loaded if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in v.split(",") if item.strip()]
    if isinstance(v, list):
        return [str(item).strip() for item in v if str(item).strip()]
    return []


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "AI Marketplace API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    API_PREFIX: str = API_PREFIX

    # Database Settings
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Redis Settings (caching, rate limiting — 06_SECURITY.md)
    REDIS_URL: str

    # Security Settings
    # Map to SECRET_KEY or fall back to JWT_SECRET_KEY for backward compatibility
    SECRET_KEY: str = Field(
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY")
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Logging Settings
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # CORS Settings
    ALLOWED_ORIGINS: list[str] | str = Field(default_factory=list)

    # OAuth Settings (AUTH-002 -- Google/Apple sign-in ID token audience
    # validation). Real values are external Google Cloud Console / Apple
    # Developer Portal configuration -- see `.env.example`.
    GOOGLE_OAUTH_CLIENT_ID: str
    APPLE_OAUTH_CLIENT_IDS: list[str] | str

    # File upload settings (PRO-002, Decision 2 -- `LocalFileStorage`,
    # explicitly interim until a future story adds `S3FileStorage`).
    # `UPLOAD_DIR` is git-ignored; served back to clients via a
    # `StaticFiles` mount at `/media` (`app/main.py`).
    UPLOAD_DIR: str = "uploads"
    MAX_PORTFOLIO_PHOTO_SIZE_BYTES: int = 5_242_880
    MAX_PORTFOLIO_PHOTOS_PER_PROVIDER: int = 20

    # Verification-document upload settings (VER-001, Decision 7,
    # `Plan_S05_VER-001.md`). A second, separate root from `UPLOAD_DIR`
    # above -- never mounted as `StaticFiles` (`app/main.py`), since
    # these documents (Emirates ID scans, trade licenses) are private
    # PII, unlike public portfolio photos.
    VERIFICATION_UPLOAD_DIR: str = "uploads_private/verification"
    MAX_VERIFICATION_DOCUMENT_SIZE_BYTES: int = 10_485_760

    # Business verification bar (VER-001, Decision 3,
    # `Plan_S04_PRO-001.md`'s successor `Plan_S05_VER-001.md`) --
    # config-driven per `04_DATABASE.md` Section 14's own stated intent,
    # since `13_OPEN_DECISIONS.md` item 5 remains unresolved. Freelancer
    # is never config-driven (always `freelancer_id`, always required).
    BUSINESS_VERIFICATION_TYPE: str = "business_lightweight"
    BUSINESS_VERIFICATION_DOCUMENT_REQUIRED: bool = False

    # Config dict to support loading from parent .env or current .env
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a valid PostgreSQL connection string starting "
                "with postgresql://, postgresql+psycopg://, or postgres://"
            )
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError(
                "REDIS_URL must be a valid Redis connection string starting "
                "with redis://, rediss://, or unix://"
            )
        return v

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_expiration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Token expiration values must be positive integers")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        return _parse_comma_separated_or_json_list(v)

    @field_validator("GOOGLE_OAUTH_CLIENT_ID")
    @classmethod
    def validate_google_oauth_client_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("GOOGLE_OAUTH_CLIENT_ID must not be empty")
        return v.strip()

    @field_validator("APPLE_OAUTH_CLIENT_IDS", mode="before")
    @classmethod
    def parse_apple_oauth_client_ids(cls, v: Any) -> list[str]:
        parsed = _parse_comma_separated_or_json_list(v)
        if not parsed:
            raise ValueError(
                "APPLE_OAUTH_CLIENT_IDS must contain at least one client ID"
            )
        return parsed


# Expose configuration as a singleton
try:
    settings = Settings()
except ValidationError as e:
    for error in e.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
    sys.exit(1)
