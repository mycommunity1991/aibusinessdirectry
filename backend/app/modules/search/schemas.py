"""
Request/response schemas for the `search` module (DIR-001, Backend
Proposed Changes item 3, `Plan_S06_DIR-001.md`).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.provider.models import ProviderType


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


class CategoryOptionResponse(BaseModel):
    """
    One distinct category label in use by a discoverable provider (AC2/
    Decision 1) -- backs `GET /search/categories`'s mobile category-chip
    picker.
    """

    label: str
