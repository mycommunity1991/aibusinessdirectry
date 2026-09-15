"""
Dependency-injection providers for the Administration module.

ADM-001 (`Plan_S11_ADM-001.md`, Decision 6) adds this module's first-ever
outgoing cross-module edge, `administration -> search.SearchEventLogService`
(see `_get_search_event_log_service_for_administration`'s own docstring
for why it is constructed directly here rather than imported from
`search/dependencies.py`).
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.repositories.claim_review_request_repository import (
    ClaimReviewRequestRepository,
)
from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewRequestService,
)
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.administration.services.unmatched_query_report_service import (
    UnmatchedQueryReportService,
)
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.search.services.search_event_log_service import SearchEventLogService


def get_admin_action_log_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActionLogRepository:
    """Provides an `AdminActionLogRepository` bound to the request-scoped
    DB session."""
    return AdminActionLogRepository(db)


def get_admin_action_log_service(
    admin_action_log_repository: Annotated[
        AdminActionLogRepository, Depends(get_admin_action_log_repository)
    ],
) -> AdminActionLogService:
    """Provides an `AdminActionLogService` bound to the request-scoped
    DB session."""
    return AdminActionLogService(admin_action_log_repository)


def get_claim_review_request_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClaimReviewRequestRepository:
    """Provides a `ClaimReviewRequestRepository` bound to the
    request-scoped DB session (CLM-001, Decision 9,
    `Plan_S06_CLM-001.md`)."""
    return ClaimReviewRequestRepository(db)


def get_claim_review_request_service(
    claim_review_request_repository: Annotated[
        ClaimReviewRequestRepository, Depends(get_claim_review_request_repository)
    ],
) -> ClaimReviewRequestService:
    """Provides a `ClaimReviewRequestService` bound to the request-scoped
    DB session -- imported into `provider/dependencies.py` the same way
    `get_admin_action_log_service` is already imported by
    `verification/dependencies.py`."""
    return ClaimReviewRequestService(claim_review_request_repository)


def get_manual_match_assignment_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ManualMatchAssignmentRepository:
    """Provides a `ManualMatchAssignmentRepository` bound to the
    request-scoped DB session (AI-002, Decision 3,
    `Plan_S07_AI-002.md`)."""
    return ManualMatchAssignmentRepository(db)


def get_manual_match_assignment_service(
    manual_match_assignment_repository: Annotated[
        ManualMatchAssignmentRepository,
        Depends(get_manual_match_assignment_repository),
    ],
) -> ManualMatchAssignmentService:
    """Provides a `ManualMatchAssignmentService` bound to the
    request-scoped DB session -- imported into `search/dependencies.py`
    the same way `get_claim_review_request_service` is already imported
    by `provider/dependencies.py`."""
    return ManualMatchAssignmentService(manual_match_assignment_repository)


def get_unmatched_query_report_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnmatchedQueryReportRepository:
    """Provides an `UnmatchedQueryReportRepository` bound to the
    request-scoped DB session (ADM-001, Decision 2,
    `Plan_S11_ADM-001.md`)."""
    return UnmatchedQueryReportRepository(db)


def _get_search_event_log_service_for_administration(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchEventLogService:
    """
    Provides a `SearchEventLogService` bound to the request-scoped DB
    session -- `administration`'s first-ever outgoing cross-module edge
    (`administration -> search`, ADM-001, Decision 6, `Plan_S11_ADM-001.md`),
    used only for read-only `search_event_log` display-context enrichment.

    Deliberately constructs `SearchEventLogService`/`SearchEventLogRepository`
    directly here rather than importing `search.dependencies.
    get_search_event_log_service` -- `search/dependencies.py` already
    imports `get_manual_match_assignment_service` from *this* module at
    module level (the existing `search -> administration` edge), so a
    same-direction import back (`administration.dependencies -> search.
    dependencies`) would be a genuine circular import at the Python
    module level, the identical class of problem Decision 4 already
    solved for `search -> conversation` by reaching for a leaf module
    instead. `search.repositories.search_event_log_repository`/`search.
    services.search_event_log_service` import only `search.models`/
    `app.repositories.base_repository` -- leaf modules with no edge back
    into `administration` -- so constructing them directly here avoids
    the cycle entirely while still keeping the edge a Service, not a raw
    Repository (`ADR-047`'s "Services only" rule remains satisfied).
    """
    return SearchEventLogService(SearchEventLogRepository(db))


def get_unmatched_query_report_service(
    unmatched_query_report_repository: Annotated[
        UnmatchedQueryReportRepository, Depends(get_unmatched_query_report_repository)
    ],
    search_event_log_service: Annotated[
        SearchEventLogService, Depends(_get_search_event_log_service_for_administration)
    ],
) -> UnmatchedQueryReportService:
    """Provides an `UnmatchedQueryReportService` bound to the
    request-scoped DB session, with `search.SearchEventLogService`
    (`administration -> search`, Decision 6) wired as a cross-module,
    constructor-injected dependency -- imported into `administration/
    api.py`, `administration`'s first-ever HTTP surface."""
    return UnmatchedQueryReportService(
        unmatched_query_report_repository, search_event_log_service
    )
