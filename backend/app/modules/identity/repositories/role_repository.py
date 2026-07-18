from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Role
from app.repositories.base_repository import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for the `identity.roles` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Role, session=session)

    async def get_by_name(self, name: str) -> Role | None:
        """Retrieve a role by its unique name (e.g. `customer`)."""
        stmt = select(Role).where(Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
