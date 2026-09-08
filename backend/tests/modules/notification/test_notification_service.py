"""
Integration tests for `NotificationService`/`NotificationRepository`
(VER-002, AC5), exercised against a real Postgres database.

Asserts the persisted `title`/`body` match the exact plain-language
copy templates word for word, and never contain a raw
`VerificationStatus` enum token (e.g. `"VerificationStatus.APPROVED"`)
or the bare word "approved"/"rejected" used as an internal status
representation.
"""

import uuid

from sqlalchemy import select

from app.modules.identity.models import AuthProvider, User
from app.modules.notification.models import Notification
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_service import NotificationService


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


class TestNotifyVerificationStatusChange:
    async def test_approved_uses_the_exact_copy_template(self, db_session) -> None:
        user = await _make_user(db_session, "901000001")
        record_id = uuid.uuid4()
        service = NotificationService(NotificationRepository(db_session))

        notification = await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=record_id,
        )
        await db_session.commit()

        assert notification.user_id == user.id
        assert notification.type == "verification_status_change"
        assert notification.title == "Verification approved"
        assert notification.body == (
            "Great news — your verification has been approved. Your "
            "listing is now visible to customers."
        )
        assert notification.related_entity_type == "verification_record"
        assert notification.related_entity_id == record_id

        result = await db_session.execute(
            select(Notification).where(Notification.id == notification.id)
        )
        persisted = result.scalar_one()
        assert persisted.title == "Verification approved"

    async def test_rejected_uses_the_exact_copy_template_with_the_reason(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "901000002")
        record_id = uuid.uuid4()
        service = NotificationService(NotificationRepository(db_session))

        notification = await service.notify_verification_status_change(
            user_id=user.id,
            approved=False,
            rejection_reason="Illegible document.",
            verification_record_id=record_id,
        )

        assert notification.title == "Verification update"
        assert notification.body == (
            "We weren't able to verify your submission. Reason: "
            "Illegible document.. You can review the details and "
            "resubmit your documents."
        )

    async def test_neither_title_nor_body_ever_contains_a_raw_enum_token(
        self, db_session
    ) -> None:
        """AC5: "never exposing internal status enum values" -- neither
        the qualified `VerificationStatus.APPROVED`/`REJECTED` repr nor
        the bare enum member name ever leaks into user-facing copy."""
        user = await _make_user(db_session, "901000003")
        service = NotificationService(NotificationRepository(db_session))

        approved = await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=uuid.uuid4(),
        )
        rejected = await service.notify_verification_status_change(
            user_id=user.id,
            approved=False,
            rejection_reason="Blurry photo.",
            verification_record_id=uuid.uuid4(),
        )

        for notification in (approved, rejected):
            assert "VerificationStatus" not in notification.title
            assert "VerificationStatus" not in notification.body
            assert "PENDING" not in notification.title
            assert "PENDING" not in notification.body
            assert "UNDER_REVIEW" not in notification.title
            assert "UNDER_REVIEW" not in notification.body

        # The word "approved" legitimately appears in the approved
        # template's own plain-language sentence -- but never as a bare,
        # capitalized internal status token like "APPROVED"/"REJECTED".
        assert "APPROVED" not in approved.title
        assert "APPROVED" not in approved.body
        assert "REJECTED" not in rejected.title
        assert "REJECTED" not in rejected.body

    async def test_each_call_creates_exactly_one_row(self, db_session) -> None:
        user = await _make_user(db_session, "901000004")
        service = NotificationService(NotificationRepository(db_session))

        await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=uuid.uuid4(),
        )
        await db_session.commit()

        result = await db_session.execute(select(Notification))
        assert len(result.scalars().all()) == 1
