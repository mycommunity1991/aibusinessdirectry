"""unmatched_query_reports

Revision ID: 34cd99dbf8db
Revises: c3c4d5e6f7a8
Create Date: 2026-09-15 10:00:00.000000

Creates `administration.unmatched_query_reports` (ADM-001, Decision 1/2,
`Plan_S11_ADM-001.md`) -- `administration`'s fourth aggregate root,
auto-created by `SearchRequestService._finalize_matches` (Decision 2)
whenever a `search_event_log` row is written with `was_matched=false`.

Column shape mirrors `04_DATABASE.md`'s already-specified spec exactly
(designed at CLM-001's closeout, never previously migrated, explicitly
labeled "remain unbuilt" until this story): `search_event_log_id` (UUID,
not null, FK -> `search.search_event_log.id`, unique -- a strict 1:1),
`category_gap_notes` (TEXT, nullable), `status` (VARCHAR(20), not null,
default `'open'`), `reviewed_by` (UUID, nullable, FK ->
`identity.users.id`), `reviewed_at` (TIMESTAMPTZ, nullable), plus the
full `CommonColumnsMixin` -- mirrors `602bf3c4bea7_claim_review_requests`'s
exact template (full mixin, not `search_event_log`'s narrower
append-only exemption -- `04_DATABASE.md`'s Soft Delete section names
only `audit_logs`/`search_event_log` as exempt).

See `docs/AI/04_DATABASE.md` (Administration Domain) and
`docs/implementation/plans/Plan_S11_ADM-001.md` (Decision 1/2).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "34cd99dbf8db"
down_revision: str | Sequence[str] | None = "c3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "administration"
IDENTITY_SCHEMA = "identity"
SEARCH_SCHEMA = "search"


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
    op.create_table(
        "unmatched_query_reports",
        *_common_columns(),
        sa.Column("search_event_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_gap_notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["search_event_log_id"],
            [f"{SEARCH_SCHEMA}.search_event_log.id"],
            name="fk_unmatched_query_reports_search_event_log_id",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_unmatched_query_reports_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_unmatched_query_reports_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_unmatched_query_reports_updated_by",
        ),
        sa.UniqueConstraint(
            "search_event_log_id",
            name="uq_unmatched_query_reports_search_event_log_id",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_unmatched_query_reports_status",
        "unmatched_query_reports",
        ["status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("unmatched_query_reports", schema=SCHEMA)
