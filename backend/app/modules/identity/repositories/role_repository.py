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

    async def get_user_ids_for_role(self, role_name: str) -> list[uuid.UUID]:
        """
        Retrieve every user id currently holding `role_name` (`ENG-001`,
        Decision 9, `Plan_S12_ENG-001.md`) -- the reverse of
        `get_role_names_for_user`, an identically-shaped `SELECT ...
        JOIN user_roles ... WHERE roles.name = :role_name` query. Used
        by `NotificationService.notify_manual_match_assignment_created`
        to broadcast an in-app-only notification to every `ROLE_ADMIN`
        account, without ever inventing a new "admin team" recipient
        concept. Returns an empty list if no account currently holds
        `role_name`.
        """
        stmt = (
            select(UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == role_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
