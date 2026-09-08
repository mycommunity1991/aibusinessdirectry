"""verification_domain

Revision ID: 906b8c537570
Revises: 272b12ab9b2f
Create Date: 2026-09-08 12:00:00.000000

Creates the `verification` Postgres schema (VER-001) and:
- Two new enums, `verification_type` (`freelancer_id`, `business_license`,
  `business_lightweight`) and `document_type` (`emirates_id`,
  `trade_license`, `other`), colocated here as their first consumer
  anywhere in the codebase.
- `verification.verification_records` -- `status` reuses (never
  duplicates) the existing `provider.verification_status` Postgres enum
  type via `postgresql.ENUM(..., name="verification_status",
  schema="provider", create_type=False)` (Decision 1,
  `Plan_S05_VER-001.md`) -- honoring `provider/models.py`'s own
  `_pg_enum` helper's forward-looking comment, written at PRO-002's
  close, instructing exactly this.
- `verification.verification_documents`.

Does **not** touch any `provider`-schema table at all (Decision 2) --
this story never reads or writes `providers.verification_status`/
`is_discoverable`; the source of truth for a provider's own status view
is `verification_records` directly.

See `docs/AI/04_DATABASE.md` (Verification Domain) and
`docs/implementation/plans/Plan_S05_VER-001.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "906b8c537570"
down_revision: str | Sequence[str] | None = "272b12ab9b2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "verification"
PROVIDER_SCHEMA = "provider"
IDENTITY_SCHEMA = "identity"

verification_type_enum = postgresql.ENUM(
    "freelancer_id",
    "business_license",
    "business_lightweight",
    name="verification_type",
    schema=SCHEMA,
)
document_type_enum = postgresql.ENUM(
    "emirates_id",
    "trade_license",
    "other",
    name="document_type",
    schema=SCHEMA,
)


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table. Mirrors
    the `provider_domain`/`provider_storefront` migrations' helper
    exactly."""
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

    verification_type_enum.create(bind, checkfirst=True)
    document_type_enum.create(bind, checkfirst=True)

    # --- verification_records -------------------------------------------
    op.create_table(
        "verification_records",
        *_common_columns(),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "verification_type",
            postgresql.ENUM(
                "freelancer_id",
                "business_license",
                "business_lightweight",
                name="verification_type",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "under_review",
                "approved",
                "rejected",
                name="verification_status",
                schema=PROVIDER_SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_verification_records_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_verification_records_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_verification_records_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_verification_records_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_verification_records_provider_id",
        "verification_records",
        ["provider_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_verification_records_status",
        "verification_records",
        ["status"],
        schema=SCHEMA,
    )

    # --- verification_documents ------------------------------------------
    op.create_table(
        "verification_documents",
        *_common_columns(),
        sa.Column(
            "verification_record_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "document_type",
            postgresql.ENUM(
                "emirates_id",
                "trade_license",
                "other",
                name="document_type",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("ocr_extracted_data", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["verification_record_id"],
            [f"{SCHEMA}.verification_records.id"],
            name="fk_verification_documents_verification_record_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_verification_documents_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_verification_documents_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_verification_documents_record_id",
        "verification_documents",
        ["verification_record_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_table("verification_documents", schema=SCHEMA)
    op.drop_table("verification_records", schema=SCHEMA)

    # `provider.verification_status` is NOT dropped here -- it is owned
    # and managed by the `provider_domain` migration (Decision 1); this
    # migration only ever referenced it via `create_type=False`.
    document_type_enum.drop(bind, checkfirst=True)
    verification_type_enum.drop(bind, checkfirst=True)

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
