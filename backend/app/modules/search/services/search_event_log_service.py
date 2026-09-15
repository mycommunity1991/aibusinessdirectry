"""
Minimal, read-only `search_event_log` display-context service (ADM-001,
Decision 6, `Plan_S11_ADM-001.md`) -- exists solely so `administration.
UnmatchedQueryReportService` can enrich its own rows with the underlying
`search_event_log` context (`category_id`/`customer_id`/`query_text`/
`result_count`) without importing `search.models`/`search.repositories`
directly (`ADR-047`'s "Services only" cross-module rule). Every other
`search_event_log` write/read need remains `SearchEventLogRepository`'s
own job, used directly within `search` itself.
"""

import uuid

from app.modules.search.models import SearchEventLog
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)


class SearchEventLogService:
    """Read-only batch lookup over `search.search_event_log`."""

    def __init__(self, repository: SearchEventLogRepository) -> None:
        self.repository = repository

    async def get_by_ids(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SearchEventLog]:
        """Keyed batch lookup -- `administration.UnmatchedQueryReport
        Service.list_filtered`/`_transition`'s enrichment mechanism
        (Decision 6). Missing ids are simply absent from the returned
        dict, never fabricated."""
        logs = await self.repository.list_by_ids(ids)
        return {log.id: log for log in logs}
