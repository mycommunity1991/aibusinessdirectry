"""
Integration tests for `RoleRepository.get_user_ids_for_role` (`ENG-001`,
Decision 9, `Plan_S12_ENG-001.md`) -- the reverse of the existing
`get_role_names_for_user`. Mirrors `test_role_assignment_service.py`'s
real-Postgres, real-DB approach.
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


class TestGetUserIdsForRole:
    @pytest.mark.anyio
    async def test_returns_exactly_the_seeded_admin_account_ids(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        role_repository = RoleRepository(db_session)
        role_assignment_service = RoleAssignmentService(role_repository)

        admin_one = await _create_user(db_session, "504000001")
        admin_two = await _create_user(db_session, "504000002")
        customer = await _create_user(db_session, "504000003")

        await role_assignment_service.ensure_role_assigned(admin_one.id, ROLE_ADMIN)
        await role_assignment_service.ensure_role_assigned(admin_two.id, ROLE_ADMIN)
        await role_assignment_service.ensure_role_assigned(customer.id, ROLE_CUSTOMER)

        admin_ids = await role_repository.get_user_ids_for_role(ROLE_ADMIN)

        assert sorted(admin_ids) == sorted([admin_one.id, admin_two.id])
        assert customer.id not in admin_ids

    @pytest.mark.anyio
    async def test_returns_an_empty_list_for_a_role_no_account_holds(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        role_repository = RoleRepository(db_session)
        role_assignment_service = RoleAssignmentService(role_repository)
        provider = await _create_user(db_session, "504000004")
        await role_assignment_service.ensure_role_assigned(provider.id, ROLE_PROVIDER)

        admin_ids = await role_repository.get_user_ids_for_role(ROLE_ADMIN)

        assert admin_ids == []
