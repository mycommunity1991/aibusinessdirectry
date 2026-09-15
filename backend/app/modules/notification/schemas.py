import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """
    Response payload for one `notifications` row (`ENG-001`, AC6,
    Decision 10, `Plan_S12_ENG-001.md`) -- raw fields, client-computed
    grouping (`ADR-046`'s "raw fields, client-computed, never a
    server-computed enum" precedent, applied here to a New/Earlier
    grouping decision rather than a badge-precedence one): the mobile
    client groups rows into New/Earlier by `read_at is None`, and
    deep-links each row by `related_entity_type`.
    """

    id: uuid.UUID
    type: str
    title: str
    body: str
    related_entity_type: str | None = None
    related_entity_id: uuid.UUID | None = None
    read_at: datetime | None = None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    """Response payload for `GET /notifications/unread-count` (AC5)."""

    count: int = Field(
        ..., description="The caller's current unread notification count."
    )
