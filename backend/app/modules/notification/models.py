"""
Notification domain model (`notification` Postgres schema, VER-002).

See `docs/AI/04_DATABASE.md` (Notification Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S05_VER-002.md`
(Decision 3) for the architecture decision behind this module.

This is the Notification domain's first slice -- `notification.
notifications` only, honestly recording "a notification of this type,
with this plain-language content, was generated for this user." No
`notification_delivery`/`notification_preferences` table exists yet
(Decision 3): there is no real delivery channel to have a status for,
and nothing to opt in/out of. Sprint 12 ("Engagement & Trust") is this
domain's own later, dedicated milestone.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "notification"
_IDENTITY_SCHEMA = "identity"


class Notification(CommonColumnsMixin, Base):
    """
    One in-app notification record (VER-002, AC5) -- e.g. a provider's
    verification status change. Built with the full `CommonColumnsMixin`
    (versioned, soft-deletable), the same spec-literal reasoning as
    `administration.AdminActionLog` (Decision 2/3,
    `Plan_S05_VER-002.md`).
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_created_at", "created_at"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
