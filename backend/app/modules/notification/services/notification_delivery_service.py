"""
`NotificationDeliveryService` (`ENG-001`, AC2/AC7/AC8, Decision 7/8,
`Plan_S12_ENG-001.md`) -- dispatches one notification to one recipient
over one external channel, idempotently, catching every typed
`NotificationDeliveryError` so a delivery failure can never break the
triggering caller's own request.
"""

import logging

from app.modules.customer.models import NotificationChannel
from app.modules.notification.models import Notification, NotificationDelivery
from app.modules.notification.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.modules.notification.services.notification_sender import (
    NotificationDeliveryError,
    NotificationSender,
)

logger = logging.getLogger(__name__)

_STATUS_PENDING = "pending"


class NotificationDeliveryService:
    """
    Holds a `dict[NotificationChannel, NotificationSender]` registry
    (mirrors `identity.dependencies.get_oauth_service`'s existing
    `{AuthProvider.GOOGLE: ..., AuthProvider.APPLE: ...}` dict-of-
    implementations shape exactly) and dispatches to the correct sender
    by the recipient's own `channel` preference.
    """

    def __init__(
        self,
        delivery_repository: NotificationDeliveryRepository,
        senders: dict[NotificationChannel, NotificationSender],
    ) -> None:
        self.delivery_repository = delivery_repository
        self.senders = senders

    async def send(
        self, notification: Notification, *, channel: NotificationChannel
    ) -> NotificationDelivery:
        """
        Sends `notification` over `channel`, idempotently (Decision 8):
        computes the deterministic `f"{notification.id}:{channel.value}"`
        idempotency key itself (never accepts one from a caller), then
        atomically `try_create`s the delivery row.

        - On conflict (a delivery row for this `(notification_id,
          channel)` pair already exists), short-circuits and returns
          the existing row -- the underlying `NotificationSender.send`
          is never called a second time for an already-attempted pair,
          regardless of whether the first attempt ultimately succeeded
          or failed (AC7/AC8).
        - Otherwise, calls `senders[channel].send(...)`, catching any
          `NotificationDeliveryError` and recording `status="failed"`
          with a non-null `failure_reason` -- never re-raising to the
          caller (AC2, Decision 7). On success, records `status="sent"`
          with the sender's own returned provider message id, if any.
        """
        idempotency_key = f"{notification.id}:{channel.value}"

        delivery = await self.delivery_repository.try_create(
            {
                "notification_id": notification.id,
                "channel": channel,
                "status": _STATUS_PENDING,
                "idempotency_key": idempotency_key,
            }
        )
        if delivery is None:
            existing = await self.delivery_repository.get_by_idempotency_key(
                idempotency_key
            )
            assert existing is not None
            return existing

        sender = self.senders[channel]
        try:
            provider_message_id = await sender.send(
                recipient_user_id=notification.user_id,
                title=notification.title,
                body=notification.body,
            )
        except NotificationDeliveryError as exc:
            logger.warning(
                "Notification delivery failed for notification %s over "
                "channel %s: %s",
                notification.id,
                channel.value,
                exc,
            )
            return await self.delivery_repository.mark_failed(
                delivery, failure_reason=str(exc)
            )

        return await self.delivery_repository.mark_sent(
            delivery, provider_message_id=provider_message_id
        )
