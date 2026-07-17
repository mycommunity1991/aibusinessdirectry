# AI Marketplace Glossary

**Document ID:** AI-10  
**Version:** 2.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, Product Team, QA, AI Assistants  
**Last Updated:** 2026-07-14

---

# Purpose

This glossary defines the official terminology used throughout the AI Marketplace platform.

All engineering, product, design, QA, documentation, and AI-generated content must use these definitions consistently.

If a term is not defined here, it should not become part of the project's vocabulary until it has been reviewed and added.

---

# General Terms

## Customer

The person seeking a service. Must hold a registered Account — there is no guest path.

---

## Provider

Represents supply on the platform. A single aggregate with two subtypes: Business or Freelancer. See `03_DOMAIN_MODEL.md`.

---

## Business (Provider subtype)

A formal, fixed-location Provider — cafe, repair shop, salon, and similar.

---

## Freelancer (Provider subtype)

An individual, mobile, one-to-one service Provider — plumber, electrician, tutor, car-washer, and similar. Mandatory ID/license verification before the listing goes live.

---

## User / Account

A system identity capable of authentication. Every Customer and every Provider owner is backed by an Account; future Admin users are also Accounts.

---

## Profile

The public-facing information associated with a Provider (or a Customer's private saved details).

Provider profile examples:

- Name
- Services offered
- Areas covered
- Price ranges
- Portfolio photos

---

## Verification

The process of confirming a Provider is genuine before it can go live (Freelancer, mandatory) or be claimed (Business, Freelancer).

Verification may include:

- Government ID / license document
- Phone
- Address / trade registration

---

# Discovery & Matching Terms

## Category

The taxonomy that structures Provider listings and the AI's category-specific question flows.

---

## Service Area

Where a Provider can be discovered and matched — a fixed-location radius (Business) or a mobile travel radius (Freelancer).

---

## Conversation Session (AI Intake)

The chat between a Customer and the platform's AI that understands an unstructured need, asks follow-up questions, and produces a Search Request. Not a public/social artifact, and not customer-provider messaging (which does not exist in this product).

---

## Confidence Score

A per-Conversation-Session score that determines whether a request is auto-matched or routed to admin-assisted (Wizard-of-Oz) matching.

---

## Search Request

The structured, matchable representation of a Customer's need, produced by a Conversation Session.

---

## Search Event Log

A record of every Search Request, matched or not — feeds provider visibility analytics and admin unmatched-query analytics.

---

## Contact View

A Customer viewing a matched Provider's phone number. Shown directly and immediately — no staged disclosure, no quote-acceptance gate. The basis for provider lead analytics and the eligibility gate for Outcome Tag / Review.

---

## Outcome Tag

The Customer's self-reported "Did you hire them?" signal tied to a Contact View. The platform's only conversion signal.

---

## Review / Rating

Anchor-verified feedback — can only be created against a Contact View with a "Yes" Outcome Tag. Drives merit-based Provider ranking.

---

## Claim Flow

The process by which a Provider owner takes ownership of a Google-seeded, unclaimed listing by passing the Verification gate.

---

# Notification Terms

## Notification

A message informing Customers or Providers about platform activity (new lead, verification status change, Outcome Tag prompt).

---

## Notification Channel

WhatsApp, SMS, or Email — the delivery channel, configurable per user.

---

# Administration Terms

## Manual Match Assignment

Admin-assisted matching for a low-confidence Conversation Session (Wizard-of-Oz fallback).

---

## Unmatched Query Report

Admin-facing analytics surfacing Search Requests that produced no good match — used to guide category and supply-gap decisions.

---

# Identity Terms

## Authentication

The process of confirming a user's identity.

---

## Authorization

The process of determining what a user is allowed to do.

---

## Access Token

A short-lived JWT used to authenticate API requests.

---

## Refresh Token

A long-lived token used to obtain new access tokens.

---

## Session

A record of an authenticated login on a specific device.

---

# Security Terms

## RBAC

Role-Based Access Control.

Permissions are granted through assigned roles (Customer / Provider / Admin).

---

## ABAC

Attribute-Based Access Control.

Future authorization model using user, resource, and contextual attributes.

---

## Least Privilege

Users receive only the permissions required to perform their responsibilities.

---

## Audit Log

An immutable record of important system activities.

---

# Technical Terms

## Modular Monolith

A single deployable application composed of independent business modules.

---

## Module

A self-contained business capability.

Examples

- Identity & Access
- Provider
- Conversation / AI Intake
- Search Request

---

## Service

Contains business logic.

Services coordinate workflows and enforce business rules.

---

## Repository

Responsible for database access.

Repositories do not contain business logic.

---

## DTO

Data Transfer Object.

Used to exchange data between application layers.

---

## Domain Event

A business event representing something that has already happened.

Examples

- CustomerRegistered
- SearchRequestSubmitted
- ContactViewCreated
- OutcomeTagSubmitted

See `03_DOMAIN_MODEL.md` for the full event list.

---

## API

Application Programming Interface.

REST endpoints exposed by the backend.

---

## Migration

A version-controlled database schema change.

Managed through Alembic.

---

## Environment

A deployment stage.

Supported environments:

- Development
- Staging
- Production

---

# Mobile Terms

## Feature

An independently developed business capability within the Flutter application.

---

## Screen

A complete page presented to the user.

---

## Widget

The fundamental UI building block in Flutter.

---

## Provider (Riverpod)

A Riverpod object responsible for managing application state.

Not to be confused with the domain term **Provider** (a Business or Freelancer supplier) above — the same word is used by Riverpod's state-management API and by the product's domain model; context disambiguates.

---

## Theme

The centralized definition of application colors, typography, spacing, and styling.

---

# Development Terms

## Pull Request (PR)

A proposed code change submitted for review.

---

## ADR

Architecture Decision Record.

Documents important architectural decisions.

Stored in:

```
09_DECISIONS.md
```

---

## Definition of Done

The minimum quality standard before work is considered complete.

Requirements:

- Code complete
- Tested
- Reviewed
- Documented
- Production ready

---

## Technical Debt

A deliberate compromise made to accelerate delivery.

All technical debt must be:

- Documented
- Tracked
- Planned for resolution

---

# AI Terms

## AI Assistant

An AI coding assistant that contributes to the project.

AI assistants must follow all documents within:

```
docs/AI/
```

---

## AI Knowledge Base

The collection of governance documents stored in:

```
docs/AI/
```

This directory is the authoritative source for project standards, architecture, and engineering guidance.

---

## RAG-Grounded

Describes the constraint that the AI intake/matching layer must never assert availability, prices, ratings, or capabilities not backed by real platform data. See `00_PROJECT_CONTEXT.md` Section 3.

---

## Wizard of Oz Fallback

Manual, admin-assisted matching used for low-confidence Conversation Sessions instead of blocking on full automation.

---

# Official Naming

| Term | Official Usage |
|------|----------------|
| AI Marketplace | Product Name (working title — see `13_OPEN_DECISIONS.md` item 8) |
| Customer | Person seeking a service |
| Provider | Business or Freelancer supplier |
| Conversation Session | AI intake chat |
| Search Request | Structured, matchable customer need |
| Contact View | Customer viewing a matched Provider's phone number |
| Outcome Tag | Customer's self-reported hire confirmation |
| Verification | Trust gate before a Provider goes live |
| Notification | User Alert |
| Administrator | Platform Management Role |
| Module | Business Capability |
| Service | Business Logic Layer |
| Repository | Data Access Layer |

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
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md

---

**End of Document**
