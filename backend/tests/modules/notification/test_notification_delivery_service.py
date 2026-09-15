"""
Integration tests for `NotificationDeliveryService` (`ENG-001`, AC2/
AC7/AC8, Decision 7/8, `Plan_S12_ENG-001.md`), exercised against a real
Postgres database.

Uses a fake, deliberately-failing `NotificationSender` to prove AC2's
typed-error requirement is genuinely caught and recorded, never
silently swallowed or propagated to the caller -- mirrors how `AUTH-001`'s
own OTP tests verify `SmsSender` failure handling via a fake, never by
forcing the real stub to fail.
"""

import uuid

import pytest
from sqlalchemy import select

from app.modules.customer.models import NotificationChannel
from app.modules.identity.models import AuthProvider, User
from app.modules.notification.models import Notification, NotificationDelivery
from app.modules.notification.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.modules.notification.services.notification_sender import (
    NotificationDeliveryError,
    NotificationSender,
    StubEmailSender,
    StubSmsSender,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _AlwaysFailingSender(NotificationSender):
    """A fake, deliberately-failing `NotificationSender` -- proves AC2's
    typed-error requirement is genuinely caught and recorded, never a
    silent no-op."""

    def __init__(self) -> None:
        self.call_count = 0

    async def send(self, *, recipient_user_id, title, body) -> str | None:
        self.call_count += 1
        raise NotificationDeliveryError("Simulated provider outage.")


class _SpySender(NotificationSender):
    """Records every call, always succeeds -- proves the sender is
    called at most once for an idempotent retry (AC7/AC8)."""

    def __init__(self) -> None:
        self.call_count = 0

    async def send(self, *, recipient_user_id, title, body) -> str | None:
        self.call_count += 1
        return "provider-message-id-1"


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


async def _make_notification(db_session, user_id: uuid.UUID) -> Notification:
    notification = await NotificationRepository(db_session).create(
        {
            "user_id": user_id,
            "type": "new_contact_view",
            "title": "You have a new lead",
            "body": "A customer just viewed your contact details.",
            "related_entity_type": "contact_view",
            "related_entity_id": uuid.uuid4(),
        }
    )
    await db_session.commit()
    return notification


def _service(db_session, sender: NotificationSender) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        NotificationDeliveryRepository(db_session),
        {
            NotificationChannel.WHATSAPP: sender,
            NotificationChannel.SMS: StubSmsSender(),
            NotificationChannel.EMAIL: StubEmailSender(),
        },
    )


class TestSendFailureIsCaughtAndRecorded:
    @pytest.mark.anyio
    async def test_a_failed_send_is_recorded_never_raised(self, db_session) -> None:
        user = await _make_user(db_session, "930000001")
        notification = await _make_notification(db_session, user.id)
        sender = _AlwaysFailingSender()
        service = _service(db_session, sender)

        delivery = await service.send(
            notification, channel=NotificationChannel.WHATSAPP
        )
        await db_session.commit()

        assert delivery.status == "failed"
        assert delivery.failure_reason is not None
        assert "Simulated provider outage" in delivery.failure_reason
        assert sender.call_count == 1

        result = await db_session.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification.id
            )
        )
        persisted = result.scalar_one()
        assert persisted.status == "failed"


class TestSendSuccessIsRecorded:
    @pytest.mark.anyio
    async def test_a_successful_send_is_recorded_sent(self, db_session) -> None:
        user = await _make_user(db_session, "930000002")
        notification = await _make_notification(db_session, user.id)
        sender = _SpySender()
        service = _service(db_session, sender)

        delivery = await service.send(
            notification, channel=NotificationChannel.WHATSAPP
        )
        await db_session.commit()

        assert delivery.status == "sent"
        assert delivery.provider_message_id == "provider-message-id-1"
        assert delivery.sent_at is not None


class TestIdempotentRetry:
    @pytest.mark.anyio
    async def test_calling_send_twice_creates_exactly_one_row_and_calls_sender_once(
        self, db_session
    ) -> None:
        """AC7/AC8: the second call's `try_create` conflicts and
        short-circuits before ever reaching the sender."""
        user = await _make_user(db_session, "930000003")
        notification = await _make_notification(db_session, user.id)
        sender = _SpySender()
        service = _service(db_session, sender)

        first = await service.send(notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()
        second = await service.send(notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()

        assert first.id == second.id
        assert sender.call_count == 1

        result = await db_session.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification.id
            )
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.anyio
    async def test_a_different_notification_gets_its_own_key_and_is_not_blocked(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "930000004")
        first_notification = await _make_notification(db_session, user.id)
        second_notification = await _make_notification(db_session, user.id)
        sender = _SpySender()
        service = _service(db_session, sender)

        await service.send(first_notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()
        await service.send(second_notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()

        assert sender.call_count == 2

    @pytest.mark.anyio
    async def test_a_failed_first_attempt_still_blocks_a_second_call(
        self, db_session
    ) -> None:
        """The idempotency guarantee holds even if the first attempt
        ultimately failed -- the sender is never called a second time
        for an already-attempted `(notification_id, channel)` pair."""
        user = await _make_user(db_session, "930000005")
        notification = await _make_notification(db_session, user.id)
        sender = _AlwaysFailingSender()
        service = _service(db_session, sender)

        await service.send(notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()
        await service.send(notification, channel=NotificationChannel.WHATSAPP)
        await db_session.commit()

        assert sender.call_count == 1
