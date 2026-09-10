"""
Admin-only manual-match-assignment-queue endpoints (AI-002, Decision 3,
`Plan_S07_AI-002.md`) -- mounted at `/admin/search/manual-matches`.

`require_role(ROLE_ADMIN)` alone is every route's entire authorization
boundary (ADR-023's ownerless shape, mirroring `provider/
admin_claim_api.py` exactly) -- an Admin has no "own" assignment to
scope to. This is the pull-based "notify an admin" mechanism (Decision
3): no push-notification recipient concept exists anywhere in this
codebase (`ADR-030`), so an admin (or a future `ADM-001` dashboard)
polls this queue. Backend-API-only -- no dashboard UI exists or is
expected here, per this story's own explicit scope boundary.
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.database.session import get_db
from app.modules.administration.models import ManualMatchAssignment
from app.modules.search.dependencies import get_search_request_service
from app.modules.search.schemas import (
    ManualMatchAssignmentSummaryResponse,
    ResolveManualMatchRequest,
    SearchRequestResultResponse,
)
from app.modules.search.services.search_request_service import SearchRequestService
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Admin Manual Matches"])

_DEFAULT_PAGE_SIZE = 20


def _to_summary(
    assignment: ManualMatchAssignment,
) -> ManualMatchAssignmentSummaryResponse:
    return ManualMatchAssignmentSummaryResponse(
        id=assignment.id,
        conversation_session_id=assignment.conversation_session_id,
        search_request_id=assignment.search_request_id,
        status=assignment.status,
        created_at=assignment.created_at,
    )


@router.get(
    "",
    response_model=CollectionResponse[ManualMatchAssignmentSummaryResponse],
    responses={
        200: {"description": "One page of the pending manual-match queue."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List Pending Manual Match Assignments",
    description=(
        "Lists `status=pending` assignments (AC2), oldest first -- the "
        "pull-based 'notify an admin' mechanism (Decision 3). Does not "
        "include the session's `messages` transcript (out of this "
        "story's scope, `ADM-001`'s job)."
    ),
)
async def list_pending_manual_matches(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_ADMIN)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    search_request_service: SearchRequestService = Depends(  # noqa: B008
        get_search_request_service
    ),
) -> CollectionResponse[ManualMatchAssignmentSummaryResponse]:
    """Returns one page of the pending manual-match queue, oldest first."""
    page_size = min(page_size, settings.SEARCH_MAX_PAGE_SIZE)
    assignments, total = await search_request_service.list_pending_manual_matches(
        page=page, page_size=page_size
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[ManualMatchAssignmentSummaryResponse](
        success=True,
        message="Pending manual match assignments retrieved.",
        data=[_to_summary(assignment) for assignment in assignments],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{assignment_id}/resolve",
    response_model=SuccessResponse[SearchRequestResultResponse],
    responses={
        200: {
            "model": SuccessResponse[SearchRequestResultResponse],
            "description": "The assignment was resolved and finalized.",
        },
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The manual match assignment does not exist."},
        409: {"description": "This assignment has already been resolved."},
    },
    summary="Resolve A Manual Match Assignment",
    description=(
        "Finalizes the underlying `search_requests` row via the "
        "**identical** `_finalize_matches` logic the automated path "
        "uses (Decision 4) -- an empty `provider_ids` list is valid "
        "('no viable match found', resolves to `unmatched`) -- then "
        "marks the assignment `status=completed`."
    ),
)
async def resolve_manual_match(
    assignment_id: uuid.UUID,
    payload: ResolveManualMatchRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_ADMIN)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    search_request_service: SearchRequestService = Depends(  # noqa: B008
        get_search_request_service
    ),
) -> SuccessResponse[SearchRequestResultResponse]:
    """Resolve a pending manual match assignment, finalizing the same
    way the automated matcher would."""
    search_request = await search_request_service.resolve_manual_match(
        assignment_id,
        admin_user_id=current_user.id,
        provider_ids=payload.provider_ids,
    )
    matched_providers = await search_request_service.get_matched_providers(
        search_request
    )
    await db.commit()
    return SuccessResponse[SearchRequestResultResponse](
        success=True,
        message="Manual match assignment resolved.",
        data=SearchRequestResultResponse(
            status=search_request.status,
            matched_providers=matched_providers,
        ),
    )
