"""
`VisibilityAnalyticsService` (LEAD-002, Backend Proposed Changes item 4,
`Plan_S10_LEAD-002.md`) -- surfaces a provider's own "search appearances"
(`search.provider_matches`) and "contact views" (`contact.contact_views`)
as two headline stats, each with a three-state trend indicator (Decision
5), plus a zero-filled 30-day daily series (Decision 4) and a "not
enough data yet" gate (Decision 6). Carries **zero** customer-
identifying or per-event field (Decision 8) -- pure aggregate counts
only.

New cross-module edge for `contact`: `search.ProviderMatchRepository`
(new) -- a **second** instance of the already-recorded ADR-047
raw-Repository exception, alongside the existing `search.
SearchRequestRepository` edge (`LeadService`, `Plan_S10_LEAD-001.md`):
neither `SearchRequestService` nor any other `search`-module Service
exposes a per-provider aggregation primitive today, so there is no
equivalent Service method to depend on instead. `provider.
ProviderService` is reused unchanged (the same ownership-resolution
primitive `LeadService`/`PortfolioService` already use).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.core.config import settings
from app.core.exceptions import ProviderNotFoundError
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.schemas import TrendDirection
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)


@dataclass(frozen=True)
class VisibilityDailyPointData:
    """One zero-filled day of the 30-day daily series (Decision 4)."""

    day: date
    search_appearances: int
    contact_views: int


@dataclass(frozen=True)
class VisibilityMetricData:
    """One headline stat's current-window total plus its three-state
    trend (Decision 5)."""

    total_last_30_days: int
    trend: TrendDirection


@dataclass(frozen=True)
class VisibilityAnalyticsData:
    """
    The service layer's raw domain data for `GET /providers/me/
    visibility-analytics` -- the API layer builds
    `VisibilityAnalyticsResponse` from this (mirrors `LeadService`'s own
    "service returns raw domain data, API layer builds the schema"
    convention).
    """

    has_sufficient_data: bool
    search_appearances: VisibilityMetricData
    contact_views: VisibilityMetricData
    daily_trend: list[VisibilityDailyPointData]


def _trend_for(*, current_total: int, previous_total: int) -> TrendDirection:
    """
    Decision 5's exact three-state comparison of `current_total` (the
    current 30-day window) against `previous_total` (the immediately
    preceding 30-day window):

    - `previous_total == 0`: `FLAT` if `current_total` is also `0` (no
      change -- both are genuinely zero); otherwise `UP` (a real
      increase from a real zero baseline, stated directionally, never as
      a percentage that would require dividing by zero).
    - `previous_total > 0`: the percentage change is bucketed against
      `settings.VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT` -- `FLAT`
      within +/- the threshold, `UP`/`DOWN` otherwise.
    """
    if previous_total == 0:
        return TrendDirection.FLAT if current_total == 0 else TrendDirection.UP

    percent_change = ((current_total - previous_total) / previous_total) * 100
    threshold = settings.VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT
    if abs(percent_change) <= threshold:
        return TrendDirection.FLAT
    return TrendDirection.UP if percent_change > 0 else TrendDirection.DOWN


def _build_daily_series(
    *,
    today: date,
    window_days: int,
    search_appearances_by_day: dict[date, int],
    contact_views_by_day: dict[date, int],
) -> list[VisibilityDailyPointData]:
    """
    Assembles the full, zero-filled, ascending-date daily series
    (Decision 4) -- exactly `window_days` calendar-day entries, ending
    with `today` (inclusive) and going back `window_days - 1` more days,
    the literal, unsurprising reading of "the last 30 days" a chart's
    caller expects (today's own activity always visible, never dropped
    off the end). Each day is looked up in the two (sparse) day->count
    maps built from the repositories' `count_daily_for_provider_since`
    rows, defaulting to `0`.

    `today` is anchored on the same midnight-aligned calendar day as the
    headline stats' own `current_start` (`get_my_visibility_analytics`
    computes `current_start` as midnight on `today - (window_days - 1)`
    days), so `window_start` here always equals `date(current_start)`
    exactly -- the chart's 30 daily buckets and the headline
    `total_last_30_days` are always drawn from the identical calendar-
    day window, and `total_last_30_days` always exactly equals the sum
    of this series' own counts for that metric.
    """
    window_start = today - timedelta(days=window_days - 1)
    days = (window_start + timedelta(days=offset) for offset in range(window_days))
    return [
        VisibilityDailyPointData(
            day=day,
            search_appearances=search_appearances_by_day.get(day, 0),
            contact_views=contact_views_by_day.get(day, 0),
        )
        for day in days
    ]


class VisibilityAnalyticsService:
    """Orchestrates a provider's own Visibility Analytics (AC1-AC5)."""

    def __init__(
        self,
        contact_view_repository: ContactViewRepository,
        provider_match_repository: ProviderMatchRepository,
        provider_service: ProviderService,
    ) -> None:
        self.contact_view_repository = contact_view_repository
        self.provider_match_repository = provider_match_repository
        self.provider_service = provider_service

    async def get_my_visibility_analytics(
        self, user_id: uuid.UUID
    ) -> VisibilityAnalyticsData:
        """
        Returns the caller's own Visibility Analytics, scoped strictly
        to their own Provider (AC3).

        Raises `ProviderNotFoundError` if the caller has not yet created
        a Provider listing -- mirrors `LeadService.list_my_leads`'s
        identical `_get_provider_or_404`-shaped guard.
        """
        provider = await self.provider_service.get_my_provider(user_id)
        if provider is None:
            raise ProviderNotFoundError()

        window_days = settings.VISIBILITY_ANALYTICS_WINDOW_DAYS
        now = datetime.now(UTC)
        today = now.date()
        # Midnight-aligned to the same calendar day the 30-day chart's
        # own `window_start` begins (`_build_daily_series`), not an
        # exact-timestamp offset from `now` -- otherwise `current_start`
        # falls exactly one calendar day before the chart's earliest
        # visible day, and any row on that boundary day is counted in
        # the headline total but can never appear in the chart series.
        # `previous_start` mirrors the same midnight alignment, exactly
        # `window_days` calendar days before `current_start`, giving a
        # clean, non-overlapping, calendar-day-aligned previous window.
        current_start = datetime.combine(
            today - timedelta(days=window_days - 1), time.min, tzinfo=UTC
        )
        previous_start = datetime.combine(
            today - timedelta(days=(2 * window_days) - 1), time.min, tzinfo=UTC
        )

        contact_views_current_total = (
            await self.contact_view_repository.count_for_provider_between(
                provider.id, current_start, now
            )
        )
        contact_views_previous_total = (
            await self.contact_view_repository.count_for_provider_between(
                provider.id, previous_start, current_start
            )
        )
        search_appearances_current_total = (
            await self.provider_match_repository.count_for_provider_between(
                provider.id, current_start, now
            )
        )
        search_appearances_previous_total = (
            await self.provider_match_repository.count_for_provider_between(
                provider.id, previous_start, current_start
            )
        )

        contact_views_daily_rows = (
            await self.contact_view_repository.count_daily_for_provider_since(
                provider.id, current_start
            )
        )
        search_appearances_daily_rows = (
            await self.provider_match_repository.count_daily_for_provider_since(
                provider.id, current_start
            )
        )

        daily_trend = _build_daily_series(
            today=today,
            window_days=window_days,
            search_appearances_by_day=dict(search_appearances_daily_rows),
            contact_views_by_day=dict(contact_views_daily_rows),
        )

        has_sufficient_data = (
            search_appearances_current_total > 0 or contact_views_current_total > 0
        )

        return VisibilityAnalyticsData(
            has_sufficient_data=has_sufficient_data,
            search_appearances=VisibilityMetricData(
                total_last_30_days=search_appearances_current_total,
                trend=_trend_for(
                    current_total=search_appearances_current_total,
                    previous_total=search_appearances_previous_total,
                ),
            ),
            contact_views=VisibilityMetricData(
                total_last_30_days=contact_views_current_total,
                trend=_trend_for(
                    current_total=contact_views_current_total,
                    previous_total=contact_views_previous_total,
                ),
            ),
            daily_trend=daily_trend,
        )
