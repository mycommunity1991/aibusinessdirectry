"""search_domain_and_manual_match_assignments

Revision ID: f3a1c9d47b02
Revises: ef7b7d439f40
Create Date: 2026-09-10 11:00:00.000000

Creates the `search` Postgres schema (AI-002) -- the `search_request_
status` enum (`matched`, `unmatched`, `pending_manual_match`, per
`04_DATABASE.md` line 190, unchanged), `search_requests`,
`provider_matches`, `search_event_log` -- column-for-column per
`04_DATABASE.md` lines 663-705, plus four flagged, necessary nullable
deviations (see `Plan_S07_AI-002.md` Decision 2 and
`app/modules/search/models.py`'s module docstring):

- `search_requests.structured_criteria` -- Decision 2b: a
  `routed_to_admin` conversation session always leaves `conversation.
  conversation_sessions.structured_criteria = NULL`.
- `search_requests.customer_latitude`/`customer_longitude` -- Decision
  2c: no location-collection step exists anywhere in the AI Conversation
  flow; a customer with no default saved address still completes
  automatically (as `unmatched`), never blocked, never guessed.
- `search_requests.category_id` -- a fourth deviation, found during
  implementation, beyond the three the Plan itself flagged: a
  `routed_to_admin` session can reach that status via `AI-001`'s hard
  turn cap without ever having resolved a category at all.

In the same migration, adds `administration.manual_match_assignments`
(AI-002, Decision 3) to the existing `administration` schema, with
`assigned_admin_id` **nullable** (Decision 2a -- `ADR-030`'s own prior
finding that `NOT NULL` here "doesn't fit 'an unassigned queue, any
admin may pick up'"). No changes to any existing table.

See `docs/AI/04_DATABASE.md` (Search Domain; Administration Domain) and
`docs/implementation/plans/Plan_S07_AI-002.md` (Decisions 2, 3).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a1c9d47b02"
down_revision: str | Sequence[str] | None = "ef7b7d439f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_SCHEMA = "search"
ADMINISTRATION_SCHEMA = "administration"
IDENTITY_SCHEMA = "identity"
CUSTOMER_SCHEMA = "customer"
CATEGORY_SCHEMA = "category"
CONVERSATION_SCHEMA = "conversation"
PROVIDER_SCHEMA = "provider"

_SEARCH_REQUEST_STATUS_VALUES = ("matched", "unmatched", "pending_manual_match")


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
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SEARCH_SCHEMA}")

    search_request_status = postgresql.ENUM(
        *_SEARCH_REQUEST_STATUS_VALUES,
        name="search_request_status",
        schema=SEARCH_SCHEMA,
    )
    search_request_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "search_requests",
        *_common_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_session_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("structured_criteria", postgresql.JSONB(), nullable=True),
        sa.Column("customer_latitude", sa.Double(), nullable=True),
        sa.Column("customer_longitude", sa.Double(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                *_SEARCH_REQUEST_STATUS_VALUES,
                name="search_request_status",
                schema=SEARCH_SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CUSTOMER_SCHEMA}.customer_profiles.id"],
            name="fk_search_requests_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_session_id"],
            [f"{CONVERSATION_SCHEMA}.conversation_sessions.id"],
            name="fk_search_requests_conversation_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            [f"{CATEGORY_SCHEMA}.categories.id"],
            name="fk_search_requests_category_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_search_requests_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_search_requests_updated_by",
        ),
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_requests_customer_id",
        "search_requests",
        ["customer_id"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_requests_created_at",
        "search_requests",
        ["created_at"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_requests_status",
        "search_requests",
        ["status"],
        schema=SEARCH_SCHEMA,
    )

    op.create_table(
        "provider_matches",
        *_common_columns(),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("match_score", sa.Numeric(5, 4), nullable=True),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            [f"{SEARCH_SCHEMA}.search_requests.id"],
            name="fk_provider_matches_search_request_id",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_provider_matches_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_matches_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_matches_updated_by",
        ),
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_provider_matches_search_request_id",
        "provider_matches",
        ["search_request_id"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_provider_matches_provider_id",
        "provider_matches",
        ["provider_id"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "uq_provider_matches_request_provider",
        "provider_matches",
        ["search_request_id", "provider_id"],
        unique=True,
        schema=SEARCH_SCHEMA,
    )

    op.create_table(
        "search_event_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column(
            "result_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("was_matched", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            [f"{SEARCH_SCHEMA}.search_requests.id"],
            name="fk_search_event_log_search_request_id",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CUSTOMER_SCHEMA}.customer_profiles.id"],
            name="fk_search_event_log_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            [f"{CATEGORY_SCHEMA}.categories.id"],
            name="fk_search_event_log_category_id",
        ),
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_event_log_created_at",
        "search_event_log",
        ["created_at"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_event_log_was_matched",
        "search_event_log",
        ["was_matched"],
        schema=SEARCH_SCHEMA,
    )
    op.create_index(
        "idx_search_event_log_category_id",
        "search_event_log",
        ["category_id"],
        schema=SEARCH_SCHEMA,
    )

    op.create_table(
        "manual_match_assignments",
        *_common_columns(),
        sa.Column(
            "conversation_session_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_session_id"],
            [f"{CONVERSATION_SCHEMA}.conversation_sessions.id"],
            name="fk_manual_match_assignments_conversation_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            [f"{SEARCH_SCHEMA}.search_requests.id"],
            name="fk_manual_match_assignments_search_request_id",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_admin_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_manual_match_assignments_assigned_admin_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_manual_match_assignments_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_manual_match_assignments_updated_by",
        ),
        schema=ADMINISTRATION_SCHEMA,
    )
    op.create_index(
        "idx_manual_match_assignments_status",
        "manual_match_assignments",
        ["status"],
        schema=ADMINISTRATION_SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("manual_match_assignments", schema=ADMINISTRATION_SCHEMA)
    op.drop_table("search_event_log", schema=SEARCH_SCHEMA)
    op.drop_table("provider_matches", schema=SEARCH_SCHEMA)
    op.drop_table("search_requests", schema=SEARCH_SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SEARCH_SCHEMA}.search_request_status")
    op.execute(f"DROP SCHEMA IF EXISTS {SEARCH_SCHEMA} RESTRICT")
