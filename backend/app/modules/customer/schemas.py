import uuid

from pydantic import BaseModel, Field

from app.modules.customer.models import NotificationChannel
from app.modules.identity.models import LanguageCode


class CustomerProfileResponse(BaseModel):
    """Response payload for `GET`/`PATCH /customers/me` (AC4)."""

    id: uuid.UUID = Field(..., description="The customer profile's unique identifier.")
    display_name: str = Field(..., description="The customer's display name.")
    avatar_url: str | None = Field(
        None, description="A URL pointing to the customer's avatar image, if set."
    )
    language: LanguageCode = Field(
        ..., description="The customer's preferred language."
    )
    notification_channel: NotificationChannel = Field(
        ..., description="The customer's preferred notification channel."
    )


class UpdateCustomerProfileRequest(BaseModel):
    """
    Request payload for `PATCH /customers/me`. Partial update: only
    fields present in the payload are changed (Pydantic v2
    `exclude_unset=True`, Decision 5 of `Plan_S03_CUS-001.md`) -- an
    omitted field is left untouched, while `avatar_url: null` explicitly
    clears it.
    """

    display_name: str | None = Field(
        None,
        description="The customer's display name.",
        max_length=150,
        examples=["Fatima Al Mansoori"],
    )
    avatar_url: str | None = Field(
        None,
        description=(
            "A URL pointing to the customer's avatar image. A plain string "
            "field -- this story does not implement file upload."
        ),
        max_length=500,
        examples=["https://example.com/avatars/fatima.png"],
    )
    language: LanguageCode | None = Field(
        None, description="The customer's preferred language."
    )
    notification_channel: NotificationChannel | None = Field(
        None, description="The customer's preferred notification channel."
    )


class SavedAddressResponse(BaseModel):
    """Response payload for a single saved address (CUS-002, AC1/AC6)."""

    id: uuid.UUID = Field(..., description="The saved address's unique identifier.")
    label: str | None = Field(None, description='A short label, e.g. "Home", "Work".')
    address_line: str = Field(..., description="The street address line.")
    city: str | None = Field(None, description="The city.")
    region: str | None = Field(None, description="The state/region/emirate.")
    country_code: str = Field(
        ..., description='ISO 3166-1 alpha-2 country code, e.g. "AE".'
    )
    latitude: float = Field(..., description="The address's latitude.")
    longitude: float = Field(..., description="The address's longitude.")
    is_default: bool = Field(
        ..., description="Whether this is the customer's default address."
    )


class CreateSavedAddressRequest(BaseModel):
    """Request payload for `POST /customers/me/addresses` (AC1/AC3)."""

    label: str | None = Field(
        None,
        description='A short label, e.g. "Home", "Work".',
        max_length=50,
        examples=["Home"],
    )
    address_line: str = Field(
        ...,
        description="The street address line.",
        max_length=500,
        examples=["Villa 12, Al Wasl Road"],
    )
    city: str | None = Field(None, description="The city.", max_length=100)
    region: str | None = Field(
        None, description="The state/region/emirate.", max_length=100
    )
    country_code: str = Field(
        ...,
        description='ISO 3166-1 alpha-2 country code, e.g. "AE".',
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        examples=["AE"],
    )
    latitude: float = Field(..., ge=-90, le=90, description="The address's latitude.")
    longitude: float = Field(
        ..., ge=-180, le=180, description="The address's longitude."
    )
    is_default: bool = Field(
        False,
        description=(
            "Whether to mark this as the default address. Setting `true` "
            "unsets any previously-default address for this customer "
            "(AC2)."
        ),
    )


class UpdateSavedAddressRequest(BaseModel):
    """
    Request payload for `PATCH /customers/me/addresses/{address_id}`.
    Partial update: only fields present in the payload are changed
    (Pydantic v2 `exclude_unset=True`, mirroring
    `UpdateCustomerProfileRequest`'s partial-update pattern).
    """

    label: str | None = Field(
        None, description='A short label, e.g. "Home", "Work".', max_length=50
    )
    address_line: str | None = Field(
        None, description="The street address line.", max_length=500
    )
    city: str | None = Field(None, description="The city.", max_length=100)
    region: str | None = Field(
        None, description="The state/region/emirate.", max_length=100
    )
    country_code: str | None = Field(
        None,
        description='ISO 3166-1 alpha-2 country code, e.g. "AE".',
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )
    latitude: float | None = Field(
        None, ge=-90, le=90, description="The address's latitude."
    )
    longitude: float | None = Field(
        None, ge=-180, le=180, description="The address's longitude."
    )
    is_default: bool | None = Field(
        None,
        description=(
            "Whether to mark this as the default address. Setting `true` "
            "unsets any previously-default address for this customer "
            "(AC2)."
        ),
    )
