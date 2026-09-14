"""
Customer-facing Review submission endpoint (REV-002) -- mounted at
`/contact-views`, mirroring `verification_router`'s identical
separate-module-shared-prefix shape (a new, standalone `review` module's
router sharing the same URL-prefix space `contact_router` itself uses).

`require_role(ROLE_CUSTOMER)` gates the route: leaving a review after a
confirmed hire is a Customer-initiated action, mirroring `contact.api`'s
identical reasoning.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.review.dependencies import get_review_service
from app.modules.review.schemas import ReviewResponse, SubmitReviewRequest
from app.modules.review.services.review_service import ReviewService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Review"])


@router.post(
    "/{contact_view_id}/review",
    response_model=SuccessResponse[ReviewResponse],
    status_code=201,
    responses={
        201: {
            "model": SuccessResponse[ReviewResponse],
            "description": "The Review was submitted.",
        },
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
        404: {
            "description": (
                "`contact_view_id` doesn't exist, or doesn't belong to "
                "the calling customer (AC2, Decision 5 -- collapsed into "
                "one non-revealing 404)."
            ),
        },
        409: {
            "description": (
                "The anchoring Contact View has no confirmed hire "
                "outcome yet (no outcome tag, or `hired=false`, AC2), or "
                "a Review was already submitted for this Contact View "
                "(AC1)."
            ),
        },
        422: {"description": "`rating` is outside the 1-5 range."},
    },
    summary="Submit A Review",
    description=(
        "Rates a provider after a confirmed ('Yes') hire outcome (AC1). "
        "Only submittable against a Contact View the caller owns whose "
        "anchoring Outcome Tag has `hired=true` (AC2); a second "
        "submission against the same Contact View is rejected (409, "
        "AC1) -- immutable, one-shot, no edit path. Recalculates the "
        "target provider's rating aggregate in the same transaction "
        "(AC4)."
    ),
)
async def submit_review(
    contact_view_id: uuid.UUID,
    payload: SubmitReviewRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    review_service: ReviewService = Depends(get_review_service),  # noqa: B008
) -> SuccessResponse[ReviewResponse]:
    """Submit a Review for a Contact View the caller owns."""
    review = await review_service.submit_review(
        current_user.id,
        contact_view_id=contact_view_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    await db.commit()
    return SuccessResponse[ReviewResponse](
        success=True,
        message="Review submitted.",
        data=ReviewResponse(
            id=review.id,
            contact_view_id=review.contact_view_id,
            provider_id=review.provider_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
        ),
    )
