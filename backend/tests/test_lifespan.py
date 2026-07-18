import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import lifespan, validate_config
from app.main import app


def test_lifespan_registration() -> None:
    """Verify that the lifespan handler is correctly registered on the FastAPI app."""
    # The lifespan function is wrapped by _merge_lifespan_context in FastAPI
    # We inspect the closure cells of the lifespan_context to verify it
    # contains our lifespan function.
    assert app.router.lifespan_context is not None
    assert app.router.lifespan_context.__closure__ is not None
    inner = app.router.lifespan_context.__closure__[0].cell_contents
    assert inner.__closure__ is not None
    registered_lifespans = [c.cell_contents for c in inner.__closure__]
    assert lifespan in registered_lifespans


def test_lifespan_success(caplog: pytest.LogCaptureFixture) -> None:
    """Verify successful lifespan startup and shutdown cycle.

    Should log start and end events, and initialize app state placeholders.
    """
    caplog.set_level(logging.INFO)

    # Use a dummy app with our lifespan to isolate testing
    test_app = FastAPI(lifespan=lifespan)

    # Mock engine.dispose and the Redis client to avoid actual connection
    # side effects
    with (
        patch("app.core.lifespan.engine") as mock_engine,
        patch("app.core.lifespan.redis_client") as mock_redis_client,
        patch("app.core.lifespan.setup_logging"),
    ):
        mock_engine.dispose = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.aclose = AsyncMock()

        with TestClient(test_app):
            # Assert state container is initialized
            assert test_app.state.services is not None
            assert test_app.state.services.db_engine == mock_engine
            assert test_app.state.services.redis_client == mock_redis_client
            assert test_app.state.services.background_workers is None

            # Assert startup logs are present
            log_messages = [record.message for record in caplog.records]
            assert "Application starting" in log_messages
            assert "Validating application configuration" in log_messages
            assert "Redis connection verified" in log_messages
            assert "Startup completed" in log_messages

        # Assert shutdown was triggered and logs are present
        log_messages = [record.message for record in caplog.records]
        assert "Shutdown initiated" in log_messages
        assert "Disposing database engine connection pool" in log_messages
        assert "Database engine connection pool disposed successfully" in log_messages
        assert "Closing Redis client connection" in log_messages
        assert "Redis client connection closed successfully" in log_messages
        assert "Shutdown completed" in log_messages
        mock_engine.dispose.assert_awaited_once()
        mock_redis_client.aclose.assert_awaited_once()


def test_lifespan_startup_failure(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that application startup fails cleanly if validation fails.

    It should log the failure and stop startup by propagating the error,
    without executing shutdown cleanup.
    """
    caplog.set_level(logging.INFO)
    test_app = FastAPI(lifespan=lifespan)

    # Mock validate_config to raise ValueError
    err = ValueError("Invalid DB URL")
    with (
        patch("app.core.lifespan.validate_config", side_effect=err),
        patch("app.core.lifespan.engine") as mock_engine,
        patch("app.core.lifespan.setup_logging"),
    ):
        mock_engine.dispose = AsyncMock()

        # TestClient should propagate the startup exception
        with pytest.raises(ValueError, match="Invalid DB URL"):
            with TestClient(test_app):
                pass

        # Verify startup failure logging
        log_messages = [record.message for record in caplog.records]
        assert "Application starting" in log_messages
        assert any("Application startup failed" in log for log in log_messages)

        # Verify shutdown cleanup did NOT execute
        assert "Shutdown initiated" not in log_messages
        mock_engine.dispose.assert_not_called()


def test_lifespan_cleanup_failure(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that shutdown continues and logs errors even if cleanup actions fail.

    It should log the cleanup error but still complete the shutdown sequence.
    """
    caplog.set_level(logging.INFO)
    test_app = FastAPI(lifespan=lifespan)

    # Mock engine.dispose and the Redis client's close to raise errors
    with (
        patch("app.core.lifespan.engine") as mock_engine,
        patch("app.core.lifespan.redis_client") as mock_redis_client,
        patch("app.core.lifespan.setup_logging"),
    ):
        mock_engine.dispose = AsyncMock(side_effect=Exception("Connection pool error"))
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.aclose = AsyncMock(side_effect=Exception("Redis close error"))

        with TestClient(test_app):
            pass

        # Verify that shutdown initiated, cleanup failed, but shutdown completed
        log_messages = [record.message for record in caplog.records]
        assert "Shutdown initiated" in log_messages
        assert "Disposing database engine connection pool" in log_messages
        assert any("Failed to dispose database engine" in log for log in log_messages)
        assert any("Failed to close Redis client" in log for log in log_messages)
        assert "Shutdown completed" in log_messages
        mock_engine.dispose.assert_awaited_once()
        mock_redis_client.aclose.assert_awaited_once()


def test_validate_config_success() -> None:
    """Verify validate_config completes successfully with correct settings."""
    with (
        patch(
            "app.core.lifespan.settings.DATABASE_URL",
            "postgresql+psycopg://localhost:5432/db",
        ),
        patch("app.core.lifespan.settings.SECRET_KEY", "supersecretkey"),
        patch("app.core.lifespan.settings.REDIS_URL", "redis://localhost:6379/0"),
        patch("app.core.lifespan.settings.ENVIRONMENT", "testing"),
    ):
        # Should not raise any exception
        validate_config()


@pytest.mark.parametrize(
    "db_url,secret_key,redis_url,env,expected_error",
    [
        (
            "",
            "key",
            "redis://localhost:6379/0",
            "testing",
            "DATABASE_URL must be configured",
        ),
        (
            "postgresql://db",
            "",
            "redis://localhost:6379/0",
            "testing",
            "SECRET_KEY must be configured",
        ),
        (
            "postgresql://db",
            "key",
            "",
            "testing",
            "REDIS_URL must be configured",
        ),
        (
            "postgresql://db",
            "key",
            "redis://localhost:6379/0",
            "invalid_env",
            "Invalid environment: invalid_env",
        ),
    ],
)
def test_validate_config_failures(
    db_url: str, secret_key: str, redis_url: str, env: str, expected_error: str
) -> None:
    """Verify validate_config raises ValueError with descriptive messages."""
    with (
        patch("app.core.lifespan.settings.DATABASE_URL", db_url),
        patch("app.core.lifespan.settings.SECRET_KEY", secret_key),
        patch("app.core.lifespan.settings.REDIS_URL", redis_url),
        patch("app.core.lifespan.settings.ENVIRONMENT", env),
    ):
        with pytest.raises(ValueError, match=expected_error):
            validate_config()
