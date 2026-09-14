"""
Real-database integration test for `OutcomeTagRepository.
get_by_contact_view_id` (REV-002, Backend Proposed Changes item 7,
`Plan_S09_REV-002.md`) -- the read-only counterpart to `try_create`,
REV-001 never needed and this story's `ReviewService` is the first
consumer of.
"""

import uuid

import pytest

from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_contact_service,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_contact_view(db_session, *, customer_user_id, provider_id):
    contact_service = make_contact_service(db_session)
    contact_view, _provider = await contact_service.create_contact_view(
        customer_user_id, provider_id=provider_id, search_request_id=None
    )
    await db_session.commit()
    return contact_view


class TestGetByContactViewId:
    @pytest.mark.anyio
    async def test_returns_the_correct_row(self, db_session) -> None:
        customer_user = await create_user(db_session, "601000018")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000019")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        repository = OutcomeTagRepository(db_session)
        created = await repository.try_create(
            {"contact_view_id": contact_view.id, "hired": True}
        )
        await db_session.commit()
        assert created is not None

        result = await repository.get_by_contact_view_id(contact_view.id)

        assert result is not None
        assert result.contact_view_id == contact_view.id
        assert result.hired is True

    @pytest.mark.anyio
    async def test_returns_none_for_a_nonexistent_contact_view_id(
        self, db_session
    ) -> None:
        repository = OutcomeTagRepository(db_session)

        result = await repository.get_by_contact_view_id(uuid.uuid4())

        assert result is None


class TestListByContactViewIds:
    """LEAD-001, Backend Proposed Changes item 4, `Plan_S10_LEAD-001.md`
    -- the batch counterpart to `get_by_contact_view_id`."""

    @pytest.mark.anyio
    async def test_returns_empty_list_for_an_empty_input_list(self, db_session) -> None:
        repository = OutcomeTagRepository(db_session)

        result = await repository.list_by_contact_view_ids([])

        assert result == []

    @pytest.mark.anyio
    async def test_returns_only_the_matching_rows_for_a_partial_match(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601200001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601200002")
        provider = await create_provider(db_session, user=provider_owner)
        tagged_contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        untagged_contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        repository = OutcomeTagRepository(db_session)
        await repository.try_create(
            {"contact_view_id": tagged_contact_view.id, "hired": True}
        )
        await db_session.commit()

        result = await repository.list_by_contact_view_ids(
            [tagged_contact_view.id, untagged_contact_view.id, uuid.uuid4()]
        )

        assert len(result) == 1
        assert result[0].contact_view_id == tagged_contact_view.id

    @pytest.mark.anyio
    async def test_returns_every_row_for_a_full_match(self, db_session) -> None:
        customer_user = await create_user(db_session, "601200003")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601200004")
        provider = await create_provider(db_session, user=provider_owner)
        first_contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        second_contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        repository = OutcomeTagRepository(db_session)
        await repository.try_create(
            {"contact_view_id": first_contact_view.id, "hired": True}
        )
        await repository.try_create(
            {"contact_view_id": second_contact_view.id, "hired": False}
        )
        await db_session.commit()

        result = await repository.list_by_contact_view_ids(
            [first_contact_view.id, second_contact_view.id]
        )

        assert {tag.contact_view_id for tag in result} == {
            first_contact_view.id,
            second_contact_view.id,
        }
