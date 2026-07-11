from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database.base import Base
from app.core.database.database import check_database_connection, engine
from app.core.database.session import async_session, get_db


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_base_class() -> None:
    """Verify that the DeclarativeBase class is configured and metadata is present."""
    assert issubclass(Base, object)
    assert hasattr(Base, "metadata")


def test_engine_properties() -> None:
    """Verify engine configuration, driver, and settings mapping."""
    assert isinstance(engine, AsyncEngine)
    assert engine.pool.size() == settings.DB_POOL_SIZE  # type: ignore[attr-defined]
    assert engine.url.drivername == "postgresql+psycopg"


def test_sessionmaker_properties() -> None:
    """Verify async_sessionmaker defaults and bind configuration."""
    assert isinstance(async_session, async_sessionmaker)
    assert async_session.kw["expire_on_commit"] is False
    assert async_session.kw["autoflush"] is False
    assert async_session.kw["autocommit"] is False
    assert async_session.class_ is AsyncSession


@pytest.mark.anyio
async def test_get_db_lifecycle() -> None:
    """Verify that get_db dependency yields the session and closes it on completion."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session

    with patch(
        "app.core.database.session.async_session", return_value=mock_session
    ) as mock_factory:
        sessions = []
        async for session in get_db():
            sessions.append(session)

        # Assert session was yielded
        assert len(sessions) == 1
        assert sessions[0] is mock_session
        mock_factory.assert_called_once()

    # Assert that the context manager __aexit__ was called (meaning the session closed)
    mock_session.__aexit__.assert_called_once()


@pytest.mark.anyio
async def test_check_database_connection_success() -> None:
    """Verify check_database_connection returns True on successful SELECT 1."""
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = MagicMock()

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    with patch("app.core.database.database.engine", mock_engine):
        result = await check_database_connection()
        assert result is True
        mock_engine.connect.assert_called_once()
        mock_conn.execute.assert_called_once()


@pytest.mark.anyio
async def test_check_database_connection_failure() -> None:
    """Verify check_database_connection returns False and handles failures.

    It should catch the exception, log the issue, and return False.
    """
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")

    with patch("app.core.database.database.engine", mock_engine):
        result = await check_database_connection()
        assert result is False
