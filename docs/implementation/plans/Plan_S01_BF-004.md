# Plan for Story BF-004 - Database Migrations

Configure Alembic as the project's database migration framework using the existing SQLAlchemy models and application configuration. This story is strictly limited to migration infrastructure.

## Goal Description
Configure Alembic database migration infrastructure for the AI Marketplace platform. It integrates with existing SQLAlchemy models and centralized Settings, detects schema changes automatically, and supports all standard migration commands (upgrade, downgrade, history, current, generate).

## Architecture Decisions
- Add `alembic` package to python dependencies.
- Initialize migration environment inside the `backend/` module.
- Set up `backend/alembic/env.py` to:
  - Dynamically load database configuration from the centralized `app.core.config.settings`.
  - Reuse the existing async SQLAlchemy engine from `app.core.database.database` for running migrations in online mode.
  - Bind SQLAlchemy metadata from `app.core.database.base.Base.metadata` to support autogeneration of migration scripts.
- Ensure logging is handled consistently using standard Python logging configurations.

## Tasks
1. Add `alembic` to `pyproject.toml` dependencies and run `uv sync`.
2. Initialize Alembic using `uv run alembic init -t async alembic`.
3. Configure `backend/alembic.ini` to read environment settings and avoid hardcoding secrets.
4. Modify `backend/alembic/env.py` to integrate settings and import the existing engine and `Base` metadata.
5. Generate the initial migration using `--autogenerate`.
6. Implement unit and integration tests to verify database migrations can be programmatically upgraded and downgraded.
7. Update `backend/README.md` and `CHANGELOG.md` with instructions and release information.
8. Verify everything locally and execute migrations.
