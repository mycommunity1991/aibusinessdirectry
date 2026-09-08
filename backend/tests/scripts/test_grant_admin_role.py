"""
Integration tests for `scripts/grant_admin_role.py`'s testable core,
`grant_admin_role()` (VER-002, Decision 1) -- mirrors
`test_role_assignment_service.py`'s own assertions (idempotency, no
effect on other roles), exercised against a real Postgres database.

The CLI's own `main()` (argument parsing, `async_session` wiring, exit
code) is deliberately thin, untested glue -- the identical shape
`scripts/seed_roles.py`'s own `main()` already established, which is
likewise untested directly; only its testable core (`seed_roles`) has
its own test module.
"""

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_PROVIDER
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.identity.services.seed_data import seed_roles
from scripts.grant_admin_role import grant_admin_role

PHONE_COUNTRY_CODE = "+971"


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestGrantAdminRole:
    async def test_grants_admin_to_an_existing_user(self, db_session) -> None:
        await seed_roles(db_session)
        user = await _create_user(db_session, "1201000001")

        granted_user = await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000001",
        )
        await db_session.commit()

        assert granted_user is not None
        assert granted_user.id == user.id
        role_names = await RoleRepository(db_session).get_role_names_for_user(user.id)
        assert ROLE_ADMIN in role_names

    async def test_returns_none_for_a_nonexistent_user_without_creating_one(
        self, db_session
    ) -> None:
        await seed_roles(db_session)

        result = await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000099",
        )

        assert result is None

    async def test_is_idempotent(self, db_session) -> None:
        """Running the grant twice never creates a duplicate `user_roles`
        row and never raises."""
        await seed_roles(db_session)
        user = await _create_user(db_session, "1201000002")

        await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000002",
        )
        await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000002",
        )
        await db_session.commit()

        role_names = await RoleRepository(db_session).get_role_names_for_user(user.id)
        assert role_names.count(ROLE_ADMIN) == 1

    async def test_does_not_affect_the_users_other_existing_roles(
        self, db_session
    ) -> None:
        """Granting Admin never removes a role the user already holds --
        mirrors `test_role_assignment_service.py`'s equivalent assertion
        for `ensure_role_assigned` directly."""
        await seed_roles(db_session)
        user = await _create_user(db_session, "1201000003")
        await RoleAssignmentService(RoleRepository(db_session)).ensure_role_assigned(
            user.id, ROLE_PROVIDER
        )
        await db_session.commit()

        await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000003",
        )
        await db_session.commit()

        role_names = await RoleRepository(db_session).get_role_names_for_user(user.id)
        assert set(role_names) == {ROLE_PROVIDER, ROLE_ADMIN}

    async def test_granting_one_user_does_not_affect_a_different_user(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        user_a = await _create_user(db_session, "1201000004")
        user_b = await _create_user(db_session, "1201000005")
        await RoleAssignmentService(RoleRepository(db_session)).ensure_role_assigned(
            user_b.id, ROLE_CUSTOMER
        )
        await db_session.commit()

        await grant_admin_role(
            db_session,
            phone_country_code=PHONE_COUNTRY_CODE,
            phone_number="1201000004",
        )
        await db_session.commit()

        assert await RoleRepository(db_session).get_role_names_for_user(user_a.id) == [
            ROLE_ADMIN
        ]
        assert await RoleRepository(db_session).get_role_names_for_user(user_b.id) == [
            ROLE_CUSTOMER
        ]
