# Sprint 1 - BF-009: Global Exception Handling

## Changes Made

Implemented a centralized global exception handling mechanism for the FastAPI application that normalizes all errors into a standardized response format.

### 1. Centralized Exception Package
- Created the `app/core/exceptions` package.
- Removed legacy `app/core/exceptions.py` and `app/api/exceptions.py`.

### 2. Standardized Error Response Models
- Created `ErrorResponse` and `ErrorDetail` models in `responses.py`.
- Enforced `success: Literal[False] = False`.
- Made `ErrorDetail.field` optional.

### 3. Error Constants
- Created `constants.py` to house common error messages to prevent hardcoded strings in handlers.

### 4. Custom Business Exception
- Added `BusinessException` which supports setting `status_code`, `message`, `errors`, and optional HTTP `headers`.

### 5. Exception Handlers
- **Validation**: Handles `RequestValidationError`, normalizes the `loc` fields to return actual property names, and logs at the `INFO` level.
- **HTTP**: Handles `HTTPException`, preserves the original status code and response headers.
- **Business**: Handles `BusinessException`, passing along headers, and logs at the `WARNING` level.
- **Unexpected**: Fallback `Exception` handler that securely returns 500 without leaking stack traces and logs at the `ERROR` level.

### 6. Application Registration
- Registered the global exception handlers in `app/main.py` via the `register_exception_handlers` function.

## Verification

### Automated Tests
- Developed comprehensive test coverage in `tests/test_exceptions.py`.
- Confirmed that all error responses follow the standard response contract (e.g., `"errors": []` when empty).
- Validated correct headers and response bodies across validation, HTTP, business, and unexpected errors.
- Tests pass cleanly when run via `uv run pytest tests/`.

### Linting and Formatting
- Ran `uv run ruff check --fix .` and `uv run ruff format .` to ensure code aligns with the project's formatting standards.

The implementation successfully fulfills the BF-009 requirements and establishes a solid architectural foundation for future error handling across modules.
