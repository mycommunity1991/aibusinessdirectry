# Plan for Story BF-006 - API Versioning

Establish a clean, modular, and scalable API versioning infrastructure for the AI Marketplace backend.

## Goal Description

Implement API versioning for the backend. Uses URI-based versioning, establishes `/api/v1` as the initial public API, makes future versions easy to introduce, keeps routing modular, and ensures startup verification checks route health and prevents duplicate route registration.

## Architecture Decisions

- **API Prefixes**: Store API prefixes centrally in `app/core/constants.py` as `API_PREFIX = "/api"` and `API_V1 = "/v1"`.
- **Modular Routers**:
  - The root router `app/api/router.py` includes `v1_router` under prefix `API_V1`.
  - The version router `app/api/v1/api.py` includes specific routers like `health_router`.
  - Individual endpoints (like health check) reside in `app/api/v1/endpoints/health.py` and assign the tags dynamically.
- **Startup Route Verification**:
  - Implement a verification check in `app/core/lifespan.py` (`verify_routes`) that checks all registered routes on startup to ensure routers loaded, registration succeeded, and no duplicate routes exist.

## Tasks

1. **Centralize Constants**:
   - Create `app/core/constants.py` defining `API_PREFIX` and `API_V1`.
   - Update `app/core/config.py` to use `API_PREFIX` from `constants.py`.
   - Update `.env.example` to show `API_PREFIX=/api`.
2. **Implement API v1 and Health Endpoint**:
   - Create `app/api/v1/endpoints/health.py` with the `/health` endpoint returning `{"status": "healthy"}` and tagged under `"Health"`.
   - Create `app/api/v1/api.py` (Version 1 router) which includes `health.py`'s router.
3. **Configure Root Router**:
   - Update `app/api/router.py` to include `v1_router` with prefix `API_V1`.
4. **Implement Startup Route Verification**:
   - Add `verify_routes` to `app/core/lifespan.py`.
   - Call `verify_routes` during lifespan startup.
5. **Verify and Test**:
   - Create unit/integration tests in `tests/test_routing.py` to verify routes, response content, and duplicate route detection.
   - Run tests using `uv run pytest`.
   - Verify linting and formatting.
6. **Documentation**:
   - Update backend `README.md` or other developer documentation to describe the API versioning strategy and how to add new versions.
   - Update `CHANGELOG.md`.
