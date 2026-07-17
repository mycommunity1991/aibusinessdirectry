from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.database import engine

# Create the async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency yielding an AsyncSession.
    Ensures that the session is closed when the request lifecycle ends.
    """
    async with async_session() as session:
        yield session
