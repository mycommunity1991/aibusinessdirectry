# Plan for Story BF-007 - Health Check Endpoints (Refined)

Implement lightweight, production-ready health check endpoints to verify API application availability and database connectivity.

## Goal Description

Provide endpoints to allow developers, load balancers, container orchestrators, and monitoring systems to verify backend application status (`GET /api/v1/health`) and database connectivity (`GET /api/v1/health/db`).

- `/api/v1/health`: Lightweight application health check, does not perform database access. Includes detailed OpenAPI responses and examples.
- `/api/v1/health/db`: Database connectivity verification, runs a lightweight `SELECT 1` query using SQLAlchemy's `text()`, returning `503 Service Unavailable` if unreachable. Both 200 and 503 responses use the `DatabaseHealthResponse` schema directly, setting the status code dynamically to avoid bypassing the Pydantic serialization.

---

## User Review Required

> [!IMPORTANT]
> The database health check endpoint uses FastAPI's `Response` object to dynamically set the status code to `503 Service Unavailable` on failures. This ensures both success and failure paths return `DatabaseHealthResponse` directly, maintaining OpenAPI validation compatibility.
>
> The database session `get_db` is implemented as an async context manager generator (`async with async_session() as session:`). This guarantees that the session's `__aexit__` is executed and the database connection is returned to the pool, even if query execution raises an exception.

---

## Open Questions

None.

---

## Proposed Changes

### Core Constants

#### [MODIFY] [constants.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/core/constants.py)
*No further changes required (constants already created).*

---

### Schemas

#### [MODIFY] [health.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/schemas/health.py)
*No further changes required (schemas already created).*

---

### Services

#### [MODIFY] [health_service.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/services/health_service.py)
- Maintain modular structure:
  - `get_app_health() -> HealthResponse`
  - `get_db_health(db: AsyncSession) -> DatabaseHealthResponse`

---

### API Routers

#### [MODIFY] [health.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/api/v1/endpoints/health.py)
- Refactor `get_db_health` endpoint to:
  - Inject `response: Response`.
  - Check `service.get_db_health(db)`.
  - Set `response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE` if the status is `"unhealthy"`.
  - Return the `DatabaseHealthResponse` directly.
- Add explicit OpenAPI response configurations, descriptions, and examples for both endpoints.

---

### Automated Tests

#### [MODIFY] [test_health.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/tests/test_health.py)
- Verify tests cover the updated endpoint implementation (verifying schema compliance on both 200 and 503 responses).

---

## Verification Plan

### Automated Tests
Run backend tests:
```bash
uv run pytest
```

### Manual Verification
- View FastAPI Swagger UI at `/docs` to confirm detailed response documentation and examples are properly displayed.
