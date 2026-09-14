"""
Real-database integration tests for `ContactViewRepository.
list_for_provider`/`count_for_provider` (LEAD-001, Backend Proposed
Changes item 2, `Plan_S10_LEAD-001.md`) -- this repository's first
custom methods (no prior test file existed for it, since it previously
had none).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)

from ._helpers import create_customer_profile, create_provider, create_user


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_contact_view(
    db_session,
    *,
    customer_id: uuid.UUID,
    provider_id: uuid.UUID,
    viewed_at: datetime,
) -> ContactView:
    contact_view = ContactView(
        customer_id=customer_id,
        provider_id=provider_id,
        search_request_id=None,
        viewed_at=viewed_at,
    )
    db_session.add(contact_view)
    await db_session.commit()
    await db_session.refresh(contact_view)
    return contact_view


class TestListForProviderOrdering:
    @pytest.mark.anyio
    async def test_returns_rows_most_recent_first(self, db_session) -> None:
        customer_user = await create_user(db_session, "601100001")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601100002")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        oldest = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=2),
        )
        middle = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=1),
        )
        newest = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now,
        )

        repository = ContactViewRepository(db_session)
        rows = await repository.list_for_provider(provider.id, limit=10, offset=0)

        assert [row.id for row in rows] == [newest.id, middle.id, oldest.id]

    @pytest.mark.anyio
    async def test_uses_id_asc_as_the_deterministic_tie_break(self, db_session) -> None:
        customer_user = await create_user(db_session, "601100003")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601100004")
        provider = await create_provider(db_session, user=provider_owner)
        shared_timestamp = datetime.now(UTC)

        first = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=shared_timestamp,
        )
        second = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=shared_timestamp,
        )
        expected_order = sorted([first.id, second.id])

        repository = ContactViewRepository(db_session)
        rows = await repository.list_for_provider(provider.id, limit=10, offset=0)

        assert [row.id for row in rows] == expected_order


class TestListForProviderScoping:
    @pytest.mark.anyio
    async def test_never_returns_another_providers_contact_views(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601100005")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "601100006")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "601100007")
        provider_b = await create_provider(db_session, user=provider_b_owner)
        now = datetime.now(UTC)

        a_view = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_a.id,
            viewed_at=now,
        )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_b.id,
            viewed_at=now,
        )

        repository = ContactViewRepository(db_session)
        rows = await repository.list_for_provider(provider_a.id, limit=10, offset=0)

        assert [row.id for row in rows] == [a_view.id]

    @pytest.mark.anyio
    async def test_returns_empty_list_for_a_provider_with_no_contact_views(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "601100008")
        provider = await create_provider(db_session, user=provider_owner)

        repository = ContactViewRepository(db_session)
        rows = await repository.list_for_provider(provider.id, limit=10, offset=0)

        assert rows == []


class TestListForProviderPagination:
    @pytest.mark.anyio
    async def test_limit_and_offset_slice_the_ordered_result(self, db_session) -> None:
        customer_user = await create_user(db_session, "601100009")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601100010")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        created = []
        for offset_days in range(5):
            created.append(
                await _create_contact_view(
                    db_session,
                    customer_id=customer_profile.id,
                    provider_id=provider.id,
                    viewed_at=now - timedelta(days=offset_days),
                )
            )
        # `created` is oldest-appended-last-created; most-recent-first
        # order matches `created` itself (index 0 = today, viewed most
        # recently).

        repository = ContactViewRepository(db_session)
        page_one = await repository.list_for_provider(provider.id, limit=2, offset=0)
        page_two = await repository.list_for_provider(provider.id, limit=2, offset=2)

        assert [row.id for row in page_one] == [created[0].id, created[1].id]
        assert [row.id for row in page_two] == [created[2].id, created[3].id]


class TestCountForProvider:
    @pytest.mark.anyio
    async def test_counts_only_the_given_providers_rows(self, db_session) -> None:
        customer_user = await create_user(db_session, "601100011")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "601100012")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "601100013")
        provider_b = await create_provider(db_session, user=provider_b_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_a.id,
            viewed_at=now,
        )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_a.id,
            viewed_at=now,
        )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_b.id,
            viewed_at=now,
        )

        repository = ContactViewRepository(db_session)

        assert await repository.count_for_provider(provider_a.id) == 2
        assert await repository.count_for_provider(provider_b.id) == 1

    @pytest.mark.anyio
    async def test_returns_zero_for_a_provider_with_no_contact_views(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "601100014")
        provider = await create_provider(db_session, user=provider_owner)

        repository = ContactViewRepository(db_session)

        assert await repository.count_for_provider(provider.id) == 0
