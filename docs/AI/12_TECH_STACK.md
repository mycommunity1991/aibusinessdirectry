# AI Marketplace Technology Stack

**Document ID:** AI-12  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the official technology stack for the AI Marketplace platform.

All development must use the technologies specified in this document.

Technology changes require CTO approval and must be recorded in `09_DECISIONS.md`.

---

# Engineering Principles

Technology choices are guided by the following principles:

- Production readiness
- Long-term maintainability
- Strong community support
- Scalability
- Excellent developer experience
- Security
- Performance
- AI-assisted development compatibility

---

# Architecture

Application Architecture

- Modular Monolith

Design Principles

- Feature-First Architecture
- Clean Architecture
- Separation of Concerns
- Domain-Driven Module Organization

Future Architecture

- Extractable Microservices

---

# Mobile Application

Framework

- Flutter (Stable Channel)

Language

- Dart

State Management

- Riverpod

Navigation

- GoRouter

Networking

- Dio

Design System

- Material Design 3

Local Storage

- Flutter Secure Storage
- SharedPreferences (non-sensitive settings only)

Serialization

- json_serializable

Code Generation

- build_runner

Image Handling

- Cached Network Image

Localization

- Flutter Localization (English & Arabic)

Testing

- flutter_test
- integration_test

---

# Backend

Language

- Python 3.14+

Framework

- FastAPI

ASGI Server

- Uvicorn

Data Validation

- Pydantic v2

ORM

- SQLAlchemy 2.x

Database Migration

- Alembic

Package Management

- uv

Background Tasks

- FastAPI Background Tasks (Phase 1)

API Documentation

- OpenAPI (Swagger)

Testing

- Pytest

---

# Database

Primary Database

- PostgreSQL

Cache

- Redis

Future Search

- PostgreSQL Full Text Search (Phase 1)
- OpenSearch (Future)

---

# Authentication

Authentication

- JWT Access Tokens
- Refresh Tokens

Password Hashing

- Argon2id

Verification

- Mobile OTP
- Email Verification

---

# Infrastructure

Cloud Provider

- AWS

Reverse Proxy

- Nginx

Containerization

- Docker (Future)

CI/CD

- GitHub Actions

Version Control

- Git

Repository Hosting

- GitHub

---

# Development Tools

IDE

- Antigravity IDE

AI Assistant

- ChatGPT
- Antigravity AI

API Testing

- Bruno

Database Management

- TablePlus

Terminal

- macOS Terminal

Package Manager

- Homebrew

---

# Development Environment

Operating System

- macOS

Required Software

- Flutter SDK
- Xcode
- Python
- uv
- PostgreSQL
- Redis
- Git
- Homebrew
- CocoaPods

Android Studio is not required during Phase 1 development.

---

# Coding Standards

Formatting

Flutter

- dart format

Python

- Black

Linting

Flutter

- flutter_lints

Python

- Ruff

Type Checking

Python

- Based on FastAPI and Pydantic typing

---

# API Standards

Protocol

- REST

Data Format

- JSON

Versioning

- /api/v1

Authentication

- Bearer JWT

Documentation

- OpenAPI

---

# Security Standards

Transport

- HTTPS

Password Hashing

- Argon2id

Database Access

- SQLAlchemy ORM

Secrets

- Environment Variables

Authorization

- Role-Based Access Control (RBAC)

---

# Approved Flutter Packages

State Management

- flutter_riverpod

Navigation

- go_router

Networking

- dio

Secure Storage

- flutter_secure_storage

Image Caching

- cached_network_image

Serialization

- json_annotation
- json_serializable

Code Generation

- build_runner

Environment Configuration

- flutter_dotenv

Authentication

- google_sign_in
- sign_in_with_apple

Maps, Location & Geocoding

- google_maps_flutter
- geolocator
- geocoding

(Added by Story CUS-002 for map-pin selection, device geolocation, and reverse geocoding in the shared
`LocationPickerScreen`; not documented here at the time — backfilled at PRO-001's story close, the first story
to newly reuse them, per the pre-existing documentation gap both `backend` and `architect` flagged during
PRO-001.)

Image Selection

- image_picker (`^1.2.3`)

(Added by Story PRO-002 for portfolio-photo selection in the Storefront's portfolio manager — no existing
image-picker capability was available to reuse; a well-established, widely-used Flutter package. Automated
tests never depend on real plugin/platform-channel behavior — `PortfolioManager` accepts an injectable picker
for tests.)

File Selection & HTTP

- file_picker (`^11.0.3`)
- http_parser (`^4.1.2`)

(Added by Story VER-001 for verification-document selection on the Upload screen — `image_picker` cannot
browse arbitrary files, and a trade license is plausibly a PDF, not a photo; a well-established, widely-used
Flutter package. `http_parser` sets an explicit `Content-Type` on the multipart document upload and was
already a transitive dependency via `dio`, promoted to direct since `verification_repository.dart` imports it
by name.)

---

# Approved Python Packages

Framework

- fastapi

Server

- uvicorn

ORM

- sqlalchemy

Migration

- alembic

Validation

- pydantic

Authentication

- python-jose

HTTP Client

- httpx

Password Hashing

- pwdlib

Multipart Upload

- python-multipart

(Approved and documented here since Sprint 1 for FastAPI's own multipart form-parsing support, but never
actually exercised by any endpoint until Story PRO-002's portfolio-photo upload endpoints — the first file
upload capability in this codebase, see ADR-017 in `09_DECISIONS.md`. Confirmed present in
`backend/pyproject.toml`'s dependency list.)

Database Driver

- psycopg

Redis

- redis

Environment Variables

- python-dotenv

Testing

- pytest

---

# Packages Requiring Approval

The following require CTO approval before introduction:

- GraphQL
- Celery
- RabbitMQ
- Kafka
- Elasticsearch
- MongoDB
- Firebase
- Third-party analytics SDKs
- Proprietary UI frameworks
- Additional state management libraries

---

# Prohibited Technologies

Do not introduce:

- Multiple state management solutions
- Multiple ORM frameworks
- Multiple HTTP clients
- Multiple routing libraries
- Deprecated Flutter packages
- Deprecated Python packages

Maintain one standard solution for each responsibility.

---

# Version Management

Always use stable releases.

Avoid:

- Alpha releases
- Beta releases
- Release candidates

Package upgrades should be evaluated before adoption.

---

# AI Development Rules

AI assistants must:

- Use only approved technologies.
- Avoid suggesting alternative frameworks unless explicitly requested.
- Reuse existing packages.
- Avoid introducing unnecessary dependencies.
- Follow project architecture and coding standards.
- Generate production-ready implementations.

---

# Technology Review

Technology choices should be reviewed:

- Before each major release
- Before introducing new infrastructure
- Before adopting new frameworks

Any approved changes must be documented in:

`09_DECISIONS.md`

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 04_DATABASE.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 11_MVP_SCOPE.md

---

**End of Document**