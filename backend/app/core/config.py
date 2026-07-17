import sys
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import API_PREFIX


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

    # Security Settings
    # Map to SECRET_KEY or fall back to JWT_SECRET_KEY for backward compatibility
    SECRET_KEY: str = Field(
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY")
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Logging Settings
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # CORS Settings
    ALLOWED_ORIGINS: list[str] | str = Field(default_factory=list)

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

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_expiration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Token expiration values must be positive integers")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "":
                return []
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    loaded = json.loads(v)
                    if isinstance(loaded, list):
                        return [
                            str(origin).strip()
                            for origin in loaded
                            if str(origin).strip()
                        ]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return []


# Expose configuration as a singleton
try:
    settings = Settings()
except ValidationError as e:
    for error in e.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
    sys.exit(1)
