from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    AUTH_RATE_LIMIT_PER_MINUTE,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    OTP_EXPIRY_MINUTES,
)
from app.core.rate_limit import RateLimitDependency
from app.database.session import get_db
from app.modules.identity.dependencies import get_auth_service, get_oauth_service
from app.modules.identity.models import AuthProvider
from app.modules.identity.schemas import (
    AuthTokenResponse,
    OAuthSignInRequest,
    RequestOtpRequest,
    RequestOtpResponse,
    UserSummaryResponse,
    VerifyOtpRequest,
)
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.oauth_service import OAuthService
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
# The OAuth endpoints reuse the same auth rate-limit bucket, IP-keyed —
# there's no "target phone number" concept for these; a client-supplied
# provider value is never trusted to key a limiter, and IP is the only
# meaningful signal available before the token itself is verified.
_google_sign_in_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="ip",
)
_apple_sign_in_rate_limiter = RateLimitDependency(
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


async def _sign_in_with_oauth(
    provider: AuthProvider,
    payload: OAuthSignInRequest,
    db: AsyncSession,
    oauth_service: OAuthService,
    auth_service: AuthService,
) -> SuccessResponse[AuthTokenResponse]:
    """
    Shared orchestration for both OAuth endpoints below: verify the ID
    token server-side (never trust a client-asserted identity — AC2),
    then find-or-create the Account and issue a JWT (AC3/AC4/AC5).
    """
    claims = await oauth_service.verify_identity(provider, payload.id_token)
    user, token, roles = await auth_service.authenticate_with_oauth(provider, claims)
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


@router.post(
    "/google",
    response_model=SuccessResponse[AuthTokenResponse],
    dependencies=[Depends(_google_sign_in_rate_limiter)],
    responses={
        200: {
            "model": SuccessResponse[AuthTokenResponse],
            "description": (
                "The Google ID token was verified and the user authenticated."
            ),
        },
        401: {
            "description": (
                "The ID token could not be verified — invalid signature, "
                "expired, wrong audience/issuer, or malformed. The "
                "response never reveals which."
            ),
        },
        429: {
            "description": "Too many requests from this client.",
        },
    },
    summary="Sign In or Register with Google",
    description=(
        "Verifies a Google ID token against Google's public keys and "
        "returns a JWT access token. Transparently creates a new Account "
        "(with the `customer` role) if this is the first sign-in for the "
        "Google account, or authenticates the existing Account otherwise. "
        "A different provider previously used with the same email "
        "produces a second, independent Account by design."
    ),
)
async def sign_in_with_google(
    payload: OAuthSignInRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    oauth_service: OAuthService = Depends(get_oauth_service),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify a Google ID token, then authenticate (creating the Account if new)."""
    return await _sign_in_with_oauth(
        AuthProvider.GOOGLE, payload, db, oauth_service, auth_service
    )


@router.post(
    "/apple",
    response_model=SuccessResponse[AuthTokenResponse],
    dependencies=[Depends(_apple_sign_in_rate_limiter)],
    responses={
        200: {
            "model": SuccessResponse[AuthTokenResponse],
            "description": (
                "The Apple identity token was verified and the user authenticated."
            ),
        },
        401: {
            "description": (
                "The identity token could not be verified — invalid "
                "signature, expired, wrong audience/issuer, or "
                "malformed. The response never reveals which."
            ),
        },
        429: {
            "description": "Too many requests from this client.",
        },
    },
    summary="Sign In or Register with Apple",
    description=(
        "Verifies an Apple identity token against Apple's public keys "
        "and returns a JWT access token. Transparently creates a new "
        "Account (with the `customer` role) if this is the first "
        "sign-in for the Apple account, or authenticates the existing "
        "Account otherwise. A different provider previously used with "
        "the same email produces a second, independent Account by "
        "design."
    ),
)
async def sign_in_with_apple(
    payload: OAuthSignInRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    oauth_service: OAuthService = Depends(get_oauth_service),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify an Apple identity token, creating the Account if it's new."""
    return await _sign_in_with_oauth(
        AuthProvider.APPLE, payload, db, oauth_service, auth_service
    )
