"""
Request/response schemas for the `administration` module's `api.py`
(ADM-001, Decision 6/9, `Plan_S11_ADM-001.md`) and `admin_dashboard_api.py`
(ADM-002, Decision 1/3, `Plan_S11_ADM-002.md`).
"""

import uuid
from datetime import datetime
from typing import Any

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


class FeatureFlagResponse(BaseModel):
    """One `feature_flags` row (ADM-002, AC1)."""

    id: uuid.UUID
    key: str
    is_enabled: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class FeatureFlagToggleRequest(BaseModel):
    """Request payload for `PATCH /admin/feature-flags/{key}` (AC4)."""

    is_enabled: bool


class SystemSettingResponse(BaseModel):
    """One `system_settings` row (ADM-002, AC1)."""

    id: uuid.UUID
    key: str
    value: Any
    description: str | None
    created_at: datetime
    updated_at: datetime


class SystemSettingUpdateRequest(BaseModel):
    """Request payload for `PATCH /admin/system-settings/{key}` (AC1)."""

    value: Any


class DashboardSummaryResponse(BaseModel):
    """
    AC2's dashboard-summary payload -- three headline counts, each
    paired with the literal, real, registered path of its own queue
    (`DashboardService.get_summary`, Decision 4/5,
    `Plan_S11_ADM-002.md`).
    """

    pending_verification_count: int
    pending_verification_queue_path: str
    pending_manual_match_count: int
    pending_manual_match_queue_path: str
    open_unmatched_query_report_count: int
    open_unmatched_query_report_queue_path: str
