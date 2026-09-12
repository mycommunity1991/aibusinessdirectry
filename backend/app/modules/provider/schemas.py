from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.provider.models import ProviderType, VerificationStatus, Weekday

_COUNTRY_CODE_PATTERN = r"^[A-Z]{2}$"
_HOUR_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"
_MAX_CATEGORY_LABELS = 5


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


class CategoryLabelInput(BaseModel):
    """One free-text category label in a `PATCH /providers/me`
    `category_labels` replace payload (PRO-002, Decision 1,
    `Plan_S04_PRO-002.md`)."""

    label: str = Field(..., max_length=100, description='e.g. "Plumbing".')
    is_primary: bool = Field(
        default=False, description="Exactly one label in the set must be primary."
    )


class CategoryLabelResponse(BaseModel):
    """Response shape mirroring `CategoryLabelInput`."""

    label: str
    is_primary: bool


class ProviderResponse(BaseModel):
    """Response payload for `GET`/`POST /providers/me`."""

    id: uuid.UUID = Field(..., description="The provider's unique identifier.")
    provider_type: ProviderType
    display_name: str
    phone_country_code: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    category_labels: list[CategoryLabelResponse] = Field(
        default_factory=list,
        description=(
            "PRO-002, Decision 1 -- a deliberate breaking change from "
            "PRO-001's singular `category_label` string, since this API "
            "has no external consumers yet."
        ),
    )
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


class UpdateBusinessDetailsRequest(BaseModel):
    """
    Partial update of a Business Provider's subtype details for `PATCH
    /providers/me` (PRO-002). Same fields as `CreateBusinessDetailsRequest`,
    all optional (`exclude_unset` semantics) -- deliberately excludes
    `country_code`, which is not editable via this story's surface.
    """

    address_line: str | None = Field(None, max_length=500)
    city: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    operating_hours: dict[str, OperatingHoursEntry | None] | None = None
    delivery_radius_meters: int | None = Field(None, gt=0)
    trade_license_number: str | None = Field(None, max_length=100)


class UpdateFreelancerDetailsRequest(BaseModel):
    """
    Partial update of a Freelancer Provider's subtype details for `PATCH
    /providers/me` (PRO-002). Same fields as
    `CreateFreelancerDetailsRequest`, all optional -- deliberately
    excludes `country_code`.
    """

    base_latitude: float | None = Field(None, ge=-90, le=90)
    base_longitude: float | None = Field(None, ge=-180, le=180)
    service_radius_meters: int | None = Field(None, gt=0)
    skills: list[str] | None = None
    years_experience: int | None = Field(None, ge=0)


class UpdateProviderRequest(BaseModel):
    """
    Request payload for `PATCH /providers/me` (PRO-002, AC5) -- partial
    update of basic info, category labels, and subtype-specific details.
    Only fields actually present in the request body are applied
    (`exclude_unset`, enforced at the API layer via
    `payload.model_dump(exclude_unset=True)`). `provider_type` is
    deliberately not a field here at all -- it remains immutable
    (PRO-001, Decision 3).
    """

    display_name: str | None = Field(None, max_length=200)
    phone_country_code: str | None = Field(None, max_length=5)
    phone_number: str | None = Field(None, max_length=20)
    whatsapp_number: str | None = Field(None, max_length=20)
    description: str | None = None
    category_labels: list[CategoryLabelInput] | None = Field(
        None,
        max_length=_MAX_CATEGORY_LABELS,
        description=(
            "When present, replaces the provider's entire label set "
            "(Decision 1, `Plan_S04_PRO-002.md`) -- capped at 5, exactly "
            "one must be `is_primary=true`."
        ),
    )
    business_details: UpdateBusinessDetailsRequest | None = Field(
        None,
        description=(
            "Rejected (400) if the provider's actual `provider_type` is "
            "not `business` (Decision 8, `Plan_S04_PRO-002.md`)."
        ),
    )
    freelancer_details: UpdateFreelancerDetailsRequest | None = Field(
        None,
        description=(
            "Rejected (400) if the provider's actual `provider_type` is "
            "not `freelancer`."
        ),
    )


class PortfolioPhotoResponse(BaseModel):
    """Response payload for one of the caller's own portfolio photos
    (PRO-002, AC2)."""

    id: uuid.UUID
    media_url: str = Field(
        ..., description="A relative, served URL path, e.g. `/media/portfolios/...`."
    )
    caption: str | None = None
    sort_order: int


class ReorderPortfolioRequest(BaseModel):
    """
    Request payload for `PUT /providers/me/portfolio/order` (PRO-002,
    Decision 4). Must be exactly the full set of the caller's own active
    photo ids -- no more, no fewer, no duplicates -- or the request is
    rejected (422) before any row is touched.
    """

    ordered_ids: list[uuid.UUID] = Field(
        ..., description="The caller's own active photo ids, in the desired order."
    )


class WeekdayAvailabilityInput(BaseModel):
    """
    One weekday's availability in a `PUT /providers/me/availability`
    request (PRO-002, AC3). `is_open=true` requires both `open_time` and
    `close_time`; `is_open=false` requires neither.
    """

    weekday: Weekday
    is_open: bool
    open_time: str | None = Field(
        None, pattern=_HOUR_PATTERN, description='24-hour "HH:MM".'
    )
    close_time: str | None = Field(
        None, pattern=_HOUR_PATTERN, description='24-hour "HH:MM".'
    )
    is_emergency_available: bool = Field(
        default=False, description="A separate urgent/emergency-availability flag."
    )

    @model_validator(mode="after")
    def _validate_times_match_is_open(self) -> WeekdayAvailabilityInput:
        if self.is_open:
            if self.open_time is None or self.close_time is None:
                raise ValueError("is_open=true requires both open_time and close_time.")
        elif self.open_time is not None or self.close_time is not None:
            raise ValueError(
                "is_open=false requires open_time and close_time to be null."
            )
        return self


class WeekdayAvailabilityResponse(BaseModel):
    """Response shape mirroring `WeekdayAvailabilityInput` -- always
    returned as exactly 7 entries (Decision 3, `Plan_S04_PRO-002.md`)."""

    weekday: Weekday
    is_open: bool
    open_time: str | None = None
    close_time: str | None = None
    is_emergency_available: bool


class UpdateAvailabilityRequest(BaseModel):
    """
    Request payload for `PUT /providers/me/availability` (PRO-002,
    Decision 3) -- upserts up to seven weekday entries in one call.
    """

    entries: list[WeekdayAvailabilityInput] = Field(..., max_length=7)

    @model_validator(mode="after")
    def _validate_no_duplicate_weekdays(self) -> UpdateAvailabilityRequest:
        weekdays = [entry.weekday for entry in self.entries]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("Each weekday may appear at most once per request.")
        return self


class ClaimSearchResultResponse(BaseModel):
    """
    One unclaimed Google-seeded listing result for `GET /claims/search`
    (CLM-001, AC3, Decision 5, `Plan_S06_CLM-001.md`).

    `phone_number_masked` lets a searcher sanity-check "is this my
    number" without the full number being exposed to anyone who merely
    searched (e.g. `"+971 5*****67"`) -- `None` if the listing has no
    public number on record at all.
    """

    id: uuid.UUID
    display_name: str
    address_line: str | None = None
    city: str | None = None
    phone_number_masked: str | None = None


class VerifyClaimOtpRequest(BaseModel):
    """Request payload for `POST /claims/{provider_id}/verify-otp` (AC5)."""

    code: str = Field(..., min_length=4, max_length=10)


class RequestClaimAdminReviewRequest(BaseModel):
    """
    Request payload for `POST /claims/{provider_id}/request-admin-review`
    (AC6) -- the explicit "this isn't working" fallback.
    """

    reason: Literal["otp_failed", "no_public_number"] = Field(
        ...,
        description=(
            '"otp_failed" -- verification was attempted and failed/locked; '
            '"no_public_number" -- the listing has no usable public number, '
            "so OTP was never attempted."
        ),
    )


class ClaimResultResponse(BaseModel):
    """Response payload for a successful `POST
    /claims/{provider_id}/verify-otp` (AC5)."""

    provider_id: uuid.UUID
    is_claimed: bool
    verification_status: VerificationStatus


class AdminClaimReviewRequestResponse(BaseModel):
    """
    Response payload for the admin claim-review surface (CLM-001,
    Decision 9) -- `GET /admin/claims` and the `approve`/`reject`
    responses. Carries enough Provider context for an Admin acting
    across every listing's queue, mirroring `AdminVerificationRecordResponse`'s
    shape.
    """

    id: uuid.UUID
    provider_id: uuid.UUID
    provider_display_name: str
    claimant_user_id: uuid.UUID
    reason: str
    status: str
    resolution: str | None = None
    resolution_notes: str | None = None
    reviewed_at: datetime | None = None


class RejectClaimReviewRequest(BaseModel):
    """Request payload for `POST /admin/claims/{request_id}/reject`."""

    resolution_notes: str | None = Field(None, max_length=2000)


class PublicProviderProfileResponse(BaseModel):
    """
    Response payload for `GET /providers/{provider_id}` (CON-001, AC5,
    Decision 2, `Plan_S08_CON-001.md`) -- the customer-facing Provider
    Profile screen's data.

    `average_rating`/`review_count` are the raw, honestly-nullable
    `providers` columns as stored, mirroring `SearchResultProviderResponse`'s
    identical "never alone" pairing (AC5) -- `average_rating` is `None`
    for every provider today (no Review domain exists yet).

    `is_claimed`/`verification_status` are both returned as raw,
    unmodified fields (Decision 8) -- the client renders exactly one of
    three trust-badge states off them (`is_claimed` checked first, since
    a still-unclaimed, Google-seeded listing can have
    `verification_status=approved` too); the server never pre-computes a
    single display enum.

    `delivery_radius_meters` is populated only for a `provider_type=
    business` provider; `service_radius_meters` only for `freelancer`.
    `city`/`region` are Business-only (Freelancer has neither field on
    `freelancer_profiles`).

    Deliberately excludes `phone_number`/`whatsapp_number`/
    `phone_country_code` -- those are only ever revealed via the Contact
    Reveal flow (`POST /contact-views`), never on this profile read, so
    a customer cannot obtain the number without a real Contact View
    being recorded (AC2).
    """

    id: uuid.UUID
    provider_type: ProviderType
    display_name: str
    category_labels: list[CategoryLabelResponse] = Field(default_factory=list)
    description: str | None = None
    primary_photo_url: str | None = None
    average_rating: Decimal | None = None
    review_count: int
    is_claimed: bool
    verification_status: VerificationStatus
    weekly_availability: list[WeekdayAvailabilityResponse]
    city: str | None = None
    region: str | None = None
    delivery_radius_meters: int | None = None
    service_radius_meters: int | None = None
