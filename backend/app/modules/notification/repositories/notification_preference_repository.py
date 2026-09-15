import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import NotificationPreference
from app.repositories.base_repository import BaseRepository


class NotificationPreferenceRepository(BaseRepository[NotificationPreference]):
    """
    Repository for the `notification.notification_preferences` table
    (`ENG-001`, Decision 3/4/5, `Plan_S12_ENG-001.md`).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=NotificationPreference, session=session)

    async def get_by_user_id(
        self, user_id: uuid.UUID
    ) -> NotificationPreference | None:
        """Retrieve a user's preferences row, if one already exists."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def try_create(
        self, values: dict[str, Any]
    ) -> NotificationPreference | None:
        """
        Atomically inserts a new `notification_preferences` row, but
        only if no row already exists for `values["user_id"]` --
        `INSERT ... ON CONFLICT (user_id) DO NOTHING ... RETURNING`,
        never a read-then-write check (`ADR-049`-shaped, mirroring
        `OutcomeTagRepository.try_create`). Returns the new row if this
        call won the race, or `None` if a row for this `user_id`
        already existed -- `NotificationPreferenceService.
        get_or_create_for_user` falls back to `get_by_user_id` in that
        case, so two concurrent first-touches for the same user never
        both "win" and never raise.
        """
        stmt = (
            postgresql.insert(NotificationPreference)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["user_id"])
            .returning(NotificationPreference.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        new_id = result.scalar_one_or_none()
        if new_id is None:
            return None
        return await self.get_by_id(new_id)
