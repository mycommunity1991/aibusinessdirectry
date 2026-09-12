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

# ADR-020

## Title

Admin-Role Provisioning — Reuse of the Existing OTP/OAuth Login Path Plus a New, Ops-Only CLI Script (`grant_admin_role.py`); Email+Password Admin Login Explicitly Deferred

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-002 introduced this codebase's first `require_role(ROLE_ADMIN)`-gated endpoints (the admin
verification-review queue and approve/reject actions). `ROLE_ADMIN` already existed as a seeded role and
`require_role()` already accepted it as a valid argument (AUTH-004) — but no mechanism anywhere in the codebase
granted `ROLE_ADMIN` to a real Account, and none should exist as a self-service flow. Separately, the schema
already reserves a genuinely unused `email_password` `auth_provider` value and a `password_hash` column,
documented in `04_DATABASE.md` as "(admin-only)"/"Populated only for `email_password` auth (internal Admin
accounts)" — but no endpoint anywhere in this codebase authenticates via email+password, confirmed by reading
every route in `identity/api.py`.

### Decision

An Admin authenticates through the exact same existing mobile-OTP or Google/Apple sign-in flow any
Customer/Provider already uses — no new login mechanism was built by this story. A new, ops-only CLI script,
`backend/scripts/grant_admin_role.py`, mirrors the existing `backend/scripts/seed_roles.py` precedent: it looks
up an already-registered user by phone via the existing `UserRepository.get_by_phone`, then calls the
already-generic `RoleAssignmentService.ensure_role_assigned(user.id, ROLE_ADMIN)` (ADR-016) and commits. It
requires the target person to already have a real, registered Account through the ordinary sign-in flow — it
never creates a phantom account, only grants a role to an existing one. It is never exposed via HTTP and
requires direct server/deployment access to run, the same trust boundary `seed_roles.py` already relies on. The
script's logging identifies the target user only by their resulting `user.id`, never by the phone number
supplied on the command line, consistent with `06_SECURITY.md`'s treatment of phone numbers as sensitive/PII
(an issue caught and fixed during this story's architect review).

The schema's `email_password`/`password_hash` reservation is read as forward-looking scaffolding for a
**future, separate Admin Portal login story** — plausibly bundled with ADM-002's own "admin operations
dashboard" work — not something VER-002 builds a slice of. This decision was explicitly confirmed by the user
before implementation began, per the Plan's own flagged confirmation requirement (Decision 1,
`Plan_S05_VER-002.md`).

### Alternatives Considered

- **Build the full `email_password` admin login endpoint now** (rejected — new authentication surface, its own
  security review and test suite, materially larger than "the verification-review action and its direct
  consequences"; flagged as a candidate for a future dedicated story instead).
- **No script at all — a manual `INSERT INTO identity.user_roles ...` runbook note** (a legitimate, more minimal
  fallback the Plan also offered; not chosen — the CLI script is safer by construction: idempotent, reuses
  already-tested application code, cannot construct a malformed row — and costs very little to add).

### Consequences

- Any future story needing to provision a second privileged role (beyond Admin) should default to this same
  shape — an ops-only CLI script calling `RoleAssignmentService.ensure_role_assigned` against an already-registered
  Account — rather than building a new self-service grant path.
- A future Admin Portal login story, if it ever builds the `email_password` path, will need its own security
  review; this ADR does not pre-approve that work, only records that the schema was deliberately left ready to
  absorb it without a breaking migration.
- CLI scripts that look up or act on identifying user data (phone numbers, emails) must log only the resulting
  internal `user.id`, never the raw identifying input, per this story's fixed logging issue.

### Related Documents

- 04_DATABASE.md
- 06_SECURITY.md
- 09_DECISIONS.md (ADR-016 — `RoleAssignmentService.ensure_role_assigned`, reused unmodified here)
- docs/implementation/plans/Plan_S05_VER-002.md (Decision 1)
- docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md

---

# ADR-021

## Title

`admin_action_log` Lives in a New, First-of-Its-Kind `administration` Domain Module — Not an Extension of `audit`

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-002 needed every admin approve/reject action recorded (AC6: "Every approval/rejection action is
written to `admin_action_log`"). `audit.audit_logs` (AUTH-004) already has a generic
`action`/`entity_type`/`entity_id`/`before_state`/`after_state` shape structurally close to what `admin_
action_log` needs, which could suggest reusing it rather than building a new table. `04_DATABASE.md` already
fully specified `administration.admin_action_log` as its own table, under its own schema, with its own,
genuinely different column names (`admin_user_id`/`action_type`/`target_entity_type`/`target_entity_id`/
`metadata`, not `audit_logs`' `actor_user_id`/`action`/`entity_type`/`entity_id`/`before_state`/`after_state`),
and `03_DOMAIN_MODEL.md` already places `Admin Action Log` inside the Administration domain's entity list, a
peer of `Admin User`/`Manual Match Assignment`/`Unmatched Query Report` — not inside Verification or a generic
cross-cutting audit concept.

### Decision

A new `backend/app/modules/administration/` module was created — this domain's first slice, exactly the same
shape `verification` itself was for VER-001. It mirrors `audit`'s own minimal footprint (model → repository →
service → dependencies; no `api.py`/`schemas.py`, since nothing here is directly HTTP-exposed — it is called
internally by `verification`'s new admin service, the same way `identity` calls `audit`'s service internally).
`AdminActionLog(CommonColumnsMixin, Base)` is built **not** exempt like the immutable `AuditLog` — `04_DATABASE.md`'s
Soft Delete section names only `audit_logs`/`search_event_log` as exempt from Common Columns, and
`admin_action_log` is not on that list, so it is built exactly like every other ordinary business table in this
codebase (versioned, soft-deletable), even though this means an admin-action row is not literally immutable the
way `audit_logs`' rows are — a deliberate, spec-literal choice, not an oversight. `AdminActionLogService`
exposes one explicit method, `record_verification_review`, mirroring `AuditService`'s "explicit methods, not one
generic `record()`" convention.

### Alternatives Considered

- **Extend `audit.audit_logs` with the admin-action events instead** (rejected — would have required either
  overloading `audit_logs`' generic columns with admin-specific semantics, or leaving the table AC6 and
  `04_DATABASE.md` both name explicitly permanently unbuilt; also blurs `audit_logs`' deliberately immutable
  nature with a mutable, soft-deletable concept).
- **Put `AdminActionLog` inside the `verification` module instead of a new `administration` module** (rejected —
  `admin_action_log` is explicitly reusable by any future admin action, e.g. Manual Match Assignment review,
  ADM-002's wider dashboard, not something scoped to Verification alone; colocating it inside `verification`
  would misrepresent its actual domain ownership).

### Consequences

- Any future admin action (Manual Match Assignment review, Unmatched Query Report actioning, ADM-002's wider
  operations dashboard) should write to this same `administration.admin_action_log` table via
  `AdminActionLogService`, rather than inventing a parallel logging mechanism.
- `admin_action_log` rows are not immutable the way `audit_logs`' rows are (they carry the full soft-delete/
  versioning Common Columns) — any future code relying on admin-action history being tamper-evident must not
  assume the same immutability guarantee `audit_logs` provides.
- This is the Administration domain's first real, if partial, implementation — the domain's much larger future
  scope (Admin User accounts as a first-class entity, Manual Match Assignment, Unmatched Query Reports, feature
  flags/system settings) remains entirely unbuilt.

### Related Documents

- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md (Administration domain)
- 04_DATABASE.md (Administration Domain, Soft Delete section)
- docs/implementation/plans/Plan_S05_VER-002.md (Decision 2)
- docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md
- docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md (the `audit` module precedent this is deliberately not merged into)

---

# ADR-022

## Title

Notification Domain, First Slice — `notification.notifications` Only, Honest In-App-Record-Only, No Real Delivery Channel Yet

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-002's AC5 required a provider to receive "a notification on status change, worded in plain language,
never exposing internal status enum values" — a literal, testable requirement, not an aspiration. No
Notification domain code existed anywhere in this codebase before this story; `03_DOMAIN_MODEL.md` and
`PROJECT_IMPLEMENTATION_STATE.md` both listed Notifications as "not yet implemented," and Sprint 12 ("Engagement
& Trust") is this domain's own dedicated future milestone with a full three-table design already specified in
`04_DATABASE.md` (`notifications`, `notification_preferences`, `notification_delivery`) for real WhatsApp/SMS/
Email sending. Building that full pipeline now would be significantly out of this story's scope; silently
no-op'ing AC5 would not honestly satisfy it either.

### Decision

A new `backend/app/modules/notification/` module — this domain's first slice — builds **only**
`notification.notifications` (`user_id`, `type`, `title`, `body`, `related_entity_type`, `related_entity_id`),
exactly per `04_DATABASE.md`'s pre-existing spec, using the full `CommonColumnsMixin` (the same spec-literal
reasoning as ADR-021's `AdminActionLog`). It deliberately does not build `notification_delivery` (there is no
real channel to have a delivery status for) or `notification_preferences` (there is nothing to opt in/out of
yet). A `notifications` row honestly records "a notification of this type, with this plain-language content, was
generated for this user" — nothing more, directly mirroring ADR-018's (`StubDocumentOcrService`) and ADR-017's
(`LocalFileStorage`) precedent of shipping an honestly-interim capability rather than a silent no-op or a
premature full build-out. `NotificationService` exposes one explicit method,
`notify_verification_status_change`, with hardcoded, plain-language copy templates for the approved/rejected
cases — never simply interpolating the raw `VerificationStatus` enum member into `title`/`body`, satisfying
AC5's "never exposing internal status enum values" literally.

### Alternatives Considered

- **Build the full three-table Notification domain now** (rejected as materially out of scope — no real
  delivery channel or preference exists to build against yet; Sprint 12 is this domain's own dedicated
  milestone).
- **Skip AC5 with a no-op or log-line only** (rejected outright — AC5 is a literal, automated-test-covered
  acceptance criterion, not an aspiration; a genuine `notifications` row is the honest minimum that satisfies
  it).
- **Reuse/extend `customer.customer_preferences.notification_channel`** (rejected — it is Customer-domain schema
  with zero delivery mechanism behind it today, and does not even apply to a Provider recipient without a
  Customer profile on the same Account).

### Consequences

- Any future story adding real WhatsApp/SMS/Email delivery, or a "read my notifications" inbox endpoint, should
  build on top of this `notifications` table and `NotificationService`, adding `notification_delivery`/
  `notification_preferences` at that point rather than before a real channel exists.
- This is the Notification domain's first real, if partial, implementation — no delivery actually happens yet;
  a `notifications` row today is purely an internal record, never seen by the recipient through any UI or
  channel this codebase currently builds.

### Related Documents

- 03_DOMAIN_MODEL.md (Notification domain)
- 04_DATABASE.md (Notification Domain)
- 09_DECISIONS.md (ADR-017, ADR-018 — the "honestly interim, not a silent no-op" precedent this follows)
- docs/implementation/plans/Plan_S05_VER-002.md (Decision 3)
- docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md

---

# ADR-023

## Title

A Third Endpoint-Authorization Shape — Ownerless, `require_role(ROLE_ADMIN)`-Only Routes, Extending ADR-015's Framework

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

ADR-015 established exactly two shapes for "a resource scoped to the authenticated caller": a `/me` singleton
(structural ownership, no `{id}` parameter at all) and a client-`{id}`-addressable collection (defensive
`ensure_owner_or_not_found` ownership checks). Story VER-002's four new admin endpoints (the review queue,
approve, reject, and the admin document-download route) fit neither shape: an Admin has no "own" verification
record to scope to at all — every record in the queue belongs to some *other* user's Provider. Applying either
of ADR-015's existing shapes here would be a category error: there is no `{id}` an Admin could ever "own," so an
`ensure_owner_or_not_found` check would either be a meaningless no-op or, worse, would incorrectly reject a
legitimate admin action against a stranger's record.

### Decision

`require_role(ROLE_ADMIN)` alone is the entire authorization boundary for this class of route — no ownership
check of any kind applies, structurally, because none would even make sense. This is recorded as a genuinely
new, third category extending ADR-015's framework, not a violation of it: ADR-015's rule was about *how* to
scope a resource to its *owner*; this new category covers resources with no meaningful "owner" relative to the
caller at all, where role membership alone is the correct and complete authorization model. The new admin
document-download route (`GET /admin/verification/documents/{document_id}/file`) is deliberately built as a
**sibling** to the existing owner-only `GET /providers/me/verification/documents/{document_id}/file`
(VER-001/ADR-019) rather than a modification of it in place — extending the owner-only route to accept "owner OR
Admin" would have blurred the meaning of a route mounted under `/providers/me/...`, where a `/me` path returning
someone *else's* provider's document reads as a contradiction in terms.

### Alternatives Considered

- **Extend the existing owner-only document-download route in place to accept "owner OR Admin"** (rejected — a
  route under `/providers/me/...` returning a *different* provider's document contradicts the path's own `/me`
  semantics, even if technically guarded correctly; ADR-019's own Consequences section had already anticipated
  this exact question and recommended a sibling route instead).
- **Nest the admin routes under `/providers/{provider_id}/verification/...`** (rejected — the admin is not
  acting "as" or "on behalf of" a specific known provider in the listing call, which spans *all* providers; the
  approve/reject/download actions are keyed by `verification_record_id`/`document_id` directly, simpler and
  avoiding a redundant, potentially-inconsistent `provider_id` path segment).

### Consequences

- Any future admin-facing, platform-wide route (e.g. a future ADM-002 operations-dashboard endpoint) should
  default to this same shape — `require_role(ROLE_ADMIN)` alone, no ownership dependency of any kind — rather
  than awkwardly forcing an ownership check onto a resource with no meaningful owner relative to the caller.
- ADR-015 remains the correct rule for genuinely caller-owned resources; this ADR does not change or narrow
  ADR-015's original two shapes, it adds a third, disjoint one for resources scoped by role membership instead
  of ownership.
- A route under a `/me` prefix must never be extended to return another user's data "for admins too" — a
  genuinely admin-facing need on the same underlying data should get its own sibling route under a distinct,
  role-gated prefix instead, per this story's document-download precedent.

### Related Documents

- 02_ARCHITECTURE.md
- 06_SECURITY.md
- 09_DECISIONS.md (ADR-015 — the framework this extends; ADR-019 — the private-document-storage precedent this
  builds a sibling route alongside)
- docs/implementation/plans/Plan_S05_VER-002.md (Decision 6)
- docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md

---

# ADR-024

## Title

Atomic Conditional `UPDATE` for Optimistic Concurrency Control — First Use in This Codebase, `VerificationRecordRepository.try_claim_for_review`

**Date**

2026-09-08

**Status**

Accepted

**Owner**

CTO

### Context

Story VER-002's independent tester review found and empirically reproduced a genuine concurrency bug in the
original admin approve/reject implementation: a plain read-then-write pattern (fetch the `verification_records`
row, check its `status` in Python, then issue an `UPDATE`) left a race window in which two truly concurrent
`approve()`/`reject()` calls against the *same* record could both pass the in-Python status check before either
call committed, each going on to write its own `admin_action_log` row and its own `notifications` row for what
should have been a single logical action — violating AC6/AC8's "exactly one" guarantee. This is this codebase's
first genuinely concurrent-write scenario against a single, contended row (every prior cross-module transaction
in this codebase — ADR-014, ADR-016, VER-001's own writes — involves a caller acting only on their own,
never-shared row).

### Decision

`VerificationRecordRepository.try_claim_for_review` replaces the read-then-write pattern with a single, atomic
conditional `UPDATE ... WHERE id = :record_id AND status IN ('pending', 'under_review')`, executed directly
against the database as one statement. Postgres takes a row lock on whichever concurrent writer's `UPDATE`
statement reaches the row first; a second, genuinely concurrent `UPDATE` targeting the same row blocks until the
first commits, then re-evaluates its own `WHERE` clause against the now-already-transitioned row — so at most
one caller's `UPDATE` can ever match, regardless of true concurrency. The method returns whether the calling
transaction won the race (based on the statement's `rowcount`); the caller
(`AdminVerificationService._claim_record_or_raise`) raises the existing `VerificationRecordNotActionableError`
(409) if it lost. This is correct under this codebase's actual, configured READ COMMITTED isolation level (no
other level is set anywhere in `app/database/database.py`); under SERIALIZABLE/REPEATABLE READ the losing
transaction would instead raise a serialization failure rather than affect zero rows — either outcome still
prevents the duplicate write this fix targets, so the pattern is robust across isolation levels, not merely
correct under one specific configuration. A dedicated regression test runs two genuinely concurrent `approve()`
calls (via `asyncio.gather`, each on its own independent `AsyncSession`/transaction) and asserts exactly one
`admin_action_log` row and exactly one `notifications` row exist afterward — confirmed to fail against the
original read-then-write code and pass against this fix.

### Alternatives Considered

- **A `SELECT ... FOR UPDATE` row lock before the read-then-write** (a viable alternative that would also close
  the race — not chosen because it requires two round trips (`SELECT FOR UPDATE` then `UPDATE`) where a single
  conditional `UPDATE` achieves the same guarantee in one statement, with less code and no separate lock-then-act
  window to reason about).
- **Optimistic locking via the existing `version` column (`CommonColumnsMixin`)** (a legitimate alternative
  general-purpose mechanism already present on every business table in this codebase — not chosen for this
  specific case because the conditional `UPDATE`'s `WHERE status IN (...)` clause already expresses the exact
  precondition that matters here — "is this record still actionable" — more directly than a generic version-number
  compare-and-swap would, and requires no separate read to first learn the current version).
- **An application-level lock (e.g. Redis-based)** (rejected as unnecessary infrastructure — Postgres's own
  row-level locking already provides a correct, dependency-free solution local to the single query that needs
  it).

### Consequences

- Any future story that needs to guard against two concurrent actors racing to transition the *same* row from
  one of several "still pending" states into a terminal state should default to this same pattern — a single
  conditional `UPDATE ... WHERE <current-state-precondition>`, checking `rowcount` to detect whether the caller's
  transaction won — rather than a Python-level read-then-write, which this story's own history now demonstrates
  is genuinely unsafe under real concurrency, not merely a theoretical concern.
- This is this codebase's first documented use of this pattern; `VerificationRecordRepository.try_claim_for_review`
  is the reference implementation future stories should model a similar guard on, rather than re-deriving the
  reasoning from scratch or reaching for heavier infrastructure (distributed locks, `SELECT FOR UPDATE`) where a
  single conditional `UPDATE` suffices.

### Related Documents

- 04_DATABASE.md (Transactions section)
- 09_DECISIONS.md (ADR-015 — `uq_saved_addresses_customer_default`'s defense-in-depth precedent this parallels
  in spirit, for a different concurrency concern)
- docs/implementation/plans/Plan_S05_VER-002.md (Decision 4)
- docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md

---

# ADR-025

## Title

New `search` Module Placement — A Genuinely New Domain's First Slice Keeps Its Actual Query Inside the Module That Owns the Queried Tables

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Story DIR-001 needed a structured (non-AI) category + geospatial-radius + discoverability query — the first
implementation of any part of `02_ARCHITECTURE.md`'s "Search Request & Matching" domain, which it names as its
own core business module distinct from Provider. Every table the query touches (`providers`,
`provider_category_labels`, `service_areas`), however, lives entirely in the `provider` schema — there is no
`search`-owned table this story needed to create (Decision 5 of `Plan_S06_DIR-001.md` explains why
`search.search_requests`/`provider_matches`/`search_event_log` are deliberately not built yet). This is the same
shape VER-001 already resolved for `verification` (a real, architecturally-named domain gets its own module even
when its first slice mostly reads another module's data) — but DIR-001 additionally needed a genuinely complex
query (raw parameterized SQL, multi-table join, pagination) against tables it doesn't own, which
`02_ARCHITECTURE.md`'s explicit "Module → Another Module's Repository: Not Allowed" rule directly constrains.

### Decision

A new `backend/app/modules/search/` module was created — this domain's first slice, with no `models.py` (no new
tables). The actual geospatial/category/discoverability SQL lives inside a new, dedicated
`ProviderSearchRepository` (`backend/app/modules/provider/repositories/provider_search_repository.py`) — **inside
the `provider` module**, since the query only ever touches `provider`-schema tables, kept as its own class
(separate from `ProviderRepository`'s simple CRUD) because of its genuine complexity. `ProviderService` gains one
new, thin, read-only method, `search_nearby(...)`, exposed to other modules the same way `ProviderService.list_by_ids`
already is (VER-002's precedent). `search`'s own `SearchService` depends on `ProviderService` only, via
constructor injection — the same one-directional, cycle-free cross-module shape ADR-014/016 already established
— and owns response-shaping (category-label/photo enrichment, distance formatting) that is genuinely
`search`'s own concern, not `provider`'s.

**The general rule this establishes:** when a new domain's first slice needs a genuinely complex query against
data owned by another, already-existing module, the query itself (the repository class issuing it) is built
inside the module that owns the queried tables, never inside the new module reaching across via a raw session or
a second module's repository directly. The new module's own service depends on the owning module's *service*
(never its repository) to reach that capability, keeping `02_ARCHITECTURE.md`'s "Module → Another Module's
Repository: Not Allowed" rule intact even for a domain whose conceptual home is elsewhere.

### Alternatives Considered

- **Extend the `provider` module directly with a `GET /providers/search` endpoint, no new `search` module**
  (rejected — this is exactly the "Search Request & Matching" responsibility `02_ARCHITECTURE.md` names as its
  own domain, and the story's own explicitly-named future upgrade path, MAT-001, will need ranking/merit logic
  that has nothing to do with a provider's own self-service storefront management; colocating it inside
  `provider` now would misrepresent domain ownership and bloat a module whose current responsibility is strictly
  "manage my own listing").
- **Build the real `search.search_requests`/`provider_matches`/`search_event_log` tables now** (rejected —
  `search_requests.category_id` is a hard `NOT NULL` FK to a `category.categories` table that does not exist yet;
  building these tables now, with a fabricated or nullable-hacked category reference, would misrepresent a
  conversational-flow table as something this purely structural query produces).
- **A `ProviderSearchRepository` placed inside `search`, issuing SQL against `provider`-schema tables via a raw
  session** (rejected outright per `02_ARCHITECTURE.md`'s explicit prohibition on one module directly accessing
  another module's repository/tables).

### Consequences

- Any future new domain module (e.g. the real `search.search_requests`-backed conversational flow, once the
  Category Taxonomy resolves) whose first slice needs to query another module's existing tables should default to
  this same shape — the query lives in the owning module, exposed via a thin service method — rather than
  reaching across module boundaries directly.
- `provider` now has a `ProviderSearchRepository` distinct from `ProviderRepository`, a precedent for splitting a
  module's repositories by genuine query complexity rather than always extending one monolithic repository class
  per module.
- `search → provider` is a new, one-directional, read-only, cycle-free cross-module edge; `provider` has zero
  imports from `search`.

### Related Documents

- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md (Search Request & Matching domain)
- 09_DECISIONS.md (ADR-014, ADR-016 — the cross-module service-injection shape this reuses)
- docs/implementation/plans/Plan_S06_DIR-001.md (Decision 4)
- docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md

---

# ADR-026

## Title

First Raw Parameterized SQL via `sqlalchemy.text()` — Justified Only When No ORM Expression-Language Mapping Exists for the Needed Database Function

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Story DIR-001's geospatial query needed `earth_box`, `earth_distance`, and `ll_to_earth` — SQL functions provided
by PostgreSQL's `earthdistance`/`cube` contrib extensions (`04_DATABASE.md` Section 13, `09_DECISIONS.md`'s
existing commitment to these extensions over PostGIS). None of these functions, nor the `@>` containment operator
`earth_box` results are queried with, have any SQLAlchemy Core/ORM expression-language mapping. Every query in
this codebase before this story was expressible entirely through SQLAlchemy's Python-object query builder — a
repo-wide check during planning confirmed no `sqlalchemy.text()`/raw-SQL usage existed anywhere.

### Decision

`ProviderSearchRepository.search_nearby` (and its matching `COUNT(*)` variant, sharing the identical `WHERE`
clause) issues a fully parameterized query via `sqlalchemy.text()`:

```sql
... WHERE
    (:category IS NULL OR EXISTS (... lower(pcl.label) = lower(:category) ...))
    AND earth_box(ll_to_earth(:origin_lat, :origin_lng), :radius_meters)
        @> ll_to_earth(sa.center_latitude, sa.center_longitude)
    AND earth_distance(ll_to_earth(:origin_lat, :origin_lng), ll_to_earth(sa.center_latitude, sa.center_longitude))
        <= :radius_meters
    AND p.is_discoverable = true AND p.is_active = true
ORDER BY distance_meters ASC, p.id ASC
```

Every value (`:origin_lat`, `:origin_lng`, `:radius_meters`, `:category`, `:limit`, `:offset`) is a bound
parameter — never string-formatted or concatenated user input — satisfying `06_SECURITY.md`'s and
`08_CODING_STANDARDS.md`'s parameterized-query rule in full, even though the query is not expressed through the
ORM's Python-object query builder. One driver-forced, non-semantic addition was required during implementation:
`:category` is wrapped in `CAST(... AS text)` at its first (`IS NULL`) usage, because the psycopg3 driver raised
`AmbiguousParameter` without explicit type context on a bare `:category IS NULL` comparison — this changes
nothing about clause order, filter semantics, or parameterization safety; it is purely a driver-compatibility
fix, confirmed by `architect`'s review.

**The general rule this establishes:** raw parameterized `text()` SQL is justified specifically when no
SQLAlchemy Core/ORM expression-language mapping exists for a database function or operator the query genuinely
needs (contrib-extension functions being the paradigm case) — never as a convenience shortcut for a query that
could be expressed through the ORM query builder. Any future raw-SQL use must, like this one, remain fully bound
via `text()`'s parameter substitution, never string-interpolated, and should be reserved for genuinely
unmappable database capabilities rather than adopted as a general pattern.

### Alternatives Considered

- **Compute distance in Python after fetching all candidate rows** (rejected — defeats the entire purpose of the
  GiST index (`idx_service_areas_location`) and AC6's index-usage verification; degrades to an O(n) full-table
  scan and Python-side Haversine computation at any real provider volume).
- **PostGIS `ST_DWithin`/`ST_Distance` instead of `cube`/`earthdistance`** (rejected — `04_DATABASE.md` Section 13
  and this codebase's existing architecture already commit to `cube`/`earthdistance` specifically because
  PostGIS is not an approved dependency per `12_TECH_STACK.md`; introducing it now would be unapproved
  infrastructure).

### Consequences

- This codebase's first documented precedent for raw parameterized SQL; any future query needing a database
  function/operator with no ORM mapping should follow the same shape (isolated in a dedicated repository method,
  fully bound parameters, no string interpolation) rather than re-deriving the reasoning or, worse, falling back
  to unsafe string formatting.
- `08_CODING_STANDARDS.md`'s "Database access must use SQLAlchemy ORM / parameterized queries" wording is
  confirmed, by this ADR, to be satisfied by bound `text()` queries — the requirement is parameterization, not
  exclusively the ORM's Python-object query builder.
- Any future maintainer touching `ProviderSearchRepository.search_nearby` must preserve the `earth_box`-before-
  `earth_distance` clause order (the GiST-indexed containment check narrowing candidates before the expensive
  exact recheck) — reordering or removing the `earth_box` clause would still be functionally correct but would
  silently regress AC6's index-usage guarantee.

### Related Documents

- 04_DATABASE.md (Section 13 — Geospatial Query Strategy)
- 06_SECURITY.md (SQL Injection Prevention)
- 08_CODING_STANDARDS.md
- docs/implementation/plans/Plan_S06_DIR-001.md (Decision 8)
- docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md

---

# ADR-027

## Title

Free-Text Category Filtering — Case-Insensitive Exact Match Against `provider_category_labels.label`, an Interim Search-Query Mechanism Pending the Real Category Taxonomy

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

`13_OPEN_DECISIONS.md` item 1 (Category Taxonomy, still Open) already documents PRO-002's `provider_category_labels`
table itself as a deliberate, flagged interim stand-in for the real `category.categories`/`provider_categories`
domain — but that decision (recorded only in `Plan_S04_PRO-002.md`/`Walkthrough_S04_PRO-002.md`, never given its
own ADR entry) only had to address *storing* free-text labels. Story DIR-001 is the first to need to *filter/match*
against this same ungoverned, unvalidated free-text field at query time — a genuinely new decision, since
matching semantics (exact vs. substring vs. fuzzy) over free text with no taxonomy to validate against carries a
real risk of silently wrong results that storage alone does not.

### Decision

`GET /search/providers?category=<value>` matches via a case-insensitive **exact** match
(`lower(pcl.label) = lower(:category)`) against any of a provider's `provider_category_labels` rows (not only the
primary one) — never a substring/`ILIKE` match. A free-text field with no taxonomy is exactly the situation where
substring matching produces silently wrong results with nothing to sanity-check against (e.g. `"AC"` matching
`"Vacation Cleaning"`) — an honest, narrow exact-match tool is chosen over a falsely-broad fuzzy one, the same
"never assert ungrounded data" principle `00_PROJECT_CONTEXT.md` applies to AI output, generalized here to search
matching. `category` is optional on the endpoint (omitting it browses across all categories, still filtered by
geo + discoverability). A new, small, deliberately **unpaginated** `GET /search/categories` endpoint (extending
ADR-012's exception to a platform-wide-but-genuinely-small collection, bounded by the number of distinct labels
real providers have actually typed, not by provider count) returns the case-normalized distinct set of labels
currently in use by `is_discoverable=true` providers, backing the mobile category-picker — never a hardcoded
client-side chip list, which would silently drift from whatever labels providers have actually entered.

### Alternatives Considered

- **Build a minimal real `categories` table now, even a handful of hardcoded rows** (rejected outright — item 1
  explicitly frames the taxonomy as blocking the entire AI question-flow design; inventing one as a side effect
  of a search story would pre-empt that larger, still-open product decision).
- **Substring/`ILIKE` matching** (rejected per the false-positive reasoning above — a substring match over
  ungoverned free text is more likely to mislead than help without a real taxonomy to bound it).
- **A hardcoded, static client-side chip list, no picker-source endpoint** (rejected — would drift from whatever
  labels providers have actually typed, which have zero validation against any fixed set, producing chips that
  either filter to empty results or omit categories real providers actually use).

### Consequences

- Any future story filtering or matching against `provider_category_labels` before the real Category Taxonomy
  (item 1) resolves should default to this same case-insensitive exact-match pattern, never substring/fuzzy
  matching, to avoid silently misleading results over ungoverned free text.
- Once item 1 resolves and the real `category.categories`/`provider_categories` domain ships, both this
  exact-match filter and the `GET /search/categories` endpoint are expected to be replaced by real
  `category_id`-based filtering — this decision is explicitly interim, mirroring ADR-017/018's "honest interim
  capability" precedent, not a preview of the real feature.
- `GET /search/categories` extends ADR-012's unpaginated-collection exception to a second, platform-wide (rather
  than single-owner-scoped) case — justified because its cardinality is bounded by real-world input (distinct
  labels providers have typed) rather than by data volume that grows with provider count.

### Related Documents

- 00_PROJECT_CONTEXT.md (Section 3 — "never assert ungrounded data" principle)
- 09_DECISIONS.md (ADR-012 — the unpaginated-collection exception this extends; ADR-017, ADR-018 — the "honest
  interim capability" precedent this mirrors)
- 13_OPEN_DECISIONS.md (item 1 — Category Taxonomy, still Open)
- docs/implementation/plans/Plan_S04_PRO-002.md (Decision 1 — the `provider_category_labels` storage precedent
  this extends to query-time matching)
- docs/implementation/plans/Plan_S06_DIR-001.md (Decision 1)
- docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md

---

# ADR-028

## Title

Idempotent Data-Seeding Migration Pattern — `ON CONFLICT ... RETURNING`-Gated Child Inserts, Plain-Data Source
Module, and a DDL-Existence-Check Guard on `upgrade()`

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Every one of this codebase's 8 prior Alembic migrations is schema/DDL only — none has ever inserted a data row.
Story `CTG-001` needed to seed the CTO-approved v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md` — 14
categories and 47 per-category question templates) into `category.categories`/`category.category_question_templates`
via a migration (`17_CATEGORY_TAXONOMY.md`'s own "Migration Notes for Implementation" section explicitly requires
this, so the seed ships identically across every environment rather than via manual `INSERT`s or an
application-level seed-on-startup mechanism, which `app/.agents/agents.md`'s Architecture Stability Rule would
treat as an unrequested parallel migration mechanism). This is a genuinely new pattern this codebase had not yet
established, and needed a concrete, empirically-provable idempotency mechanism — the story's AC4 explicitly
required proving no duplicate rows result from running `upgrade()` twice, or from `upgrade() → downgrade() →
upgrade()`, not merely trusting Alembic's own "don't reapply an already-applied revision" bookkeeping.

### Decision

A reusable three-part pattern for any future reference-data-seeding migration in this codebase:

1. **A plain-Python source-data module** (here, `backend/app/modules/category/seed_data.py`) holding the seed
   content as plain dicts/lists, with **no SQLAlchemy ORM import** — only plain data. This lets the same source
   be imported both by the migration (which, matching every existing migration's convention, uses raw
   `sa.table()`/Core constructs, never `app.modules.*.models` ORM classes) and by test fixtures, so the taxonomy
   is never transcribed twice (`08_CODING_STANDARDS.md`: never duplicate code/data).
2. **Parent-row inserts via `postgresql.insert(...).on_conflict_do_nothing(index_elements=[...]).returning(...)`**,
   against the table's own real unique constraint (here, `categories.slug`/`uq_categories_slug`) — capturing
   exactly which rows were *freshly inserted this run*, not the full candidate list. **Any child-row insert batch
   for a table with no unique constraint of its own** (here, `category_question_templates`, which
   `04_DATABASE.md`'s spec deliberately gives no unique constraint) **is gated transitively on its parent having
   been freshly returned** — a child batch is only ever inserted when its parent row was itself freshly inserted
   this run, so the parent's `ON CONFLICT DO NOTHING` propagates idempotency down to children with no unique
   constraint of their own, rather than inventing one purely to support seeding (which would be an unrequested
   schema deviation from the authoritative spec).
3. **An `upgrade()` DDL-existence-check guard** — `upgrade()` checks whether its target table(s) already exist
   (via `sa.inspect(bind).get_table_names(schema=...)`) before running `CREATE TABLE`/`CREATE INDEX` DDL, skipping
   DDL (but still running the idempotent seed step) if they do. A real `alembic upgrade head` run never actually
   re-invokes an already-applied revision's `upgrade()` — Alembic's own version-bookkeeping table prevents that —
   but this guard makes the function itself safely re-callable even when a test or an operator bypasses that
   bookkeeping and calls `upgrade()` directly against an already-migrated connection, which is exactly the shape
   `CTG-001`'s own idempotency tests use to prove AC4 empirically rather than by trusting Alembic's bookkeeping
   alone.

### Alternatives Considered

- **A standalone seed script run manually or via a deploy step, outside Alembic** — rejected: could be forgotten
  in any one environment, unlike a migration Alembic runs automatically as part of `alembic upgrade head`; also
  directly contradicted `17_CATEGORY_TAXONOMY.md`'s own explicit instruction against manual `INSERT`s.
- **Application-level "seed on startup" logic** — rejected: introduces a second, parallel seeding mechanism
  outside Alembic, which `app/.agents/agents.md`'s Architecture Stability Rule explicitly protects "Database
  migration strategy" against without explicit instruction.
- **Add a new unique constraint to the child table purely so it could use its own symmetric `ON CONFLICT DO
  NOTHING`** — rejected: `04_DATABASE.md`'s spec for `category_question_templates` lists exactly one index and no
  unique constraint; adding one not in the authoritative spec is an unrequested schema deviation. Gating child
  inserts on which parent rows were genuinely freshly returned achieves full idempotency without touching the
  spec at all.
- **Trust Alembic's own revision-bookkeeping alone as the idempotency guarantee, with no DDL-existence check in
  `upgrade()` itself** — rejected: this is exactly what the story's own AC4 wording ("upgrade run twice") asked
  to be proven true independent of that bookkeeping, and a bookkeeping-only guarantee would make a migration's
  own idempotency untestable outside the full `alembic upgrade head` CLI flow.

### Consequences

- Any future reference-data-seeding migration in this codebase (e.g. a future taxonomy edit, or a new reference
  table for another domain) should reuse this exact three-part shape: plain-data source module (no ORM import),
  `ON CONFLICT ... RETURNING`-gated parent inserts, child inserts gated on genuinely-fresh parent rows (not a
  fabricated unique constraint), and a DDL-existence-check guard on `upgrade()` if the migration's own idempotency
  needs to be provable by direct re-invocation, not merely inferred from Alembic's own bookkeeping.
- `category.categories`/`category.category_question_templates`'s seed content is now a data change (editing
  `seed_data.py` and writing a small follow-up migration to insert any newly-added rows), not a schema change —
  exactly the flexibility `04_DATABASE.md` Section 14 and `17_CATEGORY_TAXONOMY.md` both intended.
- `category.provider_categories` was created empty by this migration — this pattern was not applied to it, since
  no story yet writes to it (reconciling `provider.provider_category_labels` into it is a separate, deferred
  story).

### Related Documents

- 04_DATABASE.md (Category Domain section — `categories`, `category_question_templates`, `provider_categories`;
  Section 14 — Schema Flexibility Against Open Decisions)
- 08_CODING_STANDARDS.md (no duplicate code/data)
- 13_OPEN_DECISIONS.md (item 1 — Category Taxonomy, now closed at the implementation level by this story)
- 17_CATEGORY_TAXONOMY.md (the seeded content itself)
- docs/implementation/plans/Plan_S07_CTG-001.md (Decision 2 — the full design reasoning this ADR records)
- docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md

---

# ADR-029

## Title

Import-Time Synthetic Verification Approval for Google-Seeded Listings — `verification_status=approved` +
`is_discoverable=true` + a Matching, Never-Human-Reviewed `verification_records` Row; Structurally Excluded from
Ever Counting as a Real Verification Cycle

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Story `CLM-001` needed to reconcile two authoritative statements that must both be true at once for a Google-
seeded, unclaimed listing: `03_DOMAIN_MODEL.md` line 112 states a Provider seeded from Google "starts as Unclaimed
and is discoverable," while the DB-level `chk_providers_discoverable_requires_approved` constraint requires
`is_discoverable=false OR verification_status='approved'`. The only way both are true simultaneously is for the
import job itself to set `verification_status=approved` directly — not through the admin review queue, since at
import time there is no document, no submitter, and nothing for a human admin to review.

During `tester`'s review, this synthetic approval was found to have a real, undocumented consequence: once a
listing is claimed and `_finalize_claim` resets `providers.verification_status`/`is_discoverable` to
`pending`/`false` (Decision 6), the import-time synthetic `verification_records` row was still the provider's
"latest" record by `submitted_at`. `VerificationService.submit`'s resubmission-eligibility check and
`GET /providers/me/verification`'s status display both read `VerificationRecordRepository.get_latest_for_provider`
directly, not `providers.verification_status` — so a freshly claimed listing's first real verification submission
was rejected with a 409 (only a `REJECTED` latest record permits a new submission), and its status screen would
have shown a dishonest "Approved" despite the cached column already reading `pending`. This directly contradicted
AC5's literal "routes through the same Verification gate a self-registered Business would go through" — a
self-registered Business has no such stale record and submits cleanly on its first attempt.

### Decision

**Part 1 — creating the synthetic approval (import time):** the import job
(`ProviderService.create_google_seeded_provider`) sets `providers.verification_status=APPROVED`,
`is_discoverable=True` directly (this is a `create`, not an `update` through `apply_verification_outcome`, since
there is no existing provider row yet), and creates a matching `verification.verification_records` row in the
same operation: `status=APPROVED`, `verification_type=BUSINESS_LIGHTWEIGHT`, `reviewed_by=NULL` (no human admin
ever reviewed it — `reviewed_by` is already nullable), `submitted_at`/`reviewed_at` both `now()`. This keeps
`verification_records` — this codebase's documented source of truth for verification history — honestly in sync
with the cached `providers` columns, rather than a `providers.verification_status=approved` with no corresponding
audit row, which would be a silent, undocumented exception to that invariant.

**Part 2 — the reset at claim (Decision 6):** immediately on a successful claim, `_finalize_claim` resets
`providers.verification_status=PENDING`/`is_discoverable=False` via the existing
`ProviderService.apply_verification_outcome` — the literal mechanism of AC5's "routes through the same
Verification gate," leaving a claimed provider in the identical state a brand-new self-registered Business starts
in.

**Part 3 — the exclusion addendum (added during this story's review, closing the gap above):**
`VerificationRecordRepository.get_latest_for_provider` excludes any record matching `status=APPROVED AND
reviewed_by IS NULL` — the exact, exclusive signature of a system-generated, never-human-reviewed approval.
Confirmed exclusive by grepping every `VerificationRecord(status=APPROVED)` construction site in the codebase:
exactly two exist — `AdminVerificationService.approve` (always sets `reviewed_by=<the acting admin's id>`) and
`ProviderService.create_google_seeded_provider`'s import-time write (always leaves `reviewed_by=NULL`) — so this
`WHERE` clause can never misclassify a real, human-reviewed approval as synthetic. With this exclusion in place,
`get_latest_for_provider` returns `None` for a freshly claimed listing until it actually submits, exactly matching
a freshly self-registered Business's behavior for both the resubmission-eligibility check and the status display.

**This is a reusable pattern, not a one-off fix:** any future story that introduces another kind of
system-generated (non-human-reviewed) verification record should give it its own structurally-provable,
exclusive, non-human signature (a specific column value or combination no genuine human-reviewed record can ever
produce) and add it to this same exclusion clause, rather than inventing a parallel "latest record" query method.

### Alternatives Considered

- **Leave unclaimed listings at `verification_status=pending`, `is_discoverable=false` (hidden until claimed)** —
  rejected: directly contradicts `03_DOMAIN_MODEL.md`'s explicit "is discoverable" business rule, and would make
  AC2 ("visually distinct in search/directory results") untestable, since a non-discoverable provider never
  appears in search results at all.
- **Keep a claimed provider's `verification_status=approved` unchanged through claim (skip re-verification)** —
  rejected outright: this is precisely the outcome the story's own description forbids ("must never be treated as
  equivalent to a verified, self-registered provider").
- **A dedicated `verification_status` value like `google_verified`, distinct from `approved`** — rejected: no
  such value exists in the locked `verification_status` enum, and adding one is an unrequested schema change with
  no AC basis.
- **For the exclusion gap specifically — delete or mutate the synthetic `verification_records` row at claim time
  inside `_finalize_claim`** — rejected: `verification_records` is this codebase's documented source-of-truth
  audit trail; destroying or backdating a real historical row (even a synthetic one) to make a query behave
  correctly would trade an honest audit trail for a query-shape convenience.
- **A second, parallel "effective latest" query method used only by the claim path** — rejected as needless
  duplication when a single, correctly-scoped `get_latest_for_provider` serves every caller identically and
  correctly once the exclusion is added.

### Consequences

- A Google-seeded, unclaimed listing is honestly discoverable pre-claim (satisfying the domain model) while never
  being treated as a genuinely verified, self-registered Provider — the moment it is claimed, it re-enters the
  exact same trust gate a self-registered Business goes through.
- `verification_records` remains a complete, honest audit trail: the synthetic pre-claim approval is never
  deleted or rewritten, only excluded from "latest real cycle" queries by a structurally-provable signature.
- Any future system-generated verification record (of any kind) must be given its own exclusive, non-human
  signature and added to `get_latest_for_provider`'s exclusion clause — this is now the established pattern for
  that shape of problem, not something to re-derive from scratch.

### Related Documents

- 03_DOMAIN_MODEL.md (Provider domain — "starts as Unclaimed and is discoverable")
- 04_DATABASE.md (`providers` — `chk_providers_discoverable_requires_approved`; `verification_records` as source
  of truth)
- 09_DECISIONS.md (ADR-024 — `try_claim_for_review`'s optimistic-concurrency shape this story's `try_claim_for_
  account`, ADR-030, mirrors)
- docs/implementation/plans/Plan_S06_CLM-001.md (Decision 2)
- docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md
- backend/app/modules/verification/repositories/verification_record_repository.py
  (`get_latest_for_provider`'s docstring records this reasoning directly in code)

---

# ADR-030

## Title

Claim Finalization Pattern — Atomic Conditional `UPDATE` Race-Fix (`try_claim_for_account`), a Shared
`_finalize_claim` Helper Across Both Success Paths, and a New `administration.claim_review_requests`
Admin-API-Only Queue

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Story `CLM-001` needed a claim to finalize identically regardless of which of two paths triggered it — a
customer's successful OTP verification, or an admin approving a manual review request raised after an OTP failure
or an unusable public number (AC6). `Plan_S06_CLM-001.md`'s Decision 6 described finalization as "re-fetch the
target provider fresh... re-check `is_claimed=false`" — a plain read-then-write. `VER-002`'s own review had
already found and fixed an analogous "exactly one winner" concurrency bug for admin approve/reject actions
(`VerificationRecordRepository.try_claim_for_review`, ADR-024): two truly concurrent callers could both pass a
Python-level status check before either committed. The identical race shape exists here — two people could
concurrently attempt to claim the same still-unclaimed listing (e.g. two family members, or the OTP-success path
racing the admin-approval path for the same listing) — and a plain fetch-then-update would leave a window where
the second caller's write could silently overwrite the first claimant's `user_id` with no error at all.

### Decision

**The atomic conditional `UPDATE` (strengthening Decision 6 beyond its literal Plan text):**
`ProviderRepository.try_claim_for_account(provider_id, *, user_id, claimed_at)` issues a single `UPDATE providers
SET is_claimed=true, user_id=..., claimed_at=... WHERE id=... AND is_claimed=false`, returning whether the row was
actually affected. Postgres's row lock on the first matching writer, plus the `WHERE is_claimed=false` clause
re-evaluated against the now-current row, guarantees at most one caller's `UPDATE` can ever match — directly
mirroring `try_claim_for_review`'s already-proven shape (ADR-024) rather than inventing a second, different
optimistic-concurrency mechanism for the same class of problem.

**The shared `_finalize_claim` helper:** `ClaimService._finalize_claim(provider_id, user_id)` is the single,
private method that (1) enforces the existing one-Provider-per-Account rule (PRO-001), (2) calls
`try_claim_for_account`, raising `ClaimAlreadyClaimedError` if the row was no longer claimable, (3) resets
`verification_status=PENDING`/`is_discoverable=False` via `ProviderService.apply_verification_outcome` (ADR-029),
and (4) grants `ROLE_PROVIDER` via the existing `RoleAssignmentService`. Both `ClaimService.verify_otp` (the
OTP-success path) and `AdminClaimService.approve_review_request` (the admin-approved fallback path) call this
same method — it is the **only** place in the codebase that ever sets `is_claimed=True` — so the two success
paths can never silently drift into two different definitions of "claimed."

**The `administration.claim_review_requests` table (AC6's fallback, Decision 9):** a new, physical, writable
table (full `CommonColumnsMixin`, matching `admin_action_log`'s precedent rather than the exempted `audit_logs`),
mirroring `unmatched_query_reports`'s already-established shape for exactly this problem: "a physical table (not
a DB view) because admin review status must be writable and durable." Columns: `provider_id`,
`claimant_user_id`, `reason` (`otp_failed` | `no_public_number`), `status` (`open` | `resolved`, default `open`),
`resolution` (`approved` | `rejected`, set only when resolved), `resolution_notes`, `reviewed_by`, `reviewed_at`.
`ClaimReviewRequestService` (`administration` module) exposes exactly `create`/`list_open`/`resolve` — mirroring
`AdminActionLogService`'s "one explicit method per action" convention, not a generic CRUD surface.
`AdminClaimService` (`provider` module) depends on it the same way `AdminVerificationService` already depends on
`AdminActionLogService` (a `provider → administration` edge). Exposed at `/admin/claims`
(`require_role(ROLE_ADMIN)`-only, ADR-023's ownerless shape) — backend-API-only, no dashboard UI, per VER-002's
already-established "admin does something, no UI yet" precedent.

### Alternatives Considered

- **A plain read-then-write for claim finalization (the Plan's original literal text)** — superseded during
  implementation in favor of the atomic conditional `UPDATE`, once the same race shape ADR-024 already fixed for
  verification-record review was recognized here; confirmed correct and consistent with existing precedent by
  `architect` during this story's review.
- **No persistent table for AC6 — just notify "an admin" generically** — rejected: no "the admin team" recipient
  concept exists anywhere in this codebase (every notification precedent targets one specific user), and no
  existing flow proactively pushes work to an admin; admins pull from a queue (`GET /admin/verification/records`
  is the established precedent), which this story follows rather than inventing a push mechanism.
- **Reuse `manual_match_assignments` for the claim-review queue** — rejected: that table's `assigned_admin_id` is
  `NOT NULL` at creation, requiring a specific admin assigned up front, which doesn't fit "an unclaimed,
  unassigned queue item any admin may pick up."
- **Allow a claimant to already own another Provider (dual-listing account)** — rejected: no AC/domain text
  relaxes the existing, hard one-Provider-per-Account rule for the claim path specifically.

### Consequences

- Any future "exactly one caller wins a state transition on a shared row" problem in this codebase should default
  to the atomic conditional `UPDATE` pattern (`try_claim_for_review`, `try_claim_for_account`) rather than a plain
  read-then-write, per this and ADR-024's shared precedent.
- Any future customer-initiated success path that also has an admin-approved fallback path should extract one
  shared, private finalization helper both paths call, rather than duplicating the finalization logic — the
  `_finalize_claim` shape is now this codebase's precedent for that.
- `administration` now has a second physical review-queue table (`admin_action_log`, `claim_review_requests`)
  alongside the still-unbuilt `unmatched_query_reports`/`manual_match_assignments` — all following the same
  physical-table-not-a-view convention for admin-writable review state.

### Related Documents

- 02_ARCHITECTURE.md (Provider module's explicit "Claim flow" responsibility)
- 04_DATABASE.md (Administration Domain — `claim_review_requests`, `unmatched_query_reports` precedent)
- 09_DECISIONS.md (ADR-023 — ownerless `require_role(ROLE_ADMIN)` shape; ADR-024 — `try_claim_for_review`'s
  atomic conditional `UPDATE` precedent this story's `try_claim_for_account` mirrors; ADR-029 — the
  `apply_verification_outcome` reset this helper calls)
- docs/implementation/plans/Plan_S06_CLM-001.md (Decision 6, Decision 9)
- docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md
- backend/app/modules/provider/services/claim_service.py (`_finalize_claim`'s docstring records this reasoning
  directly in code)

---

# ADR-031

## Title

`GooglePlacesClient` Swappable Protocol — Third Application of the `FileStorage`/`DocumentOcrService`
Protocol-Swappability Pattern (ADR-017, ADR-018)

**Date**

2026-09-09

**Status**

Accepted

**Owner**

CTO

### Context

Story `CLM-001`'s import job needs to call the Google Places API, a paid third-party service with no existing
client, SDK, or credential anywhere in this codebase. Automated tests (AC8, and the import job's own tests)
cannot make real network calls to a billed external API. This is not a new problem for this codebase — ADR-017
(`FileStorage`) and ADR-018 (`DocumentOcrService`) already established the same answer twice for the same shape
of problem ("an external capability with no live-tested implementation available in CI"): a swappable Protocol
plus a concrete real implementation, never a hardcoded direct call.

### Decision

This is the third, unmodified application of that same established pattern — not a new pattern requiring its own
design discussion. `provider/services/google_places_client.py` defines a `GooglePlacesClient` Protocol
(`search_places`, `get_place_details`), with `HttpxGooglePlacesClient` as the real implementation (using the
already-approved `httpx` dependency, no new package — Places API is a plain REST/JSON API) and
`FakeGooglePlacesClient` (test-only, returns canned fixture places). The import job's service layer depends on
the Protocol, never the concrete class, exactly like `VerificationService` depends on `DocumentOcrService`. A new
`GOOGLE_PLACES_API_KEY: str | None = None` setting is added as **optional** — deliberately unlike
`GOOGLE_OAUTH_CLIENT_ID`'s required style — since it is consumed only by the standalone import script, not by the
running API application every request depends on; the script fails fast with a clear, actionable error if invoked
while unset, rather than the whole app refusing to boot in every environment that never runs the import job.

### Alternatives Considered

- **A third-party Google Maps/Places Python SDK dependency** — rejected: `httpx` direct REST calls are sufficient,
  and adding a new SDK dependency needs explicit approval per `.agents/agents.md` that no AC requests.
- **Make `GOOGLE_PLACES_API_KEY` required like `GOOGLE_OAUTH_CLIENT_ID`** — rejected: would force every
  environment, including CI and every developer's local `.env`, to hold a real or dummy Places API key just to
  boot the FastAPI app, for a capability only the standalone script ever touches.

### Consequences

- This is now this codebase's third confirmed application of the Protocol-swappability pattern for an
  unconfirmed/untestable external capability (`FileStorage`, `DocumentOcrService`, `GooglePlacesClient`) — any
  future story facing the same shape of problem should default to it without re-deriving the design from
  scratch.
- A future story adding real Places API credentials to a live environment changes zero application code — only
  configuration (`GOOGLE_PLACES_API_KEY`) and which concrete class the import script constructs.

### Related Documents

- 09_DECISIONS.md (ADR-017 — `FileStorage`, the pattern's origin; ADR-018 — `DocumentOcrService`, the pattern's
  second application)
- docs/implementation/plans/Plan_S06_CLM-001.md (Decision 10)
- docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md

---

# ADR-032

## Title

`AI-001`/`AI-002` Scope Boundary — Conversation Domain Ends at `conversation_sessions.status ∈ {completed,
routed_to_admin}`, Tracker-Confirmed

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

`14_USER_FLOWS.md` Flow 4 describes one continuous journey (free-text description → guided questions → ranked
provider list) but the Tracker splits Sprint 7's Conversation/AI Intake domain into two stories, `AI-001`/
`AI-002`. `Plan_S07_AI-001.md` originally inferred the scope boundary from `04_DATABASE.md`'s
`search_request_status` enum (`matched`/`unmatched`/`pending_manual_match` — all matching *outcomes*, with no
"submitted, awaiting processing" value), before the Tracker's verbatim `AI-002` row could be read directly.

### Decision

`AI-001` owns the `conversation` schema/module only: it ends at `conversation_sessions.status ∈ {completed,
routed_to_admin}`, with **zero** writes to `search.search_requests`/`provider_matches`/`search_event_log` or
`administration.manual_match_assignments`. This is now **Tracker-confirmed**, not merely inferred: the verbatim
`AI-002` row states its own scope boundary as "does not include the admin-side queue UI itself (`ADM-001`) — this
story implements the routing/data model side and the customer-facing continuity guarantee," which presupposes
`AI-002` — not `AI-001` — is the story that creates the manual-match routing/assignment records and any
`search_requests` row. The mobile completion state after a `completed`/`routed_to_admin` session is an honest,
plain confirmation ("Thanks — we're finding matches for you"), never a fabricated results list, since no results
exist yet at the code level — the same "ship a real, complete domain slice ahead of its future consumer" shape
`CTG-001` already established for `CategoryService`.

### Alternatives Considered

- **Build the whole Flow 4 (conversation + matching + results) as one story** — rejected: `.agents/agents.md`
  explicitly instructs not to combine stories without explicit instruction; the verbatim `AI-002` row confirms two
  stories were intended.
- **Create `search_requests` now with a new, unspecified `pending`/`submitted` status value** — rejected: adds an
  enum value to a table this story doesn't otherwise need to touch, purely to paper over a scope question.

### Consequences

- `AI-002` is now the confirmed owner of `search.search_requests` creation, real matching, and
  `administration.manual_match_assignments` — it reads `conversation_sessions.structured_criteria` (ADR-033) as
  its input rather than re-deriving it from raw `messages`.
- The boundary evidence (the locked `search_request_status` enum having no "submitted" value) remains valid and
  citable for any future story questioning this split.

### Related Documents

- 04_DATABASE.md (`search_request_status` enum; Conversation / AI Intake Domain)
- 14_USER_FLOWS.md Flow 4
- docs/implementation/plans/Plan_S07_AI-001.md (Decision 1)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md

---

# ADR-033

## Title

`conversation_sessions.structured_criteria` (JSONB) — a `search_requests`-Ready, Pydantic-Validated Payload That
Never Crosses the `search`-Schema Boundary

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

AC9 requires "every completed session produces a `search_requests`-ready `structured_criteria` payload, validated
via a Pydantic model before persistence." Writing directly to `search.search_requests` would violate ADR-032's
scope boundary, yet AC9 is a verbatim, explicit requirement of this story.

### Decision

Add `conversation_sessions.structured_criteria` — `JSONB`, nullable, populated only when a session reaches
`status=completed`. Shape, validated by `StructuredCriteria`/`StructuredCriteriaAnswer`
(`conversation/services/structured_criteria.py`) before the column is ever written: `category_id`, `category_slug`,
and an ordered `answers: list[{question_id, question_text, answer_text}]` — a generic, category-agnostic shape
built from the resolved `Category` and every answered `is_required=true` `CategoryQuestionTemplate` paired with
its persisted `messages.content` answer. `ConversationService._complete_session` builds and validates this
instance, then persists `structured_criteria.model_dump(mode="json")` in the same transaction that sets
`status=completed`; a `ValidationError` at this point raises `InvalidStructuredCriteriaError` (500) rather than a
raw Pydantic error. A `routed_to_admin` session leaves `structured_criteria` `NULL` — there is no complete,
validated answer set to build it from.

This satisfies AC9 without violating ADR-032's scope boundary: the payload lives entirely inside the
`conversation` schema, is genuinely `search_requests`-*ready* (its shape maps cleanly onto plausible future
`search_requests` filter columns) without this story creating or writing to `search_requests` itself. `AI-002` (or
a later story) is the one that reads `conversation_sessions.structured_criteria` to build the actual
`search_requests` row.

### Alternatives Considered

- **Compute `structured_criteria` on-the-fly at read time (a service method, not a persisted column)** —
  rejected: AC9 is explicit that persistence, not mere computability, is part of the requirement; a persisted
  column is also directly queryable/auditable by `AI-002` without re-deriving it from the full `messages` history.
- **A separate `structured_criteria` table instead of a column** — rejected as unrequested schema scope creep; a
  1:1 relationship with `conversation_sessions` is simpler as a nullable JSONB column, the same reasoning
  `04_DATABASE.md` already applies to `conversation_sessions.final_confidence_score`.

### Consequences

- `AI-002` has a real, validated, queryable input to build `search_requests` from, without ever needing to
  re-parse raw `messages` rows itself.
- Any future story revising a completed session (Decision 5, ADR-036) must clear a stale `structured_criteria`
  rather than leave it inconsistent with the actual answer history — already implemented as part of
  `revise_answer`.

### Related Documents

- 04_DATABASE.md (Conversation / AI Intake Domain; `search.search_requests`)
- 09_DECISIONS.md (ADR-032 — the scope boundary this decision satisfies AC9 within)
- docs/implementation/plans/Plan_S07_AI-001.md (Decision 1b)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md
- backend/app/modules/conversation/services/structured_criteria.py

---

# ADR-034

## Title

`ConversationAiClient` Swappable Protocol — Fourth Application of the `FileStorage`/`DocumentOcrService`/
`GooglePlacesClient` Pattern, with a `process_turn` Signature Generalized Beyond the Original Plan Sketch

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

No LLM provider, SDK, or credential is confirmed anywhere in this codebase. This is the fourth time this project
has hit exactly this shape of problem — an external capability with no confirmed implementation — after
`FileStorage` (ADR-017), `DocumentOcrService` (ADR-018), and `GooglePlacesClient` (ADR-031), each solved the same
way: a swappable Protocol plus an honest concrete interim implementation.

### Decision

`conversation/services/conversation_ai_client.py` defines `ConversationTurnResult` (`reply_message`,
`reply_message_ar`, `resolved_category_id`, `is_complete`, `confidence`, `quick_reply_options`), the
`ConversationAiClient` Protocol, and `RuleBasedConversationAiClient` — the only implementation this story ships.
Category resolution is a case-insensitive substring match against each active category's `name`/`name_ar`/`slug`;
zero or multiple matches return a clarifying quick-reply prompt, never a guess (AC4). Follow-up questions walk a
resolved category's required templates in `sort_order`, verbatim — the client has no natural-language generation
capability at all beyond echoing template/category data, so AC10's grounding requirement holds by construction.
Confidence is `0.0`/rising in equal steps/`1.0`, tagged `model_version="rule_based_v1"`. `ConversationService`
depends on the Protocol only, wired via `conversation/dependencies.py:get_conversation_ai_client()` — neither API
routes nor the mobile screen ever import a concrete client, which is what AC2 itself requires.

**Signature deviation from the Plan's literal sketch, deliberately made during implementation:** `Plan_S07_AI-001
.md`'s Decision 2 sketched `process_turn(..., active_question: CategoryQuestionTemplate | None, ...)`. Implementing
that same Decision's own described *behavior* — walking questions one at a time while also tracking "how many
required questions remain" for the equal-step confidence calculation — turned out to be impossible from a single
`active_question` value alone, and there is no `active_question` to hand it at all in the same-turn
category-resolution case, since the category is being resolved for the first time inside that very call. The
shipped signature instead takes `question_templates_by_category: dict[uuid.UUID, list[CategoryQuestionTemplate]]`
— every active category's templates, keyed by `category_id` — which `ConversationService` assembles once per turn
from `CategoryService` (small: 14 categories, ~47 templates in the seeded taxonomy, cheap to refetch every turn
rather than cache). This closes the circular dependency cleanly: a category resolved in the same call already has
its templates available for the very next line of the method to use. This is judged a sound generalization, not a
design regression — it implements the same Decision 2 behavior the Plan described, using a strictly more capable
input shape, with no other change to Decision 2's design or guarantees.

### Alternatives Considered

- **Wire a real LLM API now, picking a provider unilaterally** — rejected: requires explicit approval per
  `.agents/agents.md`, and would be unverifiable work without a real credential to test against.
- **Keep the Plan's literal single-`active_question` signature and derive "how many remain" some other way** —
  rejected: every alternative considered (a separate count parameter, a second Protocol method) either duplicated
  information already available in the full per-category template list or split one logical "what does this
  client need to know" concept across multiple parameters for no benefit.

### Consequences

- This is now this codebase's fourth confirmed application of the Protocol-swappability pattern (`FileStorage`,
  `DocumentOcrService`, `GooglePlacesClient`, `ConversationAiClient`) for an unconfirmed/untestable external
  capability.
- A future real LLM implementation (`OpenAiConversationAiClient`, `AnthropicConversationAiClient`, or whichever
  vendor is chosen once `13_OPEN_DECISIONS.md` item 13 resolves) is one new class plus one dependency-wiring
  change, implementing the same `process_turn(..., question_templates_by_category, ...)` signature — the
  generalization made here means a real client's own confidence/question-tracking logic is not artificially
  constrained by a single-question view of the world either.

### Related Documents

- 09_DECISIONS.md (ADR-017, ADR-018, ADR-031 — the pattern's prior three applications)
- docs/implementation/plans/Plan_S07_AI-001.md (Decision 2)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md
- backend/app/modules/conversation/services/conversation_ai_client.py (the deviation is recorded directly in the
  module's own docstring)

---

# ADR-035

## Title

AC3 and AC5 Are Honest, CTO-Accepted MVP Gaps Under the Rule-Based Interim `ConversationAiClient` — Deferred to
`13_OPEN_DECISIONS.md` Item 13

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

Two of `AI-001`'s 11 verbatim acceptance criteria are structurally unsatisfiable by `RuleBasedConversationAiClient`
(ADR-034): AC3 ("system prompts are stored as version-controlled files, not inline strings") and AC5 ("a retrieved
provider record with a null field is reported to the customer as unknown, never estimated or guessed"). The
rule-based client has no LLM prompts at all — it does deterministic substring matching and verbatim template
lookups — and never retrieves or discusses a specific provider record mid-conversation, since ADR-032's scope
boundary keeps this story out of `provider.providers` entirely.

### Decision

The CTO explicitly accepted shipping the rule-based interim client for MVP (mirroring the same risk-acceptance
pattern `13_OPEN_DECISIONS.md` item 3 already used for `CLM-001`'s Google Places decision), with AC3 and AC5
recorded honestly as **not met** by this implementation — "Deferred (MVP gap)" in the Verification Plan, never
"Satisfied." A placeholder "system prompt" file with no real content, or a fabricated synthetic provider record
just to exercise AC5's code path, were both explicitly rejected as decorative compliance that would prove nothing
true about the shipped system.

**This is a genuine product-differentiator gap, not a stub-infrastructure gap.** Unlike `FileStorage`,
`DocumentOcrService`, or `GooglePlacesClient` — where the *mechanism* (storage, OCR, a Places API call) is fully
real and only the specific vendor is interim/local — here the entire conversational intelligence is scripted and
deterministic; there is no prompt-driven reasoning or live grounding happening at all yet. Recorded as a new
`13_OPEN_DECISIONS.md` item 13, tracking (a) which real LLM vendor to select, (b) AC3 (meaningful only once real
prompts exist), and (c) AC5 (meaningful only once real provider retrieval exists) as one open, CTO-approved MVP
gap that must stay visibly open, not silently forgotten.

### Alternatives Considered

- **Write a placeholder "system prompt" file with no real content, just to check the AC3 box** — rejected as
  decorative compliance.
- **Fabricate a synthetic "provider record" with a null field just to exercise AC5's code path** — rejected: this
  story's scope boundary already excludes any provider-record retrieval from this domain; a fake retrieval solely
  to test an AC not really being exercised by production logic would assert nothing true.
- **Block the entire story on selecting a real LLM vendor first** — rejected: the Protocol boundary, the full
  `conversation` schema, the confidence/turn-cap mechanics, the revise-a-previous-answer flow, and 9 of 11 ACs are
  all real, valuable, and fully buildable and testable today, independent of which LLM is eventually chosen.

### Consequences

- `13_OPEN_DECISIONS.md` item 13 is the single authoritative place tracking this gap — any future story or review
  should check it before assuming AC3/AC5 are either resolved or forgotten.
- The moment a real LLM+RAG implementation is built (item 13's resolution), AC3 and AC5 become directly testable
  and required — this ADR's deferral has a clear, concrete trigger for revisiting it.

### Related Documents

- 09_DECISIONS.md (ADR-034 — the Protocol this gap is a property of; the item-3 Google Places precedent this
  mirrors)
- docs/AI/13_OPEN_DECISIONS.md (item 13, item 3 — the precedent for documenting a deliberate MVP gap)
- docs/implementation/plans/Plan_S07_AI-001.md (Decision 2b)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md

---

# ADR-036

## Title

Revising a Previous Answer — Truncate-and-Regenerate via Soft-Delete on a Partial Unique Index, Corrected from an
Originally-Planned Hard Delete; the Additive `conversation_status.abandoned` Value

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

AC8 requires the customer be able to revise a previous answer without restarting the conversation. Editing an
early answer can invalidate every AI question that came after it. `Plan_S07_AI-001.md`'s Decision 5 originally
specified a hard `DELETE` of every truncated message, reasoned as necessary because "`messages` has no
`deleted_at`/soft-delete column... unlike `CommonColumnsMixin`-based tables." During `architect` review, this
premise was found to be factually wrong: `Message(CommonColumnsMixin, Base)` (`backend/app/modules/conversation/
models.py`) *is* `CommonColumnsMixin`-based and *does* already have `deleted_at`/`is_active`
(`backend/app/database/mixins.py`). A hard `DELETE` of customer conversation transcript data, triggered by a
customer-initiated revise rather than an administrative action, violated `04_DATABASE.md`'s "Common Columns" rule
that permanent deletion is an administrative operation — `audit.audit_logs`/`search.search_event_log` are the
only stated exemptions, and `messages` is neither.

### Decision

`PATCH /conversations/{session_id}/answers/{message_id}` (a) updates the target message's content, (b)
**soft-deletes** every message (customer and AI alike) with a strictly greater `sequence_number` in the same
session — `MessageRepository.delete_after_sequence` sets `deleted_at`/`is_active=False`, mirroring
`SavedAddressRepository.soft_delete`'s exact convention, never a hard `DELETE` — and (c) re-invokes
`ConversationAiClient.process_turn` with the now-shorter, active-only history to generate the next turn fresh.
`list_for_session` and `get_next_sequence_number` filter `is_active.is_(True)` so a soft-deleted message is
invisible to the transcript and never double-counted when assigning the next `sequence_number` — the
customer-visible behavior (truncated messages disappear, sequence numbers continue correctly) is unchanged, only
the persistence mechanism is. If the truncated history no longer has a complete answer set, any previously
computed `structured_criteria` on that session (ADR-033) is cleared until the session re-completes.

This required promoting `uq_messages_session_sequence` from a plain table-level `UniqueConstraint` to a **partial**
unique index scoped `WHERE is_active = true` (mirroring `uq_saved_addresses_customer_default`'s existing
precedent), so a regenerated turn can reuse a soft-deleted row's old `sequence_number` without a constraint
conflict. A revise-triggered `PATCH` on an already-`completed`/`routed_to_admin` session reverts it to `active`
before reprocessing; an `abandoned` session can never be revised (`AnswerNotRevisableError`) since it was
superseded by a newer session.

**A small, additive enum value:** `conversation_status` gains `abandoned` — set when a customer starts a new
session while a previous one is still `active`. Genuinely new beyond `04_DATABASE.md`'s previously-explicit text
(`active`/`completed`/`routed_to_admin`), flagged for and now completed as a `04_DATABASE.md` update at this
story's close.

### Alternatives Considered

- **In-place edit only, leave subsequent AI messages stale** — rejected: would show AI questions that no longer
  make sense for a revised answer, directly undermining trust.
- **Hard-delete truncated messages (the Plan's original text)** — **superseded, this ADR's own correction**: the
  premise that `messages` lacked a soft-delete column was factually wrong; soft-delete is this codebase's standing
  convention for exactly this shape of problem, and hard-delete was the actual violation.
- **Silently leave `active` sessions abandoned with no status change when a new one starts** — rejected: makes
  "how many conversations did a customer actually finish vs. give up on" ungoverned and unqueryable.

### Consequences

- Any future story needing to "remove" rows from a `CommonColumnsMixin`-based table in response to a
  customer-initiated action (not an administrative one) should default to soft-delete plus a partial unique index
  scoped `WHERE is_active = true` if uniqueness needs to tolerate a superseded row's old key being reused — this
  is now the second confirmed application of that exact pattern (`saved_addresses`, `messages`).
- A Plan's own stated alternatives-considered reasoning is not automatically correct just because it's written
  down — `architect` review caught a factual premise error here that a less-thorough review might have accepted
  at face value; this is recorded so future reviews keep verifying claims like "table X has no column Y" against
  the actual model/mixin code, not just the Plan's prose.

### Related Documents

- 04_DATABASE.md (Common Columns soft-delete rule; `saved_addresses`' `uq_saved_addresses_customer_default`
  precedent; Conversation / AI Intake Domain)
- 09_DECISIONS.md (ADR-015 — the `uq_saved_addresses_customer_default` partial-unique-index precedent this
  mirrors)
- docs/implementation/plans/Plan_S07_AI-001.md (Decision 5, including its own "Correction (post-implementation,
  `architect` review)" note)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md
- backend/app/modules/conversation/repositories/message_repository.py (`delete_after_sequence`'s docstring
  records this reasoning directly in code)
- backend/alembic/versions/2026_09_10_1000-ef7b7d439f40_conversation_domain.py

---

# ADR-037

## Title

Cross-Module Wiring for `AI-002`: `conversation → search`, `search → administration`, `search → customer` — Confirmed Cycle-Free

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

`AI-002` (routing low-confidence AI-Conversation sessions to manual matching) needs three new pieces of persisted
state (`search.search_requests`/`provider_matches`/`search_event_log`,
`administration.manual_match_assignments`) created and read from several call sites, without introducing a
circular module dependency. `ConversationService` needs to trigger both the automated-match path and the
manual-assignment path from the same two terminal session transitions (`completed`, `routed_to_admin`).

### Decision

A single new outgoing edge from `conversation`, plus two new outgoing edges from `search`, mirroring
already-proven shapes (ADR-014/016/030) rather than inventing a new mechanism:

- **`conversation → search`** (new): `ConversationService` gains one new constructor dependency,
  `search_request_service: SearchRequestService`. The single call site is inside `_apply_completion_policy`,
  immediately after a session transitions to `completed` **or** `routed_to_admin` — both branches call the same
  `handle_session_completed(...)`, which internally branches on `status`. `search` receives plain primitives
  (`session.id`, `session.customer_id`, `category_id`, `category_name`, `structured_criteria`, `status` as a plain
  string) — never a `ConversationSession` ORM object — so `search` has zero imports from `conversation`.
- **`search → administration`** (new): `SearchRequestService` depends on
  `administration.ManualMatchAssignmentService` to create a `manual_match_assignments` row when routing, and to
  resolve it when an admin acts. `administration` receives only `search_request_id: uuid.UUID` as a plain value —
  zero imports from `search`.
- **`search → customer`** (new): `SearchRequestService` depends on `customer.SavedAddressService` (already
  shipped, CUS-002) to resolve the customer's default saved address for the automated-matching path. `customer`
  has zero imports from `search`.
- **`search → provider`** (already existed, DIR-001, reused unchanged): `SearchRequestService` depends on the
  existing `SearchService` (which already depends on `ProviderService`) to run the actual matching query.

**Confirmed cycle-free:** `search`, `administration`, and `customer` each have zero imports of `conversation`, of
each other in the reverse direction, or of `conversation`'s models — every edge above is one-directional,
identical in kind to every cross-module edge this codebase has shipped since ADR-014. `search` is kept as the
single owner of both *creating* a `manual_match_assignments` row and *finalizing* its resolution into
`provider_matches`/`search_requests.status` (see ADR-040), rather than splitting those two responsibilities
across `conversation`/`administration`, which was rejected specifically because it would create the exact cycle
risk (`conversation → administration → search → conversation`, or `search → administration → search`) this
Decision avoids.

### Alternatives Considered

- **`conversation → administration` directly**, bypassing `search` for the manual-assignment creation —
  rejected: would split assignment-creation from assignment-resolution across two different owning modules,
  creating a genuine cycle risk.
- **A domain-event bus** — rejected for the same reason ADR-014/016 already rejected it: no event-bus
  infrastructure exists anywhere in this codebase; building one for these call sites would be premature
  abstraction.

### Consequences

- `search` is now a real cross-module hub (depends on `provider`, `customer`, and `administration`) while
  remaining depended-upon by nothing except `conversation` — any future domain needing to react to a
  `search_requests` outcome should extend `SearchRequestService`'s own call sites, not add a new inbound edge
  from `search` into itself.
- This is the fourth distinct domain (`conversation`) shown to compose cleanly against the existing
  constructor-injection cross-module pattern first established at ADR-014 — the pattern continues to scale
  without a message bus.

### Related Documents

- 09_DECISIONS.md (ADR-014/016 — the constructor-injection cross-module pattern this mirrors; ADR-030 — the
  `provider`-owns-both-halves precedent `search` mirrors here; ADR-032 — `AI-001`'s own scope boundary that
  assigned this story ownership of `search`/`administration`)
- docs/implementation/plans/Plan_S07_AI-002.md (Decision 1)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-002.md
- backend/app/modules/search/services/search_request_service.py
- backend/app/modules/conversation/services/conversation_service.py (`_apply_completion_policy`)

---

# ADR-038

## Title

Four Flagged, Necessary Nullable-Column Deviations in the `search`/`administration` Schema (`AI-002`)

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

`04_DATABASE.md`'s pre-existing literal spec for `search.search_requests` states `category_id`,
`structured_criteria`, `customer_latitude`, and `customer_longitude` as `NOT NULL`, and
`administration.manual_match_assignments.assigned_admin_id` as `NOT NULL`. Building `AI-002` against real code
paths found all five columns cannot honestly always hold a value:

- **`assigned_admin_id`** — `ADR-030` already found, in `CLM-001`'s context, that `NOT NULL` here "doesn't fit
  'an unassigned queue, any admin may pick up.'" `AI-002` is the story that actually builds this table.
- **`structured_criteria`** — a `routed_to_admin` session (`AI-001`'s own Decision 1b/ADR-033) always leaves
  `conversation_sessions.structured_criteria = NULL` — there is no complete, validated answer set to build one
  from.
- **`customer_latitude`/`customer_longitude`** — no location-collection step exists anywhere in the AI
  Conversation flow, and adding one is materially larger than this story's scope.
- **`category_id`** (found during implementation, beyond the Plan's original three) — a `routed_to_admin` session
  reached via `AI-001`'s hard turn cap (`CONVERSATION_MAX_TURNS`) can occur with no category ever resolved at all
  — confirmed against `RuleBasedConversationAiClient._resolve_category`/
  `ConversationService._apply_completion_policy`, neither of which requires `category_id` to be set before
  routing to the turn-cap outcome.

### Decision

All five columns are nullable. Each is populated honestly whenever a real value exists, and left `NULL` — never
fabricated — when it doesn't:

- `manual_match_assignments.assigned_admin_id` — populated only at resolution (the admin who resolved it), `NULL`
  while `status = pending`, mirroring `claim_review_requests.reviewed_by`'s exact nullable-until-resolved shape.
- `search_requests.structured_criteria` — `NULL` for a `routed_to_admin` session; the admin resolving it works
  from the raw transcript context instead (out of this story's scope to expose richly).
- `search_requests.customer_latitude`/`customer_longitude` — `NULL` if the customer has no default saved address;
  the request row is still created (never blocked, AC2), resolving to `unmatched` honestly rather than a guessed
  `(0, 0)` or a country centroid. Deliberately independent of AC2's confidence-based routing: a high-confidence
  session with no saved address still completes automatically as `unmatched`, rather than being silently
  rerouted to the manual queue for an unrelated reason.
- `search_requests.category_id` — `NULL` for a turn-cap-routed session that never resolved a category; making it
  `NOT NULL` would force fabricating a category, the exact anti-fabrication violation the other three deviations
  already reject.

This is the same resolution this codebase has applied to every prior instance of "the locked spec doesn't fit
what the real code path can honestly provide" (`00_PROJECT_CONTEXT.md` §3, first applied at this scale by
`AI-001`'s own Decision 1b/2b) — make the column nullable and report the honest absence, never fabricate a value.

### Alternatives Considered

- **Leave the columns `NOT NULL` and block/error when data is missing** — rejected: directly violates AC2's "the
  session is never left in limbo with no next step," and would make a customer with no saved address unable to
  ever complete an AI-conversation search.
- **Fabricate a value** (an "unassigned" sentinel UUID, an empty `structured_criteria` object, a country-centroid
  lat/lng, a default/"uncategorized" category row) — rejected outright as exactly the "silently degrading to a
  low-quality automated match" pattern both the story's own text and `00_PROJECT_CONTEXT.md` §3 prohibit.

### Consequences

- Any future consumer of `search_requests`/`manual_match_assignments` (most immediately `ADM-001`'s admin
  dashboard) must treat all five of these columns as genuinely optional in its own UI/logic, not assume they are
  always populated.
- `04_DATABASE.md` is updated to record all four `search`/`administration` deviations plainly (Section update,
  this closeout) — the fifth ADR-030-flagged one (`assigned_admin_id`) is the same finding, now actually built.

### Related Documents

- 00_PROJECT_CONTEXT.md §3 (anti-fabrication hard constraint)
- 09_DECISIONS.md (ADR-029/ADR-030 — the prior nullable/anti-fabrication precedents this mirrors; ADR-033 — the
  `structured_criteria` payload this deviation is downstream of)
- 04_DATABASE.md (Search Domain, Administration Domain — updated at this closeout)
- docs/implementation/plans/Plan_S07_AI-002.md (Decision 2)
- backend/app/modules/search/models.py (module docstring documents all four deviations directly in code)
- backend/app/modules/administration/models.py (`ManualMatchAssignment`'s docstring)

---

# ADR-039

## Title

`administration.ManualMatchAssignmentService` — Fourth Application of the Passive-Queue-Row Pattern; Atomic `try_resolve` as the Third Application of the Atomic-Conditional-Update Pattern

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

AC2 requires that a low-confidence session "notify an admin" without leaving the customer in limbo. `ADR-030`
already established that no push-notification/"admin team recipient" concept exists anywhere in this codebase,
and that a pull-based queue (an admin polls a list endpoint) is this codebase's standing answer for "admin
becomes aware of new work" — first built for `admin_action_log`/VER-002, reused for `claim_review_requests`/
CLM-001. `AI-002` needs a fourth instance for `manual_match_assignments`.

During `architect` review, a second problem surfaced: the initially-shipped `ManualMatchAssignmentService.resolve()`
was a plain read-then-write (`get_by_id` → a Python `status` check → `repository.update`), leaving a genuine
TOCTOU race for two concurrent admins resolving the same assignment — both could pass the Python-level check
before either commits, both proceeding into `SearchRequestService._finalize_matches` and writing a duplicate
`provider_matches` batch and `search_event_log` row for one `search_requests` row.

### Decision

**Part 1 — the queue pattern (fourth application):** `ManualMatchAssignmentRepository`/`ManualMatchAssignmentService`
expose exactly `create`, `list_pending`, `get_by_id`, `resolve` — four explicit methods, no generic CRUD,
mirroring `ClaimReviewRequestService`'s shape file-for-file. `GET /admin/search/manual-matches`
(`require_role(ROLE_ADMIN)`, ownerless per ADR-023) is the queue an admin (or a future `ADM-001` dashboard) polls
— the "notify" mechanism, reused for a fourth time rather than invented anew.

**Part 2 — the atomic-conditional-update fix (third application):** `ManualMatchAssignmentRepository.try_resolve`
performs a single conditional `UPDATE manual_match_assignments SET status='completed', assigned_admin_id=...,
completed_at=... WHERE id = :id AND status = 'pending'`, checking `rowcount == 1`. This is the **third**
application of the exact atomic-conditional-update pattern first established by
`VerificationRecordRepository.try_claim_for_review` (VER-002, ADR-024) and reused by
`ProviderRepository.try_claim_for_account` (CLM-001, ADR-030) — Postgres takes a row lock on the first matching
writer under READ COMMITTED; a concurrent second `UPDATE` targeting the same row blocks until the first commits,
then re-evaluates its own `WHERE` clause against the now-current (already-completed) row, so at most one caller's
`UPDATE` can ever match, even under true concurrency. `ManualMatchAssignmentService.resolve()` now calls
`try_resolve` and raises `ManualMatchAssignmentAlreadyResolvedError` (409) on `False`, rather than trusting a
Python-level check that a concurrent commit could invalidate between the check and the write.

Proven with a genuine two-independent-database-session concurrency test (`TestTryResolveAtomicity`), not merely a
sequential-call assertion — the same standard `try_claim_for_review`'s original fix was held to.

### Alternatives Considered

- **A database-level `SELECT ... FOR UPDATE` row lock, held across the read-then-write** — rejected as
  unnecessary ceremony when a single conditional `UPDATE` achieves the identical guarantee more simply, and
  would be a new locking idiom this codebase hasn't used anywhere else, when the atomic-`UPDATE` idiom already
  has two clean precedents.
- **Optimistic concurrency via a version column** — rejected: no table in this codebase uses row versioning; the
  conditional-`UPDATE`-on-status pattern is the established, working answer for "exactly one caller wins" here.

### Consequences

- Any future admin-resolvable queue-row table (a fifth application) should default to this same
  conditional-`UPDATE` shape rather than a read-then-write, per this codebase's now three-times-confirmed
  precedent.
- `SearchRequestService.resolve_manual_match` was also reordered (see ADR-040) so the atomic guard runs strictly
  before `_finalize_matches` — the two fixes (atomicity inside the guard, and correct call ordering around it)
  are complementary, not substitutes for each other.

### Related Documents

- 09_DECISIONS.md (ADR-023 — ownerless `require_role(ROLE_ADMIN)` shape; ADR-024 — `try_claim_for_review`, the
  pattern's first application; ADR-030 — `try_claim_for_account`, the pattern's second application, and
  `ClaimReviewRequestService`'s queue-row shape this mirrors)
- docs/implementation/plans/Plan_S07_AI-002.md (Decision 3)
- docs/implementation/plans/Checkpoint_S07_AI-002.md (the backend addendum recording this fix's exact
  file/line references — to be deleted at this closeout per the Continuity & Checkpointing rule once the
  orchestrator confirms the story complete; see docs/implementation/walkthroughs/Walkthrough_S07_AI-002.md for
  the retained account)
- backend/app/modules/administration/repositories/manual_match_assignment_repository.py (`try_resolve`)
- backend/app/modules/administration/services/manual_match_assignment_service.py (`resolve`)
- backend/tests/modules/administration/test_manual_match_assignment_service.py (`TestTryResolveAtomicity`)

---

# ADR-040

## Title

`SearchRequestService._finalize_matches` — Single-Writer Mechanism for `provider_matches`/`search_requests.status`/`search_event_log`; Guard-Before-Finalize Ordering Fix

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

AC4 ("the same ranked-results screen") and AC6 ("`search_event_log` regardless of automated or manual origin")
both require that a `search_requests` row's final outcome be written through exactly one mechanism, regardless
of which of the two paths (automated match, or an admin resolving a manual assignment) produced it — otherwise
the two paths could silently drift, exactly the risk `ADR-030`'s `_finalize_claim` helper was built to prevent
for claims.

During `tester` review, a genuine ordering bug was found: `SearchRequestService.resolve_manual_match` originally
called `_finalize_matches` **before** `ManualMatchAssignmentService.resolve`'s already-resolved guard — so two
sequential resolve attempts on the same assignment could both run `_finalize_matches` before the guard on the
second call ever had a chance to reject it, directly contradicting AC6's "exactly once" guarantee.

### Decision

`SearchRequestService._finalize_matches(search_request, provider_ids)` is the **only** place in the codebase that
ever writes `provider_matches` rows, sets `search_requests.status` to its final `matched`/`unmatched` value, or
writes the corresponding `search_event_log` row. Both paths are thin wrappers around it:

- **Automated path** (`_handle_completed`) — runs the existing `SearchService` query (ADR reused unchanged, see
  the Search-domain closeout ADR below) to get an ordered provider-id list, creates the `search_requests` row with
  its final status already known, then calls `_finalize_matches` synchronously in the same operation.
- **Manual path** (`resolve_manual_match`) — validates admin-supplied `provider_ids` (see below), then calls
  `ManualMatchAssignmentService.resolve` (the atomic guard, ADR-039) **first**, and only calls
  `_finalize_matches` if that succeeds. This ordering fix (guard before finalize) is what closes the tester's
  found gap: a rejected (409) second resolve attempt now writes nothing, never a duplicate
  `provider_matches`/`search_event_log`.

`rank` in `provider_matches` is the 1-based position in whichever ordered list produced it (the query's
nearest-first order for the automated path; the admin's own supplied order for the manual path — never
re-derived). `match_score` is left `NULL` for every row either path writes, since no real merit-ranking signal
exists yet (see ADR-041).

**A related, independently-found gap, fixed in the same area:** `resolve_manual_match` never validated
admin-supplied `provider_ids` before writing `provider_matches`, so a bogus id surfaced as an opaque 500 (an FK
constraint violation) instead of a proper 4xx. Fixed by validating every id against the existing
`ProviderService.list_by_ids` (reused unchanged) **before** any mutation, raising a new
`InvalidManualMatchProviderIdsError` (422) otherwise.

### Alternatives Considered

- **Two separate finalization code paths** — rejected: the exact drift risk `ADR-030` already identified and
  fixed once for claims.
- **Have `AdminManualMatchService`/an admin-facing service write `provider_matches` directly** — rejected: would
  require `administration → search`'s repository, violating `02_ARCHITECTURE.md`'s "module → another module's
  repository" prohibition, and would duplicate `_finalize_matches`'s logic.
- **Validate `provider_ids` inside `ManualMatchAssignmentService.resolve` instead of `SearchRequestService`** —
  rejected: `administration` has no dependency on `provider`, and adding one solely for this validation would be
  a new, narrower-purpose edge duplicating a check `search` can already perform via its own existing
  `provider_service` dependency.

### Consequences

- The combination of this ADR's ordering fix and ADR-039's atomicity fix together closes both the sequential
  double-finalization gap (tester) and the true-concurrency double-finalization gap (architect) — reviewers of
  future admin-resolution flows should check for both failure modes independently; fixing one does not imply the
  other is also fixed.
- `08_CODING_STANDARDS.md`'s "validate every endpoint's input" rule is now reinforced with a second concrete
  example (`InvalidManualMatchProviderIdsError`) alongside its existing ones.

### Related Documents

- 09_DECISIONS.md (ADR-029/ADR-030 — the `_finalize_claim` single-writer precedent this mirrors; ADR-039 — the
  atomic `try_resolve` guard this ordering fix depends on)
- docs/implementation/plans/Plan_S07_AI-002.md (Decision 4)
- docs/implementation/walkthroughs/Walkthrough_S07_AI-002.md (full review-process account of both findings)
- backend/app/modules/search/services/search_request_service.py (`_finalize_matches`, `resolve_manual_match`)
- backend/app/core/exceptions/exceptions.py (`InvalidManualMatchProviderIdsError`)
- backend/tests/modules/search/test_search_request_service.py, test_search_request_api.py

---

# ADR-041

## Title

Matching-Mechanism Reuse for `AI-002`: `search.SearchService`/`provider.ProviderService.search_nearby` (DIR-001) Unchanged — No New Ranking Algorithm

**Date**

2026-09-10

**Status**

Accepted

**Owner**

CTO

### Context

AC4 requires a real automated match to exist for the manual path's output to be compared against. No persisted
matching mechanism exists yet in `search` (DIR-001's `SearchService` is a stateless read-layer). Building a new
merit-ranking algorithm (rating + review volume + proximity, per `14_USER_FLOWS.md` Flow 4 step 6's literal text)
is not realistic yet: the Review domain (`REV-001`) has not shipped, so `provider.provider_rating_summaries` is
empty/all-zero placeholder data for every provider today.

### Decision

`SearchRequestService` takes the already-shipped `SearchService` as a constructor dependency and calls its
existing matching query (category + geospatial radius + discoverability, nearest-first) unchanged, with
`category` = the resolved `Category.name` (inheriting, not worsening, ADR-027's free-text exact-match posture and
`13_OPEN_DECISIONS.md` item 1's already-tracked reconciliation gap), `radius_km =
settings.SEARCH_DEFAULT_RADIUS_KM` (no radius-selection UI exists in the AI Conversation flow), capped at a new
`settings.AI_MATCH_MAX_RESULTS: int = 10`. Ranking = the query's existing nearest-first order — identical to what
DIR-001's structured browse already shows a customer today, not a new algorithm this story invents and cannot
validate. `match_score` is left `NULL` on every `provider_matches` row this story writes, both paths — honest,
not a placeholder `0`/`1.0`.

### Alternatives Considered

- **Build a merit-ranking formula now** (rating × review-count × inverse-distance) — rejected: no real rating
  data exists yet to rank by; this would be exactly the "silently degrading to a low-quality automated match"
  pattern the story's own text warns against, dressed up as a formula instead of an admission.
- **Write a brand-new geospatial query independent of `SearchService`** — rejected: `SearchService`'s query is
  already real, tested, and identical in kind to what this story needs; duplicating it violates `08_CODING_
  STANDARDS.md`'s "reuse existing modules" rule for no benefit.

### Consequences

- The moment `REV-001` ships real, non-placeholder rating data, a future story can replace this nearest-first
  ordering with a genuine merit-ranking formula inside `SearchRequestService._run_automated_match` alone — no
  other part of `AI-002`'s design (the `_finalize_matches` contract, the `provider_matches.rank`/`match_score`
  columns, the manual path) needs to change to support that.
- `search_requests`/`provider_matches` now have real, non-ephemeral rows for the first time in this codebase —
  DIR-001's own query remains deliberately unchanged and still writes nothing to either table.

### Related Documents

- 09_DECISIONS.md (ADR-025/ADR-026/ADR-027 — `SearchService`/`ProviderSearchRepository`'s original DIR-001
  design this reuses unchanged)
- docs/implementation/plans/Plan_S07_AI-002.md (Decision 5)
- docs/implementation/plans/Plan_S06_DIR-001.md (the matching logic reused unchanged)
- backend/app/modules/search/services/search_request_service.py (`_run_automated_match`)

---

# ADR-042

## Title

Merit-Ranking Formula (`MAT-001`): In-Place Upgrade of `ProviderSearchRepository.search_nearby`'s Shared Query — Not a Second, Parallel Ranking Implementation

**Date**

2026-09-11

**Status**

Accepted

**Owner**

CTO

### Context

`MAT-001` ("see ranked providers for my request") requires AI-002's placeholder `NULL` `match_score` to become a
real, bounded ranking signal combining proximity with rating and review volume — "never distance alone" (AC3),
with a deterministic tie-break (AC4) and no second, divergent filter/ranking implementation (AC2). Two callers
share the query this story upgrades: DIR-001's own `GET /search/providers` (structured browse) and the
AI-conversation automated-match path AI-002 built (`SearchRequestService._run_automated_match`). ADR-041
(AI-002) had deliberately deferred any real ranking formula because no real rating data existed yet to rank by
— that gap is what this story closes. DIR-001's own Plan (`Plan_S06_DIR-001.md`, AC5) had already pre-announced
this exact upgrade path: "ready to be upgraded to AI-ranked matching in a future story (MAT-001)."

### Decision

`ProviderSearchRepository`'s existing `_SEARCH_NEARBY_SQL` query is modified **in place** — `_WHERE_CLAUSE`/
`_COUNT_NEARBY_SQL` stay byte-for-byte unchanged (verified by direct diff during both `tester`'s and
`architect`'s review, not merely asserted) — changing only the `SELECT`/`ORDER BY` to compute and sort by a
bounded, deterministic composite score:

```
match_score =
      weight_proximity      * (1.0 - (distance_meters / radius_meters))
    + weight_rating         * (COALESCE(average_rating, neutral_average_rating) / 5.0)
    + weight_review_volume  * (LEAST(review_count, review_volume_cap) / review_volume_cap)

ORDER BY match_score DESC, p.id ASC
```

Every term is bound to `[0, 1]` by construction (distance is already `<= radius_meters` per `_WHERE_CLAUSE`'s
own condition; rating is on a 1–5 scale or a neutral default when `NULL`; review count is capped before
normalizing), so with the default weights summing to `1.0`, `match_score` itself is always in `[0, 1]` and fits
`provider_matches.match_score NUMERIC(5,4)` comfortably. `p.id ASC` re-anchors AC4's deterministic tie-break to
the new score instead of raw distance. `search_nearby(...)` gains five new required, bound (never
string-interpolated) parameters — `weight_proximity`, `weight_rating`, `weight_review_volume`,
`neutral_average_rating`, `review_volume_cap` — sourced from five new `Settings` fields
(`RANKING_WEIGHT_PROXIMITY=0.6`, `RANKING_WEIGHT_RATING=0.3`, `RANKING_WEIGHT_REVIEW_VOLUME=0.1`,
`RANKING_NEUTRAL_AVERAGE_RATING=3.0`, `RANKING_REVIEW_VOLUME_CAP=50` — CTO-confirmed launch defaults, config not
schema, mirroring `CONVERSATION_CONFIDENCE_THRESHOLD`/`AI_MATCH_MAX_RESULTS`'s precedent) and returns one new
value, `scores_by_id: dict[uuid.UUID, float]`.

A new shared entry point, `SearchService.search_providers_ranked(...)`, reads the five `RANKING_*` settings and
calls `provider_service.search_nearby(...)` once — this is the **single** method both `SearchService.
search_providers` (DIR-001's `GET /search/providers`, which discards `scores_by_id` — no new field on
`SearchResultProviderResponse`) and `SearchRequestService._run_automated_match` (AI-002/MAT-001, which uses
`scores_by_id` to populate `provider_matches.match_score` for the first time) now call, rather than either
duplicating the settings-read/parameter-assembly logic or reaching into a private method across service
instances.

This is a deliberate, in-scope behavioral change to DIR-001's already-shipped, previously-signed-off `GET
/search/providers` endpoint's result order — not only the AI-conversation path — directly evidenced by DIR-001's
own pre-announcement of this exact upgrade, and confirmed via a live HTTP round trip against a non-uniform
rating fixture proving the order genuinely changes (`backend/tests/modules/search/test_search_endpoints.py::
TestMeritRankingChangesDirOwnEndpointOrder`).

### Alternatives Considered

- **A second, parallel ranking-only repository method (e.g. `search_nearby_ranked`), leaving DIR-001's own
  `search_nearby` completely untouched.** Rejected — DIR-001's own Plan explicitly named this exact upgrade as
  MAT-001's expected job; a parallel method would be closer to the "second, divergent filter implementation"
  AC2 warns against than the in-place upgrade is, even reusing `_WHERE_CLAUSE`.
- **Compute the composite score in Python after fetching a wider, unranked candidate set.** Rejected — this
  would either defeat `LIMIT`/`OFFSET` pagination entirely (fetch everything) or silently misrank across pages
  (a later page could contain a higher-scoring row than an earlier page's lowest). Scoring inside the same
  `ORDER BY` the database already uses for `LIMIT`/`OFFSET` avoids both failure modes.
- **A raw, unnormalized linear combination** (e.g. `rating * review_count - distance_meters`). Rejected —
  incompatible units (meters vs. a 1–5 scale vs. an unbounded count) and would not fit `match_score`'s intent as
  a normalized `[0, 1]` quality indicator.

### Consequences

- Today, for any candidate set where every provider shares the same `average_rating`/`review_count` (true for
  essentially every real provider today, since no Review domain has shipped), this formula is mathematically
  equivalent to the pre-existing nearest-first order — proven, not assumed, by a dedicated regression fixture at
  the repository layer (`TestMeritRanking::test_uniform_rating_and_review_count_preserves_nearest_first_order`)
  and confirmed across every pre-existing `test_search_service.py` fixture (all of which happened to use uniform
  rating data, so none needed its expected order updated).
- DIR-001's own shipped endpoint's result order is a legitimate, intentional behavioral change under this ADR,
  not a regression — any future story reasoning about `GET /search/providers`'s ordering should cite this ADR,
  not ADR-025/026/027 alone.
- The moment a future `REV-001` writes real, non-placeholder `providers.average_rating`/`review_count` values,
  this formula becomes genuinely differentiated in production with zero further code change — this was designed
  into the formula from the start, not a follow-up obligation invented for `REV-001`.
- One stale OpenAPI/docstring reference to "nearest-first" ordering in `backend/app/modules/search/api.py` (a
  documentation-only artifact of DIR-001's original, since-superseded behavior) was found during review and
  corrected to describe merit-ranked ordering — no functional change, a trivial doc-only bug.

### Related Documents

- 09_DECISIONS.md (ADR-025/ADR-026/ADR-027 — the original `SearchService`/`ProviderSearchRepository` design this
  ADR modifies in place; ADR-041 — AI-002's deferred-ranking decision this ADR resolves)
- docs/implementation/plans/Plan_S08_MAT-001.md (Decision 1)
- docs/implementation/plans/Plan_S06_DIR-001.md (AC5's own pre-announcement of this upgrade)
- docs/implementation/walkthroughs/Walkthrough_S08_MAT-001.md
- backend/app/modules/provider/repositories/provider_search_repository.py
- backend/app/modules/search/services/search_service.py (`search_providers_ranked`)

---

# ADR-043

## Title

Rating Source for Merit-Ranking (`MAT-001`): `providers.average_rating`/`review_count`, Not the Unbuilt `provider_rating_summaries` Table; `match_score` Real Only for the Automated Path

**Date**

2026-09-11

**Status**

Accepted

**Owner**

CTO

### Context

AC3's literal text names `provider_rating_summaries` (`review` schema) as the ranking's rating source. That
table does not exist in the codebase, and — per direct investigation during planning — cannot yet hold any real
data: `03_DOMAIN_MODEL.md`'s Review domain business rules require a Review to anchor to a Contact View with a
"Yes" Outcome Tag, and Contact View is `CON-001`, which itself depends on `MAT-001`. There is no code path, today
or by the time this story ships, that could populate a real `reviews`/`provider_rating_summaries` row.
Separately, AC1 requires `provider_matches.match_score` to genuinely store a value — AI-002 (ADR-041) had left
it always `NULL` since no ranking formula existed yet.

### Decision

ADR-042's ranking formula reads the already-existing, already-wired `providers.average_rating` (nullable,
`NUMERIC(3,2)`) and `providers.review_count` (`NOT NULL`, default `0`) columns — shipped by `PRO-001`, already
rendered honestly in every provider-facing response (`SearchResultProviderResponse`, `MatchedProviderResponse`)
as "No reviews yet" when `NULL`, never a fabricated `0.0`. Building any part of the real Review domain
(`review.reviews`/`review.provider_rating_summaries`, anchor-verification against `contact_views`, a "Yes"
Outcome Tag precondition, recalculation-on-write) remains entirely `REV-001`'s scope — a genuinely separate,
sizable domain that cannot be exercised end-to-end until `CON-001` and an Outcome Tag mechanism also ship, and
which `04_DATABASE.md` (lines 405–406) already documented as a future `REV-001` write target for these exact
`providers` columns, independent of whether `provider_rating_summaries` is ever also built.

**Addendum — `match_score` real for the automated path, `NULL` for the manual path:**
`ProviderMatchRepository.bulk_create`'s signature changed from `ranked_provider_ids: list[uuid.UUID]` to
`ranked_matches: list[tuple[uuid.UUID, float | None]]`. `SearchRequestService._run_automated_match` now returns
real `(provider_id, match_score)` tuples using ADR-042's formula output; `resolve_manual_match` continues to
build `(provider_id, None)` pairs for every row an admin manually orders — an admin's own judgment is not
produced by the formula, so a formula-derived score displayed or stored alongside it would misrepresent how that
row was actually ranked, a direct anti-fabrication violation (`00_PROJECT_CONTEXT.md` §3). This closes AI-002's
own flagged gap (ADR-041: "`match_score` is left `NULL` on every `provider_matches` row this story writes, both
paths") for the automated path only, by design.

### Alternatives Considered

- **Build an empty `review.provider_rating_summaries` table now, populated by nothing**, just so AC3's literal
  table name exists. Rejected — schema for schema's sake: an empty, writer-less table provides zero additional
  testability over the already-existing `providers.average_rating`/`review_count` columns (both equally
  placeholder-empty today), while creating a second, disconnected "rating storage" concept for a future
  `REV-001` to reconcile against.
- **Build a minimal, real Review domain slice now** (a bare `reviews` table with no anchor-verification).
  Rejected outright — this would ship a Review write path that skips the self-dealing-inheriting
  anchor-verification business rule `03_DOMAIN_MODEL.md` requires, a real, unrequested security/product
  regression baked in ahead of `REV-001`'s actual design work.
- **Also compute and store a formula-derived score for the manual path**, re-running ADR-042's formula against
  the admin's chosen providers just to fill the column. Rejected outright — the admin's ordering is not produced
  by the formula; a score displayed or stored alongside it would misrepresent how that row was actually ranked.
- **Defer AC3 entirely, ship nearest-first again (repeat AI-002's ADR-041 verbatim).** Rejected — AC8 explicitly
  requires automated tests covering "known rating/distance combinations," which is only meaningful against a
  real, testable formula; test fixtures can inject arbitrary rating/distance combinations regardless of whether
  *production* data is populated yet.

### Consequences

- `provider_rating_summaries` remains fully unbuilt and unused — tracked as a genuinely open design question for
  a future `REV-001` at `13_OPEN_DECISIONS.md` item 14 (whether it is still needed as a distinct table once real
  reviews exist, or whether `providers.average_rating`/`review_count` alone is sufficient).
- `04_DATABASE.md`'s Review Domain section carries a cross-reference note to this ADR under
  `provider_rating_summaries`'s existing spec.
- `providers.average_rating` has no DB-level `CHECK` constraint enforcing the 0–5 range today (flagged during
  `architect` review as a documentation note, not a schema change for this story) — a future `REV-001` write
  path should add one when it becomes the first real writer of this column.
- This story requires zero new migration and touches zero Review-domain code — the substitution is confined
  entirely to which existing, already-wired columns the ranking formula reads.

### Related Documents

- 00_PROJECT_CONTEXT.md §3 (anti-fabrication principle)
- 03_DOMAIN_MODEL.md (Review domain — Contact-View/Outcome-Tag anchor requirement)
- 04_DATABASE.md (`providers.average_rating`/`review_count`, lines 405–406; `provider_rating_summaries`, Review
  Domain section)
- 09_DECISIONS.md (ADR-041 — AI-002's deferred-`match_score` decision this ADR resolves for the automated path)
- 13_OPEN_DECISIONS.md item 14
- docs/implementation/plans/Plan_S08_MAT-001.md (Decision 2, Decision 3)
- docs/implementation/walkthroughs/Walkthrough_S08_MAT-001.md

---

# ADR-044

## Title

Self-Dealing Contact Guard (`CON-001`): Direct `provider.user_id == current_user_id` Comparison Inside `ContactService`, Skipped Only for a Still-Unclaimed Listing; HTTP 403, Not 409

**Date**

2026-09-12

**Status**

Accepted

**Owner**

CTO

### Context

`CON-001` ("contact a matched provider directly") implements this platform's most safety-critical rule: because
one `identity.users` Account may hold both a `customer_profiles` row and a `providers` row simultaneously
(`03_DOMAIN_MODEL.md`'s dual-role Account rule), a Contact View must be rejected outright if the requesting
Customer's Account is the same Account that owns the target Provider — otherwise a provider could inflate their
own lead/contact/review numbers by contacting themselves. AC3 requires this enforced at the point of write, not
merely documented; AC4 requires an automated test asserting the row is never created. Since
`customer_profile.user_id` is definitionally equal to the authenticated caller's own `current_user.id` (the
customer profile is resolved via `CustomerProfileRepository.get_by_user_id(current_user.id)` in the first place),
the exact comparison needed is `provider.user_id == current_user.id` — no redundant re-read of the just-fetched
customer row required. Separately, no existing exception class fit "a well-formed, correctly authenticated
request, blocked purely because of who the caller is relative to the target resource" — every existing 409 in
this codebase (e.g. `ClaimAlreadyClaimedError`) represents a state-timing conflict, not a permanent identity rule.

### Decision

`ContactService.create_contact_view` runs the guard **before any row is written**: if
`provider.user_id is not None and provider.user_id == current_user_id`, it raises a new
`SelfDealingContactError(BusinessException)`, `status_code=403`, with a plain-language message ("You can't
contact your own listing."). `provider.user_id is None` (a still-unclaimed, Google-seeded listing) can never
self-deal by construction — there is no owning Account yet — so the guard is skipped and Contact View creation
proceeds normally, mirroring `CLM-001`'s own existing design (an unclaimed listing is fully contactable, exactly
as it is fully claimable by anyone). 403 was chosen over 409 because this is not a race or a timing issue — it is
a permanent, identity-based authorization rule: this specific caller may never create this specific write,
regardless of retry timing. No information-leakage concern applies (unlike claim-flow's masked 404s), since the
caller already knows they own the target listing.

The guard is enforced entirely inside the service layer, not a database constraint or trigger, since the
comparison spans two tables (`customer_profiles`, `providers`) joined through a third (`identity.users`) — a
single-table `CHECK` cannot express it, and a cross-table trigger would hide a security-critical business rule
inside opaque DB logic, contrary to this codebase's established pattern (every other business rule enforced in a
`*Service`, e.g. `ClaimService`, `AdminVerificationService`).

### Alternatives Considered

- **A database `CHECK` constraint or trigger.** Rejected — cannot express a cross-table join in a single-table
  `CHECK`, and a trigger would obscure a safety-critical rule outside the codebase's service-layer convention.
- **Enforcing the guard only in the mobile client** (e.g. hiding the Contact button on your own listing).
  Rejected outright as the sole mechanism — trivially bypassable by calling the API directly; AC3's literal
  wording ("enforced at the point of Contact View creation, not just documented as a rule") rules this out.
- **409 Conflict**, matching `ClaimAlreadyClaimedError`'s precedent. Rejected — this is not a race/timing
  conflict; it is a permanent, identity-based authorization rule with no retry that would ever succeed for the
  same caller/provider pair.

### Consequences

- `AC3`/`AC4` are satisfied by construction: `test_contact_service.py`'s self-dealing fixture (the same
  `user_id` owning both a `customer_profiles` and a `providers` row) asserts `SelfDealingContactError` is raised
  **and** directly queries `contact_views` to confirm the row count is unchanged — not merely that an exception
  was thrown.
- Since `outcome_tags` and `reviews` both anchor to `contact_views` (`04_DATABASE.md`), blocking self-dealing here
  transitively blocks self-tagging and self-reviewing too, once those domains ship.
- `architect` review independently re-verified the guard's line-by-line ordering (fires before
  `search_request_id` validation and before any write) and confirmed no bypass path exists.
- This is a new precedent: the first 403 in this codebase for a permanent identity-based authorization rule,
  distinct from the existing 409-for-timing-conflict and masked-404-for-information-leakage precedents. Future
  stories with a similarly permanent "this caller may never do this to this resource" rule should cite this ADR,
  not force-fit a 409 or a 404.

### Related Documents

- 03_DOMAIN_MODEL.md (the dual-role Account rule; the Contact View self-dealing restriction's exact wording)
- 04_DATABASE.md (`contact.contact_views`'s Self-dealing guard note)
- 09_DECISIONS.md (ADR-030 — `CLM-001`'s claim-finalization `user_id`-comparison precedent this guard mirrors, in
  the opposite direction)
- docs/implementation/plans/Plan_S08_CON-001.md (Decision 1, Decision 10)
- docs/implementation/walkthroughs/Walkthrough_S08_CON-001.md
- backend/app/modules/contact/services/contact_service.py
- backend/app/core/exceptions/exceptions.py (`SelfDealingContactError`)

---

# ADR-045

## Title

Customer-Facing `GET /providers/{id}` Public Profile Endpoint (`CON-001`): Sibling Router Registered After the Owner-Scoped `/me` Router; Not Gated on `is_discoverable`

**Date**

2026-09-12

**Status**

Accepted

**Owner**

CTO

### Context

`CON-001`'s AC5 (Provider Profile screen) needed a real, customer-facing detail endpoint; none existed —
`backend/app/modules/provider/api.py` was entirely `/me`-scoped (owner-only). A new, separate, arbitrary-
`provider_id` read is a different concern with different authorization (any `ROLE_CUSTOMER` caller, any target
provider) than the owner-only file. Separately, `03_DOMAIN_MODEL.md`/`04_DATABASE.md` distinguish
`is_discoverable` (a search-visibility flag) from eligibility to view/contact a provider a customer already has a
direct reference to (e.g. from a previous search result, a deep link, or re-opening the screen after results
refreshed) — no AC or domain text restricts profile viewing/contact to only-currently-discoverable providers.

### Decision

A new sibling file `backend/app/modules/provider/public_api.py` (mirrors this module's own existing
`claim_api.py`/`admin_claim_api.py` sibling-router convention), one route: `GET /{provider_id}`, gated by
`require_role(ROLE_CUSTOMER)`. Registered in `app/api/v1/api.py` as a **second**
`v1_router.include_router(provider_public_router, prefix="/providers")` call, placed **after** the existing
owner-scoped `provider_router` registration — Starlette matches routes in registration order, so
`/me`/`/me/portfolio`/`/me/availability` (registered first) continue to match their literal paths before the new
`/{provider_id}` path-parameter route is ever reached. This ordering requirement was independently re-verified by
`architect` as provably correct (not merely "tests happen to pass"), and a dedicated regression test
(`test_public_provider_api.py`) proves `/me` still resolves to the owner-only router.

`ProviderService.get_for_public_profile(provider_id)` only requires the row to exist and be `is_active=True` (not
soft-deleted) — it deliberately does **not** additionally require `is_discoverable=True`. `Contact View` creation
(`ContactService`, ADR-044) uses the same provider lookup and inherits the same posture. The response
(`PublicProviderProfileResponse`) deliberately excludes `phone_number`/`whatsapp_number` — those are revealed
only via the Contact Reveal flow, never on the profile screen itself, so a customer cannot obtain the number
without a real Contact View being recorded.

### Alternatives Considered

- **Extending `SearchResultProviderResponse`/`MatchedProviderResponse` with the extra profile fields** instead of
  a new endpoint. Rejected — those are paginated list-row shapes; adding hours/service-area/badge fields to every
  row of every search result would bloat a hot, frequently-paginated response for data only needed once a
  customer taps into one specific provider.
- **Adding the route directly into the existing `provider_router` object**, ordered after the `/me...` routes in
  the same file. Considered and viable, but a separate file/router was chosen for clearer separation of
  "self-service, owner-only" vs. "public, customer-facing" concerns, consistent with this module's own
  `claim_api.py`/`admin_claim_api.py` split.
- **Require `is_discoverable=True`, mirroring the search results' own filter.** Rejected as an unrequested,
  stricter-than-specified restriction — `is_discoverable` gates *search visibility*, not contact eligibility for
  a listing the customer already has a direct reference to. CTO-confirmed as the intended posture before
  implementation began.

### Consequences

- A customer who already holds a specific `provider_id` (from a prior search, a deep link, or a stale results
  list) can always open the Provider Profile screen and contact the provider, as long as the listing is still
  `is_active`, regardless of its current `is_discoverable` value — proven by a dedicated regression test.
- Any future endpoint needing a similar "owner-scoped `/me`-family router already exists, add a public
  arbitrary-id read" shape should follow the same sibling-file, registered-after pattern, not interleave a new
  route into the existing owner-only router.
- `PublicProviderProfileResponse` never exposes contact details — verified by `architect` directly against the
  schema (no phone/whatsapp field anywhere in it or its nested types).

### Related Documents

- 03_DOMAIN_MODEL.md / 04_DATABASE.md (`providers.is_discoverable` vs. `is_active`; Provider Domain)
- 09_DECISIONS.md (ADR-015 — the `{id}`-addressable-collection-always-404 convention this endpoint's 404 posture
  follows)
- docs/implementation/plans/Plan_S08_CON-001.md (Decision 2, Decision 7)
- docs/implementation/walkthroughs/Walkthrough_S08_CON-001.md
- backend/app/modules/provider/public_api.py
- backend/app/modules/provider/services/provider_service.py (`get_for_public_profile`)
- backend/app/api/v1/api.py (registration order)

---

# ADR-046

## Title

Trust-Badge Precedence Pattern (`CON-001`): Raw `is_claimed`/`verification_status` Fields, Client-Computed Precedence — Never a Server-Computed Enum

**Date**

2026-09-12

**Status**

Accepted

**Owner**

CTO

### Context

`CON-001`'s AC5 requires the Provider Profile screen to show "a Verified badge (or Unclaimed label) as
applicable" — but `is_claimed=false` and `verification_status=approved` can both be true simultaneously for a
Google-seeded listing (`CLM-001`'s own design: a still-unclaimed listing is marked `verification_status=APPROVED`
purely so it is searchable). Checking the two fields independently would produce a contradictory "Verified"
badge on a listing nobody has claimed yet — a direct anti-fabrication violation (`00_PROJECT_CONTEXT.md` §3).

### Decision

The server returns the two raw fields unchanged — `is_claimed: bool`, `verification_status: enum` — never a
pre-computed `trust_badge` enum. The mobile client renders exactly one of three states, in strict precedence
order:

1. `is_claimed == false` → the shared `UnclaimedBanner` widget, regardless of `verification_status`.
2. `is_claimed == true && verification_status == approved` → the new `VerifiedBadge` widget.
3. Otherwise (claimed, but `pending`/`under_review`/`rejected`) → neither badge is shown.

This mirrors `ProviderResultCard`'s own existing precedent (`CLM-001`, ADR-030-adjacent) of computing its
unclaimed-banner visibility client-side off a server-driven boolean, never inferring from other signals.

### Alternatives Considered

- **Have the backend compute and return a single `trust_badge: "verified" | "unclaimed" | "none"` enum field.**
  Rejected — this codebase's established precedent (`SearchResultProviderResponse.is_claimed`) is to expose the
  raw, honest boolean and let the client render off it, not to pre-compute a display-only enum server-side; a new
  enum here would be the first inconsistent departure from that pattern for no functional gain.

### Consequences

- No contradictory or fabricated trust signal can ever be shown — `is_claimed` is checked first and always wins,
  by construction, confirmed by three explicit badge-precedent fixtures (`test_public_provider_api.py`) and
  mirrored widget tests on mobile.
- **This is a reusable precedent for future stories that display more than one raw trust-related field together**
  (e.g. a future Review domain's "Verified Visit" badge, `03_DOMAIN_MODEL.md`) — cite this ADR rather than
  re-deriving a precedence rule from scratch, and keep computing precedence client-side off raw server booleans,
  never a server-computed enum, unless a future ADR explicitly supersedes this one.

### Related Documents

- 00_PROJECT_CONTEXT.md §3 (anti-fabrication principle)
- 09_DECISIONS.md (ADR-029/030 — `CLM-001`'s Google-seeded `is_claimed=false`/`verification_status=approved`
  combination that drives this pattern)
- docs/implementation/plans/Plan_S08_CON-001.md (Decision 8, Decision 9)
- docs/implementation/walkthroughs/Walkthrough_S08_CON-001.md
- mobile/lib/shared/widgets/unclaimed_banner.dart, verified_badge.dart
- mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart

---

# ADR-047

## Title

Cross-Module Wiring Convention: Services Only, Never Raw Repositories (`CON-001`'s `ContactService`/`ProviderService` Fix, Commit `bed63e8`, as the Concrete Precedent)

**Date**

2026-09-12

**Status**

Accepted

**Owner**

CTO

### Context

`02_ARCHITECTURE.md` already states that cross-module communication must go through constructor-injected
**Services** only, never a raw Repository from another module. `CON-001`'s new `contact` module was the first
module with four cross-module edges (`customer`, `provider`, `search`, `notification`) in one service. During
`architect`'s first review, `ContactService` was found wired with three raw cross-module *Repositories*
(`CustomerProfileRepository`, `ProviderRepository`, `SearchRequestRepository`) rather than those modules'
*Service* classes, and `contact/dependencies.py`'s own docstring inaccurately claimed this "mirrors
`SearchRequestService`'s own multi-module wiring shape" — `SearchRequestService` in fact only takes cross-module
*Services* (`ProviderService`, `CustomerService`, `SavedAddressService`, etc.), never a raw cross-module
Repository. Concretely, the `provider` edge also produced a duplicate-logic instance: `ContactService`'s inline
provider-lookup-plus-404 block (`get_by_id` + `is_active` check + `ProviderNotFoundError`) duplicated
`ProviderService.get_for_public_profile`'s identical logic (ADR-045) instead of calling it.

### Decision

`ContactService` is fixed (commit `bed63e8`) to depend on `ProviderService` (calling
`get_for_public_profile(provider_id)`) instead of `ProviderRepository` directly — eliminating the duplicate logic
entirely, not relocating it. The `customer`/`search` raw-repository edges
(`CustomerProfileRepository`/`SearchRequestRepository`) are **left as-is**, since neither `CustomerService` nor
`SearchRequestService` expose an equivalent raw-lookup primitive today — a documented, deliberate exception, not
an oversight. `contact/dependencies.py`'s docstring was corrected to state the `provider` edge is a Service
specifically because of the "modules communicate through services only" rule, while explicitly flagging that
`customer`/`search` remain raw Repositories for this documented reason.

**Established convention going forward**: when a new module's service needs data from another module, prefer
that module's Service class. A raw cross-module Repository dependency is only acceptable when the target
module's Service genuinely exposes no equivalent read primitive — and that gap should be named explicitly in the
new module's own `dependencies.py` docstring (not silently assumed acceptable), so a future architect review can
evaluate whether to add the missing Service method instead.

### Alternatives Considered

- **Leave `ContactService` depending on all three raw Repositories, treating this as pre-existing acceptable
  practice.** Rejected — `02_ARCHITECTURE.md`'s rule already existed; this would have let a first violation of it
  stand uncorrected and duplicate logic remain in two places at once.
- **Add a new `ProviderService` passthrough method instead of reusing `get_for_public_profile`.** Rejected as
  needless duplication — `get_for_public_profile` already does exactly the lookup `ContactService` needs
  (existence + `is_active` check + `ProviderNotFoundError`), with no ownership-check side effect that would be
  inappropriate for `ContactService`'s use.
- **Also force `CustomerProfileRepository`/`SearchRequestRepository` into new `CustomerService`/
  `SearchRequestService` passthrough methods for symmetry.** Rejected for this story — no equivalent primitive
  exists today, and inventing one purely for wiring symmetry (with no other caller) would be an unrequested,
  unjustified new abstraction. Flagged as a documented exception instead, revisitable if a future module needs
  the same primitive.

### Consequences

- `contact → provider` is now a genuine Service-to-Service edge, same direction as before, just through the
  correct layer — no new cross-module cycle introduced, confirmed by `architect` re-checking the diff directly.
- Zero regressions: the full backend suite (702/702) passed unchanged before and after the fix; no test
  assertions changed, consistent with a pure refactor.
- **This is now the concrete, citable example** for `02_ARCHITECTURE.md`'s pre-existing services-only rule — any
  future module's `dependencies.py` review should check against this precedent, not merely the abstract rule
  text, when deciding whether a new cross-module Repository dependency is acceptable.

### Related Documents

- 02_ARCHITECTURE.md (the pre-existing "modules communicate through services only" cross-module rule this ADR
  gives a concrete violation-and-fix example for)
- 08_CODING_STANDARDS.md
- docs/implementation/plans/Plan_S08_CON-001.md
- docs/implementation/plans/Checkpoint_S08_CON-001.md (architect's first review and re-check, full account)
- docs/implementation/walkthroughs/Walkthrough_S08_CON-001.md
- backend/app/modules/contact/services/contact_service.py, dependencies.py (commit `bed63e8`)
- backend/app/modules/provider/services/provider_service.py (`get_for_public_profile`, ADR-045)

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