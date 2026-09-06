"""audit_domain

Revision ID: d81be77c601d
Revises: bc69dfa02341
Create Date: 2026-09-06 09:00:00.000000

Creates the `audit` Postgres schema and its single `audit_logs` table
(AUTH-004, AC8). Immutable/append-only -- no `updated_at`/`deleted_at`/
`is_active`/`version` columns, per `04_DATABASE.md`'s explicit note that
`audit_logs` is exempt from the Common Columns convention. See
`docs/AI/04_DATABASE.md` (Audit Domain) and
`docs/implementation/plans/Plan_S02_AUTH-004.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d81be77c601d"
down_revision: str | Sequence[str] | None = "bc69dfa02341"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "audit"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["identity.users.id"],
            name="fk_audit_logs_actor_user_id",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], schema=SCHEMA
    )
    op.create_index(
        "idx_audit_logs_entity_type_entity_id",
        "audit_logs",
        ["entity_type", "entity_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_audit_logs_created_at", "audit_logs", ["created_at"], schema=SCHEMA
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("audit_logs", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
