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
