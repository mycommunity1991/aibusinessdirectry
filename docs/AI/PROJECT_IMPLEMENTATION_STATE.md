# AI Marketplace
## Project Implementation State

**Project:** AI Marketplace
**Current Phase:** MVP Development
**Current Sprint:** Sprint 1 (Complete) → Sprint 2 (In Progress — 3 of 4 stories done)
**Completed Story:** AUTH-003 Stay Signed In and Manage Active Sessions
**Status:** Identity & Access domain underway — mobile OTP, Google/Apple sign-in, and session/refresh-token management shipped
**Last Updated:** 05 September 2026
**Owner:** CTO

---

# 1. Executive Summary

AI Marketplace is a location-based directory and AI-mediated contact marketplace connecting formal businesses and individual freelancers with nearby customers through conversational AI intake, rather than category-tree search. The platform is a task-oriented utility (search → match → contact) — not a social feed.

The engineering team follows a Specification-Driven Development approach where every implementation is driven by approved architecture, engineering standards, security guidelines, API standards, UI guidelines, and sprint stories.

The objective is to build production-quality software from Day One while avoiding architectural drift and unnecessary technical debt.

Sprint 1 delivered a complete backend foundation (BF-001 through BF-018). Sprint 2 (Identity & Access) is underway: AUTH-001 (mobile OTP registration/login) shipped the first business domain module, establishing the `identity` schema and the `backend/app/modules/<domain>/...` structural convention every later domain will follow. AUTH-002 (Google/Apple sign-in) shipped on top of it, adding server-side ID-token verification and the `(auth_provider, external_auth_subject)` account-matching pattern both OAuth providers and future auth methods share. AUTH-003 (stay signed in and manage active sessions) has since shipped on top of both: `sessions`/`refresh_tokens`/`devices` tables, a narrowed 15-minute JWT payload, rotating opaque refresh tokens with reuse-detection cascade-revocation, and real session listing/revocation endpoints, replacing the BF-011 `get_current_user` placeholder with a real implementation.

---

# 2. Product Vision

Any business or individual freelancer can list what they do for free and be found by nearby customers through AI-powered, natural-language search, in a country-agnostic architecture launching first in the UAE.

Core principles:

- Utility, not feed — no post/comment/reaction loop
- AI-mediated intake as the differentiated core, RAG-grounded against real platform data
- Country-agnostic architecture
- Mobile First
- Security by Design
- Simplicity

See `00_PROJECT_CONTEXT.md` for the full product context and `03_DOMAIN_MODEL.md` for entities and business rules.

---

# 3. Approved Technology Stack

## Mobile

- Flutter
- Dart
- Riverpod
- GoRouter
- Dio
- Material 3

## Backend

- Python 3.14+
- FastAPI
- SQLAlchemy Async
- Alembic
- Pydantic v2
- Uvicorn
- uv

## Database

- PostgreSQL

## Cache

- Redis

## Infrastructure

- AWS
- GitHub
- GitHub Actions
- Docker (Future)

Development is performed locally on macOS.

Android Studio is intentionally excluded during Phase 1.

All technologies are governed by AI-12 Technology Stack.

---

# 4. Architecture

Architecture style:

Modular Monolith

Future architecture:

Extractable Microservices

Key architectural principles:

- Clean Architecture
- Feature-First organization
- Service-oriented module communication
- Repository Pattern
- Domain isolation
- Async-first backend
- Strong typing
- Dependency inversion

Modules never communicate directly with repositories belonging to another module.

Business logic exists only inside services.

Routes remain orchestration only. See `02_ARCHITECTURE.md`.

---

# 5. Domain Overview

Current approved business domains (per `03_DOMAIN_MODEL.md`):

- Identity & Access
- Customer
- Provider (Business / Freelancer)
- Category
- Service Area
- Conversation / AI Intake Session
- Search Request
- Contact View
- Outcome Tag
- Verification
- Review
- Notification
- Administration

There is no Community, Feed, Events, or Messaging domain in this model — that concept belonged to an earlier product direction and was superseded by the AI Marketplace pivot (see `00_PROJECT_CONTEXT.md` Section 11 for the changelog).

---

# 6. Project Documentation

The project maintains a centralized AI Knowledge Base inside:

docs/AI/

Current documents include:

- AI-00 Project Context
- AI-01 Engineering Playbook
- AI-02 Architecture
- AI-03 Domain Model
- AI-04 Database Design
- AI-05 API Guidelines
- AI-06 Security Standards
- AI-07 UI Guidelines
- AI-08 Coding Standards
- AI-09 Architecture Decisions
- AI-10 Glossary
- AI-11 MVP Scope
- AI-12 Technology Stack
- AI-13 Open Decisions

These documents are the authoritative source for all implementation decisions.

---

# 7. Development Workflow

Development follows Specification-Driven Development.

Each implementation story is executed independently.

Workflow:

1. Architecture approved.
2. Story created.
3. AI coding agent receives implementation prompt.
4. Implementation completed.
5. Walkthrough generated.
6. Architecture review performed.
7. Recommendations implemented.
8. Documentation updated.
9. Git cleanup.
10. Story approved.

Each conversation represents exactly one implementation story.

No story may introduce functionality outside its defined scope.

---

# 8. Sprint Progress

## Sprint 1 — Backend Foundation (Complete)

| Story | Description | Status |
|--------|-------------|--------|
| BF-001 | Backend Foundation | ✅ |
| BF-002 | Configuration Management | ✅ |
| BF-003 | Database Connectivity | ✅ |
| BF-004 | Database Migrations | ✅ |
| BF-005 | Application Lifecycle Management | ✅ |
| BF-006 | API Versioning | ✅ |
| BF-007 | Health Check Endpoints | ✅ |
| BF-008 | Structured Logging | ✅ |
| BF-009 | Global Exception Handling | ✅ |
| BF-010 | Standardized API Response Models | ✅ |
| BF-011 | Security Utilities | ✅ |
| BF-012 | Repository Layer | ✅ |
| BF-013 | Middleware Foundation | ✅ |
| BF-014 | Request Logging & Correlation Middleware | ✅ |
| BF-015 | Automatic API Documentation | ✅ |
| BF-016 | Testing Framework Configuration | ✅ |
| BF-017 | Code Quality Configuration | ✅ |
| BF-018 | Project Documentation | ✅ |

Full detail in `docs/sprints/sprint_01_summary.md`.

## Sprint 2 — Identity & Access (In Progress — 3 of 4 stories done)

**Correction (18 July 2026):** This section previously described a stale 9-story AUTH-001..009 backlog (models → OTP service → mobile auth → OAuth → JWT → sessions → RBAC → rate limiting → audit logging) that no longer matches `docs/AI/Project_Tracker.xlsx`, the authoritative backlog source. The Tracker defines a smaller, 4-story Sprint 2, each a full vertical slice (backend + mobile + tests), not a layered breakdown. The table below reflects the current, real backlog. See `docs/implementation/plans/Plan_S02_AUTH-001.md`'s Supersession Notice for the full history of this correction.

Scope is limited strictly to the Identity & Access domain (`03_DOMAIN_MODEL.md`) — no Customer/Provider profile creation, which is deferred to its own later sprint even though registration triggers it conceptually in `14_USER_FLOWS.md` Flow 1.

| Story | Description | Status |
|--------|-------------|--------|
| AUTH-001 | Register and sign in with Mobile OTP | ✅ Done |
| AUTH-002 | Register and sign in with Google or Apple | ✅ Done |
| AUTH-003 | Stay signed in and manage active sessions | ✅ Done |
| AUTH-004 | Access the app according to my role | 🔲 Not Started |

**Note:** `docs/implementation/plans/Plan_S02_AUTH-004.md` (and any remaining `_AUTH-005` through `_AUTH-009` plans) still describe the old 9-story breakdown and do not correspond 1:1 to the current tracker's AUTH-004. It is stale/superseded and must be re-planned against the current 4-story tracker scope before that story is picked up — do not implement against it as-is. `Plan_S02_AUTH-002.md` and `Plan_S02_AUTH-003.md` were both re-planned against the current tracker scope and are no longer stale; see their respective Walkthroughs for completed implementation detail.

---

# 9. Current Backend Capabilities

The backend currently provides:

✓ Application startup
✓ Configuration loading
✓ Environment validation
✓ Database connectivity
✓ Async session management
✓ Alembic migrations
✓ API versioning
✓ Health / readiness / liveness monitoring
✓ Structured logging with correlation IDs
✓ Global exception handling
✓ Standardized API response models
✓ Security utilities (Argon2id hashing, JWT foundation)
✓ Generic repository layer
✓ Automatic OpenAPI documentation
✓ Production-ready project structure
✓ Identity & Access domain (mobile OTP registration/login — AUTH-001): `identity` schema, roles/permissions scaffolding, `request-otp`/`verify-otp` endpoints, stateless JWT issuance
✓ Google/Apple sign-in (AUTH-002): JWKS-based ID-token verification (`IdTokenVerifier`/`JwksIdTokenVerifier`), `OAuthService`, `POST /auth/google`/`POST /auth/apple`, find-or-create by `(auth_provider, external_auth_subject)`
✓ Session management and refresh-token rotation (AUTH-003): `identity.sessions`/`identity.refresh_tokens` tables, 15-minute JWT access tokens narrowed to `{sub, exp, iat, jti, roles}`, opaque SHA-256-hashed refresh tokens with rotation and reuse-detection cascade-revocation, `SessionService`, `POST /auth/refresh`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`, `POST /auth/sessions/logout-all`, and a real `get_current_user` dependency (replacing the BF-011 placeholder)

The first business module (Identity & Access, partial — mobile OTP, Google/Apple sign-in, and session/refresh-token management) has landed. RBAC enforcement remains (AUTH-004).

---

# 10. Coding Standards

The project follows strict engineering standards.

Highlights:

- snake_case naming
- SOLID principles
- Repository Pattern
- Structured logging
- No print statements
- Async-first design
- Dependency injection
- Small focused services
- Unit testing
- Integration testing
- Production-ready code only

These standards apply equally to human developers and AI assistants.

---

# 11. Security Standards

Security is treated as a foundational concern.

Current standards include:

- JWT authentication
- RBAC
- Argon2id password hashing
- Input validation
- Parameterized queries
- HTTPS
- OWASP compliance
- UAE PDPL alignment
- Secrets managed through environment variables
- Structured security logging

Security shortcuts are prohibited.

---

# 12. API Standards

Every API follows:

- REST
- JSON
- /api/v1
- Standard response model
- Consistent error responses
- Pagination
- Filtering
- Sorting
- OpenAPI documentation
- Stateless authentication

Future versions will evolve using additive changes where possible.

---

# 13. Architecture Decisions

Important approved decisions include:

- Modular Monolith
- Flutter mobile application
- FastAPI backend
- PostgreSQL
- Redis
- Feature-First Flutter architecture
- UUID primary keys
- JWT authentication
- AI-first development workflow

All architectural decisions are recorded as ADRs in `09_DECISIONS.md` and remain append-only.

---

# 14. Repository State

Current backend foundation is production-ready.

Implemented layers include:

- Configuration
- Database
- Core infrastructure
- API routing
- Lifecycle management
- Health monitoring
- Logging & exception handling
- Repository layer
- Testing & code quality tooling
- Identity & Access module (`backend/app/modules/identity/`) — mobile OTP registration/login (AUTH-001), establishing the `backend/app/modules/<domain>/...` structural convention every later domain module will follow; Google/Apple sign-in (AUTH-002) built on top of it, adding JWKS-based ID-token verification and `OAuthService`; session management and refresh-token rotation (AUTH-003) built on top of both, adding `SessionService`, `sessions`/`refresh_tokens` tables, and a real `get_current_user` dependency

Remaining business modules are deferred until their corresponding sprint stories.

The Flutter mobile app has moved beyond the default scaffold: Riverpod/GoRouter/Dio/l10n infrastructure plus the Splash, Language Selection, Phone Entry, and OTP Entry screens (AUTH-001), real Google/Apple sign-in buttons on the Phone Entry screen (AUTH-002), and secure cross-restart session persistence, a silent-refresh Dio interceptor, and a "Log out" action on the Home stub (AUTH-003), are implemented. A dedicated Manage Sessions UI was deliberately not built this story (see AUTH-003's Walkthrough). The full Home screen and all other feature areas remain unbuilt.

---

# 15. Current Limitations

Not yet implemented:

- Authentication / Identity & Access — partial: mobile OTP registration/login (AUTH-001), Google/Apple OAuth (AUTH-002), and session/refresh-token management (AUTH-003) are done; RBAC enforcement (AUTH-004) remains
- Customer profile
- Provider profile (Business / Freelancer)
- Category taxonomy
- Conversation / AI Intake
- Search & Matching
- Contact View
- Verification
- Review / Outcome Tag
- Notifications
- Administration
- Flutter application (beyond the AUTH-001 auth flow — Home screen and all other feature areas)

These will be implemented according to the approved sprint backlog, gated by the open decisions in `13_OPEN_DECISIONS.md` — category taxonomy in particular blocks the AI intake work.

---

# 16. Overall Progress

Project Planning — 100%

Architecture — 100%

Engineering Standards — 100%

AI Knowledge Base — 100%

Backend Foundation — 100%

Identity & Access — In Progress (3 of 4 stories done: AUTH-001, AUTH-002, AUTH-003)

Provider / Customer Profiles — Not Started

Conversation / AI Intake — Not Started

Flutter Application — In Progress (auth flow only: Splash with session recovery, Language Selection, Phone Entry with Google/Apple sign-in, OTP Entry, Home stub with Log out)

Deployment — Not Started

Overall Estimated Project Completion: Approximately 25-30%

---

# 17. Next Planned Story

Sprint 2 — AUTH-004 (Access the app according to my role), fourth and last story in the current backlog defined in Section 8.

Identity & Access domain concludes with role-based authorization enforcement, built on top of the `roles` claim AUTH-003's access tokens already carry and the `User`/session infrastructure AUTH-001/002/003 established.

AUTH-001 (mobile OTP registration/login), AUTH-002 (Google/Apple sign-in), and AUTH-003 (session/refresh-token management) are all done. Note: `docs/implementation/plans/Plan_S02_AUTH-004.md` is stale (written against the old 9-story backlog) and must be re-planned against the current tracker scope before AUTH-004 implementation begins — the same re-planning process AUTH-002 and AUTH-003 both went through.

---

# 18. Key Achievements

By completion of Sprint 1 (BF-018), the project has achieved:

- Stable backend foundation
- Production-grade architecture
- Complete AI governance documentation
- Centralized engineering standards
- Modular backend structure
- Database migration capability
- Versioned API infrastructure
- Health monitoring endpoints
- Structured logging and exception handling
- Repository layer and testing/code-quality tooling
- Specification-driven development workflow
- AI-assisted implementation process
- Clean Git history after each story
- Architecture review process for every completed implementation

The project is now ready to begin implementation of core business functionality on top of a stable, maintainable, and scalable foundation.

---

# End of Document
