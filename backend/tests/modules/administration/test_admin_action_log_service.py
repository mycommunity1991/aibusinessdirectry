"""
Integration tests for `AdminActionLogService`/`AdminActionLogRepository`
(VER-002, AC6), exercised against a real Postgres database (see
`tests/conftest.py`'s `db_session` fixture).
"""

import uuid

from sqlalchemy import select

from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
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


class TestRecordVerificationReview:
    async def test_approval_persists_the_expected_columns(self, db_session) -> None:
        admin_user = await _make_user(db_session, "801000001")
        record_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        service = AdminActionLogService(AdminActionLogRepository(db_session))

        log = await service.record_verification_review(
            admin_user_id=admin_user.id,
            verification_record_id=record_id,
            provider_id=provider_id,
            decision="approved",
            rejection_reason=None,
        )
        await db_session.commit()

        assert log.id is not None
        assert log.admin_user_id == admin_user.id
        assert log.action_type == "verification_approved"
        assert log.target_entity_type == "verification_record"
        assert log.target_entity_id == record_id
        assert log.metadata_ == {"provider_id": str(provider_id)}

        result = await db_session.execute(
            select(AdminActionLog).where(AdminActionLog.id == log.id)
        )
        persisted = result.scalar_one()
        assert persisted.action_type == "verification_approved"

    async def test_rejection_carries_the_reason_in_metadata(self, db_session) -> None:
        admin_user = await _make_user(db_session, "801000002")
        record_id = uuid.uuid4()
        provider_id = uuid.uuid4()
        service = AdminActionLogService(AdminActionLogRepository(db_session))

        log = await service.record_verification_review(
            admin_user_id=admin_user.id,
            verification_record_id=record_id,
            provider_id=provider_id,
            decision="rejected",
            rejection_reason="Illegible document.",
        )

        assert log.action_type == "verification_rejected"
        assert log.metadata_ == {
            "provider_id": str(provider_id),
            "rejection_reason": "Illegible document.",
        }

    async def test_each_call_creates_exactly_one_row(self, db_session) -> None:
        admin_user = await _make_user(db_session, "801000003")
        service = AdminActionLogService(AdminActionLogRepository(db_session))

        await service.record_verification_review(
            admin_user_id=admin_user.id,
            verification_record_id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            decision="approved",
            rejection_reason=None,
        )
        await db_session.commit()

        result = await db_session.execute(select(AdminActionLog))
        assert len(result.scalars().all()) == 1
