# Sprint 1 | BF-014 | Request Tracing Middleware

## Walkthrough

### Changes Implemented

1. **Context Management Refactoring (`context.py`)**:
   - Renamed `request_id_ctx_var` to `correlation_id_ctx_var`.
   - Updated getter and setter functions from `request_id` to `correlation_id`.

2. **Logging Structure Updates (`logging.py`)**:
   - Updated the `JSONFormatter` to map `"correlation_id"` to the extracted context variable instead of `"request_id"`.

3. **Request Tracing Middleware (`logging_middleware.py`)**:
   - Switched header extraction and response injection to use `X-Correlation-ID`.
   - Populated `correlation_id` in both `request.state` and context variables.
   - Captured `request.client.host` and stored it as `client_ip` for the log extra dictionary.
   - Renamed the calculated execution duration variable to `execution_time` and logged it in ms.

4. **Testing Enhancements (`test_logging_middleware.py`, `test_logging.py`)**:
   - Extracted middleware-specific request ID logic from `test_logging.py`.
   - Created comprehensive tests validating:
     - `X-Correlation-ID` generation.
     - `X-Correlation-ID` header propagation.
     - Execution time inclusion in logging records.
     - Client IP logging accuracy.
     - Execution across multiple endpoints simultaneously.

5. **Documentation Refactoring**:
   - Replaced all explicit references to "Request ID" with "Correlation ID" in:
     - `docs/AI/02_ARCHITECTURE.md`
     - `docs/AI/05_API_GUIDELINES.md`
     - `docs/AI/08_CODING_STANDARDS.md`

### Testing Performed

- Ran the isolated middleware test suite: `pytest backend/tests/middleware/test_logging_middleware.py -v` (100% Passed).
- Executed the entire application test suite to ensure backwards compatibility and proper cleanup of tests: `pytest backend/tests -v` (64 Passed).
- Successfully validated linting and formatting via Ruff.

### Validation Results

All HTTP requests will now consistently feature correlation IDs that are correctly propagated via headers and injected into structured logs alongside accurate request duration and client IP metadata. No sensitive internal or authentication data is logged, complying precisely with security rules.
