"""
Customer-facing claim-flow endpoints (CLM-001, Decision 6/7,
`Plan_S06_CLM-001.md`) -- mounted at `/claims`.

`require_role(ROLE_CUSTOMER)` gates every route (Backend Proposed
Changes item 7): searching for and claiming a listing is a
Customer-initiated action in the product sense (mirroring DIR-001
Decision 3's identical reasoning), and every registered Account already
holds `ROLE_CUSTOMER`, so this imposes no extra friction.

The OTP endpoints are rate-limited identically to `identity/api.py`'s
existing OTP endpoints (`RateLimitDependency`, the same
`AUTH_RATE_LIMIT_PER_MINUTE`/`AUTH_RATE_LIMIT_WINDOW_SECONDS` bucket) --
IP-keyed for both: unlike `identity`'s registration/login OTP, this
story's `request-otp` endpoint has no request-body phone number at all
(AC4's own point -- the number is never caller-supplied), so there is no
"target phone number" to key against; IP is the meaningful signal here.
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.config import settings
from app.core.constants import (
    AUTH_RATE_LIMIT_PER_MINUTE,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    ROLE_CUSTOMER,
)
from app.core.rate_limit import RateLimitDependency
from app.database.session import get_db
from app.modules.identity.schemas import RequestOtpResponse
from app.modules.provider.dependencies import get_claim_service
from app.modules.provider.models import BusinessProfile, Provider
from app.modules.provider.schemas import (
    ClaimResultResponse,
    ClaimSearchResultResponse,
    RequestClaimAdminReviewRequest,
    VerifyClaimOtpRequest,
)
from app.modules.provider.services.claim_service import ClaimService
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Claims"])

_DEFAULT_PAGE_SIZE = 20
_OTP_EXPIRY_MINUTES = 5

_request_otp_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="ip",
)
_verify_otp_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="ip",
)


def _mask_phone_number(
    phone_country_code: str | None, phone_number: str | None
) -> str | None:
    """
    Masks a public phone number for pre-claim display (AC3) -- e.g.
    `"+971 5*****67"` -- so a searcher can sanity-check "is this my
    number" without the full number being exposed to anyone who merely
    searched. `None` if the listing has no public number at all.
    """
    if not phone_country_code or not phone_number:
        return None
    if len(phone_number) <= 4:
        masked_local = "*" * len(phone_number)
    else:
        masked_local = (
            f"{phone_number[0]}{'*' * (len(phone_number) - 3)}{phone_number[-2:]}"
        )
    return f"{phone_country_code} {masked_local}"


def _to_search_result_response(
    provider: Provider, business_profile: BusinessProfile | None
) -> ClaimSearchResultResponse:
    return ClaimSearchResultResponse(
        id=provider.id,
        display_name=provider.display_name,
        address_line=business_profile.address_line if business_profile else None,
        city=business_profile.city if business_profile else None,
        phone_number_masked=_mask_phone_number(
            provider.phone_country_code, provider.phone_number
        ),
    )


@router.get(
    "/search",
    response_model=CollectionResponse[ClaimSearchResultResponse],
    responses={
        200: {"description": "One page of matching, still-unclaimed listings."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
    },
    summary="Search Unclaimed Google-Seeded Listings",
    description=(
        "Case-insensitive substring search by business name/address among "
        "`listing_source=google_seeded_unclaimed AND is_claimed=false` "
        "listings only (AC3, Decision 5) -- a self-registered or "
        "already-claimed provider matching the same query text never "
        "appears here."
    ),
)
async def search_unclaimed_listings(
    query: str,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    claim_service: ClaimService = Depends(get_claim_service),  # noqa: B008
) -> CollectionResponse[ClaimSearchResultResponse]:
    """Search still-unclaimed Google-seeded listings by name/address."""
    page_size = min(page_size, settings.CLAIM_SEARCH_MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    providers, total_items = await claim_service.search_unclaimed(
        query=query, limit=page_size, offset=offset
    )

    business_profiles_by_id = await claim_service.get_business_profiles_by_provider_id(
        [provider.id for provider in providers]
    )
    data = [
        _to_search_result_response(provider, business_profiles_by_id.get(provider.id))
        for provider in providers
    ]
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[ClaimSearchResultResponse](
        success=True,
        message="Search results retrieved.",
        data=data,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{provider_id}/request-otp",
    response_model=SuccessResponse[RequestOtpResponse],
    dependencies=[Depends(_request_otp_rate_limiter)],
    responses={
        200: {"description": "A verification code was requested."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
        404: {"description": "The listing is not an available claim target."},
        409: {
            "description": (
                "The listing has no public phone number on record -- the "
                "OTP trust gate is unusable; fall back to "
                "`request-admin-review`."
            ),
        },
        429: {"description": "Too many requests from this client."},
    },
    summary="Request An OTP Against The Listing's Public Number",
    description=(
        "Sends a 6-digit OTP to the **target listing's own stored** "
        "`phone_country_code`/`phone_number` (AC4) -- there is no "
        "request-body phone-number field of any kind; the number used "
        "structurally always comes from the provider row itself, never "
        "any caller-supplied value."
    ),
)
async def request_claim_otp(
    provider_id: uuid.UUID,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    claim_service: ClaimService = Depends(get_claim_service),  # noqa: B008
) -> SuccessResponse[RequestOtpResponse]:
    """Request an OTP against the target listing's own public number."""
    await claim_service.request_otp(provider_id)
    await db.commit()
    return SuccessResponse[RequestOtpResponse](
        success=True,
        message="If this listing has a public number on record, a code has been sent.",
        data=RequestOtpResponse(expires_in_seconds=_OTP_EXPIRY_MINUTES * 60),
    )


@router.post(
    "/{provider_id}/verify-otp",
    response_model=SuccessResponse[ClaimResultResponse],
    dependencies=[Depends(_verify_otp_rate_limiter)],
    responses={
        200: {"description": "The listing was successfully claimed."},
        400: {
            "description": "The code didn't match, was expired, or was already used."
        },
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
        404: {"description": "The listing is not an available claim target."},
        409: {
            "description": (
                "The listing was already claimed, or the caller's account "
                "already owns a different provider listing."
            ),
        },
        429: {
            "description": (
                "Either too many incorrect attempts (OTP locked), or too "
                "many requests from this client (rate limited)."
            ),
        },
    },
    summary="Verify The Claim OTP And Finalize The Claim",
    description=(
        "Verifies the submitted code against the listing's own public "
        "number, then -- only on success -- sets `is_claimed=true`, "
        "populates `user_id`, and resets `verification_status=pending`/"
        "`is_discoverable=false` (AC5), routing the claimed listing "
        "through the same Verification gate a self-registered Business "
        "would go through. Grants `ROLE_PROVIDER` to the caller's "
        "Account."
    ),
)
async def verify_claim_otp(
    provider_id: uuid.UUID,
    payload: VerifyClaimOtpRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    claim_service: ClaimService = Depends(get_claim_service),  # noqa: B008
) -> SuccessResponse[ClaimResultResponse]:
    """Verify the OTP code and finalize the claim on success."""
    provider = await claim_service.verify_otp(
        current_user.id, provider_id, payload.code
    )
    await db.commit()
    return SuccessResponse[ClaimResultResponse](
        success=True,
        message="Listing claimed successfully.",
        data=ClaimResultResponse(
            provider_id=provider.id,
            is_claimed=provider.is_claimed,
            verification_status=provider.verification_status,
        ),
    )


@router.post(
    "/{provider_id}/request-admin-review",
    response_model=SuccessResponse[None],
    responses={
        200: {"description": "The claim attempt was flagged for manual review."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
        404: {"description": "The listing is not an available claim target."},
    },
    summary="Request Manual Review Of A Failed Claim Attempt",
    description=(
        "AC6's explicit 'this isn't working' fallback -- creates a "
        '`claim_review_requests` row for either `reason="otp_failed"` '
        'or `reason="no_public_number"`, for an admin to pick up from '
        "`GET /admin/claims`."
    ),
)
async def request_claim_admin_review(
    provider_id: uuid.UUID,
    payload: RequestClaimAdminReviewRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    claim_service: ClaimService = Depends(get_claim_service),  # noqa: B008
) -> SuccessResponse[None]:
    """Flag a failed/unusable claim attempt for manual admin review."""
    await claim_service.request_admin_review(
        current_user.id, provider_id, reason=payload.reason
    )
    await db.commit()
    return SuccessResponse[None](
        success=True,
        message="We've flagged this for manual review.",
        data=None,
    )
