from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class IBaseRepository[ModelType](ABC):
    """
    Abstract Base Class for generic repository contracts.
    """

    @abstractmethod
    async def get_by_id(self, id: Any) -> ModelType | None:
        """Retrieve a record by its primary key."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Retrieve all records with optional pagination."""
        pass

    @abstractmethod
    async def create(self, obj_in: dict[str, Any] | ModelType) -> ModelType:
        """Create a new record."""
        pass

    @abstractmethod
    async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """Update an existing record."""
        pass

    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Delete a record by its primary key."""
        pass

    @abstractmethod
    async def exists(self, id: Any) -> bool:
        """Check if a record exists by its primary key."""
        pass
