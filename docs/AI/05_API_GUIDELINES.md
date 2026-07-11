# MyCommunity API Guidelines

**Document ID:** AI-05  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Backend Engineers, Mobile Engineers, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the API design standards for MyCommunity.

All APIs must follow these guidelines to ensure consistency, maintainability, security, and scalability.

Every public API exposed by the platform must comply with this document.

---

# API Architecture

Architecture Style

- RESTful API
- Resource-Oriented Design
- Stateless Communication
- JSON Request/Response
- HTTPS Only

Current Version

```
/api/v1
```

Future versions

```
/api/v2
```

Versioning is mandatory.

---

# Base URL

Development

```
http://localhost:8000/api/v1
```

Staging

```
https://staging-api.mycommunity.com/api/v1
```

Production

```
https://api.mycommunity.com/api/v1
```

---

# Resource Naming

Use nouns.

Good

```
/users

/communities

/posts

/comments

/events

/listings

/notifications
```

Avoid verbs.

Bad

```
/createUser

/getPosts

/deleteComment
```

---

# HTTP Methods

| Method | Purpose |
|----------|----------|
| GET | Retrieve resource |
| POST | Create resource |
| PUT | Replace resource |
| PATCH | Partial update |
| DELETE | Remove resource |

---

# URL Design

Good

```
GET /communities

GET /communities/{id}

GET /communities/{id}/members

POST /communities

PATCH /communities/{id}

DELETE /communities/{id}
```

Avoid deeply nested resources.

Maximum nesting

```
/communities/{id}/posts
```

Avoid

```
/communities/{id}/posts/{id}/comments/{id}/reactions
```

---

# Request Headers

Standard headers

```
Authorization

Content-Type

Accept

X-Request-ID

Accept-Language
```

---

# Authentication

Protected endpoints require

```
Authorization: Bearer <JWT Token>
```

Anonymous access is allowed only where explicitly documented.

---

# Request Body

JSON only.

Example

```json
{
  "title": "Community Cleanup",
  "description": "Weekend cleanup event.",
  "start_date": "2026-07-10T10:00:00Z"
}
```

---

# Standard Success Response

```json
{
  "success": true,
  "message": "Request completed successfully.",
  "data": {}
}
```

---

# Collection Response

```json
{
  "success": true,
  "message": "Data retrieved successfully.",
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 125,
    "total_pages": 7
  }
}
```

---

# Error Response

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

---

# HTTP Status Codes

| Code | Meaning |
|------|----------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

---

# Pagination

All collection endpoints must support pagination.

Query Parameters

```
?page=1

?page_size=20
```

Maximum page size

```
100
```

Default

```
20
```

---

# Sorting

Supported

```
?sort=name

?sort=-created_at

?sort=price
```

"-" indicates descending order.

---

# Filtering

Example

```
?status=active

?community_id=123

?category=sports

?verified=true
```

Multiple filters

```
?status=active&verified=true
```

---

# Search

Standard parameter

```
?q=football
```

Avoid endpoint-specific search parameters.

---

# Field Selection

Supported

```
?fields=id,name,email
```

Useful for mobile optimization.

---

# Resource Expansion

Supported

```
?expand=community

?expand=author

?expand=images
```

Nested expansion should be limited.

---

# Idempotency

Required for critical POST operations.

Header

```
Idempotency-Key
```

Examples

- Payments
- Membership Requests
- Invitations

---

# Validation

Validation occurs in four layers

1. Flutter
2. FastAPI Request Validation
3. Service Layer
4. Database Constraints

Never trust client input.

---

# API Documentation

Every endpoint must include

- Purpose
- Authentication
- Request
- Response
- Error Codes
- Examples

OpenAPI documentation must remain synchronized with implementation.

---

# Security

Every endpoint must

- Validate input
- Validate authorization
- Prevent SQL Injection
- Prevent Mass Assignment
- Sanitize output
- Log security events

Never expose

- Stack traces
- Internal IDs
- Database errors
- Server paths

---

# File Upload

Uploads use

```
multipart/form-data
```

Supported file types are validated.

Maximum file size is configurable.

Virus scanning may be introduced in future releases.

---

# Rate Limiting

Rate limiting is enforced using Redis.

Examples

Authentication

```
10 requests/minute
```

Public APIs

```
100 requests/minute
```

Authenticated APIs

```
1000 requests/hour
```

Limits are configurable.

---

# API Deprecation

Deprecated endpoints

- Must remain functional for one major version.
- Must return deprecation headers.
- Must be documented.

Breaking changes require a new API version.

---

# Logging

Every request logs

- Correlation ID
- User ID
- Endpoint
- Method
- Status Code
- Execution Time
- Client IP

Sensitive information must never be logged.

---

# Performance

API responses should

- Be paginated
- Avoid unnecessary nesting
- Return only required fields
- Minimize payload size
- Use efficient queries

Compression should be enabled in production.

---

# Naming Conventions

JSON properties use

```
snake_case
```

Examples

```
first_name

phone_number

created_at

community_id
```

Consistency is mandatory.

---

# Endpoint Organization

```
/auth

/users

/communities

/posts

/comments

/events

/listings

/notifications

/reports

/admin
```

Each module owns its endpoints.

---

# API Evolution

Rules

- Additive changes are preferred.
- Breaking changes require versioning.
- Maintain backward compatibility whenever possible.

---

# API Principles

Every API should be

- Predictable
- Consistent
- Secure
- Fast
- Well documented
- Backward compatible
- Easy to consume

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 04_DATABASE.md
- 06_SECURITY.md
- 07_UI_GUIDELINES.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**