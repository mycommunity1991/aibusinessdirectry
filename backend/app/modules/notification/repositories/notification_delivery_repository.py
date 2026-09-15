from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import NotificationDelivery
from app.repositories.base_repository import BaseRepository


class NotificationDeliveryRepository(BaseRepository[NotificationDelivery]):
    """
    Repository for the `notification.notification_delivery` table
    (`ENG-001`, AC2/AC7, Decision 8, `Plan_S12_ENG-001.md`).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=NotificationDelivery, session=session)

    async def try_create(self, values: dict[str, Any]) -> NotificationDelivery | None:
        """
        Atomically inserts a new `notification_delivery` row, but only
        if no row already exists for `values["idempotency_key"]`
        (Decision 8) -- `INSERT ... ON CONFLICT (idempotency_key) DO
        NOTHING ... RETURNING`, never a read-then-write check
        (`ADR-049`-shaped, the fourth application of this codebase's
        atomic-conditional-write family, mirroring `OutcomeTagRepository.
        try_create`/`ReviewRepository.try_create` exactly). Returns
        `None` on conflict -- `NotificationDeliveryService.send` treats
        this as "already attempted" and never calls the sender.
        """
        stmt = (
            postgresql.insert(NotificationDelivery)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(NotificationDelivery.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        new_id = result.scalar_one_or_none()
        if new_id is None:
            return None
        return await self.get_by_id(new_id)

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> NotificationDelivery | None:
        """
        Resolves the existing row for an idempotency key that `try_create`
        just reported a conflict for -- used by `NotificationDeliveryService.
        send` to return the already-attempted row rather than `None`.
        """
        stmt = select(NotificationDelivery).where(
            NotificationDelivery.idempotency_key == idempotency_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_sent(
        self, delivery: NotificationDelivery, *, provider_message_id: str | None
    ) -> NotificationDelivery:
        """Marks a delivery attempt `status="sent"` (Decision 7) -- a
        plain `BaseRepository.update` call; no race to guard against
        once the row is already exclusively owned by the one delivery
        attempt that created it."""
        return await self.update(
            delivery,
            {
                "status": "sent",
                "provider_message_id": provider_message_id,
                "sent_at": datetime.now(UTC),
            },
        )

    async def mark_failed(
        self, delivery: NotificationDelivery, *, failure_reason: str
    ) -> NotificationDelivery:
        """Marks a delivery attempt `status="failed"` with a non-null
        `failure_reason` (AC2) -- never re-raised past
        `NotificationDeliveryService.send` (Decision 7)."""
        return await self.update(
            delivery,
            {"status": "failed", "failure_reason": failure_reason},
        )
