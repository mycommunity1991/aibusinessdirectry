"""
Weekly availability management for a Provider (PRO-002, AC3).

`get_my_availability` always synthesizes exactly seven entries (Decision
3, `Plan_S04_PRO-002.md`) so the mobile client never has to handle a
variable-length response; any weekday without a saved row is returned as
a "closed, not yet configured" entry (both times `None`).
`update_my_availability` upserts up to seven entries in one call/flush --
Create+Read+Update collapsed into `GET`+`PUT`, never a per-weekday
`PATCH`.

`_synthesize` (CON-001, Decision 6, `Plan_S08_CON-001.md`) is the same
seven-day synthesis loop extracted into a private, provider-id-keyed
helper, shared by `get_my_availability` (owner-scoped, resolves its own
`Provider` by `user_id`) and the new `get_availability_for_provider`
(arbitrary target, no ownership check -- the caller has already resolved
and authorized viewing that `provider_id` via `ProviderService.
get_for_public_profile`). `get_my_availability`'s own behavior is
byte-for-byte unchanged by this extraction.
"""

import uuid
from dataclasses import dataclass
from datetime import time

from app.core.exceptions import ProviderNotFoundError
from app.modules.provider.models import Provider, Weekday
from app.modules.provider.repositories.provider_availability_repository import (
    ProviderAvailabilityRepository,
)
from app.modules.provider.services.provider_service import ProviderService

WEEKDAY_ORDER: list[Weekday] = [
    Weekday.MONDAY,
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
    Weekday.FRIDAY,
    Weekday.SATURDAY,
    Weekday.SUNDAY,
]


@dataclass(frozen=True)
class WeekdayAvailabilityEntry:
    """
    A uniform, duck-typed representation of one weekday's availability --
    shared shape for both real `ProviderAvailability` rows and
    synthesized "closed, not yet configured" weekdays, so the API layer's
    response-builder works identically for either.
    """

    weekday: Weekday
    open_time: time | None
    close_time: time | None
    is_emergency_available: bool


class AvailabilityService:
    """Orchestrates reading (with synthesis) and upserting a provider's
    weekly availability."""

    def __init__(
        self,
        provider_availability_repository: ProviderAvailabilityRepository,
        provider_service: ProviderService,
    ) -> None:
        self.provider_availability_repository = provider_availability_repository
        self.provider_service = provider_service

    async def get_my_availability(
        self, user_id: uuid.UUID
    ) -> list[WeekdayAvailabilityEntry]:
        """Returns exactly 7 entries, synthesizing "closed" for any
        weekday without a saved row yet (AC3)."""
        provider = await self._get_provider_or_404(user_id)
        return await self._synthesize(provider.id)

    async def get_availability_for_provider(
        self, provider_id: uuid.UUID
    ) -> list[WeekdayAvailabilityEntry]:
        """
        Returns exactly 7 entries for an arbitrary `provider_id` (CON-
        001, AC5, Decision 6, `Plan_S08_CON-001.md`) -- the Provider
        Profile screen's read path. No ownership check: the caller has
        already resolved and authorized viewing this `provider_id` via
        `ProviderService.get_for_public_profile` before calling this.
        """
        return await self._synthesize(provider_id)

    async def _synthesize(
        self, provider_id: uuid.UUID
    ) -> list[WeekdayAvailabilityEntry]:
        """
        Shared seven-day synthesis loop (Decision 6) -- any weekday
        without a saved row becomes a "closed, not yet configured"
        entry (both times `None`).
        """
        rows = await self.provider_availability_repository.list_for_provider(
            provider_id
        )
        by_weekday = {row.weekday: row for row in rows}

        return [
            WeekdayAvailabilityEntry(
                weekday=weekday,
                open_time=by_weekday[weekday].open_time
                if weekday in by_weekday
                else None,
                close_time=by_weekday[weekday].close_time
                if weekday in by_weekday
                else None,
                is_emergency_available=by_weekday[weekday].is_emergency_available
                if weekday in by_weekday
                else False,
            )
            for weekday in WEEKDAY_ORDER
        ]

    async def update_my_availability(
        self, user_id: uuid.UUID, entries: list[dict[str, object]]
    ) -> list[WeekdayAvailabilityEntry]:
        """
        Upserts up to 7 weekday entries in one flush (AC3) -- creates a
        missing row or updates an existing one. Returns the full,
        re-synthesized 7-entry set afterward.
        """
        provider = await self._get_provider_or_404(user_id)
        await self.provider_availability_repository.upsert_many(provider.id, entries)
        return await self.get_my_availability(user_id)

    async def _get_provider_or_404(self, user_id: uuid.UUID) -> Provider:
        provider = await self.provider_service.get_my_provider(user_id)
        if provider is None:
            raise ProviderNotFoundError()
        return provider
