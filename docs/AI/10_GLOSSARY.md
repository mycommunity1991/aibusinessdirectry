# MyCommunity Glossary

**Document ID:** AI-10  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, Product Team, QA, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This glossary defines the official terminology used throughout the MyCommunity platform.

All engineering, product, design, QA, documentation, and AI-generated content must use these definitions consistently.

If a term is not defined here, it should not become part of the project's vocabulary until it has been reviewed and added.

---

# General Terms

## Community

A verified residential group where residents communicate, collaborate, and participate in local activities.

Examples:

- Apartment Building
- Residential Tower
- Villa Community
- Gated Community

---

## Resident

A verified individual who belongs to one or more communities and uses the MyCommunity platform.

---

## User

A system account capable of authentication.

Every Resident is a User, but future system users (administrators, moderators, service providers) are also Users.

---

## Profile

The public information associated with a User.

Examples

- Name
- Profile Picture
- Bio
- Interests

---

## Verification

The process of confirming that a user, resident, or organization is genuine.

Verification may include:

- Email
- Phone
- Community
- Identity

---

# Community Terms

## Membership

Represents the relationship between a Resident and a Community.

---

## Community Administrator

A resident responsible for managing a community.

Responsibilities include:

- Approving members
- Managing announcements
- Moderation
- Community settings

---

## Moderator

A trusted user responsible for enforcing community rules.

Moderators have limited administrative privileges.

---

## Community Rules

Guidelines governing acceptable behavior inside a community.

---

# Feed Terms

## Feed

The primary timeline displaying community activity.

---

## Post

Content published by a resident inside a community.

---

## Comment

A response attached to a post.

---

## Reaction

A lightweight interaction expressing sentiment toward a post or comment.

Examples

- Like
- Love
- Helpful

---

## Mention

A reference to another user within content.

---

## Attachment

Media associated with a post or comment.

Examples

- Image
- Video
- Document

---

# Marketplace Terms

## Marketplace

The feature that allows residents to buy and sell items locally.

---

## Listing

An item or service published in the Marketplace.

---

## Listing Owner

The resident who created a listing.

---

## Inquiry

A conversation initiated regarding a marketplace listing.

---

## Listing Status

Possible states:

- Draft
- Published
- Reserved
- Sold
- Archived

---

# Event Terms

## Event

A scheduled activity within a community.

---

## RSVP

A resident's response to an event invitation.

Possible responses:

- Going
- Interested
- Not Going

---

## Attendance

The confirmed participation of a resident in an event.

---

# Notification Terms

## Notification

A message informing users about platform activity.

---

## Push Notification

A notification delivered to a mobile device.

---

## In-App Notification

A notification displayed within the application.

---

## Notification Preference

User-defined settings controlling notification delivery.

---

# Moderation Terms

## Report

A complaint submitted regarding content or user behavior.

---

## Moderation Case

The investigation created from a report.

---

## Warning

A formal notice issued to a user.

---

## Suspension

Temporary removal of platform access.

---

## Ban

Permanent removal of platform access.

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

Permissions are granted through assigned roles.

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

- Community
- Marketplace
- Events

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

- UserRegistered
- CommunityJoined
- ListingPublished

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

## Provider

A Riverpod object responsible for managing application state.

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

Examples

- Antigravity
- ChatGPT
- GitHub Copilot

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

# Official Naming

| Term | Official Usage |
|------|----------------|
| MyCommunity | Product Name |
| Resident | Primary User |
| Community | Residential Group |
| Listing | Marketplace Item |
| Event | Community Activity |
| Notification | User Alert |
| Report | Moderation Submission |
| Moderator | Community Safety Role |
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