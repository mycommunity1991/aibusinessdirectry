"""
Read-only Category exposure (CTG-001, AC5).

Two plain, real methods -- no `api.py`/HTTP route in this story
(Decision 3, `Plan_S07_CTG-001.md`): the implementation is fully real,
backed by the full CTO-approved seeded taxonomy, but there is no real
caller yet (`AI-001`, the eventual Conversation/AI Intake module, has
not been built). Both methods return raw ORM entities, matching this
codebase's established precedent for cross-module service-to-service
reads (`ProviderService.list_by_ids` returning raw `Provider` rows to
`AdminVerificationService`, VER-002) -- a Pydantic response schema is
what an HTTP layer needs, and there is no HTTP layer here.
"""

import uuid

from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository


class CategoryService:
    """Read-only access to the Category taxonomy for a future
    cross-module consumer (`AI-001`)."""

    def __init__(
        self,
        category_repository: CategoryRepository,
        category_question_template_repository: CategoryQuestionTemplateRepository,
    ) -> None:
        self.category_repository = category_repository
        self.category_question_template_repository = (
            category_question_template_repository
        )

    async def list_active_categories(self) -> list[Category]:
        """All 14 launch categories, ordered by `sort_order` -- the
        category-resolution read a future `AI-001` needs."""
        return await self.category_repository.list_active()

    async def get_question_templates(
        self, category_id: uuid.UUID
    ) -> list[CategoryQuestionTemplate]:
        """
        A category's follow-up question templates, ordered by
        `sort_order` -- the follow-up-question read a future `AI-001`
        needs. Returns an empty list for an unknown `category_id`
        rather than raising -- an honest "no questions" answer, not a
        fabricated error, matching the fact there is no HTTP layer here
        to translate an exception into a response for.
        """
        return await self.category_question_template_repository.list_for_category(
            category_id
        )
