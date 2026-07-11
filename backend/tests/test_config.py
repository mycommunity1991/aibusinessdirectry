import pytest
from pydantic import ValidationError

from app.core.config import Environment, LogLevel, Settings


def test_settings_load_success():
    # settings singleton should have loaded testing config
    from app.core.config import settings

    assert settings.ENVIRONMENT == Environment.TESTING
    assert settings.LOG_LEVEL == LogLevel.WARNING
    assert (
        settings.DATABASE_URL
        == "postgresql+psycopg://postgres:postgres@localhost:5432/test_db"
    )
    assert settings.SECRET_KEY == "test_secret_key_that_is_long_enough"


def test_settings_database_url_normalization(monkeypatch):
    # Test normalization of postgresql://
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    s1 = Settings(_env_file=None)
    assert s1.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"

    # Test normalization of postgres://
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/db")
    s2 = Settings(_env_file=None)
    assert s2.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"

    # Test preservation of postgresql+psycopg://
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/db")
    s3 = Settings(_env_file=None)
    assert s3.DATABASE_URL == "postgresql+psycopg://user:pass@host:5432/db"


def test_settings_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # We pass _env_file=None to ignore the local .env files
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "DATABASE_URL" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_settings_invalid_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "DATABASE_URL" in str(exc_info.value)
    assert "DATABASE_URL must be a valid PostgreSQL connection string" in str(
        exc_info.value
    )


def test_settings_missing_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "SECRET_KEY" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_settings_secret_key_fallback(monkeypatch):
    # If SECRET_KEY is missing but JWT_SECRET_KEY is present, it should fall back
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "fallback_secret_key")
    s = Settings(_env_file=None)
    assert s.SECRET_KEY == "fallback_secret_key"


def test_settings_invalid_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "invalid_env")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "ENVIRONMENT" in str(exc_info.value)
    assert "Input should be 'development', 'testing' or 'production'" in str(
        exc_info.value
    )


def test_settings_invalid_log_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "LOG_LEVEL" in str(exc_info.value)


def test_settings_invalid_token_expiration(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "-10")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in str(exc_info.value)
    assert "Token expiration values must be positive integers" in str(exc_info.value)


def test_settings_cors_origins(monkeypatch):
    # Test comma separated
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com, http://b.com")
    s = Settings(_env_file=None)
    assert s.ALLOWED_ORIGINS == ["http://a.com", "http://b.com"]

    # Test json list
    monkeypatch.setenv("ALLOWED_ORIGINS", '["http://c.com", "http://d.com"]')
    s = Settings(_env_file=None)
    assert s.ALLOWED_ORIGINS == ["http://c.com", "http://d.com"]

    # Test empty
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    s = Settings(_env_file=None)
    assert s.ALLOWED_ORIGINS == []
