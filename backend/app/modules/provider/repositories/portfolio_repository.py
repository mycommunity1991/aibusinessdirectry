import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import Portfolio
from app.repositories.base_repository import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    """
    Repository for the `provider.portfolios` table (PRO-002).

    `BaseRepository.delete()` hard-deletes -- deliberately not used here.
    `soft_delete()` mirrors `SavedAddressRepository.soft_delete` exactly
    (Decision 5, `Plan_S04_PRO-002.md`): every list/get query below
    filters `is_active` so a soft-deleted photo is invisible going
    forward, while the row (and its on-disk file) survive.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Portfolio, session=session)

    async def list_active_for_provider(
        self, provider_id: uuid.UUID
    ) -> Sequence[Portfolio]:
        """Lists every active (non-soft-deleted) photo owned by a
        provider, ordered by `sort_order` (Decision 3)."""
        stmt = (
            select(Portfolio)
            .where(
                Portfolio.provider_id == provider_id,
                Portfolio.is_active.is_(True),
            )
            .order_by(Portfolio.sort_order.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_active_for_provider_ids(
        self, provider_ids: list[uuid.UUID]
    ) -> Sequence[Portfolio]:
        """
        Batch-fetches every active photo for a set of providers in one
        query (DIR-001, `Plan_S06_DIR-001.md`) -- used by
        `ProviderService.get_primary_photo_urls` to enrich a page of
        search results without an N+1 query per result. Ordered by
        `provider_id`, then `sort_order` (Decision 3) so the first photo
        encountered per provider while iterating the result is always
        that provider's primary (lowest `sort_order`) photo.
        """
        if not provider_ids:
            return []
        stmt = (
            select(Portfolio)
            .where(
                Portfolio.provider_id.in_(provider_ids),
                Portfolio.is_active.is_(True),
            )
            .order_by(Portfolio.provider_id, Portfolio.sort_order.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_id(self, portfolio_id: uuid.UUID) -> Portfolio | None:
        """
        Retrieves a photo by id only if it has not been soft-deleted.
        Used before the caller's ownership check (AC7/AC8) -- a
        soft-deleted row is treated identically to a never-existing one,
        mirroring `SavedAddressRepository.get_active_by_id`'s pattern.
        """
        stmt = select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.is_active.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, photo: Portfolio) -> None:
        """
        Soft-deletes a photo (Decision 5): sets `deleted_at`/`is_active`,
        flush only. Never a hard `session.delete()` -- the on-disk file
        is deliberately left in place; orphaned-file cleanup is a future
        administrative job, out of this story's scope.
        """
        photo.deleted_at = datetime.now(UTC)
        photo.is_active = False
        self.session.add(photo)
        await self.session.flush()

    async def bulk_set_sort_order(self, ordered: list[tuple[uuid.UUID, int]]) -> None:
        """
        Sets each photo's `sort_order` to its new index, in one flush
        (Decision 4, `Plan_S04_PRO-002.md`) -- mirrors
        `SavedAddressRepository.unset_other_defaults`'s single-flush
        bulk-write pattern. Callers must validate the id set *before*
        calling this (`PortfolioService.reorder`) -- this method assumes
        every id has already been confirmed to belong to the caller.
        """
        for photo_id, new_sort_order in ordered:
            photo = await self.session.get(Portfolio, photo_id)
            if photo is not None:
                photo.sort_order = new_sort_order
                self.session.add(photo)
        await self.session.flush()
