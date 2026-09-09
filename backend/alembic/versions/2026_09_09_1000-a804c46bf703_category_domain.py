"""category_domain

Revision ID: a804c46bf703
Revises: a3f6e9c21d47
Create Date: 2026-09-09 10:00:00.000000

Creates the `category` Postgres schema (CTG-001) and its three tables
exactly per `04_DATABASE.md`'s Category Domain section:

- `category.categories` -- full `CommonColumnsMixin`-equivalent columns
  (mirroring `administration_domain`'s `_common_columns()` helper) plus
  `parent_category_id` (self-FK, nullable), `name`, `name_ar`, `slug`
  (`uq_categories_slug`), `icon_url`, `sort_order`.
- `category.category_question_templates` -- full
  `CommonColumnsMixin`-equivalent columns plus `category_id` (FK ->
  `categories.id`), `question_text`, `question_text_ar`,
  `question_type`, `options` (JSONB), `is_required`, `sort_order`.
- `category.provider_categories` -- pure join table (composite PK,
  `created_at` only, no `CommonColumnsMixin`), created **empty**:
  reconciling `provider.provider_category_labels` into this table is
  explicitly deferred to a future story (`13_OPEN_DECISIONS.md` item 1).

Also seeds the CTO-approved v1 launch taxonomy
(`docs/AI/17_CATEGORY_TAXONOMY.md` -- 14 categories and their AI
follow-up question templates) via an idempotent
`INSERT ... ON CONFLICT (slug) DO NOTHING ... RETURNING` against
`categories`, gating each category's question-template insert batch on
that category having been *freshly inserted this run* (Decision 2,
`Plan_S07_CTG-001.md`) -- `category_question_templates` has no unique
constraint of its own (per `04_DATABASE.md`'s spec), so its own
idempotency is entirely inherited from `categories.slug`'s conflict
target: a re-run (upgrade run twice, or upgrade -> downgrade -> upgrade)
inserts zero categories AND zero question rows the second time. Seed
content itself lives in `app.modules.category.seed_data` (plain data,
no ORM import) so it is never transcribed twice.

**Arabic content caveat (Decision 4):** both `name_ar` and
`question_text_ar` are seeded with `17_CATEGORY_TAXONOMY.md` v1.1.0's
first-pass Arabic text (categories and all 47 question templates) -- a
first-pass translation, not yet native-speaker-verified; do not treat
as launch-final. (v1.0.0 of that document did not actually contain any
per-question Arabic text despite claiming the caveat covered it;
`question_text_ar` was seeded `NULL` in this migration's first version
rather than fabricate translations with no source -- v1.1.0 supplied
the missing text, see `seed_data.py`'s module docstring for the full
history.)

This is this codebase's first data-seeding migration -- every prior
migration is schema/DDL only. Flagged for `architect`'s attention per
`Plan_S07_CTG-001.md` Decision 2.

See `docs/AI/04_DATABASE.md` (Category Domain) and
`docs/implementation/plans/Plan_S07_CTG-001.md`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.modules.category import seed_data

# revision identifiers, used by Alembic.
revision: str = "a804c46bf703"
down_revision: str | Sequence[str] | None = "a3f6e9c21d47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "category"
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


def _seed_taxonomy() -> None:
    """
    Decision 2's idempotent seed step: inserts `seed_data.CATEGORY_SEED`
    via `ON CONFLICT (slug) DO NOTHING ... RETURNING`, then inserts each
    freshly-inserted category's question templates from
    `seed_data.QUESTION_SEED_BY_SLUG`. A category whose `slug` already
    exists is not returned by the `RETURNING` clause, so its question
    templates are never (re-)inserted -- the whole seed step is a no-op
    on a re-run against an already-seeded database.
    """
    bind = op.get_bind()

    categories_tbl = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("sort_order", sa.SmallInteger),
        schema=SCHEMA,
    )
    questions_tbl = sa.table(
        "category_question_templates",
        sa.column("category_id", postgresql.UUID(as_uuid=True)),
        sa.column("question_text", sa.String),
        sa.column("question_text_ar", sa.String),
        sa.column("question_type", sa.String),
        sa.column("options", postgresql.JSONB),
        sa.column("is_required", sa.Boolean),
        sa.column("sort_order", sa.SmallInteger),
        schema=SCHEMA,
    )

    insert_categories_stmt = (
        postgresql.insert(categories_tbl)
        .values(seed_data.CATEGORY_SEED)
        .on_conflict_do_nothing(index_elements=["slug"])
        .returning(categories_tbl.c.id, categories_tbl.c.slug)
    )
    freshly_inserted = bind.execute(insert_categories_stmt).fetchall()

    if not freshly_inserted:
        # Every category already existed -- gate transitively means zero
        # question rows are inserted either, proving idempotency.
        return

    question_rows = [
        {
            "category_id": row.id,
            "question_text": question["question_text"],
            "question_text_ar": question["question_text_ar"],
            "question_type": question["question_type"],
            "options": question["options"],
            "is_required": question["is_required"],
            "sort_order": question["sort_order"],
        }
        for row in freshly_inserted
        for question in seed_data.QUESTION_SEED_BY_SLUG[row.slug]
    ]

    if question_rows:
        bind.execute(sa.insert(questions_tbl), question_rows)


def upgrade() -> None:
    """Upgrade schema.

    DDL (schema/table/index creation) is guarded by an existence check
    so that calling `upgrade()` a second time against an
    already-migrated database (AC4's literal "upgrade run twice" case,
    Decision 5's `test_category_migration.py`) is safe end-to-end, not
    only for the seed-insert step -- a real `alembic upgrade head` run
    never actually re-invokes a revision's `upgrade()` after Alembic's
    own version bookkeeping records it as applied, but AC4 explicitly
    asks this to be proven true even bypassing that bookkeeping.
    """
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    bind = op.get_bind()
    tables_already_exist = "categories" in sa.inspect(bind).get_table_names(
        schema=SCHEMA
    )

    if not tables_already_exist:
        _create_tables()

    _seed_taxonomy()


def _create_tables() -> None:
    op.create_table(
        "categories",
        *_common_columns(),
        sa.Column("parent_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_ar", sa.String(length=100), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column(
            "sort_order", sa.SmallInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
        sa.ForeignKeyConstraint(
            ["parent_category_id"],
            [f"{SCHEMA}.categories.id"],
            name="fk_categories_parent_category_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_categories_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_categories_updated_by",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "category_question_templates",
        *_common_columns(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_text", sa.String(length=500), nullable=False),
        sa.Column("question_text_ar", sa.String(length=500), nullable=True),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "sort_order", sa.SmallInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            [f"{SCHEMA}.categories.id"],
            name="fk_category_question_templates_category_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_category_question_templates_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_category_question_templates_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_category_question_templates_category_id",
        "category_question_templates",
        ["category_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "provider_categories",
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "provider_id", "category_id", name="pk_provider_categories"
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            [f"{PROVIDER_SCHEMA}.providers.id"],
            name="fk_provider_categories_provider_id",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            [f"{SCHEMA}.categories.id"],
            name="fk_provider_categories_category_id",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_provider_categories_category_id",
        "provider_categories",
        ["category_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("provider_categories", schema=SCHEMA)
    op.drop_table("category_question_templates", schema=SCHEMA)
    op.drop_table("categories", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
