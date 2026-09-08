from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.modules.provider.models import ProviderType, VerificationStatus

_COUNTRY_CODE_PATTERN = r"^[A-Z]{2}$"
_HOUR_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class OperatingHoursEntry(BaseModel):
    """One weekday's open/close time, per `04_DATABASE.md`'s
    `business_profiles.operating_hours` JSONB shape (AC5)."""

    open: str = Field(
        ..., pattern=_HOUR_PATTERN, description='24-hour "HH:MM", e.g. "09:00".'
    )
    close: str = Field(
        ..., pattern=_HOUR_PATTERN, description='24-hour "HH:MM", e.g. "18:00".'
    )


class CreateBusinessDetailsRequest(BaseModel):
    """Business-subtype details for `POST /providers/me` (AC5)."""

    address_line: str = Field(
        ..., max_length=500, description="The business's street address line."
    )
    city: str | None = Field(None, max_length=100, description="The city.")
    region: str | None = Field(
        None, max_length=100, description="The state/region/emirate."
    )
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=_COUNTRY_CODE_PATTERN,
        description=(
            'ISO 3166-1 alpha-2 country code, e.g. "AE" -- reverse-'
            "geocoded client-side via `LocationPickerScreen` (Decision "
            "6, `Plan_S04_PRO-001.md`). Copied up onto `providers."
            "country_code`."
        ),
        examples=["AE"],
    )
    latitude: float = Field(..., ge=-90, le=90, description="The address's latitude.")
    longitude: float = Field(
        ..., ge=-180, le=180, description="The address's longitude."
    )
    operating_hours: dict[str, OperatingHoursEntry | None] | None = Field(
        None,
        description=(
            "Weekly operating hours keyed by lowercase weekday name "
            '(e.g. "monday"); `null` for a closed day.'
        ),
    )
    delivery_radius_meters: int | None = Field(
        None, gt=0, description="Optional delivery radius beyond the fixed location."
    )
    trade_license_number: str | None = Field(
        None, max_length=100, description="Optional trade license number."
    )


class CreateFreelancerDetailsRequest(BaseModel):
    """Freelancer-subtype details for `POST /providers/me` (AC6)."""

    base_latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Center point of the freelancer's travel radius.",
    )
    base_longitude: float = Field(..., ge=-180, le=180)
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=_COUNTRY_CODE_PATTERN,
        description=(
            "ISO 3166-1 alpha-2 country code -- flows to `providers."
            "country_code` only, not persisted on `freelancer_profiles` "
            "(Decision 6, `Plan_S04_PRO-001.md`)."
        ),
        examples=["AE"],
    )
    service_radius_meters: int = Field(
        ..., gt=0, description="The freelancer's service radius, in meters."
    )
    skills: list[str] | None = Field(
        None, description='Free-text skill tags, e.g. ["Plumbing", "AC Repair"].'
    )
    years_experience: int | None = Field(
        None, ge=0, description="Years of professional experience."
    )


class CreateProviderRequest(BaseModel):
    """
    Request payload for `POST /providers/me` -- submitted exactly once,
    at the end of the mobile onboarding wizard (Decision 2,
    `Plan_S04_PRO-001.md`), containing type + basic info + subtype
    details together.
    """

    provider_type: ProviderType = Field(
        ..., description="Business or Freelancer -- immutable after creation (AC3)."
    )
    display_name: str = Field(
        ..., max_length=200, description="The provider's display name."
    )
    phone_country_code: str = Field(..., max_length=5, examples=["+971"])
    phone_number: str = Field(..., max_length=20)
    whatsapp_number: str | None = Field(None, max_length=20)
    category_label: str = Field(
        ...,
        max_length=100,
        description=(
            'Free-text category, e.g. "Plumbing" (Decision 4, '
            "`Plan_S04_PRO-001.md` -- a temporary stand-in for the "
            "not-yet-built Category domain)."
        ),
    )
    description: str | None = Field(
        None, description="An optional free-text description."
    )
    business_details: CreateBusinessDetailsRequest | None = Field(
        None, description="Required when `provider_type=business`."
    )
    freelancer_details: CreateFreelancerDetailsRequest | None = Field(
        None, description="Required when `provider_type=freelancer`."
    )

    @model_validator(mode="after")
    def _validate_subtype_details_match_type(self) -> CreateProviderRequest:
        """
        Enforces exactly one of `business_details`/`freelancer_details`
        is present and matches `provider_type` (AC3/AC4, schema item 12,
        `Plan_S04_PRO-001.md`) -- rejected here (422) before ever
        reaching `ProviderService`.
        """
        if self.provider_type == ProviderType.BUSINESS:
            if self.business_details is None or self.freelancer_details is not None:
                raise ValueError(
                    "provider_type=business requires business_details and "
                    "must not include freelancer_details."
                )
        else:
            if self.freelancer_details is None or self.business_details is not None:
                raise ValueError(
                    "provider_type=freelancer requires freelancer_details and "
                    "must not include business_details."
                )
        return self


class BusinessProfileResponse(BaseModel):
    """Response payload for a Provider's Business subtype details."""

    address_line: str
    city: str | None = None
    region: str | None = None
    latitude: float
    longitude: float
    operating_hours: dict[str, Any] | None = None
    delivery_radius_meters: int | None = None
    trade_license_number: str | None = None


class FreelancerProfileResponse(BaseModel):
    """Response payload for a Provider's Freelancer subtype details."""

    base_latitude: float
    base_longitude: float
    service_radius_meters: int
    skills: list[str] | None = None
    years_experience: int | None = None


class ProviderResponse(BaseModel):
    """Response payload for `GET`/`POST /providers/me`."""

    id: uuid.UUID = Field(..., description="The provider's unique identifier.")
    provider_type: ProviderType
    display_name: str
    phone_country_code: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    category_label: str
    description: str | None = None
    slug: str = Field(
        ..., description="Server-generated; used in shareable profile deep links."
    )
    verification_status: VerificationStatus
    is_discoverable: bool = Field(
        ...,
        description=(
            "Always `false` on a freshly created Provider (AC7) -- flips "
            "to `true` only once VER-001's Verification gate approves it."
        ),
    )
    country_code: str
    business_profile: BusinessProfileResponse | None = None
    freelancer_profile: FreelancerProfileResponse | None = None
