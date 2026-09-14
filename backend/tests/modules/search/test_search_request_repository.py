"""
Integration test for `SearchRequestRepository.list_by_ids` (LEAD-001,
Backend Proposed Changes item 3, `Plan_S10_LEAD-001.md`) -- no prior
test file existed for this repository's read methods.
"""

import uuid

import pytest

from app.modules.search.models import SearchRequest, SearchRequestStatus
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)

from ._helpers import create_customer_profile, create_user


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_search_request(db_session, customer_id: uuid.UUID) -> SearchRequest:
    search_request = SearchRequest(
        customer_id=customer_id,
        status=SearchRequestStatus.MATCHED,
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)
    return search_request


class TestListByIds:
    @pytest.mark.anyio
    async def test_returns_empty_list_for_an_empty_input_list(self, db_session) -> None:
        repository = SearchRequestRepository(db_session)

        result = await repository.list_by_ids([])

        assert result == []

    @pytest.mark.anyio
    async def test_returns_only_the_matching_rows(self, db_session) -> None:
        customer_user = await create_user(db_session, "601300001")
        customer_profile = await create_customer_profile(db_session, customer_user)
        first = await _create_search_request(db_session, customer_profile.id)
        second = await _create_search_request(db_session, customer_profile.id)
        # A third row exists but is deliberately not requested.
        await _create_search_request(db_session, customer_profile.id)

        repository = SearchRequestRepository(db_session)
        result = await repository.list_by_ids([first.id, second.id, uuid.uuid4()])

        assert {row.id for row in result} == {first.id, second.id}
