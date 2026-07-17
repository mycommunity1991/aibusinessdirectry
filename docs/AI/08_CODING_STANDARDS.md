# AI Marketplace Coding Standards

**Document ID:** AI-08  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the coding standards for the AI Marketplace platform.

Its objective is to ensure that every line of code is:

- Consistent
- Readable
- Maintainable
- Secure
- Testable
- Scalable

These standards apply equally to human developers and AI-generated code.

---

# Engineering Philosophy

Code is written once but maintained for years.

Always optimize for:

- Readability
- Maintainability
- Simplicity
- Correctness

Never optimize for writing fewer lines of code.

Readable code is preferred over clever code.

---

# General Principles

Every implementation should follow these principles:

- Single Responsibility Principle
- Separation of Concerns
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple)
- Composition over Inheritance
- Explicit over Implicit
- Fail Fast
- Least Surprise

---

# Project Structure

Every project follows the defined architecture.

Never create new folders unless approved.

Never duplicate an existing module.

Shared functionality belongs in shared modules.

---

# File Naming

Use:

```
snake_case
```

Examples

```
user_service.py

community_repository.py

create_post_screen.dart

notification_provider.dart
```

Avoid

```
UserService.py

createPost.dart

temp.dart
```

---

# Folder Naming

Always use

```
snake_case
```

Example

```
user

provider

search_request

notifications
```

---

# Class Naming

Use

```
PascalCase
```

Example

```
UserService

CommunityRepository

NotificationManager
```

---

# Method Naming

Use

```
camelCase
```

Flutter

```
loadPosts()

createCommunity()

sendNotification()
```

Python

```
load_posts()

create_community()

send_notification()
```

Methods should describe actions.

---

# Variable Naming

Variables should clearly describe their purpose.

Good

```
communityMembers

currentUser

notificationCount
```

Avoid

```
data

obj

temp

value

test
```

---

# Constant Naming

Use

```
UPPER_SNAKE_CASE
```

Example

```
MAX_LOGIN_ATTEMPTS

DEFAULT_PAGE_SIZE

JWT_EXPIRATION
```

---

# Function Design

Functions should:

- Perform one task
- Be small
- Be readable
- Avoid side effects

Preferred size

```
20-40 lines
```

Large functions should be refactored.

---

# Class Design

Classes should:

- Have one responsibility
- Be cohesive
- Minimize dependencies
- Be easy to test

Avoid "God Classes."

---

# Comments

Code should explain itself.

Comments explain:

- Why
- Business rules
- Complex algorithms

Comments should never explain obvious code.

Good

```python
# Freelancers must pass verification before their listing can go live.
```

Bad

```python
# Increment i
i += 1
```

---

# Documentation

Every public class and function should include documentation.

Python

```python
"""
Creates a new search request.

Args:
    request: Search request creation payload.

Returns:
    Search request response.
"""
```

Flutter

Use Dart documentation comments.

```dart
/// Returns the current user's profile.
```

---

# Error Handling

Handle expected errors.

Unexpected errors should:

- Be logged
- Return safe messages
- Never expose implementation details

Never swallow exceptions.

Avoid

```python
except:
    pass
```

---

# Logging

Use structured logging.

Never use

```
print()
```

Production logging should include:

- Correlation ID
- User ID
- Module
- Severity

Never log:

- Passwords
- Tokens
- Secrets
- Personal information

---

# Dependency Management

Every dependency must:

- Solve a real problem
- Be actively maintained
- Have a clear purpose

Avoid unnecessary packages.

---

# Flutter Standards

Architecture

Feature First

State Management

Riverpod

Navigation

GoRouter

Networking

Dio

Local Storage

Flutter Secure Storage

---

## Flutter Widgets

Widgets should:

- Be reusable
- Be stateless whenever possible
- Avoid business logic
- Receive dependencies through constructors

Avoid deeply nested widgets.

---

## Flutter State

Business logic belongs inside:

- Providers
- Controllers
- Services

Never inside Widgets.

---

## Flutter UI

Do not hardcode:

- Colors
- Strings
- Padding
- Radius
- Font sizes

Use centralized design tokens.

---

# Python Standards

Framework

FastAPI

ORM

SQLAlchemy

Validation

Pydantic

Package Management

uv

---

## Python Structure

```
Router

↓

Service

↓

Repository

↓

Database
```

Routers never contain business logic.

Repositories never contain business rules.

---

# Database Access

Only repositories communicate directly with the database.

Never execute SQL inside:

- API Routes
- Services
- Controllers

---

# API Standards

Every endpoint must:

- Validate input
- Validate authorization
- Return consistent responses
- Use correct HTTP status codes

---

# Security Standards

Never:

- Hardcode secrets
- Commit credentials
- Disable authentication
- Skip authorization
- Trust client input

Always:

- Validate input
- Sanitize output
- Use parameterized queries

---

# Performance Standards

Avoid:

- N+1 queries
- Blocking operations
- Unnecessary API calls
- Duplicate calculations

Prefer:

- Pagination
- Lazy loading
- Caching
- Efficient indexing

---

# Git Standards

Branch names

```
feature/user-profile

bugfix/login

hotfix/token-expiry

release/v1.0.0
```

Commit format

```
feat:

fix:

docs:

refactor:

test:

chore:

style:

perf:

ci:
```

Examples

```
feat: add freelancer verification

fix: resolve token refresh issue

docs: update API guidelines
```

---

# Formatting

Formatting is enforced automatically.

Never manually format code differently.

Python

Black

Flutter

dart format

Imports should remain organized.

---

# Testing Standards

Business logic requires unit tests.

Critical workflows require integration tests.

Bug fixes require regression tests.

Code without tests should not be merged if it affects critical business functionality.

---

# Code Review Checklist

Every Pull Request should verify:

- Compiles successfully
- Lint passes
- Tests pass
- Documentation updated
- No duplicated logic
- No security issues
- No hardcoded values
- No dead code

---

# Prohibited Practices

Never:

- Copy and paste code unnecessarily
- Create duplicate models
- Create duplicate services
- Use global mutable state
- Ignore exceptions
- Leave commented-out code
- Commit temporary debugging code
- Commit TODOs to production
- Use magic numbers
- Hardcode configuration

---

# AI Coding Rules

AI-generated code must:

- Follow project architecture
- Reuse existing modules
- Follow naming conventions
- Follow security standards
- Follow UI guidelines
- Produce production-ready code
- Avoid placeholders
- Avoid incomplete implementations
- Avoid unnecessary abstractions
- Explain architectural decisions only when requested

AI must never generate code that violates this document.

---

# Definition of Done

Code is complete only when:

- Requirements are implemented
- Code compiles
- Lint passes
- Tests pass
- Documentation updated
- Security reviewed
- No known critical issues
- Ready for production deployment

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 04_DATABASE.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 07_UI_GUIDELINES.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**