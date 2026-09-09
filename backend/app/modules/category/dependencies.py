"""Dependency-injection providers for the Category module.

No HTTP route consumes this chain in this story (Decision 3,
`Plan_S07_CTG-001.md`) -- it exists so a future `AI-001` module can add
a one-directional `ai_intake -> category` cross-module edge via
constructor injection, the same DI-provider shape every other module
already uses.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.category.services.category_service import CategoryService


def get_category_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryRepository:
    """Provides a `CategoryRepository` bound to the request-scoped DB
    session."""
    return CategoryRepository(db)


def get_category_question_template_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryQuestionTemplateRepository:
    """Provides a `CategoryQuestionTemplateRepository` bound to the
    request-scoped DB session."""
    return CategoryQuestionTemplateRepository(db)


def get_category_service(
    category_repository: Annotated[
        CategoryRepository, Depends(get_category_repository)
    ],
    category_question_template_repository: Annotated[
        CategoryQuestionTemplateRepository,
        Depends(get_category_question_template_repository),
    ],
) -> CategoryService:
    """Provides a `CategoryService` bound to the request-scoped DB
    session."""
    return CategoryService(
        category_repository, category_question_template_repository
    )
