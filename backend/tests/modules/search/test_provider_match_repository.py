"""
Real-database integration tests for `ProviderMatchRepository.
count_for_provider_between`/`count_daily_for_provider_since` (LEAD-002,
Backend Proposed Changes item 3, Tests item 9, `Plan_S10_LEAD-002.md`)
-- this repository's first per-provider aggregation methods (previously
only `bulk_create`/`list_for_search_request` existed). Inclusive/
exclusive window-boundary edge cases, cross-provider isolation, and
zero-row cases, mirroring `test_contact_view_repository.py`'s mirrored
pair exactly.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.identity.models import User
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.search.models import ProviderMatch, SearchRequest, SearchRequestStatus
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)

from ._helpers import create_customer_profile, create_user


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_provider(db_session, *, user: User) -> Provider:
    """Mirrors `tests/modules/contact/_helpers.py`'s identical
    `create_provider` -- not reused directly since `search/_helpers.py`
    exposes no equivalent (only the heavier `create_discoverable_
    provider`, which this file's window-boundary tests don't need)."""
    provider = Provider(
        user_id=user.id,
        provider_type=ProviderType.BUSINESS,
        display_name="Al Noor Plumbing Services LLC",
        slug=f"al-noor-plumbing-{uuid.uuid4().hex[:8]}",
        phone_country_code="+971",
        phone_number="43334455",
        whatsapp_number="43334455",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


async def _create_search_request(
    db_session, *, customer_id: uuid.UUID
) -> SearchRequest:
    search_request = SearchRequest(
        customer_id=customer_id,
        status=SearchRequestStatus.MATCHED,
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)
    return search_request


async def _create_provider_match(
    db_session,
    *,
    search_request_id: uuid.UUID,
    provider_id: uuid.UUID,
    created_at: datetime,
    rank: int = 1,
) -> ProviderMatch:
    provider_match = ProviderMatch(
        search_request_id=search_request_id,
        provider_id=provider_id,
        rank=rank,
        match_score=None,
        created_at=created_at,
    )
    db_session.add(provider_match)
    await db_session.commit()
    await db_session.refresh(provider_match)
    return provider_match


class TestCountForProviderBetween:
    @pytest.mark.anyio
    async def test_start_boundary_is_inclusive(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100001")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "604100002")
        provider = await _create_provider(db_session, user=provider_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id
        )
        start = datetime.now(UTC)
        end = start + timedelta(days=1)

        await _create_provider_match(
            db_session,
            search_request_id=search_request.id,
            provider_id=provider.id,
            created_at=start,
        )

        repository = ProviderMatchRepository(db_session)

        assert (
            await repository.count_for_provider_between(provider.id, start, end) == 1
        )

    @pytest.mark.anyio
    async def test_end_boundary_is_exclusive(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100003")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "604100004")
        provider = await _create_provider(db_session, user=provider_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id
        )
        start = datetime.now(UTC)
        end = start + timedelta(days=1)

        await _create_provider_match(
            db_session,
            search_request_id=search_request.id,
            provider_id=provider.id,
            created_at=end,
        )

        repository = ProviderMatchRepository(db_session)

        assert (
            await repository.count_for_provider_between(provider.id, start, end) == 0
        )

    @pytest.mark.anyio
    async def test_rows_outside_the_window_are_never_counted(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "604100005")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "604100006")
        provider = await _create_provider(db_session, user=provider_owner)
        start = datetime.now(UTC)
        end = start + timedelta(days=30)

        # `uq_provider_matches_request_provider` allows at most one row
        # per `(search_request_id, provider_id)` pair -- each row here
        # needs its own `search_requests` row, mirroring the real
        # "one appearance per search" shape.
        for created_at in (
            start - timedelta(seconds=1),
            end + timedelta(seconds=1),
            start + timedelta(days=15),
        ):
            search_request = await _create_search_request(
                db_session, customer_id=customer_profile.id
            )
            await _create_provider_match(
                db_session,
                search_request_id=search_request.id,
                provider_id=provider.id,
                created_at=created_at,
            )

        repository = ProviderMatchRepository(db_session)

        assert (
            await repository.count_for_provider_between(provider.id, start, end) == 1
        )

    @pytest.mark.anyio
    async def test_never_counts_another_providers_rows(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100007")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "604100008")
        provider_a = await _create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "604100009")
        provider_b = await _create_provider(db_session, user=provider_b_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id
        )
        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC) + timedelta(days=1)

        await _create_provider_match(
            db_session,
            search_request_id=search_request.id,
            provider_id=provider_b.id,
            created_at=datetime.now(UTC),
        )

        repository = ProviderMatchRepository(db_session)

        assert (
            await repository.count_for_provider_between(provider_a.id, start, end)
            == 0
        )

    @pytest.mark.anyio
    async def test_returns_zero_for_a_provider_with_no_rows_in_range(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "604100010")
        provider = await _create_provider(db_session, user=provider_owner)
        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC) + timedelta(days=1)

        repository = ProviderMatchRepository(db_session)

        assert (
            await repository.count_for_provider_between(provider.id, start, end) == 0
        )


class TestCountDailyForProviderSince:
    @pytest.mark.anyio
    async def test_returns_only_days_with_at_least_one_row(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100011")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "604100012")
        provider = await _create_provider(db_session, user=provider_owner)
        since = datetime.now(UTC) - timedelta(days=10)
        day_one = since + timedelta(days=1)
        day_five = since + timedelta(days=5)

        # `uq_provider_matches_request_provider` allows at most one row
        # per `(search_request_id, provider_id)` pair -- each row here
        # needs its own `search_requests` row.
        for created_at in (day_one, day_one + timedelta(hours=2), day_five):
            search_request = await _create_search_request(
                db_session, customer_id=customer_profile.id
            )
            await _create_provider_match(
                db_session,
                search_request_id=search_request.id,
                provider_id=provider.id,
                created_at=created_at,
            )

        repository = ProviderMatchRepository(db_session)
        rows = await repository.count_daily_for_provider_since(provider.id, since)
        counts_by_day = dict(rows)

        assert len(counts_by_day) == 2
        assert counts_by_day[day_one.date()] == 2
        assert counts_by_day[day_five.date()] == 1

    @pytest.mark.anyio
    async def test_rows_before_since_are_excluded(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100013")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "604100014")
        provider = await _create_provider(db_session, user=provider_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id
        )
        since = datetime.now(UTC)

        await _create_provider_match(
            db_session,
            search_request_id=search_request.id,
            provider_id=provider.id,
            created_at=since - timedelta(seconds=1),
        )

        repository = ProviderMatchRepository(db_session)
        rows = await repository.count_daily_for_provider_since(provider.id, since)

        assert rows == []

    @pytest.mark.anyio
    async def test_never_returns_another_providers_rows(self, db_session) -> None:
        customer_user = await create_user(db_session, "604100015")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "604100016")
        provider_a = await _create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "604100017")
        provider_b = await _create_provider(db_session, user=provider_b_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id
        )
        since = datetime.now(UTC) - timedelta(days=1)

        await _create_provider_match(
            db_session,
            search_request_id=search_request.id,
            provider_id=provider_b.id,
            created_at=datetime.now(UTC),
        )

        repository = ProviderMatchRepository(db_session)
        rows = await repository.count_daily_for_provider_since(provider_a.id, since)

        assert rows == []

    @pytest.mark.anyio
    async def test_returns_empty_list_for_a_provider_with_no_rows(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "604100018")
        provider = await _create_provider(db_session, user=provider_owner)
        since = datetime.now(UTC) - timedelta(days=1)

        repository = ProviderMatchRepository(db_session)
        rows = await repository.count_daily_for_provider_since(provider.id, since)

        assert rows == []
