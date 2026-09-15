"""
Unmatched-query-report queue recording/listing/review-action (ADM-001,
Decision 2/6/7/8, `Plan_S11_ADM-001.md`, AC1/AC5).

Depends on `search.SearchEventLogService` (Decision 6) -- `administration`'s
first-ever outgoing cross-module edge (`administration -> search`), wired
via a Service (`ADR-047`'s "Services only" cross-module rule) rather than
a raw Repository, since `search` has no circular-import obstacle in this
direction (unlike Decision 4's `search -> conversation` edge). Used only
for read-only display enrichment (`category_id`/`customer_id`/
`query_text`/`result_count`) -- this module never writes into `search`'s
schema, mirroring how `verification/admin_api.py` reads `provider.
Provider` for display context without ever writing to it.
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    UnmatchedQueryReportInvalidTransitionError,
    UnmatchedQueryReportNotFoundError,
)
from app.modules.administration.models import UnmatchedQueryReport
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.search.models import SearchEventLog
from app.modules.search.services.search_event_log_service import SearchEventLogService

_STATUS_OPEN = "open"
_STATUS_REVIEWED = "reviewed"
_STATUS_ACTIONED = "actioned"


class UnmatchedQueryReportService:
    """Creates, lists, and transitions `unmatched_query_reports` rows."""

    def __init__(
        self,
        repository: UnmatchedQueryReportRepository,
        search_event_log_service: SearchEventLogService,
        admin_action_log_service: AdminActionLogService,
    ) -> None:
        self.repository = repository
        self.search_event_log_service = search_event_log_service
        # ADM-002, Decision 6 (`Plan_S11_ADM-002.md`): a trivial,
        # intra-module constructor-injection addition -- closes the real
        # gap where `mark_reviewed`/`mark_actioned` previously wrote no
        # `admin_action_log` row at all, despite AC3's literal "every...
        # queue action" wording.
        self.admin_action_log_service = admin_action_log_service

    async def create(self, *, search_event_log_id: uuid.UUID) -> UnmatchedQueryReport:
        """
        Creates a new `status=open` row (Decision 2's write-time hook) --
        called exactly once, by `SearchRequestService._finalize_matches`,
        immediately after writing a `search_event_log` row with
        `was_matched=False`.
        """
        return await self.repository.create(
            {
                "search_event_log_id": search_event_log_id,
                "status": _STATUS_OPEN,
            }
        )

    async def list_filtered(
        self,
        *,
        status: str | None,
        sort_desc: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[UnmatchedQueryReport], dict[uuid.UUID, SearchEventLog], int]:
        """
        Paginates `unmatched_query_reports` (Decision 7's `status`/
        `created_at` filter/sort scope), then batch-enriches each page
        with its underlying `search_event_log` context (Decision 6) --
        `status="all"` is mapped to `None` (no filter) before reaching
        the repository.
        """
        offset = (page - 1) * page_size
        reports, total = await self.repository.list_filtered(
            status=status, sort_desc=sort_desc, offset=offset, limit=page_size
        )
        search_event_log_ids = [report.search_event_log_id for report in reports]
        search_event_logs_by_id = await self.search_event_log_service.get_by_ids(
            search_event_log_ids
        )
        return reports, search_event_logs_by_id, total

    async def get_by_id(self, report_id: uuid.UUID) -> UnmatchedQueryReport | None:
        """Single-report lookup, used by the API layer to 404 on a
        nonexistent id before rendering the enriched response."""
        return await self.repository.get_by_id(report_id)

    async def mark_reviewed(
        self,
        report_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
        category_gap_notes: str | None,
    ) -> tuple[UnmatchedQueryReport, SearchEventLog | None]:
        """`open` -> `reviewed` only (Decision 8)."""
        return await self._transition(
            report_id,
            from_statuses=(_STATUS_OPEN,),
            to_status=_STATUS_REVIEWED,
            admin_user_id=admin_user_id,
            category_gap_notes=category_gap_notes,
        )

    async def mark_actioned(
        self,
        report_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
        category_gap_notes: str | None,
    ) -> tuple[UnmatchedQueryReport, SearchEventLog | None]:
        """`open` **or** `reviewed` -> `actioned` (Decision 8) -- a
        single admin may reasonably action a report directly without a
        separate review step first."""
        return await self._transition(
            report_id,
            from_statuses=(_STATUS_OPEN, _STATUS_REVIEWED),
            to_status=_STATUS_ACTIONED,
            admin_user_id=admin_user_id,
            category_gap_notes=category_gap_notes,
        )

    # -- internal helpers -----------------------------------------------

    async def _transition(
        self,
        report_id: uuid.UUID,
        *,
        from_statuses: tuple[str, ...],
        to_status: str,
        admin_user_id: uuid.UUID,
        category_gap_notes: str | None,
    ) -> tuple[UnmatchedQueryReport, SearchEventLog | None]:
        report = await self.repository.get_by_id(report_id)
        if report is None:
            raise UnmatchedQueryReportNotFoundError()

        won = await self.repository.try_transition_status(
            report_id,
            from_statuses=from_statuses,
            to_status=to_status,
            admin_user_id=admin_user_id,
            reviewed_at=datetime.now(UTC),
            category_gap_notes=category_gap_notes,
        )
        if not won:
            raise UnmatchedQueryReportInvalidTransitionError()

        await self.repository.session.refresh(report)
        await self.admin_action_log_service.record_unmatched_query_report_transition(
            admin_user_id=admin_user_id,
            report_id=report.id,
            to_status=to_status,
            category_gap_notes=category_gap_notes,
        )
        search_event_logs_by_id = await self.search_event_log_service.get_by_ids(
            [report.search_event_log_id]
        )
        return report, search_event_logs_by_id.get(report.search_event_log_id)
