import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import ProviderAvailability, Weekday
from app.repositories.base_repository import BaseRepository


class ProviderAvailabilityRepository(BaseRepository[ProviderAvailability]):
    """Repository for the `provider.provider_availability` table (PRO-002)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ProviderAvailability, session=session)

    async def list_for_provider(
        self, provider_id: uuid.UUID
    ) -> Sequence[ProviderAvailability]:
        """Lists every configured weekday row for a provider -- may be
        fewer than seven; `AvailabilityService` synthesizes the rest
        (Decision 3, `Plan_S04_PRO-002.md`)."""
        stmt = select(ProviderAvailability).where(
            ProviderAvailability.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_many(
        self, provider_id: uuid.UUID, entries: list[dict[str, Any]]
    ) -> None:
        """
        Creates a missing weekday row or updates an existing one, for up
        to seven entries, in one flush (Decision 3) -- never a separate
        commit per weekday.
        """
        existing_rows = await self.list_for_provider(provider_id)
        existing_by_weekday: dict[Weekday, ProviderAvailability] = {
            row.weekday: row for row in existing_rows
        }

        for entry in entries:
            weekday: Weekday = entry["weekday"]
            existing = existing_by_weekday.get(weekday)
            if existing is not None:
                existing.open_time = entry["open_time"]
                existing.close_time = entry["close_time"]
                existing.is_emergency_available = entry["is_emergency_available"]
                self.session.add(existing)
            else:
                self.session.add(
                    ProviderAvailability(
                        provider_id=provider_id,
                        weekday=weekday,
                        open_time=entry["open_time"],
                        close_time=entry["close_time"],
                        is_emergency_available=entry["is_emergency_available"],
                    )
                )

        await self.session.flush()
