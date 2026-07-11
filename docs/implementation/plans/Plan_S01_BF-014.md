# Sprint 1 | BF-014 | Request Tracing Middleware

This plan details the implementation of centralized HTTP middleware for request logging, correlation IDs, and execution timing. The implementation builds upon the structured logging foundation from BF-008.

## Proposed Changes

### Core Context & Logging
- **[MODIFY] [context.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/core/context.py)**:
  - Rename `request_id_ctx_var` to `correlation_id_ctx_var`.
  - Rename `get_request_id` and `set_request_id` to `get_correlation_id` and `set_correlation_id`.
- **[MODIFY] [logging.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/core/logging.py)**:
  - Update `JSONFormatter.format()` to output `correlation_id` instead of `request_id`.

### Middleware
- **[MODIFY] [logging_middleware.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/app/middleware/logging_middleware.py)**:
  - Extract `X-Correlation-ID` from incoming headers (generate UUID4 if absent).
  - Store correlation ID in both `request.state.correlation_id` and the context variables.
  - Extract `client_ip` from `request.client.host`.
  - Include `correlation_id`, `client_ip`, and `execution_time` in structured logs (rename the previous `duration_ms` local variable to log `execution_time` for exact matching with requirements).
  - Return the `X-Correlation-ID` in the HTTP response headers.

### Testing
- **[NEW] [test_logging_middleware.py](file:///Users/dumbo/Documents/MyCommunity/product/app/backend/tests/middleware/test_logging_middleware.py)**:
  - Add tests validating correlation ID extraction and generation.
  - Add tests verifying response header injection.
  - Add tests ensuring execution time and client IP are logged correctly.

### Documentation Updates
- **[MODIFY] [02_ARCHITECTURE.md](file:///Users/dumbo/Documents/MyCommunity/product/app/docs/AI/02_ARCHITECTURE.md)**: Replace "Request ID" references with "Correlation ID".
- **[MODIFY] [05_API_GUIDELINES.md](file:///Users/dumbo/Documents/MyCommunity/product/app/docs/AI/05_API_GUIDELINES.md)**: Replace "Request ID" references with "Correlation ID".
- **[MODIFY] [08_CODING_STANDARDS.md](file:///Users/dumbo/Documents/MyCommunity/product/app/docs/AI/08_CODING_STANDARDS.md)**: Replace "Request ID" references with "Correlation ID".

## Verification Plan

### Automated Tests
- Run `pytest backend/tests/middleware/test_logging_middleware.py -v`.
- Ensure all other existing backend tests pass: `pytest backend/tests -v`.

### Linter & Formatter
- Run `ruff check backend` and `ruff format --check backend`.

### Manual Verification
- N/A - automated tests provide full coverage of the middleware requirements.
