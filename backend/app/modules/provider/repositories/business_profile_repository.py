import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import BusinessProfile
from app.repositories.base_repository import BaseRepository


class BusinessProfileRepository(BaseRepository[BusinessProfile]):
    """Repository for the `provider.business_profiles` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=BusinessProfile, session=session)

    async def get_by_provider_id(
        self, provider_id: uuid.UUID
    ) -> BusinessProfile | None:
        """Retrieve the 1:1 `business_profiles` row for a given Provider."""
        stmt = select(BusinessProfile).where(BusinessProfile.provider_id == provider_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_provider_ids(
        self, provider_ids: list[uuid.UUID]
    ) -> list[BusinessProfile]:
        """
        Batch-fetches `business_profiles` rows for a set of providers in
        one query (CLM-001, AC3, `Plan_S06_CLM-001.md`) -- used by
        `ProviderService.get_business_profiles_by_provider_id` to enrich
        a page of claim-search results without an N+1 query per result,
        mirroring `ProviderCategoryLabelRepository.list_for_provider_ids`'s
        identical batching pattern.
        """
        if not provider_ids:
            return []
        stmt = select(BusinessProfile).where(
            BusinessProfile.provider_id.in_(provider_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
