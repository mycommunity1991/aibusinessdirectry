"""saved_addresses

Revision ID: 9f47869ca8bb
Revises: 35cd57521089
Create Date: 2026-09-06 15:00:00.000000

Creates `customer.saved_addresses` (CUS-002), 1:N with
`customer_profiles`, column-for-column per `docs/AI/04_DATABASE.md`
(Customer Domain, "saved_addresses").

Also creates `uq_saved_addresses_customer_default`, a partial unique
index on `customer_id` (`WHERE is_default = true AND is_active = true`)
-- a defense-in-depth addition beyond `04_DATABASE.md`'s literal text for
this table (Decision 2, `Plan_S03_CUS-002.md`). The real uniqueness
guarantee is `SavedAddressService`'s transactional unset-then-set on
every "set default" write path; this index only backstops it. Carries
zero migration risk: brand-new table, no pre-existing data. Flagged for
a follow-up `04_DATABASE.md` update at story close, mirroring this
project's existing partial-unique-default precedent
(`uq_users_email_provider`, `uq_users_phone`, `uq_users_external_auth`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f47869ca8bb"
down_revision: str | Sequence[str] | None = "35cd57521089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "customer"
IDENTITY_SCHEMA = "identity"


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table. Mirrors
    the `customer_domain` migration's helper exactly."""
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
        "saved_addresses",
        *_common_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=True),
        sa.Column("address_line", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.CHAR(length=2), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{SCHEMA}.customer_profiles.id"],
            name="fk_saved_addresses_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_saved_addresses_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_saved_addresses_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_saved_addresses_customer_id",
        "saved_addresses",
        ["customer_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_saved_addresses_customer_default",
        "saved_addresses",
        ["customer_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("is_default = true AND is_active = true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("saved_addresses", schema=SCHEMA)
