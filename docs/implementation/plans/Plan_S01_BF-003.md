# Plan for Story BF-003 - Configuring Asynchronous Database Connectivity

## Goal Description
Configure asynchronous PostgreSQL connectivity for the FastAPI backend using SQLAlchemy 2.x Async ORM, psycopg v3, connection pooling, and dependency injection, including tests, documentation, and error handling, while avoiding ORM model implementation.

## Architecture Decisions
- Use SQLAlchemy 2.x Async ORM (`create_async_engine`, `async_sessionmaker`, `AsyncSession`).
- Use the modern `psycopg` (v3) database driver.
- Set up connection pooling via `QueuePool` with production-ready defaults:
  - `DB_POOL_SIZE` (default: 5)
  - `DB_MAX_OVERFLOW` (default: 10)
  - `pool_pre_ping=True` (for liveness check on checkout)
- Validate and normalize database URLs in the configuration layer to prevent runtime rewriting discrepancies.
  - Supported incoming formats: `postgresql://`, `postgres://`, `postgresql+psycopg://`.
  - Canonical format returned: `postgresql+psycopg://`.

## Tasks
1. Define database configuration settings (`DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO`) in Pydantic Settings class.
2. Implement validation and protocol normalization in `app/core/config.py`.
3. Set up the async engine and `async_sessionmaker` in `app/core/database/database.py` and `app/core/database/session.py`.
4. Implement a `check_database_connection` helper utility to verify connection on startup.
5. Create dependency injection `get_db` for FastAPI endpoints to retrieve database sessions.
6. Write unit and integration tests to verify connection pooling, session lifecycle, and URL normalization.
7. Update documentation to describe the database layout.
