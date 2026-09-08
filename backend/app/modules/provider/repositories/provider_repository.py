import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import Provider
from app.repositories.base_repository import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    """Repository for the `provider.providers` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Provider, session=session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Provider | None:
        """
        Retrieve a Provider by its owning `identity.users.id`. The
        one-provider-per-account existence check (AC8) and the backing
        query for `GET /providers/me` (Decision 9,
        `Plan_S04_PRO-001.md`).
        """
        stmt = select(Provider).where(Provider.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Provider | None:
        """
        Retrieve a Provider by its unique `slug` -- used only by
        `ProviderService._generate_unique_slug`'s collision-check loop
        (Decision 6, `Plan_S04_PRO-001.md`); never a client-facing lookup
        key in this story.
        """
        stmt = select(Provider).where(Provider.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Provider]:
        """
        Batch-fetches Providers by id in one query (VER-002, Decision 9,
        `Plan_S05_VER-002.md`) -- used by `AdminVerificationService.
        list_pending_for_review` to enrich a page of verification
        records with Provider context without an N+1 query per record.
        """
        if not ids:
            return []
        stmt = select(Provider).where(Provider.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
