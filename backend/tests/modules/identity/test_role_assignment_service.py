"""
Integration tests for `RoleAssignmentService` (PRO-001, Decision 1) --
the new `provider -> identity` cross-module role-grant capability.

Uses the real-Postgres `db_session`/`db_engine` fixtures (ADR-013) since
this service's entire purpose is to correctly read/write real
`identity.roles`/`identity.user_roles` rows via `RoleRepository`.
"""

import pytest

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_PROVIDER
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.identity.services.seed_data import seed_roles

PHONE_COUNTRY_CODE = "+971"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


class TestEnsureRoleAssigned:
    @pytest.mark.anyio
    async def test_grants_a_missing_role(self, db_session) -> None:
        await seed_roles(db_session)
        user = await _create_user(db_session, "503000001")
        role_repository = RoleRepository(db_session)
        service = RoleAssignmentService(role_repository)

        await service.ensure_role_assigned(user.id, ROLE_PROVIDER)

        role_names = await role_repository.get_role_names_for_user(user.id)
        assert ROLE_PROVIDER in role_names

    @pytest.mark.anyio
    async def test_is_a_no_op_for_an_already_held_role(self, db_session) -> None:
        """Idempotency: calling it twice never creates a duplicate
        `user_roles` row and never raises."""
        await seed_roles(db_session)
        user = await _create_user(db_session, "503000002")
        role_repository = RoleRepository(db_session)
        service = RoleAssignmentService(role_repository)

        await service.ensure_role_assigned(user.id, ROLE_PROVIDER)
        await service.ensure_role_assigned(user.id, ROLE_PROVIDER)

        role_names = await role_repository.get_role_names_for_user(user.id)
        assert role_names.count(ROLE_PROVIDER) == 1

    @pytest.mark.anyio
    async def test_granting_a_role_does_not_remove_existing_roles(
        self, db_session
    ) -> None:
        """A Customer gains Provider without losing Customer."""
        await seed_roles(db_session)
        user = await _create_user(db_session, "503000003")
        role_repository = RoleRepository(db_session)
        service = RoleAssignmentService(role_repository)
        await service.ensure_role_assigned(user.id, ROLE_CUSTOMER)

        await service.ensure_role_assigned(user.id, ROLE_PROVIDER)

        role_names = await role_repository.get_role_names_for_user(user.id)
        assert set(role_names) == {ROLE_CUSTOMER, ROLE_PROVIDER}

    @pytest.mark.anyio
    async def test_unseeded_role_name_is_a_no_op_not_an_error(self, db_session) -> None:
        """Defensive: a role name with no matching `identity.roles` row
        never raises -- it simply isn't granted."""
        await seed_roles(db_session)
        user = await _create_user(db_session, "503000004")
        role_repository = RoleRepository(db_session)
        service = RoleAssignmentService(role_repository)

        await service.ensure_role_assigned(user.id, "not_a_real_role")

        role_names = await role_repository.get_role_names_for_user(user.id)
        assert role_names == []

    @pytest.mark.anyio
    async def test_granting_provider_role_does_not_affect_admin_role_state(
        self, db_session
    ) -> None:
        """Granting `ROLE_PROVIDER` never touches an unrelated role's
        assignment for a different, unrelated account."""
        await seed_roles(db_session)
        user_a = await _create_user(db_session, "503000005")
        user_b = await _create_user(db_session, "503000006")
        role_repository = RoleRepository(db_session)
        service = RoleAssignmentService(role_repository)
        await service.ensure_role_assigned(user_b.id, ROLE_ADMIN)

        await service.ensure_role_assigned(user_a.id, ROLE_PROVIDER)

        assert await role_repository.get_role_names_for_user(user_a.id) == [
            ROLE_PROVIDER
        ]
        assert await role_repository.get_role_names_for_user(user_b.id) == [ROLE_ADMIN]
