"""reviews_domain

Revision ID: b2b3c4d5e6f7
Revises: e11a26e9560e
Create Date: 2026-09-14 10:00:00.000000

Creates the `review` Postgres schema (REV-002, Decision 1,
`Plan_S09_REV-002.md`) and its two tables, exactly per `04_DATABASE.md`'s
pre-existing spec: `review.reviews` (`contact_view_id`, `customer_id`,
`provider_id`, `rating`, `comment`) and `review.provider_rating_summaries`
(`provider_id`, `average_rating`, `review_count`, `recalculated_at`) --
full `CommonColumnsMixin` columns on each (Backend Proposed Changes item
1, `Plan_S09_REV-002.md`), plus every named constraint/index:
`uq_reviews_contact_view_id`, `chk_reviews_rating_range`,
`idx_reviews_provider_id` on `reviews`; `uq_provider_rating_summaries_
provider_id` on `provider_rating_summaries`.

A new, standalone `review` module (Decision 1) -- not folded into
`contact` -- because it owns a genuinely separate Postgres schema,
unlike REV-001's `outcome_tags` (which shared `contact`'s own schema).

See `docs/AI/04_DATABASE.md` (Review Domain) and
`docs/implementation/plans/Plan_S09_REV-002.md` (Backend Proposed
Changes item 1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "e11a26e9560e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "review"
IDENTITY_SCHEMA = "identity"
CONTACT_SCHEMA = "contact"
CUSTOMER_SCHEMA = "customer"
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
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "reviews",
        *_common_columns(),
        sa.Column("contact_view_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contact_view_id"],
            [f"{CONTACT_SCHEMA}.contact_views.id"],
            name="fk_reviews_contact_view_id",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CUSTOMER_SCHEMA}.customer_profiles.id"],
            name="fk_reviews_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_reviews_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_reviews_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_reviews_updated_by",
        ),
        sa.UniqueConstraint("contact_view_id", name="uq_reviews_contact_view_id"),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5", name="chk_reviews_rating_range"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_reviews_provider_id",
        "reviews",
        ["provider_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "provider_rating_summaries",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "average_rating",
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "review_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_provider_rating_summaries_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_rating_summaries_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_rating_summaries_updated_by",
        ),
        sa.UniqueConstraint(
            "provider_id", name="uq_provider_rating_summaries_provider_id"
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("provider_rating_summaries", schema=SCHEMA)
    op.drop_index("idx_reviews_provider_id", table_name="reviews", schema=SCHEMA)
    op.drop_table("reviews", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
