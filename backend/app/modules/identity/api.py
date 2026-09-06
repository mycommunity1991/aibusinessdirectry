import ipaddress
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user, require_role
from app.core.constants import (
    AUTH_RATE_LIMIT_PER_MINUTE,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    OTP_EXPIRY_MINUTES,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_PROVIDER,
)
from app.core.rate_limit import RateLimitDependency
from app.database.session import get_db
from app.modules.identity.dependencies import (
    get_auth_service,
    get_oauth_service,
    get_session_service,
)
from app.modules.identity.models import AuthProvider
from app.modules.identity.schemas import (
    AuthTokenResponse,
    LogoutAllRequest,
    OAuthSignInRequest,
    RefreshTokenRequest,
    RequestOtpRequest,
    RequestOtpResponse,
    SessionSummaryResponse,
    UserSummaryResponse,
    VerifyOtpRequest,
)
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.oauth_service import OAuthService
from app.modules.identity.services.session_service import SessionService
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
# The refresh endpoint reuses the same auth rate-limit bucket, IP-keyed —
# it is public (no access token required, since the whole point is to
# mint a new one), so IP is the only signal available (AUTH-003).
_refresh_rate_limiter = RateLimitDependency(
    limit=AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_by="ip",
)


def _client_context(request: Request) -> tuple[str | None, str | None]:
    """
    Best-effort client IP/user-agent extraction (AUTH-003). Deliberately
    not proxy-aware (`X-Forwarded-For` chain parsing is explicitly out of
    scope, `Plan_S02_AUTH-003.md`) -- `request.client.host` only.

    `sessions.ip_address` is a Postgres `INET` column, which rejects
    anything that isn't a real, parseable IP address -- ASGI test clients
    (e.g. Starlette's `TestClient`) set `request.client.host` to the
    literal string `"testclient"`, which is not one. Falls back to `None`
    rather than raising for any host value that doesn't parse.
    """
    raw_host = request.client.host if request.client else None
    ip_address = None
    if raw_host:
        try:
            ipaddress.ip_address(raw_host)
            ip_address = raw_host
        except ValueError:
            ip_address = None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.get(
    "/me",
    response_model=SuccessResponse[UserSummaryResponse],
    responses={
        200: {
            "model": SuccessResponse[UserSummaryResponse],
            "description": "The caller's own id, roles, and account status.",
        },
        401: {
            "description": (
                "No token was provided, or the token is invalid or expired."
            ),
        },
        403: {
            "description": (
                "The token is valid, but the caller's role is not one of "
                "the platform's recognized roles."
            ),
        },
    },
    summary="Get the Authenticated Caller's Own Profile Summary",
    description=(
        "Returns the authenticated caller's own id, roles, and account "
        "status (AUTH-004, AC5). Proves `require_role()` end-to-end "
        "against a real endpoint -- every registered account holds at "
        "least one of the platform's three roles, so this is reachable "
        "by any authenticated caller."
    ),
)
async def get_me(
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)  # noqa: B008
    ),
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[UserSummaryResponse]:
    """Return the caller's own id/roles/status."""
    user, roles = await auth_service.get_current_user_summary(current_user.id)
    return SuccessResponse[UserSummaryResponse](
        success=True,
        message="Profile retrieved.",
        data=UserSummaryResponse(
            id=user.id,
            phone_country_code=user.phone_country_code,
            phone_number=user.phone_number,
            status=user.status,
            preferred_language=user.preferred_language,
            roles=roles,
        ),
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
        "Verifies a 6-digit OTP code and returns a JWT access token plus "
        "a refresh token. Transparently creates a new Account (with the "
        "`customer` role) if the phone number is not yet registered, or "
        "authenticates the existing Account otherwise — the client never "
        "needs to know in advance which will happen. Records/updates a "
        "Device row for the signing-in device (AUTH-003)."
    ),
)
async def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify an OTP code, then authenticate (creating the Account if new)."""
    ip_address, user_agent = _client_context(request)
    (
        user,
        access_token,
        refresh_token,
        roles,
    ) = await auth_service.verify_otp_and_authenticate(
        payload.phone_country_code,
        payload.phone_number,
        payload.code,
        payload.device.device_platform,
        payload.device.device_name,
        ip_address,
        user_agent,
        request.headers.get("accept-language"),
    )
    await db.commit()

    return SuccessResponse[AuthTokenResponse](
        success=True,
        message="Signed in successfully.",
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
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
    request: Request,
    db: AsyncSession,
    oauth_service: OAuthService,
    auth_service: AuthService,
) -> SuccessResponse[AuthTokenResponse]:
    """
    Shared orchestration for both OAuth endpoints below: verify the ID
    token server-side (never trust a client-asserted identity — AC2),
    then find-or-create the Account and start a session (AC3/AC4/AC5,
    AUTH-003).
    """
    claims = await oauth_service.verify_identity(provider, payload.id_token)
    ip_address, user_agent = _client_context(request)
    (
        user,
        access_token,
        refresh_token,
        roles,
    ) = await auth_service.authenticate_with_oauth(
        provider,
        claims,
        payload.device.device_platform,
        payload.device.device_name,
        ip_address,
        user_agent,
        request.headers.get("accept-language"),
    )
    await db.commit()

    return SuccessResponse[AuthTokenResponse](
        success=True,
        message="Signed in successfully.",
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
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
        "returns a JWT access token plus a refresh token. Transparently "
        "creates a new Account (with the `customer` role) if this is the "
        "first sign-in for the Google account, or authenticates the "
        "existing Account otherwise. A different provider previously "
        "used with the same email produces a second, independent Account "
        "by design."
    ),
)
async def sign_in_with_google(
    payload: OAuthSignInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    oauth_service: OAuthService = Depends(get_oauth_service),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify a Google ID token, then authenticate (creating the Account if new)."""
    return await _sign_in_with_oauth(
        AuthProvider.GOOGLE, payload, request, db, oauth_service, auth_service
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
        "and returns a JWT access token plus a refresh token. "
        "Transparently creates a new Account (with the `customer` role) "
        "if this is the first sign-in for the Apple account, or "
        "authenticates the existing Account otherwise. A different "
        "provider previously used with the same email produces a "
        "second, independent Account by design."
    ),
)
async def sign_in_with_apple(
    payload: OAuthSignInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    oauth_service: OAuthService = Depends(get_oauth_service),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Verify an Apple identity token, creating the Account if it's new."""
    return await _sign_in_with_oauth(
        AuthProvider.APPLE, payload, request, db, oauth_service, auth_service
    )


@router.post(
    "/refresh",
    response_model=SuccessResponse[AuthTokenResponse],
    dependencies=[Depends(_refresh_rate_limiter)],
    responses={
        200: {
            "model": SuccessResponse[AuthTokenResponse],
            "description": "A new access/refresh token pair was issued.",
        },
        401: {
            "description": (
                "The refresh token was not found, expired, already used "
                "(rotated away), or revoked. The response never reveals "
                "which."
            ),
        },
        429: {
            "description": "Too many requests from this client.",
        },
    },
    summary="Rotate a Refresh Token",
    description=(
        "Exchanges a valid, unexpired refresh token for a new "
        "access/refresh pair, invalidating the presented refresh token "
        "(rotation, AC4). Reusing an already-rotated-away or revoked "
        "refresh token is rejected and, as hardening, revokes the whole "
        "session (AC5)."
    ),
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    session_service: SessionService = Depends(get_session_service),  # noqa: B008
) -> SuccessResponse[AuthTokenResponse]:
    """Rotate a refresh token, issuing a new access/refresh pair."""
    user, roles, access_token, new_refresh_token = await session_service.refresh(
        payload.refresh_token
    )
    await db.commit()

    return SuccessResponse[AuthTokenResponse](
        success=True,
        message="Token refreshed successfully.",
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
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


@router.get(
    "/sessions",
    response_model=SuccessResponse[list[SessionSummaryResponse]],
    responses={
        200: {
            "model": SuccessResponse[list[SessionSummaryResponse]],
            "description": "The caller's active sessions.",
        },
        401: {"description": "Authentication required."},
    },
    summary="List Active Sessions",
    description=(
        "Lists the caller's active sessions with device name, platform, "
        "and last-seen time, flagging the current one (AC7). "
        "Deliberately unpaginated — a user's realistic session count is "
        "small and per-owner."
    ),
)
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session_service: SessionService = Depends(get_session_service),  # noqa: B008
) -> SuccessResponse[list[SessionSummaryResponse]]:
    """List the caller's active sessions."""
    items = await session_service.list_active_sessions(
        current_user.id, current_user.session_id
    )
    return SuccessResponse[list[SessionSummaryResponse]](
        success=True,
        message="Active sessions retrieved.",
        data=[
            SessionSummaryResponse(
                id=item.id,
                device_name=item.device_name,
                platform=item.platform,
                last_seen_at=item.last_seen_at,
                created_at=item.created_at,
                is_current=item.is_current,
            )
            for item in items
        ],
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessResponse[None],
    responses={
        200: {
            "model": SuccessResponse[None],
            "description": "The session was revoked.",
        },
        401: {"description": "Authentication required."},
        404: {
            "description": (
                "The session does not exist, or does not belong to the "
                "caller — the response never reveals which (AC10)."
            ),
        },
    },
    summary="Revoke a Single Session",
    description=(
        "Revokes one session and every refresh token in its chain "
        "(AC8). A subsequent refresh attempt with that session's "
        "refresh token fails."
    ),
)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session_service: SessionService = Depends(get_session_service),  # noqa: B008
) -> SuccessResponse[None]:
    """Revoke a single session owned by the caller."""
    ip_address, _user_agent = _client_context(request)
    await session_service.revoke_session(
        current_user.id,
        session_id,
        current_session_id=current_user.session_id,
        ip_address=ip_address,
    )
    await db.commit()
    return SuccessResponse[None](success=True, message="Session revoked.", data=None)


@router.post(
    "/sessions/logout-all",
    response_model=SuccessResponse[None],
    responses={
        200: {
            "model": SuccessResponse[None],
            "description": "Every session was revoked.",
        },
        401: {"description": "Authentication required."},
    },
    summary="Log Out Everywhere",
    description=(
        "Revokes every active session for the caller, optionally "
        "excluding the current one (`keep_current`). A distinct, "
        "separately labeled action from `DELETE /auth/sessions/{id}` "
        "(AC9)."
    ),
)
async def logout_all_sessions(
    payload: LogoutAllRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session_service: SessionService = Depends(get_session_service),  # noqa: B008
) -> SuccessResponse[None]:
    """Revoke every session for the caller (optionally keeping the current one)."""
    ip_address, _user_agent = _client_context(request)
    await session_service.revoke_all_sessions(
        current_user.id,
        current_user.session_id,
        payload.keep_current,
        ip_address=ip_address,
    )
    await db.commit()
    return SuccessResponse[None](
        success=True, message="Signed out of all sessions.", data=None
    )
