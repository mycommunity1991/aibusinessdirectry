# AI Marketplace
## Project Implementation State

**Project:** AI Marketplace
**Current Phase:** MVP Development
**Current Sprint:** Sprint 1 (Complete) → Sprint 2 (Complete — 4 of 4 stories done) → Sprint 3 (Complete — 2 of 2 stories done) → Sprint 4 (Complete — 2 of 2 stories done) → Sprint 5 (Complete — 2 of 2 stories done) → Sprint 6 (Complete — 2 of 2 stories done: DIR-001, CLM-001) → Sprint 7 (In Progress — 2 of 3 stories done: CTG-001, AI-001; AI-002 not yet started)
**Completed Story:** AI-001 Describe My Service Need in a Guided AI Conversation
**Status:** Identity & Access domain complete. Customer domain complete: profile/preferences auto-provisioning, `GET`/`PATCH /customers/me`, and saved service-location addresses (`GET`/`POST`/`PATCH`/`DELETE /customers/me/addresses`) have all shipped. Provider domain fully shipped for Sprint 4's scope: PRO-001 shipped the new `provider` module (`providers`/`business_profiles`/`freelancer_profiles`, immutable-type onboarding wizard, one-provider-per-account); PRO-002 shipped the ongoing Storefront (`provider_availability`, `portfolios`, `service_areas`, the new `provider_category_labels` interim table, this codebase's first file-upload capability, and the mobile Storefront screen). **Sprint 5 (Provider Verification) is now complete.** VER-001 shipped a new `verification` module (`verification_records`/`verification_documents`, an OCR-stub-assisted preview→confirm→submit flow, a private/public file-storage split for sensitive documents) and the mobile S-19/S-20 screens. VER-002 has since shipped the admin review side on top of it: an admin-only review queue and approve/reject endpoints, an atomic status+discoverability cache update (with a DB-level `CHECK` constraint as defense-in-depth), two new first-slice domain modules (`administration`, `notification`), and a new ops-only `grant_admin_role.py` script — backend-only, by deliberate design, since the admin dashboard is out of the mobile MVP's screen inventory. A genuine concurrency bug (two truly concurrent approve calls on the same record both succeeding) was found during review and fixed with an atomic conditional `UPDATE`; see `docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md` for the full account. Sprint 5's two stories together complete the Verification domain's trust gate: a Provider can now submit for verification, be reviewed by an Admin, and become discoverable once approved. **Sprint 6 (Directory & Listing Claims) is now complete.** DIR-001 (browse nearby providers by category and location) has shipped: this codebase's first `search` domain module, the `cube`/`earthdistance` GiST geospatial indexes `04_DATABASE.md` Section 13 had only ever specified (now confirmed shipped), a category+radius+discoverability structured directory query (this codebase's first raw parameterized `sqlalchemy.text()` SQL, ADR-026), and the mobile Search Filters/Search Results screens (S-08). `CLM-001` ("claim my Google-seeded business listing"), Sprint 6's second and final story, has since shipped and been signed off: an idempotent Google Places bulk-import script, a synthetic import-time verification approval structurally excluded from ever counting as a real verification cycle (ADR-029 — the review process found and fixed a genuine gap here, a claimed listing's first real verification submission was initially blocked by the stale synthetic record), an atomic-conditional-`UPDATE` claim-finalization race-fix and a new `administration.claim_review_requests` admin-fallback queue (ADR-030), and a third application of the swappable-Protocol pattern for the Google Places client (ADR-031). This executes exactly the bulk-import design the CTO's 09 September 2026 risk-acceptance decision (`13_OPEN_DECISIONS.md` item 3) approved — the underlying legal question stays genuinely open regardless. **Sprint 6 (Directory & Listing Claims) is now complete.** See `docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md` and `docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md` for each story's full account. **Sprint 7 (Category Domain / AI Intake foundation) has now started.** CTG-001 (build the real Category domain and seed the v1 launch taxonomy) has shipped: a new `category` domain module (`category.categories`/`category.category_question_templates`/`category.provider_categories`, all exactly per `04_DATABASE.md`'s pre-existing spec), seeded via this codebase's first data-seeding migration (ADR-028) with the full CTO-approved 14-category, 47-question v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md`, now v1.1.0). `13_OPEN_DECISIONS.md` item 1 (Category Taxonomy) is now resolved and implemented — `AI-001`/`AI-002` (Sprint 7's Conversation/AI Intake stories) and everything cascading from them through Sprint 12 are genuinely unblocked at the code level, though neither has yet been planned or started. See `docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md` for CTG-001's full account. **`AI-001` ("describe my service need in a guided AI conversation") has since shipped and been signed off on top of it:** a new `conversation` domain module (`conversation.conversation_sessions`/`conversation.messages`/`conversation.confidence_scores`, all exactly per `04_DATABASE.md`'s pre-existing spec plus two additive items — a fourth `conversation_status` value, `abandoned`, and a new `structured_criteria` JSONB column satisfying AC9), a swappable `ConversationAiClient` Protocol (the fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern, ADR-034) whose only implementation, `RuleBasedConversationAiClient`, is fully deterministic and grounded by construction against the seeded Category taxonomy, and the mobile AI Conversation screen (S-07) with tiered typing-indicator/timeout feedback and a revise-a-previous-answer flow. **Explicit, CTO-accepted MVP gap:** no real LLM vendor is selected — two of the story's 11 verbatim acceptance criteria (AC3, AC5) are honestly recorded as not met rather than silently skipped, tracked as a new, deliberately open `13_OPEN_DECISIONS.md` item 13. This story's review found and fixed two genuine issues: a mobile error-mapping bug (every HTTP 422 was misclassified as "this answer can no longer be revised," even for an unrelated request-validation failure) and a backend standards violation (the revise-answer flow originally hard-deleted truncated messages on a factually incorrect premise that `messages` lacked a soft-delete column — corrected to soft-delete via a partial unique index, mirroring `saved_addresses`' existing precedent). See `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md` for the full account.
**Last Updated:** 10 September 2026
**Owner:** CTO

---

# 1. Executive Summary

AI Marketplace is a location-based directory and AI-mediated contact marketplace connecting formal businesses and individual freelancers with nearby customers through conversational AI intake, rather than category-tree search. The platform is a task-oriented utility (search → match → contact) — not a social feed.

The engineering team follows a Specification-Driven Development approach where every implementation is driven by approved architecture, engineering standards, security guidelines, API standards, UI guidelines, and sprint stories.

The objective is to build production-quality software from Day One while avoiding architectural drift and unnecessary technical debt.

Sprint 1 delivered a complete backend foundation (BF-001 through BF-018). Sprint 2 (Identity & Access) is now complete: AUTH-001 (mobile OTP registration/login) shipped the first business domain module, establishing the `identity` schema and the `backend/app/modules/<domain>/...` structural convention every later domain will follow. AUTH-002 (Google/Apple sign-in) shipped on top of it, adding server-side ID-token verification and the `(auth_provider, external_auth_subject)` account-matching pattern both OAuth providers and future auth methods share. AUTH-003 (stay signed in and manage active sessions) shipped on top of both: `sessions`/`refresh_tokens`/`devices` tables, a narrowed 15-minute JWT payload, rotating opaque refresh tokens with reuse-detection cascade-revocation, and real session listing/revocation endpoints, replacing the BF-011 `get_current_user` placeholder with a real implementation. AUTH-004 (access the app according to my role) has since shipped on top of all three: a composable `require_role()` dependency, an ownership-check helper (404, not 403), a new `audit` module with an immutable `audit_logs` table recording registration/login/logout/session-revocation events, and `GET /auth/me` — closing out Sprint 2 in full.

Sprint 3 (Customer Profile & Locations) is now complete. Its first story, CUS-001 (set up my customer profile and preferences), shipped a new `customer` domain module (`customer_profiles`/`customer_preferences`, one-to-one with `users`), auto-provisioned in the same database transaction as registration via a new `identity → customer` cross-module service dependency that deliberately mirrors the `identity → audit` pattern AUTH-004 already established (recorded as ADR-014), sensible defaults (WhatsApp notification channel, `Accept-Language`-derived language falling back to English), and `GET`/`PATCH /customers/me` with no `{id}` parameter — ownership is structurally guaranteed rather than defensively checked. On mobile, a new Profile & Settings screen delivers live language switching (no app restart) and this codebase's first automated RTL test. Its second and final story, CUS-002 (manage my service locations), has since shipped on top of it: `customer.saved_addresses` (this codebase's first genuine soft-delete pattern), transactional default-address uniqueness backed by a partial unique index as defense-in-depth, and `GET`/`POST /customers/me/addresses` + `PATCH`/`DELETE /customers/me/addresses/{address_id}` — a client-`{id}`-addressable collection, deliberately shaped differently from CUS-001's `/me` singleton (the distinction is now recorded as ADR-015). On mobile, a new shared, reusable `LocationPickerScreen` (map-pin/manual/current-location entry, zero Customer-domain coupling, built for future Provider-domain reuse) backs a skippable first-address prompt at registration and a Saved Addresses management screen with Undo-on-delete. Sprint 4 (Provider Storefront) is now complete. Its first story, PRO-001 (create my business or freelancer listing), shipped a new `provider` domain module (`providers`, `business_profiles`, `freelancer_profiles`), a new cross-module `RoleAssignmentService` letting `provider` grant `ROLE_PROVIDER` to an already-authenticated Account (the reverse direction of ADR-014's `identity → customer`/`identity → audit` edges, recorded as ADR-016), server-generated slugs, unconditional `verification_status=pending`/`is_discoverable=false` defaulting, and a strict one-Provider-per-Account rule enforced at the service layer. On mobile, a new `StepIndicator` shared widget and a `features/provider/` onboarding wizard (type selection → basic info → subtype-specific details) reuse CUS-002's `LocationPickerScreen` for address/base-location capture, reachable from a new "List Your Business" tile on Profile & Settings. Its second and final story, PRO-002 (manage my provider storefront), has since shipped on top of it: `provider_availability`, `portfolios`, and `service_areas` (all exactly per the pre-existing schema spec), plus a new, deliberately-not-`provider_categories`-named interim table `provider_category_labels` (replacing PRO-001's temporary `providers.category_label` column, which this story's migration backfills and drops); this codebase's first file-upload capability, a `FileStorage` protocol with a `LocalFileStorage` implementation explicitly interim pending real AWS infrastructure (recorded as ADR-017); `PATCH /providers/me` and the new portfolio/availability sub-resource endpoints, all bare-authenticated per ADR-016's token-refresh-lag reasoning. On mobile, a new Storefront screen (S-25) with four independently-saveable sections, a portfolio manager (using the new `image_picker` dependency), and a shared `WeeklyHoursEditor` widget factored out of PRO-001's onboarding screen. **Sprint 4 (Provider Storefront) is now complete.**

Sprint 5 (Provider Verification) is now complete. Its first story, VER-001 (submit my provider verification), shipped a new `verification` domain module (`verification_records`/`verification_documents`), reusing `provider`'s existing `verification_status` Postgres enum type rather than duplicating it (`create_type=False`); a deliberate three-step preview→confirm→submit flow so OCR-extracted fields are shown and made editable before any database row exists; `StubDocumentOcrService`, this codebase's first OCR integration point, honestly returning empty candidate fields pending a future story's real pipeline (recorded as ADR-018); and a private-vs-public file-storage split (`FileStorage` gains a `public_url_prefix` parameter, a separate never-mounted `VERIFICATION_UPLOAD_DIR` root, and an authenticated streaming-download endpoint) so sensitive identity/license documents are never reachable through the existing public `/media` mount PRO-002 built for portfolio photos (recorded as ADR-019 — the single most consequential decision in this story, per both the Plan and the architect's own assessment). On mobile, a new `features/verification/` module delivers the S-19 upload and S-20 status screens plus the OCR-confirm step, wired into the end of the Provider onboarding wizard and a new status chip on the Storefront screen. This story's review was more eventful than prior ones: a real pending-slot file bug was found and fixed during backend review (a stale file from an earlier preview with a different extension could otherwise be picked up at submit time), a dead exception class was found and removed by the tester, and the architect's first-pass review returned CHANGES REQUIRED over a genuine bidirectional mobile feature-coupling violation between `features/provider/` and `features/verification/` — fixed by moving `ProviderType` to `shared/` and introducing two minimal shared accessor repositories, then confirmed by a focused architect re-review that returned APPROVED WITH RECOMMENDATIONS. **Important scope note, stated explicitly so it is never overstated:** VER-001 only got a submission into the `pending` queue and let a provider view their own current status — it did not make any provider discoverable and did not implement any part of the admin review/approval mechanism. See `docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md` for full detail.

Sprint 5's second and final story, VER-002 (review provider verification as an administrator), has since shipped the admin side of the trust gate VER-001 left open: a new, ownerless `require_role(ROLE_ADMIN)`-only authorization shape (a genuinely third endpoint category alongside ADR-015's existing two, recorded as ADR-023) backs a new admin-only review queue (this codebase's first real use of the previously-unused `CollectionResponse`/`PaginationMeta` pagination infrastructure) and approve/reject endpoints; approving atomically updates `providers.verification_status`/`is_discoverable` in the same transaction as the `verification_records` status change, for **both** Freelancer and Business Providers (Decision 5, explicitly confirmed by the user), backed by a new DB-level `chk_providers_discoverable_requires_approved` `CHECK` constraint as defense-in-depth. Two new, first-slice domain modules were built — `administration` (`admin_action_log`, recorded as ADR-021) and `notification` (`notifications`, recorded as ADR-022) — both honestly minimal, in-app-record-only capabilities, not full build-outs of their much larger future scope. A new ops-only `backend/scripts/grant_admin_role.py` CLI script (recorded as ADR-020, explicitly confirmed by the user before implementation) grants `ROLE_ADMIN` to an already-registered Account; no new admin login mechanism was built. This story's review found a genuine, empirically-reproduced concurrency bug — two truly concurrent approve calls on the same record could both succeed, each writing a duplicate `admin_action_log`/`notification` row — fixed with an atomic conditional `UPDATE` (`VerificationRecordRepository.try_claim_for_review`, recorded as ADR-024, this codebase's first use of this optimistic-concurrency-control pattern), independently re-verified by the architect (who reverted and re-applied the fix to confirm it) before returning APPROVED WITH RECOMMENDATIONS. **This story is backend-only, by deliberate design** — the admin operations dashboard is explicitly excluded from the mobile MVP's screen inventory. **Sprint 5 (Provider Verification) is now complete**: a Provider can submit for verification, be reviewed by an Admin, and become discoverable once approved — the full trust gate this domain exists to enforce. See `docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md` for full detail.

Sprint 6 (Directory & Listing Claims) is now complete. Its first story, DIR-001 (browse nearby providers by category and location), shipped this codebase's first `search` domain module (no new tables of its own — the geospatial/category/discoverability query lives inside the `provider` module, ADR-025), confirmed the `cube`/`earthdistance` GiST indexes `04_DATABASE.md` Section 13 had only ever specified, and delivered the mobile Search Filters/Search Results (S-08) screens, searching only self-registered, `is_discoverable=true` providers via a free-text category exact-match against `provider_category_labels` (ADR-027). Its second and final story, `CLM-001` ("claim my Google-seeded business listing"), has since shipped on top of it: an idempotent CLI import script bulk-seeding Business listings from the Google Places API (`GooglePlacesClient` swappable Protocol, ADR-031), a synthetic import-time `verification_status=approved`/`is_discoverable=true` state paired with a matching, never-human-reviewed `verification_records` row structurally excluded from ever counting as a real verification cycle (ADR-029), a claim flow (search → OTP-to-public-number → finalize) using an atomic conditional `UPDATE` race-fix and a shared finalization helper across both the OTP-success and admin-approval paths, plus a new `administration.claim_review_requests` admin-fallback queue (ADR-030), and one additive `is_claimed` field on DIR-001's existing search response rendering a full-width "Unclaimed" banner on mobile. This executes — does not re-litigate — the CTO's explicit risk-acceptance decision (09 September 2026, `13_OPEN_DECISIONS.md` item 3) to proceed with the original bulk-import scope despite the underlying Google Places legal/UAE-PDPL review remaining genuinely open. This story's review found and fixed one genuine gap: the synthetic import-time verification record was initially not excluded from a claimant's "latest verification cycle," blocking a freshly claimed listing's first real submission — fixed in `VerificationRecordRepository.get_latest_for_provider`. See `docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md` and `docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md` for full detail.

Sprint 7 (Category Domain / AI Intake foundation) has now started. Its first story, CTG-001 (build the real Category domain and seed the v1 launch taxonomy), shipped a new `category` domain module — `category.categories`, `category.category_question_templates`, and `category.provider_categories` (created empty), all exactly per `04_DATABASE.md`'s pre-existing spec — seeded via this codebase's first data-seeding migration (an idempotent `ON CONFLICT (slug) DO NOTHING ... RETURNING`-gated insert, recorded as ADR-028) with the full CTO-approved 14-category, 47-question v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md`, now v1.1.0 after a genuine Arabic-content gap found during implementation was corrected). A new, real, read-only `CategoryService` (no HTTP route yet — no caller exists this story) exposes both tables for a future consumer. Backend-only; does not touch `provider_category_labels`, `provider_categories` reconciliation, or DIR-001's `search` module. `13_OPEN_DECISIONS.md` item 1 (Category Taxonomy) is now resolved *and implemented* — `AI-001`/`AI-002` (this same sprint's remaining stories) and everything cascading from them through Sprint 12 are genuinely unblocked at the code level, though neither has yet been planned or started. See `docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md` for full detail.

Sprint 7's second story, `AI-001` ("describe my service need in a guided AI conversation"), has since shipped on top of `CTG-001`: a new `conversation` domain module (`conversation_sessions`/`messages`/`confidence_scores`, exactly per `04_DATABASE.md`'s pre-existing spec, plus two additive items — a fourth `conversation_status` value `abandoned`, and a new `structured_criteria` JSONB column on `conversation_sessions` satisfying AC9's `search_requests`-ready, Pydantic-validated payload, ADR-033), and a new swappable `ConversationAiClient` Protocol (ADR-034, the fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern) whose only implementation, `RuleBasedConversationAiClient`, resolves a category from free text via case-insensitive substring matching against the seeded taxonomy and walks that category's required follow-up questions verbatim in `sort_order` — never inventing a question or fact outside `category.categories`/`category_question_templates` (AC10, proven structurally, not by prompt instruction). Confidence-threshold completion and a hard turn cap are both `Settings`, not code (Decision 4). On mobile, a new `features/conversation/` module delivers the AI Conversation screen (S-07): tiered typing-indicator/contextual-label/timeout feedback (AC6/AC7), an inline revise-a-previous-answer flow (AC8) gated to still-`active` sessions only, and a new entry point on the Home placeholder screen. `AI-001` ends at `conversation_sessions.status ∈ {completed, routed_to_admin}` with zero writes to `search`/`administration` (ADR-032, Tracker-confirmed) — `AI-002` is the story that creates any `search.search_requests` row or routes to manual matching. **Explicit, CTO-accepted MVP gap:** no real LLM vendor is selected anywhere in this codebase; two of the story's 11 verbatim ACs (AC3 — system prompts as version-controlled files; AC5 — a null provider field reported as unknown) are honestly recorded as not met by this fully rule-based interim implementation, not silently skipped, tracked as a new, deliberately open `13_OPEN_DECISIONS.md` item 13 (ADR-035). This story's review found and fixed two genuine issues: a mobile error-mapping bug where every HTTP 422 was misclassified as "this answer can no longer be revised" regardless of which endpoint produced it (fixed by distinguishing the revise-specific 422 from an ordinary request-validation 422), and a backend standards violation where the revise-answer flow originally hard-deleted truncated messages on a factually incorrect premise that `messages` lacked a soft-delete column — corrected to soft-delete via a promoted partial unique index on `(conversation_session_id, sequence_number)`, mirroring `saved_addresses`' `uq_saved_addresses_customer_default` precedent (ADR-036). See `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md` for the full account.

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
- AI-13 Open Decisions — **created 08 September 2026**, reconstructed from every citation of this file across
  the codebase after three independent stories (PRO-001, PRO-002, VER-001) each had to design a flagged
  workaround because it never existed. Items 1 (Category Taxonomy), 3 (Google Places Data Legal Review), 4
  (Unclaimed Listing UX), 5 (Business Verification Bar), and 8 (Final Product/Company Name) are recorded Open
  with direct textual evidence; item 9 (Launch Market Confirmation) is recorded Resolved (UAE confirmed, per
  `00_PROJECT_CONTEXT.md`'s own changelog); items 2, 6, and 7 are unrecoverable numbering gaps flagged for the
  CTO to fill in or confirm unused; two new items (10 — degree of manual/Wizard-of-Oz matching at launch, 11 —
  real OCR pipeline interface confirmation) were added, surfaced by implementation work but never previously
  tracked under any number. The CTO should review this reconstruction for accuracy.

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

## Sprint 2 — Identity & Access (Complete — 4 of 4 stories done)

**Correction (18 July 2026):** This section previously described a stale 9-story AUTH-001..009 backlog (models → OTP service → mobile auth → OAuth → JWT → sessions → RBAC → rate limiting → audit logging) that no longer matches `docs/AI/Project_Tracker.xlsx`, the authoritative backlog source. The Tracker defines a smaller, 4-story Sprint 2, each a full vertical slice (backend + mobile + tests), not a layered breakdown. The table below reflects the current, real backlog. See `docs/implementation/plans/Plan_S02_AUTH-001.md`'s Supersession Notice for the full history of this correction.

Scope is limited strictly to the Identity & Access domain (`03_DOMAIN_MODEL.md`) — no Customer/Provider profile creation, which is deferred to its own later sprint even though registration triggers it conceptually in `14_USER_FLOWS.md` Flow 1.

| Story | Description | Status |
|--------|-------------|--------|
| AUTH-001 | Register and sign in with Mobile OTP | ✅ Done |
| AUTH-002 | Register and sign in with Google or Apple | ✅ Done |
| AUTH-003 | Stay signed in and manage active sessions | ✅ Done |
| AUTH-004 | Access the app according to my role | ✅ Done |

**Sprint 2 (Identity & Access) is now complete.** All four plans (`Plan_S02_AUTH-001.md` through
`Plan_S02_AUTH-004.md`) were re-planned against the current, authoritative 4-story tracker scope and are no
longer stale; see each story's respective Walkthrough for completed implementation detail.

## Sprint 3 — Customer Profile & Locations (Complete — 2 of 2 stories done)

Scope is limited to the Customer domain (`03_DOMAIN_MODEL.md`): the customer-facing profile/preferences record
auto-provisioned at registration, and the customer's saved service-location addresses. Does not include the
Provider-side profile equivalent (PRO-001/002) or a full bottom-navigation shell — both deferred to their own
later stories.

| Story | Description | Status |
|--------|-------------|--------|
| CUS-001 | Set up my customer profile and preferences | ✅ Done |
| CUS-002 | Manage my service locations | ✅ Done |

**Sprint 3 (Customer Profile & Locations) is now complete.** See
`docs/implementation/walkthroughs/Walkthrough_S03_CUS-001.md` and
`docs/implementation/walkthroughs/Walkthrough_S03_CUS-002.md` for each story's completed implementation
detail.

## Sprint 4 — Provider Storefront (Complete — 2 of 2 stories done)

Scope is limited to the Provider domain (`03_DOMAIN_MODEL.md`): the Business/Freelancer listing itself and
storefront management. Does not include the Verification gate (VER-001), the Category domain, or
Claim-Your-Listing — all deferred to their own later stories.

| Story | Description | Status |
|--------|-------------|--------|
| PRO-001 | Create my business or freelancer listing | ✅ Done |
| PRO-002 | Manage my provider storefront | ✅ Done |

**Sprint 4 (Provider Storefront) is now complete.** See
`docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md` and
`docs/implementation/walkthroughs/Walkthrough_S04_PRO-002.md` for each story's full implementation detail.

PRO-001 shipped the new `provider` domain module (`providers`, `business_profiles`, `freelancer_profiles`
tables), the immutable-type onboarding wizard (S-15 through S-18a/b), a new `RoleAssignmentService` enabling the
`provider → identity` cross-module role grant (ADR-016), and a strict one-Provider-per-Account rule. PRO-002
completed the Provider aggregate (`provider_availability`, `portfolios`, `service_areas`, and the new interim
`provider_category_labels` table, Decision 1), added this codebase's first file-upload capability
(`FileStorage`/`LocalFileStorage`, ADR-017, explicitly interim pending real AWS infrastructure), and delivered
the ongoing Storefront screen (S-25) on mobile. A newly created Provider always defaults to
`verification_status=pending`/`is_discoverable=false` and is not yet discoverable to customers — that gate is
lifted only once VER-001 (Verification, not yet built) ships and approves it. Neither PRO-001 nor PRO-002
implements any part of the Verification gate itself; PRO-002 only documents (without implementing) which field
(`business_profiles.trade_license_number`) is the most plausible future re-verification trigger candidate.

## Sprint 5 — Provider Verification (Complete — 2 of 2 stories done)

Per `docs/AI/Project_Tracker.xlsx`'s Sprint/Milestone structure (ML5, "Provider Verification"), the first story
is **VER-001**, which the Tracker lists as depending on PRO-001 (done). Scope covers the full Verification
domain's trust gate: document submission (VER-001) and admin review/approval (VER-002).

| Story | Description | Status |
|--------|-------------|--------|
| VER-001 | Submit my provider verification | ✅ Done |
| VER-002 | Review provider verification as an administrator | ✅ Done |

**Sprint 5 (Provider Verification) is now complete.** See
`docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md` and
`docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md` for each story's full implementation detail.

VER-001 shipped a new `verification` domain module (`verification_records`/`verification_documents`, reusing
`provider`'s existing `verification_status` Postgres enum type), a preview→confirm→submit flow with an honest
OCR stub (`StubDocumentOcrService`, ADR-018), and a private/public file-storage split for sensitive documents
(ADR-019). **Scope boundary, stated explicitly:** VER-001 only got a provider's submission into the `pending`
queue and let them view their own current status — no code that story added read or wrote
`providers.verification_status`/`is_discoverable`. VER-002 completed the gate on top of it: a new, ownerless
`require_role(ROLE_ADMIN)`-only authorization shape (ADR-023) backing an admin review queue and approve/reject
endpoints, an atomic status+discoverability cache update with a DB-level `CHECK` constraint as defense-in-depth,
two new first-slice domain modules (`administration`/ADR-021, `notification`/ADR-022), an ops-only
`grant_admin_role.py` script (ADR-020), and — following a genuine, empirically-reproduced concurrency bug found
during review — an atomic conditional-`UPDATE` optimistic-concurrency pattern (ADR-024, this codebase's first
use of it). VER-002 is backend-only by deliberate design (the admin dashboard is out of the mobile MVP's screen
inventory).

**Caveat resolved:** the Tracker's own `Depends On` field for both Sprint 6 stories was directly opened and
confirmed on 08 September 2026 — see Section 17 below. `DIR-001` depends only on already-done stories; `CLM-001`
alone carries the dependency the earlier version of this caveat was worried about.

## Sprint 6 — Directory & Listing Claims (Complete — 2 of 2 stories done)

Scope covers the first non-AI, structured browse/discovery surface (`DIR-001`) and claiming a Google-seeded
unclaimed listing (`CLM-001`), the latter built against the CTO's 09 September 2026 risk-acceptance decision
(`13_OPEN_DECISIONS.md` item 3).

| Story | Description | Status |
|--------|-------------|--------|
| DIR-001 | Browse nearby providers by category and location | ✅ Done |
| CLM-001 | Claim my Google-seeded business listing | ✅ Done |

**DIR-001** has shipped and been signed off — see
`docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md`. It builds this codebase's first `search` domain
module (no new tables of its own — the geospatial/category/discoverability query lives inside the `provider`
module, per ADR-025), confirms the `cube`/`earthdistance` GiST indexes `04_DATABASE.md` Section 13 had only ever
specified as now actually shipped, and delivers the mobile Search Filters + Search Results (S-08) screens.
Searches only self-registered, `is_discoverable=true` providers — it never touches Google-seeded/unclaimed
listings or the `is_claimed`/`google_place_id` columns.

**`CLM-001` has shipped and been signed off** — see
`docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md`. It executes exactly the design the CTO's 09
September 2026 risk-acceptance decision (`13_OPEN_DECISIONS.md` item 3) approved for MVP: bulk-importing Google
Places data as permanent, pre-claim `providers` rows without per-listing owner verification at seed time,
mitigated by an OTP-to-public-number claim gate. This story does not resolve the underlying legal question
(whether this is legally permissible under Google Maps Platform Terms of Service and UAE PDPL) — item 3 stays
Open, now updated to reflect that the mechanism is live in the codebase against real, imported data. It shipped
a new, idempotent bulk-import CLI script (`import_google_places.py`), a synthetic import-time verification
approval structurally excluded from ever counting as a real verification cycle (ADR-029 — this story's review
found and fixed a genuine gap here, see the Walkthrough for the full account), an atomic-conditional-`UPDATE`
claim-finalization race-fix plus a shared finalization helper and a new `administration.claim_review_requests`
admin-fallback queue (ADR-030), a third application of the swappable-Protocol pattern for the Google Places
client (ADR-031), and the mobile claim search/OTP screens (S-21/S-22) plus the locked "Unclaimed" banner on the
existing search results card (S-08). Item 4 (Unclaimed Listing UX)'s design was already resolved
(`16_UX_GUIDELINES.md`) and is now built exactly as specified.

## Sprint 7 — Category Domain / AI Intake foundation (In Progress — 2 of 3 stories done)

Scope covers building the real Category domain and seeding the v1 launch taxonomy (`CTG-001`), then the
Conversation/AI Intake domain itself (`AI-001`, `AI-002`) on top of it.

| Story | Description | Status |
|--------|-------------|--------|
| CTG-001 | Build the real Category domain and seed the v1 launch taxonomy | ✅ Done |
| AI-001 | Describe my service need in a guided AI conversation | ✅ Done |
| AI-002 | Route low-confidence sessions to manual matching (Sprint 7) | ⏳ Not started — unblocked at the code level, not yet planned |

**CTG-001** has shipped and been signed off — see `docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md`.
It builds this codebase's first data-seeding migration (ADR-028), a new `category` domain module
(`category.categories`/`category.category_question_templates`/`category.provider_categories`, the last created
empty), seeded with the full 14-category, 47-question v1 launch taxonomy, and a real, read-only `CategoryService`
for a future consumer to call. Backend-only — no mobile change, no HTTP route (no caller exists yet).

**`AI-001`** ("describe my service need in a guided AI conversation") has since shipped and been signed off on
top of it — see `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md`. It builds a new `conversation`
domain module (`conversation_sessions`/`messages`/`confidence_scores`, exactly per `04_DATABASE.md`'s
pre-existing spec plus two additive items — the `abandoned` status value and the `structured_criteria` JSONB
column, ADR-032/ADR-033), a swappable `ConversationAiClient` Protocol (ADR-034, the fourth application of the
`FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern) with a fully rule-based, deterministic interim
implementation, and the mobile AI Conversation screen (S-07). Ends at `conversation_sessions.status ∈ {completed,
routed_to_admin}` with zero writes to `search`/`administration` (ADR-032) — `AI-002` is the story that creates any
`search.search_requests` row or routes to manual matching. **Explicit, CTO-accepted MVP gap:** no real LLM vendor
is selected; two of the story's 11 verbatim ACs (AC3, AC5) are honestly recorded as not met, tracked as a new,
deliberately open `13_OPEN_DECISIONS.md` item 13 (ADR-035). This story's review found and fixed a mobile
error-mapping bug and a backend hard-delete-vs-soft-delete standards violation (corrected to soft-delete via a
partial unique index, ADR-036) — see the Walkthrough for the full account.

**`AI-002` is now genuinely unblocked at the code level** — `13_OPEN_DECISIONS.md` item 1 (Category Taxonomy) is
resolved and implemented, and `AI-001`'s `conversation_sessions.structured_criteria` gives it a real, validated
input to build a `search.search_requests` row from — but it **has not been planned or started**. This closeout
does not plan `AI-002`; that remains a separate future planning pass, per standing process (no story combines
with another without explicit instruction).

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
✓ Role-based authorization and audit logging (AUTH-004): a composable `require_role()` dependency (401 vs. 403 structurally guaranteed, never interchangeable), an `ensure_owner_or_not_found` ownership-check helper (404, not 403), a new `audit` module with an immutable `audit.audit_logs` table recording registration/login/logout/session_revocation events with no secrets/tokens/PII, and `GET /auth/me` (role-protected, returns id/roles/status)
✓ Customer domain — profile and preferences (CUS-001): a new `customer` schema with `customer_profiles`/
`customer_preferences` tables (1:1 with `identity.users`), auto-provisioned atomically at registration via a
new `identity → customer` cross-module service dependency (`CustomerService`, ADR-014); sensible defaults
(WhatsApp notification channel, `Accept-Language`-derived language with English fallback); `GET`/`PATCH
/customers/me` (no `{id}` parameter — ownership structurally guaranteed); lazy get-or-create backfill so
Sprint-2 accounts that predate this story never 404 on first access
✓ Customer domain — saved service-location addresses (CUS-002): `customer.saved_addresses` table (label,
address line, city, region, country code, latitude/longitude, default flag) via a reversible Alembic migration
— this codebase's first genuine soft-delete pattern (`deleted_at`/`is_active`, never a hard delete); default-
address uniqueness enforced transactionally in the service layer (unset-then-set, same session) with a partial
unique index (`uq_saved_addresses_customer_default`) as defense-in-depth; `GET`/`POST /customers/me/addresses`
and `PATCH`/`DELETE /customers/me/addresses/{address_id}` — a client-`{id}`-addressable collection (unlike
CUS-001's `/me` singleton), ownership enforced via AUTH-004's `ensure_owner_or_not_found` (404, never 403);
endpoint-shape choice recorded as ADR-015
✓ Provider domain — create my business or freelancer listing (PRO-001): a new `provider` schema with
`providers` (the aggregate root, plus a flagged temporary `category_label` column standing in for the
not-yet-built Category domain), `business_profiles`, and `freelancer_profiles` tables via a reversible Alembic
migration; a new `RoleAssignmentService` in `identity` (`ensure_role_assigned`, idempotent) lets `provider`
grant `ROLE_PROVIDER` to an already-authenticated caller on the same transaction as the new Provider row — the
reverse direction of ADR-014's `identity → customer`/`identity → audit` edges, recorded as ADR-016;
`GET`/`POST /providers/me` (a `/me` singleton per ADR-015), server-generated slugs, unconditional
`verification_status=pending`/`is_discoverable=false` defaulting regardless of subtype, and a strict
one-Provider-per-Account rule enforced at the service layer (rejects both a same-type and a different-type
second creation attempt, proving `provider_type` immutability by construction — no update endpoint exists for
it anywhere in this story)
✓ Provider domain — manage my provider storefront (PRO-002): completes the Provider aggregate via a reversible
Alembic migration adding `provider_availability`, `portfolios`, and `service_areas` (all exactly per
`04_DATABASE.md`'s pre-existing spec), plus a new, deliberately-not-`provider_categories`-named interim table
`provider_category_labels` (Decision 1) that replaces PRO-001's temporary `providers.category_label` column
(backfilled then dropped in the same migration); this codebase's first file-upload capability — a `FileStorage`
protocol with a `LocalFileStorage` implementation, served via a new `/media` `StaticFiles` mount, explicitly
interim pending real AWS infrastructure (ADR-017), with size/extension/magic-byte upload validation and
always-server-generated filenames; `PATCH /providers/me` (partial update of basic info, category labels, and
subtype-specific details) and new portfolio/availability sub-resource endpoints (`GET`/`POST
/providers/me/portfolio`, `DELETE /providers/me/portfolio/{portfolio_id}`, `PUT /providers/me/portfolio/order`,
`GET`/`PUT /providers/me/availability`), all bare-authenticated (Decision 7, mirroring ADR-016's
token-refresh-lag reasoning) with ownership enforced via `ensure_owner_or_not_found` on every genuinely
`{id}`-addressable route (ADR-015)

✓ Verification domain — submit my provider verification (VER-001): a new `verification` schema with
`verification_records`/`verification_documents` tables via a reversible Alembic migration (`status` reusing
`provider.verification_status`'s existing Postgres enum type via `create_type=False`, never a duplicate type);
`VerificationService` (`preview_document`, `submit`, `get_my_current_status`, `get_document_bytes`) and a
swappable `DocumentOcrService` Protocol whose only implementation, `StubDocumentOcrService`, honestly returns
empty candidate fields (ADR-018); `POST /providers/me/verification/documents/preview`, `POST`/`GET
/providers/me/verification`, and `GET /providers/me/verification/documents/{document_id}/file` (an
authenticated streaming download, never a public URL); a private-vs-public split added to `FileStorage`
(`public_url_prefix`, a new `read()` method, a separate never-mounted `VERIFICATION_UPLOAD_DIR` root — ADR-019)
so sensitive identity/license documents are never reachable through the public `/media` mount PRO-002 built for
portfolio photos. **This story never reads or writes `providers.verification_status`/`is_discoverable`** — a
provider's submission lands in `pending`; discoverability and verification outcome resolution were VER-002's job.

✓ Verification domain — review provider verification as an administrator (VER-002): a new, ownerless
`require_role(ROLE_ADMIN)`-only authorization shape (ADR-023) backs `AdminVerificationService`
(`admin_verification_service.py`) and four new routes at `/admin/verification` — `GET .../records` (paginated,
this codebase's first real use of `CollectionResponse`/`PaginationMeta`), `POST .../records/{id}/approve`,
`POST .../records/{id}/reject`, and `GET .../documents/{id}/file` (a sibling to the existing owner-only
download route, with deliberately no ownership check). Approving atomically transitions the record and updates
`providers.verification_status=approved`/`is_discoverable=true` — for **both** Freelancer and Business
Providers (Decision 5, user-confirmed) — on the same session/transaction, backed by a new
`chk_providers_discoverable_requires_approved` DB `CHECK` constraint as defense-in-depth. Two new first-slice
domain modules: `administration` (`admin_action_log`, written once per approve/reject, ADR-021) and
`notification` (`notifications`, hardcoded plain-language copy, never a raw status-enum value, ADR-022). A new
ops-only `backend/scripts/grant_admin_role.py` (ADR-020) grants `ROLE_ADMIN` to an already-registered Account —
no new admin login mechanism exists. A genuine concurrency bug (two truly concurrent `approve()` calls on the
same record both succeeding) was found during review and fixed with an atomic conditional `UPDATE`
(`VerificationRecordRepository.try_claim_for_review`, ADR-024). Backend-only — no mobile changes, by deliberate
design (the admin dashboard is out of the mobile MVP's screen inventory).

✓ Search domain — browse nearby providers by category and location (DIR-001): a new, first-slice `search`
module (no tables of its own — a genuinely new domain whose actual query is owned by the `provider` module it
reads, per ADR-025) exposing `GET /search/providers` (category `EXISTS` → `earth_box` GiST-indexed containment →
`earth_distance` exact recheck → `is_discoverable`/`is_active`, `ORDER BY distance_meters ASC, id ASC` for
deterministic tie-breaking) and `GET /search/categories` (an unpaginated, distinct-label picker source per
ADR-012/ADR-027), both `require_role(ROLE_CUSTOMER)`. A new `ProviderSearchRepository` (`provider` module) issues
this codebase's first raw parameterized `sqlalchemy.text()` SQL (ADR-026), since `earth_box`/`earth_distance`/
`ll_to_earth` have no SQLAlchemy ORM/Core mapping. `providers.average_rating`/`review_count` render honestly as
"No reviews yet" when `NULL` (the only state achievable today — the Review domain doesn't exist yet), never a
fabricated `0.0 (0 reviews)`. A new, reversible Alembic migration enables the `cube`/`earthdistance` extensions
and creates `idx_service_areas_location`/`idx_saved_addresses_location` (both GiST, confirming `04_DATABASE.md`
Section 13's long-specified-but-unbuilt design), verified via a real `EXPLAIN (FORMAT JSON)` test at
representative volume to confirm the planner genuinely chooses the index over a sequential scan.

✓ Provider domain — claim my Google-seeded business listing (CLM-001): a new, idempotent, manually-invoked CLI
script (`backend/scripts/import_google_places.py`) bulk-imports Business listings from the Google Places API,
keyed on `google_place_id`, behind a new swappable `GooglePlacesClient` Protocol (`HttpxGooglePlacesClient`/
`FakeGooglePlacesClient`, ADR-031 — the third application of the `FileStorage`/`DocumentOcrService`
Protocol-swappability pattern). Imported rows are created `listing_source=google_seeded_unclaimed`,
`is_claimed=false`, and — to satisfy `03_DOMAIN_MODEL.md`'s "starts as Unclaimed and is discoverable" rule
alongside the `chk_providers_discoverable_requires_approved` DB constraint — a synthetic
`verification_status=approved`/`is_discoverable=true` state paired with a matching, never-human-reviewed
`verification_records` row (ADR-029). A new `ClaimService` (`GET /claims/search`, `POST
/claims/{provider_id}/request-otp`/`verify-otp`/`request-admin-review`) sends an OTP only to the provider's own
stored public phone number (never a client-supplied one — structurally, by omitting any phone-number parameter),
and on success runs a shared `_finalize_claim` helper: an atomic conditional `UPDATE`
(`ProviderRepository.try_claim_for_account`, mirroring ADR-024's `try_claim_for_review` race-fix) sets
`is_claimed=true`/`user_id`/`claimed_at`, resets `verification_status=pending`/`is_discoverable=false` (the same
gate a self-registered Business starts in), and grants `ROLE_PROVIDER`. A new `administration.claim_review_requests`
table and `AdminClaimService` (`/admin/claims`, backend-API-only) back the AC6 fallback when OTP verification
fails or no public number exists — the same shared `_finalize_claim` helper both success paths call (ADR-030).
Post-claim re-syncs only backfill genuinely empty fields, never overwriting an owner's edits. **A genuine gap
found during review and fixed**: the synthetic import-time `verification_records` row was initially not excluded
from `VerificationRecordRepository.get_latest_for_provider`, silently blocking a freshly claimed listing's first
real verification submission — fixed by excluding any record matching `status=approved AND reviewed_by IS NULL`
(the exact, exclusive signature of a system-generated approval), recorded as part of ADR-029.
`search.SearchResultProviderResponse` gains one additive `is_claimed: bool` field (Decision 8) so the mobile
Search Results card can render the locked "Unclaimed" banner.

✓ Category domain — build the real Category domain and seed the v1 launch taxonomy (CTG-001): a new
`category` schema with `categories`, `category_question_templates`, and `provider_categories` (created empty)
tables, all exactly per `04_DATABASE.md`'s pre-existing spec, via this codebase's first data-seeding migration
(`ON CONFLICT (slug) DO NOTHING ... RETURNING`-gated inserts sourced from a plain-data `seed_data.py` module with
no ORM import, ADR-028) that seeds the full CTO-approved 14-category, 47-question v1 launch taxonomy
(`docs/AI/17_CATEGORY_TAXONOMY.md`, now v1.1.0). A new, real, read-only `CategoryService`
(`list_active_categories`, `get_question_templates`) exposes both tables for a future cross-module consumer —
no `api.py`/HTTP route in this story, since no real caller (`AI-001`) exists yet. Does not touch
`provider.provider_category_labels`, does not populate `provider_categories`, and does not alter DIR-001's
`search` module in any way.

✓ Conversation / AI Intake domain — describe my service need in a guided AI conversation (AI-001): a new
`conversation` schema with `conversation_sessions`, `messages`, and `confidence_scores` tables, exactly per
`04_DATABASE.md`'s pre-existing spec plus two additive items — a fourth `conversation_status` value, `abandoned`,
and a new `structured_criteria` JSONB column on `conversation_sessions` (AC9's `search_requests`-ready,
Pydantic-validated payload, ADR-033). A new swappable `ConversationAiClient` Protocol (`process_turn`, ADR-034 —
the fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern) with one shipped
implementation, `RuleBasedConversationAiClient`: resolves a category via case-insensitive substring matching
against the seeded taxonomy (never guessing on zero/multiple matches) and walks that category's required
follow-up questions verbatim in `sort_order`, so no question or fact outside `category.categories`/
`category_question_templates` can ever be surfaced (AC10, a structural guarantee, tested directly). `POST
/conversations`, `POST /conversations/{id}/messages`, `PATCH /conversations/{id}/answers/{message_id}` (AC8's
truncate-and-regenerate revise flow — soft-deletes truncated messages via a partial unique index on
`(conversation_session_id, sequence_number)`, ADR-036), and `GET /conversations/{id}`, all
`require_role(ROLE_CUSTOMER)` + `ensure_owner_or_not_found`. `ConversationSessionResponse` never includes a raw
confidence field (AC6, enforced at the API-contract level). Confidence-threshold completion and a hard turn cap
are both `Settings` (`CONVERSATION_CONFIDENCE_THRESHOLD`, `CONVERSATION_MAX_TURNS`), not code. **Ends at
`conversation_sessions.status ∈ {completed, routed_to_admin}`** with zero writes to `search`/`administration`
(ADR-032, Tracker-confirmed) — `AI-002` is the story that creates any `search.search_requests` row or routes to
manual matching. **Explicit, CTO-accepted MVP gap:** no real LLM vendor is selected anywhere in this codebase —
AC3 (system prompts as version-controlled files) and AC5 (a null provider field reported as unknown) are honestly
recorded as not met by this fully rule-based interim implementation, tracked as `13_OPEN_DECISIONS.md` item 13
(ADR-035).

The first business module (Identity & Access) is now fully shipped — mobile OTP, Google/Apple sign-in, session/refresh-token management, and role-based authorization + audit logging (AUTH-001 through AUTH-004). Sprint 2 is complete. The Customer domain is now fully shipped as well — profile/preferences (CUS-001) and saved addresses (CUS-002) — completing Sprint 3. The Provider domain is now fully shipped for its Sprint 4 scope — PRO-001 shipped the Provider aggregate root and onboarding wizard, and PRO-002 has since completed the aggregate (portfolio/availability/service-area/category-labels) and the ongoing Storefront screen — completing Sprint 4. **Sprint 5 (Provider Verification) is now complete**: VER-001 shipped the document-submission half of the Verification domain, and VER-002 has since shipped the admin review/approval half on top of it, including this codebase's first two `administration`/`notification` domain modules. **Sprint 6 (Directory & Listing Claims) is now complete**: DIR-001 shipped this codebase's first Search domain slice — a structured (non-AI) category+radius+discoverability directory query and its mobile Search Filters/Search Results screens; CLM-001 has since shipped on top of it — the Google Places bulk-import script, the OTP-to-public-number claim flow, and the admin-review fallback, executing the CTO's 09 September 2026 risk-acceptance decision (`13_OPEN_DECISIONS.md` item 3, which stays open at the legal level). **Sprint 7 (Category Domain / AI Intake foundation) is now in progress, 2 of 3 stories done**: CTG-001 has shipped the real Category domain and its seeded v1 launch taxonomy — `13_OPEN_DECISIONS.md` item 1 is now resolved and implemented; `AI-001` has since shipped on top of it — the real `conversation` domain module, a swappable `ConversationAiClient` Protocol with a fully rule-based interim implementation, and the mobile AI Conversation screen (S-07), ending at `conversation_sessions.status ∈ {completed, routed_to_admin}` with zero writes to `search`/`administration` (`AI-002`'s job). No real LLM vendor is selected yet — this is an explicit, CTO-accepted MVP gap tracked as `13_OPEN_DECISIONS.md` item 13. `AI-002` is now genuinely unblocked at the code level but has not yet been planned or started.

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
- Identity & Access module (`backend/app/modules/identity/`) — mobile OTP registration/login (AUTH-001), establishing the `backend/app/modules/<domain>/...` structural convention every later domain module will follow; Google/Apple sign-in (AUTH-002) built on top of it, adding JWKS-based ID-token verification and `OAuthService`; session management and refresh-token rotation (AUTH-003) built on top of both, adding `SessionService`, `sessions`/`refresh_tokens` tables, and a real `get_current_user` dependency; role-based authorization and audit logging (AUTH-004) built on top of all three, adding `require_role()`, `ensure_owner_or_not_found`, a new `backend/app/modules/audit/` module (immutable `audit_logs` table), and `GET /auth/me` — completing Sprint 2
- Customer module (`backend/app/modules/customer/`) — profile and preferences (CUS-001), the first module of the
  new Customer domain: `customer_profiles`/`customer_preferences` tables, `CustomerService` (auto-provisioning,
  get-or-create, `Accept-Language` parsing), and `GET`/`PATCH /customers/me`. Required one edit to `identity`
  (`AuthService` gained a `CustomerService` constructor dependency, mirroring AUTH-004's `AuditService` wiring)
  — no other existing module was touched. Saved service-location addresses (CUS-002) built on top of it in the
  same module: `saved_addresses` table, `SavedAddressRepository` (this codebase's first genuine soft-delete
  method), `SavedAddressService` (default-uniqueness, ownership enforcement, reuses `CustomerService`'s
  get-or-create rather than duplicating it), and `GET`/`POST`/`PATCH`/`DELETE /customers/me/addresses`. Touched
  no other existing module. This completes the Customer domain's Sprint 3 scope.
- Provider module (`backend/app/modules/provider/`) — create my business or freelancer listing (PRO-001), the
  first module of the new Provider domain: `Provider`/`BusinessProfile`/`FreelancerProfile` models,
  `ProviderService` (one-provider-per-account enforcement, server-generated slugs, unconditional
  verification/discoverability defaulting), and `GET`/`POST /providers/me`. Required one new capability in
  `identity` (`RoleAssignmentService`, a small idempotent role-grant service, wired into
  `provider/dependencies.py` — the reverse of CUS-001's `AuthService → CustomerService` edge) — no existing
  `identity` file (`AuthService` included) was modified. Manage my provider storefront (PRO-002) built on top
  of it in the same module: `ProviderAvailability`/`Portfolio`/`ServiceArea`/`ProviderCategoryLabel` models,
  `PortfolioService`/`AvailabilityService` (new), `ProviderService.update_basic_info` (new), and `PATCH
  /providers/me` plus the new portfolio/availability sub-resource endpoints. Also added a new
  `backend/app/shared/storage/` module (`FileStorage` protocol, `LocalFileStorage`, image-upload validation) —
  this codebase's first file-upload capability, shared infrastructure rather than domain-specific, per
  `02_ARCHITECTURE.md`'s "Infrastructure depends on Domain" placement. Touched no other existing module. This
  completes the Provider domain's Sprint 4 scope.

- Verification module (`backend/app/modules/verification/`) — submit my provider verification (VER-001), the
  first module of the new Verification domain: `VerificationRecord`/`VerificationDocument` models (`status`
  reusing `provider.models.VerificationStatus` rather than a duplicate enum), `VerificationService`, and the
  preview/submit/status/document-download endpoints. Required a small, additive extension to the existing
  `backend/app/shared/storage/` module (`FileStorage` gains `public_url_prefix`/`read()`; a new
  `file_signatures.py`/`document_validation.py`) — zero behavior change to PRO-002's existing portfolio wiring.
  A new, one-directional `verification → provider` cross-module service edge (`ProviderService.get_my_provider`,
  read-only, ADR-014/ADR-016's established shape) was added; no existing `provider` file was modified to support
  it. Touched no other existing module. This shipped Sprint 5's first story.

- Verification module, extended — review provider verification as an administrator (VER-002): a new
  `AdminVerificationService`/`admin_api.py` inside the existing `verification` module (deliberately a separate
  service class from the provider-facing `VerificationService` — different authorization model, callers, and
  side effects), plus `VerificationRecordRepository.try_claim_for_review` (the atomic conditional-`UPDATE`
  concurrency fix, ADR-024). Two genuinely new domain modules were created for the first time:
  `backend/app/modules/administration/` (`AdminActionLog`/`AdminActionLogRepository`/`AdminActionLogService`,
  ADR-021) and `backend/app/modules/notification/` (`Notification`/`NotificationRepository`/
  `NotificationService`, ADR-022) — both first slices of domains that previously had zero code. `provider`
  gained one new write method (`ProviderService.apply_verification_outcome`) and one new `CHECK` constraint on
  `providers` (no column changes). A new ops-only `backend/scripts/grant_admin_role.py` (ADR-020) was added,
  never exposed via HTTP. Touched no mobile code. This completes Sprint 5's scope. `administration` gained a
  second slice in Sprint 6 (CLM-001): `models.py`'s `ClaimReviewRequest`,
  `repositories/claim_review_request_repository.py`, and `services/claim_review_request_service.py`
  (`create`/`list_open`/`resolve`, mirroring `AdminActionLogService`'s explicit-methods convention) — see below.

- Search module (`backend/app/modules/search/`) — browse nearby providers by category and location (DIR-001),
  the first module of the new Search domain: no `models.py` (no new tables — the actual query is owned by
  `provider`, per ADR-025), `SearchService` (constructor-injected `ProviderService` dependency only, the
  ADR-014/016 shape), and `GET /search/providers`/`GET /search/categories`. `provider` gained one new
  `ProviderSearchRepository` (issuing this codebase's first raw parameterized `sqlalchemy.text()` SQL, ADR-026)
  and one new `ProviderService.search_nearby`/`list_distinct_category_labels` read-only method pair, plus a new
  reversible Alembic migration (`cube`/`earthdistance` extensions, `idx_service_areas_location`/
  `idx_saved_addresses_location` GiST indexes). Touched no other existing module. This shipped Sprint 6's first
  story.

- Provider module, extended — claim my Google-seeded business listing (CLM-001): a new
  `services/claim_service.py` (`ClaimService`, `_finalize_claim`), `services/admin_claim_service.py`
  (`AdminClaimService`), `services/google_places_client.py` (`GooglePlacesClient` Protocol,
  `HttpxGooglePlacesClient`, `FakeGooglePlacesClient`, ADR-031), and two new routers (`claim_api.py`,
  `admin_claim_api.py`). `ProviderRepository` gained `get_by_google_place_id`, `search_unclaimed`, and
  `try_claim_for_account` (the atomic conditional-`UPDATE` race-fix, ADR-030); `ProviderService` gained
  `create_google_seeded_provider`, `backfill_google_seeded_provider`, and `search_unclaimed_listings`. A new,
  first-time `provider → administration` cross-module edge (`ClaimReviewRequestService`) mirrors VER-002's
  existing `verification → administration` shape. `search`'s `SearchResultProviderResponse` gained one additive
  `is_claimed: bool` field. A new ops-only `backend/scripts/import_google_places.py` CLI script bulk-imports and
  re-syncs listings, mirroring `seed_roles.py`/`grant_admin_role.py`'s shape. A genuine gap was found and fixed
  during review: `verification`'s `VerificationRecordRepository.get_latest_for_provider` now excludes the
  import-time synthetic `verification_records` row (ADR-029) — the one change this story made to an existing
  `verification` file, isolated to a single query's `WHERE` clause. This completes Sprint 6's scope.

- Category module (`backend/app/modules/category/`) — build the real Category domain and seed the v1 launch
  taxonomy (CTG-001): a new `category` schema with `models.py` (`Category`, `CategoryQuestionTemplate`,
  `ProviderCategory`), `repositories/` (`CategoryRepository.list_active`,
  `CategoryQuestionTemplateRepository.list_for_category`), `services/category_service.py` (`CategoryService`:
  `list_active_categories`, `get_question_templates`), and `dependencies.py` — no `api.py`, mirroring
  `administration`/`notification`'s "first slice of a real domain, no HTTP route" shape. A new
  `seed_data.py` (plain data, no ORM import) sources this codebase's first data-seeding migration
  (`category_domain`, ADR-028), which seeds the full 14-category, 47-question taxonomy via an idempotent
  `ON CONFLICT (slug) DO NOTHING ... RETURNING`-gated insert. Touched no other existing module — does not read or
  write `provider.provider_category_labels`, and `category.provider_categories` was created empty. This shipped
  Sprint 7's first story.

- Conversation module (`backend/app/modules/conversation/`) — describe my service need in a guided AI
  conversation (AI-001), the first module of the new Conversation/AI Intake domain: `models.py`
  (`ConversationStatus`, `MessageSender`, `ConversationSession`, `Message`, `ConfidenceScore`),
  `repositories/` (`conversation_session_repository.py`, `message_repository.py`,
  `confidence_score_repository.py`), `services/conversation_ai_client.py` (`ConversationAiClient` Protocol,
  `RuleBasedConversationAiClient`, ADR-034), `services/structured_criteria.py`
  (`StructuredCriteria`/`StructuredCriteriaAnswer`, ADR-033), `services/conversation_service.py`
  (`ConversationService`), `api.py`, `schemas.py`, and `dependencies.py`. A new, first-time
  `conversation → customer` and `conversation → category` cross-module edge pair (constructor-injected,
  same-session, mirroring ADR-014/016 exactly) — `category`/`customer` gained no new import from `conversation`.
  Two genuine issues found and fixed during review: a mobile `ConversationRepository._mapError` bug conflating
  two unrelated HTTP 422 causes, and a backend standards violation where `MessageRepository.delete_after_sequence`
  originally hard-deleted truncated messages rather than soft-deleting them (`04_DATABASE.md`'s Common Columns
  rule) — corrected, requiring `uq_messages_session_sequence`'s promotion to a partial unique index (ADR-036).
  Touched no other existing module. This shipped Sprint 7's second story.

Remaining business modules are deferred until their corresponding sprint stories.

The Flutter mobile app has moved beyond the default scaffold: Riverpod/GoRouter/Dio/l10n infrastructure plus the Splash, Language Selection, Phone Entry, and OTP Entry screens (AUTH-001), real Google/Apple sign-in buttons on the Phone Entry screen (AUTH-002), and secure cross-restart session persistence, a silent-refresh Dio interceptor, and a "Log out" action on the Home stub (AUTH-003), are implemented. A dedicated Manage Sessions UI was deliberately not built this story (see AUTH-003's Walkthrough). CUS-001 added a new `features/customer/` module and a Profile & Settings screen (reachable via a temporary entry point on the Home stub, not yet a bottom-nav tab) plus an `AcceptLanguageInterceptor` on `ApiClient`. CUS-002 extended `features/customer/` with a Saved Addresses management screen and a skippable first-address prompt wired into registration, plus a new shared, reusable `LocationPickerScreen` (`shared/widgets/location_picker/`) and three new Flutter dependencies (`google_maps_flutter`, `geolocator`, `geocoding`). PRO-001 added a new `features/provider/` module (a five-screen onboarding wizard reusing `LocationPickerScreen` for address/base-location capture) and this codebase's first shared `StepIndicator` widget, plus a "List Your Business" tile on Profile & Settings. PRO-002 extended `features/provider/` with the ongoing Storefront screen (S-25, four independently-saveable sections), a portfolio manager widget backed by a new `image_picker` dependency, and a new shared `WeeklyHoursEditor` widget (`shared/widgets/weekly_hours_editor.dart`) factored out of PRO-001's onboarding screen. VER-001 added a new, sibling `features/verification/` module (the S-19 upload, OCR-confirm, and S-20 status screens, using a new `file_picker` dependency since `image_picker` cannot browse an arbitrary PDF), wired into the end of the Provider onboarding wizard and a new status chip on the Storefront screen; two small shared additions (`shared/models/provider_type.dart`, moved from `features/provider/`, plus two new minimal accessor repositories — `CurrentProviderTypeRepository`, `VerificationStatusSummaryRepository`) keep `features/provider/` and `features/verification/` from importing each other's internals directly, per `02_ARCHITECTURE.md`'s "features must not depend directly on each other" rule (a real coupling violation the architect caught and this fix resolved — see VER-001's Walkthrough). DIR-001 added a new `features/search/` module (Search Filters and Search Results — S-08 — screens, a reusable `ProviderSearchCard` widget, Riverpod controllers) and rewired `HomePlaceholderScreen`'s "Find a Service" button to open it, replacing CUS-002's temporary "coming soon" snackbar. `features/search/` (and the pre-existing `features/home/`) import `features/customer/`'s `SavedAddressRepository` directly to pre-fill the search origin — a real, logged architecture-rule deviation, not fixed in this story (`13_OPEN_DECISIONS.md` item 12). CLM-001 extended `features/search/` (the unclaimed "Warning"-color banner on the existing `ProviderSearchCard`, a new `onClaimTap` callback) and added a new, sibling `features/claim/` module — the Claim Search (S-21) and Claim OTP (S-22) screens, backed by `claim_repository.dart` and Riverpod controllers, reachable both from the search-card banner and a new secondary entry point on the Home placeholder screen. AI-001 added a new, sibling `features/conversation/` module — the AI Conversation screen (S-07), backed by `conversation_repository.dart` and a Riverpod `ConversationController` owning the >3s/>8s latency-tier timers and an in-flight-turn queue (input is never frozen while a turn is in flight), reachable from a new primary "Describe what you need" entry point on the Home placeholder screen. The full S-06 Home screen (AI input box, mic icon), a bottom-navigation shell, and all other feature areas remain unbuilt.

---

# 15. Current Limitations

Not yet implemented:

- Authentication / Identity & Access — complete: mobile OTP registration/login (AUTH-001), Google/Apple OAuth (AUTH-002), session/refresh-token management (AUTH-003), and role-based authorization + audit logging (AUTH-004) are all done. RBAC/audit is no longer a gap. Note: a permission-catalog/ABAC layer beyond simple role-name checks, and an admin-facing audit-log-viewing endpoint, remain out of scope until a future story requires them.
- Customer domain — no longer a gap, fully shipped: auto-provisioned profile/preferences (display name, avatar, language, notification channel) and `GET`/`PATCH /customers/me` (CUS-001); saved service-location addresses, map-pin/manual/current-location entry, and a skippable first-address-at-registration flow (CUS-002).
- Provider profile (Business / Freelancer) — no longer a gap: PRO-001 shipped the Provider aggregate root,
  immutable-type onboarding wizard, and one-Provider-per-Account enforcement; PRO-002 completed the aggregate
  (portfolio, availability, service area, category labels) and the ongoing Storefront/Edit Profile screen. A
  newly created Provider still starts with `is_discoverable=false`, but VER-002 has since shipped the admin
  approval path that flips it to `true` for an approved Provider of either subtype — the full submit-to-discoverable
  path now exists end to end, and DIR-001 has since shipped a structured way to actually browse those
  discoverable providers. Claim-Your-Listing (`CLM-001`) **has since shipped** — a Google Places bulk-import
  script, the OTP-to-public-number claim flow, and an admin-review fallback for a failed claim attempt, executing
  the CTO's 09 September 2026 risk-acceptance decision despite `13_OPEN_DECISIONS.md` item 3's Google Places
  legal/PDPL review remaining genuinely open. The real
  Category domain **has since shipped (CTG-001, Sprint 7)** — `category.categories`/
  `category.category_question_templates`/`category.provider_categories` all now exist, seeded with the full v1
  launch taxonomy. `provider_category_labels` (PRO-002) remains in place, unchanged, as a free-text interim
  stand-in — DIR-001's category filter (ADR-027) still works against it, not the real taxonomy; reconciling the
  two is a separate, not-yet-scheduled follow-up story, tracked at `13_OPEN_DECISIONS.md` item 1.
- Category taxonomy — **no longer a gap, fully shipped (CTG-001):** the real `category` schema domain
  (`categories`/`category_question_templates`/`provider_categories`) exists and is seeded with the CTO-approved
  14-category, 47-question v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md` v1.1.0), exposed via a
  real, read-only `CategoryService` for a future consumer. **Not yet built:** any HTTP route for reading it (no
  caller exists yet — deferred to `AI-001`), native-speaker verification of the seeded Arabic text (tracked
  non-blocking at the source-document level), and reconciling `provider_category_labels` into
  `provider_categories` (a separate, deferred story).
- Conversation / AI Intake — **`AI-001` has shipped**: a customer can describe their need in free text, get
  routed to a resolved category, and answer that category's required follow-up questions one at a time, ending in
  a `completed` (with a validated `structured_criteria` payload) or `routed_to_admin` session. **Explicit,
  CTO-accepted MVP gap:** the AI is fully rule-based/deterministic — no real LLM vendor is selected
  (`13_OPEN_DECISIONS.md` item 13) — so AC3 (system prompts as version-controlled files) and AC5 (a null provider
  field reported as unknown) are honestly not met. **Not yet built:** `AI-002` (routing a low-confidence session
  to manual matching) — genuinely unblocked at the code level by `AI-001`'s `structured_criteria` payload, but not
  yet planned or started.
- Search & Matching — **partially shipped as of DIR-001**: a structured, proximity-ordered (non-AI) directory
  browse exists (`GET /search/providers`/`GET /search/categories`, the mobile Search Filters/Search Results
  screens), searching only self-registered, `is_discoverable=true` providers via free-text category exact-match
  (`13_OPEN_DECISIONS.md` item 1's interim posture, ADR-027) and the now-confirmed-shipped `cube`/`earthdistance`
  GiST indexes (`04_DATABASE.md` Section 13). **Not yet built:** `AI-002` (Sprint 7 — now unblocked at the code
  level by `AI-001`'s `conversation_sessions.structured_criteria` output, but not yet planned or started),
  AI-ranked/merit-based results (MAT-001), and the real
  `search.search_requests`/`provider_matches`/`search_event_log` tables — DIR-001's query is deliberately
  ephemeral and writes none of them (`Plan_S06_DIR-001.md` Decision 5), and `AI-001` deliberately never writes to
  `search` either (Decision 1/ADR-032).
- Contact View
- Verification — no longer a gap, fully shipped for its Sprint 5 scope: VER-001 (submit my provider
  verification) lets a provider upload a document, review OCR-stub-assisted (currently empty) fields, and
  submit into the `pending` queue; VER-002 (review provider verification as an administrator) adds the
  admin-only review queue, approve/reject endpoints (atomically updating `providers.verification_status`/
  `is_discoverable`), the `admin_action_log` write, and the notification send on status change. A real OCR
  pipeline remains unbuilt; `StubDocumentOcrService` (ADR-018) is explicitly interim. No admin dashboard UI
  (mobile or web) exists — the four new admin endpoints have no consumer beyond a direct API client
  (Postman/curl/a future internal tool) today; the broader admin operations dashboard (ADM-002) remains a
  separate, later story.
- Review / Outcome Tag
- Notifications — partially shipped as of VER-002: `notification.notifications` exists and is written to on a
  verification status change, with honest, hardcoded plain-language copy. **Not yet built:** any real delivery
  channel (WhatsApp/SMS/Email), `notification_delivery`, `notification_preferences`, and any "read my
  notifications" inbox endpoint or UI — Sprint 12 ("Engagement & Trust") remains this domain's own dedicated
  future milestone.
- Administration — partially shipped as of VER-002/CLM-001: `administration.admin_action_log` exists and records
  every admin approve/reject action; `administration.claim_review_requests` (CLM-001) exists and backs the
  claim-flow's admin-review fallback (`/admin/claims`, backend-API-only). **Not yet built:** any admin dashboard
  UI, Admin User as a first-class managed entity, Manual Match Assignment, Unmatched Query Reports, feature flags,
  or system settings — all of ADM-002's wider "operations dashboard" scope, explicitly out of both VER-002's and
  CLM-001's bounds.
- Flutter application (beyond the auth flow and the Profile & Settings screen — Home screen, a bottom-navigation shell, and all other feature areas)

These will be implemented according to the approved sprint backlog, gated by the open decisions in `13_OPEN_DECISIONS.md`. Category taxonomy (item 1) no longer blocks the AI intake work at the code level as of CTG-001 — `AI-001` has since shipped on top of it, and `AI-002` is genuinely unblocked, though not yet planned or started. Item 3 (the Google Places legal review) no longer blocks `CLM-001` either, as of the CTO's 09 September 2026 risk-acceptance decision — but the underlying legal question itself remains open regardless of what it now gates. Item 13 (real LLM vendor selection), added at `AI-001`'s close, does not block anything already shipped, but must resolve before AC3/AC5 can ever be genuinely satisfied.

---

# 16. Overall Progress

Project Planning — 100%

Architecture — 100%

Engineering Standards — 100%

AI Knowledge Base — 100%

Backend Foundation — 100%

Identity & Access — Complete (4 of 4 stories done: AUTH-001, AUTH-002, AUTH-003, AUTH-004)

Customer Domain — Complete (2 of 2 Sprint 3 stories done: CUS-001, CUS-002)

Provider Profile — Complete (Sprint 4, 2 of 2 stories done: PRO-001, PRO-002)

Provider Verification — Complete (Sprint 5, 2 of 2 stories done: VER-001, VER-002 — a Provider can now submit
for verification, be reviewed by an Admin, and become discoverable once approved)

Directory & Listing Claims — Complete (Sprint 6, 2 of 2 stories done: DIR-001 shipped a structured,
non-AI directory browse; CLM-001 shipped the Google Places bulk-import/claim flow, executing the CTO's 09
September 2026 risk-acceptance decision on `13_OPEN_DECISIONS.md` item 3, which stays open at the legal level)

Category Domain — Complete for Sprint 7's foundation scope (CTG-001 shipped the real `category` schema domain
and seeded the v1 launch taxonomy; `13_OPEN_DECISIONS.md` item 1 resolved and implemented)

Conversation / AI Intake — In Progress (Sprint 7, 1 of 2 stories done: `AI-001` shipped the real `conversation`
schema domain, a swappable `ConversationAiClient` Protocol with a fully rule-based interim implementation, and
the mobile AI Conversation screen — S-07; no real LLM vendor selected yet, `13_OPEN_DECISIONS.md` item 13 open;
`AI-002` unblocked at the code level, not yet planned)

Flutter Application — In Progress (auth flow: Splash with session recovery, Language Selection, Phone Entry with Google/Apple sign-in, OTP Entry, Home stub with Log out; Profile & Settings screen with live language switching, CUS-001; Saved Addresses management, a shared Location Picker, and a skippable first-address-at-registration flow, CUS-002; Provider onboarding wizard — type selection, basic info, Business/Freelancer details, PRO-001; Storefront screen — portfolio, availability, category labels, PRO-002; Verification upload/confirm/status screens — S-19/S-20, VER-001; VER-002 is backend-only, no mobile changes; Search Filters/Search Results screens — S-08, DIR-001; unclaimed-listing banner, Claim Search/Claim OTP screens — S-21/S-22, CLM-001; AI Conversation screen — S-07, AI-001)

Deployment — Not Started

Overall Estimated Project Completion: Approximately 58-63%

---

# 17. Next Planned Story

Sprint 2 (Identity & Access) is **complete** — AUTH-001, AUTH-002, AUTH-003, and AUTH-004 have all shipped
and been signed off.

Sprint 3 (Customer Profile & Locations) is **complete** — CUS-001 (set up my customer profile and preferences)
and CUS-002 (manage my service locations) have both shipped and been signed off.

Sprint 4 (Provider Storefront) is **complete** — PRO-001 ("create my business or freelancer listing") and
PRO-002 ("manage my provider storefront") have both shipped and been signed off; see
`docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md` and
`docs/implementation/walkthroughs/Walkthrough_S04_PRO-002.md`.

**Sprint 5 (Provider Verification) is complete** — **VER-001** ("submit my provider verification") and
**VER-002** ("review provider verification as an administrator") have both shipped and been signed off; see
`docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md` and
`docs/implementation/walkthroughs/Walkthrough_S05_VER-002.md`.

**Sprint 6 (Directory & Listing Claims) is complete — both DIR-001 and CLM-001 are done.**
`DIR-001` ("browse nearby providers by category and location") shipped and was signed off on 09 September 2026;
see `docs/implementation/walkthroughs/Walkthrough_S06_DIR-001.md`. `CLM-001` ("claim my Google-seeded business
listing") has since shipped on top of it and was signed off on 09 September 2026; see
`docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md`. `CLM-001` executes — does not resolve — the CTO's
explicit risk-acceptance decision recorded in `docs/AI/13_OPEN_DECISIONS.md` item 3: the underlying legal
question (whether bulk-importing Google Places data as permanent, pre-claim `providers` rows is permissible
under Google's current Maps Platform Terms of Service and UAE PDPL) remains genuinely open — no legal counsel
review or first-party reading of Google's current terms has happened, and item 3 stays **Open** even though the
story it gated has shipped. This is a deliberate acceptance of known exposure, not a finding that the activity is
compliant; the `listing_source`/`google_place_id` bulk-deletion mitigation item 3 describes is now operative
against real, imported data rather than a theoretical schema affordance. This story's review found and fixed one
genuine gap (the import-time synthetic verification approval was not initially excluded from a claimant's
"latest verification cycle," blocking their first real submission) — see the Walkthrough for the full account.

**Sprint 7 (Category Domain / AI Intake foundation) is in progress — `CTG-001` and `AI-001` are both done,
`AI-002` remains.**
`CTG-001` ("build the real Category domain and seed the v1 launch taxonomy") shipped and was signed off on
09 September 2026; see `docs/implementation/walkthroughs/Walkthrough_S07_CTG-001.md`. `13_OPEN_DECISIONS.md`
item 1 (Category Taxonomy) is now resolved and implemented, genuinely unblocking `AI-001`/`AI-002` at the code
level. `AI-001` ("describe my service need in a guided AI conversation") has since shipped and was signed off on
10 September 2026; see `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md`. It builds the real
`conversation` domain module (`conversation_sessions`/`messages`/`confidence_scores`, plus the additive
`abandoned` status value and `structured_criteria` JSONB column), a swappable `ConversationAiClient` Protocol
(ADR-034) with a fully rule-based, deterministic interim implementation, and the mobile AI Conversation screen
(S-07). It ends at `conversation_sessions.status ∈ {completed, routed_to_admin}`, with zero writes to
`search`/`administration` — `AI-002` is the story that creates any `search.search_requests` row or routes to
manual matching, now with a real, validated `structured_criteria` input to build from. **Explicit, CTO-accepted
MVP gap**: no real LLM vendor is selected — AC3 and AC5 are honestly recorded as not met, tracked as a new,
deliberately open `13_OPEN_DECISIONS.md` item 13. This story's review found and fixed a mobile error-mapping bug
and a backend hard-delete-vs-soft-delete standards violation (corrected via a promoted partial unique index) —
see the Walkthrough for the full account. **`AI-002` is not yet planned or started** — this closeout deliberately
does not plan it; that is a separate future planning pass.

**With `AI-001` now shipped, the next genuinely unblocked candidate is `AI-002`** (routing low-confidence
sessions to manual matching, Sprint 7, unblocked at the code level by `AI-001`'s `structured_criteria` output).
Whether to plan `AI-002` next — or any other sequencing choice — is a product/sequencing call for the CTO, not
one this document makes on its own; **no engineering agent should plan or start `AI-002` without that explicit
direction**, matching this document's own established convention for every prior "genuinely unblocked but not yet
planned" story.

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
