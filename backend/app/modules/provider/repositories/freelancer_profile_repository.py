import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import FreelancerProfile
from app.repositories.base_repository import BaseRepository


class FreelancerProfileRepository(BaseRepository[FreelancerProfile]):
    """Repository for the `provider.freelancer_profiles` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=FreelancerProfile, session=session)

    async def get_by_provider_id(
        self, provider_id: uuid.UUID
    ) -> FreelancerProfile | None:
        """Retrieve the 1:1 `freelancer_profiles` row for a given Provider."""
        stmt = select(FreelancerProfile).where(
            FreelancerProfile.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
