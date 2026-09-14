import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.models import ProviderMatch
from app.repositories.base_repository import BaseRepository


class ProviderMatchRepository(BaseRepository[ProviderMatch]):
    """
    Repository for the `search.provider_matches` table (AI-002,
    `Plan_S07_AI-002.md`). Written exactly once per `search_requests`
    row, by `SearchRequestService._finalize_matches` (Decision 4).

    `count_for_provider_between`/`count_daily_for_provider_since`
    (LEAD-002, Backend Proposed Changes item 3, `Plan_S10_LEAD-002.md`)
    are this repository's first per-provider aggregation methods --
    the bounded-range/daily-bucketed source of `contact.
    VisibilityAnalyticsService`'s "search appearances" headline stat and
    chart series (AC1/AC2/AC5, Decision 2's table-reference correction
    away from `search_event_log`, which has no `provider_id` column).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ProviderMatch, session=session)

    async def bulk_create(
        self,
        search_request_id: uuid.UUID,
        ranked_matches: list[tuple[uuid.UUID, float | None]],
    ) -> list[ProviderMatch]:
        """
        Creates one row per `(provider_id, match_score)` pair, `rank` =
        the 1-based position in `ranked_matches` -- the caller's own
        ordering *is* the rank, never re-derived (Decision 4: merit-
        ranked for the automated path, the admin's own supplied order for
        the manual path).

        `match_score` (MAT-001, Decision 3, `Plan_S08_MAT-001.md`) is the
        tuple's second element, populated as-is: a real `[0, 1]` score
        for the automated path (from `ProviderSearchRepository.
        search_nearby`'s `scores_by_id`), or `None` for every row on the
        manual path -- an admin's own judgment produces that order, so no
        formula-derived score is ever fabricated to fill the column
        (anti-fabrication principle, `00_PROJECT_CONTEXT.md` §3).
        """
        rows = [
            ProviderMatch(
                search_request_id=search_request_id,
                provider_id=provider_id,
                rank=rank,
                match_score=match_score,
            )
            for rank, (provider_id, match_score) in enumerate(ranked_matches, start=1)
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_for_search_request(
        self, search_request_id: uuid.UUID
    ) -> list[ProviderMatch]:
        """All matches for a `search_requests` row, ordered by `rank` --
        backs `GET /search-requests/{id}` (Decision 6)."""
        stmt = (
            select(ProviderMatch)
            .where(ProviderMatch.search_request_id == search_request_id)
            .order_by(ProviderMatch.rank.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_provider_between(
        self, provider_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """
        The count of a provider's own `provider_matches` rows with
        `start <= created_at < end` (LEAD-002, Backend Proposed Changes
        item 3) -- `start` is inclusive, `end` is exclusive, so two
        adjacent windows (e.g. the current 30-day window and the
        immediately preceding one, Decision 5) never double-count a row
        that lands exactly on the shared boundary.
        """
        stmt = (
            select(func.count())
            .select_from(ProviderMatch)
            .where(
                ProviderMatch.provider_id == provider_id,
                ProviderMatch.created_at >= start,
                ProviderMatch.created_at < end,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_daily_for_provider_since(
        self, provider_id: uuid.UUID, since: datetime
    ) -> list[tuple[date, int]]:
        """
        One `(day, count)` pair per calendar day with at least one
        `provider_matches` row at or after `since` (Decision 4,
        `Plan_S10_LEAD-002.md`) -- only days that actually have a row
        are returned; `VisibilityAnalyticsService` zero-fills the rest
        in Python. Plain `GROUP BY date_trunc('day', ...)`, deliberately
        not a SQL `generate_series` (Decision 4). `created_at` is
        converted to UTC via `AT TIME ZONE 'UTC'` before truncation, so
        the day boundary is always UTC midnight regardless of the DB
        session's timezone GUC -- matching `VisibilityAnalyticsService`'s
        own explicit `tzinfo=UTC` window boundaries.
        """
        day_column = func.date_trunc(
            "day", ProviderMatch.created_at.op("AT TIME ZONE")("UTC")
        )
        stmt = (
            select(day_column, func.count())
            .select_from(ProviderMatch)
            .where(
                ProviderMatch.provider_id == provider_id,
                ProviderMatch.created_at >= since,
            )
            .group_by(day_column)
        )
        result = await self.session.execute(stmt)
        return [(bucket.date(), int(count)) for bucket, count in result.all()]
