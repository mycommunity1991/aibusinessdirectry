# MyCommunity Database Design

**Document ID:** AI-04  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, Database Engineers, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the database architecture, design principles, entity relationships, naming conventions, indexing strategy, and data management standards for the MyCommunity platform.

This document focuses on persistence.

Business concepts are defined in `03_DOMAIN_MODEL.md`.

---

# Database Technology

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL 16+ |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Cache | Redis |
| Full Text Search | PostgreSQL Full Text Search (Phase 1) |
| Vector Search | Planned (Phase 3) |

---

# Database Principles

The database must be:

- Normalized where practical
- Highly maintainable
- Secure by default
- Performance optimized
- Migration friendly
- Cloud ready
- Auditable
- Easy to scale

---

# Database Architecture

```
                    FastAPI

                       │

               SQLAlchemy ORM

                       │

                 PostgreSQL

                       │

          Read / Write Transactions

                       │

                    Redis Cache
```

---

# Schema Organization

```
public

├── identity
├── resident
├── community
├── feed
├── marketplace
├── events
├── notification
├── moderation
├── administration
└── audit
```

Schemas separate business domains while remaining inside a single PostgreSQL database.

---

# Common Columns

Every business table should contain:

| Column | Type |
|---------|------|
| id | UUID |
| created_at | TIMESTAMP WITH TIME ZONE |
| created_by | UUID |
| updated_at | TIMESTAMP WITH TIME ZONE |
| updated_by | UUID |
| deleted_at | TIMESTAMP WITH TIME ZONE (nullable) |
| is_active | BOOLEAN |
| version | INTEGER |

---

# Primary Keys

All primary keys use UUID.

Example

```
id UUID PRIMARY KEY
```

Sequential integers must not be used as public identifiers.

---

# Foreign Keys

Every relationship must use explicit foreign keys.

Example

```
community_id

user_id

post_id
```

Never store relationships as comma-separated values.

---

# Naming Standards

## Tables

Plural snake_case

Examples

```
users

communities

posts

comments

events

marketplace_listings
```

---

## Columns

snake_case

Examples

```
first_name

phone_number

community_id

created_at
```

---

## Indexes

```
idx_users_email

idx_posts_created_at

idx_events_community
```

---

## Constraints

```
pk_users

fk_posts_users

uq_users_email

chk_listing_price
```

---

# Identity Domain

## Tables

```
users

roles

permissions

role_permissions

user_roles

devices

sessions

refresh_tokens

verifications
```

---

# Resident Domain

## Tables

```
profiles

addresses

privacy_settings

emergency_contacts
```

---

# Community Domain

## Tables

```
communities

community_members

community_rules

community_invitations
```

---

# Feed Domain

## Tables

```
posts

comments

reactions

attachments

hashtags

mentions
```

---

# Marketplace Domain

## Tables

```
marketplace_categories

marketplace_listings

listing_images

listing_favorites

listing_inquiries
```

---

# Events Domain

## Tables

```
events

event_categories

event_rsvps

event_attendance
```

---

# Notification Domain

## Tables

```
notifications

notification_preferences

notification_delivery
```

---

# Moderation Domain

## Tables

```
reports

report_reasons

moderation_cases

moderation_actions
```

---

# Administration Domain

## Tables

```
audit_logs

feature_flags

system_settings
```

---

# Relationships

```
User

│

├── Profile

├── Devices

├── Sessions

├── Communities

├── Posts

├── Listings

├── Events

└── Notifications
```

---

```
Community

│

├── Members

├── Posts

├── Events

├── Marketplace Listings

└── Rules
```

---

```
Post

│

├── Comments

├── Reactions

└── Attachments
```

---

# Soft Delete

Business entities use soft delete.

```
deleted_at

is_active
```

Records are never permanently removed during normal operations.

Permanent deletion is an administrative operation.

---

# Audit Strategy

Critical tables include:

```
created_at

updated_at

created_by

updated_by
```

Sensitive operations generate audit log entries.

---

# Transactions

Every business operation must execute inside a database transaction.

Examples

- User Registration
- Community Join
- Marketplace Listing Creation
- Event Registration
- Moderation Actions

Partial writes are prohibited.

---

# Indexing Strategy

Indexes should exist for:

- Foreign Keys
- Frequently filtered columns
- Search columns
- Sorting columns
- Authentication queries

Examples

```
users.email

users.phone_number

posts.community_id

posts.created_at

events.start_date

marketplace_listings.status
```

---

# Unique Constraints

Examples

```
email

phone_number

community_slug

username
```

Business uniqueness should always be enforced by the database.

---

# Data Validation

Validation occurs at multiple layers.

1. Flutter
2. API Validation
3. Service Layer
4. Database Constraints

The database is the final authority.

---

# Caching Strategy

Redis stores:

- Sessions
- Refresh Tokens
- Rate Limits
- Frequently accessed configuration
- Frequently accessed community data

Redis is never the source of truth.

PostgreSQL remains authoritative.

---

# Search Strategy

Phase 1

PostgreSQL Full Text Search

Searchable entities:

- Communities
- Posts
- Marketplace Listings
- Events

Future versions may introduce Elasticsearch or OpenSearch without changing business logic.

---

# Backup Strategy

Production

- Daily full backup
- Hourly incremental backup
- Point-in-time recovery
- Cross-region backup

Development

- Local database dumps
- Seed data
- Migration scripts

---

# Migration Strategy

Schema changes are managed exclusively through Alembic.

Rules:

- Never modify production databases manually.
- Every schema change requires a migration.
- Every migration must support rollback where practical.

---

# Performance Guidelines

- Avoid SELECT *
- Use pagination
- Optimize joins
- Minimize N+1 queries
- Create indexes only where justified
- Profile slow queries
- Batch database operations when possible

---

# Security Guidelines

- Parameterized queries only
- No dynamic SQL
- Encrypt sensitive data
- Store password hashes only
- Never store plaintext secrets
- Apply least privilege database access

---

# Database Growth Strategy

Current Architecture

Single PostgreSQL instance

Future Options

- Read replicas
- Connection pooling
- Table partitioning
- Archive tables
- Independent databases after service extraction

The application architecture must not depend on a single database forever.

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 07_UI_GUIDELINES.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**