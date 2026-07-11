# Rule: SQLAlchemy Async Patterns

## SQLAlchemy 2.x Paradigm
* **Session Management:** Strictly use `AsyncSession`. Do not mix synchronous sessions (`Session`) with asynchronous routes.
* **2.0 Style Executions:** Always use the new 2.0-style constructs (`select()`, `insert()`, `update()`, `delete()`). Legacy 1.x `Query` objects (`session.query()`) are strictly prohibited.

## Handling Relationships
* **No Lazy Loading:** Lazy loading is strictly prohibited in async contexts. Attempting to lazy-load a relationship will trigger implicit synchronous I/O, resulting in `MissingGreenlet` errors.
* **Explicit Eager Loading:** Always use explicit relationship loading strategies (`selectinload` for collections, `joinedload` for many-to-one) when querying entities that require their relations.

## Migrations & Connection Pooling
* **Alembic Driven:** All schema changes must be driven by Alembic migrations. Never rely on `Base.metadata.create_all()` in production or staging environments.
* **Connection Pooling:** Ensure the async engine uses `asyncpg` with appropriate connection pooling limits (e.g., `QueuePool`) configured via environment variables to prevent exhausting database connections under load.