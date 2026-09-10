import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import ServiceArea
from app.repositories.base_repository import BaseRepository


class ServiceAreaRepository(BaseRepository[ServiceArea]):
    """
    Repository for the `provider.service_areas` table (PRO-002).

    Internal-only -- `service_areas` rows are derived data, kept in sync
    by `ProviderService` whenever a subtype profile's location/radius
    fields change (Decision, item 1, `Plan_S04_PRO-002.md`). No direct
    API exposes this table for reading or editing in this story.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ServiceArea, session=session)

    async def get_for_provider(self, provider_id: uuid.UUID) -> ServiceArea | None:
        stmt = select(ServiceArea).where(ServiceArea.provider_id == provider_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_provider_ids(
        self, provider_ids: list[uuid.UUID]
    ) -> list[ServiceArea]:
        """
        Batch-fetches `service_areas` rows for a set of providers in one
        query (AI-002, `Plan_S07_AI-002.md`) -- mirrors
        `BusinessProfileRepository.list_by_provider_ids`'s identical
        batching pattern. `ProviderService.get_locations_by_provider_id`
        uses this (not `business_profiles`/`freelancer_profiles`) because
        `service_areas.center_latitude/center_longitude` is the exact
        location `ProviderSearchRepository.search_nearby`'s geospatial
        query itself matches/ranks against -- the only source that keeps
        a manually-recomputed `distance_meters` (Decision 6) consistent
        with what the automated matcher actually used.
        """
        if not provider_ids:
            return []
        stmt = select(ServiceArea).where(ServiceArea.provider_id.in_(provider_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_for_provider(
        self,
        provider_id: uuid.UUID,
        *,
        center_latitude: float,
        center_longitude: float,
        radius_meters: int,
    ) -> ServiceArea:
        """Creates or updates the provider's single derived service-area row."""
        existing = await self.get_for_provider(provider_id)
        if existing is not None:
            existing.center_latitude = center_latitude
            existing.center_longitude = center_longitude
            existing.radius_meters = radius_meters
            self.session.add(existing)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            {
                "provider_id": provider_id,
                "center_latitude": center_latitude,
                "center_longitude": center_longitude,
                "radius_meters": radius_meters,
            }
        )
