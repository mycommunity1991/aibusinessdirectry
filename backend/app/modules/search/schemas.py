"""
Request/response schemas for the `search` module (DIR-001, Backend
Proposed Changes item 3, `Plan_S06_DIR-001.md`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.provider.models import ProviderType
from app.modules.search.models import SearchRequestStatus


class SearchResultProviderResponse(BaseModel):
    """
    One provider result row for `GET /search/providers` (AC3).

    `average_rating`/`review_count` are the raw, honestly-nullable
    `providers` columns as stored (Decision 2) -- `average_rating` is
    `None` for every provider today (no Review domain exists yet); no
    synthesized `0.0` default is ever substituted here. Rendering
    "No reviews yet" vs. `"4.8 (3 reviews)"` is a mobile/frontend
    concern over this raw shape, not a backend one.
    """

    id: uuid.UUID
    display_name: str
    slug: str
    provider_type: ProviderType
    category_labels: list[str] = Field(default_factory=list)
    primary_photo_url: str | None = None
    average_rating: Decimal | None = None
    review_count: int
    distance_meters: float = Field(
        ..., description="Great-circle distance from the search origin, in meters."
    )
    is_claimed: bool = Field(
        ...,
        description=(
            "CLM-001, Decision 8 -- `false` for a still-unclaimed "
            "Google-seeded listing, driving the mobile card's full-width "
            "Warning-color 'Unclaimed' banner. Server-driven off this one "
            "boolean; never inferred client-side from other signals."
        ),
    )


class CategoryOptionResponse(BaseModel):
    """
    One distinct category label in use by a discoverable provider (AC2/
    Decision 1) -- backs `GET /search/categories`'s mobile category-chip
    picker.
    """

    label: str


class MatchedProviderResponse(BaseModel):
    """
    One matched provider row for `GET /search-requests/{id}` (AI-002,
    Decision 6) -- identical shape regardless of whether the underlying
    `search_requests` row was resolved automatically or by an admin
    (AC4), since both paths write `provider_matches` through the same
    `SearchRequestService._finalize_matches` helper.

    A **new** response schema, not a reuse of `SearchResultProviderResponse`
    (DIR-001), precisely because `distance_meters` here is nullable --
    `NULL` only when the request's customer had no default saved address
    (Decision 2c) or the matched provider's own location cannot be
    resolved, never estimated.
    """

    id: uuid.UUID
    display_name: str
    slug: str
    provider_type: ProviderType
    category_labels: list[str] = Field(default_factory=list)
    primary_photo_url: str | None = None
    average_rating: Decimal | None = None
    review_count: int
    distance_meters: float | None = Field(
        None,
        description=(
            "Great-circle distance from the search origin, in meters -- "
            "`null` only when no origin location or provider location "
            "could be resolved (Decision 2c), never estimated."
        ),
    )
    is_claimed: bool


class SearchRequestResultResponse(BaseModel):
    """
    Response payload for `GET /search-requests/{id}` (AI-002, Decision
    6) -- the customer's ranked-results screen, identical in shape
    whether the request was resolved by the automated matcher or by an
    admin (AC4). While `status=pending_manual_match`, `matched_providers`
    is an empty list -- the mobile client's own polling/waiting-state
    copy (never "manual"/"fallback"/"admin", AC3) is what distinguishes
    "still waiting" from "matched with zero results" (`unmatched`).
    """

    status: SearchRequestStatus
    matched_providers: list[MatchedProviderResponse] = Field(default_factory=list)


class ManualMatchAssignmentSummaryResponse(BaseModel):
    """
    One admin-queue list item for `GET /admin/search/manual-matches`
    (AI-002, Decision 3) -- the pull-based "notify an admin" mechanism.
    Deliberately does not include the session's `messages` transcript
    (Explicitly Out of Scope, `Plan_S07_AI-002.md`) -- `ADM-001`'s job to
    design; `conversation_session_id` is included so a future admin UI
    has everything it needs to add that later.
    """

    id: uuid.UUID
    conversation_session_id: uuid.UUID
    search_request_id: uuid.UUID | None
    status: str
    created_at: datetime


class ResolveManualMatchRequest(BaseModel):
    """
    Request payload for `POST /admin/search/manual-matches/{assignment_id}
    /resolve` (AI-002, Decision 4). An empty `provider_ids` list is
    valid -- "no viable match found" resolves to `unmatched`, not a
    validation error.
    """

    provider_ids: list[uuid.UUID] = Field(default_factory=list)
