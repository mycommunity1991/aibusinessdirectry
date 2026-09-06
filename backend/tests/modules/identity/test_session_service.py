"""
Integration tests for `SessionService` (AUTH-003), exercised against a
real Postgres database (see `tests/conftest.py`'s `db_session` fixture)
since its repositories issue real UPDATE/SELECT statements whose
semantics (bulk revocation, rotation chains, ownership filtering) are
best verified against the real thing rather than mocked.

Covers AC4 (rotation), AC5 (reused/revoked/expired rejection), AC6
(device capture -- exercised indirectly via `start_session`), AC7
(`list_active_sessions`' `is_current` flag), AC8 (revoke-then-refresh-
fails), AC9 (`revoke_all_sessions`, with and without `keep_current`),
AC10 (ownership boundary), and AC11 (the explicit rotation /
revocation-then-refresh-fails / ownership-boundary trio).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import InvalidRefreshTokenError, SessionNotFoundError
from app.core.security import hash_refresh_token
from app.modules.audit.models import AuditLog
from app.modules.audit.repositories.audit_log_repository import AuditLogRepository
from app.modules.audit.services.audit_service import AuditService
from app.modules.identity.models import (
    AuthProvider,
    DevicePlatform,
    RefreshToken,
    Role,
    User,
    UserRole,
)
from app.modules.identity.repositories.device_repository import DeviceRepository
from app.modules.identity.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.session_repository import SessionRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.session_service import SessionService


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


async def _assign_role(db_session, user: User, role_name: str) -> None:
    """
    Persists a real `Role`/`UserRole` assignment for `user`, so
    `RoleRepository.get_role_names_for_user` (which `SessionService`
    queries fresh at every refresh) actually returns something.
    """
    role = Role(name=role_name)
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.commit()


@pytest.fixture
def session_service(db_session) -> SessionService:
    return SessionService(
        device_repository=DeviceRepository(db_session),
        session_repository=SessionRepository(db_session),
        refresh_token_repository=RefreshTokenRepository(db_session),
        user_repository=UserRepository(db_session),
        role_repository=RoleRepository(db_session),
        audit_service=AuditService(AuditLogRepository(db_session)),
    )


async def _last_audit_log(db_session) -> AuditLog:
    """Fetches the most recently created `audit.audit_logs` row -- used
    to assert the correct `action`/`entity_type`/`entity_id`/`after_state`
    was recorded for the event under test (AUTH-004, AC8/AC9)."""
    result = await db_session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
    )
    log: AuditLog = result.scalars().one()
    return log


class TestStartSession:
    async def test_start_session_creates_device_session_and_refresh_token(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000001")

        (
            session_row,
            access_token,
            raw_refresh_token,
        ) = await session_service.start_session(
            user=user,
            roles=["customer"],
            device_platform=DevicePlatform.IOS,
            device_name="iPhone 15",
            ip_address="127.0.0.1",
            user_agent="pytest-agent",
        )
        await db_session.commit()

        assert session_row.id is not None
        assert session_row.user_id == user.id
        assert session_row.device_id is not None
        assert isinstance(access_token, str)
        assert isinstance(raw_refresh_token, str)

        from app.core.security import decode_token

        payload = decode_token(access_token)
        assert payload["jti"] == str(session_row.id)
        assert payload["roles"] == ["customer"]

    async def test_start_session_never_persists_the_raw_refresh_token(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000002")

        (
            _session,
            _access_token,
            raw_refresh_token,
        ) = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        from sqlalchemy import select

        result = await db_session.execute(select(RefreshToken))
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].token_hash != raw_refresh_token
        assert rows[0].token_hash == hash_refresh_token(raw_refresh_token)

    async def test_start_session_reuses_device_row_on_repeat_login(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC6: repeated logins from the same device info update rather
        than duplicate the `Device` row."""
        user = await _make_user(db_session, "505000003")

        first_session, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="Same Device",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        second_session, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="Same Device",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        assert first_session.device_id == second_session.device_id


class TestRefreshRotation:
    async def test_refresh_rotates_and_invalidates_the_old_token(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC4: a valid refresh issues a new pair and invalidates the
        previous refresh token."""
        user = await _make_user(db_session, "505000010")
        await _assign_role(db_session, user, "customer")
        (
            _session,
            _access_token,
            raw_refresh_token,
        ) = await session_service.start_session(
            user=user,
            roles=["customer"],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        (
            new_user,
            roles,
            new_access_token,
            new_raw_refresh_token,
        ) = await session_service.refresh(raw_refresh_token)
        await db_session.commit()

        assert new_user.id == user.id
        assert roles == ["customer"]
        assert new_raw_refresh_token != raw_refresh_token
        assert isinstance(new_access_token, str)

        # The newly issued token works (checked *before* the replay
        # attempt below, since replaying an already-rotated token is a
        # reuse-detection signal that cascades to revoke the *entire*
        # session, including this still-legitimate token -- see
        # `test_reusing_an_already_rotated_token_cascades_to_full_session_revocation`
        # for that specific, deliberate behavior).
        _u, _r, _a, _newer_token = await session_service.refresh(new_raw_refresh_token)
        await db_session.commit()

        # The old (already-rotated-once) token is unusable (AC11: rotation).
        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_refresh_token)
        await db_session.commit()

    async def test_reusing_an_already_rotated_token_cascades_to_full_session_revocation(
        self, db_session, session_service: SessionService
    ) -> None:
        """Decision 7 / AC5: replaying a rotated-away token doesn't just
        fail that one call -- it revokes the entire session, so even the
        legitimately-rotated newest token stops working too."""
        user = await _make_user(db_session, "505000011")
        (
            _session,
            _access_token,
            raw_refresh_token,
        ) = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        _u, _r, _a, new_raw_refresh_token = await session_service.refresh(
            raw_refresh_token
        )
        await db_session.commit()

        # Replay the old (already-rotated) token.
        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_refresh_token)
        await db_session.commit()

        # The cascade must have revoked the whole session -- the newer,
        # otherwise-still-valid token is now also rejected.
        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(new_raw_refresh_token)
        await db_session.commit()

    async def test_refresh_with_an_expired_token_is_rejected(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000012")
        session_row, _access_token, _raw = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        expired_raw = "expired-raw-refresh-token"
        db_session.add(
            RefreshToken(
                user_id=user.id,
                session_id=session_row.id,
                token_hash=hash_refresh_token(expired_raw),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        await db_session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(expired_raw)

    async def test_refresh_with_an_unknown_token_is_rejected(
        self, session_service: SessionService
    ) -> None:
        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh("this-token-was-never-issued")


class TestListActiveSessions:
    async def test_lists_active_sessions_and_flags_the_current_one(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC7."""
        user = await _make_user(db_session, "505000020")
        session_a, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="Phone A",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()
        session_b, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name="Phone B",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        items = await session_service.list_active_sessions(user.id, session_b.id)

        assert len(items) == 2
        by_id = {item.id: item for item in items}
        assert by_id[session_a.id].is_current is False
        assert by_id[session_a.id].device_name == "Phone A"
        assert by_id[session_a.id].platform == "ios"
        assert by_id[session_b.id].is_current is True
        assert by_id[session_b.id].device_name == "Phone B"
        assert by_id[session_b.id].platform == "android"

    async def test_revoked_sessions_are_excluded(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000021")
        session_a, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_session(user.id, session_a.id)
        await db_session.commit()

        items = await session_service.list_active_sessions(user.id, None)
        assert items == []


class TestRevokeSession:
    async def test_revoke_session_then_refresh_fails(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC8 / AC11: revoking a session then attempting a refresh with
        that session's token fails."""
        user = await _make_user(db_session, "505000030")
        (
            session_row,
            _access_token,
            raw_refresh_token,
        ) = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_session(user.id, session_row.id)
        await db_session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_refresh_token)

    async def test_revoke_session_owned_by_a_different_user_raises_not_found(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC10 / AC11: a user cannot revoke another user's session --
        the failure is indistinguishable from "doesn't exist"."""
        owner = await _make_user(db_session, "505000031")
        attacker = await _make_user(db_session, "505000032")
        session_row, _, _ = await session_service.start_session(
            user=owner,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        with pytest.raises(SessionNotFoundError):
            await session_service.revoke_session(attacker.id, session_row.id)

    async def test_revoke_session_that_does_not_exist_raises_not_found(
        self, db_session, session_service: SessionService
    ) -> None:
        import uuid

        user = await _make_user(db_session, "505000033")

        with pytest.raises(SessionNotFoundError):
            await session_service.revoke_session(user.id, uuid.uuid4())


class TestRevokeSessionAuditLogging:
    """
    AUTH-004, AC8/AC9: `revoke_session` records a `logout` audit row when
    the revoked session IS the caller's own current session, or a
    `session_revocation` row when it's a *different* session --
    `Plan_S02_AUTH-004.md` Decision 5.
    """

    async def test_revoking_own_current_session_records_a_logout_event(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000060")
        session_row, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_session(
            user.id,
            session_row.id,
            current_session_id=session_row.id,
            ip_address="127.0.0.1",
        )
        await db_session.commit()

        log = await _last_audit_log(db_session)
        assert log.action == "logout"
        assert log.entity_type == "session"
        assert log.entity_id == session_row.id
        assert log.actor_user_id == user.id
        assert str(log.ip_address) == "127.0.0.1"
        # No secrets/PII in before/after state.
        assert log.before_state is None
        assert log.after_state is None

    async def test_revoking_a_different_session_records_a_session_revocation_event(
        self, db_session, session_service: SessionService
    ) -> None:
        user = await _make_user(db_session, "505000061")
        current_session, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="Current Device",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()
        other_session, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name="Other Device",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_session(
            user.id,
            other_session.id,
            current_session_id=current_session.id,
            ip_address="127.0.0.1",
        )
        await db_session.commit()

        log = await _last_audit_log(db_session)
        assert log.action == "session_revocation"
        assert log.entity_type == "session"
        assert log.entity_id == other_session.id
        assert log.actor_user_id == user.id

    async def test_revoke_all_sessions_records_a_session_revocation_event(
        self, db_session, session_service: SessionService
    ) -> None:
        """`revoke_all_sessions` always records `session_revocation`,
        never `logout`, even with `keep_current=True` -- a distinct bulk
        action, `entity_id=None`."""
        user = await _make_user(db_session, "505000062")
        session_row, _, _ = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_all_sessions(
            user.id,
            current_session_id=session_row.id,
            keep_current=True,
            ip_address="10.0.0.1",
        )
        await db_session.commit()

        log = await _last_audit_log(db_session)
        assert log.action == "session_revocation"
        assert log.entity_type == "session"
        assert log.entity_id is None
        assert log.after_state == {"scope": "all_sessions", "kept_current": True}
        assert str(log.ip_address) == "10.0.0.1"


class TestRevokeAllSessions:
    async def test_logout_everywhere_revokes_every_session(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC9 (no keep_current)."""
        user = await _make_user(db_session, "505000040")
        session_a, _, raw_a = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="A",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()
        session_b, _, raw_b = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name="B",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_all_sessions(
            user.id, current_session_id=session_b.id, keep_current=False
        )
        await db_session.commit()

        items = await session_service.list_active_sessions(user.id, None)
        assert items == []

        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_a)
        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_b)

    async def test_logout_everywhere_can_keep_the_current_session(
        self, db_session, session_service: SessionService
    ) -> None:
        """AC9 (keep_current=True) -- a distinct outcome from a plain
        single-session `DELETE`."""
        user = await _make_user(db_session, "505000041")
        session_a, _, raw_a = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name="A",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()
        session_b, _, raw_b = await session_service.start_session(
            user=user,
            roles=[],
            device_platform=DevicePlatform.ANDROID,
            device_name="B",
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        await session_service.revoke_all_sessions(
            user.id, current_session_id=session_b.id, keep_current=True
        )
        await db_session.commit()

        items = await session_service.list_active_sessions(user.id, session_b.id)
        assert len(items) == 1
        assert items[0].id == session_b.id

        with pytest.raises(InvalidRefreshTokenError):
            await session_service.refresh(raw_a)

        # session_b's own refresh token is untouched.
        _u, _r, _a, _newer = await session_service.refresh(raw_b)
        await db_session.commit()


class TestOwnershipBoundary:
    """AC10 / AC11: a user cannot list or revoke another user's
    sessions."""

    async def test_list_active_sessions_never_returns_another_users_session(
        self, db_session, session_service: SessionService
    ) -> None:
        user_a = await _make_user(db_session, "505000050")
        user_b = await _make_user(db_session, "505000051")
        session_a, _, _ = await session_service.start_session(
            user=user_a,
            roles=[],
            device_platform=DevicePlatform.IOS,
            device_name=None,
            ip_address=None,
            user_agent=None,
        )
        await db_session.commit()

        items_for_b = await session_service.list_active_sessions(user_b.id, None)
        assert items_for_b == []

        items_for_a = await session_service.list_active_sessions(user_a.id, None)
        assert [item.id for item in items_for_a] == [session_a.id]
