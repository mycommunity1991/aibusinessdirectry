"""
Request/response schemas for the `administration` module's first-ever
`api.py` (ADM-001, Decision 6/9, `Plan_S11_ADM-001.md`).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UnmatchedQueryReportResponse(BaseModel):
    """
    One `unmatched_query_reports` row, enriched with its underlying
    `search_event_log` display context (Decision 6) -- `customer_id`/
    `query_text` are exposed directly (Decision 9): this is an admin
    operational tool reviewing a specific case, not a provider-facing
    "Analytics" surface `06_SECURITY.md`'s Sensitive Data restriction
    targets. `query_text` currently always reads `null` -- a pre-existing
    AI-002 write-path gap (Decision 1), not something this story fixes.
    """

    id: uuid.UUID
    search_event_log_id: uuid.UUID
    status: str
    category_gap_notes: str | None
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    category_id: uuid.UUID | None = Field(
        None, description="Enriched from `search_event_log`, if the row still exists."
    )
    customer_id: uuid.UUID | None = Field(
        None, description="Enriched from `search_event_log`, if the row still exists."
    )
    query_text: str | None = Field(
        None,
        description=(
            "Enriched from `search_event_log` -- currently always `null` "
            "(a pre-existing AI-002 write-path gap, Decision 1)."
        ),
    )
    result_count: int | None = Field(
        None, description="Enriched from `search_event_log`, if the row still exists."
    )


class UnmatchedQueryReportActionRequest(BaseModel):
    """Request payload for both `/review` and `/action` (Decision 8) --
    admin-supplied notes on a spotted supply/category gap."""

    category_gap_notes: str | None = Field(
        None, max_length=2000, description="Optional admin notes on the gap spotted."
    )
