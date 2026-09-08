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
