"""provider_storefront

Revision ID: 272b12ab9b2f
Revises: 6133c77f062e
Create Date: 2026-09-08 11:00:00.000000

Completes the Provider aggregate (PRO-002): `provider_availability`,
`portfolios`, `service_areas` -- each exactly per `04_DATABASE.md`'s
Provider Domain spec -- and `provider_category_labels`, a new,
deliberately-not-`provider_categories`-named interim table (Decision 1,
`Plan_S04_PRO-002.md`) standing in for the not-yet-built Category domain
without conflating with the real join table `04_DATABASE.md` already
reserves the `provider_categories` name for.

Also backfills every existing `providers.category_label` value into
`provider_category_labels` (marked `is_primary=true`) and then drops
`providers.category_label` -- no dual representation is left behind
(this codebase has no production data to protect yet).

A new `weekday` enum is created, scoped to the `provider` schema as its
first consumer (mirrors the `provider_domain` migration's own enum-
colocation precedent) -- flagged for any future domain needing the same
enum to reuse via `create_type=False, schema="provider"` rather than
duplicating it.

Deliberately does NOT add the `cube`/`earthdistance` GiST index over
`service_areas` (`04_DATABASE.md` Section 13) -- no AC in this story
performs a geospatial query against this table; that begins with the
future Search & Matching story.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "272b12ab9b2f"
down_revision: str | Sequence[str] | None = "6133c77f062e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "provider"
IDENTITY_SCHEMA = "identity"

weekday_enum = postgresql.ENUM(
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    name="weekday",
    schema=SCHEMA,
)


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table. Mirrors
    the `provider_domain` migration's helper exactly."""
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
    bind = op.get_bind()

    weekday_enum.create(bind, checkfirst=True)

    # --- provider_availability ------------------------------------------
    op.create_table(
        "provider_availability",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "weekday",
            postgresql.ENUM(
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                name="weekday",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("open_time", sa.Time(), nullable=True),
        sa.Column("close_time", sa.Time(), nullable=True),
        sa.Column(
            "is_emergency_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint(
            "provider_id",
            "weekday",
            name="uq_provider_availability_provider_weekday",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_provider_availability_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_availability_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_availability_updated_by",
        ),
        schema=SCHEMA,
    )

    # --- portfolios -------------------------------------------------------
    op.create_table(
        "portfolios",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_url", sa.String(length=500), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column(
            "sort_order", sa.SmallInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_portfolios_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_portfolios_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_portfolios_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_portfolios_provider_id", "portfolios", ["provider_id"], schema=SCHEMA
    )

    # --- service_areas ------------------------------------------------------
    op.create_table(
        "service_areas",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("center_latitude", sa.Double(), nullable=False),
        sa.Column("center_longitude", sa.Double(), nullable=False),
        sa.Column("radius_meters", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_service_areas_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_service_areas_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_service_areas_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_service_areas_provider_id", "service_areas", ["provider_id"], schema=SCHEMA
    )

    # --- provider_category_labels --------------------------------------
    op.create_table(
        "provider_category_labels",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_provider_category_labels_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_category_labels_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_provider_category_labels_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_provider_category_labels_provider_id",
        "provider_category_labels",
        ["provider_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_provider_category_labels_primary",
        "provider_category_labels",
        ["provider_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("is_primary = true"),
    )

    # --- backfill providers.category_label -> provider_category_labels ---
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.provider_category_labels
            (provider_id, label, is_primary)
        SELECT id, category_label, true
        FROM {SCHEMA}.providers
        """
    )

    op.drop_column("providers", "category_label", schema=SCHEMA)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.add_column(
        "providers",
        sa.Column("category_label", sa.String(length=100), nullable=True),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        UPDATE {SCHEMA}.providers AS p
        SET category_label = pcl.label
        FROM {SCHEMA}.provider_category_labels AS pcl
        WHERE pcl.provider_id = p.id AND pcl.is_primary = true
        """
    )
    op.execute(
        f"""
        UPDATE {SCHEMA}.providers
        SET category_label = ''
        WHERE category_label IS NULL
        """
    )
    op.alter_column("providers", "category_label", nullable=False, schema=SCHEMA)

    op.drop_table("provider_category_labels", schema=SCHEMA)
    op.drop_table("service_areas", schema=SCHEMA)
    op.drop_table("portfolios", schema=SCHEMA)
    op.drop_table("provider_availability", schema=SCHEMA)

    weekday_enum.drop(bind, checkfirst=True)
