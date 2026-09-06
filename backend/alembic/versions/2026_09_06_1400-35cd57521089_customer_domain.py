"""customer_domain

Revision ID: 35cd57521089
Revises: d81be77c601d
Create Date: 2026-09-06 14:00:00.000000

Creates the `customer` Postgres schema and its two CUS-001 tables:
`customer_profiles` (1:1 with `identity.users`) and `customer_preferences`
(1:1 with `customer_profiles`). See `docs/AI/04_DATABASE.md` (Customer
Domain) and `docs/implementation/plans/Plan_S03_CUS-001.md`.

`customer_preferences.language` reuses the exact `identity.language_code`
Postgres enum type already created by the identity-domain migration
(`create_type=False` -- Decision 2 of the Plan) rather than creating a
duplicate type. `notification_channel` has no prior schema presence
anywhere -- this is its first consumer, so it is created here, scoped to
the `customer` schema.

Deliberately does NOT create `saved_addresses` (CUS-002, a separate,
not-yet-built story) even though `04_DATABASE.md` documents it in the
same "Customer Domain" section.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35cd57521089"
down_revision: str | Sequence[str] | None = "d81be77c601d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "customer"
IDENTITY_SCHEMA = "identity"

notification_channel_enum = postgresql.ENUM(
    "whatsapp", "sms", "email", name="notification_channel", schema=SCHEMA
)


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table. Mirrors
    `identity_domain`'s migration helper exactly."""
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

    notification_channel_enum.create(bind, checkfirst=True)

    # --- customer_profiles ------------------------------------------------
    op.create_table(
        "customer_profiles",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_customer_profiles_user_id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_customer_profiles_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_customer_profiles_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_customer_profiles_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_customer_profiles_user_id",
        "customer_profiles",
        ["user_id"],
        schema=SCHEMA,
    )

    # --- customer_preferences ----------------------------------------------
    op.create_table(
        "customer_preferences",
        *_common_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_channel",
            postgresql.ENUM(
                "whatsapp",
                "sms",
                "email",
                name="notification_channel",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="whatsapp",
        ),
        sa.Column(
            "language",
            postgresql.ENUM(
                "en",
                "ar",
                name="language_code",
                schema=IDENTITY_SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="en",
        ),
        sa.UniqueConstraint("customer_id", name="uq_customer_preferences_customer_id"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{SCHEMA}.customer_profiles.id"],
            name="fk_customer_preferences_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_customer_preferences_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_customer_preferences_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_customer_preferences_customer_id",
        "customer_preferences",
        ["customer_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_table("customer_preferences", schema=SCHEMA)
    op.drop_table("customer_profiles", schema=SCHEMA)

    notification_channel_enum.drop(bind, checkfirst=True)
    # `language_code` is NOT dropped here -- it is owned by the
    # identity-domain migration (`create_type=False` above); dropping it
    # here would break `identity.users.preferred_language`.

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
