"""
Admin-only claim-review endpoints (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`) -- mounted at `/admin/claims`.

`require_role(ROLE_ADMIN)` alone is every route's entire authorization
boundary (ADR-023's ownerless shape, mirroring `verification/
admin_api.py` exactly) -- an Admin has no "own" review request to scope
to, since every request belongs to some *other* user's claim attempt.
No dashboard UI exists or is expected for this surface (VER-002's own
established "admin does something, no UI yet" precedent).
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_ADMIN
from app.database.session import get_db
from app.modules.administration.models import ClaimReviewRequest
from app.modules.provider.dependencies import get_admin_claim_service
from app.modules.provider.models import Provider
from app.modules.provider.schemas import (
    AdminClaimReviewRequestResponse,
    RejectClaimReviewRequest,
)
from app.modules.provider.services.admin_claim_service import AdminClaimService
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Admin Claims"])

_DEFAULT_PAGE_SIZE = 20


def _to_response(
    request: ClaimReviewRequest, provider: Provider
) -> AdminClaimReviewRequestResponse:
    return AdminClaimReviewRequestResponse(
        id=request.id,
        provider_id=request.provider_id,
        provider_display_name=provider.display_name,
        claimant_user_id=request.claimant_user_id,
        reason=request.reason,
        status=request.status,
        resolution=request.resolution,
        resolution_notes=request.resolution_notes,
        reviewed_at=request.reviewed_at,
    )


@router.get(
    "",
    response_model=CollectionResponse[AdminClaimReviewRequestResponse],
    responses={
        200: {"description": "One page of the open claim-review queue."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List Open Claim Review Requests",
    description=(
        "Lists `status=open` claim-review requests (AC6), oldest first, "
        "with each request's Provider context. `require_role(ROLE_ADMIN)` "
        "is the entire authorization boundary; no ownership check applies."
    ),
)
async def list_open_claim_reviews(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_claim_service: AdminClaimService = Depends(  # noqa: B008
        get_admin_claim_service
    ),
) -> CollectionResponse[AdminClaimReviewRequestResponse]:
    """Returns one page of the open claim-review queue."""
    (
        requests,
        providers_by_id,
        total,
    ) = await admin_claim_service.list_open_review_requests(
        page=page, page_size=page_size
    )
    data = [
        _to_response(request, providers_by_id[request.provider_id])
        for request in requests
    ]
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[AdminClaimReviewRequestResponse](
        success=True,
        message="Claim review requests retrieved.",
        data=data,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{request_id}/approve",
    response_model=SuccessResponse[AdminClaimReviewRequestResponse],
    responses={
        200: {"description": "The claim was approved and finalized."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The claim review request does not exist."},
        409: {
            "description": (
                "The listing was already claimed, or the claimant's account "
                "already owns a different provider listing."
            ),
        },
    },
    summary="Approve A Claim Review Request",
    description=(
        "Finalizes the claim via the **identical** logic the OTP-success "
        "path uses (Decision 6/9) -- `is_claimed`/`user_id`/`claimed_at` "
        "are set, `verification_status`/`is_discoverable` are reset, and "
        "`ROLE_PROVIDER` is granted -- then marks the request "
        "`status=resolved`/`resolution=approved`."
    ),
)
async def approve_claim_review(
    request_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_claim_service: AdminClaimService = Depends(  # noqa: B008
        get_admin_claim_service
    ),
) -> SuccessResponse[AdminClaimReviewRequestResponse]:
    """Approve an open claim review request, finalizing the claim."""
    request, provider = await admin_claim_service.approve_review_request(
        current_user.id, request_id
    )
    await db.commit()
    return SuccessResponse[AdminClaimReviewRequestResponse](
        success=True,
        message="Claim approved.",
        data=_to_response(request, provider),
    )


@router.post(
    "/{request_id}/reject",
    response_model=SuccessResponse[AdminClaimReviewRequestResponse],
    responses={
        200: {"description": "The claim review request was rejected."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The claim review request does not exist."},
    },
    summary="Reject A Claim Review Request",
    description=(
        "Marks the request `status=resolved`/`resolution=rejected`, "
        "leaving the target listing unclaimed -- no `providers`/"
        "`verification_records` write of any kind happens here."
    ),
)
async def reject_claim_review(
    request_id: uuid.UUID,
    payload: RejectClaimReviewRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_claim_service: AdminClaimService = Depends(  # noqa: B008
        get_admin_claim_service
    ),
) -> SuccessResponse[AdminClaimReviewRequestResponse]:
    """Reject an open claim review request, leaving the listing unclaimed."""
    request = await admin_claim_service.reject_review_request(
        current_user.id, request_id, notes=payload.resolution_notes
    )
    provider = await admin_claim_service.get_provider(request.provider_id)
    await db.commit()
    return SuccessResponse[AdminClaimReviewRequestResponse](
        success=True,
        message="Claim review request rejected.",
        data=_to_response(request, provider),
    )
