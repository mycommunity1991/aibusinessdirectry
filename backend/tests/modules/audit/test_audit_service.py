"""
Integration tests for `AuditService`/`AuditLogRepository` (AUTH-004,
AC8/AC9), exercised against a real Postgres database (see
`tests/conftest.py`'s `db_session` fixture) since the immutability
guarantee (no update/delete path) and the exact column values written
per event type are best verified against the real thing.
"""

import uuid

from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.modules.audit.repositories.audit_log_repository import AuditLogRepository
from app.modules.audit.services.audit_service import AuditService
from app.modules.identity.models import AuthProvider, User


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


class TestAuditLogRepositoryImmutability:
    def test_repository_exposes_no_update_or_delete_method(self) -> None:
        """AC8: immutability is enforced by the class's shape, not just
        by convention -- no `update`/`delete` method is ever defined."""
        repo = AuditLogRepository(session=None)  # type: ignore[arg-type]
        assert not hasattr(repo, "update")
        assert not hasattr(repo, "delete")


class TestAuditLogRepositoryCreate:
    async def test_create_persists_a_row_with_the_given_fields(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "508000001")
        repo = AuditLogRepository(db_session)

        log = await repo.create(
            actor_user_id=user.id,
            action="login",
            entity_type="user",
            entity_id=user.id,
            after_state={"auth_provider": "mobile_otp"},
            ip_address="127.0.0.1",
        )
        await db_session.commit()

        assert log.id is not None
        assert log.actor_user_id == user.id
        assert log.action == "login"
        assert log.entity_type == "user"
        assert log.entity_id == user.id
        assert log.after_state == {"auth_provider": "mobile_otp"}
        assert log.before_state is None
        assert str(log.ip_address) == "127.0.0.1"
        assert log.created_at is not None

        result = await db_session.execute(select(AuditLog).where(AuditLog.id == log.id))
        assert result.scalar_one().action == "login"

    async def test_create_allows_a_null_actor_and_null_entity_id(
        self, db_session
    ) -> None:
        """`actor_user_id`/`entity_id` are both nullable -- e.g. a bulk
        "log out everywhere" event has no single entity."""
        repo = AuditLogRepository(db_session)

        log = await repo.create(
            actor_user_id=None,
            action="session_revocation",
            entity_type="session",
            entity_id=None,
            after_state={"scope": "all_sessions", "kept_current": False},
            ip_address=None,
        )
        await db_session.commit()

        assert log.actor_user_id is None
        assert log.entity_id is None


class TestAuditServiceEventMapping:
    """Each of `AuditService`'s four explicit methods writes the exact
    action/entity_type/after_state shape `Plan_S02_AUTH-004.md`
    Decision 5 specifies."""

    async def test_record_registration_writes_the_expected_row(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "508000010")
        service = AuditService(AuditLogRepository(db_session))

        log = await service.record_registration(
            user_id=user.id, auth_provider="mobile_otp", ip_address="127.0.0.1"
        )
        await db_session.commit()

        assert log.action == "registration"
        assert log.entity_type == "user"
        assert log.entity_id == user.id
        assert log.actor_user_id == user.id
        assert log.after_state == {"auth_provider": "mobile_otp"}
        # No PII/secrets: only the non-revealing auth_provider value.
        assert "phone_number" not in (log.after_state or {})
        assert "email" not in (log.after_state or {})

    async def test_record_login_writes_the_expected_row(self, db_session) -> None:
        user = await _make_user(db_session, "508000011")
        service = AuditService(AuditLogRepository(db_session))

        log = await service.record_login(
            user_id=user.id, auth_provider="google", ip_address=None
        )
        await db_session.commit()

        assert log.action == "login"
        assert log.entity_type == "user"
        assert log.entity_id == user.id
        assert log.after_state == {"auth_provider": "google"}

    async def test_record_logout_writes_the_expected_row(self, db_session) -> None:
        user = await _make_user(db_session, "508000012")
        session_id = uuid.uuid4()
        service = AuditService(AuditLogRepository(db_session))

        log = await service.record_logout(
            user_id=user.id, session_id=session_id, ip_address="127.0.0.1"
        )
        await db_session.commit()

        assert log.action == "logout"
        assert log.entity_type == "session"
        assert log.entity_id == session_id
        assert log.actor_user_id == user.id
        assert log.after_state is None

    async def test_record_session_revocation_writes_the_expected_row(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "508000013")
        session_id = uuid.uuid4()
        service = AuditService(AuditLogRepository(db_session))

        log = await service.record_session_revocation(
            user_id=user.id, session_id=session_id, ip_address="127.0.0.1"
        )
        await db_session.commit()

        assert log.action == "session_revocation"
        assert log.entity_type == "session"
        assert log.entity_id == session_id

    async def test_record_session_revocation_bulk_scope_writes_no_entity_id(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "508000014")
        service = AuditService(AuditLogRepository(db_session))

        log = await service.record_session_revocation(
            user_id=user.id,
            session_id=None,
            ip_address=None,
            after_state={"scope": "all_sessions", "kept_current": True},
        )
        await db_session.commit()

        assert log.action == "session_revocation"
        assert log.entity_id is None
        assert log.after_state == {"scope": "all_sessions", "kept_current": True}
