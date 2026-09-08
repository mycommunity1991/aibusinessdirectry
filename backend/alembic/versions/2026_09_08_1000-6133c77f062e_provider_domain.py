"""provider_domain

Revision ID: 6133c77f062e
Revises: 9f47869ca8bb
Create Date: 2026-09-08 10:00:00.000000

Creates the `provider` Postgres schema, its three PRO-001 enums
(`provider_type`, `listing_source`, `verification_status` -- colocated
here as their first consumer anywhere in the codebase, flagged for the
future Verification-domain story to reuse `verification_status` via
`create_type=False, schema="provider"` rather than duplicating it,
mirroring the `customer_domain` migration's `notification_channel`
precedent), and its three PRO-001 tables: `providers` (the aggregate
root, 1:1 with `identity.users` when claimed), `business_profiles`, and
`freelancer_profiles` (both 1:1 with `providers`). See
`docs/AI/04_DATABASE.md` (Provider Domain) and
`docs/implementation/plans/Plan_S04_PRO-001.md`.

`providers.category_label VARCHAR(100) NOT NULL` is a genuine, flagged
addition beyond `04_DATABASE.md`'s literal `providers` spec (Decision 4
of the Plan) -- a temporary free-text stand-in for the not-yet-built
Category domain. Flagged for a `04_DATABASE.md` follow-up update at
story close.

Deliberately does NOT create `provider_availability`, `portfolios`, or
`service_areas` -- PRO-002 scope, a separate, not-yet-built story, even
though `04_DATABASE.md` documents them in the same "Provider Domain"
section.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6133c77f062e"
down_revision: str | Sequence[str] | None = "9f47869ca8bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "provider"
IDENTITY_SCHEMA = "identity"

provider_type_enum = postgresql.ENUM(
    "business", "freelancer", name="provider_type", schema=SCHEMA
)
listing_source_enum = postgresql.ENUM(
    "self_registered",
    "google_seeded_unclaimed",
    name="listing_source",
    schema=SCHEMA,
)
verification_status_enum = postgresql.ENUM(
    "pending",
    "under_review",
    "approved",
    "rejected",
    name="verification_status",
    schema=SCHEMA,
)


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table. Mirrors
    the `customer_domain`/`saved_addresses` migrations' helper exactly."""
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

    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    provider_type_enum.create(bind, checkfirst=True)
    listing_source_enum.create(bind, checkfirst=True)
    verification_status_enum.create(bind, checkfirst=True)

    # --- providers -----------------------------------------------------
    op.create_table(
        "providers",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "provider_type",
            postgresql.ENUM(
                "business",
                "freelancer",
                name="provider_type",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone_country_code", sa.String(length=5), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("whatsapp_number", sa.String(length=20), nullable=True),
        sa.Column(
            "listing_source",
            postgresql.ENUM(
                "self_registered",
                "google_seeded_unclaimed",
                name="listing_source",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_claimed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("google_place_id", sa.String(length=255), nullable=True),
        sa.Column(
            "verification_status",
            postgresql.ENUM(
                "pending",
                "under_review",
                "approved",
                "rejected",
                name="verification_status",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "is_discoverable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("average_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "review_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("country_code", sa.CHAR(length=2), nullable=False),
        # Decision 4, `Plan_S04_PRO-001.md`: flagged, temporary addition
        # beyond `04_DATABASE.md`'s literal `providers` spec.
        sa.Column("category_label", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("slug", name="uq_providers_slug"),
        sa.CheckConstraint(
            "is_claimed = false OR user_id IS NOT NULL",
            name="chk_providers_claimed_has_owner",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_providers_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_providers_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_providers_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_providers_user_id",
        "providers",
        ["user_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_providers_google_place_id",
        "providers",
        ["google_place_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("google_place_id IS NOT NULL"),
    )
    op.create_index(
        "idx_providers_provider_type", "providers", ["provider_type"], schema=SCHEMA
    )
    op.create_index(
        "idx_providers_is_discoverable",
        "providers",
        ["is_discoverable"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_providers_verification_status",
        "providers",
        ["verification_status"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_providers_country_code", "providers", ["country_code"], schema=SCHEMA
    )

    # --- business_profiles ----------------------------------------------
    op.create_table(
        "business_profiles",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trade_license_number", sa.String(length=100), nullable=True),
        sa.Column("address_line", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("operating_hours", postgresql.JSONB(), nullable=True),
        sa.Column("delivery_radius_meters", sa.Integer(), nullable=True),
        sa.UniqueConstraint("provider_id", name="uq_business_profiles_provider_id"),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_business_profiles_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_business_profiles_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_business_profiles_updated_by",
        ),
        schema=SCHEMA,
    )

    # --- freelancer_profiles ---------------------------------------------
    op.create_table(
        "freelancer_profiles",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_latitude", sa.Double(), nullable=False),
        sa.Column("base_longitude", sa.Double(), nullable=False),
        sa.Column("service_radius_meters", sa.Integer(), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("years_experience", sa.SmallInteger(), nullable=True),
        sa.UniqueConstraint(
            "provider_id", name="uq_freelancer_profiles_provider_id"
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{SCHEMA}.providers.id"],
            name="fk_freelancer_profiles_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_freelancer_profiles_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_freelancer_profiles_updated_by",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_table("freelancer_profiles", schema=SCHEMA)
    op.drop_table("business_profiles", schema=SCHEMA)
    op.drop_table("providers", schema=SCHEMA)

    verification_status_enum.drop(bind, checkfirst=True)
    listing_source_enum.drop(bind, checkfirst=True)
    provider_type_enum.drop(bind, checkfirst=True)

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
