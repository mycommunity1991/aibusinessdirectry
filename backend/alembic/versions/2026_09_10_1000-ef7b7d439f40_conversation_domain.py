"""conversation_domain

Revision ID: ef7b7d439f40
Revises: 602bf3c4bea7
Create Date: 2026-09-10 10:00:00.000000

Creates the `conversation` Postgres schema (AI-001) and its three
tables column-for-column per `04_DATABASE.md`'s Conversation / AI
Intake Domain section (lines 588-628), plus two additive items flagged
in `Plan_S07_AI-001.md` for a `04_DATABASE.md` update at story close:

- `conversation_status` gains a fourth value, `abandoned` (Decision 5)
  -- set when a customer starts a new session while a previous one is
  still `active`. `04_DATABASE.md`'s text only names `active`/
  `completed`/`routed_to_admin` explicitly.
- `conversation_sessions.structured_criteria` (JSONB, nullable,
  Decision 1b) -- the AC9 `search_requests`-ready payload, populated
  only when a session reaches `status = completed`, validated via the
  `StructuredCriteria` Pydantic model before it is ever written. Never
  written to by any `search` schema; this story does not create or
  touch `search.search_requests` at all (Decision 1's scope boundary).

`uq_messages_session_sequence` is a **partial** unique index on
`(conversation_session_id, sequence_number)` scoped `WHERE is_active =
true` -- not a plain table-level `UniqueConstraint` -- mirroring this
project's existing partial-unique-active precedent
(`uq_saved_addresses_customer_default`). This is required, not
cosmetic: `messages` is soft-deleted (Decision 5's revise/truncate
mechanism sets `deleted_at`/`is_active=false` rather than hard-deleting,
per `04_DATABASE.md`'s "Common Columns" soft-delete rule), and
`MessageRepository.get_next_sequence_number` reassigns a regenerated
turn's `sequence_number` starting right after the last still-*active*
message -- a value a now-soft-deleted row in the same session may
already occupy. A plain, unscoped unique constraint would reject that
insert; scoping the index to `is_active = true` lets a soft-deleted
row's old `sequence_number` be reused by the row that replaces it,
while still fully enforcing uniqueness among every message the
customer can currently see.

`conversation_sessions.customer_id` -> `customer.customer_profiles.id`
and `conversation_sessions.category_id` -> `category.categories.id`
are this story's first genuine cross-schema FKs into those two already-
shipped domains (Decision 3).

See `docs/AI/04_DATABASE.md` (Conversation / AI Intake Domain) and
`docs/implementation/plans/Plan_S07_AI-001.md` (Decisions 1b, 3, 5).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef7b7d439f40"
down_revision: str | Sequence[str] | None = "602bf3c4bea7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "conversation"
IDENTITY_SCHEMA = "identity"
CUSTOMER_SCHEMA = "customer"
CATEGORY_SCHEMA = "category"

_CONVERSATION_STATUS_VALUES = ("active", "completed", "routed_to_admin", "abandoned")
_MESSAGE_SENDER_VALUES = ("customer", "ai")


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` -- mirrors every prior domain
    migration's own identically-named helper."""
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    conversation_status = postgresql.ENUM(
        *_CONVERSATION_STATUS_VALUES,
        name="conversation_status",
        schema=SCHEMA,
    )
    conversation_status.create(op.get_bind(), checkfirst=True)

    message_sender = postgresql.ENUM(
        *_MESSAGE_SENDER_VALUES,
        name="message_sender",
        schema=SCHEMA,
    )
    message_sender.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversation_sessions",
        *_common_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                *_CONVERSATION_STATUS_VALUES,
                name="conversation_status",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("final_confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("structured_criteria", postgresql.JSONB(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CUSTOMER_SCHEMA}.customer_profiles.id"],
            name="fk_conversation_sessions_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            [f"{CATEGORY_SCHEMA}.categories.id"],
            name="fk_conversation_sessions_category_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_conversation_sessions_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_conversation_sessions_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_conversation_sessions_customer_id",
        "conversation_sessions",
        ["customer_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_conversation_sessions_status",
        "conversation_sessions",
        ["status"],
        schema=SCHEMA,
    )

    op.create_table(
        "messages",
        *_common_columns(),
        sa.Column(
            "conversation_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "sender",
            postgresql.ENUM(
                *_MESSAGE_SENDER_VALUES,
                name="message_sender",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_session_id"],
            [f"{SCHEMA}.conversation_sessions.id"],
            name="fk_messages_conversation_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_messages_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_messages_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_messages_conversation_session_id",
        "messages",
        ["conversation_session_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_messages_session_sequence",
        "messages",
        ["conversation_session_id", "sequence_number"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "confidence_scores",
        *_common_columns(),
        sa.Column(
            "conversation_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("score", sa.Numeric(4, 3), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_session_id"],
            [f"{SCHEMA}.conversation_sessions.id"],
            name="fk_confidence_scores_conversation_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_confidence_scores_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_confidence_scores_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_confidence_scores_session_id",
        "confidence_scores",
        ["conversation_session_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("confidence_scores", schema=SCHEMA)
    op.drop_table("messages", schema=SCHEMA)
    op.drop_table("conversation_sessions", schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.message_sender")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.conversation_status")
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
