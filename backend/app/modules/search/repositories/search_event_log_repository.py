import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.models import SearchEventLog
from app.repositories.base_repository import BaseRepository


class SearchEventLogRepository(BaseRepository[SearchEventLog]):
    """
    Repository for the append-only `search.search_event_log` table
    (AI-002, AC6, `Plan_S07_AI-002.md`). `create` (inherited from
    `BaseRepository`) is written exactly once per `search_requests` row,
    by `SearchRequestService._finalize_matches` (Decision 4) -- never
    updated or soft-deleted (`SearchEventLog` has no such columns at
    all, mirroring `audit.audit_logs`'s exemption).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=SearchEventLog, session=session)

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[SearchEventLog]:
        """
        Batch lookup by id (ADM-001, Decision 6) -- backs `search
        EventLogService.get_by_ids`'s keyed enrichment of an
        `unmatched_query_reports` page. An empty `ids` list short-
        circuits to `[]` without issuing a query.
        """
        if not ids:
            return []
        stmt = select(SearchEventLog).where(SearchEventLog.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
