from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for the `identity.users` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=User, session=session)

    async def get_by_phone(
        self, phone_country_code: str, phone_number: str
    ) -> User | None:
        """Retrieve a user by their unique (phone_country_code, phone_number)."""
        stmt = select(User).where(
            User.phone_country_code == phone_country_code,
            User.phone_number == phone_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
