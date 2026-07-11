# Walkthrough for Story BF-004 - Database Migrations

## Overview
This story establishes Alembic as the project's database migration framework. It integrates Alembic with the existing SQLAlchemy asynchronous engine and `Base.metadata`, loads database configuration dynamically from Pydantic Settings, enables chronological version file naming, and adds programmatic migration test coverage.

## Work Completed

1. **Dependency Installation (`pyproject.toml`)**:
   - Added `alembic>=1.13.1` to the dependencies array.
   - Added `greenlet>=3.0.0` to the dependencies array. SQLAlchemy requires `greenlet` to run synchronous migration tasks on top of an asynchronous engine connection.
   - Ran `uv sync` to update `uv.lock`.

2. **Alembic Environment Setup (`alembic.ini` & `alembic/env.py`)**:
   - Initialized Alembic with the standard async template: `alembic init -t async alembic`.
   - Updated `alembic.ini` to use chronological date-prefixed filenames: `file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s`.
   - Removed the default hardcoded `sqlalchemy.url` from `alembic.ini` to enforce dynamic loading from Settings.
   - Configured `alembic/env.py` to import Pydantic application `settings` and declarative `Base.metadata`.
   - Integrated `alembic/env.py` with the existing asynchronous `engine` singleton from `app.core.database.database` to execute migrations without configuration duplication.

3. **Initial Migration (`alembic/versions/2026_07_03_2335-101b27d7096b_initial_migration.py`)**:
   - Generated the first pipeline-verifying migration script using `uv run alembic revision --autogenerate -m "initial_migration"`.
   - Verified that both `upgrade()` and `downgrade()` contain `pass` statements, reflecting the empty metadata of the backend monorepo at this stage.

4. **Integration Testing (`tests/test_migrations.py`)**:
   - Created programmatic unit tests that verify Alembic config loading.
   - Wrote programmatic integration tests that execute `command.upgrade` and `command.downgrade` on the Alembic configuration using a mocked database connection and dialect properties.

5. **Documentation (`backend/README.md` & `CHANGELOG.md`)**:
   - Added a "Database Migrations" section in `backend/README.md` explaining the layout, common commands, and developer guidelines.
   - Logged Story BF-004 deliverables in the repository's main `CHANGELOG.md`.

---

## Testing Performed

### Manual Verification
Executed local CLI migration flow:
1. Applied upgrade to head:
   ```bash
   uv run alembic upgrade head
   # Output: Running upgrade -> 101b27d7096b, initial_migration
   ```
2. Verified current revision in db:
   ```bash
   uv run alembic current
   # Output: 101b27d7096b (head)
   ```
3. Verified migration history output:
   ```bash
   uv run alembic history --verbose
   # Output: Rev: 101b27d7096b (head)
   ```
4. Performed rollback to base:
   ```bash
   uv run alembic downgrade base
   # Output: Running downgrade 101b27d7096b -> , initial_migration
   ```
5. Verified database returned to base status:
   ```bash
   uv run alembic current
   # Output: (empty/base)
   ```
6. Re-applied upgrade to head to leave the database migrated.

### Automated Tests
Ran the full backend test suite:
```bash
uv run pytest
```
Output:
```
============================== 19 passed in 0.18s ==============================
```
All 19 unit and integration tests passed, verifying config loading, database driver properties, session management, and the migration pipeline.
