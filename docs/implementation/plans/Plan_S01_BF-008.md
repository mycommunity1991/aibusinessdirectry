# BF-008 Structured Logging - Implementation Plan

## Goal Description
Implement a centralized, production-ready structured logging framework for the FastAPI backend. This involves setting up a custom JSON logger, a request-context mechanism to propagate `request_id`, and a logging middleware to trace HTTP requests. 

## Proposed Changes

### `backend/app/core/`

#### [NEW] `context.py`
- Create `contextvars` for `request_id` and `user_id` to allow propagation of context across async tasks without passing them explicitly in every function call.

#### [MODIFY] `logging.py`
- Replace the dummy file with the centralized logging configuration.
- Implement a `JSONFormatter` that extends `logging.Formatter`.
- Extract `request_id` and `user_id` from the context variables to include them in the log record.
- Include logic to mask sensitive data (e.g., passwords, tokens) if they accidentally appear in log messages.
- Provide a `setup_logging` function to initialize handlers, clear duplicate handlers, and set the default log level from `settings.LOG_LEVEL`.

#### [MODIFY] `lifespan.py`
- Call `setup_logging()` inside the lifespan.
- Modify existing `logger.info` calls to align with structured logging expectations (e.g. "application starting", "configuration loaded").

### `backend/app/middleware/`

#### [NEW] `logging_middleware.py`
- Implement a Starlette `BaseHTTPMiddleware` (or pure ASGI middleware) to handle:
  - Reading `X-Request-ID` from headers, or generating a `uuid4()`.
  - Setting `request_id` in context.
  - Logging "request started" before calling `call_next`.
  - Measuring request duration (`duration_ms`).
  - Logging "request completed" with status code.
  - Adding `X-Request-ID` to the response headers.

### `backend/app/api/`

#### [NEW] `exceptions.py`
- Add a global exception handler for unhandled `Exception` to log the stack trace using the structured logger before returning the 500 error response. This ensures the stack trace is captured correctly.

### `backend/app/`

#### [MODIFY] `main.py`
- Register the `LoggingMiddleware`.
- Register the unhandled exception handler.

### `backend/tests/`

#### [NEW] `test_logging.py`
- Add tests covering `X-Request-ID` generation/propagation.
- Test structured JSON formatting.
- Test exception logging.
- Ensure sensitive data masking works.

## Verification Plan

### Automated Tests
- Run `pytest backend/tests/test_logging.py` to verify the middleware and structured formatting.
- Run `pytest` on the entire suite to ensure existing tests still pass.

### Manual Verification
- Start the server (`uvicorn app.main:app --reload`).
- Send a `GET /health` request to verify the logs printed to the console are in proper JSON format, containing all the requested fields (`timestamp`, `level`, `request_id`, `duration_ms`, etc.).
- Send a request with `X-Request-ID` to verify it gets returned and logged.
- Trigger an unhandled exception to ensure the stack trace is printed to the server logs as a structured JSON error, and the client receives a normal 500 response.
