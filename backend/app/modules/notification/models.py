"""
Notification domain models (`notification` Postgres schema, VER-002 +
`ENG-001`).

See `docs/AI/04_DATABASE.md` (Notification Domain) for the column-level
source of truth, `docs/implementation/plans/Plan_S05_VER-002.md`
(Decision 3) for `Notification`'s own original architecture decision,
and `docs/implementation/plans/Plan_S12_ENG-001.md` (Decisions 3/4) for
`NotificationPreference`/`NotificationDelivery` and `Notification.
read_at`.

`ENG-001` closes the two genuine table gaps VER-002's own migration
flagged as "remain unbuilt" (`NotificationPreference`/
`NotificationDelivery`), and adds `Notification.read_at` -- the
read/unread boundary AC5's "badge" and AC6's "New/Earlier grouping"
both need.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin
from app.modules.customer.models import NotificationChannel

SCHEMA = "notification"
_IDENTITY_SCHEMA = "identity"
_CUSTOMER_SCHEMA = "customer"


def _customer_notification_channel_enum() -> SqlEnum:
    """
    Reuses the exact `customer.notification_channel` Postgres enum type
    already created by the customer-domain migration (Decision 4,
    `Plan_S12_ENG-001.md`) -- never a second, duplicate type. Mirrors
    `customer/models.py`'s own `_identity_language_code_enum()` helper
    shape exactly, applied here in the opposite direction (`notification`
    reusing a `customer`-owned type, rather than `customer` reusing an
    `identity`-owned one) -- the same cross-schema enum-type-reuse
    precedent `CUS-001` (Decision 2, `Plan_S03_CUS-001.md`) established
    for `identity.language_code`. The canonical Python enum
    (`NotificationChannel`) is imported directly from `customer.models`,
    not redefined here -- a plain Python-level type import for
    schema-shape purposes, not a business-logic cross-module call (no
    `ADR-047` concern, mirroring `customer/models.py`'s own identical
    import of `identity.models.LanguageCode`).
    """
    return SqlEnum(
        NotificationChannel,
        name="notification_channel",
        schema=_CUSTOMER_SCHEMA,
        create_type=False,
        values_callable=lambda obj: [member.value for member in obj],
    )


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
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class NotificationPreference(CommonColumnsMixin, Base):
    """
    A single row per user, recording their notification channel and
    per-category opt-in state (`ENG-001`, AC4, Decision 3/4/5,
    `Plan_S12_ENG-001.md`). Lazily created on first touch by
    `NotificationPreferenceService.get_or_create_for_user` -- every
    account created before this story shipped gets default-allow,
    default-`whatsapp`-or-seeded-from-`customer_preferences` values the
    first time any trigger fires for them (Decision 5).
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
        Index("idx_notification_preferences_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _customer_notification_channel_enum(),
        nullable=False,
        server_default=NotificationChannel.WHATSAPP.value,
    )
    channel_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    leads_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    verification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    outcome_prompts_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )


class NotificationDelivery(CommonColumnsMixin, Base):
    """
    One row per external-delivery attempt against a `notifications` row
    (`ENG-001`, AC2/AC7, Decision 3/8, `Plan_S12_ENG-001.md`).
    `idempotency_key` (a genuine addition beyond `04_DATABASE.md`'s
    original pre-written spec) is a deterministic, server-computed
    `f"{notification_id}:{channel}"` string (never caller-supplied) --
    its `UNIQUE` constraint is what makes a retried send genuinely
    idempotent: `NotificationDeliveryRepository.try_create`'s `INSERT
    ... ON CONFLICT DO NOTHING` silently short-circuits a second attempt
    for the same `(notification_id, channel)` pair, never calling the
    underlying `NotificationSender` twice.

    `status` is a plain `VARCHAR(20)` (`pending`/`sent`/`failed`) --
    never a native Postgres enum, matching every other status-string
    column across this codebase's status-bearing tables.
    `delivered`/`delivered_at` are pre-specified per `04_DATABASE.md`'s
    original spec but genuinely unused by this story (Open Question 5)
    -- no real vendor webhook exists yet to ever set them.
    """

    __tablename__ = "notification_delivery"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_notification_delivery_idempotency_key"
        ),
        Index("idx_notification_delivery_notification_id", "notification_id"),
        {"schema": SCHEMA},
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.notifications.id"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _customer_notification_channel_enum(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
