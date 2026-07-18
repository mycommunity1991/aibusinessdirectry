"""
Idempotent seed data for reference tables.

Seed functions are safe to re-run: they upsert on the table's natural
unique key and never duplicate rows, per `docs/AI/04_DATABASE.md` and
AC2 of `Plan_S02_AUTH-001.md`.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_PROVIDER
from app.modules.identity.models import Role

# name -> description
_SEED_ROLES: dict[str, str] = {
    ROLE_CUSTOMER: "Searches for and contacts businesses/freelancers.",
    ROLE_PROVIDER: "Offers services as a business or freelancer listing.",
    ROLE_ADMIN: "Platform administrator with back-office access.",
}


async def seed_roles(session: AsyncSession) -> None:
    """
    Idempotently insert the platform's fixed role set (`customer`,
    `provider`, `admin`) into `identity.roles`.

    Uses `INSERT ... ON CONFLICT (name) DO NOTHING` so running this
    function multiple times (e.g. on every deploy) never duplicates or
    errors. Does not commit — the caller controls the transaction
    boundary.
    """
    values = [
        {"name": name, "description": description}
        for name, description in _SEED_ROLES.items()
    ]
    stmt = pg_insert(Role).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
    await session.execute(stmt)
