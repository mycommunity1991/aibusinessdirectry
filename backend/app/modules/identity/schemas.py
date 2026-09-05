import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import OTP_CODE_LENGTH
from app.modules.identity.models import DevicePlatform


class DeviceContext(BaseModel):
    """
    Client-supplied device context (AUTH-003, AC6), required on every
    login-shaped request (`verify-otp`/`google`/`apple`) so a `Device`
    row can be recorded/updated. No client-generated device ID exists in
    the documented schema (Decision 2, `Plan_S02_AUTH-003.md`) -- the
    find-or-update key is `(user_id, platform, device_name)`.
    """

    device_platform: DevicePlatform = Field(
        ..., description="The device's operating system.", examples=["ios"]
    )
    device_name: str | None = Field(
        None,
        description='A human-readable device label, e.g. "iPhone 15".',
        max_length=255,
        examples=["iPhone 15"],
    )


class RequestOtpRequest(BaseModel):
    """Request payload for `POST /auth/request-otp`."""

    phone_country_code: str = Field(
        ...,
        description="The phone number's country calling code, e.g. +971.",
        pattern=r"^\+[1-9]\d{0,3}$",
        examples=["+971"],
    )
    phone_number: str = Field(
        ...,
        description="The subscriber number, without the country code.",
        min_length=4,
        max_length=20,
        pattern=r"^\d{4,20}$",
        examples=["501234567"],
    )


class RequestOtpResponse(BaseModel):
    """
    Response payload for a successful `POST /auth/request-otp`.

    Carries no information about whether the phone number is registered
    (AC5's non-revealing guarantee) — `expires_in_seconds` is always the
    same server-configured value, letting the client size its resend
    countdown from the actual OTP expiry instead of a hardcoded duplicate
    constant (FU-2).
    """

    expires_in_seconds: int = Field(
        ...,
        description="How long the requested OTP code remains valid, in seconds.",
        examples=[300],
    )


class VerifyOtpRequest(BaseModel):
    """Request payload for `POST /auth/verify-otp`."""

    phone_country_code: str = Field(
        ...,
        description="The phone number's country calling code, e.g. +971.",
        pattern=r"^\+[1-9]\d{0,3}$",
        examples=["+971"],
    )
    phone_number: str = Field(
        ...,
        description="The subscriber number, without the country code.",
        min_length=4,
        max_length=20,
        pattern=r"^\d{4,20}$",
        examples=["501234567"],
    )
    code: str = Field(
        ...,
        description="The 6-digit OTP code sent to the phone number.",
        min_length=OTP_CODE_LENGTH,
        max_length=OTP_CODE_LENGTH,
        pattern=r"^\d{6}$",
        examples=["123456"],
    )
    device: DeviceContext = Field(
        ..., description="The signing-in device's context (AUTH-003, AC6)."
    )


class OAuthSignInRequest(BaseModel):
    """Request payload for `POST /auth/google` and `POST /auth/apple`."""

    id_token: str = Field(
        ...,
        description=(
            "The provider-issued identity token (Google or Apple), "
            "obtained by the client from the provider's native sign-in "
            "SDK. Verified server-side against the provider's public "
            "keys before any account is created or authenticated -- the "
            "client's assertion of identity is never trusted directly."
        ),
        min_length=1,
        examples=["eyJhbGciOiJSUzI1NiIsImtpZCI6Ii4uLiJ9..."],
    )
    device: DeviceContext = Field(
        ..., description="The signing-in device's context (AUTH-003, AC6)."
    )


class UserSummaryResponse(BaseModel):
    """A minimal summary of the authenticated user, returned on verify-otp."""

    id: uuid.UUID = Field(..., description="The user's unique identifier.")
    phone_country_code: str | None = Field(
        None, description="The user's phone country calling code."
    )
    phone_number: str | None = Field(None, description="The user's phone number.")
    status: str = Field(..., description="The user's account status.")
    preferred_language: str = Field(..., description="The user's preferred language.")
    roles: list[str] = Field(
        default_factory=list, description="The role names assigned to this user."
    )


class AuthTokenResponse(BaseModel):
    """
    Response payload for a successful `POST /auth/verify-otp`/`google`/
    `apple`/`refresh`. Every login (or refresh) now mints a session and
    refresh token, not only an access token (AUTH-003).
    """

    access_token: str = Field(..., description="A short-lived JWT access token.")
    refresh_token: str = Field(
        ...,
        description=(
            "An opaque refresh token. Store securely; use it against "
            "`POST /auth/refresh` to obtain a new access/refresh pair "
            "once the access token expires."
        ),
    )
    token_type: str = Field("bearer", description="The token type.")
    user: UserSummaryResponse = Field(..., description="The authenticated user.")


class RefreshTokenRequest(BaseModel):
    """Request payload for `POST /auth/refresh`."""

    refresh_token: str = Field(
        ..., description="The opaque refresh token issued at the last login/refresh."
    )


class SessionSummaryResponse(BaseModel):
    """A single entry of `GET /auth/sessions`' response (AC7)."""

    id: uuid.UUID = Field(..., description="The session's unique identifier.")
    device_name: str | None = Field(
        None, description="The signed-in device's human-readable name, if known."
    )
    platform: str | None = Field(
        None, description="The signed-in device's platform (ios/android), if known."
    )
    last_seen_at: datetime | None = Field(
        None, description="When this device was last seen, if known."
    )
    created_at: datetime = Field(..., description="When this session was created.")
    is_current: bool = Field(
        ..., description="Whether this is the session the caller is using right now."
    )


class LogoutAllRequest(BaseModel):
    """Request payload for `POST /auth/sessions/logout-all` (AC9)."""

    keep_current: bool = Field(
        False,
        description=(
            "If true, the caller's own current session is kept active; "
            "every other session is revoked. A distinct, separately "
            "labeled action from `DELETE /auth/sessions/{session_id}`."
        ),
    )
