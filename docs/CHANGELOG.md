# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

Current Version: 0.1.0 (Pre-MVP)

---

## [Unreleased]

### Added
- Search domain (new `search` schema) and Administration domain (third slice) — receive matches even when AI
  confidence is low (Story AI-002): a new reversible Alembic migration creates `search.search_requests`,
  `search.provider_matches`, `search.search_event_log`, and adds `administration.manual_match_assignments` to
  the existing `administration` schema — all column-for-column per `04_DATABASE.md`'s pre-existing spec
  **except four flagged nullable-column deviations** (three anticipated by the Plan —
  `manual_match_assignments.assigned_admin_id`, `search_requests.structured_criteria`,
  `search_requests.customer_latitude`/`customer_longitude` — plus a genuine fourth found during implementation,
  `search_requests.category_id`, since a hard-turn-cap `routed_to_admin` session can occur with no category ever
  resolved), each recorded plainly rather than fabricated (**ADR-038**). A new, first-time `conversation →
  search`, `search → administration`, and `search → customer` cross-module edge triple (**ADR-037**, confirmed
  cycle-free) wires `ConversationService`'s two terminal session transitions (`completed`, `routed_to_admin`) to
  a new `SearchRequestService.handle_session_completed(...)` — the single call site inside
  `_apply_completion_policy`. A single shared, private `_finalize_matches` helper (**ADR-040**) is the **only**
  place in the codebase that ever writes `provider_matches` rows, sets `search_requests.status` to its final
  `matched`/`unmatched` value, or writes a `search_event_log` row — called by both the automated path (reusing
  `search.SearchService`/`provider.ProviderService.search_nearby`, DIR-001, entirely unchanged — no new ranking
  algorithm, since the Review domain hasn't shipped and there's no real rating signal to rank by yet, **ADR-041**)
  and the manual path (an admin resolving a `routed_to_admin` session's queue entry). A new
  `administration.ManualMatchAssignmentService` (**ADR-039**) — `create`/`list_pending`/`get_by_id`/`resolve`,
  the fourth application of the passive-queue-row pattern (`admin_action_log`/VER-002,
  `claim_review_requests`/CLM-001 before it) — backs a new pull-based admin queue, `GET
  /api/v1/admin/search/manual-matches` and `POST /api/v1/admin/search/manual-matches/{id}/resolve` (both
  `require_role(ROLE_ADMIN)`, backend-API-only, no dashboard UI — `ADM-001`'s job). A new customer-facing `GET
  /api/v1/search-requests/{id}` (`ensure_owner_or_not_found`) returns a `SearchRequestResultResponse` whose shape
  is byte-for-byte identical regardless of whether the request was resolved automatically or by an admin.
  `ConversationSessionResponse` gains exactly one new field, `search_request_id: uuid.UUID | None` — no
  confidence/score field added, preserving `AI-001`'s AC6 and this story's own AC3 unchanged. A new
  `test_no_forbidden_customer_copy.py` asserts `{"manual", "fallback", "admin"}` never appear in any
  customer-facing string literal or live HTTP response, satisfying AC3/AC7 as an automated test rather than a
  style guideline. **Fixed during review:** (1) the `tester` found `SearchRequestService.resolve_manual_match`
  called `_finalize_matches` **before** `ManualMatchAssignmentService.resolve`'s already-resolved guard, so two
  sequential resolve attempts on the same assignment could both finalize before the guard on the second call
  ever had a chance to reject it — fixed by reordering (the guard now runs first); (2) the `architect`'s
  subsequent review found the guard itself was still a plain read-then-write, not truly atomic — a genuine TOCTOU
  race remained for two truly concurrent admins resolving the same assignment. Fixed by adding
  `ManualMatchAssignmentRepository.try_resolve`, a single atomic conditional `UPDATE ... WHERE status =
  'pending'`, mirroring `ProviderRepository.try_claim_for_account` (CLM-001, ADR-030) and
  `VerificationRecordRepository.try_claim_for_review` (VER-002, ADR-024) exactly — the **third** application of
  this atomic-conditional-update pattern, proven with a genuine two-independent-database-session concurrency
  test; (3) the same review pass found `resolve_manual_match` never validated admin-supplied `provider_ids`
  before writing `provider_matches`, so a bogus id surfaced as an opaque 500 instead of a proper 4xx — fixed by
  validating every id against the existing `ProviderService.list_by_ids` before any mutation, raising a new
  `InvalidManualMatchProviderIdsError` (422) otherwise. A second `architect` review pass confirmed both fixes and
  returned **APPROVED with zero remaining findings**. This completes Sprint 7 (Category Domain / AI Intake
  foundation) in full and, with it, Milestone ML7 (`CTG-001`, `AI-001`, `AI-002`) entirely.
- Mobile AI Conversation screen, extended, and a new shared results-rendering module (Story AI-002): a full
  shared-widget extraction — `mobile/lib/shared/models/ranked_provider_result.dart` and
  `mobile/lib/shared/widgets/provider_result_card.dart`/`ranked_provider_results_list.dart` (generalized from
  `features/search`'s existing `ProviderSearchCard`, with a nullable `distanceMeters` rendered by omitting the
  distance line rather than guessing/zeroing it) — now serve both `features/search`'s Search Results screen
  (S-08) and `features/conversation`'s completion state; neither feature imports the other's screen/widget file
  directly, a cleaner outcome than `13_OPEN_DECISIONS.md` item 12's already-logged debt, not a new instance of
  it. `ai_conversation_screen.dart`'s completion state, previously a static "we're finding matches for you"
  message with no results mechanism to link to, now renders the shared ranked-results widget inline once
  `status` is `matched`/`unmatched`, while `pending_manual_match` keeps showing the **exact existing** waiting
  copy verbatim (never a new string that could reintroduce a forbidden word), with lifecycle-aware polling
  (paused when the app is backgrounded via `WidgetsBindingObserver`, cancelled on dispose/"Start over") since no
  real push-notification delivery channel exists yet.
- Conversation / AI Intake domain — describe my service need in a guided AI conversation (Story AI-001): a new
  `conversation` Postgres schema with `conversation_sessions`, `messages`, and `confidence_scores` tables, all
  exactly per `04_DATABASE.md`'s pre-existing spec, via a new reversible Alembic migration (`conversation_domain`).
  Two additive items beyond that spec: `conversation_status` gains a fourth value, `abandoned` (set when a
  customer starts a new session while a previous one is still `active`); and `conversation_sessions` gains
  `structured_criteria` (JSONB, nullable), a `search_requests`-ready payload validated via a new
  `StructuredCriteria` Pydantic model and populated only when a session reaches `status=completed` — recorded
  together as **ADR-032**/**ADR-033**. A new swappable `ConversationAiClient` Protocol (`process_turn`) — the
  fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` Protocol-swappability
  precedent — with one shipped implementation, `RuleBasedConversationAiClient` (**ADR-034**): resolves a category
  from the customer's free text via case-insensitive substring matching against the seeded taxonomy, returning a
  clarifying quick-reply category picker rather than ever guessing on zero or multiple matches, then walks that
  category's required follow-up questions verbatim, one at a time, in `sort_order` — no code path can emit a
  question, category, or fact absent from the seeded `category.categories`/`category_question_templates` rows,
  proven directly by a new structural grounding test rather than claimed by prompt instruction. Confidence rises
  in equal steps as required questions are answered, `0.0` while unresolved and `1.0` once complete.
  `ConversationService` (`POST /api/v1/conversations`, `POST /api/v1/conversations/{id}/messages`, `PATCH
  /api/v1/conversations/{id}/answers/{message_id}`, `GET /api/v1/conversations/{id}`, all
  `require_role(ROLE_CUSTOMER)` + `ensure_owner_or_not_found`) applies a confidence-threshold-then-turn-cap
  completion policy, both `Settings` (`CONVERSATION_CONFIDENCE_THRESHOLD`, `CONVERSATION_MAX_TURNS`), not code.
  Revising a previous answer (`PATCH .../answers/{message_id}`) truncates every later message in the session and
  regenerates the next turn fresh from the shorter history, clearing any stale `structured_criteria`.
  `ConversationSessionResponse` never includes a raw confidence field anywhere in its schema. This story ends at
  `conversation_sessions.status ∈ {completed, routed_to_admin}` — it makes **zero** writes to
  `search.search_requests`/`provider_matches`/`search_event_log` or `administration.manual_match_assignments`
  (**ADR-032**, Tracker-confirmed scope boundary); `AI-002` is the story that creates any `search_requests` row or
  routes to manual matching. **Explicit, CTO-accepted MVP gap (ADR-035):** no real LLM vendor is selected
  anywhere in this codebase — two of this story's 11 verbatim acceptance criteria, AC3 (system prompts stored as
  version-controlled files) and AC5 (a retrieved provider record's null field reported as unknown, never
  estimated), are honestly recorded as **not met** by this fully rule-based interim implementation, not silently
  skipped, tracked as a new `docs/AI/13_OPEN_DECISIONS.md` item 13. **Fixed during review:** (1) a mobile
  `ConversationRepository._mapError` bug that mapped every HTTP 422 response to "this answer can no longer be
  revised," even for an unrelated request-body validation failure on `POST /conversations`/`POST .../messages` —
  fixed by distinguishing the revise-specific 422 (`PATCH .../answers/{id}`) from every other endpoint's 422; (2)
  a backend standards violation (**ADR-036**) — the revise-answer flow originally hard-`DELETE`d truncated
  messages, reasoned on a factually incorrect premise that `messages` lacked a soft-delete column (it is
  `CommonColumnsMixin`-based and already has `deleted_at`/`is_active`, like every other soft-deletable table in
  this codebase); corrected to soft-delete, mirroring `saved_addresses`' precedent, requiring
  `uq_messages_session_sequence`'s promotion from a plain unique constraint to a **partial** unique index (`WHERE
  is_active = true`).
- Mobile AI Conversation screen (Story AI-001): a new, sibling `features/conversation/` module — the AI
  Conversation screen (S-07) with a tiered perceived-latency UI (a typing indicator through 3 seconds, a
  contextual label from 3–8 seconds, then "we'll notify you" hand-off messaging past 8 seconds or on a timeout —
  never an indefinite spinner), an in-flight-turn queue so the input field is never frozen while a turn is being
  processed, quick-reply chips for `single_select`/`multi_select` questions, an inline tap-to-revise editor on any
  past customer bubble (gated to still-`active` sessions only), an always-available "Start over" action, and
  never a numeric confidence value anywhere in the widget tree. RTL-mirrored chat bubbles and Arabic prompt/
  response rendering verified on this screen. A new primary "Describe what you need" entry point was added to the
  Home placeholder screen.
- Provider domain — claim my Google-seeded business listing (Story CLM-001): a new, idempotent, manually-invoked
  CLI script (`backend/scripts/import_google_places.py`) bulk-imports Business listings from the Google Places
  API, upserting on `google_place_id` so the same script run serves as both the first bulk seed and every later
  re-sync, behind a new swappable `GooglePlacesClient` Protocol (`HttpxGooglePlacesClient` real implementation,
  `FakeGooglePlacesClient` test-only — recorded as ADR-031, the third application of the `FileStorage`/
  `DocumentOcrService` Protocol-swappability precedent). Imported rows are created
  `listing_source=google_seeded_unclaimed`, `is_claimed=false`, with a populated `google_place_id` — never
  `self_registered`. To satisfy `03_DOMAIN_MODEL.md`'s "starts as Unclaimed and is discoverable" rule alongside
  the existing `chk_providers_discoverable_requires_approved` DB constraint, the import job also sets a synthetic
  `verification_status=approved`/`is_discoverable=true` state paired with a matching, never-human-reviewed
  `verification_records` row (`reviewed_by=NULL`) — recorded as **ADR-029**. A new customer-facing `ClaimService`
  (`GET /api/v1/claims/search`, `POST /api/v1/claims/{provider_id}/request-otp`/`verify-otp`/`request-admin-review`)
  finds an unclaimed listing by name/address substring match and sends an OTP only to the provider's own stored
  public phone number — structurally, by never accepting a phone-number parameter of any kind, never a
  client-supplied one. On success, a shared `_finalize_claim` helper (also called by the admin-approval fallback
  path, so the two success paths can never drift apart) atomically claims the listing via a new conditional
  `UPDATE ... WHERE is_claimed = false` (`ProviderRepository.try_claim_for_account`, mirroring VER-002's
  `try_claim_for_review` race-fix, ADR-024), resets `verification_status=pending`/`is_discoverable=false` — the
  same Verification gate a self-registered Business starts in — and grants `ROLE_PROVIDER`. A new
  `administration.claim_review_requests` table and `AdminClaimService` (`/api/v1/admin/claims`, backend-API-only,
  no dashboard UI, mirroring VER-002's precedent) back the fallback path when OTP verification fails or the
  listing has no usable public number — recorded together with the finalization pattern as **ADR-030**. Once
  claimed, subsequent re-syncs only backfill genuinely empty fields, never overwriting an owner's edits. A new,
  additive `is_claimed: bool` field on `search.SearchResultProviderResponse` (DIR-001) lets the mobile Search
  Results card render the locked "Unclaimed" banner. **Fixed during review (commit `0df2e48`):** the tester found
  that the import-time synthetic `verification_records` row was not excluded from
  `VerificationRecordRepository.get_latest_for_provider`, so it silently outlived the claim-time reset and
  blocked a freshly claimed listing's first real verification submission with a 409, directly contradicting AC5's
  "routes through the same Verification gate a self-registered Business would go through." Fixed by excluding any
  record matching `status=approved AND reviewed_by IS NULL` — confirmed as the exact, exclusive signature of a
  system-generated (never-human-reviewed) approval, since every real admin approval always sets `reviewed_by`.
  This executes — does not resolve — the CTO's explicit risk-acceptance decision on the still-open Google Places
  legal/UAE-PDPL question (`docs/AI/13_OPEN_DECISIONS.md` item 3).
- Mobile claim-a-listing screens (Story CLM-001): a new, sibling `features/claim/` module — the Claim Search
  screen (S-21, free-text search among unclaimed listings) and the Claim OTP screen (S-22, code entry with an
  always-visible "This isn't working" admin-review-fallback link, never conditional on repeated failures), backed
  by `claim_repository.dart` and Riverpod controllers. `features/search/`'s existing `ProviderSearchCard` (DIR-001)
  now renders a full-width, solid Warning-color banner ("Unclaimed — Is this your business? Claim it") when a
  result's `isClaimed` is `false`, navigating directly to the Claim OTP screen for that listing. A new secondary
  entry point ("Already listed on Google? Claim your business") was added to the Home placeholder screen.
- Category domain — build the real Category domain and seed the v1 launch taxonomy (Story CTG-001): a new
  `category` Postgres schema with `categories`, `category_question_templates`, and `provider_categories`
  (created empty) tables, all exactly per `04_DATABASE.md`'s pre-existing spec, via a new reversible Alembic
  migration (`category_domain`) — this codebase's first data-seeding migration, recorded as ADR-028: an
  idempotent `INSERT ... ON CONFLICT (slug) DO NOTHING ... RETURNING` against `categories`, with
  each category's question-template insert batch gated on that category having been genuinely freshly inserted
  this run (`category_question_templates` has no unique constraint of its own per spec, so its idempotency is
  entirely inherited from the parent's conflict target), and an `upgrade()` DDL-existence-check guard making the
  function safely re-callable outside Alembic's own one-time-per-revision bookkeeping. Seeds the full
  CTO-approved v1 launch taxonomy — 14 categories and 47 AI follow-up question templates
  (`docs/AI/17_CATEGORY_TAXONOMY.md`, bumped to v1.1.0 after implementation found v1.0.0 was missing the Arabic
  question text its own prose claimed existed; the CTO supplied real first-pass Arabic text for all 47 questions).
  A new, real, read-only `CategoryService` (`list_active_categories`, `get_question_templates`) exposes both
  tables for a future cross-module consumer (`AI-001`) — no `api.py`/HTTP route in this story, since no real
  caller exists yet, mirroring the established `ProviderService.list_by_ids` cross-module-read precedent.
  Backend-only; does not modify, migrate, or reconcile `provider.provider_category_labels`, and does not alter
  DIR-001's `search` module or its endpoint behavior in any way. **Fixed during review:** a tautological test
  assertion (`assert "questions_unique_constraints" not in info`, a dict key never added, so it always passed
  regardless of the database's real state) was replaced with a real assertion against
  `inspector.get_unique_constraints(...)`. `docs/AI/13_OPEN_DECISIONS.md` item 1 (Category Taxonomy) is now
  resolved *and implemented* — `AI-001`/`AI-002` and everything cascading from them through Sprint 12 are
  genuinely unblocked at the code level.
- Search domain — browse nearby providers by category and location (Story DIR-001): a new, first-slice `search`
  module (no new tables — the domain's actual query is owned by the `provider` module it reads, recorded as
  ADR-025) exposing `GET /api/v1/search/providers` (category exact-match → `earth_box` GiST-indexed containment
  → `earth_distance` exact recheck → `is_discoverable`/`is_active`, deterministic `ORDER BY distance_meters ASC,
  id ASC` tie-break) and `GET /api/v1/search/categories` (an unpaginated distinct-label picker source, extending
  ADR-012's exception). Both endpoints require `ROLE_CUSTOMER`, no guest path, per `14_USER_FLOWS.md` Flow 1. A
  new, reversible Alembic migration enables the `cube`/`earthdistance` Postgres contrib extensions and creates
  `provider.service_areas`'s and `customer.saved_addresses`'s `idx_service_areas_location`/
  `idx_saved_addresses_location` GiST indexes, exactly per `04_DATABASE.md` Section 13's pre-existing (previously
  unbuilt) spec — verified via a real `EXPLAIN (FORMAT JSON)` test at representative volume to confirm the
  planner genuinely chooses the index over a sequential scan. A new `ProviderSearchRepository` (`provider`
  module) issues this codebase's first raw parameterized `sqlalchemy.text()` SQL (ADR-026), since
  `earth_box`/`earth_distance`/`ll_to_earth` have no SQLAlchemy ORM/Core mapping. Category filtering is a
  case-insensitive exact match against the existing free-text `provider_category_labels.label` (never substring/
  `ILIKE`), an explicitly interim mechanism pending the real Category Taxonomy (recorded as ADR-027).
  `average_rating`/`review_count` render honestly ("No reviews yet" when `NULL`, never a fabricated `0.0 (0
  reviews)`) since the Review domain has never been built. **Fixed during review:** an N+1 query in
  `SearchService.search_providers` (one category-label lookup per result instead of a batch), resolved with a
  new `ProviderService.get_category_labels_by_provider_id` batch method mirroring the already-batched photo-URL
  lookup. **Logged as accepted debt, not fixed in this story:** mobile `features/search`/`features/home` both
  import `features/customer`'s `SavedAddressRepository` directly — a real, pre-existing-in-kind architecture-rule
  violation, recorded as `docs/AI/13_OPEN_DECISIONS.md` item 12 pending a deliberate shared-abstraction
  extraction covering both call sites together.
- Mobile Search screens (Story DIR-001): a new `features/search/` module — the Search Filters screen (category
  chips, a location field pre-filled from the customer's default saved address, a radius slider) and the real
  S-08 Search Results screen (provider cards, two textually distinct empty states — "no search performed yet" vs.
  "no results for this search" — loading/error states, pull-to-refresh). A new, reusable `ProviderSearchCard`
  widget renders rating+count honestly and has no ranking-specific UI, so a future AI-ranked-results story
  (MAT-001) can reuse it unchanged. `HomePlaceholderScreen`'s "Find a Service" button now opens the Search
  Filters screen, replacing CUS-002's temporary "coming soon" snackbar.
- Verification domain — review provider verification as an administrator (Story VER-002): a new, ownerless
  `require_role(ROLE_ADMIN)`-only authorization shape (recorded as ADR-023, extending ADR-015's framework with a
  genuinely third category) backs four new admin-only routes at `/api/v1/admin/verification`: `GET .../records`
  (paginated — this codebase's first real use of the previously-unused `CollectionResponse`/`PaginationMeta`
  infrastructure), `POST .../records/{record_id}/approve`, `POST .../records/{record_id}/reject` (requires a
  non-empty `rejection_reason`), and `GET .../documents/{document_id}/file` (a new sibling to the existing
  owner-only document-download route, deliberately with no ownership check). Approving atomically transitions
  the `verification_records` row and sets `providers.verification_status=approved`/`is_discoverable=true` on the
  same transaction, for **both** Freelancer and Business Providers (a user-confirmed interpretive decision);
  rejecting never sets `is_discoverable=true`. A new DB-level `chk_providers_discoverable_requires_approved`
  `CHECK` constraint on `provider.providers` is a second, independent, DB-enforced layer alongside the
  transactional mechanism. Two new, first-slice domain modules: `administration`
  (`administration.admin_action_log`, written once per approve/reject action, ADR-021) and `notification`
  (`notification.notifications`, hardcoded plain-language copy on a status change, never a raw
  `VerificationStatus` enum value, ADR-022) — both honestly minimal, in-app-record-only capabilities; no real
  WhatsApp/SMS/Email delivery and no admin dashboard UI exist yet. A new ops-only
  `backend/scripts/grant_admin_role.py` CLI script (ADR-020) grants `ROLE_ADMIN` to an already-registered
  Account via the existing OTP/Google/Apple sign-in path; no new admin login mechanism was built. **Fixed during
  review:** a genuine, empirically-reproduced concurrency bug — two truly concurrent `approve()` calls against
  the same record could both succeed, each writing a duplicate `admin_action_log`/`notification` row — resolved
  with an atomic conditional `UPDATE ... WHERE status IN (...)` (`VerificationRecordRepository.
  try_claim_for_review`, ADR-024, this codebase's first use of this optimistic-concurrency-control pattern),
  with a regression test verified to fail without the fix and pass with it. Backend-only — no mobile changes, by
  deliberate design (the admin operations dashboard is explicitly excluded from the mobile MVP's screen
  inventory).
- Verification domain — submit my provider verification (Story VER-001): new `verification` Postgres schema
  with `verification.verification_records` and `verification.verification_documents` tables via a reversible
  Alembic migration. `verification_records.status` reuses `provider.verification_status`'s existing Postgres
  enum type (`create_type=False`) rather than duplicating it. New `POST
  /api/v1/providers/me/verification/documents/preview` (validate + OCR-stub + stash to a private pending slot;
  writes no DB row), `POST`/`GET /api/v1/providers/me/verification` (submit / read latest status), and `GET
  /api/v1/providers/me/verification/documents/{document_id}/file` (authenticated, ownership-checked byte
  stream). A new swappable `DocumentOcrService` Protocol — the only implementation shipped,
  `StubDocumentOcrService`, always returns empty candidate fields, honestly, pending a future real OCR pipeline
  — recorded as ADR-018. `FileStorage` (ADR-017) gains a `public_url_prefix` parameter and a `read()` method so
  verification documents are stored under a separate, never-mounted `VERIFICATION_UPLOAD_DIR` root and are never
  reachable through the existing public `/media` mount — recorded as ADR-019. Submitting creates a `pending`
  `verification_records` row; **this story never reads or writes `providers.verification_status`/
  `is_discoverable`** — discoverability and verification outcome remain entirely VER-002's responsibility, not
  yet built.
- Mobile Verification screens (Story VER-001): a new, sibling `features/verification/` module — S-19 (document
  upload, via a new `file_picker` Flutter dependency since `image_picker` cannot browse an arbitrary PDF), an
  OCR-confirm step (editable fields, copy honestly framed as "we couldn't read this automatically yet"), and
  S-20 (status view with a Resubmit action on rejection). Wired into the end of the Provider onboarding wizard
  and a new status chip on the Storefront screen. Two small shared additions —
  `shared/models/provider_type.dart` (moved from `features/provider/`) and two new minimal accessor
  repositories, `CurrentProviderTypeRepository`/`VerificationStatusSummaryRepository` — keep
  `features/provider/` and `features/verification/` from importing each other's internals directly, per
  `02_ARCHITECTURE.md`'s "features must not depend directly on each other" rule (fixing a real coupling
  violation caught during architect review).
- Provider domain — manage my provider storefront (Story PRO-002): completes the Provider aggregate via a
  reversible Alembic migration adding `provider.provider_availability`, `provider.portfolios`, and
  `provider.service_areas` (all exactly per `04_DATABASE.md`'s pre-existing spec), plus a new,
  deliberately-not-`provider_categories`-named interim table `provider.provider_category_labels`
  (`provider_id`, `label`, `is_primary`, partial unique index enforcing exactly one primary per provider) that
  replaces PRO-001's temporary `providers.category_label` column — the migration backfills every existing value
  into the new table and drops the column in the same step. New `PATCH /api/v1/providers/me` (partial update of
  basic info, category labels, and subtype-specific details; never touches `verification_status`/
  `is_discoverable`), `GET`/`POST /api/v1/providers/me/portfolio`, `DELETE
  /api/v1/providers/me/portfolio/{portfolio_id}`, `PUT /api/v1/providers/me/portfolio/order`, and `GET`/`PUT
  /api/v1/providers/me/availability` — all bare-authenticated, ownership enforced via `ensure_owner_or_not_found`
  on the genuinely `{id}`-addressable portfolio-delete route (ADR-015). **Breaking change** to the pre-launch
  `ProviderResponse` shape: `category_label: str` is replaced by `category_labels: list[CategoryLabelResponse]`
  (acceptable pre-launch, no real API consumers yet). This codebase's first file-upload capability: a
  `FileStorage` protocol with a `LocalFileStorage` implementation (local filesystem, git-ignored `UPLOAD_DIR`,
  served via a new `/media` `StaticFiles` mount), explicitly interim pending real AWS infrastructure — recorded
  as ADR-017 in `09_DECISIONS.md`. Uploads are validated for size, extension, and a magic-byte
  content sniff against the declared MIME type, and always stored under a server-generated filename, never the
  client's original filename.
- Mobile Storefront screen (Story PRO-002): a new ongoing Storefront screen (S-25) in `features/provider/` with
  four independently-saveable sections (basic info incl. category labels, subtype-specific details, portfolio
  manager, availability editor), replacing the "you already have a listing" snackbar from PRO-001 with real
  navigation. New `image_picker` Flutter dependency backs the portfolio manager's "Add Photo" action. A new
  shared `WeeklyHoursEditor` widget was factored out of PRO-001's onboarding screen to avoid duplicating the
  per-weekday hours UI, extended with a per-weekday emergency-availability toggle.
- Provider domain — create my business or freelancer listing (Story PRO-001): new `provider` Postgres schema
  with `providers` (the aggregate root, plus a flagged, temporary `category_label VARCHAR(100) NOT NULL` column
  standing in for the not-yet-built Category domain), `business_profiles`, and `freelancer_profiles` tables via
  a reversible Alembic migration; three new enums (`provider_type`, `listing_source`, `verification_status`)
  scoped to the `provider` schema. A new `RoleAssignmentService` in `identity`
  (`ensure_role_assigned(user_id, role_name)`, idempotent, flush-only) lets `provider` grant `ROLE_PROVIDER` to
  an already-authenticated caller on the same transaction as the new Provider row — the reverse direction of
  ADR-014's `identity → customer`/`identity → audit` edges, recorded as ADR-016; `AuthService`'s own
  registration-time role assignment is untouched. New `GET`/`POST /api/v1/providers/me` (a `/me` singleton per
  ADR-015), gated by bare authentication only. `POST` accepts type, basic info, and subtype-specific details in
  a single submission, generates a server-side `slug`, and unconditionally defaults
  `verification_status=pending`/`is_discoverable=false` regardless of subtype or request input. A caller may
  create at most one Provider per Account — enforced at the service layer (rejects both a same-type and a
  different-type second creation attempt, since no update endpoint for `provider_type` exists anywhere in this
  story).
- Mobile Provider onboarding wizard (Story PRO-001): a new `features/provider/` module — five screens (intro,
  choose type, basic info, business details, freelancer details) backed by an in-memory Riverpod draft
  controller, submitting exactly one `createProvider()` call at the end. Reuses CUS-002's `LocationPickerScreen`
  unmodified for both Business address and Freelancer base-location capture. This codebase's first shared
  `StepIndicator` widget (`shared/widgets/step_indicator.dart`) satisfies the multi-step-form step-indicator
  requirement. A new "List Your Business" tile on Profile & Settings checks for an existing listing first
  (`getMyProvider()`) before entering the wizard.
- Saved service-location addresses (Story CUS-002): new `customer.saved_addresses` table (label, address line,
  city, region, country code, latitude/longitude, default flag), linked to `customer_profiles`, via a
  reversible Alembic migration — this codebase's first genuine soft-delete pattern (`deleted_at`/`is_active`,
  never a hard `session.delete()`; every read path filters `is_active`). Default-address uniqueness is enforced
  transactionally in the service layer (unset every other active default before writing the new one, same
  session) with a partial unique index (`uq_saved_addresses_customer_default`, on `customer_id` WHERE
  `is_default = true AND is_active = true`) as defense-in-depth, not the sole mechanism. New `GET`/`POST
  /api/v1/customers/me/addresses` and `PATCH`/`DELETE /api/v1/customers/me/addresses/{address_id}`, gated by
  `require_role(customer)` — a client-`{id}`-addressable collection (unlike CUS-001's `/me` singleton),
  ownership enforced defensively via AUTH-004's `ensure_owner_or_not_found` (404, never 403, on both a missing
  row and a row owned by another customer). Unpaginated per ADR-012's small/single-owner-scoped carve-out.
- Mobile Saved Addresses feature (Story CUS-002): three new Flutter dependencies (`google_maps_flutter`,
  `geolocator`, `geocoding`) back a new shared, reusable `LocationPickerScreen`
  (`shared/widgets/location_picker/`, zero Customer-domain coupling, built for future Provider-domain reuse) —
  map-pin selection, manual entry, and "use current location," all reverse-geocoded into editable address
  fields. A skippable first-address prompt is now inserted into both registration success paths (mobile OTP and
  Google/Apple sign-in), after session establishment so Skip can never block registration; a temporary "Find a
  Service" button on the Home placeholder screen re-prompts (non-skippable) only when the customer has zero
  addresses and attempts to search — the real AI Conversation/Search feature doesn't exist until Sprint 7/8.
  New Saved Addresses management screen (linked from Profile & Settings) with an Undo-on-delete snackbar and,
  when deleting the current default, either a "choose a new default" bottom sheet or a clear "no default set"
  indicator.
- Customer profile and preferences (Story CUS-001): new `customer` Postgres schema with `customer_profiles`
  and `customer_preferences` tables (one-to-one with `identity.users`) via a reversible Alembic migration;
  `customer_preferences.language` reuses the existing `identity.language_code` enum (`create_type=False`)
  rather than duplicating it, and a new `notification_channel` enum (`whatsapp`/`sms`/`email`, default
  `whatsapp`) is scoped to the `customer` schema as its first consumer. Completing registration via mobile OTP
  (AUTH-001) or Google/Apple sign-in (AUTH-002) now also creates a `customer_profiles` row and a
  `customer_preferences` row in the same database transaction as the `User` row — `AuthService` gained a
  `CustomerService` constructor dependency and calls it inline inside its existing `is_new_user` branch, flush
  only, mirroring the `identity → audit` cross-module pattern already shipped in AUTH-004. Default language is
  derived from the `Accept-Language` request header (q-value aware), falling back to English on a missing or
  malformed header; `identity`'s endpoints now read and forward this header, never interpreting it themselves.
  New `GET`/`PATCH /api/v1/customers/me`, both gated by `require_role(customer)`, resolving the target
  exclusively from the caller's JWT — no `{id}` path parameter exists, so cross-account access is structurally
  impossible rather than defensively checked. Sprint-2 accounts that predate this story are backfilled lazily:
  `get_my_profile`/`update_my_profile` are get-or-create, so a legacy caller's first `GET`/`PATCH` call
  transparently provisions their row instead of 404ing.
- Mobile Profile & Settings screen (Story CUS-001): a new `features/customer/` module (editable display name,
  avatar URL, language toggle, notification-channel picker), reachable via a temporary entry point from the
  Home placeholder screen. Changing language calls the `PATCH` endpoint and updates the existing
  `LanguageController` in the same call, taking effect immediately with no app restart. A new
  `AcceptLanguageInterceptor` was added to `ApiClient`, closing a pre-existing gap where no outgoing request
  ever sent an `Accept-Language` header. First automated RTL test in this codebase (`pumpApp`/`pumpScreen`
  gained an optional `Locale?` parameter), establishing the pattern for future RTL acceptance criteria.
- Role-based authorization and audit logging (Story AUTH-004): a new `require_role()` FastAPI dependency
  (`app/api/dependencies.py`), composable and layered on top of the existing `get_current_user` — a
  missing/invalid/expired token still 401s inside `get_current_user`; `require_role()` raises the new
  `InsufficientRoleError` (403) only for a validly authenticated caller whose `roles` claim doesn't intersect
  the endpoint's allowed set. New `ensure_owner_or_not_found` helper (`app/core/authorization.py`) collapses
  "resource doesn't exist" and "exists but isn't yours" into the same non-revealing 404; `SessionService`'s
  session-ownership check was refactored to use it (no behavior change). New `audit` module
  (`app/modules/audit/`) with an immutable `audit.audit_logs` table (`identity.users`-linked, no
  soft-delete/version columns) via a reversible Alembic migration, backing a new `AuditService` with four
  explicit event methods (`record_registration`, `record_login`, `record_logout`,
  `record_session_revocation`), wired into `AuthService` (registration/login on every OTP/OAuth
  authentication) and `SessionService` (logout vs. session_revocation, including bulk revoke-all) — no
  secrets, tokens, or PII appear in any audit row. New `GET /api/v1/auth/me`, protected by
  `require_role(customer, provider, admin)`, returning the caller's own id/roles/status via the existing
  `UserSummaryResponse` schema. Auth-endpoint rate limiting (Redis, 10/min, generic 429 message) from
  AUTH-001/AUTH-002 was re-confirmed intact and untouched.
- Session management and refresh-token rotation (Story AUTH-003): `identity.sessions` and
  `identity.refresh_tokens` tables (linked to `users`/`devices`) via a reversible Alembic migration. Access
  tokens are now 15 minutes (down from 30) and their JWT payload is narrowed to exactly `sub`, `exp`, `iat`,
  `jti`, `roles` — no email or phone. Refresh tokens are opaque (`secrets.token_urlsafe(32)`), only their
  SHA-256 hash is persisted. New `SessionService` (device/session/refresh-token lifecycle, separate from
  `AuthService`) backs new endpoints: `POST /api/v1/auth/refresh` (rotation with reuse-detection cascade —
  replaying an already-rotated or revoked refresh token revokes the entire session, not just that call),
  `GET /api/v1/auth/sessions` (lists the caller's active sessions with device/platform/last-seen, flags the
  current one), `DELETE /api/v1/auth/sessions/{session_id}`, and `POST /api/v1/auth/sessions/logout-all`
  (optional `keep_current`). Ownership enforcement collapses "not found" and "not yours" into one non-revealing
  404. `app/api/dependencies.py::get_current_user` is now a real implementation (replacing the BF-011
  placeholder that unconditionally raised), decoding the JWT into a `CurrentUser(id, session_id, roles)`.
- Mobile session persistence (Story AUTH-003): access/refresh token pairs are now persisted securely
  (`flutter_secure_storage`) across app restarts; a Dio `AuthInterceptor` attaches the access token to every
  request and performs one silent refresh-and-retry on a 401; the Splash screen validates a persisted session
  via a real refresh call before routing to Home. A bare "Log out" action was added to the existing Home stub.
  No new "Manage Sessions" UI screen was built this story (backend endpoints are fully built/tested regardless).
- Google and Apple sign-in (Story AUTH-002): `POST /api/v1/auth/google` and `POST /api/v1/auth/apple`, backed by a shared `IdTokenVerifier`/`JwksIdTokenVerifier` (RS256, JWKS-published keys) serving both providers through one verification code path, and `OAuthService`, which collapses any verification failure into a single generic, non-revealing error. `AuthService.authenticate_with_oauth` finds-or-creates a `User` by `(auth_provider, external_auth_subject)`, assigning the `customer` role only on creation, matching AUTH-001's mobile-OTP find-or-create pattern.
- Mobile Google/Apple sign-in buttons on the Phone Entry screen (`google_sign_in`, `sign_in_with_apple` packages), replacing AUTH-001's disabled placeholders, with graceful cancellation handling (no error shown, no stuck loading state) and localized failure copy (EN/AR).
- Identity & Access domain foundation (Story AUTH-001): `identity` Postgres schema with `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `devices`, `otp_verifications` tables via a reversible Alembic migration, native enums (`user_status`, `auth_provider`, `device_platform`, `language_code`, `otp_purpose`), and the reusable `CommonColumnsMixin` (`backend/app/database/mixins.py`) that every future domain migration will inherit.
- Idempotent role seeding (`customer`, `provider`, `admin`) via `backend/app/modules/identity/services/seed_data.py` and `backend/scripts/seed_roles.py`.
- Mobile OTP registration/login: `POST /api/v1/auth/request-otp` and `POST /api/v1/auth/verify-otp`, backed by `OtpService` (6-digit code via `secrets`, Argon2id-hashed, 5-minute expiry, 5-attempt lockout, non-revealing error responses) and `AuthService` (find-or-create `User` by phone, assigns `customer` role on creation, issues a stateless JWT access token — no session/refresh-token/device persistence in this story, deferred to AUTH-003).
- `SmsSender` interface with a stub implementation (`backend/app/modules/identity/services/sms_sender.py`) — no real SMS provider integrated yet; never logs the raw OTP code above `DEBUG`.
- `hash_otp_code`/`verify_otp_code` wrappers in `app/core/security.py`, reusing the existing Argon2id primitive.
- `InvalidOtpError`/`OtpLockedError` plain-language exceptions in `app/core/exceptions/exceptions.py`.
- Mobile app scaffolding stood up from the default Flutter counter app: Riverpod, GoRouter, Dio, `flutter_secure_storage`, `shared_preferences`, and bilingual (EN/AR) `flutter_localizations`/`intl` infrastructure, plus Material 3 theme tokens and a Feature-First `core/`/`shared/`/`features/` layout.
- Mobile auth flow screens: Splash (auto-routing), Language Selection (persisted), Phone Entry, and OTP Entry with a resend countdown matching the backend's 5-minute OTP expiry, wired to the live `request-otp`/`verify-otp` endpoints via `auth_repository.dart`.
- Backend tests under `backend/tests/modules/identity/` and mobile widget tests under `mobile/test/features/auth/` covering new-number registration, existing-number login, expired/reused-code rejection, attempt-cap lockout, and screen-level rendering/validation/countdown behavior.
- API schemas (`HealthResponse`, `DatabaseHealthResponse`) in `app/schemas/health.py` and service class (`HealthService`) in `app/services/health_service.py` to support modular, decoupled health checking (Story BF-007).
- Database health endpoint (`GET /api/v1/health/db`) to verify PostgreSQL connectivity using a lightweight `SELECT 1` query, returning `503 Service Unavailable` on connection failures (Story BF-007).
- Comprehensive unit tests in `tests/test_health.py` validating application and database health check responses, including mock database failure cases.
- URI-based API Versioning infrastructure setting `/api/v1` as the active API root (Story BF-006).
- Centralized API prefix constants defined in `app/core/constants.py`.
- Health check endpoint under Version 1 (`GET /api/v1/health`) returning a status code of 200 and a JSON body `{"status": "healthy"}`.
- Startup verification (`verify_routes`) to recursively check and validate route registration and uniqueness.
- Comprehensive routing and verification unit tests in `tests/test_routing.py`.
- Configure FastAPI lifespan API using the modern context manager in `app/core/lifespan.py` (Story BF-005).
- Application configuration validation on startup, ensuring valid environment settings and required variables.
- Standardized lifecycle logging for startup and shutdown sequences.
- Strongly typed `AppState` container in `app/core/app_state.py` registered under `app.state.services` for centralizing shared resources.
- Graceful cleanup during shutdown, ensuring database engine disposal runs in isolated try-except blocks.
- Comprehensive unit tests in `tests/test_lifespan.py` verifying registration, cycles, config validation, and exception resilience.
- Centralized configuration module in `app/core/config.py` using `pydantic-settings` (Story BF-002).
- Automatic `.env` configuration loading with support for parent directory lookups in monorepo structures.
- Strict startup validation for critical configuration fields (`DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `LOG_LEVEL`, and token expirations).
- Custom configuration validation unit tests in `tests/test_config.py`.
- Formatted, user-friendly CLI validation error reporting on startup.
- Alembic database migration infrastructure in `backend/alembic/` (Story BF-004).
- Added `alembic` and `greenlet` packages to python dependencies list.
- Dynamic connection string resolution in `env.py` using centralized application settings.
- Configured `env.py` to reuse the existing asynchronous database engine and declarative metadata.
- Chronological date-prefixed file naming format for migration version scripts.
- Initial pipeline validation migration script.
- Programmatic unit and integration tests for migrations in `tests/test_migrations.py`.
- Migration developer guidelines and instructions in `backend/README.md`.

### Changed
- Every login (mobile OTP, Google, Apple) now requires a `device: { device_platform, device_name }` field in
  the request body and returns a `refresh_token` alongside `access_token` (Story AUTH-003) — an additive-field
  but conforming-client-affecting contract change to the three endpoints AUTH-001/AUTH-002 previously shipped.
  `request-otp` (unauthenticated, no login outcome) was not changed.
- Replaced the `identity.users` table's global `uq_users_email` unique constraint with `uq_users_email_provider`, scoped to `(auth_provider, email)`, so the same email address under two different sign-in providers can each hold an independent account (Story AUTH-002). Promoted `httpx` from a dev-only to a runtime backend dependency to support JWKS fetching.
- Refactored the backend from a flat `app/{models,services,repositories,schemas}/` layout to the documented modular structure (`app/modules/<domain>/...`), starting with the identity domain (`app/modules/identity/`), to match `02_ARCHITECTURE.md`'s Feature-First/module convention and set the precedent for every future domain (Story AUTH-001, post-architect-review). No behavior change: 104 backend tests still passing, API route paths/contracts unchanged, mobile required zero changes.
- Enhanced `GET /api/v1/health` to use the service layer and return a structured `HealthResponse` schema containing service name and version (Story BF-007).
- Updated `app/api/router.py` to delegate to version routers (Story BF-006).
- Updated `app/core/config.py` default settings prefix to use the centralized prefix constants.
- Updated `.env.example` in the workspace root with the corrected `API_PREFIX`.
- Updated `app/main.py` to initialize FastAPI using the strongly typed config settings (title, version, debug mode, and api prefix).
- Updated `.env.example` in the workspace root with the required and optional config keys.

### Fixed
-


### Removed
-

---

## [0.1.0] - Engineering Platform

### Added

- Initial project structure.
- Flutter application foundation.
- FastAPI backend foundation.
- PostgreSQL database configuration.
- SQLAlchemy integration.
- Alembic migration framework.
- Environment configuration.
- Structured logging.
- Request ID and Correlation ID support.
- Ruff, Black, isort and mypy configuration.
- Pre-commit hooks.
- AI development workflow.
- Documentation framework.

### Changed

- Migrated database driver from psycopg2-binary to psycopg (v3).
- Renamed logging.py to logger.py to avoid namespace collision.

### Fixed

- Database driver compatibility with SQLAlchemy 2.x.
- Python logging namespace conflict.

### Removed

- psycopg2-binary dependency.
