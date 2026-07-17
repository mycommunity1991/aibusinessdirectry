# Standardized API Response Models

This plan implements standardized API response models to ensure all API endpoints return a consistent response contract for success, collections, pagination, and errors, satisfying the requirements of story BF-010.

## User Review Required

- Please confirm if there are any `Readiness` and `Liveness` endpoints that are separate from the `/` and `/db` endpoints in `backend/app/api/v1/endpoints/health.py`. Only `/` and `/db` exist in that file right now. I will proceed assuming `/` and `/db` are the intended health endpoints.

## Open Questions

- None.

## Proposed Changes

---

### Shared Schemas

I will create a new shared schema file for common response models using Pydantic v2 Generics. This module will become the single source of truth for all HTTP responses across the backend. I will migrate the existing error schemas from `app/core/exceptions/responses.py` to this new shared module to prevent duplication and ensure consistency.

#### [NEW] [response.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/app/shared/schemas/response.py)
This file will contain the following generic Pydantic v2 models:
- `BaseResponse`
- `SuccessResponse[T]`
- `CollectionResponse[T]`
- `PaginationMeta`
- `ErrorDetail`
- `ErrorResponse`

#### [DELETE] [responses.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/app/core/exceptions/responses.py)
This file will be deleted and its models (`ErrorDetail`, `ErrorResponse`) will be moved to the new `backend/app/shared/schemas/response.py`.

---

### Core Exceptions

Update imports to reference the new location of the error models.

#### [MODIFY] [exceptions.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/app/core/exceptions/exceptions.py)
Update import for `ErrorDetail`.

#### [MODIFY] [handlers.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/app/core/exceptions/handlers.py)
Update import for `ErrorDetail` and `ErrorResponse`.

---

### API Endpoints

Update the existing health endpoints to use the new `SuccessResponse` schema.

#### [MODIFY] [health.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/app/api/v1/endpoints/health.py)
- Wrap `HealthResponse` and `DatabaseHealthResponse` inside `SuccessResponse`.
- Update the API routes and OpenAPI schema definitions to return the appropriate `SuccessResponse[HealthResponse]` and `SuccessResponse[DatabaseHealthResponse]`.
- Return the exact same business logic results wrapped in the `data` field of the generic model.

---

### Tests

Update existing tests to reference the new schemas, and create new tests for the new response models.

#### [MODIFY] [test_exceptions.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/tests/test_exceptions.py)
Update import for `ErrorDetail`.

#### [NEW] [test_responses.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/tests/test_responses.py)
Add unit tests covering:
- Success response serialization
- Collection response serialization
- Pagination model serialization
- Error response serialization
- Generic type support and JSON output structure.

#### [MODIFY] [test_health.py](file:///Users/dumbo/Documents/AI Marketplace/product/app/backend/tests/api/v1/test_health.py) (if exists)
Update any health tests to expect the new response format (e.g. `{"success": true, "message": "...", "data": ...}`).

## Verification Plan

### Automated Tests
- Run `pytest backend/tests/` to verify all new and existing tests pass.
- Run `ruff check backend/` and `ruff format --check backend/` to ensure code quality rules pass.

### Manual Verification
- Start the server and visit `/docs` (Swagger UI) to verify that the OpenAPI specification correctly renders the new generic response models, pagination metadata, and error details.
