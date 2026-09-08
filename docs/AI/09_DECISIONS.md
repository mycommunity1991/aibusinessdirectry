# AI Marketplace Architecture Decision Log

**Document ID:** AI-09  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO  
**Audience:** Engineering Team, Product Team, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document records all significant architectural, technical, and engineering decisions made throughout the AI Marketplace project (decisions predating the product's rename from "MyCommunity" are kept verbatim below, per the append-only rule).

Every major decision must be documented here before implementation.

This document serves as the historical record explaining **why** decisions were made.

This document is append-only.

Existing decisions must never be modified or removed. If a decision changes, create a new decision entry referencing the previous one.

---

# Decision Status

A decision can have one of the following statuses:

- Proposed
- Accepted
- Superseded
- Deprecated
- Rejected

---

# Decision Template

```
Decision ID:

Title:

Date:

Status:

Owner:

Context

Decision

Alternatives Considered

Consequences

Related Documents
```

---

# ADR-001

## Title

Adopt Modular Monolith Architecture

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The platform is initially developed by a small engineering team and requires rapid delivery while remaining scalable.

### Decision

Adopt a Modular Monolith architecture.

Business modules remain independent and communicate through well-defined service interfaces.

### Alternatives Considered

- Traditional Monolith
- Microservices
- Serverless

### Consequences

- Faster development
- Lower operational complexity
- Easier debugging
- Future migration to microservices remains possible

### Related Documents

- 02_ARCHITECTURE.md

---

# ADR-002

## Title

Use Flutter for Mobile Development

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The platform requires both Android and iOS support while maintaining a single codebase.

### Decision

Use Flutter as the mobile framework.

### Alternatives Considered

- React Native
- Native Android + Native iOS

### Consequences

- Single codebase
- Faster feature delivery
- Native performance
- Lower maintenance cost

### Related Documents

- 02_ARCHITECTURE.md
- 07_UI_GUIDELINES.md

---

# ADR-003

## Title

Use FastAPI for Backend Development

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The backend requires excellent API performance, strong typing, asynchronous support, and rapid development.

### Decision

Use Python with FastAPI.

### Alternatives Considered

- Django
- Node.js (NestJS)
- ASP.NET Core

### Consequences

- High developer productivity
- Excellent OpenAPI support
- Modern asynchronous architecture
- Strong ecosystem

### Related Documents

- 02_ARCHITECTURE.md

---

# ADR-004

## Title

Use PostgreSQL as Primary Database

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The application requires ACID compliance, relational modeling, advanced indexing, and long-term scalability.

### Decision

Use PostgreSQL as the primary database.

### Alternatives Considered

- MySQL
- MongoDB
- SQL Server

### Consequences

- Excellent relational capabilities
- Strong indexing
- JSON support
- Mature ecosystem

### Related Documents

- 04_DATABASE.md

---

# ADR-005

## Title

Use Redis for Caching and Temporary Data

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

Certain data requires fast retrieval and temporary storage.

### Decision

Use Redis for:

- Cache
- Sessions
- Rate limiting
- Temporary data
- Background processing support

### Alternatives Considered

- Memcached
- Database caching

### Consequences

- Faster response times
- Reduced database load
- Better scalability

### Related Documents

- 04_DATABASE.md

---

# ADR-006

## Title

Separate Website and Application Repositories

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The marketing website and application have different lifecycles, deployment strategies, and technology stacks.

### Decision

Maintain two independent repositories.

Repository 1

```
mycommunity-app
```

Repository 2

```
mycommunity-website
```

### Alternatives Considered

Single repository

### Consequences

- Independent deployments
- Cleaner CI/CD
- Easier collaboration
- Better separation of responsibilities

### Related Documents

- 00_PROJECT_CONTEXT.md

---

# ADR-007

## Title

Adopt Feature-First Flutter Architecture

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The mobile application will continue to grow significantly over time.

### Decision

Organize Flutter code by feature rather than by technical layer.

### Alternatives Considered

Layer-based architecture

### Consequences

- Better maintainability
- Easier onboarding
- Better scalability

### Related Documents

- 02_ARCHITECTURE.md
- 07_UI_GUIDELINES.md

---

# ADR-008

## Title

Use UUID as Primary Keys

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The application requires globally unique identifiers and secure public resource identifiers.

### Decision

All primary keys use UUID.

### Alternatives Considered

Auto-increment integers

### Consequences

- Better scalability
- Improved security
- Easier future service extraction

### Related Documents

- 04_DATABASE.md

---

# ADR-009

## Title

Use JWT Authentication

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

The mobile application requires stateless authentication.

### Decision

Use:

- JWT Access Token
- Refresh Token

### Alternatives Considered

- Cookie Sessions
- OAuth-only

### Consequences

- Mobile friendly
- Stateless APIs
- Better scalability

### Related Documents

- 05_API_GUIDELINES.md
- 06_SECURITY.md

---

# ADR-010

## Title

Adopt AI-Driven Development Standards

**Date**

2026-07-03

**Status**

Accepted

**Owner**

CTO

### Context

AI assistants are first-class contributors throughout the project lifecycle.

### Decision

Maintain an AI knowledge base under:

```
docs/AI/
```

All AI-generated code must follow the documented architecture, standards, and guidelines.

### Alternatives Considered

No centralized AI documentation

### Consequences

- Consistent AI output
- Faster development
- Reduced architectural drift
- Improved onboarding

### Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 08_CODING_STANDARDS.md

---

# ADR-011

## Title

Product Pivot and Rename: MyCommunity → AI Marketplace

**Date**

2026-07-14

**Status**

Accepted

**Owner**

CTO / Founder

### Context

The product concept changed from a UAE-first verified resident/community platform (Community, Feed, Events, Moderation modules) to a location-based directory and AI-mediated conversational-intake marketplace connecting businesses and freelancers with customers. There is no Community, Feed, Events, or Messaging domain in the current model — see `00_PROJECT_CONTEXT.md` Section 11 for the full product changelog and `03_DOMAIN_MODEL.md` for the current domain boundaries.

### Decision

Rename the product from "MyCommunity" to "AI Marketplace" (working title — final name is still an open decision, see `13_OPEN_DECISIONS.md` item 8) and update all forward-looking documentation, code identifiers, and infrastructure naming (backend app title, Flutter project/package identifiers, local database/role names) to match.

Prior ADR entries in this log that reference "MyCommunity" or the old repository names (e.g. ADR-006's `mycommunity-app` / `mycommunity-website`) are historical record and are not rewritten. Where a new repository or package name is needed going forward, it should follow the `ai_marketplace` / `ai-marketplace` convention until a final product name is locked.

### Alternatives Considered

- Leave historical naming in place and only rename net-new code (rejected — leaves the codebase in a permanently inconsistent, confusing state for both engineers and AI assistants)
- Rewrite historical ADR entries in place (rejected — violates this document's own append-only rule)

### Consequences

- All docs under `docs/AI/` now consistently describe the AI Marketplace domain
- Backend app title, Flutter project name/org, and local Postgres database/role were renamed to match
- Historical ADRs, sprint records, and implementation-story logs keep their original "MyCommunity" wording as a historical record, since they describe work already completed under that name

### Related Documents

- 00_PROJECT_CONTEXT.md
- 03_DOMAIN_MODEL.md
- 13_OPEN_DECISIONS.md

---

# ADR-012

## Title

Small, Single-Owner-Scoped Collection Endpoints May Omit Pagination

**Date**

2026-09-05

**Status**

Accepted

**Owner**

CTO

### Context

`05_API_GUIDELINES.md` states, without carve-out, that "all collection endpoints must support pagination."
Story AUTH-003 introduced `GET /api/v1/auth/sessions`, which lists only the calling user's own active
sessions — a collection that is inherently small and bounded by the number of real devices a person actually
owns and signs in from (never "thousands," unlike a business/provider directory listing or a search-results
endpoint). The endpoint was shipped unpaginated, a deliberate and documented deviation flagged during
planning and implementation, not a silent omission. The `architect` agent reviewed the deviation during
AUTH-003's story review and agreed the underlying reasoning was sound, but noted that a deviation from a
documented "must" needs a formal record, not just an inline code comment and a Plan paragraph, so it isn't
re-litigated the next time a similarly-shaped endpoint is built.

### Decision

A collection endpoint may omit pagination when both of the following hold:

- The collection is scoped to a single owner (e.g. the calling user's own resources), not a shared or
  platform-wide collection.
- The collection's cardinality is inherently small and bounded by a real-world constraint on the owner side
  (e.g. the number of devices a person plausibly owns), not by data volume that grows with platform usage or
  time.

`GET /api/v1/auth/sessions` (Story AUTH-003) is the first endpoint this applies to. This is a narrow
exception to `05_API_GUIDELINES.md`'s blanket pagination rule, not a general license to skip pagination —
any endpoint returning a platform-wide, shared, or unbounded-growth collection (business/provider listings,
search results, reviews, notifications, etc.) must still paginate per the existing rule. When in doubt,
default to pagination; this exception is for cases where pagination would be unnecessary complexity with no
real benefit, consistent with `08_CODING_STANDARDS.md`'s "avoid unnecessary abstractions" principle.

### Alternatives Considered

- Paginate `GET /sessions` anyway for blanket consistency with `05_API_GUIDELINES.md` (rejected — adds
  complexity with no realistic benefit for a collection that will essentially never exceed single-digit to
  low-double-digit rows per user).
- Leave the deviation as an inline code comment only, without a formal ADR (rejected per `architect`'s
  review — a documented "must" being deviated from needs a recorded decision, not just a comment that could
  be lost or contradicted by a future, uninformed implementer).

### Consequences

- Future stories building a similarly-shaped small, single-owner-scoped collection endpoint may cite this
  ADR to omit pagination without re-deriving the reasoning from scratch.
- `05_API_GUIDELINES.md`'s pagination rule remains the default for every other collection endpoint; this ADR
  narrows it only for the specific shape described above.

### Related Documents

- 05_API_GUIDELINES.md
- 08_CODING_STANDARDS.md
- docs/implementation/plans/Plan_S02_AUTH-003.md
- docs/implementation/walkthroughs/Walkthrough_S02_AUTH-003.md

---

# ADR-013

## Title

Test Suite Bypasses Alembic — Schemas Created Directly via `Base.metadata.create_all`/`drop_all`

**Date**

2026-09-06

**Status**

Accepted

**Owner**

CTO

### Context

`04_DATABASE.md`'s Migration Strategy section states schema changes are "managed exclusively through
Alembic." That is true for how any real database (dev, staging, production) reaches a given schema state —
but it does not describe how the backend's own pytest suite gets there. Since Sprint 1, `backend/tests/conftest.py`'s
function-scoped `db_engine` fixture has created every domain schema and table directly via SQLAlchemy's
`Base.metadata.create_all`, and torn them down via `Base.metadata.drop_all` plus `DROP SCHEMA ... CASCADE`, at
the start/end of every single test — never invoking Alembic at all. Story AUTH-004 extended this same fixture,
in kind, to also cover the new `audit` schema, and in doing so both the `tester` and `architect` agents
independently investigated *why* — confirming this is a genuine structural necessity, not a shortcut: the
shared `ai_marketplace_test` database has an `alembic_version` table that is out of sync with the real
migration chain, and running `alembic upgrade head` directly against it would only make that worse, because
the suite's own per-test teardown (`DROP SCHEMA ... CASCADE`) would immediately delete the migrated schemas on
the very next test run while leaving `alembic_version` still claiming `head` — an actively self-desyncing
combination, not merely stale bookkeeping. This trade-off previously lived only in a fixture's docstring and
in two agents' independent investigative write-ups during AUTH-004's review — not written down anywhere in
`docs/AI/`, which meant every future engineer/agent extending the fixture to a new domain schema would have to
re-derive the same reasoning from scratch.

### Decision

The backend's automated test suite (`backend/tests/conftest.py` and any fixture built on the same pattern)
creates and tears down its own schema/table structure directly via SQLAlchemy metadata operations
(`Base.metadata.create_all`/`drop_all`), independently of Alembic, for every test run. This is deliberate and
correct for the test suite specifically — it is not a statement that migrations are optional or that the
Alembic chain is unreliable for real deployments. Migration reversibility (`upgrade head` → `downgrade -1` →
`upgrade head` → `downgrade base`) continues to be verified manually against a disposable scratch database
per story (never the shared `ai_marketplace`/`ai_marketplace_test` databases), as has been done for every
migration-adding story since AUTH-001.

Every future domain module's test fixtures should follow this same pattern (import the new module's models so
its tables are included in `Base.metadata`, add its schema to the same create/drop lifecycle) rather than
attempting to invoke Alembic inside the test suite.

### Alternatives Considered

- Run `alembic upgrade head` against the shared `ai_marketplace_test` database once, outside the test loop
  (rejected — the suite's own per-test teardown drops schemas via `metadata.drop_all` regardless of
  `alembic_version`'s state, so this would desync `alembic_version` from reality on the very next test run;
  confirmed by directly inspecting the shared test DB).
- Stand up a dedicated, Alembic-migrated, long-lived test database that the suite never tears down (rejected
  as out of scope for this ADR — a bigger tooling investment than the story that surfaced this question
  warranted; may be revisited later if the fixture's current approach becomes a real bottleneck).

### Consequences

- Test-suite schema setup and real-database schema setup are two genuinely different code paths by design;
  this must not be read as evidence that a story can skip writing a real, reversible Alembic migration —
  every story that changes the schema still needs one, verified independently against a scratch database.
- Future engineers/agents extending `conftest.py`'s fixtures for a new domain module can cite this ADR instead
  of re-deriving the reasoning, and should follow the same pattern rather than introducing a second,
  inconsistent test-DB strategy.

### Related Documents

- 04_DATABASE.md
- docs/implementation/plans/Plan_S02_AUTH-004.md
- docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md

---

# ADR-014

## Title

Cross-Module Provisioning Trigger via Direct Service Injection — `identity → customer`

**Date**

2026-09-06

**Status**

Accepted

**Owner**

CTO

### Context

Story CUS-001 needed every newly registered account (via mobile OTP, AUTH-001, or Google/Apple sign-in,
AUTH-002) to also get a `customer_profiles` row and a `customer_preferences` row, created in the same database
transaction as the `User` row — never as a separate, possibly-failing follow-up call. `identity`'s registration
services (`AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth`) already had an explicit
`is_new_user` branch and a single, well-understood transaction boundary (one `await db.commit()` per endpoint,
after the service call returns), but no existing mechanism for one module to trigger another module's
provisioning logic within that same transaction. Story AUTH-004 had already established exactly this shape for
a different purpose: `AuthService` takes `AuditService` (a different module's service) as a constructor
dependency and calls it inline, flush-only, on the same request-scoped session — a one-directional
`identity → audit` dependency with zero cycle risk, since `audit`'s models/repositories/services import
nothing from `identity` (only a plain `user_id: uuid.UUID`, never a `User` object).

### Decision

`AuthService` gains a second cross-module service dependency, `customer_service: CustomerService`, wired via
`identity/dependencies.py`'s `get_auth_service()` (`Depends(get_customer_service)`), in the identical shape as
the existing `Depends(get_audit_service)` line. Both `verify_otp_and_authenticate` and `authenticate_with_oauth`
call `await self.customer_service.provision_default_profile(user_id=user.id, accept_language_header=...)`
inline inside their existing `if is_new_user:` blocks, on the same `AsyncSession` already in use — flush only,
never a nested commit. The endpoint's single, pre-existing `db.commit()` remains the only transaction boundary,
so the `User` row and the new `customer_profiles`/`customer_preferences` rows either all land together or none
do.

Dependency direction is deliberately one-directional: `customer`'s code has zero imports from `identity`'s
services or repositories anywhere — only a plain FK-by-string to `identity.users.id` (via the pre-existing
`CommonColumnsMixin` convention) and a reuse of `identity.models.LanguageCode` (a pure value enum, not a
service or ORM-mapped class). This is not a new architectural pattern being introduced for CUS-001 — it is a
second, independent application of the same pattern AUTH-004 already established and had reviewed. Any future
story that needs one module to trigger another module's same-transaction provisioning logic on a shared
lifecycle event (e.g. a future Notification-domain default-preferences row on registration) should default to
this same shape rather than re-deriving a new mechanism.

### Alternatives Considered

- **SQLAlchemy `after_insert` ORM event listener** registered by `customer` on `identity.User` (rejected — the
  language default needs the `Accept-Language` HTTP header, which is invisible to a low-level ORM mapper
  event; it also makes the trigger implicit and untraceable from `AuthService` itself, violating this
  project's "prefer explicit code over implicit behavior" rule; and it still requires `customer` to import
  `identity`'s mapped `User` class at import time — a worse, "spooky action at a distance" coupling, for no
  atomicity benefit over direct injection).
- **Domain event** (`CustomerRegistered`, named in `03_DOMAIN_MODEL.md`'s Domain Events list) via an in-process
  event bus (rejected — no event-bus infrastructure exists anywhere in this codebase today; building one
  solely for this single call site is the kind of premature abstraction `08_CODING_STANDARDS.md` warns
  against, and a synchronous, same-transaction event handler would be functionally identical to direct
  injection with an extra indirection layer and no isolation benefit).

### Consequences

- `identity` now has two outgoing cross-module service dependencies (`audit`, `customer`), both following the
  identical constructor-injection, flush-only, same-session shape — a consistent, repeatable pattern rather
  than two different mechanisms for a similar problem.
- Future modules needing to react to a registration (or other shared lifecycle) event within the same
  transaction should default to this pattern; a domain-event bus remains a legitimate option to revisit only if
  a genuinely independent, decoupled subscriber count grows large enough to justify the infrastructure
  investment — not before.
- `customer`'s own code must continue to have zero imports from `identity`'s services/repositories to keep the
  dependency one-directional and cycle-free; any future PR that would import an `identity` service into
  `customer` (or vice versa in a way that would create a cycle) should be treated as a design smell, not a
  quick fix.

### Related Documents

- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 04_DATABASE.md
- docs/implementation/plans/Plan_S03_CUS-001.md
- docs/implementation/walkthroughs/Walkthrough_S03_CUS-001.md
- docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md (the `identity → audit` precedent this mirrors)

---

# ADR-015

## Title

Endpoint Shape Rule: Client-`{id}`-Addressable Collections Use `ensure_owner_or_not_found`; Singleton `/me`
Resources Rely on Structural Ownership

**Date**

2026-09-07

**Status**

Accepted

**Owner**

CTO

### Context

Three stories have now each shipped one of two distinct endpoint shapes for "a resource that belongs to the
calling user": AUTH-003/AUTH-004 built `GET /auth/sessions` and `DELETE /auth/sessions/{session_id}` (a genuine
1:N collection the client must address by id — one specific session among several); CUS-001 built `GET`/`PATCH
/customers/me` (a 1:1 resource with no `{id}` at all — there is nothing else for a caller to even attempt to
address); CUS-002 built `GET`/`POST /customers/me/addresses` and `PATCH`/`DELETE
/customers/me/addresses/{address_id}` (another genuine 1:N collection, correctly following the sessions shape
rather than the `/me` shape it extends). Each story derived the correct choice independently by reasoning from
first principles, and both `tester` and `architect` flagged during CUS-002's review that this reasoning should
be written down once, rather than re-derived by every future story that ships a "my own resource(s)" endpoint.

### Decision

When a new endpoint exposes a resource scoped to the authenticated caller, the shape is chosen as follows:

- **If the resource is inherently 1:1 with the caller** (there is at most one instance, ever, per user —
  e.g. a profile, a preferences record), expose it at a fixed path with no `{id}` parameter at all (e.g.
  `/customers/me`). Ownership is then **structurally guaranteed**, not defensively checked: there is no route
  shape through which a caller could even attempt to address another user's instance, because the path never
  carries a client-suppliable identifier. No `ensure_owner_or_not_found` call is needed or appropriate here —
  there is no id to check.
- **If the resource is a genuine 1:N collection** (the caller can have zero, one, or many, and must address
  one specific instance to read/update/delete it — e.g. sessions, saved addresses), expose it as a normal
  client-`{id}`-addressable resource (e.g. `/auth/sessions/{session_id}`, `/customers/me/addresses/{address_id}`).
  Because the `{id}` in the path is real and client-supplied, ownership **must** be defensively enforced on
  every read/write of a specific instance via `ensure_owner_or_not_found` (`app/core/authorization.py`),
  collapsing "row doesn't exist" and "row exists but isn't yours" into the same non-revealing 404 — never a
  403, which would leak that the id is valid but belongs to someone else.

This is not a new mechanism — `ensure_owner_or_not_found` already existed from AUTH-004. This ADR records the
*rule for choosing between* the two already-proven shapes, so a future story doesn't have to re-derive it, and
so a future PR that puts an `{id}` on a genuinely 1:1 resource (or omits the ownership check on a genuinely 1:N
one) is recognized as a design smell against a documented rule, not a fresh judgment call.

### Alternatives Considered

- Always use `{id}`-addressable paths, even for 1:1 resources, for uniformity (rejected — adds a meaningless
  client-supplied identifier to a resource that can only ever be "mine," and would require either a fake `id`
  the client must first look up, or `id=me` string-literal indirection; CUS-001's `/me`-only shape is simpler,
  safer by construction, and already shipped and reviewed clean).
- Always require `ensure_owner_or_not_found` on every "my resource" endpoint regardless of shape (rejected —
  on a true `/me` singleton there is no `{id}` to check against, so the call would be checking a caller-derived
  id against itself, a no-op that adds code without adding safety, as CUS-001's own architect review already
  concluded).

### Consequences

- Every future "my own resource(s)" endpoint should pick its shape using this rule up front, rather than
  re-deriving the sessions-vs-profile reasoning from scratch.
- `04_DATABASE.md`/`05_API_GUIDELINES.md` readers can now cite this ADR for why some caller-owned endpoints
  carry `{id}` and defend ownership at runtime, while others (`/me`) do not and structurally cannot need to.

### Related Documents

- 05_API_GUIDELINES.md
- 06_SECURITY.md
- docs/implementation/plans/Plan_S02_AUTH-004.md (origin of `ensure_owner_or_not_found`)
- docs/implementation/plans/Plan_S03_CUS-001.md (the `/me` singleton precedent)
- docs/implementation/plans/Plan_S03_CUS-002.md (Decision 1 — the collection precedent this ADR generalizes)
- docs/implementation/walkthroughs/Walkthrough_S03_CUS-002.md

---

# ADR-016

## Title

Cross-Module Role-Grant Trigger via Direct Service Injection — `provider → identity` (the Reverse Direction of ADR-014)

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story PRO-001 needed a caller who already has an authenticated Account (created at registration, per AUTH-001/
AUTH-002) to be granted `ROLE_PROVIDER` at the moment they create their first Provider listing, in the same
database transaction as the new `providers`/subtype-profile rows — never as a separate, possibly-failing
follow-up call. No existing mechanism allowed a module other than `identity` to grant a role to an
already-registered Account: `AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth` assign
`ROLE_CUSTOMER` inline, directly against `RoleRepository`/`UserRole`, only at first registration — there was no
reusable, importable "assign this role to this user" service method anywhere in the codebase. This is the
mirror image of ADR-014's `identity → customer`/`identity → audit` edges: those cover `identity`'s own
registration flow triggering *another* module's provisioning logic; this story needed a *different* module
(`provider`) to modify `identity`'s own data (`user_roles`) for an *already-authenticated* caller, not at
registration time.

### Decision

A new, single-purpose `RoleAssignmentService` lives in `identity`
(`backend/app/modules/identity/services/role_assignment_service.py`), exposing exactly one method:
`async def ensure_role_assigned(self, user_id: uuid.UUID, role_name: str) -> None` — idempotent (checks
`RoleRepository.get_role_names_for_user(user_id)` first; only inserts a new `UserRole` row if the role is not
already present), flush only, never commits. `provider`'s `ProviderService` takes this as a constructor
dependency and calls `await self.role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)` inside
`create_provider`, on the same request-scoped `AsyncSession` already in use — the `providers` row, its subtype
profile row, and the new `user_roles` row either all land together or none do, since the endpoint's single,
pre-existing `db.commit()` remains the only transaction boundary. Wired via a new
`get_role_assignment_service()` in `identity/dependencies.py`, imported into `provider/dependencies.py`'s
`get_provider_service()` — the identical shape `identity/dependencies.py`'s `get_auth_service()` already uses
to import `customer/dependencies.py`'s `get_customer_service`, just reversed.

`RoleAssignmentService` has zero imports from `provider` (only `identity.models`/`identity.repositories`), so
this is a second, independent, one-directional edge (`provider → identity`) — it does not create a cycle with
the existing `identity → customer`/`identity → audit` edges, since those involve entirely different files and
service classes. `AuthService`'s own inline role-assignment logic during registration is untouched by this
story; `RoleAssignmentService` is a new, narrower, reusable capability `AuthService` could later be refactored
to call too, but that refactor is out of this story's scope.

### Alternatives Considered

- **`ProviderService` importing `RoleRepository`/`UserRole` directly** (rejected — this is exactly the
  "Module → Another Module's Repository" pattern `02_ARCHITECTURE.md` explicitly prohibits; modules communicate
  through services only).
- **`provider` depending on the full `AuthService`** (rejected — `AuthService` orchestrates OTP verification,
  OAuth claims, and session/device issuance; pulling all of that into `provider`'s dependency graph for one
  idempotent role-grant call is far heavier coupling than needed, and violates "small, focused services").
- **A domain event (`ProviderRegistered`) via an in-process event bus** (rejected for the same reason ADR-014
  rejected it for `CustomerRegistered`: no event-bus infrastructure exists anywhere in this codebase; building
  one for a single call site is premature abstraction).

### Consequences

- `identity` now has an incoming cross-module service dependency (`provider → identity`) in addition to its two
  existing outgoing ones (`identity → audit`, `identity → customer`) — all three follow the same
  constructor-injection, flush-only, same-session shape, keeping this a single, repeatable pattern for
  cross-module same-transaction side effects rather than several different mechanisms.
- The caller's *current* JWT was issued before `ROLE_PROVIDER` existed on their account, so `CurrentUser.roles`
  won't reflect it until their next token refresh — already-supported behavior, since
  `RoleRepository.get_role_names_for_user` is re-read by `SessionService.refresh` on every refresh. No new
  token-refresh mechanism was needed.
- Any future module needing to grant an existing Account a role outside of registration should reuse
  `RoleAssignmentService.ensure_role_assigned` rather than re-deriving a new mechanism or reaching into
  `identity`'s repositories directly.

### Related Documents

- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- docs/implementation/plans/Plan_S04_PRO-001.md
- docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md
- docs/implementation/walkthroughs/Walkthrough_S03_CUS-001.md (ADR-014, the `identity → customer`/`identity → audit` precedent this reverses)

---

# ADR-017

## Title

First File-Upload Capability — `FileStorage` Protocol / `LocalFileStorage`, Explicitly Interim Pending Real AWS Infrastructure

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story PRO-002 needed provider portfolio-photo uploads (AC2: validated for MIME type, extension, and size,
stored under a generated filename) — the first feature in this codebase to need any file-upload/storage
capability at all. Confirmed by direct search during planning: no `boto3`, no S3 client, no `StaticFiles`
mount, no upload directory, and no image-validation utility existed anywhere. `12_TECH_STACK.md` names AWS as
the approved cloud provider architecturally, but no AWS credentials, bucket, or SDK integration exist in this
codebase or this development environment — building against a cloud resource that cannot actually be
provisioned or tested here would be unverifiable, unrequested infrastructure work, not a Sprint-4 storefront
story.

### Decision

A small, generic `FileStorage` protocol (`backend/app/shared/storage/interfaces.py`: `async def save(self,
content: bytes, *, filename: str, subdirectory: str) -> str`, returning a served, relative URL path; `async def
delete(self, url_path: str) -> None`) decouples `PortfolioService` from any concrete storage backend — it
depends on the protocol, never a concrete implementation directly. The only concrete implementation shipped by
this story is `LocalFileStorage` (`backend/app/shared/storage/local_file_storage.py`), writing to a new,
git-ignored `UPLOAD_DIR` setting (default `uploads/`) on the local filesystem, with blocking filesystem calls
offloaded via `asyncio.to_thread` so they never block the event loop, served back to clients via a
`StaticFiles` mount at `/media` in `main.py`. This is explicitly and deliberately **interim**: once real AWS
credentials/bucket provisioning exist in this environment, a future story can add `S3FileStorage` by writing
one new class and changing one dependency-wiring line, with zero changes to `PortfolioService` itself.

**Validation approach** (`backend/app/shared/storage/image_validation.py`, satisfying AC2 and `06_SECURITY.md`'s
File Upload Security section): size is checked against the actual read byte length (never a client-declared
`Content-Length` header) against a new `MAX_PORTFOLIO_PHOTO_SIZE_BYTES` setting (default 5 MB). The original
client-supplied filename's extension is checked only against an allow-list (`.jpg`, `.jpeg`, `.png`, `.webp`)
for rejection purposes — it is never used to construct the stored filename or path. Both the client-declared
`UploadFile.content_type` and a magic-byte sniff of the actual content (JPEG/PNG/WEBP file signatures) must
agree with an allowed image type; a mismatch (e.g. a `.jpg`-named file whose bytes are actually something else)
is rejected. This deliberately uses only Python's standard library for the magic-byte check — no Pillow or
other new imaging dependency was added, since no acceptance criterion in the story required
thumbnailing/re-encoding, only validation, and `08_CODING_STANDARDS.md`/`12_TECH_STACK.md` both call for
minimizing new dependencies. The stored filename is always server-generated
(`f"{uuid4().hex}{validated_extension}"`, where the extension comes from the *validated detected type*, never
the client's original filename) — never derived from client input.

### Alternatives Considered

- **Real AWS S3 integration now** (rejected — no AWS credentials, bucket, or IAM configuration exist in this
  environment; building and "testing" against a cloud resource that cannot actually be provisioned here would
  be unverifiable work, not something this story could honestly claim to have validated).
- **Storing image bytes directly in Postgres (`bytea`)** (rejected — `04_DATABASE.md`'s own
  `verification_documents.file_url` precedent already establishes "stored file reference, not the file itself"
  as this codebase's convention for uploaded files; no reason to deviate for portfolios).
- **Pillow-based content sniffing / image processing** (rejected for now, per the dependency-minimization
  reasoning above — a magic-byte check is sufficient to satisfy AC2's "validated for MIME type" requirement
  without a new package; if virus scanning or thumbnail generation is added in a future story,
  `06_SECURITY.md` already flags malware scanning as a future enhancement, and that is the natural point to
  reconsider adding an imaging library).

### Consequences

- `PortfolioService` and any future file-upload-needing service should depend on the `FileStorage` protocol,
  never a concrete storage class, so a future `S3FileStorage` (or any other backend) can be substituted with a
  single dependency-wiring change.
- `LocalFileStorage` must not be treated as production-durable storage — it exists specifically as an interim,
  environment-appropriate choice until real AWS infrastructure is provisioned; deploying to a real environment
  without first replacing it with a durable backend would be a regression, not a continuation of this decision.
- Orphaned-file cleanup (e.g. for soft-deleted portfolio photos) and virus/malware scanning remain explicitly
  out of scope for this decision and are documented as future administrative/security enhancements.

### Related Documents

- 04_DATABASE.md
- 06_SECURITY.md
- 12_TECH_STACK.md
- docs/implementation/plans/Plan_S04_PRO-002.md
- docs/implementation/walkthroughs/Walkthrough_S04_PRO-002.md

---

# ADR-018

## Title

First OCR Integration Point — `DocumentOcrService` Protocol / `StubDocumentOcrService`, Explicitly Interim Pending a Confirmed Real Pipeline

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-001 needed a provider's uploaded identity/license document to produce OCR-extracted candidate fields
(name, ID number, expiry date) for the mobile confirmation screen (AC4: "shows OCR-extracted fields... as
editable"). The story description itself referenced "the existing Ejari/Emirates ID pipeline," but a repo-wide
grep during planning (`ocr|OCR|ejari|Ejari|emirates.id|EmiratesId`) confirmed no OCR pipeline, external OCR SDK,
or Ejari integration exists anywhere in this codebase or development environment — every hit outside narrative
`docs/AI/` documents was either this story's own future-facing text or a *behavioral* skill file
(`.agents/skills/identity-verification/SKILL.md`) instructing agents on trust-gate discipline, not an actual
integration. `00_PROJECT_CONTEXT.md`'s own changelog documents this codebase as a pivot from an earlier
"MyCommunity" product (ADR-011); the "existing pipeline" language is best read as a product-level asset
assumption carried over from planning, not literal code present in this repository. Building a new OCR engine
from scratch, or guessing at/mocking a specific unconfirmed vendor's interface, was both out of this story's
scope and explicitly disclaimed by the story's own text ("The OCR integration itself is stubbed pending
confirmation of the existing... pipeline's interface... this story does not build a new OCR engine from
scratch").

### Decision

`backend/app/modules/verification/services/document_ocr_service.py` defines a `DocumentOcrResult` value object
(`full_name: str | None`, `id_number: str | None`, `expiry_date: date | None`, `confidence: float`) and a
`DocumentOcrService` `Protocol` (`async def extract(self, content: bytes, *, document_type: DocumentType) ->
DocumentOcrResult`). The only implementation shipped by this story, `StubDocumentOcrService`, **always** returns
`DocumentOcrResult(full_name=None, id_number=None, expiry_date=None, confidence=0.0)` regardless of the actual
file content — it never attempts real extraction of any kind. `VerificationService` (the preview-call handler)
depends on the `DocumentOcrService` Protocol, never `StubDocumentOcrService` directly, wired via a
`get_document_ocr_service()` DI provider in `verification/dependencies.py`. This satisfies AC4's structural
requirement (a confirmation screen with editable OCR-extracted fields) while being honest that nothing was
actually read yet — the mobile confirmation screen's copy reflects this plainly ("we couldn't automatically read
your document yet — please fill in these details yourself"), rather than implying a real extraction happened.
This mirrors ADR-017's `FileStorage` swappability pattern exactly: a future story, once a real OCR pipeline's
interface is actually confirmed to exist, can add a real implementation as one new class and change one
dependency-wiring line, with zero changes to `VerificationService` itself.

### Alternatives Considered

- **Build or partially reverse-engineer a specific vendor's OCR integration now** (rejected — no real pipeline,
  SDK, or vendor credentials exist anywhere in this codebase or environment; this would be unverifiable,
  speculative work against an interface that isn't actually confirmed, directly contrary to the story's own
  explicit instruction not to do this).
- **Skip the confirm-step fields entirely until real OCR exists** (rejected — AC4 explicitly requires an editable
  confirmation step now; the Protocol/stub shape lets that UI ship honestly today without blocking on
  infrastructure that isn't ready).
- **Have `VerificationService` depend on `StubDocumentOcrService` directly, without a Protocol** (rejected — this
  would require changing `VerificationService`'s own code, not just its dependency wiring, the moment a real
  implementation exists; the Protocol costs nothing extra to introduce now and avoids that future churn).

### Consequences

- Any future story swapping in a real OCR implementation changes exactly one dependency-wiring line
  (`get_document_ocr_service()`), never `VerificationService`'s own logic.
- The stub's honesty (`confidence=0.0`, all fields `None`) must be preserved in any interim implementation —
  no future change should make the stub *appear* to read real data without actually doing so, per this
  project's broader "never assert ungrounded data" principle.
- This is this codebase's first OCR integration point; any second OCR-adjacent need (e.g. a different document
  category) should default to extending this same Protocol rather than inventing a parallel mechanism.

### Related Documents

- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 06_SECURITY.md
- .agents/skills/identity-verification/SKILL.md
- docs/implementation/plans/Plan_S05_VER-001.md
- docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md
- docs/implementation/walkthroughs/Walkthrough_S04_PRO-002.md (ADR-017, the `FileStorage` swappability precedent this mirrors)

---

# ADR-019

## Title

Private vs. Public File Storage — `FileStorage` Gains a `public_url_prefix` Split, an Authenticated Streaming-Download Endpoint Pattern for Sensitive Documents

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-001 needed to store identity/license documents (Emirates ID scans, trade licenses) — data
`06_SECURITY.md` explicitly lists under Sensitive Data, on a platform targeting UAE PDPL/GDPR-ready compliance.
ADR-017's `FileStorage`/`LocalFileStorage` (Story PRO-002) was built for portfolio photos, which are meant to be
public-facing (the customer-visible storefront), and its `LocalFileStorage.save()` hardcoded every stored file's
returned reference as `f"/media/{subdirectory}/{filename}"` — i.e. it assumed every file it stores is meant to be
served through the existing public `/media` `StaticFiles` mount. That assumption is correct for portfolios and
directly wrong for verification documents: reusing it unmodified would mean any predictable/guessed
`/media/verification/...` URL is publicly fetchable with no authentication at all. `06_SECURITY.md`'s generic
File Upload Security section (MIME/extension/size validation) does not by itself cover access-control-at-rest
for a distinct sensitivity class of file, so this had to be reasoned through independently as a new consequence
of the file-storage infrastructure, not something ADR-017's original text anticipated.

### Decision

`LocalFileStorage` gains one new constructor parameter, `public_url_prefix: str | None = "/media"` — defaulting
to today's exact existing behavior, so the pre-existing portfolio wiring (`get_file_storage()`) is entirely
unchanged, zero behavior difference for PRO-002. When constructed with `public_url_prefix=None` (the new
verification wiring), `save()` returns a bare storage-relative reference instead of a public URL — meaningful
only to the backend itself, never handed to a client as a clickable link. `delete()`'s previously-hardcoded
`removeprefix("/media/")` is generalized to use `self._public_url_prefix`. The `FileStorage` Protocol gains one
new method, `async def read(self, url_path: str) -> bytes` (additive; `LocalFileStorage` is the only
implementer, and `PortfolioService` never calls it, so this has zero effect on PRO-002's existing behavior).

Verification documents are written under a second, completely separate root directory
(`VERIFICATION_UPLOAD_DIR`, e.g. `uploads_private/verification`) that is **never** mounted as `StaticFiles` and
**never** produces a `/media/...` URL (`.gitignore` gains a matching `/uploads_private/` entry alongside the
existing `/uploads/`). Clients never receive a raw file path or public URL for a verification document: `GET
/providers/me/verification`'s response includes, per document, a `file_download_url` pointing at a new,
authenticated, ownership-checked streaming endpoint
(`GET /providers/me/verification/documents/{document_id}/file`) — the mobile client's existing Dio bearer-token
interceptor already authenticates the request, so no new authentication mechanism was needed, only an endpoint
that runs `ensure_owner_or_not_found` (via the document → its parent record → `provider_id` chain, per ADR-015)
before streaming bytes. The preview step writes to a fixed, deterministic, per-provider "pending" slot rather
than a client-supplied token, self-bounding disk usage to at most one file per provider for any
never-submitted preview — no rate limiting or cleanup job is needed to bound this.

Independently confirmed, not merely claimed: the tester verified via real HTTP requests that a verification
document is never reachable through the public `/media` mount's URL shape (404, since it was never written
there at all); the architect assessed this as the part of the story that held up best under review, cleanly
satisfying both `06_SECURITY.md`'s Sensitive Data handling and `02_ARCHITECTURE.md`'s "Infrastructure depends on
Domain" dependency rule.

### Alternatives Considered

- **Reuse the existing public `/media` mount, unchanged, for verification documents too** (rejected outright —
  this is the exact security-sensitive default this decision exists to avoid).
- **A signed/expiring URL scheme (a short-lived query-string token) instead of an authenticated streaming
  endpoint** (rejected as unnecessary complexity — the mobile client already authenticates every request via its
  existing Dio bearer-token interceptor, so a normal authenticated `GET` is simpler and equally secure, with no
  new expiry/signing infrastructure to build or reason about).
- **Storing documents as `bytea` directly in Postgres** (rejected for the same reason PRO-002/ADR-017 rejected it
  for portfolios — `verification_documents.file_url`'s own spec says "stored file reference, not the file
  itself").
- **A client-supplied opaque preview token, stored server-side in Redis with a TTL, instead of the deterministic
  pending-slot path** (rejected as premature infrastructure for a single call site — a stateless, deterministic
  per-provider path achieves the same self-bounding effect with no new moving parts).

### Consequences

- `FileStorage`/`LocalFileStorage` now supports two genuinely distinct storage postures — public (portfolios,
  `public_url_prefix="/media"`) and private (verification documents, `public_url_prefix=None`) — through the same
  small abstraction, rather than a fork. Any future sensitive-file need (e.g. a future admin-facing document)
  should default to the private posture (`public_url_prefix=None` + an authenticated streaming endpoint) rather
  than reusing the public mount by default.
- A future `S3FileStorage` (per ADR-017's own interim framing) must preserve this same public/private
  distinction — e.g. via S3 bucket ACLs/pre-signed URLs for the public case and IAM-gated, non-public access for
  the private case — not silently collapse both postures back into one.
- The authenticated document-download endpoint's ownership check is written so a future VER-002 admin-review
  surface can extend it to "owner OR an Admin" without restructuring the storage split itself.

### Related Documents

- 02_ARCHITECTURE.md
- 04_DATABASE.md
- 06_SECURITY.md
- docs/implementation/plans/Plan_S05_VER-001.md
- docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md
- docs/implementation/walkthroughs/Walkthrough_S04_PRO-002.md (ADR-017, the `FileStorage`/`LocalFileStorage` origin this extends)

---

# Future Decisions

Future architectural decisions should include topics such as:

- Event-driven architecture
- Background job processing
- Search engine adoption
- AI service integration
- Analytics platform
- Observability platform
- CI/CD evolution
- Infrastructure as Code
- Kubernetes adoption
- Multi-region deployment

Each decision must receive a new ADR entry.

---

# Decision Rules

Every new architectural decision must:

- Have a unique ADR number.
- Include business and technical context.
- Explain why the decision was made.
- Record alternatives considered.
- Describe long-term consequences.
- Reference related documentation.
- Be approved by the CTO before implementation.

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
- 10_GLOSSARY.md

---

**End of Document**