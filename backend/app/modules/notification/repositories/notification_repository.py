import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """
    Repository for the `notification.notifications` table (VER-002).
    `ENG-001` (Decision 10, `Plan_S12_ENG-001.md`) adds `list_for_user`/
    `count_unread`/`mark_read` -- the Notifications Inbox screen's read
    paths (`GET /notifications`, `GET /notifications/unread-count`,
    `PATCH /notifications/{id}/read`).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Notification, session=session)

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[Notification], int]:
        """
        Lists one page of `user_id`'s notifications, newest first, plus
        a total count for `PaginationMeta` -- mirrors `VerificationRecord
        Repository.list_for_review`'s identical count-then-page shape.
        """
        filtered = select(Notification).where(Notification.user_id == user_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(filtered.subquery())
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            filtered.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_unread(self, user_id: uuid.UUID) -> int:
        """
        A dedicated, `COUNT(*)`-only query (mirrors `ADM-002`'s
        "dedicated count-only method, never reuse a `list_*`'s bundled
        total" precedent) -- backs AC5's "badge".
        """
        stmt = select(func.count()).select_from(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .subquery()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        """
        Ownership-scoped `UPDATE ... WHERE id = :id AND user_id =
        :user_id AND read_at IS NULL RETURNING` -- idempotent: marking
        an already-read row read again is a harmless no-op. Returns the
        row (fetched via a follow-up `get_by_id`) whether this call set
        `read_at` or found it already set, or `None` if no row exists
        for `notification_id` at all, or it exists but belongs to a
        different user (the caller maps that to a 404, never a 403,
        `ADR-015`).
        """
        existing = await self.get_by_id(notification_id)
        if existing is None or existing.user_id != user_id:
            return None

        if existing.read_at is None:
            stmt = (
                update(Notification)
                .where(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
                .values(read_at=datetime.now(UTC))
            )
            await self.session.execute(stmt)
            await self.session.flush()
            await self.session.refresh(existing)

        return existing
