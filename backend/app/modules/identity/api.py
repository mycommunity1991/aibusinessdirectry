from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    AUTH_RATE_LIMIT_PER_MINUTE,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    OTP_EXPIRY_MINUTES,
)
from app.core.rate_limit import RateLimitDependency
from app.database.session import get_db
from app.modules.identity.dependencies import get_auth_service
from app.modules.identity.schemas import (
    AuthTokenResponse,
    RequestOtpRequest,
    RequestOtpResponse,
    UserSummaryResponse,
    VerifyOtpRequest,
)
from app.modules.identity.services.auth_service import AuthService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Auth"])

# Redis-backed fixed-window rate limits (05_API_GUIDELINES.md "Rate
# Limiting" — Authentication: 10 requests/minute). `request-otp` is keyed
# by the target phone number (the primary SMS-bombing vector); `verify-otp`
# is keyed by client IP as defense in depth — it caps how fast a single
# client can hit the endpoint at all (e.g. spinning through many different
# phone numbers), which a phone-keyed limit would not catch since each
# phone number would get its own independent counter.
_request_otp_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="phone",
)
_verify_otp_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="ip",
)


@router.post(
    "/request-otp",
    response_model=SuccessResponse[RequestOtpResponse],
    dependencies=[Depends(_request_otp_rate_limiter)],
    responses={
        200: {
            "model": SuccessResponse[RequestOtpResponse],
            "description": "A verification code was requested.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": (
                            "If this number is valid, a verification code "
                            "has been sent."
                        ),
                        "data": {"expires_in_seconds": 300},
                    }
                }
            },
        },
        429: {
            "description": "Too many requests for this phone number.",
        },
    },
    summary="Request a Mobile OTP Code",
    description=(
        "Sends a 6-digit one-time-password to the given phone number, "
        "valid for 5 minutes. Always returns the same acknowledgement "
        "regardless of whether the phone number is already registered, so "
        "the response never reveals account existence."
    ),
)
async def request_otp(
    payload: RequestOtpRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[RequestOtpResponse]:
    """Request an OTP code for mobile sign-in (registration or login)."""
    await auth_service.request_otp(payload.phone_country_code, payload.phone_number)
    await db.commit()
    return SuccessResponse[RequestOtpResponse](
        success=True,
        message="If this number is valid, a verification code has been sent.",
        data=RequestOtpResponse(expires_in_seconds=OTP_EXPIRY_MINUTES * 60),
    )


@router.post(
    "/verify-otp",
    response_model=SuccessResponse[AuthTokenResponse],
    dependencies=[Depends(_verify_otp_rate_limiter)],
    responses={
        200: {
            "model": SuccessResponse[AuthTokenResponse],
            "description": "The OTP code was verified and the user authenticated.",
        },
        400: {
            "description": (
                "The code didn't match, was expired, or was already used. "
                "The response never reveals which — or whether the phone "
                "number is registered."
            ),
        },
        429: {
            "description": (
                "Either too many incorrect attempts for this code (OTP "
                "locked), or too many requests from this client "
                "(rate limited) — both return the same status code and a "
                "plain-language message."
            ),
        },
    },
    summary="Verify a Mobile OTP Code and Authenticate",
    description=(
        "Verifies a 6-digit OTP code and returns a JWT access token. "
        "Transparently creates a new Account (with the `customer` role) if "
        "the phone number is not yet registered, or authenticates the "
        "existing Account otherwise — the client never needs to know in "
        "advance which will happen."
    ),
)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify an OTP code, then authenticate (creating the Account if new)."""
    user, token, roles = await auth_service.verify_otp_and_authenticate(
        payload.phone_country_code, payload.phone_number, payload.code
    )
    await db.commit()

    return SuccessResponse[AuthTokenResponse](
        success=True,
        message="Signed in successfully.",
        data=AuthTokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserSummaryResponse(
                id=user.id,
                phone_country_code=user.phone_country_code,
                phone_number=user.phone_number,
                status=user.status,
                preferred_language=user.preferred_language,
                roles=roles,
            ),
        ),
    )
