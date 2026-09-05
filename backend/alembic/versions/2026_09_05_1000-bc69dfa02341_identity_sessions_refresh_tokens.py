"""identity_sessions_refresh_tokens

Revision ID: bc69dfa02341
Revises: be1f79b6fa2a
Create Date: 2026-09-05 10:00:00.000000

Creates `identity.sessions` and `identity.refresh_tokens` (AUTH-003).
`identity.devices` already exists (AUTH-001 migration) and is not touched
here. See `docs/AI/04_DATABASE.md` (Identity Domain) and
`docs/implementation/plans/Plan_S02_AUTH-003.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc69dfa02341"
down_revision: str | Sequence[str] | None = "be1f79b6fa2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "identity"


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table."""
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
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    # --- sessions ----------------------------------------------------------
    op.create_table(
        "sessions",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.users.id"], name="fk_sessions_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], [f"{SCHEMA}.devices.id"], name="fk_sessions_device_id"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_sessions_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], [f"{SCHEMA}.users.id"], name="fk_sessions_updated_by"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"], schema=SCHEMA)
    op.create_index(
        "idx_sessions_expires_at", "sessions", ["expires_at"], schema=SCHEMA
    )

    # --- refresh_tokens ------------------------------------------------
    op.create_table(
        "refresh_tokens",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_token_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.users.id"], name="fk_refresh_tokens_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            [f"{SCHEMA}.sessions.id"],
            name="fk_refresh_tokens_session_id",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            [f"{SCHEMA}.refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by_token_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.users.id"],
            name="fk_refresh_tokens_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{SCHEMA}.users.id"],
            name="fk_refresh_tokens_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema=SCHEMA
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("refresh_tokens", schema=SCHEMA)
    op.drop_table("sessions", schema=SCHEMA)
