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
