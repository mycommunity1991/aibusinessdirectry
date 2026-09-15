"""
Dependency-injection providers for the Administration module.

ADM-001 (`Plan_S11_ADM-001.md`, Decision 6) adds this module's first-ever
outgoing cross-module edge, `administration -> search.SearchEventLogService`
(see `_get_search_event_log_service_for_administration`'s own docstring
for why it is constructed directly here rather than imported from
`search/dependencies.py`).

ADM-002 (`Plan_S11_ADM-002.md`, Decision 5) adds this module's second
outgoing cross-module edge, `administration -> verification.
VerificationRecordRepository` (see `_get_verification_record_repository_
for_administration`'s own docstring for the identical circular-import
rationale, mirrored from the edge above).

`ENG-001` (`Plan_S12_ENG-001.md`, Decision 9) adds this module's third
outgoing cross-module edge, `administration -> notification.
NotificationService` -- imported directly from `notification.
dependencies.get_notification_service` (unlike the two edges above,
this one imports the *other* module's own `dependencies.py`, since
`notification/dependencies.py` has no edge back into `administration`
at all -- confirmed no circular import, `ADR-060`).
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
from app.modules.administration.repositories.feature_flag_repository import (
    FeatureFlagRepository,
)
from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.repositories.system_setting_repository import (
    SystemSettingRepository,
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
from app.modules.administration.services.dashboard_service import DashboardService
from app.modules.administration.services.feature_flag_service import FeatureFlagService
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.administration.services.system_setting_service import (
    SystemSettingService,
)
from app.modules.administration.services.unmatched_query_report_service import (
    UnmatchedQueryReportService,
)
from app.modules.notification.dependencies import get_notification_service
from app.modules.notification.services.notification_service import NotificationService
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.search.services.search_event_log_service import SearchEventLogService
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)


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
    admin_action_log_service: Annotated[
        AdminActionLogService, Depends(get_admin_action_log_service)
    ],
    notification_service: Annotated[
        NotificationService, Depends(get_notification_service)
    ],
) -> ManualMatchAssignmentService:
    """Provides a `ManualMatchAssignmentService` bound to the
    request-scoped DB session -- imported into `search/dependencies.py`
    the same way `get_claim_review_request_service` is already imported
    by `provider/dependencies.py`. Gained `admin_action_log_service`
    (ADM-002, Decision 6, `Plan_S11_ADM-002.md`) -- a trivial,
    intra-module constructor-injection addition, closing the real gap
    where `resolve` previously wrote no `admin_action_log` row (AC3).
    Gained `notification_service` (`ENG-001`, Decision 9,
    `Plan_S12_ENG-001.md`) -- `administration`'s third outgoing
    cross-module edge, so `create` can broadcast an in-app notification
    to every `ROLE_ADMIN` account (AC3)."""
    return ManualMatchAssignmentService(
        manual_match_assignment_repository,
        admin_action_log_service,
        notification_service,
    )


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
    admin_action_log_service: Annotated[
        AdminActionLogService, Depends(get_admin_action_log_service)
    ],
) -> UnmatchedQueryReportService:
    """Provides an `UnmatchedQueryReportService` bound to the
    request-scoped DB session, with `search.SearchEventLogService`
    (`administration -> search`, Decision 6) wired as a cross-module,
    constructor-injected dependency -- imported into `administration/
    api.py`, `administration`'s first-ever HTTP surface. Gained
    `admin_action_log_service` (ADM-002, Decision 6, `Plan_S11_ADM-002.md`)
    -- a trivial, intra-module constructor-injection addition, closing
    the real gap where `mark_reviewed`/`mark_actioned` previously wrote
    no `admin_action_log` row (AC3)."""
    return UnmatchedQueryReportService(
        unmatched_query_report_repository,
        search_event_log_service,
        admin_action_log_service,
    )


def get_feature_flag_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureFlagRepository:
    """Provides a `FeatureFlagRepository` bound to the request-scoped DB
    session (ADM-002, Decision 1, `Plan_S11_ADM-002.md`)."""
    return FeatureFlagRepository(db)


def get_feature_flag_service(
    feature_flag_repository: Annotated[
        FeatureFlagRepository, Depends(get_feature_flag_repository)
    ],
    admin_action_log_service: Annotated[
        AdminActionLogService, Depends(get_admin_action_log_service)
    ],
) -> FeatureFlagService:
    """Provides a `FeatureFlagService` bound to the request-scoped DB
    session -- imported into `search/dependencies.py` the same way
    `get_manual_match_assignment_service` is already imported (Decision
    7, `Plan_S11_ADM-002.md`, the `search -> administration` edge)."""
    return FeatureFlagService(feature_flag_repository, admin_action_log_service)


def get_system_setting_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SystemSettingRepository:
    """Provides a `SystemSettingRepository` bound to the request-scoped
    DB session (ADM-002, Decision 1, `Plan_S11_ADM-002.md`)."""
    return SystemSettingRepository(db)


def get_system_setting_service(
    system_setting_repository: Annotated[
        SystemSettingRepository, Depends(get_system_setting_repository)
    ],
    admin_action_log_service: Annotated[
        AdminActionLogService, Depends(get_admin_action_log_service)
    ],
) -> SystemSettingService:
    """Provides a `SystemSettingService` bound to the request-scoped DB
    session (ADM-002, Decision 1, `Plan_S11_ADM-002.md`)."""
    return SystemSettingService(system_setting_repository, admin_action_log_service)


def _get_verification_record_repository_for_administration(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationRecordRepository:
    """
    Provides a `VerificationRecordRepository` bound to the
    request-scoped DB session -- `administration`'s second outgoing
    cross-module edge (`administration -> verification`, ADM-002,
    Decision 5, `Plan_S11_ADM-002.md`), used only for the read-only,
    business-logic-free `count_for_review()` query `DashboardService`
    needs for AC2's pending-verification headline count.

    Deliberately constructs `VerificationRecordRepository` directly here
    rather than importing `verification.dependencies.
    get_verification_record_repository` -- `verification/dependencies.py`
    already imports `get_admin_action_log_service` from *this* module at
    module level (the existing `verification -> administration` edge,
    VER-002), so a same-direction import back
    (`administration.dependencies -> verification.dependencies`) would be
    a genuine circular import at the Python module level, the identical
    class of problem `_get_search_event_log_service_for_administration`
    above already solved for `administration -> search`
    (`ADM-001`, Decision 6, `ADR-060`). `verification.repositories.
    verification_record_repository` is a leaf module with no edge back
    into `administration`, so constructing it directly here avoids the
    cycle entirely. This is a raw-Repository edge (not a Service), since
    the only thing needed is `count_for_review()` -- a single,
    business-logic-free read with no equivalent lightweight Service to
    reach for (Decision 5; `ADR-047`'s "Services only" rule is a
    deliberate, narrow exception here, not silently ignored).
    """
    return VerificationRecordRepository(db)


def get_dashboard_service(
    manual_match_assignment_repository: Annotated[
        ManualMatchAssignmentRepository,
        Depends(get_manual_match_assignment_repository),
    ],
    unmatched_query_report_repository: Annotated[
        UnmatchedQueryReportRepository, Depends(get_unmatched_query_report_repository)
    ],
    verification_record_repository: Annotated[
        VerificationRecordRepository,
        Depends(_get_verification_record_repository_for_administration),
    ],
) -> DashboardService:
    """Provides a `DashboardService` bound to the request-scoped DB
    session (ADM-002, Decision 4/5, `Plan_S11_ADM-002.md`) -- imported
    into `administration/admin_dashboard_api.py` (AC2)."""
    return DashboardService(
        manual_match_assignment_repository,
        unmatched_query_report_repository,
        verification_record_repository,
    )
