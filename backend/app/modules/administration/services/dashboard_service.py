"""
`DashboardService` (ADM-002, Decision 4/5, `Plan_S11_ADM-002.md`) --
AC2's single aggregation surface, summarizing verification queues,
manual-match workload, and the unmatched-query-report queue.

Depends on a raw `VerificationRecordRepository` (`administration ->
verification`, Decision 5) -- constructed directly by `administration/
dependencies.py`'s `_get_verification_record_repository_for_
administration` to avoid a genuine circular import (`verification.
dependencies` already imports `administration.dependencies` at module
level, VER-002) -- alongside this module's own `ManualMatchAssignment
Repository`/`UnmatchedQueryReportRepository`. A raw Repository is used
here (not a Service) since the only capability needed is a single,
business-logic-free `count_for_review()` read (Decision 5) --
introducing a new, single-method Service purely to satisfy `ADR-047`'s
"Services only" preference would be an unnecessary abstraction for one
COUNT query.
"""

from dataclasses import dataclass

from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)

_UNMATCHED_QUERY_REPORT_OPEN_STATUS = "open"

# Decision-documented literal path constants (AC2's "each linking to its
# respective queue") -- never derived/guessed from a router's registration.
PENDING_VERIFICATION_QUEUE_PATH = "/admin/verification/records"
PENDING_MANUAL_MATCH_QUEUE_PATH = "/admin/search/manual-matches"
OPEN_UNMATCHED_QUERY_REPORT_QUEUE_PATH = "/admin/unmatched-query-reports"


@dataclass(frozen=True)
class DashboardSummary:
    """Internal, framework-free summary payload -- mapped to
    `DashboardSummaryResponse` at the API layer."""

    pending_verification_count: int
    pending_verification_queue_path: str
    pending_manual_match_count: int
    pending_manual_match_queue_path: str
    open_unmatched_query_report_count: int
    open_unmatched_query_report_queue_path: str


class DashboardService:
    """Aggregates the three dashboard-linked queue counts (AC2)."""

    def __init__(
        self,
        manual_match_assignment_repository: ManualMatchAssignmentRepository,
        unmatched_query_report_repository: UnmatchedQueryReportRepository,
        verification_record_repository: VerificationRecordRepository,
    ) -> None:
        self.manual_match_assignment_repository = manual_match_assignment_repository
        self.unmatched_query_report_repository = unmatched_query_report_repository
        self.verification_record_repository = verification_record_repository

    async def get_summary(self) -> DashboardSummary:
        """
        Returns the three headline counts (Decision 4's dedicated
        count-only repository methods -- never a full page of hydrated,
        PII-bearing rows) plus each queue's own real, registered path
        string (AC2).
        """
        pending_verification_count = (
            await self.verification_record_repository.count_for_review()
        )
        pending_manual_match_count = (
            await self.manual_match_assignment_repository.count_pending()
        )
        open_unmatched_query_report_count = (
            await self.unmatched_query_report_repository.count_by_status(
                _UNMATCHED_QUERY_REPORT_OPEN_STATUS
            )
        )
        return DashboardSummary(
            pending_verification_count=pending_verification_count,
            pending_verification_queue_path=PENDING_VERIFICATION_QUEUE_PATH,
            pending_manual_match_count=pending_manual_match_count,
            pending_manual_match_queue_path=PENDING_MANUAL_MATCH_QUEUE_PATH,
            open_unmatched_query_report_count=open_unmatched_query_report_count,
            open_unmatched_query_report_queue_path=(
                OPEN_UNMATCHED_QUERY_REPORT_QUEUE_PATH
            ),
        )
