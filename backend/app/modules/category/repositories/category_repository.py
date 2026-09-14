import uuid

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

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Category]:
        """
        Batch-fetches Categories by id in one query (LEAD-001, Backend
        Proposed Changes item 5, `Plan_S10_LEAD-001.md`) -- the same
        `WHERE id IN (...)` batch-fetch shape as `ProviderRepository.
        list_by_ids`/`SearchRequestRepository.list_by_ids`, used by
        `LeadService` to resolve category names for a page of leads'
        `search_requests.category_id`s without an N+1 query.
        """
        if not ids:
            return []
        stmt = select(Category).where(Category.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
