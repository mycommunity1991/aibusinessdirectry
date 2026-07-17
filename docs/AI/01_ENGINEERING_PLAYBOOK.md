# AI Marketplace Engineering Playbook

Version: 2.0
Owner: CTO
Status: Active

---

# 1. Project Vision

AI Marketplace is a UAE-first, country-agnostic-by-design directory and AI-mediated contact marketplace connecting businesses and freelancers with nearby customers.

Primary goals:

- Utility, not feed — search, match, contact
- AI intake grounded in real platform data, never invented
- Mobile first (native Flutter app)
- High performance
- Enterprise-grade architecture
- Production-ready code from Day 1

---

# 2. Repository Structure

mobile/
Flutter application

backend/
FastAPI backend

infrastructure/
Infrastructure configuration

scripts/
Automation scripts

tools/
Developer tools

docs/
Technical documentation

.github/
GitHub workflows

---

# 3. Architecture

Architecture Style

Modular Monolith

Future

Extractable to Microservices

Never tightly couple modules.

Every module communicates through services/interfaces.

---

# 4. Backend

Language

Python

Framework

FastAPI

ORM

SQLAlchemy 2.x

Migration

Alembic

Validation

Pydantic v2

Package Manager

uv

Database

PostgreSQL

Cache

Redis

Authentication

JWT

OAuth

Refresh Tokens

---

# 5. Mobile

Flutter Stable

Architecture

Feature First

Clean Architecture

State Management

Riverpod

Routing

GoRouter

Networking

Dio

Storage

Flutter Secure Storage

Localization

English

Arabic

Theme

Material 3

---

# 6. Code Principles

Always

Readable

Maintainable

Testable

Modular

Never

Large classes

Business logic inside UI

SQL inside routes

Duplicate code

Hardcoded strings

Magic numbers

---

# 7. Naming

Folders

snake_case

Python

snake_case

Flutter

PascalCase

Files

snake_case

Constants

UPPER_SNAKE_CASE

---

# 8. API Rules

REST

Versioned

/api/v1

Always return

Success

Message

Data

Errors

Never expose stack traces

---

# 9. Security

Validate every input

Parameterized SQL

JWT

HTTPS

Encrypt secrets

No credentials in code

Environment variables only

---

# 10. Git

Branch

main

Feature

feature/<name>

Bug

bugfix/<name>

Release

release/<version>

Hotfix

hotfix/<name>

Commit Style

feat:

fix:

refactor:

docs:

test:

chore:

---

# 11. Testing

Backend

pytest

Flutter

flutter_test

Critical business logic must have tests.

---

# 12. Logging

Structured logging

Never print()

Use logging library

---

# 13. Performance

Pagination

Lazy Loading

Caching

Indexes

Avoid N+1 queries

---

# 14. Documentation

Every module must include

README

Architecture

Dependencies

Public APIs

---

# 15. AI Coding Rules

Before generating code

Understand existing architecture

Never create duplicate models

Never create duplicate APIs

Reuse components

Follow project folder structure

Keep functions small

Prefer composition over inheritance

Always explain architectural decisions

Never introduce breaking changes without justification.

---

# 16. Definition of Done

Code Compiles

Lint Passes

Tests Pass

Documentation Updated

Reviewed

No TODOs

No Dead Code

Ready for Production

---

END