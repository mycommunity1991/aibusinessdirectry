# Plan for Story BF-005 - Application Lifecycle Management

Configure application lifecycle management using FastAPI's modern lifespan API so that startup and shutdown events are handled correctly, logging works as expected, and future shared resources are registered inside a centralized `AppState` container.

## Goal Description
Configure FastAPI's modern lifespan API inside `app/core/lifespan.py`, register it in `app/main.py`, implement startup validation and logging, implement graceful shutdown cleanup, write comprehensive tests, and update documentation.

## Architecture Decisions
- Isolate lifecycle management into `app/core/lifespan.py` away from `app/main.py`.
- Use modern FastAPI `lifespan` parameter during application creation rather than deprecated event decorators (`@app.on_event("startup")` / `@app.on_event("shutdown")`).
- Use standard Python logging with the existing logging configuration (`logging.getLogger(__name__)`).
- Ensure startup failures stop application startup, log errors, and prevent partially initialized state.
- Ensure shutdown executes cleanup safely, wrapping tasks (such as database engine disposal) in separate try-except blocks so one failure does not prevent others from running.
- Define a strongly typed `AppState` container in `app/core/app_state.py` for shared resources, and register it under `app.state.services` on startup to avoid cluttering `app.state` with multiple top-level attributes.

## Tasks
1. Create `app/core/app_state.py` containing the `AppState` dataclass.
2. Update `app/core/lifespan.py` to:
   - Implement configuration validation (`validate_config()`).
   - Log application start ("Application starting") and startup completion ("Startup completed").
   - Register the `AppState` container under `app.state.services`.
   - Log shutdown initiation ("Shutdown initiated") and completion ("Shutdown completed").
   - Gracefully dispose of the database engine connection pool (`app.state.services.db_engine.dispose()`), logging any exceptions.
3. Ensure `app/main.py` properly registers `lifespan`.
4. Create unit tests in `tests/test_lifespan.py` using FastAPI's `TestClient` to verify:
   - Lifespan registration on the app.
   - Successful startup logging and state container initialization.
   - Successful shutdown logging and database engine disposal.
   - Startup failure handling when configuration validation fails.
   - Graceful cleanup during shutdown.
5. Update `CHANGELOG.md` and documentation about lifespan registration.
