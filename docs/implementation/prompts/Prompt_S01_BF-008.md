# Sprint 1 | BF-008 | Structured Logging

## Story

As a developer,
I want structured logging
So that application behavior is easy to monitor and troubleshoot.

---

## Objective

Implement a centralized, production-ready structured logging framework for the FastAPI backend.

This story establishes the application's logging foundation only.

Do not implement distributed tracing, metrics collection, OpenTelemetry, external log aggregation, audit logging, or authentication-aware logging beyond supporting an optional user identifier when available.

Remain strictly within the scope of structured application logging.

---

## Expected Outcome

The application consistently logs:

- Application startup
- Application shutdown
- Incoming HTTP requests
- Completed HTTP responses
- Unhandled exceptions
- Health endpoint execution
- Database readiness failures
- Request duration

Logs must be structured and machine-readable.

---

## Requirements

### 1. Centralized Logging Module

Create a reusable logging module under the existing core/shared infrastructure.

Responsibilities:

- Configure application logger
- Configure formatter
- Configure handlers
- Prevent duplicate handlers
- Expose helper for retrieving loggers

No feature module should configure logging independently.

---

### 2. Structured JSON Logging

Every log entry must include at minimum:

- timestamp
- level
- logger
- module
- message
- request_id
- user_id (nullable)
- http_method (when applicable)
- request_path (when applicable)
- status_code (when applicable)
- duration_ms (when applicable)

The format must remain consistent across the application.

---

### 3. Request ID Support

Implement request ID propagation.

Requirements:

- Read X-Request-ID if provided.
- Generate UUID when missing.
- Store request ID in request state.
- Include request ID in every request log.
- Return X-Request-ID response header.

---

### 4. Logging Middleware

Create middleware responsible for:

Before request:

- request started

After request:

- request completed
- status code
- duration

Unhandled exceptions:

- error log
- stack trace in server logs only

The middleware should never modify API response formats.

---

### 5. Startup Logging

Existing lifespan events should use the centralized logger.

Log examples include:

- application starting
- configuration loaded
- database initialized
- application ready
- graceful shutdown started
- graceful shutdown completed

Remove any ad hoc logging already present.

---

### 6. Exception Logging

Unexpected exceptions should produce structured ERROR logs.

Do not expose:

- stack traces
- internal implementation
- secrets

Clients continue receiving existing error responses.

---

### 7. Sensitive Data Protection

Never log:

- Authorization header
- JWT
- passwords
- refresh tokens
- secrets
- database credentials
- environment values
- personal information

Mask or omit sensitive values.

---

### 8. Log Levels

Use appropriate levels.

DEBUG

Development diagnostics only.

INFO

Startup
Shutdown
Requests
Health checks

WARNING

Recoverable failures.

ERROR

Unhandled exceptions
Database failures
Unexpected application errors

CRITICAL

Application cannot continue.

---

### 9. Configuration

Support log level through application configuration.

Development:

Default INFO

Future environments must be configurable without code changes.

---

### 10. Health Endpoints

Existing BF-007 endpoints should automatically participate through middleware.

No duplicate logging inside endpoint handlers.

---

### 11. Testing

Add automated tests covering:

- request ID generation
- request ID propagation
- X-Request-ID response header
- middleware execution
- startup logging initialization
- structured log fields
- exception logging
- no duplicate handlers

Existing tests must continue passing.

---

### 12. Documentation

Update:

- README if logging configuration is documented
- Walkthrough
- Any developer documentation affected by logging

Do not modify architecture documents.

---

## Out of Scope

Do NOT implement:

- OpenTelemetry
- Grafana
- Prometheus
- Loki
- Elastic Stack
- CloudWatch
- Audit logging
- Authentication logging
- Business event logging
- Correlation across services
- Metrics collection

Those belong to future stories.

---

## Deliverables

Provide:

1. Implementation summary
2. Files added
3. Files modified
4. Test results
5. Architectural decisions
6. Documentation updates
7. Confirmation that:

- structured logging is centralized
- middleware is active
- request IDs work
- sensitive data is excluded
- no duplicate logging exists
- all acceptance criteria are satisfied
