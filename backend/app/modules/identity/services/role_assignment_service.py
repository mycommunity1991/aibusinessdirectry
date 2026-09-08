"""
Cross-module role-grant capability: `provider -> identity` (PRO-001,
Decision 1) -- the reverse direction of ADR-014's `identity -> customer`/
`identity -> audit` edges.

`AuthService`'s existing inline role-assignment logic (at registration
time only, directly against `RoleRepository`/`UserRole`) is untouched by
this file -- this is a new, narrower, reusable capability for granting a
role to an *already-authenticated* caller from a *different* module,
not a refactor of already-shipped code. See
`docs/implementation/plans/Plan_S04_PRO-001.md`, Decision 1.
"""

import uuid

from app.modules.identity.models import UserRole
from app.modules.identity.repositories.role_repository import RoleRepository


class RoleAssignmentService:
    """
    Grants a named role to an already-existing user, idempotently.

    Deliberately the only capability this service exposes -- `provider`
    (and any future module) depends on this service, never on
    `RoleRepository`/`UserRole` directly, per `02_ARCHITECTURE.md`'s
    "modules communicate through services only" rule.
    """

    def __init__(self, role_repository: RoleRepository) -> None:
        self.role_repository = role_repository

    async def ensure_role_assigned(self, user_id: uuid.UUID, role_name: str) -> None:
        """
        Idempotently ensures `user_id` holds `role_name`: a no-op if the
        role is already assigned, and a no-op (rather than raising) if
        `role_name` does not exist as a seeded `identity.roles` row --
        this method never fails the caller's own transaction over a
        role-catalog inconsistency.

        Flush only -- never commits. The caller shares the same
        request-scoped `AsyncSession`, so the new `user_roles` row rides
        whatever single `db.commit()` the caller's own endpoint already
        performs (Decision 1, `Plan_S04_PRO-001.md`).
        """
        existing_role_names = await self.role_repository.get_role_names_for_user(
            user_id
        )
        if role_name in existing_role_names:
            return

        role = await self.role_repository.get_by_name(role_name)
        if role is None:
            return

        self.role_repository.session.add(UserRole(user_id=user_id, role_id=role.id))
        await self.role_repository.session.flush()
