"""
Integration test for `CategoryRepository.list_by_ids` (LEAD-001, Backend
Proposed Changes item 5, `Plan_S10_LEAD-001.md`) -- no prior dedicated
repository test file existed (`test_category_service.py` exercises
`CategoryRepository` only indirectly, via `CategoryService`).
"""

import uuid

import pytest

from app.modules.category.models import Category
from app.modules.category.repositories.category_repository import CategoryRepository


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_category(db_session, *, name: str) -> Category:
    category = Category(
        name=name,
        name_ar=None,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
        sort_order=0,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


class TestListByIds:
    @pytest.mark.anyio
    async def test_returns_empty_list_for_an_empty_input_list(self, db_session) -> None:
        repository = CategoryRepository(db_session)

        result = await repository.list_by_ids([])

        assert result == []

    @pytest.mark.anyio
    async def test_returns_only_the_matching_rows(self, db_session) -> None:
        plumbing = await _create_category(db_session, name="Plumbing")
        electrical = await _create_category(db_session, name="Electrical")
        # A third category exists but is deliberately not requested.
        await _create_category(db_session, name="Carpentry")

        repository = CategoryRepository(db_session)
        result = await repository.list_by_ids(
            [plumbing.id, electrical.id, uuid.uuid4()]
        )

        assert {row.id for row in result} == {plumbing.id, electrical.id}
