"""notification_domain

Revision ID: 04c69a216287
Revises: 4cf80a64436f
Create Date: 2026-09-08 14:00:00.000000

Creates the `notification` Postgres schema (VER-002) and its first
table, `notification.notifications`, exactly per `04_DATABASE.md`'s
pre-existing spec (`user_id`, `type`, `title`, `body`,
`related_entity_type`, `related_entity_id`).

Deliberately does **not** create `notification_delivery` or
`notification_preferences` (Decision 3, `Plan_S05_VER-002.md`) -- no
real delivery channel or preference exists yet to have a status/opt-in
for; those are Sprint 12's own, later scope.

See `docs/AI/04_DATABASE.md` (Notification Domain) and
`docs/implementation/plans/Plan_S05_VER-002.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "04c69a216287"
down_revision: str | Sequence[str] | None = "4cf80a64436f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "notification"
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
        "notifications",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notifications_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notifications_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notifications_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_notifications_user_id",
        "notifications",
        ["user_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_notifications_created_at",
        "notifications",
        ["created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("notifications", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
