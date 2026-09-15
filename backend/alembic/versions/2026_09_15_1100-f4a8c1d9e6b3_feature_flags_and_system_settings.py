"""feature_flags_and_system_settings

Revision ID: f4a8c1d9e6b3
Revises: 34cd99dbf8db
Create Date: 2026-09-15 11:00:00.000000

Creates `administration.feature_flags` and `administration.system_
settings` (ADM-002, Decision 1, `Plan_S11_ADM-002.md`) --
`administration`'s fifth and sixth aggregate roots, exactly per
`04_DATABASE.md`'s already-specified column shape (designed at
`CLM-001`'s closeout, never previously migrated, explicitly labeled
"remain unbuilt" until this story):

- `feature_flags` -- `key` (VARCHAR(100), not null, unique),
  `is_enabled` (BOOLEAN, not null, default `false`), `description`
  (TEXT, nullable), plus the full `CommonColumnsMixin`.
- `system_settings` -- `key` (VARCHAR(100), not null, unique), `value`
  (JSONB, not null), `description` (TEXT, nullable), plus the full
  `CommonColumnsMixin`.

Mirrors `34cd99dbf8db_unmatched_query_reports.py`'s exact template
(same `_common_columns()` helper, same FK-per-`created_by`/`updated_by`
pattern). Also seeds exactly one row per table (Decision 1's literal
seed values) via a plain `INSERT`, mirroring
`a804c46bf703_category_domain.py`'s data-seeding precedent -- so AC1's
"editable" claim and AC4's "toggling takes effect" claim are both
genuinely exercisable end-to-end from day one:

- `feature_flags`: `key="manual_matching_force_all"`,
  `is_enabled=false`, operationalizing `13_OPEN_DECISIONS.md` item 10
  as a live, no-deploy operational lever (Decision 7) -- defaulted
  `false` so today's existing automated-first behavior is unchanged out
  of the box.
- `system_settings`: `key="support_contact_email"`,
  `value={"email": "support@aimarketplace.example"}` -- a placeholder
  value; nothing reads it at runtime (Open Question 3), it exists
  solely to make AC1's "editable" claim genuinely testable.

See `docs/AI/04_DATABASE.md` (Administration Domain) and
`docs/implementation/plans/Plan_S11_ADM-002.md` (Decision 1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a8c1d9e6b3"
down_revision: str | Sequence[str] | None = "34cd99dbf8db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "administration"
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
        "feature_flags",
        *_common_columns(),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_feature_flags_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_feature_flags_updated_by",
        ),
        sa.UniqueConstraint("key", name="uq_feature_flags_key"),
        schema=SCHEMA,
    )

    op.create_table(
        "system_settings",
        *_common_columns(),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_system_settings_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_system_settings_updated_by",
        ),
        sa.UniqueConstraint("key", name="uq_system_settings_key"),
        schema=SCHEMA,
    )

    _seed_rows()


def _seed_rows() -> None:
    """Decision 1's literal seed values -- exactly one row per table."""
    bind = op.get_bind()

    feature_flags_tbl = sa.table(
        "feature_flags",
        sa.column("key", sa.String),
        sa.column("is_enabled", sa.Boolean),
        sa.column("description", sa.Text),
        schema=SCHEMA,
    )
    system_settings_tbl = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
        schema=SCHEMA,
    )

    bind.execute(
        sa.insert(feature_flags_tbl).values(
            key="manual_matching_force_all",
            is_enabled=False,
            description=(
                "When enabled, every conversation session that would "
                "otherwise auto-match is instead routed through manual "
                "admin review -- a live, no-deploy operational lever "
                "for 13_OPEN_DECISIONS.md item 10."
            ),
        )
    )
    bind.execute(
        sa.insert(system_settings_tbl).values(
            key="support_contact_email",
            value={"email": "support@aimarketplace.example"},
            description=(
                "Contact email surfaced to internal admin tooling; "
                "editable without a deploy."
            ),
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("system_settings", schema=SCHEMA)
    op.drop_table("feature_flags", schema=SCHEMA)
