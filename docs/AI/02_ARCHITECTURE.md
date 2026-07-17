# AI Marketplace Architecture

**Document ID:** AI-02  
**Version:** 2.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, AI Assistants  
**Last Updated:** 2026-07-14

---

# Purpose

This document defines the software architecture of the AI Marketplace platform.

It serves as the single source of truth for system organization, module boundaries, technology choices, communication patterns, and engineering principles.

All implementation must conform to this architecture.

---

# Architecture Goals

The architecture must provide:

- High maintainability
- Clear separation of concerns
- Strong security
- Excellent performance
- Modular design
- Easy testing
- Cloud-native deployment
- Future scalability
- Low operational complexity

---

# Architecture Style

## Primary Pattern

Modular Monolith

The system is deployed as a single application while being internally divided into independent business modules.

Modules communicate only through well-defined service interfaces.

Direct coupling between modules is prohibited.

---

## Future Evolution

The modular monolith has been intentionally designed so that individual modules can later be extracted into independent microservices without significant refactoring.

No implementation should assume that every module will always execute within the same process.

---

# System Overview

```
                    Flutter Mobile App (iOS / Android)
                               |
                               |
                    HTTPS / REST APIs
                               |
                               v
+--------------------------------------------------------------+
|                    FastAPI Backend                           |
|--------------------------------------------------------------|
| Identity & Access                                             |
| Customer                                                      |
| Provider (Business / Freelancer)                              |
| Category                                                       |
| Conversation / AI Intake (LLM-API, RAG-grounded)               |
| Search Request & Matching                                     |
| Contact View                                                  |
| Verification                                                  |
| Review & Outcome Tag                                          |
| Notifications                                                 |
| Administration                                                 |
+------------------------+--------------------------------------+
                         |
                         |
         +---------------+---------------+
         |                               |
         v                               v
 PostgreSQL                         Redis
 Primary Database              Cache / Queue / Sessions
```

There is no landing website in this architecture and no Community, Feed, Events, or Messaging module — see `03_DOMAIN_MODEL.md` for the authoritative domain boundaries. The product is a directory/AI-intake/contact utility, not a social platform.

---

# Technology Stack

## Mobile

- Flutter
- Dart
- Material 3
- Riverpod
- GoRouter
- Dio
- Flutter Secure Storage

---

## Backend

- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- Uvicorn
- uv

---

## AI / Matching Layer

- LLM API (prompt-engineered, RAG-grounded against the platform's own provider database)
- No custom-trained matching model — see `00_PROJECT_CONTEXT.md` Section 3
- Manual ("Wizard of Oz") fallback for low-confidence Conversation Sessions

---

## Database

- PostgreSQL

---

## Cache

- Redis

---

## Authentication

- JWT Access Tokens
- Refresh Tokens
- Secure Password Hashing

---

## Infrastructure

- AWS
- Docker (Future)
- GitHub Actions
- Nginx

---

# High-Level Layers

```
Presentation Layer

↓

Application Layer

↓

Domain Layer

↓

Infrastructure Layer

↓

Database
```

---

# Mobile Architecture

Feature-First Clean Architecture

```
mobile/

features/

core/

shared/

config/

services/

theme/

routes/
```

Each feature owns:

- UI
- State
- Business Logic
- Repository
- Models

Features must not depend directly on each other.

Shared functionality belongs in shared modules.

---

# Backend Architecture

```
backend/

app/

api/

core/

modules/

shared/

database/

middleware/

workers/

tests/
```

Each module contains:

```
module/

api/

services/

repositories/

schemas/

models/

dependencies/

events/
```

---

# Core Business Modules

These modules follow the aggregates defined in `03_DOMAIN_MODEL.md`. There is no Community, Feed, Events, or Messaging module in this architecture — that concept was superseded by the AI Marketplace pivot (see `00_PROJECT_CONTEXT.md` Section 11 for the changelog).

## Identity & Access

Responsibilities

- Registration (Google / Apple / Mobile + OTP) — mandatory, no guest path
- Login
- Token Management
- Session Management
- Role (Customer / Provider / Admin)

---

## Customer

Responsibilities

- Customer Profile
- Saved Addresses / Location
- Notification and language preferences

---

## Provider

Responsibilities

- Provider profile (Business Profile / Freelancer Profile subtypes)
- Availability (working hours, emergency/urgent flag)
- Portfolio (photos)
- Claim flow for Google-seeded unclaimed listings

---

## Category

Responsibilities

- Category taxonomy
- Category Question Templates that drive the AI's follow-up questions

---

## Conversation / AI Intake

Responsibilities

- Conversation Session (customer/AI message turns)
- Confidence scoring, driving Wizard-of-Oz fallback routing
- Producing a structured Search Request from unstructured customer input

---

## Search Request & Matching

Responsibilities

- Location + service-area + category matching against Provider data
- Search Event Log (matched and unmatched queries)
- Ranked provider results

---

## Contact View

Responsibilities

- Recording a customer viewing a matched provider's phone number
- Basis for provider visibility analytics and future pay-per-lead billing
- Eligibility gate for Outcome Tag / Review submission

---

## Verification

Responsibilities

- Verification Record / Document / Status lifecycle
- Mandatory gate for Freelancer Providers before listing goes live
- Configurable, lighter-weight gate for Business Providers

---

## Review

Responsibilities

- Anchor-verified Reviews and Ratings (require a "Yes" Outcome Tag)
- Merit-based provider ranking input

---

## Notifications

Responsibilities

- WhatsApp / SMS / Email delivery
- Triggered by new Contact View, Verification status change, Outcome Tag prompts

---

## Administration

Responsibilities

- Manual verification review
- Manual Match Assignment for low-confidence Conversation Sessions
- Unmatched Query Reports (category/supply-gap analytics)
- System configuration, audit, monitoring

---

# Data Flow

```
Flutter

↓

REST API

↓

FastAPI Router

↓

Application Service

↓

Repository

↓

PostgreSQL

↓

Response DTO

↓

Flutter UI
```

Business logic must never exist inside API routes.

Routes orchestrate.

Services implement business rules.

Repositories handle persistence.

---

# Communication Rules

Allowed

```
Module

↓

Service

↓

Repository
```

Not Allowed

```
Module

↓

Another Module's Repository
```

Modules communicate through services only.

---

# Dependency Rules

Presentation depends on Application.

Application depends on Domain.

Infrastructure depends on Domain.

Domain depends on nothing.

Dependencies must always point inward.

---

# Error Handling

Errors must be:

- Predictable
- Structured
- Logged
- User Friendly

Stack traces must never be returned to clients.

---

# Configuration

Environment-specific configuration must exist outside source code.

Supported environments:

- Development
- Staging
- Production

No secrets may be committed to Git.

---

# Logging

Structured logging only.

Each request should include:

- Correlation ID
- User ID (when authenticated)
- Timestamp
- Module
- Severity

---

# Security Principles

- Authentication required where applicable
- Authorization enforced at service layer
- Input validation everywhere
- Parameterized database queries
- Encrypted secrets
- HTTPS only
- Principle of least privilege

---

# Performance Principles

- Pagination by default
- Lazy loading where appropriate
- Database indexing
- Query optimization
- Response caching
- Asynchronous background processing for long-running tasks

---

# Testing Strategy

Unit Tests

Service Layer

Integration Tests

API Layer

Widget Tests

Flutter UI

End-to-End Tests

Critical User Journeys

Every bug fix should include a corresponding automated test.

---

# Deployment Strategy

Current

Single deployable application

Future

Independent deployment of extracted services without changing external APIs.

---

# Architectural Constraints

The following practices are prohibited:

- Business logic inside controllers
- Database access inside controllers
- Circular dependencies
- Shared mutable global state
- Hardcoded configuration
- Hardcoded secrets
- Direct module coupling
- Duplicate domain models

---

# Architecture Principles

Every implementation should satisfy the following principles:

- Simplicity
- Consistency
- Readability
- Security
- Testability
- Performance
- Maintainability
- Extensibility

Whenever two valid solutions exist, prefer the simpler solution.

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 03_DOMAIN_MODEL.md
- 04_DATABASE.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 07_UI_GUIDELINES.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**
