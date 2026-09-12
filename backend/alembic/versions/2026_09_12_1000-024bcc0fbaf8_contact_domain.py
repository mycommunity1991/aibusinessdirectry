"""contact_domain

Revision ID: 024bcc0fbaf8
Revises: f3a1c9d47b02
Create Date: 2026-09-12 10:00:00.000000

Creates the `contact` Postgres schema (CON-001) and its first table,
`contact.contact_views`, exactly per `04_DATABASE.md`'s pre-existing
spec (`customer_id`, `provider_id`, `search_request_id`, `viewed_at`) --
full `CommonColumnsMixin` columns (Decision 1,
`Plan_S08_CON-001.md`'s Backend Proposed Changes item 1) plus the three
named indexes.

Deliberately does **not** create `outcome_tags` or `visit_verifications`
-- both are explicitly out of this story's scope (the story's own stated
boundary: "does not include the Outcome Tag prompt or reviews").

The self-dealing guard (Decision 1) is enforced entirely at the service
layer (`ContactService.create_contact_view`), never as a DB constraint
-- `04_DATABASE.md`'s own Contact Domain section explains why a
single-table `CHECK` cannot express a comparison spanning
`customer_profiles`/`providers` joined through `identity.users`.

See `docs/AI/04_DATABASE.md` (Contact Domain) and
`docs/implementation/plans/Plan_S08_CON-001.md` (Decision 1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "024bcc0fbaf8"
down_revision: str | Sequence[str] | None = "f3a1c9d47b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "contact"
IDENTITY_SCHEMA = "identity"
CUSTOMER_SCHEMA = "customer"
PROVIDER_SCHEMA = "provider"
SEARCH_SCHEMA = "search"


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
        "contact_views",
        *_common_columns(),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            [f"{CUSTOMER_SCHEMA}.customer_profiles.id"],
            name="fk_contact_views_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_contact_views_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_id"],
            [f"{SEARCH_SCHEMA}.search_requests.id"],
            name="fk_contact_views_search_request_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_contact_views_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_contact_views_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_contact_views_customer_id",
        "contact_views",
        ["customer_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_contact_views_provider_id",
        "contact_views",
        ["provider_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_contact_views_viewed_at",
        "contact_views",
        ["viewed_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("contact_views", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
