# Rule: Python / FastAPI Tech Stack Idioms

## Directive
You must strictly adhere to the official AI Marketplace technology stack. You are writing Python 3.14+ and must utilize the specific approved frameworks. Do not introduce competing technologies or outdated idioms.

## Core Rules

1.  **Framework Execution:** All routing and API handling must use FastAPI. Do not introduce Flask, Django, or raw WSGI middleware. Serve using Uvicorn.
2.  **Data Validation:** All request payloads, response serialization, and environment configuration must be handled using Pydantic v2.
3.  **Persistence:** Use SQLAlchemy 2.x for all ORM mapping. You must use SQLAlchemy 2.0 style queries (e.g., `select(Entity).where(...)`) and reject legacy 1.x `.query()` patterns. Database migrations must be managed via Alembic.
4.  **Database Engine:** The primary datastore is PostgreSQL, caching is handled via Redis, and database connections should use the `psycopg` driver. 
5.  **Security Implementation:** Implement JWT Access/Refresh tokens using `python-jose` and hash passwords using Argon2id via `pwdlib`. 
6.  **Code Quality:** Enforce `Black` for formatting and `Ruff` for linting. Strict type hinting is mandatory across the entire codebase. Write tests exclusively using `pytest`.

## Anti-Patterns to Reject

* **Rogue Dependencies:** Reject PRs that introduce unapproved libraries like Celery, RabbitMQ, or MongoDB without explicit architectural approval. (Use FastAPI Background Tasks for basic asynchronous work during Phase 1).
* **Untyped Python:** Reject PRs lacking complete type hints for function arguments and return types. 
* **Manual JSON Parsing:** Reject code that uses the standard `json` library to manually validate or deserialize HTTP payloads instead of using Pydantic schemas.