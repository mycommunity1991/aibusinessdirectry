"""claim_review_requests

Revision ID: 602bf3c4bea7
Revises: a804c46bf703
Create Date: 2026-09-09 11:00:00.000000

Creates `administration.claim_review_requests` (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`) -- the AC6 admin-fallback queue for a Google-
seeded-unclaimed-listing claim attempt that failed OTP verification or
found no usable public phone number. Mirrors `unmatched_query_reports`'s
already-established precedent for exactly this shape (a physical,
writable, durable admin-review-queue table, not a DB view or a
fire-and-forget notification) -- built with the full
`CommonColumnsMixin`, matching `admin_action_log`'s own precedent of
using the full mixin rather than being exempted like `audit_logs`.

Genuinely new schema, not previously specified anywhere in
`04_DATABASE.md` -- flagged in the Plan for `04_DATABASE.md`'s
Administration Domain section to be updated at story close.

See `docs/AI/04_DATABASE.md` (Administration Domain) and
`docs/implementation/plans/Plan_S06_CLM-001.md` (Decision 9).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "602bf3c4bea7"
down_revision: str | Sequence[str] | None = "a804c46bf703"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "administration"
IDENTITY_SCHEMA = "identity"
PROVIDER_SCHEMA = "provider"


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
        "claim_review_requests",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claimant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("resolution", sa.String(length=20), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_claim_review_requests_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["claimant_user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_claim_review_requests_claimant_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_claim_review_requests_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_claim_review_requests_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_claim_review_requests_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_claim_review_requests_provider_id",
        "claim_review_requests",
        ["provider_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_claim_review_requests_status",
        "claim_review_requests",
        ["status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("claim_review_requests", schema=SCHEMA)
