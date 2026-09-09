import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.category.models import CategoryQuestionTemplate
from app.repositories.base_repository import BaseRepository


class CategoryQuestionTemplateRepository(BaseRepository[CategoryQuestionTemplate]):
    """Repository for the `category.category_question_templates` table
    (CTG-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=CategoryQuestionTemplate, session=session)

    async def list_for_category(
        self, category_id: uuid.UUID
    ) -> list[CategoryQuestionTemplate]:
        """
        A category's follow-up question templates, ordered by
        `sort_order` (CTG-001, AC5) -- the follow-up-question read
        `CategoryService.get_question_templates` exposes to a future
        `AI-001` consumer. Returns an empty list for a `category_id`
        with no question templates (including an unknown/nonexistent
        one), never raises.
        """
        stmt = (
            select(CategoryQuestionTemplate)
            .where(CategoryQuestionTemplate.category_id == category_id)
            .order_by(CategoryQuestionTemplate.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
