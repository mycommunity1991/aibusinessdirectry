"""
CLI entry point to grant `ROLE_ADMIN` to an already-registered user
(VER-002, Decision 1, `Plan_S05_VER-002.md`).

Requires the target person to already have a real, registered Account
(through the ordinary OTP/Google/Apple sign-in flow) -- this script
never creates a phantom account; it looks one up and grants a role to
it. Never exposed via HTTP -- requires direct server/deployment access
to run, the same trust boundary `seed_roles.py` already relies on.

Usage (from the `backend/` directory, so `app`/`scripts` are importable):
    uv run python -m scripts.grant_admin_role --phone-country-code +971 \\
        --phone-number 501234567
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN
from app.database.session import async_session
from app.modules.identity.models import User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)

logger = logging.getLogger(__name__)


async def grant_admin_role(
    session: AsyncSession, *, phone_country_code: str, phone_number: str
) -> User | None:
    """
    Looks up the target user by phone and idempotently grants
    `ROLE_ADMIN` (via `RoleAssignmentService.ensure_role_assigned`, the
    same generic, already-tested capability PRO-001 built) -- never
    affecting any other role the user already holds. Flush only; the
    caller controls the commit boundary (mirrors `seed_roles`'s own
    convention, and keeps this function directly testable against the
    `db_session` fixture rather than only through the CLI's own
    `async_session`).

    Returns `None` (never raises) if no such user exists -- this
    function never creates a new account.
    """
    user_repository = UserRepository(session)
    user = await user_repository.get_by_phone(phone_country_code, phone_number)
    if user is None:
        return None

    role_assignment_service = RoleAssignmentService(RoleRepository(session))
    await role_assignment_service.ensure_role_assigned(user.id, ROLE_ADMIN)
    return user


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grant the Admin role to an already-registered user."
    )
    parser.add_argument("--phone-country-code", required=True, help="E.g. +971")
    parser.add_argument("--phone-number", required=True, help="E.g. 501234567")
    return parser.parse_args()


async def main(phone_country_code: str, phone_number: str) -> int:
    async with async_session() as session:
        user = await grant_admin_role(
            session,
            phone_country_code=phone_country_code,
            phone_number=phone_number,
        )
        if user is None:
            logger.error(
                "No existing user found for the given phone number -- this "
                "script never creates a new account. The target person must "
                "register through the ordinary sign-in flow first."
            )
            return 1
        await session.commit()

    logger.info("Granted ROLE_ADMIN to user %s.", user.id)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    exit_code = asyncio.run(main(args.phone_country_code, args.phone_number))
    sys.exit(exit_code)
