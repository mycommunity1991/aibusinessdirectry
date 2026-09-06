import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer.models import CustomerProfile
from app.repositories.base_repository import BaseRepository


class CustomerProfileRepository(BaseRepository[CustomerProfile]):
    """Repository for the `customer.customer_profiles` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=CustomerProfile, session=session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> CustomerProfile | None:
        """Retrieve a customer profile by its owning `identity.users.id`
        (the only lookup key ever used -- Decision 5,
        `Plan_S03_CUS-001.md`)."""
        stmt = select(CustomerProfile).where(CustomerProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
