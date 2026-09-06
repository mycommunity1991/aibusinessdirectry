import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer.models import CustomerPreferences
from app.repositories.base_repository import BaseRepository


class CustomerPreferencesRepository(BaseRepository[CustomerPreferences]):
    """Repository for the `customer.customer_preferences` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=CustomerPreferences, session=session)

    async def get_by_customer_id(
        self, customer_id: uuid.UUID
    ) -> CustomerPreferences | None:
        """Retrieve preferences by their owning `customer_profiles.id`."""
        stmt = select(CustomerPreferences).where(
            CustomerPreferences.customer_id == customer_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
