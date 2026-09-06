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