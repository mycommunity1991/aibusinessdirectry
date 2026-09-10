# AI Marketplace Database Design

**Document ID:** AI-04
**Version:** 3.8.0
**Status:** Active
**Owner:** CTO
**Audience:** Engineering Team, Database Engineers, AI Assistants
**Last Updated:** 2026-09-10

**Change note (v3.7.0 → v3.8.0):** Confirmed the Search Domain's three tables (`search_requests`,
`provider_matches`, `search_event_log`) and `administration.manual_match_assignments` shipped, by Story AI-002
(Sprint 7) — via a new reversible Alembic migration creating the `search` schema and adding
`manual_match_assignments` to the existing `administration` schema. Four flagged, necessary nullable-column
deviations from this document's previously-literal `NOT NULL` text (see ADR-038, `09_DECISIONS.md`):
`search_requests.category_id`, `search_requests.structured_criteria`, `search_requests.customer_latitude`/
`customer_longitude` (all now nullable — a routed-to-admin session may have no resolved category, no validated
structured criteria, and/or no default saved-address coordinates, and the row is still created honestly rather
than fabricating a value or blocking the customer), and `manual_match_assignments.assigned_admin_id` (nullable,
populated only at resolution — `ADR-030` had already found `NOT NULL` here didn't fit an unassigned pull-queue,
this is the story that actually built the table). Updated the Search Domain and Administration Domain sections'
tables accordingly.

**Change note (v3.6.0 → v3.7.0):** Confirmed the Conversation / AI Intake Domain section's three tables
(`conversation_sessions`, `messages`, `confidence_scores`) shipped exactly per this document's own pre-existing
spec, by Story AI-001 (Sprint 7) — plus two additive items flagged for this update: `conversation_status` gains a
fourth value, `abandoned` (set when a customer starts a new session while a previous one is still `active`); and
`conversation_sessions` gains `structured_criteria` (JSONB, nullable), the AC9 `search_requests`-ready payload
populated only when a session reaches `status=completed`, validated via a Pydantic model before persistence (see
ADR-032/ADR-033, `09_DECISIONS.md`). Also documented `messages`' `uq_messages_session_sequence` as a **partial**
unique index (`WHERE is_active = true`) rather than a plain table-level constraint — required because
`AI-001`'s revise-a-previous-answer flow soft-deletes truncated messages rather than hard-deleting them (ADR-036),
mirroring `uq_saved_addresses_customer_default`'s existing precedent.

**Change note (v3.5.0 → v3.6.0):** Confirmed the Category Domain section's three tables (`categories`,
`category_question_templates`, `provider_categories`) shipped exactly per this document's own pre-existing spec,
by Story CTG-001 (Sprint 7) — via this codebase's first data-seeding migration (ADR-028, `09_DECISIONS.md`),
seeding the full v1 launch taxonomy into `categories`/`category_question_templates`. `provider_categories` was
created empty; reconciling `provider_category_labels` into it remains a separate, deferred story. Updated the
`provider_category_labels` and Category Domain sections accordingly (previously noting the real domain "does not
exist yet" — no longer accurate).

**Change note (v3.4.0 → v3.5.0):** Confirmed Section 13's `idx_service_areas_location` and
`idx_saved_addresses_location` GiST indexes shipped exactly per this document's own pre-existing spec, by Story
DIR-001 (Sprint 6) — via a new, reversible Alembic migration enabling the `cube`/`earthdistance` extensions and
creating both indexes. Updated the `service_areas` and `saved_addresses` table sections' Indexes lists
accordingly (previously noting the geospatial index as "not yet added, no story queries it yet" — no longer
accurate). See ADR-025/ADR-026 (`09_DECISIONS.md`) for the new `search` module and raw-SQL precedents this
story's query established.

**Change note (v3.3.0 → v3.4.0):** Documented `administration.admin_action_log` and `notification.notifications`
as shipped exactly per their pre-existing spec by Story VER-002 (Sprint 5), both built with the full
`CommonColumnsMixin` per the spec-literal reasoning recorded in ADR-021/ADR-022 (`09_DECISIONS.md`); added
`providers.chk_providers_discoverable_requires_approved` to the Constraints list — a new DB-level defense-in-depth
`CHECK` constraint added by VER-002 (Plan Decision 4), applying unconditionally to both Provider subtypes.

**Change note (v3.2.0 → v3.3.0):** Documented `provider.provider_availability`, `provider.portfolios`, and
`provider.service_areas` as shipped exactly per their pre-existing spec by Story PRO-002 (Sprint 4); added
`provider.provider_category_labels` as a new, deliberately-not-`provider_categories`-named interim table
(Decision 1, `Plan_S04_PRO-002.md` — see ADR-017 in `09_DECISIONS.md` for the related file-upload decision);
removed `providers.category_label` (PRO-001), which PRO-002's migration backfilled into
`provider_category_labels` and then dropped.

**Change note (v3.1.0 → v3.2.0):** Documented `saved_addresses`' `uq_saved_addresses_customer_default` partial
unique index, added by Story CUS-002 (Sprint 3) as defense-in-depth alongside the primary transactional
default-uniqueness mechanism — see ADR-015 in `09_DECISIONS.md`.

**Change note (v3.0.0 → v3.1.0):** Documented the self-dealing guard on `contact_views`/`reviews` required by the confirmed dual-role rule (one Account may hold both Customer and Provider roles) — see `03_DOMAIN_MODEL.md` v0.8.1.

---

# Purpose

This document defines the complete, implementation-ready database schema for the AI Marketplace platform: every table, column, type, key, constraint, and index, organized by business domain.

Business concepts, entities, and rules are defined in `03_DOMAIN_MODEL.md`. This document is the persistence-layer translation of that model, scoped to `11_MVP_SCOPE.md`. Where a product decision is still open (`13_OPEN_DECISIONS.md`), this schema is built to absorb the eventual answer without a breaking migration — each such case is called out explicitly in Section 14.

**Change note (v2.0.0 → v3.0.0):** v2.0.0 (and everything before it) listed table names only, grouped by domain, with no columns, types, or keys — a naming skeleton, not a buildable schema. No SQLAlchemy models exist yet (`backend/app/models/` is empty) and the only live Alembic migration is an empty initial revision — a prior migration implementing the old "MyCommunity" resident/community data model was removed from the codebase during the pivot (see `09_DECISIONS.md` ADR-011). v3.0.0 is the first full, column-level design for the AI Marketplace domain and is intended to be implemented directly as SQLAlchemy models and Alembic migrations. Nothing from the pre-pivot resident/community schema is carried forward.

---

# Database Technology

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL 16+ |
| ORM | SQLAlchemy 2.x (async) |
| Migration | Alembic |
| Cache | Redis |
| Full Text Search | PostgreSQL Full Text Search (Phase 1) |
| Geospatial | PostgreSQL `cube` + `earthdistance` contrib extensions (Phase 1) — see Section 13 |
| Vector Search | Planned (Phase 3), for Conversation/AI Intake ↔ Provider semantic matching |

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

               SQLAlchemy ORM (async)

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
├── customer
├── provider
├── category
├── conversation
├── search
├── contact
├── verification
├── review
├── notification
├── administration
└── audit
```

Schemas separate business domains while remaining inside a single PostgreSQL database. Cross-schema foreign keys are permitted (e.g. `provider.providers.user_id → identity.users.id`) — schema separation is organizational, not a hard isolation boundary; module isolation is enforced at the application/repository layer per `02_ARCHITECTURE.md`, not by database schema alone.

---

# Common Columns

Every business table (i.e. every table below except pure join tables and `audit.audit_logs`, which is append-only) includes:

| Column | Type | Nullable | Notes |
|---------|------|----------|-------|
| id | UUID | No | Primary key. Default `gen_random_uuid()`. |
| created_at | TIMESTAMPTZ | No | Default `now()`. |
| created_by | UUID | Yes | FK → `identity.users.id`. Null for system-generated rows (seed data, imports). |
| updated_at | TIMESTAMPTZ | No | Default `now()`, updated on every write. |
| updated_by | UUID | Yes | FK → `identity.users.id`. |
| deleted_at | TIMESTAMPTZ | Yes | Null unless soft-deleted. |
| is_active | BOOLEAN | No | Default `true`. |
| version | INTEGER | No | Default `1`. Optimistic locking. |

Pure join/association tables (e.g. `provider_categories`, `role_permissions`, `user_roles`) use a composite primary key and only `created_at` — they represent a relationship, not an independently-owned business record, so soft delete/versioning does not apply; the relationship is inserted or deleted outright.

Column tables below list only columns **in addition to** the Common Columns, unless a table is a join table (called out explicitly).

---

# Primary & Foreign Keys

All primary keys use UUID (`gen_random_uuid()`), per ADR-008 in `09_DECISIONS.md`. Sequential integers must not be used as public identifiers. Every relationship is an explicit foreign key column named `<entity>_id`. Comma-separated or array-encoded relationships are prohibited except where explicitly noted (e.g. `freelancer_profiles.skills` as a text array, which is an attribute list, not a relationship).

---

# Enum Types

Small, stable, rarely-changing value sets use native PostgreSQL `ENUM` types (cheap to filter/index, self-documenting). Value sets that are expected to grow or change without a deploy (e.g. admin action types, notification types) use `VARCHAR` with an application-level constant, not a DB enum, to avoid `ALTER TYPE` migration friction.

| Enum | Values |
|---|---|
| `user_status` | `active`, `suspended`, `deleted` |
| `auth_provider` | `google`, `apple`, `mobile_otp`, `email_password` (admin-only) |
| `device_platform` | `ios`, `android` |
| `language_code` | `en`, `ar` |
| `notification_channel` | `whatsapp`, `sms`, `email` |
| `otp_purpose` | `registration`, `login`, `arrival_verification`, `claim_listing` |
| `provider_type` | `business`, `freelancer` |
| `listing_source` | `self_registered`, `google_seeded_unclaimed` |
| `verification_status` | `pending`, `under_review`, `approved`, `rejected` |
| `verification_type` | `freelancer_id`, `business_license`, `business_lightweight` |
| `document_type` | `emirates_id`, `trade_license`, `other` |
| `conversation_status` | `active`, `completed`, `abandoned`, `routed_to_admin` |
| `message_sender` | `customer`, `ai` |
| `search_request_status` | `matched`, `unmatched`, `pending_manual_match` |
| `weekday` | `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday` |

---

# Identity Domain (`identity` schema)

## users

| Column | Type | Nullable | Notes |
|---|---|---|---|
| email | VARCHAR(255) | Yes | Unique (partial: `WHERE email IS NOT NULL`). |
| email_verified_at | TIMESTAMPTZ | Yes | |
| phone_country_code | VARCHAR(5) | Yes | E.g. `+971`. |
| phone_number | VARCHAR(20) | Yes | Unique together with `phone_country_code` (partial: `WHERE phone_number IS NOT NULL`). |
| phone_verified_at | TIMESTAMPTZ | Yes | |
| password_hash | VARCHAR(255) | Yes | Argon2id. Populated only for `email_password` auth (internal Admin accounts). Customer/Provider accounts authenticate via OAuth or OTP and have no password. |
| auth_provider | `auth_provider` | No | Primary auth method used at registration. |
| external_auth_subject | VARCHAR(255) | Yes | Google/Apple `sub` claim. Unique together with `auth_provider`. |
| status | `user_status` | No | Default `active`. |
| preferred_language | `language_code` | No | Default `en`. |
| last_login_at | TIMESTAMPTZ | Yes | |

**Constraints**
- `uq_users_email_provider` on `(auth_provider, email)` (partial, `WHERE email IS NOT NULL`) — scoped per provider (not globally unique) so the same email under two different providers can each hold their own `User` row (see AUTH-002, AC5/AC9); still prevents a duplicate within the same provider.
- `uq_users_phone` on `(phone_country_code, phone_number)` (partial, `WHERE phone_number IS NOT NULL`)
- `uq_users_external_auth` on `(auth_provider, external_auth_subject)` (partial, `WHERE external_auth_subject IS NOT NULL`)
- `chk_users_has_identifier`: at least one of `email`, `phone_number`, `external_auth_subject` must be non-null

**Indexes:** `idx_users_email`, `idx_users_phone_number`, `idx_users_status`

Passwords are never stored in plaintext (see `06_SECURITY.md`). A `User` has zero or one `Customer Profile` and zero or one `Provider` — the same account may in principle hold both roles.

## roles

| Column | Type | Nullable | Notes |
|---|---|---|---|
| name | VARCHAR(50) | No | Unique. Seed values: `customer`, `provider`, `admin`. |
| description | TEXT | Yes | |

**Constraints:** `uq_roles_name`

## permissions

| Column | Type | Nullable | Notes |
|---|---|---|---|
| code | VARCHAR(100) | No | Unique, e.g. `provider.verify`, `search.view_analytics`. |
| description | TEXT | Yes | |

**Constraints:** `uq_permissions_code`

## role_permissions *(join table)*

| Column | Type | Nullable | Notes |
|---|---|---|---|
| role_id | UUID | No | FK → `roles.id`, part of composite PK |
| permission_id | UUID | No | FK → `permissions.id`, part of composite PK |
| created_at | TIMESTAMPTZ | No | |

**Constraints:** `pk_role_permissions (role_id, permission_id)`

## user_roles *(join table)*

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `users.id`, part of composite PK |
| role_id | UUID | No | FK → `roles.id`, part of composite PK |
| created_at | TIMESTAMPTZ | No | |

**Constraints:** `pk_user_roles (user_id, role_id)`

## devices

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `users.id` |
| platform | `device_platform` | No | |
| device_name | VARCHAR(255) | Yes | |
| push_token | VARCHAR(255) | Yes | For notification delivery |
| is_trusted | BOOLEAN | No | Default `false` |
| last_seen_at | TIMESTAMPTZ | Yes | |

**Indexes:** `idx_devices_user_id`

## sessions

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `users.id` |
| device_id | UUID | Yes | FK → `devices.id` |
| ip_address | INET | Yes | |
| user_agent | VARCHAR(500) | Yes | |
| expires_at | TIMESTAMPTZ | No | |
| revoked_at | TIMESTAMPTZ | Yes | User- or admin-initiated revocation |

**Indexes:** `idx_sessions_user_id`, `idx_sessions_expires_at`

## refresh_tokens

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `users.id` |
| session_id | UUID | No | FK → `sessions.id` |
| token_hash | VARCHAR(255) | No | SHA-256 hash of the token; raw token never persisted |
| expires_at | TIMESTAMPTZ | No | |
| revoked_at | TIMESTAMPTZ | Yes | |
| replaced_by_token_id | UUID | Yes | FK → `refresh_tokens.id`, self-referential (rotation chain) |

**Constraints:** `uq_refresh_tokens_token_hash`
**Indexes:** `idx_refresh_tokens_user_id`

## otp_verifications

Reused across every OTP use case in the product — registration/login, arrival-verification ("Verified Visit"), and the claim-your-listing flow — rather than one-off tables per feature.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | Yes | FK → `users.id`. Null when OTP precedes account creation (registration). |
| phone_country_code | VARCHAR(5) | No | |
| phone_number | VARCHAR(20) | No | |
| purpose | `otp_purpose` | No | |
| code_hash | VARCHAR(255) | No | Hashed OTP code, never stored plaintext |
| attempt_count | SMALLINT | No | Default `0` |
| expires_at | TIMESTAMPTZ | No | |
| verified_at | TIMESTAMPTZ | Yes | |

**Indexes:** `idx_otp_verifications_phone`, `idx_otp_verifications_user_id`

---

# Customer Domain (`customer` schema)

## customer_profiles

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `identity.users.id`, unique (1:1) |
| display_name | VARCHAR(150) | No | |
| avatar_url | VARCHAR(500) | Yes | |

**Constraints:** `uq_customer_profiles_user_id`

## saved_addresses

| Column | Type | Nullable | Notes |
|---|---|---|---|
| customer_id | UUID | No | FK → `customer_profiles.id` |
| label | VARCHAR(50) | Yes | E.g. "Home", "Work" |
| address_line | VARCHAR(500) | No | |
| city | VARCHAR(100) | Yes | |
| region | VARCHAR(100) | Yes | State/Emirate — kept generic, not UAE-specific, per country-agnostic requirement |
| country_code | CHAR(2) | No | ISO 3166-1 alpha-2 |
| latitude | DOUBLE PRECISION | No | |
| longitude | DOUBLE PRECISION | No | |
| is_default | BOOLEAN | No | Default `false` |

**Constraints:** `uq_saved_addresses_customer_default` — partial unique index on `customer_id` WHERE
`is_default = true AND is_active = true`. Defense-in-depth only: the primary correctness mechanism is
transactional (the service layer unsets every other active default for that customer before writing the new
one, on the same session, before this index would ever need to reject a write) — see CUS-002 and ADR-015.

**Indexes:** `idx_saved_addresses_customer_id`; `idx_saved_addresses_location` — GiST, `ll_to_earth(latitude,
longitude)`, added by Story DIR-001 (Sprint 6) per Section 13's spec. Built for AC1's explicit, literal
requirement and forward-looking parity with `service_areas`' own geospatial index; DIR-001's own search query
never queries through this index (its origin point is a raw request lat/lng, never a `saved_addresses` FK — see
`Plan_S06_DIR-001.md` Decision 5) — it exists ready for a future story needing a `saved_addresses`-centered
geospatial query.

## customer_preferences

| Column | Type | Nullable | Notes |
|---|---|---|---|
| customer_id | UUID | No | FK → `customer_profiles.id`, unique (1:1) |
| notification_channel | `notification_channel` | No | Default `whatsapp` |
| language | `language_code` | No | Default `en` |

**Constraints:** `uq_customer_preferences_customer_id`

---

# Provider Domain (`provider` schema)

## providers

The Provider aggregate root — shared columns for both subtypes. `user_id` is nullable to support Google-seeded unclaimed listings, which exist before any owning account claims them (per `13_OPEN_DECISIONS.md` item 3–4).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | Yes | FK → `identity.users.id`, unique when set. Null until claimed for `google_seeded_unclaimed` listings. |
| provider_type | `provider_type` | No | Immutable after creation — a Provider cannot change subtype. |
| display_name | VARCHAR(200) | No | |
| slug | VARCHAR(220) | No | Unique. Used in shareable profile deep links. |
| description | TEXT | Yes | |
| phone_country_code | VARCHAR(5) | Yes | |
| phone_number | VARCHAR(20) | Yes | Shown directly to customers on Contact View — see `contact.contact_views` |
| whatsapp_number | VARCHAR(20) | Yes | |
| listing_source | `listing_source` | No | |
| is_claimed | BOOLEAN | No | Default `false` for `google_seeded_unclaimed`; `true` for `self_registered` |
| claimed_at | TIMESTAMPTZ | Yes | |
| google_place_id | VARCHAR(255) | Yes | Unique when set. Source key for Google-seeded rows, per `13_OPEN_DECISIONS.md` item 3. |
| verification_status | `verification_status` | No | Denormalized cache of the latest `verification.verification_records` row for fast discoverability filtering; source of truth is `verification_records`. Default `pending`. |
| is_discoverable | BOOLEAN | No | Default `false`. Computed at write-time from `verification_status` (mandatory `approved` for Freelancer; configurable for Business — see Section 14) and unclaimed-listing visibility policy. |
| average_rating | NUMERIC(3,2) | Yes | Denormalized from `review.reviews`; recalculated on Review write |
| review_count | INTEGER | No | Default `0` |
| country_code | CHAR(2) | No | ISO 3166-1 alpha-2 — deliberately not hardcoded to UAE |

**`category_label` column — added then dropped:** PRO-001 (Decision 4) had added a temporary
`category_label VARCHAR(100) NOT NULL` free-text column here as a stand-in for the not-yet-built Category
domain. Story PRO-002 (Decision 1) **replaced it**: every existing `category_label` value was backfilled into
the new `provider.provider_category_labels` table (see below, marked `is_primary = true`), and the
`category_label` column was then dropped from `providers` in the same migration
(`272b12ab9b2f_provider_storefront`). `providers` no longer has a `category_label` column — do not reintroduce
it; category labels now live exclusively in `provider_category_labels`.

**Constraints**
- `uq_providers_slug`
- `uq_providers_user_id` (partial, `WHERE user_id IS NOT NULL`)
- `uq_providers_google_place_id` (partial, `WHERE google_place_id IS NOT NULL`)
- `chk_providers_claimed_has_owner`: `is_claimed = false OR user_id IS NOT NULL`
- `chk_providers_discoverable_requires_approved`: `is_discoverable = false OR verification_status = 'approved'`
  — added by Story VER-002 (Sprint 5) as a DB-level defense-in-depth layer for the invariant "a Provider's
  `is_discoverable` can never be true while its cached `verification_status` isn't `approved`" (AC4). Applies
  unconditionally to **both** Provider subtypes, not only Freelancer — approval also sets
  `is_discoverable=true` for Business Providers (see `03_DOMAIN_MODEL.md`/`09_DECISIONS.md` ADR-023 context and
  `Plan_S05_VER-002.md` Decision 5). The primary correctness mechanism is transactional (the same service call
  writes both `verification_status` and `is_discoverable` together, on the same session); this constraint is a
  second, independent, DB-enforced layer, mirroring `uq_saved_addresses_customer_default`'s (CUS-002/ADR-015)
  existing defense-in-depth precedent.

**Indexes:** `idx_providers_provider_type`, `idx_providers_is_discoverable`, `idx_providers_verification_status`, `idx_providers_country_code`

## business_profiles

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id`, unique (1:1) |
| trade_license_number | VARCHAR(100) | Yes | Present only if the chosen verification bar requires it (Section 14) |
| address_line | VARCHAR(500) | No | |
| city | VARCHAR(100) | Yes | |
| region | VARCHAR(100) | Yes | |
| latitude | DOUBLE PRECISION | No | Fixed location |
| longitude | DOUBLE PRECISION | No | |
| operating_hours | JSONB | Yes | Per-weekday open/close; free-form to avoid a rigid schema before hours UX is finalized |
| delivery_radius_meters | INTEGER | Yes | Optional service-delivery radius beyond the fixed location |

**Constraints:** `uq_business_profiles_provider_id`

## freelancer_profiles

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id`, unique (1:1) |
| base_latitude | DOUBLE PRECISION | No | Center point of travel radius |
| base_longitude | DOUBLE PRECISION | No | |
| service_radius_meters | INTEGER | No | |
| skills | TEXT[] | Yes | Free-text skill tags, not a relationship — attribute list |
| years_experience | SMALLINT | Yes | |

**Constraints:** `uq_freelancer_profiles_provider_id`

## provider_availability

Shipped by Story PRO-002, exactly per this spec — no deviation.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id` |
| weekday | `weekday` | No | |
| open_time | TIME | Yes | Null if closed that day |
| close_time | TIME | Yes | |
| is_emergency_available | BOOLEAN | No | Default `false` — urgent/emergency availability flag |

**Constraints:** `uq_provider_availability_provider_weekday (provider_id, weekday)`

`GET /providers/me/availability` always synthesizes exactly 7 entries (one per weekday), treating a missing row
as "closed, not yet configured" — a day being closed is expressed by `open_time`/`close_time` both null, never
by the row's absence for a weekday that has actually been saved as closed.

## portfolios

Shipped by Story PRO-002, exactly per this spec — no deviation. Soft-deleted on removal
(`deleted_at`/`is_active`, Common Columns); the underlying file on disk/storage is deliberately left in place
when a row is soft-deleted — orphaned-file cleanup is a future administrative/retention job.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id` |
| media_url | VARCHAR(500) | No | Always a server-generated, relative `/media/...` URL path — never a raw filesystem path, never derived from the client's original filename (see ADR-017, `06_SECURITY.md`) |
| caption | VARCHAR(255) | Yes | |
| sort_order | SMALLINT | No | Default `0`. Reordered via a dedicated bulk `PUT /providers/me/portfolio/order` endpoint accepting the full ordered set of the caller's own active photo ids. |

**Indexes:** `idx_portfolios_provider_id`

## service_areas

Shipped by Story PRO-002, exactly per this spec — no deviation. Internal-only: no direct API exposes this
table for reading or editing; it is kept in sync automatically by `ProviderService` whenever a provider's
location/radius fields (business fixed location + delivery radius, or freelancer base location + service
radius) are created or edited, in the same flush. PRO-002 deliberately deferred the `cube`/`earthdistance` GiST
index in Section 13 to "the future Search & Matching story that actually queries it" — that story, DIR-001
(Sprint 6), has since shipped the index and is this table's first real query consumer, via a new
`ProviderSearchRepository` (`provider` module) issuing Section 13's exact `earth_box`/`earth_distance` query
shape (recorded as ADR-025/ADR-026 in `09_DECISIONS.md`).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id` |
| center_latitude | DOUBLE PRECISION | No | |
| center_longitude | DOUBLE PRECISION | No | |
| radius_meters | INTEGER | No | Business: derived from fixed location + optional delivery radius. Freelancer: travel radius. |

**Indexes:** `idx_service_areas_provider_id`; `idx_service_areas_location` — GiST, `ll_to_earth(center_latitude,
center_longitude)`, shipped by Story DIR-001 (Sprint 6) exactly per Section 13's pre-existing spec, no deviation
— see Section 13.

## provider_category_labels

**New table, added by Story PRO-002 (Decision 1) — deliberately NOT the `provider_categories` join table
this document's Category Domain section (below) reserves that name for.** The real Category domain
(`category.categories`, `category.category_question_templates`, and the real `provider_categories` join table
with a hard FK to `category.categories.id`) has since shipped via Story `CTG-001` (Sprint 7) — see the Category
Domain section below. `provider_category_labels` remains in place as a distinctly-named interim stand-in: it
stores free-text category labels with no taxonomy validation, satisfying the *structural* shape a provider
having "one or more categories, exactly one primary" requires, without pretending to be the real Category
entity. Reconciling its free-text values into the real `provider_categories` join table (created empty by
`CTG-001`) remains a separate, deliberately deferred follow-up story (`13_OPEN_DECISIONS.md` item 1) — both
tables exist side by side for a transition period.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `providers.id` |
| label | VARCHAR(100) | No | Free-text (e.g. "Plumbing", "AC Repair"), no taxonomy validation |
| is_primary | BOOLEAN | No | Default `false`. Exactly one row per provider should be primary — enforced transactionally at the service layer (delete-existing-then-insert-new, one flush, mirroring `saved_addresses`' default-uniqueness precedent), with the partial unique index below as defense-in-depth. |

**Constraints:** `uq_provider_category_labels_primary` — partial unique index on `provider_id` WHERE
`is_primary = true`.
**Indexes:** `idx_provider_category_labels_provider_id`

Capped at 5 labels per provider (service-layer enforced, not a DB constraint) to prevent unbounded abuse of a
free-text field with no taxonomy gate. Edited only as a full-set replace via `PATCH /providers/me`'s optional
`category_labels` field — never a per-label CRUD surface. This table directly replaces
`providers.category_label` (PRO-001, Decision 4; see the `providers` table section above) — that column was
backfilled into this table and dropped in the same migration that created this table.

**Future reconciliation path:** once the real Category domain ships, a follow-up story is expected to
fuzzy-match/admin-reconcile `provider_category_labels.label` values into real `provider_categories` rows
referencing `category.categories`, and either retire this interim table or keep it as a free-text
fallback/search-boost field alongside the real relationship — that migration design is deliberately deferred,
not decided by PRO-002.

---

# Category Domain (`category` schema)

**Shipped exactly per this section's spec by Story `CTG-001` (Sprint 7, 09 September 2026)** — no deviation. All
three tables below exist via a reversible Alembic migration (`category_domain`,
`backend/alembic/versions/2026_09_09_1000-a804c46bf703_category_domain.py`), and `categories`/
`category_question_templates` are seeded with the full CTO-approved v1 launch taxonomy (14 categories, 47
question templates — `docs/AI/17_CATEGORY_TAXONOMY.md`) via this codebase's first data-seeding migration
(recorded as ADR-028 in `09_DECISIONS.md`). `category.provider_categories` was created **empty** — reconciling
`provider.provider_category_labels` (above) into it remains a separate, deliberately deferred follow-up story;
this section's previous "not yet built" framing no longer applies to any of the three tables themselves. See
`docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md` for the full account.

## categories

| Column | Type | Nullable | Notes |
|---|---|---|---|
| parent_category_id | UUID | Yes | FK → `categories.id`, self-referential, for optional sub-categories |
| name | VARCHAR(100) | No | English |
| name_ar | VARCHAR(100) | Yes | Arabic — nullable only until translation is populated; required before launch per bilingual UI requirement |
| slug | VARCHAR(120) | No | Unique |
| icon_url | VARCHAR(500) | Yes | |
| sort_order | SMALLINT | No | Default `0` |

**Constraints:** `uq_categories_slug`

## category_question_templates

Drives the AI's category-specific follow-up questions. Kept schema-flexible (`options` as JSONB) since the exact question set is the critical-path open decision in `13_OPEN_DECISIONS.md` item 1 and will be edited without code changes.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| category_id | UUID | No | FK → `categories.id` |
| question_text | VARCHAR(500) | No | English |
| question_text_ar | VARCHAR(500) | Yes | Arabic |
| question_type | VARCHAR(30) | No | `text` \| `single_select` \| `multi_select` \| `number` \| `boolean` — VARCHAR, not enum: expected to grow |
| options | JSONB | Yes | Choice list for select types |
| is_required | BOOLEAN | No | Default `true` |
| sort_order | SMALLINT | No | Default `0` |

**Indexes:** `idx_category_question_templates_category_id`

## provider_categories *(join table)*

A Provider belongs to one or more Categories (many-to-many). Not present in the v2.0.0 skeleton — added because the domain model's "one or more Categories" rule cannot be represented by a single FK column.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `provider.providers.id`, part of composite PK |
| category_id | UUID | No | FK → `categories.id`, part of composite PK |
| is_primary | BOOLEAN | No | Default `false`. Exactly one row per provider should be primary — enforced at service layer. |
| created_at | TIMESTAMPTZ | No | |

**Constraints:** `pk_provider_categories (provider_id, category_id)`
**Indexes:** `idx_provider_categories_category_id`

---

# Conversation / AI Intake Domain (`conversation` schema)

**Shipped exactly per this section's spec by Story `AI-001` (Sprint 7, 10 September 2026)** — plus two additive
items, both flagged below and recorded in `09_DECISIONS.md` (ADR-032/ADR-033/ADR-036). All three tables exist via
a reversible Alembic migration (`conversation_domain`,
`backend/alembic/versions/2026_09_10_1000-ef7b7d439f40_conversation_domain.py`). `AI-001` ships a fully
rule-based, deterministic interim `ConversationAiClient` behind a swappable Protocol — no real LLM vendor is
selected yet (`13_OPEN_DECISIONS.md` item 13, open). This story never creates or writes to
`search.search_requests`; see the Search Domain section below for that table's own status. See
`docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md` for the full account.

## conversation_sessions

| Column | Type | Nullable | Notes |
|---|---|---|---|
| customer_id | UUID | No | FK → `customer.customer_profiles.id` |
| category_id | UUID | Yes | FK → `category.categories.id`. Null until the AI has narrowed to a category. |
| status | `conversation_status` | No | Default `active`. Values: `active`, `completed`, `routed_to_admin`, `abandoned` (the last is additive — see the enum table's own note above, added by `AI-001`/ADR-036, set when a customer starts a new session while a previous one is still `active`). |
| final_confidence_score | NUMERIC(4,3) | Yes | Cached latest value from `confidence_scores`; drives Wizard-of-Oz routing |
| structured_criteria | JSONB | Yes | **Additive, `AI-001`/ADR-033.** The AC9 `search_requests`-ready payload (`{category_id, category_slug, answers: [{question_id, question_text, answer_text}]}`), populated only when `status` reaches `completed`, validated via the `StructuredCriteria` Pydantic model before persistence. `NULL` for an active, `routed_to_admin`, or `abandoned` session. Lives entirely inside this schema — `AI-002` (or a later story) reads it to build the actual `search.search_requests` row; this table is never written to from `search`. |
| started_at | TIMESTAMPTZ | No | Default `now()` |
| completed_at | TIMESTAMPTZ | Yes | |

**Indexes:** `idx_conversation_sessions_customer_id`, `idx_conversation_sessions_status`

## messages

The AI intake chat only — not customer-provider messaging, which does not exist in this domain model.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| conversation_session_id | UUID | No | FK → `conversation_sessions.id` |
| sender | `message_sender` | No | |
| content | TEXT | No | |
| sequence_number | INTEGER | No | Ordering within the session |

**Constraints:** `uq_messages_session_sequence` — **partial** unique index on `(conversation_session_id,
sequence_number)` WHERE `is_active = true` (not a plain table-level `UniqueConstraint`), mirroring
`saved_addresses`' `uq_saved_addresses_customer_default` precedent (ADR-015). Required by `AI-001`'s
revise-a-previous-answer flow (ADR-036): a revised answer soft-deletes every later message in the session
(`deleted_at`/`is_active=false`, per this document's own Common Columns soft-delete rule — never a hard `DELETE`
of customer transcript data) rather than hard-deleting it, and the regenerated turn that replaces it must be able
to reuse a soft-deleted row's old `sequence_number` without a constraint conflict. `list_for_session`/
`get_next_sequence_number` (application code) filter `is_active = true` so a soft-deleted message is invisible to
the transcript and never double-counted.
**Indexes:** `idx_messages_conversation_session_id`

## confidence_scores

Append-only log of confidence over the life of a session (a single session may be re-scored as more turns arrive); `conversation_sessions.final_confidence_score` caches the latest value for cheap filtering.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| conversation_session_id | UUID | No | FK → `conversation_sessions.id` |
| score | NUMERIC(4,3) | No | 0.000–1.000 |
| model_version | VARCHAR(50) | Yes | Which LLM/prompt version produced this score |
| computed_at | TIMESTAMPTZ | No | Default `now()` |

**Indexes:** `idx_confidence_scores_session_id`

---

# Search Domain (`search` schema)

Shipped by Story AI-002 (Sprint 7), exactly per this spec, **except four flagged nullable-column deviations**
recorded in the table below and at ADR-038 (`09_DECISIONS.md`) — each resolved the way this codebase resolves
every prior instance of "the locked spec doesn't fit what the real code path can honestly provide": make the
column nullable and report the honest absence, never fabricate a value. `SearchRequestService` is this schema's
sole writer, via one shared `_finalize_matches` helper for both the automated-match path (a `completed`
Conversation Session) and the manual-resolution path (an admin resolving a `routed_to_admin` session's queue
entry, `administration.manual_match_assignments` below) — see ADR-040. `DIR-001`'s `SearchService` remains a
stateless read-layer over `provider` and writes none of these tables (unchanged, ADR-025/ADR-041).

## search_requests

| Column | Type | Nullable | Notes |
|---|---|---|---|
| customer_id | UUID | No | FK → `customer.customer_profiles.id` |
| conversation_session_id | UUID | Yes | FK → `conversation.conversation_sessions.id` |
| category_id | UUID | **Yes** (deviation — was `NOT NULL`) | FK → `category.categories.id`. `NULL` only for a `routed_to_admin` session that reached the AI-Conversation hard turn cap without ever resolving a category (AI-002, ADR-038) — never fabricated. |
| structured_criteria | JSONB | **Yes** (deviation — was `NOT NULL`) | Structured output of the Conversation Session (category-specific answers). `NULL` for a `routed_to_admin` session, which never has a complete, validated answer set (AI-001 Decision 1b/ADR-033; AI-002 ADR-038). |
| customer_latitude | DOUBLE PRECISION | **Yes** (deviation — was `NOT NULL`) | `NULL` if the customer has no default saved address at request time — the row is still created (never blocked), resolving to `unmatched` (AI-002, ADR-038). |
| customer_longitude | DOUBLE PRECISION | **Yes** (deviation — was `NOT NULL`) | Same nullability reasoning as `customer_latitude` (AI-002, ADR-038). |
| status | `search_request_status` | No | |

**Indexes:** `idx_search_requests_customer_id`, `idx_search_requests_created_at`, `idx_search_requests_status`

## provider_matches

The ranked result set of a Search Request against Provider data — explicitly not a Quote and not a booking state machine.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| search_request_id | UUID | No | FK → `search_requests.id` |
| provider_id | UUID | No | FK → `provider.providers.id` |
| rank | SMALLINT | No | 1 = best match |
| match_score | NUMERIC(5,4) | Yes | |

**Constraints:** `uq_provider_matches_request_provider (search_request_id, provider_id)`
**Indexes:** `idx_provider_matches_search_request_id`, `idx_provider_matches_provider_id`

## search_event_log

Every Search Request, matched or not. Feeds provider visibility analytics and admin unmatched-query analytics (`administration.unmatched_query_reports`). Append-only; no soft delete.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| search_request_id | UUID | Yes | FK → `search_requests.id`. Null only if logging happens before a Search Request row is finalized. |
| customer_id | UUID | Yes | FK → `customer.customer_profiles.id` |
| category_id | UUID | Yes | FK → `category.categories.id` |
| query_text | TEXT | Yes | Raw customer query, for admin review |
| result_count | INTEGER | No | Default `0` |
| was_matched | BOOLEAN | No | |
| created_at | TIMESTAMPTZ | No | Default `now()` |

**Indexes:** `idx_search_event_log_created_at`, `idx_search_event_log_was_matched`, `idx_search_event_log_category_id`

---

# Contact Domain (`contact` schema)

## contact_views

Replaces the old Quote/staged-disclosure step entirely: a Contact View shows the Provider's phone number directly and immediately.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| customer_id | UUID | No | FK → `customer.customer_profiles.id` |
| provider_id | UUID | No | FK → `provider.providers.id` |
| search_request_id | UUID | Yes | FK → `search.search_requests.id` |
| viewed_at | TIMESTAMPTZ | No | Default `now()` |

**Indexes:** `idx_contact_views_customer_id`, `idx_contact_views_provider_id`, `idx_contact_views_viewed_at`

Basis for: provider visibility analytics, future pay-per-lead billing (post-MVP, see `11_MVP_SCOPE.md`), and eligibility for Outcome Tag / Review.

**Self-dealing guard (service-layer, not a DB constraint):** since one `identity.users` row may own both a `customer_profiles` row and a `providers` row (see `03_DOMAIN_MODEL.md` Identity & Access), the Contact View creation service must reject the write if `customer_profiles.user_id` (via `customer_id`) equals `providers.user_id` (via `provider_id`) — i.e. a Provider cannot generate a Contact View against their own listing. This can't be a table-level `CHECK` because it requires joining across `customer_profiles` and `providers` through `users`; it must be validated where the row is inserted. Because `outcome_tags` and `reviews` both anchor to `contact_views`, blocking it here transitively blocks self-tagging and self-reviewing too.

## outcome_tags

The platform's only conversion signal.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| contact_view_id | UUID | No | FK → `contact_views.id`, unique (1:1) |
| hired | BOOLEAN | No | "Did you hire them?" |
| submitted_at | TIMESTAMPTZ | No | Default `now()` |

**Constraints:** `uq_outcome_tags_contact_view_id`. Service-layer rule: only the Customer who owns the parent Contact View may submit this row.

## visit_verifications

Backs the "Verified Visit" tag (Section 9 of `00_PROJECT_CONTEXT.md`) — a provider-optional, OTP-based confirmation that they physically attended a job tied to a specific Contact View. Reuses `identity.otp_verifications` rather than a parallel OTP mechanism.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| contact_view_id | UUID | No | FK → `contact_views.id`, unique (1:1) |
| otp_verification_id | UUID | No | FK → `identity.otp_verifications.id` |
| verified_at | TIMESTAMPTZ | No | |

**Constraints:** `uq_visit_verifications_contact_view_id`

---

# Verification Domain (`verification` schema)

## verification_records

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `provider.providers.id` |
| verification_type | `verification_type` | No | `freelancer_id` is mandatory before a Freelancer goes live; `business_license` / `business_lightweight` per the (open) Business verification bar decision |
| status | `verification_status` | No | Default `pending` |
| submitted_at | TIMESTAMPTZ | No | |
| reviewed_at | TIMESTAMPTZ | Yes | |
| reviewed_by | UUID | Yes | FK → `identity.users.id` (Admin) |
| rejection_reason | TEXT | Yes | |

**Indexes:** `idx_verification_records_provider_id`, `idx_verification_records_status`

A trigger or service-layer hook updates `provider.providers.verification_status` (and `is_discoverable`) whenever the latest record here changes status — the `providers` column is a read-optimized cache, this table is the source of truth.

**Enum-reuse note (Story VER-001):** `status` does **not** get its own Postgres enum type scoped to the `verification` schema. It reuses the exact same native `verification_status` enum type `provider.providers.verification_status` already created (Story PRO-002), mapped via `postgresql.ENUM(..., name="verification_status", schema="provider", create_type=False)` in the migration and mirrored at the ORM level (`app/modules/verification/models.py` imports `VerificationStatus` directly from `app.modules.provider.models` — a pure value-enum import, not a service/repository coupling, the same shape ADR-014 already established for `customer` reusing `identity.models.LanguageCode`). This is a deliberate deviation from a naive "colocate every enum in its own domain schema" reading: `verification_records.status` and `providers.verification_status` share the same Postgres enum OID, confirmed against a real database, rather than two identically-valued duplicate types. See `docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md` for the full decision record (this specific mechanism was not significant enough on its own to warrant a dedicated ADR; ADR-018/ADR-019 record this story's two ADR-worthy decisions — the OCR stub Protocol and the private/public storage split).

## verification_documents

| Column | Type | Nullable | Notes |
|---|---|---|---|
| verification_record_id | UUID | No | FK → `verification_records.id` |
| document_type | `document_type` | No | |
| file_url | VARCHAR(500) | No | Stored file reference, not the file itself. As shipped by Story VER-001, this is a **private**, storage-relative reference under a separate, never-mounted `VERIFICATION_UPLOAD_DIR` root — never a public `/media/...` URL (see ADR-019). Clients are never given this raw reference; the API exposes an authenticated, ownership-checked streaming-download endpoint instead. |
| ocr_extracted_data | JSONB | Yes | As shipped by Story VER-001, this is the caller's own **confirmed/edited** field values submitted at the final "submit" step — never the raw output of an actual OCR read. No real Ejari/Emirates ID OCR pipeline exists in this codebase yet; `StubDocumentOcrService` (ADR-018) always returns empty candidate fields, honestly, pending a future story that plugs in a real, confirmed OCR pipeline. |

**Indexes:** `idx_verification_documents_record_id`

Uploaded documents are validated per `06_SECURITY.md` (MIME type, extension, size, unique filename) at the application layer before this row is written.

---

# Review Domain (`review` schema)

## reviews

Anchor-verified: can only exist against a Contact View with a "Yes" Outcome Tag — enforced at the service layer, not purely by a DB constraint (the DB constraint below enforces the anchor *reference*, the "Yes" condition is a service-layer precondition since it must read `outcome_tags.hired` at write time). Since the anchoring Contact View is already rejected for self-dealing at creation time (see `contact_views` above), a Review can never end up pointing back at its own author's Provider.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| contact_view_id | UUID | No | FK → `contact.contact_views.id`, unique (1:1) |
| customer_id | UUID | No | FK → `customer.customer_profiles.id` |
| provider_id | UUID | No | FK → `provider.providers.id` |
| rating | SMALLINT | No | 1–5 |
| comment | TEXT | Yes | |

**Constraints:** `uq_reviews_contact_view_id`, `chk_reviews_rating_range CHECK (rating BETWEEN 1 AND 5)`
**Indexes:** `idx_reviews_provider_id`

## provider_rating_summaries

Denormalized aggregate per Provider, recalculated whenever a Review is written — backs the merit-based ranking algorithm without scanning `reviews` on every search. (Named more precisely than the original "ratings" placeholder in v2.0.0, which this table replaces — a per-review "Rating" sub-entity would just duplicate `reviews.rating`.)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `provider.providers.id`, unique (1:1) |
| average_rating | NUMERIC(3,2) | No | Default `0` |
| review_count | INTEGER | No | Default `0` |
| recalculated_at | TIMESTAMPTZ | No | |

**Constraints:** `uq_provider_rating_summaries_provider_id`

---

# Notification Domain (`notification` schema)

## notifications

Shipped by Story VER-002 (Sprint 5), exactly per this spec, as the Notification domain's first slice — built
with the full `CommonColumnsMixin` (versioned, soft-deletable), not exempted like `audit.audit_logs` (see
`09_DECISIONS.md` ADR-022). Only this table exists so far; `notification_preferences` and
`notification_delivery` (below) remain unbuilt — there is no real WhatsApp/SMS/Email delivery channel to have a
status for, and nothing to opt in/out of yet. Written by `NotificationService.notify_verification_status_change`
on a verification status change (VER-002, AC5), with hardcoded, plain-language `title`/`body` copy — never the
raw `VerificationStatus` enum value.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `identity.users.id` |
| type | VARCHAR(50) | No | `new_lead` \| `verification_status_change` \| `outcome_tag_prompt` \| others — VARCHAR, expected to grow |
| title | VARCHAR(255) | No | |
| body | TEXT | No | |
| related_entity_type | VARCHAR(50) | Yes | E.g. `contact_view`, `verification_record` |
| related_entity_id | UUID | Yes | Polymorphic reference — no FK constraint possible across varying target tables; integrity enforced at service layer |

**Indexes:** `idx_notifications_user_id`, `idx_notifications_created_at`

## notification_preferences

| Column | Type | Nullable | Notes |
|---|---|---|---|
| user_id | UUID | No | FK → `identity.users.id`, unique (1:1) |
| channel | `notification_channel` | No | Default `whatsapp` |
| leads_enabled | BOOLEAN | No | Default `true` |
| verification_enabled | BOOLEAN | No | Default `true` |
| outcome_prompts_enabled | BOOLEAN | No | Default `true` |

**Constraints:** `uq_notification_preferences_user_id`

## notification_delivery

| Column | Type | Nullable | Notes |
|---|---|---|---|
| notification_id | UUID | No | FK → `notifications.id` |
| channel | `notification_channel` | No | |
| status | VARCHAR(20) | No | `pending` \| `sent` \| `delivered` \| `failed` |
| provider_message_id | VARCHAR(255) | Yes | External provider's (e.g. Twilio, WhatsApp Business API) message ID |
| sent_at | TIMESTAMPTZ | Yes | |
| delivered_at | TIMESTAMPTZ | Yes | |
| failure_reason | TEXT | Yes | |

**Indexes:** `idx_notification_delivery_notification_id`

---

# Administration Domain (`administration` schema)

## admin_action_log

Shipped by Story VER-002 (Sprint 5), exactly per this spec, as the Administration domain's first slice — built
with the full `CommonColumnsMixin` (versioned, soft-deletable), a deliberate, spec-literal choice **not** to
exempt it the way the immutable `audit.audit_logs` is exempted (see `09_DECISIONS.md` ADR-021 for the full
reasoning). Written by `AdminActionLogService.record_verification_review` on every admin approve/reject action
(AC6) — `metadata` carries `provider_id` and, for a rejection, `rejection_reason`, since `target_entity_id` is a
single polymorphic reference and cannot itself hold a second id. `claim_review_requests` (below) has since shipped
alongside it as the Administration domain's second slice (Story CLM-001, Sprint 6); `manual_match_assignments`
(below) has since shipped as its third slice (Story AI-002, Sprint 7); `unmatched_query_reports`, `feature_flags`,
and `system_settings` (below) remain unbuilt.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| admin_user_id | UUID | No | FK → `identity.users.id` |
| action_type | VARCHAR(100) | No | |
| target_entity_type | VARCHAR(50) | Yes | |
| target_entity_id | UUID | Yes | Polymorphic — no FK constraint |
| metadata | JSONB | Yes | |

**Indexes:** `idx_admin_action_log_admin_user_id`, `idx_admin_action_log_created_at`

## manual_match_assignments

Wizard-of-Oz fallback for low-confidence Conversation Sessions. Shipped by Story AI-002 (Sprint 7) — a pull-based
admin queue (no push-notification recipient concept exists anywhere in this codebase, `ADR-030`), the fourth
application of the passive-queue-row pattern (`admin_action_log`/`claim_review_requests` before it), with an
atomic conditional-`UPDATE` resolution guard (`ManualMatchAssignmentRepository.try_resolve`, mirroring
`try_claim_for_account`/`try_claim_for_review`) — see `09_DECISIONS.md` ADR-039.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| conversation_session_id | UUID | No | FK → `conversation.conversation_sessions.id` |
| search_request_id | UUID | Yes | FK → `search.search_requests.id` |
| assigned_admin_id | UUID | **Yes** (deviation — was `NOT NULL`) | FK → `identity.users.id`. `NULL` while `status = pending` (an unassigned queue — any admin may pick up); populated only at resolution with the admin who resolved it, mirroring `claim_review_requests.reviewed_by`'s nullable-until-resolved shape (`ADR-030`'s own prior finding on this exact column, now actually built; AI-002 ADR-038). |
| status | VARCHAR(20) | No | `pending` \| `completed` |
| completed_at | TIMESTAMPTZ | Yes | |

**Indexes:** `idx_manual_match_assignments_status`

## claim_review_requests

Shipped by Story CLM-001 (Sprint 6) — the AC6 admin-fallback queue for a Google-seeded-unclaimed-listing claim
attempt that failed OTP verification or found no usable public phone number. Genuinely new schema, not previously
specified anywhere in this document prior to CLM-001; built directly by analogy to `unmatched_query_reports`'s
already-established shape below (a physical, writable, durable admin-review-queue table, not a DB view or a
fire-and-forget notification), with the full `CommonColumnsMixin` (versioned, soft-deletable), matching
`admin_action_log`'s own precedent of using the full mixin rather than being exempted like `audit_logs`. Written
by `ClaimReviewRequestService.create` (`ClaimService.request_admin_review`, AC6); resolved via
`ClaimReviewRequestService.resolve`, called by `AdminClaimService.approve_review_request`/`reject_review_request`
(admin-facing, `/admin/claims`, no dashboard UI — backend-API-only, per VER-002's established precedent). See
`09_DECISIONS.md` ADR-030 for the full design reasoning.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `provider.providers.id` |
| claimant_user_id | UUID | No | FK → `identity.users.id` — who was attempting to claim |
| reason | VARCHAR(30) | No | `otp_failed` \| `no_public_number` |
| status | VARCHAR(20) | No | `open` \| `resolved`. Default `open`. |
| resolution | VARCHAR(20) | Yes | `approved` \| `rejected`, set only when `status=resolved` |
| resolution_notes | TEXT | Yes | |
| reviewed_by | UUID | Yes | FK → `identity.users.id` (Admin) |
| reviewed_at | TIMESTAMPTZ | Yes | |

**Indexes:** `idx_claim_review_requests_provider_id`, `idx_claim_review_requests_status`

## unmatched_query_reports

Admin-facing view over `search.search_event_log` entries where `was_matched = false`, with admin annotation/workflow state attached — kept as a physical table (not a DB view) because admin review status must be writable and durable.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| search_event_log_id | UUID | No | FK → `search.search_event_log.id`, unique (1:1) |
| category_gap_notes | TEXT | Yes | |
| status | VARCHAR(20) | No | `open` \| `reviewed` \| `actioned`. Default `open`. |
| reviewed_by | UUID | Yes | FK → `identity.users.id` |
| reviewed_at | TIMESTAMPTZ | Yes | |

**Constraints:** `uq_unmatched_query_reports_search_event_log_id`

## feature_flags

| Column | Type | Nullable | Notes |
|---|---|---|---|
| key | VARCHAR(100) | No | Unique |
| is_enabled | BOOLEAN | No | Default `false` |
| description | TEXT | Yes | |

**Constraints:** `uq_feature_flags_key`

## system_settings

| Column | Type | Nullable | Notes |
|---|---|---|---|
| key | VARCHAR(100) | No | Unique |
| value | JSONB | No | |
| description | TEXT | Yes | |

**Constraints:** `uq_system_settings_key`

---

# Audit Domain (`audit` schema)

## audit_logs

Immutable — no `updated_at`, `deleted_at`, `is_active`, or `version`. Rows are never updated or deleted, including by administrators, per `06_SECURITY.md`.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| actor_user_id | UUID | Yes | FK → `identity.users.id`. Null for system-initiated actions. |
| action | VARCHAR(100) | No | E.g. `login`, `password_reset`, `verification_status_change` |
| entity_type | VARCHAR(50) | No | |
| entity_id | UUID | Yes | |
| before_state | JSONB | Yes | |
| after_state | JSONB | Yes | |
| ip_address | INET | Yes | |
| created_at | TIMESTAMPTZ | No | Default `now()` |

**Indexes:** `idx_audit_logs_actor_user_id`, `idx_audit_logs_entity_type_entity_id`, `idx_audit_logs_created_at`

---

# Relationships (Summary)

```
users (identity)
│
├── customer_profiles (1:1, optional)
│     ├── saved_addresses (1:N)
│     ├── customer_preferences (1:1)
│     ├── conversation_sessions (1:N)
│     ├── search_requests (1:N)
│     ├── contact_views (1:N, as customer)
│     └── reviews (1:N, as customer)
│
├── providers (1:1, optional — null user_id until claimed)
│     ├── business_profiles / freelancer_profiles (1:1, by provider_type)
│     ├── provider_categories (N:M → categories)
│     ├── provider_availability (1:N)
│     ├── portfolios (1:N)
│     ├── service_areas (1:N)
│     ├── verification_records (1:N) → verification_documents (1:N)
│     ├── claim_review_requests (1:N, optional — a still-unclaimed Google-seeded listing's failed claim attempts)
│     ├── contact_views (1:N, as target)
│     ├── reviews (1:N, as target)
│     └── provider_rating_summaries (1:1)
│
├── devices (1:N)
├── sessions (1:N) → refresh_tokens (1:N)
├── otp_verifications (1:N)
└── notifications (1:N) → notification_delivery (1:N)

conversation_sessions
├── messages (1:N)
├── confidence_scores (1:N)
└── search_requests (1:1, optional)

search_requests
├── provider_matches (1:N → providers)
└── contact_views (1:N)

contact_views
├── outcome_tags (1:1, optional)
├── visit_verifications (1:1, optional)
└── reviews (1:1, optional — requires a "Yes" outcome_tag)

search_event_log
└── unmatched_query_reports (1:1, optional, where was_matched = false)
```

---

# Explicitly Excluded Tables

Per `03_DOMAIN_MODEL.md` ("Explicitly Out of Scope") and `11_MVP_SCOPE.md` Section 6, the following must **not** be created unless the MVP scope is formally amended in `13_OPEN_DECISIONS.md`:

- `quotes`, `quote_status_history`, or any RFQ→Quote state machine table
- `message_threads` / `chat_messages` between Customer and Provider (the only chat is `conversation.messages`, the AI intake — not P2P messaging)
- `payments`, `transactions`, `escrow_accounts`, `payouts`
- `pricing_rules` / dynamic pricing tables
- `loyalty_programs`, `subscriptions`, `disputes`
- `masked_phone_numbers` / call-proxy tables, contact-info-detection tables — later-phase anti-circumvention hardening only

---

# Soft Delete

Business entities use soft delete via `deleted_at` + `is_active` (Common Columns). Records are never permanently removed during normal operations. Permanent deletion is an administrative operation, logged in `audit.audit_logs`.

`audit.audit_logs` and `search.search_event_log` are append-only and exempt from soft delete — they are immutable historical records by design, not mutable business entities.

---

# Transactions

Every business operation must execute inside a database transaction. Examples:

- User registration (`users` + `user_roles` + `customer_profiles` or `providers` in one transaction)
- Search Request submission (`search_requests` + `search_event_log` + `provider_matches`)
- Contact View creation (`contact_views`, plus the `providers` visibility-analytics read path)
- Verification status change (`verification_records` update + `providers.verification_status`/`is_discoverable` cache update, in the same transaction)
- Outcome Tag / Review submission (`outcome_tags` or `reviews` + `provider_rating_summaries` recalculation)

Partial writes are prohibited.

---

# Indexing Strategy

Indexes exist for: foreign keys, frequently filtered columns, search columns, sorting columns, and authentication lookups. Every foreign key column listed above gets a supporting index unless already covered by a unique constraint on the same column. Additional examples beyond the per-table lists:

```
identity.users.email
identity.users.phone_number
provider.provider_categories.category_id
provider.service_areas (geospatial — see Section 13)
search.search_requests.created_at
search.search_requests.status
```

---

# Section 13 — Geospatial Query Strategy

Location + service-area matching (core to the product, per `00_PROJECT_CONTEXT.md` Section 1) is not covered by any extension in the currently approved stack (`12_TECH_STACK.md` lists PostgreSQL FTS for Phase 1 and vector search for Phase 3, but no geospatial extension). Naive `lat/long` range filtering with plain B-tree indexes does not scale past a small provider count.

**Shipped exactly per this spec by Story DIR-001 (Sprint 6, 09 September 2026) — confirmed, not merely
recommended.** Uses PostgreSQL's built-in `cube` and `earthdistance` contrib extensions (ship with core
PostgreSQL, no new package-approval overhead) to build a GiST index over each provider's location:

```
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;

CREATE INDEX idx_service_areas_location
  ON provider.service_areas
  USING gist (ll_to_earth(center_latitude, center_longitude));
```

DIR-001's migration additionally created a matching `idx_saved_addresses_location` GiST index on
`customer.saved_addresses` (`ll_to_earth(latitude, longitude)`) for forward-looking parity — not queried by
DIR-001's own search (its origin point is always a raw request lat/lng, never a `saved_addresses` FK), but ready
for a future story that needs a `saved_addresses`-centered geospatial query. Both indexes were verified via a
dedicated `EXPLAIN (FORMAT JSON)` test at representative data volume (≥1,000 seeded `service_areas` rows) to
confirm the Postgres planner genuinely chooses an `Index Scan`/`Bitmap Index Scan` over a sequential scan, not
merely that the index exists. `DROP EXTENSION` is deliberately never run on migration downgrade (extensions are
shared, low-risk-to-leave, high-risk-to-drop if anything else depends on them) — only the two indexes are
dropped.

This supports "providers within N meters of point (lat, lng)" queries efficiently without introducing PostGIS as a new approved dependency. The actual query issued against this index — `earth_box` GiST-indexed containment narrowing candidates before an exact `earth_distance` recheck, `ORDER BY distance ASC, id ASC` for deterministic tie-breaking — lives in `backend/app/modules/provider/repositories/provider_search_repository.py`, this codebase's first use of raw parameterized `sqlalchemy.text()` SQL (recorded as ADR-026 in `09_DECISIONS.md`, since `earth_box`/`earth_distance`/`ll_to_earth` have no SQLAlchemy ORM/Core expression-language mapping). If richer geospatial needs emerge later (polygon zones, routing), evaluate PostGIS at that point and record the decision in `09_DECISIONS.md`.

---

# Section 14 — Schema Flexibility Against Open Decisions

Several `13_OPEN_DECISIONS.md` items are still unresolved. This schema is built so each resolves without a breaking migration:

| Open Decision | Schema accommodation |
|---|---|
| 1. Category Taxonomy | `categories` is self-referential and freely insertable; `category_question_templates.options` is JSONB — new categories/questions are data changes, not migrations |
| 3. Google Places Data legal review | `providers.listing_source` + `google_place_id` already model the seeded/unclaimed state; if legal review forces deletion of imported data, `listing_source = 'google_seeded_unclaimed'` rows are the exact filter needed |
| 4. Unclaimed Listing UX | `providers.is_claimed` / `is_discoverable` are independent flags — "hidden until claimed" vs. "shown with an unclaimed label" is a query-time filter on existing columns, not a schema change |
| 5. Business Verification Bar | `verification_type` enum already includes both `business_license` and `business_lightweight`; which one is required is an application-config decision, not a schema decision |
| 9. Launch Market Confirmation | No table hardcodes UAE. `country_code` (ISO 3166-1) appears wherever geography matters instead of an implicit default |

---

# Data Validation

Validation occurs at multiple layers:

1. Flutter
2. API Validation (Pydantic v2)
3. Service Layer
4. Database Constraints

The database is the final authority.

---

# Caching Strategy

Redis stores: sessions, refresh tokens, rate limits, frequently accessed configuration, and frequently accessed category/provider data. Redis is never the source of truth; PostgreSQL remains authoritative.

---

# Search Strategy

**Phase 1:** PostgreSQL Full Text Search over `provider.providers` (name/description) and `category.categories`, plus the geospatial index in Section 13.

**Phase 3:** Vector search, planned for semantic matching of the Conversation/AI Intake layer against Provider data — see `00_PROJECT_CONTEXT.md` Section 3. Will likely require a `provider_embeddings` table (`provider_id`, `embedding VECTOR(n)`, `model_version`) via `pgvector` — not yet an approved extension; requires a future ADR.

---

# Backup Strategy

**Production:** daily full backup, hourly incremental backup, point-in-time recovery, cross-region backup.

**Development:** local database dumps, seed data, migration scripts.

---

# Migration Strategy

Schema changes are managed exclusively through Alembic. Rules:

- Never modify production databases manually.
- Every schema change requires a migration.
- Every migration must support rollback where practical.
- Each domain's tables in this document should map to one Alembic migration per domain (e.g. `identity`, then `customer`, then `provider`, …) in dependency order, mirroring the Sprint 2+ build sequence in `11_MVP_SCOPE.md` Section 3, rather than one monolithic migration.

---

# Performance Guidelines

- Avoid `SELECT *`
- Use pagination
- Optimize joins
- Minimize N+1 queries
- Create indexes only where justified
- Profile slow queries
- Batch database operations when possible

---

# Security Guidelines

- Parameterized queries only (SQLAlchemy ORM)
- No dynamic SQL
- Encrypt sensitive data at rest
- Store password hashes only (Argon2id) — and only for the `email_password` admin path; Customer/Provider accounts never have a password
- Never store plaintext secrets or plaintext OTP codes
- Apply least privilege database access per schema

---

# Database Growth Strategy

**Current architecture:** single PostgreSQL instance, schema-per-domain.

**Future options:** read replicas, connection pooling, table partitioning (`audit.audit_logs` and `search.search_event_log` are the first partitioning candidates by `created_at`, given unbounded append-only growth), archive tables, independent databases after service extraction.

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
- 11_MVP_SCOPE.md
- 13_OPEN_DECISIONS.md
- 14_USER_FLOWS.md

---

**End of Document**
