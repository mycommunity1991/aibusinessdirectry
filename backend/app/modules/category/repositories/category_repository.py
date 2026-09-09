from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.category.models import Category
from app.repositories.base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for the `category.categories` table (CTG-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Category, session=session)

    async def list_active(self) -> list[Category]:
        """
        All categories ordered by `sort_order` (CTG-001, AC5) -- the
        category-resolution read `CategoryService.list_active_categories`
        exposes to a future `AI-001` consumer.
        """
        stmt = select(Category).order_by(Category.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
