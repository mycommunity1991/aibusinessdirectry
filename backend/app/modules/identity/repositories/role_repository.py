import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Role, UserRole
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

    async def get_role_names_for_user(self, user_id: uuid.UUID) -> list[str]:
        """
        Retrieve the current role names assigned to a user via
        `user_roles`. Shared by `AuthService` (at login) and
        `SessionService` (at refresh, so a role change since the last
        login is reflected in the reissued access token) -- kept here
        rather than duplicated in each service.
        """
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
