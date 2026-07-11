from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import Base
from app.repositories.interfaces.base import IBaseRepository


class BaseRepository[ModelType: Base](IBaseRepository[ModelType]):
    """
    Generic BaseRepository implementation.
    Methods here should NOT call `self.session.commit()`.
    Transaction boundaries must be managed by the application/service layer.
    Exceptions are intentionally allowed to propagate.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """
        Initialize the repository.

        Args:
            model: The SQLAlchemy declarative model class.
            session: The SQLAlchemy AsyncSession for database operations.
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> ModelType | None:
        """Retrieve a record by its primary key."""
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Retrieve all records with optional pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any] | ModelType) -> ModelType:
        """Create a new record."""
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = obj_in

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """Update an existing record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> bool:
        """Delete a record by its primary key."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def exists(self, id: Any) -> bool:
        """Check if a record exists by its primary key."""
        db_obj = await self.get_by_id(id)
        return db_obj is not None
