import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contact.models import ContactView
from app.repositories.base_repository import BaseRepository


class ContactViewRepository(BaseRepository[ContactView]):
    """
    Repository for the `contact.contact_views` table (CON-001).
    `ContactService` exposes the one explicit write path this module
    needs today (`create`, inherited from `BaseRepository`); no
    dedup/uniqueness lookup is ever performed (Decision 5,
    `Plan_S08_CON-001.md` -- every Contact tap creates a new row).

    `list_for_provider`/`count_for_provider` (LEAD-001, Backend Proposed
    Changes item 2, `Plan_S10_LEAD-001.md`) are this module's first
    custom read methods -- the paginated, provider-scoped source of a
    provider's own Leads list (AC2/AC4).

    `count_for_provider_between`/`count_daily_for_provider_since`
    (LEAD-002, Backend Proposed Changes item 2, `Plan_S10_LEAD-002.md`)
    are this module's second pair of custom read methods -- the
    bounded-range/daily-bucketed source of `VisibilityAnalyticsService`'s
    "contact views" headline stat and chart series (AC1/AC2/AC5).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ContactView, session=session)

    async def list_for_provider(
        self, provider_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[ContactView]:
        """
        One page of a provider's own Contact Views, most-recent-first
        (AC2) -- `id ASC` is the deterministic tie-break for two rows
        with an identical `viewed_at`, mirroring
        `ProviderSearchRepository`'s own `p.id ASC` tie-break precedent.
        """
        stmt = (
            select(ContactView)
            .where(ContactView.provider_id == provider_id)
            .order_by(ContactView.viewed_at.desc(), ContactView.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_provider(self, provider_id: uuid.UUID) -> int:
        """
        The matching, unpaginated count of a provider's own Contact
        Views, for `PaginationMeta.total_items` -- mirrors
        `ProviderSearchRepository`'s own paired count-query pattern.
        """
        stmt = select(func.count()).select_from(ContactView).where(
            ContactView.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_for_provider_between(
        self, provider_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """
        The count of a provider's own Contact Views with `start <=
        viewed_at < end` (LEAD-002, Backend Proposed Changes item 2) --
        the bounded-range counterpart to `count_for_provider`'s
        unbounded count. `start` is inclusive, `end` is exclusive, so
        two adjacent windows (e.g. the current 30-day window and the
        immediately preceding one, Decision 5) never double-count a row
        that lands exactly on the shared boundary.
        """
        stmt = (
            select(func.count())
            .select_from(ContactView)
            .where(
                ContactView.provider_id == provider_id,
                ContactView.viewed_at >= start,
                ContactView.viewed_at < end,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_daily_for_provider_since(
        self, provider_id: uuid.UUID, since: datetime
    ) -> list[tuple[date, int]]:
        """
        One `(day, count)` pair per calendar day with at least one
        Contact View at or after `since` (Decision 4,
        `Plan_S10_LEAD-002.md`) -- only days that actually have a row
        are returned; `VisibilityAnalyticsService` zero-fills the rest
        in Python. Plain `GROUP BY date_trunc('day', ...)`, deliberately
        not a SQL `generate_series` (Decision 4). `viewed_at` is
        converted to UTC via `AT TIME ZONE 'UTC'` before truncation, so
        the day boundary is always UTC midnight regardless of the DB
        session's timezone GUC -- matching `VisibilityAnalyticsService`'s
        own explicit `tzinfo=UTC` window boundaries.
        """
        day_column = func.date_trunc(
            "day", ContactView.viewed_at.op("AT TIME ZONE")("UTC")
        )
        stmt = (
            select(day_column, func.count())
            .select_from(ContactView)
            .where(
                ContactView.provider_id == provider_id,
                ContactView.viewed_at >= since,
            )
            .group_by(day_column)
        )
        result = await self.session.execute(stmt)
        return [(bucket.date(), int(count)) for bucket, count in result.all()]
