"""
Conversation / AI Intake domain model (`conversation` Postgres schema,
AI-001).

See `docs/AI/04_DATABASE.md` (Conversation / AI Intake Domain, lines
588-628) for the column-level source of truth and
`docs/implementation/plans/Plan_S07_AI-001.md` (Decisions 1, 1b, 3, 5)
for the architecture decisions behind this module.

Two additive items beyond `04_DATABASE.md`'s current text, both flagged
in the Plan for a doc update at story close:
- `ConversationStatus.ABANDONED` (Decision 5) -- set when a customer
  starts a new session while a previous one is still `active`.
- `ConversationSession.structured_criteria` (JSONB, nullable, Decision
  1b) -- the AC9 `search_requests`-ready payload, populated only on the
  `completed` transition, never written to the `search` schema itself
  (Decision 1's scope boundary).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "conversation"
_CUSTOMER_SCHEMA = "customer"
_CATEGORY_SCHEMA = "category"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ROUTED_TO_ADMIN = "routed_to_admin"
    ABANDONED = "abandoned"


class MessageSender(StrEnum):
    CUSTOMER = "customer"
    AI = "ai"


def _conversation_status_enum() -> SqlEnum:
    return SqlEnum(
        ConversationStatus,
        name="conversation_status",
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


def _message_sender_enum() -> SqlEnum:
    return SqlEnum(
        MessageSender,
        name="message_sender",
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


class ConversationSession(CommonColumnsMixin, Base):
    """
    One guided AI-intake conversation belonging to a Customer (AC1).
    `category_id` is `NULL` until `RuleBasedConversationAiClient`
    resolves exactly one category from the customer's free text.
    `structured_criteria` (Decision 1b, AC9) is populated only when
    `status` transitions to `completed`; a `routed_to_admin` or
    `abandoned` session always leaves it `NULL`.
    """

    __tablename__ = "conversation_sessions"
    __table_args__ = (
        Index("idx_conversation_sessions_customer_id", "customer_id"),
        Index("idx_conversation_sessions_status", "status"),
        {"schema": SCHEMA},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CUSTOMER_SCHEMA}.customer_profiles.id"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CATEGORY_SCHEMA}.categories.id"),
        nullable=True,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        _conversation_status_enum(),
        nullable=False,
        server_default=ConversationStatus.ACTIVE.value,
    )
    # `asdecimal=False` -- returns a native Python `float` rather than
    # SQLAlchemy's default `decimal.Decimal` for a `NUMERIC` column,
    # matching `ConversationTurnResult.confidence: float` (Decision 2)
    # and `settings.CONVERSATION_CONFIDENCE_THRESHOLD: float` (Decision
    # 4) so no `Decimal`/`float` conversion is needed anywhere this
    # value is compared or serialized.
    final_confidence_score: Mapped[float | None] = mapped_column(
        Numeric(4, 3, asdecimal=False), nullable=True
    )
    structured_criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Message(CommonColumnsMixin, Base):
    """
    One turn in a `ConversationSession` -- the AI-intake chat only, not
    customer-provider messaging (`04_DATABASE.md`'s own note, no such
    domain exists here). Ordered by `sequence_number`, enforced unique
    per session (AC1).
    """

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_session_id",
            "sequence_number",
            name="uq_messages_session_sequence",
        ),
        Index("idx_messages_conversation_session_id", "conversation_session_id"),
        {"schema": SCHEMA},
    )

    conversation_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.conversation_sessions.id"),
        nullable=False,
    )
    sender: Mapped[MessageSender] = mapped_column(
        _message_sender_enum(), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)


class ConfidenceScore(CommonColumnsMixin, Base):
    """
    Append-only confidence log for a `ConversationSession` (Decision 4)
    -- a session may be re-scored as more turns arrive;
    `ConversationSession.final_confidence_score` caches the latest value
    for cheap filtering. `model_version` is tagged `"rule_based_v1"` by
    this story's interim client (Decision 2), ready to be replaced by a
    real model/prompt-version string once a real LLM is wired in.
    """

    __tablename__ = "confidence_scores"
    __table_args__ = (
        Index("idx_confidence_scores_session_id", "conversation_session_id"),
        {"schema": SCHEMA},
    )

    conversation_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.conversation_sessions.id"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Numeric(4, 3, asdecimal=False), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
