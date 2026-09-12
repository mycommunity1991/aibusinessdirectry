import uuid

from pydantic import BaseModel, Field


class CreateContactViewRequest(BaseModel):
    """
    Request payload for `POST /contact-views` (CON-001, AC2) -- tapping
    Contact on a matched provider.
    """

    provider_id: uuid.UUID = Field(..., description="The provider being contacted.")
    search_request_id: uuid.UUID | None = Field(
        None,
        description=(
            "The originating `search_requests` row, if the customer "
            "reached this provider via the AI Conversation search path "
            "(Decision 4, `Plan_S08_CON-001.md`). Omitted for the "
            "structured search path, which creates no `search_requests` "
            "row at all. Must belong to the calling customer -- a "
            "mismatched or nonexistent id is rejected (404), never "
            "silently dropped."
        ),
    )


class ContactViewRevealResponse(BaseModel):
    """
    Response payload for a successful `POST /contact-views` (AC2) -- the
    Contact Reveal sheet's data: the provider's phone number, shown
    immediately, with no quote/approval/messaging step in between.
    """

    id: uuid.UUID = Field(..., description="The new Contact View's id.")
    provider_id: uuid.UUID
    provider_display_name: str
    phone_country_code: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
