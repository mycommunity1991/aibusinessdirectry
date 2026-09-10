"""
Search domain model (`search` Postgres schema, AI-002).

See `docs/AI/04_DATABASE.md` (Search Domain, lines 663-705) for the
column-level source of truth and
`docs/implementation/plans/Plan_S07_AI-002.md` (Decision 2) for the
architecture decisions behind this module. This is the first story to
add persisted state to `search` -- `DIR-001`'s `SearchService` remains a
stateless read-layer over `provider.ProviderService`, reused unchanged
(Decision 5) rather than replaced.

**Four flagged, necessary nullable-column deviations from
`04_DATABASE.md`'s current literal text**, each resolved the way this
codebase has resolved every prior instance of "the locked spec doesn't
fit what the real code path can honestly provide" -- make the column
nullable and report the honest absence, never fabricate a value:

- `structured_criteria` (Decision 2b) -- a `routed_to_admin` session
  always leaves `conversation_sessions.structured_criteria = NULL`
  (`AI-001`'s own Decision 1b/ADR-033); a `search_requests` row created
  for such a session structurally cannot inherit a non-null payload.
- `customer_latitude`/`customer_longitude` (Decision 2c) -- no
  location-collection step exists anywhere in the AI Conversation flow;
  a customer with no default saved address still completes automatically
  (as `unmatched`), never blocked, never guessed.
- `category_id` -- **a fourth deviation, found during implementation,
  beyond the three the Plan itself flagged.** A `routed_to_admin`
  session can reach `status=routed_to_admin` via `AI-001`'s hard turn
  cap (`CONVERSATION_MAX_TURNS`) without ever having resolved a category
  at all (e.g. the customer's free text never unambiguously matched one
  category across every turn) -- confirmed against
  `RuleBasedConversationAiClient._resolve_category`/
  `ConversationService._apply_completion_policy`, which never requires
  `category_id` to be set before routing to the turn-cap outcome. Making
  this column `NOT NULL` (as `04_DATABASE.md`'s literal text and the
  Plan's Decision 2 both currently state) would force fabricating a
  category for a session that never had one, the exact anti-fabrication
  violation Decision 2b/2c already reject for the other two columns.
  Flagged here for the same `04_DATABASE.md`/ADR treatment as the other
  three.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "search"
_CUSTOMER_SCHEMA = "customer"
_CONVERSATION_SCHEMA = "conversation"
_CATEGORY_SCHEMA = "category"
_PROVIDER_SCHEMA = "provider"


class SearchRequestStatus(StrEnum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    PENDING_MANUAL_MATCH = "pending_manual_match"


def _search_request_status_enum() -> SqlEnum:
    return SqlEnum(
        SearchRequestStatus,
        name="search_request_status",
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


class SearchRequest(CommonColumnsMixin, Base):
    """
    One AI-conversation-triggered (or, in future, structured) search
    request (AI-002). `status` is always set to its final value at
    creation (`matched`/`unmatched` for the automated path,
    `pending_manual_match` for the manual path) -- never a "submitted,
    awaiting processing" placeholder (Decision 4, mirrors ADR-029).
    """

    __tablename__ = "search_requests"
    __table_args__ = (
        Index("idx_search_requests_customer_id", "customer_id"),
        Index("idx_search_requests_created_at", "created_at"),
        Index("idx_search_requests_status", "status"),
        {"schema": SCHEMA},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CUSTOMER_SCHEMA}.customer_profiles.id"),
        nullable=False,
    )
    conversation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CONVERSATION_SCHEMA}.conversation_sessions.id"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CATEGORY_SCHEMA}.categories.id"),
        nullable=True,
    )
    structured_criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    customer_latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    customer_longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    status: Mapped[SearchRequestStatus] = mapped_column(
        _search_request_status_enum(), nullable=False
    )


class ProviderMatch(CommonColumnsMixin, Base):
    """
    The ranked result set of a `SearchRequest` against Provider data --
    explicitly not a Quote and not a booking state machine
    (`04_DATABASE.md`'s own note). Written exactly once, by
    `SearchRequestService._finalize_matches` (Decision 4) -- the only
    place in the codebase that ever writes this table.
    """

    __tablename__ = "provider_matches"
    __table_args__ = (
        Index("idx_provider_matches_search_request_id", "search_request_id"),
        Index("idx_provider_matches_provider_id", "provider_id"),
        Index(
            "uq_provider_matches_request_provider",
            "search_request_id",
            "provider_id",
            unique=True,
        ),
        {"schema": SCHEMA},
    )

    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.search_requests.id"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    match_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4, asdecimal=False), nullable=True
    )


class SearchEventLog(Base):
    """
    Every `SearchRequest`, matched or not (AC6) -- append-only, no soft
    delete, deliberately does NOT inherit `CommonColumnsMixin`, mirroring
    `audit.audit_logs`'s exact exemption (`04_DATABASE.md`'s "Common
    Columns" section names only `audit_logs`/`search_event_log` as
    exempt). Written exactly once per `search_requests` row, by
    `SearchRequestService._finalize_matches` (Decision 4), regardless of
    whether resolution was automated or manual.
    """

    __tablename__ = "search_event_log"
    __table_args__ = (
        Index("idx_search_event_log_created_at", "created_at"),
        Index("idx_search_event_log_was_matched", "was_matched"),
        Index("idx_search_event_log_category_id", "category_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.search_requests.id"),
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CUSTOMER_SCHEMA}.customer_profiles.id"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CATEGORY_SCHEMA}.categories.id"),
        nullable=True,
    )
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    was_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
