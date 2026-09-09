"""
Administration domain model (`administration` Postgres schema, VER-002).

See `docs/AI/04_DATABASE.md` (Administration Domain) for the
column-level source of truth and
`docs/implementation/plans/Plan_S05_VER-002.md` (Decision 2) for the
architecture decision behind this module.

This is the Administration domain's first slice -- `AdminActionLog` is a
peer of `Admin User`/`Manual Match Assignment`/`Unmatched Query Report`
in `03_DOMAIN_MODEL.md`'s domain boundaries, not an extension of
`audit.audit_logs` (genuinely different column names, a genuinely
different table `04_DATABASE.md`/AC6 both name explicitly).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "administration"
_IDENTITY_SCHEMA = "identity"
_PROVIDER_SCHEMA = "provider"


class AdminActionLog(CommonColumnsMixin, Base):
    """
    One admin action event (VER-002, AC6) -- e.g. an approval/rejection
    of a provider's verification submission.

    Deliberately built with the full `CommonColumnsMixin` (versioned,
    soft-deletable) -- unlike the deliberately-immutable
    `audit.audit_logs`, `04_DATABASE.md`'s Soft Delete section does
    **not** name `admin_action_log` in its narrow Common-Columns
    exemption list (only `audit_logs`/`search_event_log` are named), so
    this table is built exactly like every other ordinary business
    table in this codebase (Decision 2, `Plan_S05_VER-002.md`) -- a
    deliberate, spec-literal choice, even though this means a row here
    is not literally immutable the way `audit_logs`' rows are.

    The Python attribute is named `metadata_` (never bare `metadata`,
    which `Base`/`DeclarativeBase` already reserves for SQLAlchemy's own
    `MetaData` object) but is mapped to the actual `metadata` database
    column `04_DATABASE.md`/AC6 name explicitly.
    """

    __tablename__ = "admin_action_log"
    __table_args__ = (
        Index("idx_admin_action_log_admin_user_id", "admin_user_id"),
        Index("idx_admin_action_log_created_at", "created_at"),
        {"schema": SCHEMA},
    )

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )


class ClaimReviewRequest(CommonColumnsMixin, Base):
    """
    AC6's admin-fallback queue item (CLM-001, Decision 9,
    `Plan_S06_CLM-001.md`) -- created when a claim attempt on a
    Google-seeded-unclaimed listing either failed OTP verification or
    found no usable public phone number on record. Mirrors
    `unmatched_query_reports`'s already-established shape: a physical,
    writable, durable table an admin pulls from (`GET /admin/claims`),
    not a DB view or a push notification.

    Full `CommonColumnsMixin` (versioned, soft-deletable), matching
    `AdminActionLog`'s own precedent -- `04_DATABASE.md`'s Soft Delete
    section names only `audit_logs`/`search_event_log` as exempt.

    `reason`/`status`/`resolution` are `VARCHAR`, not a native Postgres
    enum -- mirrors `04_DATABASE.md`'s own stated preference for
    VARCHAR + application-level constants over a DB enum for values
    expected to grow (`AdminActionLog.action_type` follows the same
    convention).
    """

    __tablename__ = "claim_review_requests"
    __table_args__ = (
        Index("idx_claim_review_requests_provider_id", "provider_id"),
        Index("idx_claim_review_requests_status", "status"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
    )
    claimant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'open'")
    )
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
