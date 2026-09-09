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