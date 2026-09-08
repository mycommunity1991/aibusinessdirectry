import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from redis.asyncio import Redis
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Set default environment variables for testing before any imports occur
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/test_db"
os.environ["SECRET_KEY"] = "test_secret_key_that_is_long_enough"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
# Placeholder, unconnected by default (mirrors DATABASE_URL above) — only
# tests that exercise Redis-backed behavior (rate limiting) override this
# via the `redis_client` fixture below, pointed at a dedicated test DB
# index so it never collides with local dev data on db 0.
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
# AUTH-002: OAuth audience placeholders. Test ID tokens are minted (see
# `tests/support/id_token_factory.py`) with an `aud` claim matching these
# exact values, so the real verification code path can be exercised
# end-to-end without any real Google/Apple credentials.
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test-google-client-id"
os.environ["APPLE_OAUTH_CLIENT_IDS"] = (
    "test-apple-client-id-ios,test-apple-client-id-android"
)

# ---------------------------------------------------------------------------
# Real-database fixtures for identity-domain integration tests.
#
# The rest of the Sprint 1 suite mocks `AsyncSession` entirely (see
# `settings.DATABASE_URL` above, which is a placeholder never actually
# connected to). Identity-domain tests that need to exercise real
# constraints (partial unique indexes, CHECK constraints, native enums)
# connect to a real local Postgres test database instead.
#
# No secret is hardcoded: the default connects as the local superuser role
# over trust-authenticated TCP (this project's local Postgres requires no
# password for it), matching how `DATABASE_URL` above already hardcodes a
# non-secret local placeholder. Override with `TEST_DATABASE_URL` in any
# environment where that default isn't valid.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://dumbo@localhost:5432/ai_marketplace_test",
)


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine]:
    """
    Function-scoped engine bound to a real local Postgres test database,
    with the identity schema/tables created for the duration of the test
    and torn down afterward.

    Function-scoped (rather than session-scoped) because this project's
    `asyncio_default_fixture_loop_scope` is `function` — a broader-scoped
    async fixture would conflict with pytest-asyncio's per-test event loop.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    import app.modules.administration.models  # noqa: F401 - registers admin_action_log
    import app.modules.audit.models  # noqa: F401 - registers the audit_logs table
    import app.modules.customer.models  # noqa: F401 - registers customer tables
    import app.modules.identity.models  # noqa: F401 - registers identity tables
    import app.modules.notification.models  # noqa: F401 - registers notification tables
    import app.modules.provider.models  # noqa: F401 - registers provider tables
    import app.modules.verification.models  # noqa: F401 - registers verification tables
    from app.database.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, future=True)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS customer"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS provider"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS verification"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS administration"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS notification"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP SCHEMA IF EXISTS identity CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS audit CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS customer CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS provider CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS verification CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS administration CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS notification CASCADE"))
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """
    Function-scoped real `AsyncSession`. All identity tables are truncated
    after every test so tests remain isolated from one another regardless
    of whether the test (or the code under test) committed.
    """
    from app.modules.administration.models import AdminActionLog
    from app.modules.audit.models import AuditLog
    from app.modules.customer.models import (
        CustomerPreferences,
        CustomerProfile,
        SavedAddress,
    )
    from app.modules.identity.models import (
        Device,
        OtpVerification,
        Permission,
        RefreshToken,
        Role,
        RolePermission,
        Session,
        User,
        UserRole,
    )
    from app.modules.notification.models import Notification
    from app.modules.provider.models import (
        BusinessProfile,
        FreelancerProfile,
        Portfolio,
        Provider,
        ProviderAvailability,
        ProviderCategoryLabel,
        ServiceArea,
    )
    from app.modules.verification.models import (
        VerificationDocument,
        VerificationRecord,
    )

    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with db_engine.begin() as conn:
        for model in (
            AuditLog,
            AdminActionLog,
            Notification,
            SavedAddress,
            CustomerPreferences,
            CustomerProfile,
            VerificationDocument,
            VerificationRecord,
            Portfolio,
            ProviderAvailability,
            ServiceArea,
            ProviderCategoryLabel,
            BusinessProfile,
            FreelancerProfile,
            Provider,
            RefreshToken,
            Session,
            OtpVerification,
            Device,
            RolePermission,
            UserRole,
            Permission,
            Role,
            User,
        ):
            await conn.execute(delete(model))


# ---------------------------------------------------------------------------
# Real-Redis fixture for rate-limiting tests (FU-5).
#
# Matches the real-Postgres philosophy above: connects to the same local
# Redis instance used for development, but on a dedicated test DB index
# (15) so it never collides with dev data living on the default db 0.
# Flushed (only that index) before and after every test for isolation.
# ---------------------------------------------------------------------------
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis]:
    """
    Function-scoped Redis client bound to a dedicated test DB index (15).

    Deliberately not connected (no command issued) by this fixture's own
    setup/teardown code: `fastapi.testclient.TestClient` drives the ASGI
    app — and therefore anything depending on this client via a dependency
    override — from its own background event loop, distinct from
    pytest-asyncio's per-test loop this fixture body runs on. redis-py's
    asyncio connections bind to whichever event loop first uses them, so
    issuing a command here would bind `client` to the wrong loop and every
    request in the test would fail with `RuntimeError: ... Future
    attached to a different loop`. A separate, short-lived client is used
    purely for flush bookkeeping so it never shares a connection (or a
    loop) with `client`.
    """

    async def _flush() -> None:
        flush_client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
        await flush_client.flushdb()
        await flush_client.aclose()

    client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await _flush()
    yield client
    await _flush()
