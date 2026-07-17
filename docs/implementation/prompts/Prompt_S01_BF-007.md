# Sprint 1 | BF-007 | Health Check Endpoints

## Story

**As a developer,**  
I want health check endpoints  
**So that** I can verify application and database availability.

---

# AG Developer Prompt

## Story

**As a developer,**  
I want health check endpoints  
**So that** I can verify application and database availability.

---

## Objective

Implement production-ready health check endpoints that allow developers, infrastructure, container orchestration platforms, load balancers, and monitoring tools to verify application availability and database connectivity.

This story establishes the application's health endpoint foundation. The implementation should remain lightweight, reliable, and easily extensible for future infrastructure integrations.

---

# Scope

Implement the following REST endpoints.

## 1. Application Health Endpoint

```
GET /api/v1/health
```

### Purpose

Verify that the API application is running and able to serve requests.

This endpoint should **not** perform any database access.

### Success Response

**HTTP 200**

```json
{
  "status": "healthy",
  "service": "ai-marketplace-api",
  "version": "1.0.0"
}
```

---

## 2. Database Health Endpoint

```
GET /api/v1/health/db
```

### Purpose

Verify PostgreSQL connectivity using a lightweight database query.

This endpoint validates that:

- Database server is reachable
- Connection pool is operational
- SQLAlchemy session works correctly

### Database Query

Use the lightest possible query.

```sql
SELECT 1;
```

Prefer SQLAlchemy's:

```python
text("SELECT 1")
```

instead of ORM operations.

---

### Healthy Response

**HTTP 200**

```json
{
    "status": "healthy",
    "database": "connected"
}
```

---

### Failure Response

**HTTP 503 Service Unavailable**

```json
{
    "status": "unhealthy",
    "database": "disconnected"
}
```

Do not expose internal exception messages to the client.

---

# Implementation Requirements

## API Router

Create a dedicated Health router.

Suggested structure

```
app/
 ├── api/
 │    └── v1/
 │         └── health.py
```

Register the router using the existing API Versioning implementation from BF-006.

---

## Service Layer

Business logic must not reside inside the API route.

Create

```
app/services/health_service.py
```

Responsibilities:

- Build health responses
- Perform database connectivity verification
- Handle database exceptions
- Return strongly typed response models

Routes should simply call the service.

---

## Database Access

Reuse the existing infrastructure implemented in previous stories.

Do not:

- create a new engine
- create another SessionLocal
- duplicate dependency injection

Reuse the centralized database session.

Ensure sessions are always released properly.

---

## Response Models

Create response schemas.

Suggested location

```
app/schemas/health.py
```

Example models

```python
HealthResponse

DatabaseHealthResponse
```

Use Pydantic models consistent with the project standards.

---

## Configuration

Do not hardcode:

- application name
- version
- environment

Read these values from the centralized configuration created in BF-002.

Example

```
settings.APP_NAME

settings.APP_VERSION
```

---

## Constants

Avoid hardcoded strings.

Move reusable values into constants where appropriate.

Examples

```
healthy

unhealthy

connected

disconnected
```

---

## Logging

Healthy requests should not generate logs.

Only log failures.

Database connection failures should include stack traces using the project's logging strategy.

---

## Exception Handling

Reuse the centralized exception handling already implemented.

Do not introduce custom exception middleware.

---

## OpenAPI Documentation

Document both endpoints completely.

Include:

- summary
- description
- tags
- response models
- HTTP status codes

Swagger should clearly display both endpoints.

---

# Testing

Create automated tests.

## Application Health

Verify

- HTTP 200
- response schema
- expected payload

---

## Database Health

Verify

Healthy

- HTTP 200
- database connected response

Failure

- mock database exception
- HTTP 503
- expected response payload

---

Use the project's existing testing framework.

---

# Acceptance Criteria

- Health endpoint implemented
- Database health endpoint implemented
- Lightweight SQL query used
- Service layer implemented
- Response models created
- API Versioning respected
- Swagger documentation generated
- Unit tests added
- Existing architecture unchanged

---

# Out of Scope

Do not implement

- Prometheus
- Grafana
- OpenTelemetry
- Metrics endpoint
- Kubernetes readiness probe
- Kubernetes liveness probe
- CPU monitoring
- Memory monitoring
- Disk monitoring
- Redis health
- External service health
- Dependency aggregation
- Background monitoring

---

# Recommendations

These recommendations are within the scope of this story and should be implemented if they do not introduce unnecessary complexity.

## Recommendation 1

Use SQLAlchemy's

```python
text("SELECT 1")
```

instead of ORM operations for the database health check.

Reason:

- fastest execution
- lowest overhead
- database independent

---

## Recommendation 2

Return responses using Pydantic models instead of dictionaries.

Benefits

- consistent API
- automatic validation
- cleaner OpenAPI documentation

---

## Recommendation 3

Read application metadata from centralized configuration.

Example

```
APP_NAME
APP_VERSION
```

This prevents future code changes during releases.

---

## Recommendation 4

Implement the service in a way that allows future dependency health checks to be added without modifying the API routes.

Example future additions

- Redis
- Object Storage
- Email Service
- Search Engine

The router should remain unchanged.

---

## Recommendation 5

Keep response schemas stable.

Avoid changing field names later.

Recommended format

```json
{
    "status": "healthy"
}
```

instead of

```json
{
    "message": "Everything is working"
}
```

Stable responses simplify infrastructure integrations.

---

## Recommendation 6

Return HTTP 503 for database failures instead of HTTP 500.

Most monitoring systems and load balancers interpret HTTP 503 correctly as a temporary service availability issue.

---

## Recommendation 7

Ensure no sensitive information is returned to clients.

Never expose

- SQL errors
- stack traces
- connection strings
- database names
- credentials

These should only appear in server logs.

---

## Recommendation 8

Keep the endpoint response time under 100 ms under normal conditions.

Health endpoints are called frequently by

- Docker
- Kubernetes
- Load balancers
- Monitoring systems

---

## Recommendation 9

Tag the endpoints under

```
Health
```

within Swagger to keep API documentation organized.

---

## Recommendation 10

Use dependency injection consistently with the rest of the project rather than creating database sessions manually.
