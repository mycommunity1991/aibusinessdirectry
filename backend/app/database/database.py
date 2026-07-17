import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create the asynchronous SQLAlchemy engine using the normalized settings.DATABASE_URL
engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
)


async def check_database_connection() -> bool:
    """
    Verify database connection using the async engine.
    Executes SELECT 1. Logs connection failures cleanly and safely.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        # Log failure with type and message, avoiding full URL output
        # which could leak passwords.
        logger.error(
            f"Database connection check failed: {type(e).__name__}. "
            "Please verify connection settings."
        )
        return False
