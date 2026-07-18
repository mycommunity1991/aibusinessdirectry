"""
CLI entry point to seed the fixed Identity domain role set.

Usage (from the `backend/` directory, so `app`/`scripts` are importable):
    uv run python -m scripts.seed_roles
"""

import asyncio
import logging

from app.database.session import async_session
from app.modules.identity.services.seed_data import seed_roles

logger = logging.getLogger(__name__)


async def main() -> None:
    async with async_session() as session:
        await seed_roles(session)
        await session.commit()
    logger.info("Identity roles seeded successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
