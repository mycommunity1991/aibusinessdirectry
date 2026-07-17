from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from alembic.config import Config

from alembic import command


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_alembic_config_loading() -> None:
    """Verify that Alembic configuration is loaded correctly from alembic.ini."""
    config = Config("alembic.ini")
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert "alembic" in script_location


def test_migration_upgrade_downgrade_mocked() -> None:
    """Verify that Alembic can run upgrade and downgrade using the async engine.

    Mocks the async connection and its run_sync helper to execute
    migrations without requiring a live PostgreSQL instance.
    """
    mock_conn = AsyncMock()
    mock_sync_conn = MagicMock()
    mock_sync_conn.dialect.name = "postgresql"

    # Mock run_sync to execute the migration function immediately
    async def mock_run_sync(fn, *args, **kwargs):
        return fn(mock_sync_conn, *args, **kwargs)

    mock_conn.run_sync.side_effect = mock_run_sync

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Patch the global engine imported inside app/core/database/database.py
    with patch("app.database.database.engine", mock_engine):
        config = Config("alembic.ini")

        # Test upgrade
        command.upgrade(config, "head")
        mock_engine.connect.assert_called_once()
        mock_conn.run_sync.assert_called_once()

        # Reset mocks for downgrade
        mock_engine.reset_mock()
        mock_conn.reset_mock()

        # Test downgrade
        command.downgrade(config, "base")
        mock_engine.connect.assert_called_once()
        mock_conn.run_sync.assert_called_once()
