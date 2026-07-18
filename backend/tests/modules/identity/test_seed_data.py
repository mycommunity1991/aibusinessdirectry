"""
Integration tests for `app.modules.identity.services.seed_data.seed_roles`
(AC2 — seeded roles must be idempotent to re-run).
"""

from sqlalchemy import select

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_PROVIDER
from app.modules.identity.models import Role
from app.modules.identity.services.seed_data import seed_roles


async def test_seed_roles_creates_expected_roles(db_session):
    await seed_roles(db_session)
    await db_session.commit()

    result = await db_session.execute(select(Role.name))
    names = set(result.scalars().all())

    assert {ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN}.issubset(names)


async def test_seed_roles_is_idempotent(db_session):
    await seed_roles(db_session)
    await db_session.commit()

    # Running it again must not error or duplicate rows.
    await seed_roles(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(Role.name).where(
            Role.name.in_([ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN])
        )
    )
    names = result.scalars().all()

    assert len(names) == 3
    assert len(set(names)) == 3
