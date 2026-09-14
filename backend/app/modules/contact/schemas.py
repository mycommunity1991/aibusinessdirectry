import uuid
from datetime import date as date_
from datetime import datetime
from enum import StrEnum

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


class SubmitOutcomeTagRequest(BaseModel):
    """
    Request payload for `POST /contact-views/{contact_view_id}/
    outcome-tag` (REV-001, AC1) -- the minimal "did you hire them?"
    yes/no. Deliberately carries no payment amount, job-completion
    detail, or scheduling field (AC4).
    """

    hired: bool = Field(..., description="Did the customer hire this provider?")


class OutcomeTagResponse(BaseModel):
    """
    Response payload for a successfully submitted Outcome Tag
    (REV-001, AC1).
    """

    id: uuid.UUID
    contact_view_id: uuid.UUID
    hired: bool
    submitted_at: datetime


class LeadOutcomeStatus(StrEnum):
    """
    LEAD-001, Decision 5, `Plan_S10_LEAD-001.md` -- the three-state
    outcome status a Lead's `OutcomeTag` (if any) maps onto, computed
    server-side (never the raw boolean or a raw-row absence left for the
    client to interpret). Mirrors `search/models.py`'s own
    `SearchRequestStatus` `StrEnum` shape.
    """

    HIRED = "hired"
    NOT_HIRED = "not_hired"
    NOT_YET_REPORTED = "not_yet_reported"


class LeadResponse(BaseModel):
    """
    Response payload for one row of `GET /providers/me/leads`
    (LEAD-001, AC1, Decision 4) -- deliberately carries no
    `customer_id`/`provider_id`/PII field: no customer name, avatar,
    phone, or raw customer id anywhere on this shape. `category_name`
    is `null` whenever Decision 3's two-hop lookup dead-ends (never a
    fabricated fallback) -- the mobile client renders an honest fallback
    string in that case.
    """

    id: uuid.UUID = Field(..., description="The underlying Contact View's own id.")
    category_name: str | None = Field(
        None,
        description=(
            "The category this lead was reached through, if resolvable "
            "(Decision 3). `null` when the Contact View has no "
            "`search_request_id`, or when that search request's own "
            "`category_id` is `null` -- never a fabricated substitute."
        ),
    )
    viewed_at: datetime = Field(
        ..., description="When the customer viewed this provider's contact details."
    )
    outcome_status: LeadOutcomeStatus = Field(
        ..., description="Hired / Not hired / not yet reported (Decision 5)."
    )


class TrendDirection(StrEnum):
    """
    LEAD-002, Decision 5, `Plan_S10_LEAD-002.md` -- the three-state
    trend indicator each Visibility Analytics headline stat carries,
    computed server-side (never a raw percentage the mobile client would
    have to render, and never left for the client to derive itself).
    Mirrors `LeadOutcomeStatus`'s own plain three-state `StrEnum` shape.
    """

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class VisibilityDailyPoint(BaseModel):
    """
    One zero-filled day of the 30-day daily series (LEAD-002, AC2,
    Decision 4) -- carries only plain integer counts, never a
    per-event/per-customer detail (Decision 8).
    """

    date: date_ = Field(..., description="The calendar day this point covers (UTC).")
    search_appearances: int = Field(
        ..., description="How many times this provider appeared in search results."
    )
    contact_views: int = Field(
        ..., description="How many times this provider's contact details were viewed."
    )


class VisibilityMetric(BaseModel):
    """One headline stat's current-30-day total plus its three-state
    trend (LEAD-002, AC1, Decision 5)."""

    total_last_30_days: int = Field(
        ..., description="The metric's total over the current 30-day window."
    )
    trend: TrendDirection = Field(
        ...,
        description=(
            "Up/down/flat versus the immediately preceding 30-day window "
            "(Decision 5)."
        ),
    )


class VisibilityAnalyticsResponse(BaseModel):
    """
    Response payload for `GET /providers/me/visibility-analytics`
    (LEAD-002, AC1/AC2/AC4, Decision 3) -- one synthesized,
    non-paginated object, mirroring `GET /providers/me/availability`'s
    shape. Deliberately carries no customer-identifying or per-event
    field anywhere on this shape (Decision 8) -- no customer id, no raw
    `search_event_log`/`contact_views` row, no `query_text`, no category
    breakdown.
    """

    has_sufficient_data: bool = Field(
        ...,
        description=(
            "`false` for a newly-onboarded provider with little or no "
            "history (AC4, Decision 6) -- `true` when either headline "
            "stat's current-30-day total is greater than zero. The real "
            "(possibly all-zero) numbers and a fully zero-filled chart "
            "series are still returned alongside this flag; the mobile "
            "client branches on this boolean, never re-derives it."
        ),
    )
    search_appearances: VisibilityMetric = Field(
        ..., description="How often this provider appeared in search results."
    )
    contact_views: VisibilityMetric = Field(
        ..., description="How often this provider's contact details were viewed."
    )
    daily_trend: list[VisibilityDailyPoint] = Field(
        ...,
        description=(
            "Exactly `VISIBILITY_ANALYTICS_WINDOW_DAYS` ascending-date "
            "entries, ending today, zero-filled for any day with no "
            "events (Decision 4)."
        ),
    )
