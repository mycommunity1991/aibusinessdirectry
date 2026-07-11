# MyCommunity Domain Model

**Document ID:** AI-03  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, Product Team, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the core business domain of MyCommunity.

It identifies the primary business entities, their responsibilities, ownership, relationships, and boundaries.

This document represents the business model, not the database schema.

Database implementation details belong in `04_DATABASE.md`.

---

# Domain Overview

MyCommunity is organized around verified communities.

Residents interact with one another through communities by creating posts, participating in events, buying and selling items, requesting help, and communicating safely within trusted neighborhoods.

The platform is composed of independent business domains that collaborate while maintaining clear ownership boundaries.

---

# Domain Boundaries

```
Identity & Access

↓

Resident

↓

Community

↓

Content

↓

Marketplace

↓

Events

↓

Notifications

↓

Moderation

↓

Administration
```

Every business capability belongs to exactly one domain.

---

# Core Domains

## Identity & Access

### Purpose

Responsible for authentication, authorization, verification and account security.

### Entities

- User
- Authentication
- Session
- Refresh Token
- Device
- Verification
- Role
- Permission

---

## Resident

### Purpose

Represents the individual using the platform.

### Entities

- User Profile
- Preferences
- Address
- Resident Verification
- Privacy Settings
- Emergency Contact

---

## Community

### Purpose

Represents residential communities where residents interact.

### Entities

- Community
- Building
- Tower
- Villa Community
- Membership
- Invitation
- Community Rules

---

## Feed

### Purpose

Handles community conversations and interactions.

### Entities

- Post
- Comment
- Reaction
- Attachment
- Mention
- Hashtag
- Poll

---
# Marketplace (Phase 2)

## Status

Deferred

## Purpose

The Marketplace domain enables trusted buying and selling between verified residents.

This domain is part of the long-term product architecture but is **not included in the approved Phase 1 MVP**.

## Planned Entities

- Listing
- Category
- Listing Image
- Favorite
- Inquiry
- Transaction
- Rating

## Implementation Rule

Marketplace is intentionally deferred until Phase 2.

AI assistants must not implement Marketplace-related:

- Database tables
- APIs
- Business logic
- Flutter screens
- Widgets
- Tests

unless explicitly instructed by the CTO.

The domain exists only to preserve the long-term architecture and prevent future redesign.
---
## Notification

### Purpose

Delivers system and community notifications.

### Entities

- Notification
- Notification Preference
- Push Notification
- Email Notification

---

## Moderation

### Purpose

Maintains trust and safety.

### Entities

- Report
- Report Reason
- Moderation Case
- Warning
- Suspension
- Ban

---

## Administration

### Purpose

Platform management.

### Entities

- Admin User
- Audit Log
- Feature Flag
- System Configuration

---

# Primary Entity Relationships

```
Resident

│

├── belongs to → Community

│

├── creates → Posts

│

├── comments on → Posts

│

├── reacts to → Posts

│

├── creates → Listings

│

├── creates → Events

│

├── receives → Notifications

│

└── submits → Reports
```

---

# Aggregate Roots

The following entities are aggregate roots.

Changes to child entities must occur through their aggregate root.

| Aggregate | Child Entities |
|------------|----------------|
| User | Devices, Preferences, Sessions |
| Community | Memberships, Rules |
| Post | Comments, Reactions, Attachments |
| Listing | Images, Favorites, Inquiries |
| Event | RSVPs, Attendance |
| Notification | Delivery Records |
| Report | Moderation Actions |

---

# Ownership Rules

Each aggregate owns its child entities.

Example:

```
Community

↓

Membership

↓

Member Role
```

Membership cannot exist without a Community.

---

# Business Rules

## User

- Every user has one profile.
- Every user has one unique account.
- Email and phone must be unique.
- Users may belong to multiple communities.
- Users control their privacy settings.

---

## Community

- Every community has administrators.
- Communities define their own rules.
- Membership is required before participation.
- Communities may require verification.

---

## Feed

- Posts belong to one community.
- Comments belong to one post.
- Reactions belong to one post or comment.
- Deleted posts remain recoverable for moderation.

---

## Marketplace

- Listings belong to one community.
- Listings have one owner.
- Archived listings remain searchable by administrators.
- Sold listings become read-only.

---

## Events

- Events belong to one community.
- Residents may RSVP once.
- Event creators manage attendance.

---

## Notifications

- Notifications belong to one user.
- Delivery status is tracked.
- Read status is stored independently.

---

## Moderation

- Reports reference exactly one target.
- Every report has a lifecycle.
- Moderation decisions are auditable.
- Permanent deletion requires administrator approval.

---

# Domain Events

The platform uses domain events internally.

Examples:

```
UserRegistered

CommunityJoined

PostCreated

CommentAdded

ListingPublished

ListingSold

EventCreated

EventCancelled

NotificationSent

ReportSubmitted

ReportResolved
```

Events should represent completed business actions.

---

# Entity Lifecycle

Example

Post

```
Draft

↓

Published

↓

Edited

↓

Archived

↓

Deleted
```

Example

Listing

```
Draft

↓

Published

↓

Reserved

↓

Sold

↓

Archived
```

Example

Report

```
Submitted

↓

Under Review

↓

Resolved

↓

Closed
```

---

# Cross-Domain Communication

Domains communicate through services and domain events.

Direct access to another domain's internal data is prohibited.

Allowed

```
Community Service

↓

Membership Service
```

Not Allowed

```
Marketplace Repository

↓

Community Database Tables
```

---

# Domain Principles

Every domain should:

- Have a single responsibility.
- Own its own business rules.
- Expose clear interfaces.
- Hide internal implementation.
- Avoid shared mutable state.
- Be independently testable.

---

# Future Domain Expansion

The following domains are part of the long-term product vision but are intentionally excluded from the Phase 1 MVP.

- Marketplace
- Local Services
- Community Polls
- Volunteer Programs
- Smart Building Integration
- Resident Rewards
- AI Recommendations
- Digital Documents
- Government Services

These domains must not be implemented unless the MVP scope is formally expanded.

Their inclusion in this document is architectural only and must not be interpreted as implementation approval.

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 04_DATABASE.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 07_UI_GUIDELINES.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**