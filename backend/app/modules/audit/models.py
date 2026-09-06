"""
Audit domain model (`audit` Postgres schema, AUTH-004).

See `docs/AI/04_DATABASE.md` (Audit Domain) for the column-level source
of truth and `docs/implementation/plans/Plan_S02_AUTH-004.md` for the
architecture decisions behind this module.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

SCHEMA = "audit"


class AuditLog(Base):
    """
    A single, immutable audit event (AC8). Deliberately does NOT inherit
    `CommonColumnsMixin` -- no `updated_at`/`deleted_at`/`is_active`/
    `version` columns exist, per `04_DATABASE.md`'s explicit note that
    `audit_logs` is exempt from the Common Columns convention (append-
    only, never updated or deleted, including by administrators, per
    `06_SECURITY.md`).

    `before_state`/`after_state` must never contain a phone number,
    email, raw token, or token hash -- only non-PII metadata. `entity_id`
    (pointing at the `user`/`session` row already recorded elsewhere)
    gives full traceability without duplicating PII into this table.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_actor_user_id", "actor_user_id"),
        Index("idx_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("idx_audit_logs_created_at", "created_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
