# Sprint 1 | BF-010 | Standardized API Response Models

## Story

**As a developer, I want reusable standardized API response models so that every API endpoint returns a consistent response contract for success, collections, pagination, and errors.**

---

# Objective

Implement reusable API response models that become the single source of truth for all HTTP responses across the backend.

This story establishes the common response contracts that every current and future API endpoint will use.

The implementation must remain independent and must not introduce any business functionality.

This story builds on the global exception handling implemented in BF-009 by providing reusable response schemas consumed by endpoints and exception handlers.

---

# References

Before implementation, review:

- AGENT.md
- docs/AI/*
- AI-02 Architecture
- AI-05 API Guidelines
- AI-06 Security
- AI-08 Coding Standards

Follow all existing project conventions.

Do not redesign existing architecture.

---

# Scope

Implement only reusable response models.

Do not implement authentication, business modules, middleware, or endpoint-specific functionality.

---

# Implementation Tasks

## 1. Create Shared Response Models

Create reusable response schemas under the shared layer.

Suggested location:

```text
backend/
└── app/
    └── shared/
        └── schemas/
            └── response.py
```

Implement reusable generic response models using **Pydantic v2 generics**.

Suggested models:

- BaseResponse[T]
- SuccessResponse[T]
- CollectionResponse[T]
- PaginationMeta
- ErrorResponse
- ErrorDetail

Avoid endpoint-specific response models.

Future APIs should reuse these models without modification.

---

## 2. Base Success Response

Implement the standard success response defined by the project API Guidelines.

Example:

```json
{
    "success": true,
    "message": "Request completed successfully.",
    "data": {}
}
```

Requirements:

- `success` always equals `true`
- `message` is required
- `data` is generic
- Works with any response DTO

---

## 3. Collection Response

Implement a reusable collection response supporting pagination.

Example:

```json
{
    "success": true,
    "message": "Data retrieved successfully.",
    "data": [],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_items": 120,
        "total_pages": 6
    }
}
```

Create a reusable `PaginationMeta` model.

Future collection endpoints must reuse this model.

---

## 4. Error Response

Implement reusable error response models compatible with BF-009.

Example:

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": [
        {
            "field": "email",
            "message": "Email address is invalid."
        }
    ]
}
```

Requirements:

- Compatible with existing exception handlers
- No duplicate exception logic
- Safe for all API errors
- No internal implementation details exposed

---

## 5. Update Existing Endpoints

Update the existing foundation endpoints to use the new response models.

Update only:

- Health
- Readiness
- Liveness

Do not modify:

- Routes
- Business logic
- Status codes
- Endpoint behavior

Only standardize their response models.

---

## 6. OpenAPI Integration

Update FastAPI route definitions to expose the standardized response models.

Requirements:

- Consistent Swagger documentation
- Reusable schemas
- No duplicate schema generation
- Generic responses correctly documented

---

## 7. Testing

Add unit tests covering:

- Success response serialization
- Generic response support
- Collection response serialization
- Pagination model
- Error response serialization
- JSON output

Existing tests must continue passing.

---

## 8. Documentation

Update project documentation where necessary.

Document:

- Response model hierarchy
- Usage examples
- How future endpoints should consume the shared models

---

# Out of Scope

Do not implement:

- Authentication
- Authorization
- Business modules
- DTO refactoring
- Exception handler redesign
- Middleware changes
- New API endpoints
- API version changes

---

# Acceptance Criteria

- Reusable generic response models are implemented.
- Success responses follow the common schema.
- Collection responses support reusable pagination metadata.
- Error responses remain compatible with BF-009.
- Existing health endpoints use standardized response models.
- OpenAPI documentation reflects the new schemas.
- Unit tests validate serialization and generic behavior.
- No business functionality is introduced.
- No duplicated response models exist.
- Code follows project architecture and coding standards.

---

# Expected Deliverables

- Shared response model module
- Generic success response model
- Generic collection response model
- Pagination metadata model
- Error response model
- Updated health endpoints
- Updated OpenAPI documentation
- Unit tests
- Updated documentation

---

# Definition of Done

- Acceptance criteria satisfied
- Ruff passes
- Formatting passes
- Tests pass
- Documentation updated
- No architectural violations
- No duplicated response models
- Production ready

---

# Review Checklist

## Acceptance Criteria

- [ ] Generic response models implemented
- [ ] Success response matches project API guidelines
- [ ] Collection response includes reusable pagination metadata
- [ ] Error response compatible with BF-009
- [ ] Health endpoints migrated
- [ ] Swagger/OpenAPI updated

## Architecture Compliance

- [ ] Models placed in shared layer
- [ ] Uses Pydantic v2 generics
- [ ] No duplicate response models
- [ ] No business logic introduced
- [ ] Follows Modular Monolith architecture

## Code Quality

- [ ] Strong typing
- [ ] Small reusable models
- [ ] Unit tests added
- [ ] Documentation updated
- [ ] Ruff passes
- [ ] Formatting passes

## Scope Compliance

- [ ] No authentication changes
- [ ] No middleware changes
- [ ] No business modules introduced
- [ ] No exception handling redesign
- [ ] Story remains independent
