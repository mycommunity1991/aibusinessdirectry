"""
Admin-only unmatched-query-report endpoints (ADM-001, Decision 6,
`Plan_S11_ADM-001.md`) -- mounted at `/admin/unmatched-query-reports`.

`administration`'s first-ever `api.py` -- every one of this module's
three prior aggregates (`admin_action_log`, `claim_review_requests`,
`manual_match_assignments`) was resolved by writing into some *other*
module's schema, so their routes live in that other module
(`verification/admin_api.py`, `provider/admin_claim_api.py`, `search/
admin_manual_match_api.py`, respectively). Marking an `unmatched_query_
reports` row `reviewed`/`actioned` is a self-contained state transition
entirely within `administration`'s own table -- no cross-module write is
needed, so this capability is hosted here instead.

`require_role(ROLE_ADMIN)` alone is every route's entire authorization
boundary (mirrors `search/admin_manual_match_api.py`/`provider/
admin_claim_api.py` exactly) -- an Admin has no "own" report to scope to.
Backend-API-only -- no dashboard UI exists or is expected here, per this
story's own explicit scope boundary.
"""

import math
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.database.session import get_db
from app.modules.administration.dependencies import get_unmatched_query_report_service
from app.modules.administration.models import UnmatchedQueryReport
from app.modules.administration.schemas import (
    UnmatchedQueryReportActionRequest,
    UnmatchedQueryReportResponse,
)
from app.modules.administration.services.unmatched_query_report_service import (
    UnmatchedQueryReportService,
)
from app.modules.search.models import SearchEventLog
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Admin Unmatched Query Reports"])

_DEFAULT_PAGE_SIZE = 20


def _to_response(
    report: UnmatchedQueryReport, search_event_log: SearchEventLog | None
) -> UnmatchedQueryReportResponse:
    return UnmatchedQueryReportResponse(
        id=report.id,
        search_event_log_id=report.search_event_log_id,
        status=report.status,
        category_gap_notes=report.category_gap_notes,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        created_at=report.created_at,
        category_id=search_event_log.category_id if search_event_log else None,
        customer_id=search_event_log.customer_id if search_event_log else None,
        query_text=search_event_log.query_text if search_event_log else None,
        result_count=search_event_log.result_count if search_event_log else None,
    )


@router.get(
    "",
    response_model=CollectionResponse[UnmatchedQueryReportResponse],
    responses={
        200: {"description": "One page of the unmatched-query-report queue."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List Unmatched Query Reports",
    description=(
        "Lists `unmatched_query_reports` rows (AC5), filtered by `status` "
        "(default `open`) and sorted by `created_at` (Decision 7), each "
        "enriched with its underlying `search_event_log` display context "
        "(Decision 6)."
    ),
)
async def list_unmatched_query_reports(
    status: Literal["open", "reviewed", "actioned", "all"] = "open",
    sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc",
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    unmatched_query_report_service: UnmatchedQueryReportService = Depends(  # noqa: B008
        get_unmatched_query_report_service
    ),
) -> CollectionResponse[UnmatchedQueryReportResponse]:
    """Returns one page of the unmatched-query-report queue."""
    page_size = min(page_size, settings.UNMATCHED_QUERY_REPORT_MAX_PAGE_SIZE)
    filter_status = None if status == "all" else status
    (
        reports,
        search_event_logs_by_id,
        total,
    ) = await unmatched_query_report_service.list_filtered(
        status=filter_status,
        sort_desc=(sort == "created_at_desc"),
        page=page,
        page_size=page_size,
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[UnmatchedQueryReportResponse](
        success=True,
        message="Unmatched query reports retrieved.",
        data=[
            _to_response(
                report, search_event_logs_by_id.get(report.search_event_log_id)
            )
            for report in reports
        ],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{report_id}/review",
    response_model=SuccessResponse[UnmatchedQueryReportResponse],
    responses={
        200: {"description": "The report was marked reviewed."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The unmatched query report does not exist."},
        409: {"description": "This report is not currently `open`."},
    },
    summary="Mark An Unmatched Query Report Reviewed",
    description=(
        "Transitions a report `open` -> `reviewed` only (Decision 8) -- "
        "an atomic conditional `UPDATE`, race-safe under concurrent "
        "admin calls."
    ),
)
async def mark_unmatched_query_report_reviewed(
    report_id: uuid.UUID,
    payload: UnmatchedQueryReportActionRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    unmatched_query_report_service: UnmatchedQueryReportService = Depends(  # noqa: B008
        get_unmatched_query_report_service
    ),
) -> SuccessResponse[UnmatchedQueryReportResponse]:
    """Mark an open unmatched query report reviewed."""
    report, search_event_log = await unmatched_query_report_service.mark_reviewed(
        report_id,
        admin_user_id=current_user.id,
        category_gap_notes=payload.category_gap_notes,
    )
    await db.commit()
    return SuccessResponse[UnmatchedQueryReportResponse](
        success=True,
        message="Unmatched query report marked reviewed.",
        data=_to_response(report, search_event_log),
    )


@router.post(
    "/{report_id}/action",
    response_model=SuccessResponse[UnmatchedQueryReportResponse],
    responses={
        200: {"description": "The report was marked actioned."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The unmatched query report does not exist."},
        409: {"description": "This report is not currently `open` or `reviewed`."},
    },
    summary="Mark An Unmatched Query Report Actioned",
    description=(
        "Transitions a report `open` **or** `reviewed` -> `actioned` "
        "(Decision 8) -- a single admin may action a report directly "
        "without a separate review step first."
    ),
)
async def mark_unmatched_query_report_actioned(
    report_id: uuid.UUID,
    payload: UnmatchedQueryReportActionRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    unmatched_query_report_service: UnmatchedQueryReportService = Depends(  # noqa: B008
        get_unmatched_query_report_service
    ),
) -> SuccessResponse[UnmatchedQueryReportResponse]:
    """Mark an open or reviewed unmatched query report actioned."""
    report, search_event_log = await unmatched_query_report_service.mark_actioned(
        report_id,
        admin_user_id=current_user.id,
        category_gap_notes=payload.category_gap_notes,
    )
    await db.commit()
    return SuccessResponse[UnmatchedQueryReportResponse](
        success=True,
        message="Unmatched query report marked actioned.",
        data=_to_response(report, search_event_log),
    )
