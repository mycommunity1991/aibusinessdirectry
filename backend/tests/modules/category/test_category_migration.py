"""
Live-executed migration tests for `category_domain` (CTG-001, AC1/AC4).

Unlike `tests/test_migrations.py` (which exercises Alembic's CLI
plumbing against a fully-mocked connection), these tests run the
`category_domain` revision's actual `upgrade()`/`downgrade()` Python
functions directly against a real Postgres connection, via
`alembic.runtime.migration.MigrationContext.configure(connection)` +
`alembic.operations.Operations.context(...)` (the standard way to run a
single migration's operations outside the full `alembic upgrade head`
CLI flow) -- Decision 5, `Plan_S07_CTG-001.md`.

This proves AC4's idempotency claim ("upgrade run twice", and
"upgrade -> downgrade -> upgrade") for real, against actual `ON
CONFLICT DO NOTHING`/`RETURNING` behavior, not merely by asserting it.
"""

import importlib.util
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest_asyncio
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.modules.category import seed_data
from app.modules.category.models import Category, CategoryQuestionTemplate

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://dumbo@localhost:5432/ai_marketplace_test",
)

_VERSIONS_DIR = Path(__file__).resolve().parents[3] / "alembic" / "versions"


def _load_category_domain_migration() -> ModuleType:
    """
    Loads the `category_domain` migration module directly from its file
    (Alembic version files are not ordinarily importable -- their
    filenames start with a date and contain hyphens). Located by
    filename suffix rather than a hardcoded revision id, so this test
    keeps working if the revision id is ever regenerated.
    """
    matches = list(_VERSIONS_DIR.glob("*_category_domain.py"))
    assert len(matches) == 1, (
        f"Expected exactly one category_domain migration file under "
        f"{_VERSIONS_DIR}, found: {matches}"
    )
    spec = importlib.util.spec_from_file_location(
        "category_domain_migration", matches[0]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = _load_category_domain_migration()


def _run_upgrade(sync_conn: Connection) -> None:
    context = MigrationContext.configure(sync_conn)
    with Operations.context(context):
        MIGRATION.upgrade()


def _run_downgrade(sync_conn: Connection) -> None:
    context = MigrationContext.configure(sync_conn)
    with Operations.context(context):
        MIGRATION.downgrade()


@pytest_asyncio.fixture
async def migration_engine() -> AsyncGenerator[AsyncEngine]:
    """
    A scratch engine bound to the same real local Postgres test
    database as `tests/conftest.py`'s `db_engine`, but deliberately does
    **not** create `category`'s own tables via `Base.metadata.
    create_all()` -- this test module's entire point is to prove the
    `category_domain` migration's own `upgrade()`/`downgrade()` create
    those tables correctly and idempotently, so they must not already
    exist before the migration under test runs. Every *other* domain
    schema/table this migration's foreign keys point at
    (`identity.users`, `provider.providers`) is created normally.
    """
    import app.modules.administration.models  # noqa: F401
    import app.modules.audit.models  # noqa: F401
    import app.modules.customer.models  # noqa: F401
    import app.modules.identity.models  # noqa: F401
    import app.modules.notification.models  # noqa: F401
    import app.modules.provider.models  # noqa: F401
    import app.modules.verification.models  # noqa: F401
    from app.database.base import Base

    non_category_tables = [
        t for t in Base.metadata.sorted_tables if t.schema != "category"
    ]

    engine = create_async_engine(TEST_DATABASE_URL, future=True)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS customer"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS provider"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS verification"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS administration"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS notification"))
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=non_category_tables
            )
        )

    yield engine

    async with engine.begin() as conn:
        # Drop `category`'s schema/tables (created by the migration
        # under test, not by this fixture) first, in case a test left
        # it seeded (e.g. forgot to call downgrade()).
        await conn.execute(text("DROP SCHEMA IF EXISTS category CASCADE"))
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(
                sync_conn, tables=non_category_tables
            )
        )
        await conn.execute(text("DROP SCHEMA IF EXISTS identity CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS audit CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS customer CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS provider CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS verification CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS administration CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS notification CASCADE"))
    await engine.dispose()


async def _category_count(engine: AsyncEngine) -> int:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Category))
        return result.scalar_one()


async def _question_counts_by_slug(engine: AsyncEngine) -> dict[str, int]:
    """Question-template row counts per category slug, read from the
    real database -- compared against `seed_data.QUESTION_SEED_BY_SLUG`
    itself (never re-typed literals) so this test stays correct if the
    seed data is ever edited in place."""
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(Category.slug, func.count(CategoryQuestionTemplate.id))
            .select_from(Category)
            .outerjoin(
                CategoryQuestionTemplate,
                CategoryQuestionTemplate.category_id == Category.id,
            )
            .group_by(Category.slug)
        )
        return dict(result.tuples().all())


def _assert_seed_counts_match(counts: dict[str, int]) -> None:
    assert len(counts) == 14
    for slug, expected_questions in seed_data.QUESTION_SEED_BY_SLUG.items():
        assert counts[slug] == len(expected_questions), (
            f"expected {len(expected_questions)} questions for '{slug}', "
            f"found {counts.get(slug)}"
        )


class TestUpgradeSeedsTheTaxonomy:
    async def test_single_upgrade_seeds_14_categories_and_their_questions(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)

        assert await _category_count(migration_engine) == 14
        _assert_seed_counts_match(await _question_counts_by_slug(migration_engine))


class TestUpgradeRunTwiceIsIdempotent:
    async def test_second_upgrade_against_the_same_schema_inserts_nothing_new(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)

        assert await _category_count(migration_engine) == 14
        _assert_seed_counts_match(await _question_counts_by_slug(migration_engine))


class TestUpgradeDowngradeUpgradeIsIdempotent:
    async def test_downgrade_then_upgrade_reseeds_cleanly_with_no_duplicates(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_downgrade)
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)

        assert await _category_count(migration_engine) == 14
        _assert_seed_counts_match(await _question_counts_by_slug(migration_engine))


def _inspect_after_upgrade(sync_conn: Connection) -> dict[str, Any]:
    _run_upgrade(sync_conn)
    inspector = inspect(sync_conn)
    return {
        "categories_columns": {
            c["name"]: c
            for c in inspector.get_columns("categories", schema="category")
        },
        "categories_unique_constraints": inspector.get_unique_constraints(
            "categories", schema="category"
        ),
        "categories_foreign_keys": inspector.get_foreign_keys(
            "categories", schema="category"
        ),
        "questions_columns": {
            c["name"]: c
            for c in inspector.get_columns(
                "category_question_templates", schema="category"
            )
        },
        "questions_indexes": inspector.get_indexes(
            "category_question_templates", schema="category"
        ),
        "questions_foreign_keys": inspector.get_foreign_keys(
            "category_question_templates", schema="category"
        ),
        "provider_categories_columns": {
            c["name"]: c
            for c in inspector.get_columns("provider_categories", schema="category")
        },
        "provider_categories_pk": inspector.get_pk_constraint(
            "provider_categories", schema="category"
        ),
        "provider_categories_indexes": inspector.get_indexes(
            "provider_categories", schema="category"
        ),
        "provider_categories_foreign_keys": inspector.get_foreign_keys(
            "provider_categories", schema="category"
        ),
    }


class TestSchemaMatchesDatabaseDoc:
    """AC1: column types, nullability, constraints (`uq_categories_slug`)
    and both named indexes match `04_DATABASE.md`'s Category Domain
    section exactly."""

    async def test_categories_table_matches_spec(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            info = await conn.run_sync(_inspect_after_upgrade)

        columns = info["categories_columns"]
        assert columns["parent_category_id"]["nullable"] is True
        assert columns["name"]["nullable"] is False
        assert columns["name"]["type"].length == 100
        assert columns["name_ar"]["nullable"] is True
        assert columns["name_ar"]["type"].length == 100
        assert columns["slug"]["nullable"] is False
        assert columns["slug"]["type"].length == 120
        assert columns["icon_url"]["nullable"] is True
        assert columns["icon_url"]["type"].length == 500
        assert columns["sort_order"]["nullable"] is False
        # Common columns (CommonColumnsMixin-equivalent).
        for common_column in (
            "id",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "is_active",
            "version",
        ):
            assert common_column in columns

        unique_names = {
            uc["name"] for uc in info["categories_unique_constraints"]
        }
        assert "uq_categories_slug" in unique_names

        self_fk_columns = [
            fk["constrained_columns"] for fk in info["categories_foreign_keys"]
        ]
        assert ["parent_category_id"] in self_fk_columns

    async def test_category_question_templates_table_matches_spec(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            info = await conn.run_sync(_inspect_after_upgrade)

        columns = info["questions_columns"]
        assert columns["category_id"]["nullable"] is False
        assert columns["question_text"]["nullable"] is False
        assert columns["question_text"]["type"].length == 500
        assert columns["question_text_ar"]["nullable"] is True
        assert columns["question_text_ar"]["type"].length == 500
        assert columns["question_type"]["nullable"] is False
        assert columns["question_type"]["type"].length == 30
        assert columns["options"]["nullable"] is True
        assert "JSONB" in str(columns["options"]["type"]).upper()
        assert columns["is_required"]["nullable"] is False
        assert columns["sort_order"]["nullable"] is False

        index_names = {ix["name"] for ix in info["questions_indexes"]}
        assert "idx_category_question_templates_category_id" in index_names

        fk_columns = [
            fk["constrained_columns"] for fk in info["questions_foreign_keys"]
        ]
        assert ["category_id"] in fk_columns

        # No unique constraint on this table (Decision 2's idempotency
        # gating relies on this being absent).
        assert "questions_unique_constraints" not in info

    async def test_provider_categories_join_table_matches_spec(
        self, migration_engine: AsyncEngine
    ) -> None:
        async with migration_engine.begin() as conn:
            info = await conn.run_sync(_inspect_after_upgrade)

        columns = info["provider_categories_columns"]
        assert columns["provider_id"]["nullable"] is False
        assert columns["category_id"]["nullable"] is False
        assert columns["is_primary"]["nullable"] is False
        assert columns["created_at"]["nullable"] is False
        # Join table -- no CommonColumnsMixin columns.
        for absent_column in ("id", "updated_at", "deleted_at", "version"):
            assert absent_column not in columns

        pk = info["provider_categories_pk"]
        assert set(pk["constrained_columns"]) == {"provider_id", "category_id"}
        assert pk["name"] == "pk_provider_categories"

        index_names = {ix["name"] for ix in info["provider_categories_indexes"]}
        assert "idx_provider_categories_category_id" in index_names

        fk_columns = {
            tuple(fk["constrained_columns"]): fk["referred_table"]
            for fk in info["provider_categories_foreign_keys"]
        }
        assert fk_columns[("provider_id",)] == "providers"
        assert fk_columns[("category_id",)] == "categories"

    async def test_provider_categories_table_is_created_empty(
        self, migration_engine: AsyncEngine
    ) -> None:
        """AC6 / Explicitly Out of Scope: `provider_categories` gets no
        rows from this story's migration."""
        async with migration_engine.begin() as conn:
            await conn.run_sync(_run_upgrade)
            count = await conn.scalar(
                text("SELECT count(*) FROM category.provider_categories")
            )

        assert count == 0
