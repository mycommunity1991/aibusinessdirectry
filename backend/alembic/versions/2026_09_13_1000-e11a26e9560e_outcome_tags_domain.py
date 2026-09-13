"""outcome_tags_domain

Revision ID: e11a26e9560e
Revises: 024bcc0fbaf8
Create Date: 2026-09-13 10:00:00.000000

Creates `contact.outcome_tags` (REV-001), exactly per `04_DATABASE.md`'s
pre-existing spec (`contact_view_id`, `hired`, `submitted_at`) -- full
`CommonColumnsMixin` columns (Backend Proposed Changes item 1,
`Plan_S09_REV-001.md`) plus `uq_outcome_tags_contact_view_id`, the
unique constraint AC1/AC6 require ("one outcome tag per Contact View").

Does **not** create a new Postgres schema -- `contact` already exists
(`024bcc0fbaf8`, CON-001) -- and does **not** touch `visit_verifications`
or `reviews`, both explicitly out of this story's scope.

See `docs/AI/04_DATABASE.md` (Contact Domain, `outcome_tags`) and
`docs/implementation/plans/Plan_S09_REV-001.md` (Backend Proposed
Changes item 1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e11a26e9560e"
down_revision: str | Sequence[str] | None = "024bcc0fbaf8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "contact"
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
    op.create_table(
        "outcome_tags",
        *_common_columns(),
        sa.Column("contact_view_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hired", sa.Boolean(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["contact_view_id"],
            [f"{SCHEMA}.contact_views.id"],
            name="fk_outcome_tags_contact_view_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_outcome_tags_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_outcome_tags_updated_by",
        ),
        sa.UniqueConstraint(
            "contact_view_id", name="uq_outcome_tags_contact_view_id"
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("outcome_tags", schema=SCHEMA)
