"""
Integration tests for `VisibilityAnalyticsService` (LEAD-002, AC1/AC3/
AC4/AC5, `Plan_S10_LEAD-002.md`) -- this story's correctness-critical
core. Decision 5 (three-state trend comparison, including the specific
zero-baseline handling) and Decision 6 (`has_sufficient_data`'s gate)
are each tested separately, per the Plan's own explicit instruction
(mirrors `test_lead_service.py`'s identical "explicit, separately-named
test cases" precedent) -- five separately-named trend cases, three
separately-named `has_sufficient_data` cases.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.core.exceptions import ProviderNotFoundError
from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.schemas import TrendDirection
from app.modules.contact.services.visibility_analytics_service import (
    VisibilityAnalyticsService,
)
from app.modules.search.models import ProviderMatch, SearchRequest, SearchRequestStatus
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_provider_service,
)

_WINDOW_DAYS = settings.VISIBILITY_ANALYTICS_WINDOW_DAYS


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_visibility_analytics_service(db_session) -> VisibilityAnalyticsService:
    return VisibilityAnalyticsService(
        contact_view_repository=ContactViewRepository(db_session),
        provider_match_repository=ProviderMatchRepository(db_session),
        provider_service=make_provider_service(db_session),
    )


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


async def _create_provider_match(
    db_session,
    *,
    customer_id: uuid.UUID,
    provider_id: uuid.UUID,
    created_at: datetime,
) -> ProviderMatch:
    """
    Each `provider_matches` row needs its own `search_requests` row
    (`uq_provider_matches_request_provider` allows at most one row per
    `(search_request_id, provider_id)` pair) -- mirrors
    `test_provider_match_repository.py`'s identical one-search-request-
    per-row shape.
    """
    search_request = SearchRequest(
        customer_id=customer_id, status=SearchRequestStatus.MATCHED
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)

    provider_match = ProviderMatch(
        search_request_id=search_request.id,
        provider_id=provider_id,
        rank=1,
        match_score=None,
        created_at=created_at,
    )
    db_session.add(provider_match)
    await db_session.commit()
    await db_session.refresh(provider_match)
    return provider_match


class TestOwnershipNoProvider:
    """AC3: a caller with no Provider at all has nothing to see."""

    @pytest.mark.anyio
    async def test_raises_provider_not_found_for_a_caller_with_no_provider(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000001")
        await create_customer_profile(db_session, customer_user)
        service = make_visibility_analytics_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.get_my_visibility_analytics(customer_user.id)


class TestOwnershipCrossProviderBoundary:
    """AC3's direct, explicit ownership-boundary test -- a fixture with
    Contact Views and `provider_matches` rows against both Provider A
    and Provider B asserts Provider A's totals reflect only Provider
    A's own rows."""

    @pytest.mark.anyio
    async def test_provider_a_never_reflects_provider_bs_activity(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000002")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "605000003")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "605000004")
        provider_b = await create_provider(db_session, user=provider_b_owner)
        now = datetime.now(UTC)

        # Provider A: 2 contact views, 3 search appearances, all
        # squarely inside the current window.
        for _ in range(2):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider_a.id,
                viewed_at=now - timedelta(days=5),
            )
        for _ in range(3):
            await _create_provider_match(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider_a.id,
                created_at=now - timedelta(days=5),
            )
        # Provider B: a different, larger number of rows -- must never
        # leak into Provider A's totals.
        for _ in range(9):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider_b.id,
                viewed_at=now - timedelta(days=5),
            )
        for _ in range(7):
            await _create_provider_match(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider_b.id,
                created_at=now - timedelta(days=5),
            )

        service = make_visibility_analytics_service(db_session)
        analytics_a = await service.get_my_visibility_analytics(provider_a_owner.id)

        assert analytics_a.contact_views.total_last_30_days == 2
        assert analytics_a.search_appearances.total_last_30_days == 3


class TestHeadlineAggregationCorrectness:
    """AC5: `total_last_30_days` reflects exactly the in-window count,
    never the all-time count -- a fixture with rows inside the current
    window, inside the previous window, and further back than both."""

    @pytest.mark.anyio
    async def test_total_last_30_days_excludes_rows_outside_the_current_window(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000005")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000006")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        # 2 rows inside the current window (0-30 days ago).
        for offset_days in (3, 10):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=offset_days),
            )
            await _create_provider_match(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                created_at=now - timedelta(days=offset_days),
            )
        # 1 row inside the previous window (30-60 days ago).
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=45),
        )
        await _create_provider_match(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            created_at=now - timedelta(days=45),
        )
        # 1 row further back than both windows.
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=90),
        )
        await _create_provider_match(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            created_at=now - timedelta(days=90),
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.total_last_30_days == 2
        assert analytics.search_appearances.total_last_30_days == 2


class TestTrendBothZero:
    """Decision 5: previous=0, current=0 -> `FLAT` (no real rows in
    either window)."""

    @pytest.mark.anyio
    async def test_previous_zero_and_current_zero_is_flat(self, db_session) -> None:
        provider_owner = await create_user(db_session, "605000007")
        await create_provider(db_session, user=provider_owner)
        service = make_visibility_analytics_service(db_session)

        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.trend == TrendDirection.FLAT


class TestTrendUpFromZeroBaseline:
    """Decision 5: previous=0, current>0 -> `UP` (a real increase from a
    real zero baseline, never a fabricated percentage)."""

    @pytest.mark.anyio
    async def test_previous_zero_and_current_positive_is_up(self, db_session) -> None:
        customer_user = await create_user(db_session, "605000008")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000009")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.trend == TrendDirection.UP


class TestTrendUpBeyondThreshold:
    """Decision 5: previous>0 with a >10% increase -> `UP`."""

    @pytest.mark.anyio
    async def test_previous_positive_with_a_large_increase_is_up(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000010")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000011")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        for _ in range(10):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=45),
            )
        for _ in range(15):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=5),
            )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.trend == TrendDirection.UP


class TestTrendDownBeyondThreshold:
    """Decision 5: previous>0 with a >10% decrease -> `DOWN`."""

    @pytest.mark.anyio
    async def test_previous_positive_with_a_large_decrease_is_down(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000012")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000013")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        for _ in range(10):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=45),
            )
        for _ in range(8):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=5),
            )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.trend == TrendDirection.DOWN


class TestTrendFlatWithinThreshold:
    """Decision 5: previous>0, within +/-10% -> `FLAT`."""

    @pytest.mark.anyio
    async def test_previous_positive_with_a_small_change_is_flat(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000014")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000015")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        for _ in range(10):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=45),
            )
        # +10% exactly -- within the +/-10% threshold band, inclusive.
        for _ in range(11):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=5),
            )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.contact_views.trend == TrendDirection.FLAT


class TestHasSufficientDataBothZero:
    """Decision 6: both current-window totals are `0` -> `false`."""

    @pytest.mark.anyio
    async def test_both_totals_zero_is_insufficient(self, db_session) -> None:
        provider_owner = await create_user(db_session, "605000016")
        await create_provider(db_session, user=provider_owner)
        service = make_visibility_analytics_service(db_session)

        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.has_sufficient_data is False
        assert analytics.contact_views.total_last_30_days == 0
        assert analytics.search_appearances.total_last_30_days == 0
        assert len(analytics.daily_trend) == _WINDOW_DAYS


class TestHasSufficientDataOnlyOneMetricNonZero:
    """Decision 6: only one of the two current-window totals is
    positive -> `true`."""

    @pytest.mark.anyio
    async def test_one_nonzero_metric_is_sufficient(self, db_session) -> None:
        customer_user = await create_user(db_session, "605000017")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000018")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.has_sufficient_data is True
        assert analytics.search_appearances.total_last_30_days == 0


class TestHasSufficientDataBothNonZero:
    """Decision 6: both current-window totals are positive -> `true`."""

    @pytest.mark.anyio
    async def test_both_nonzero_metrics_are_sufficient(self, db_session) -> None:
        customer_user = await create_user(db_session, "605000019")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000020")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )
        await _create_provider_match(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            created_at=now - timedelta(days=5),
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert analytics.has_sufficient_data is True


class TestDailySeriesHeadlineTotalDivergence:
    """
    Investigates the `_build_daily_series` anchoring deviation flagged in
    the service module's own docstring (`Plan_S10_LEAD-002.md`, Decision
    4): the chart's 30-day window is anchored on calendar dates ending
    "today" (`window_start = today - (window_days - 1)` through `today`),
    while the headline `total_last_30_days` is anchored on the exact
    timestamp window `[current_start, now)`. Because `date(current_start)`
    is always exactly one calendar day *before* `window_start` (both are
    derived from the same `now` with a fixed `window_days`-day offset --
    subtracting a whole number of days never changes the time-of-day, so
    this holds regardless of what time of day the request happens to
    land on), any row whose `created_at`/`viewed_at` falls on
    `current_start`'s own calendar day is counted in the headline total
    but never appears anywhere in the 30-entry chart series. This test
    proves that divergence is real and reproducible, not merely
    theoretical -- flagged for `backend` to decide how (or whether) to
    reconcile it; not fixed here (test-only boundary).
    """

    @pytest.mark.anyio
    async def test_a_row_on_current_starts_calendar_day_never_appears_in_the_chart(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000023")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000024")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)
        current_start = now - timedelta(days=_WINDOW_DAYS)
        # A small forward buffer past this test's own `current_start`:
        # the service recomputes its own `now` (and therefore its own,
        # very slightly later, `current_start`) at call time, so a row
        # placed at exactly this test's `current_start` can otherwise
        # land just *before* the service's actual boundary and be
        # excluded from the headline count entirely, which would falsify
        # this test for the wrong reason. Two seconds safely covers that
        # gap without risking crossing into the next calendar day.
        row_timestamp = current_start + timedelta(seconds=2)

        # Squarely on the current window's own start boundary's calendar
        # day (inclusive, per `count_for_provider_between`'s `>= start`
        # semantics) -- the oldest possible calendar day still inside the
        # headline window.
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=row_timestamp,
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        chart_sum = sum(point.contact_views for point in analytics.daily_trend)
        chart_days = {point.day for point in analytics.daily_trend}

        # The headline total counts this row...
        assert analytics.contact_views.total_last_30_days == 1
        # ...but its own calendar day is never one of the chart's 30
        # entries...
        assert row_timestamp.date() not in chart_days
        # ...so the chart's own 30-day sum silently diverges from the
        # headline total a provider sees directly alongside it on screen.
        assert chart_sum == 0
        assert chart_sum != analytics.contact_views.total_last_30_days


class TestDailySeriesZeroFill:
    """Decision 4: a fixture with events on only 2 of the 30 days
    asserts the returned series has exactly 30 ascending-date entries,
    the 2 populated days carry the right counts, the other 28 are `0`."""

    @pytest.mark.anyio
    async def test_series_has_30_ascending_entries_zero_filled_around_two_real_days(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "605000021")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "605000022")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)
        populated_day_one = (now - timedelta(days=20)).date()
        populated_day_two = (now - timedelta(days=5)).date()

        for _ in range(2):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(days=20),
            )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )

        service = make_visibility_analytics_service(db_session)
        analytics = await service.get_my_visibility_analytics(provider_owner.id)

        assert len(analytics.daily_trend) == _WINDOW_DAYS
        assert [point.day for point in analytics.daily_trend] == sorted(
            point.day for point in analytics.daily_trend
        )

        counts_by_day = {
            point.day: point.contact_views for point in analytics.daily_trend
        }
        assert counts_by_day[populated_day_one] == 2
        assert counts_by_day[populated_day_two] == 1

        zero_days = [
            count
            for day, count in counts_by_day.items()
            if day not in (populated_day_one, populated_day_two)
        ]
        assert len(zero_days) == _WINDOW_DAYS - 2
        assert all(count == 0 for count in zero_days)
