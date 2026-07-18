import uuid

from pydantic import BaseModel, Field

from app.core.constants import OTP_CODE_LENGTH


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
    """Response payload for a successful `POST /auth/verify-otp`."""

    access_token: str = Field(..., description="A short-lived JWT access token.")
    token_type: str = Field("bearer", description="The token type.")
    user: UserSummaryResponse = Field(..., description="The authenticated user.")
