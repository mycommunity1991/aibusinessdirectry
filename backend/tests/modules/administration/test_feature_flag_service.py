"""
Integration tests for `FeatureFlagService`/`FeatureFlagRepository`
(ADM-002, Decision 1/3/7/8, `Plan_S11_ADM-002.md`), exercised against a
real Postgres database (see `tests/conftest.py`'s `db_session` fixture).

This test's DB schema is created directly from the SQLAlchemy models
(`tests/conftest.py`'s `db_engine` fixture), not by running the real
Alembic migration -- so the migration's own seed row does not exist
here; each test seeds its own `feature_flags` row directly through the
repository, mirroring every other administration test file's "build the
real thing, no mocks" convention.
"""

import uuid

from sqlalchemy import select

from app.core.exceptions import FeatureFlagNotFoundError
from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.repositories.feature_flag_repository import (
    FeatureFlagRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.administration.services.feature_flag_service import FeatureFlagService
from app.modules.identity.models import AuthProvider, User

_FLAG_KEY = "manual_matching_force_all"


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _service(db_session) -> FeatureFlagService:
    return FeatureFlagService(
        FeatureFlagRepository(db_session),
        AdminActionLogService(AdminActionLogRepository(db_session)),
    )


async def _seed_flag(
    db_session, *, key: str = _FLAG_KEY, is_enabled: bool = False
) -> None:
    """Mirrors Decision 1's literal migration-seed row -- built directly
    through the repository here, since this test's schema is created
    from models, not the real migration."""
    await FeatureFlagRepository(db_session).create(
        {"key": key, "is_enabled": is_enabled, "description": None}
    )
    await db_session.commit()


class TestIsEnabled:
    async def test_returns_the_seeded_default_false(self, db_session) -> None:
        await _seed_flag(db_session, is_enabled=False)
        service = _service(db_session)

        result = await service.is_enabled(_FLAG_KEY)

        assert result is False

    async def test_returns_true_once_enabled(self, db_session) -> None:
        await _seed_flag(db_session, is_enabled=True)
        service = _service(db_session)

        result = await service.is_enabled(_FLAG_KEY)

        assert result is True

    async def test_returns_false_for_a_nonexistent_key_never_raises(
        self, db_session
    ) -> None:
        """Decision 7/8's anti-fabrication default -- absence means
        disabled, never assumed enabled."""
        service = _service(db_session)

        result = await service.is_enabled("some_key_that_does_not_exist")

        assert result is False


class TestListAll:
    async def test_lists_every_row_ordered_by_key(self, db_session) -> None:
        await _seed_flag(db_session, key="b_flag", is_enabled=False)
        await _seed_flag(db_session, key="a_flag", is_enabled=True)
        service = _service(db_session)

        flags = await service.list_all()

        assert [flag.key for flag in flags] == ["a_flag", "b_flag"]


class TestToggle:
    async def test_toggle_flips_is_enabled_and_persists_it(self, db_session) -> None:
        admin = await _make_user(db_session, "960000001")
        await _seed_flag(db_session, is_enabled=False)
        service = _service(db_session)

        updated = await service.toggle(
            _FLAG_KEY, is_enabled=True, admin_user_id=admin.id
        )
        await db_session.commit()

        assert updated.is_enabled is True
        assert await service.is_enabled(_FLAG_KEY) is True

    async def test_toggle_writes_exactly_one_admin_action_log_row(
        self, db_session
    ) -> None:
        admin = await _make_user(db_session, "960000002")
        await _seed_flag(db_session, is_enabled=False)
        service = _service(db_session)

        updated = await service.toggle(
            _FLAG_KEY, is_enabled=True, admin_user_id=admin.id
        )
        await db_session.commit()

        result = await db_session.execute(select(AdminActionLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].admin_user_id == admin.id
        assert logs[0].action_type == "feature_flag_toggled"
        assert logs[0].target_entity_type == "feature_flag"
        assert logs[0].target_entity_id == updated.id
        assert logs[0].metadata_ == {"key": _FLAG_KEY, "is_enabled": True}

    async def test_toggle_on_an_unknown_key_raises_not_found(
        self, db_session
    ) -> None:
        service = _service(db_session)

        try:
            await service.toggle(
                "unknown_key", is_enabled=True, admin_user_id=uuid.uuid4()
            )
            raise AssertionError("expected FeatureFlagNotFoundError")
        except FeatureFlagNotFoundError:
            pass
