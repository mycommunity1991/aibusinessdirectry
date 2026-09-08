"""administration_domain

Revision ID: 4cf80a64436f
Revises: 906b8c537570
Create Date: 2026-09-08 13:00:00.000000

Creates the `administration` Postgres schema (VER-002) and its first
table, `administration.admin_action_log`, exactly per `04_DATABASE.md`'s
pre-existing spec (`admin_user_id`, `action_type`, `target_entity_type`,
`target_entity_id`, `metadata`).

Deliberately **not** modeled after the deliberately-immutable
`audit.audit_logs` (Decision 2, `Plan_S05_VER-002.md`): `04_DATABASE.md`'s
Soft Delete section names only `audit_logs`/`search_event_log` as exempt
from the Common Columns convention -- `admin_action_log` is not on that
list, so it is built with the full `CommonColumnsMixin` (versioned,
soft-deletable) like every other ordinary business table.

See `docs/AI/04_DATABASE.md` (Administration Domain) and
`docs/implementation/plans/Plan_S05_VER-002.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4cf80a64436f"
down_revision: str | Sequence[str] | None = "906b8c537570"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "administration"
IDENTITY_SCHEMA = "identity"


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

    op.create_table(
        "admin_action_log",
        *_common_columns(),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_entity_type", sa.String(length=50), nullable=True),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_admin_action_log_admin_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_admin_action_log_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_admin_action_log_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_admin_action_log_admin_user_id",
        "admin_action_log",
        ["admin_user_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_admin_action_log_created_at",
        "admin_action_log",
        ["created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("admin_action_log", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
