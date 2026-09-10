# Plan for Story AI-002 — Receive Matches Even When AI Confidence Is Low

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Epic:** ML7-EP02 | **Milestone:** ML7 | **Phase:** PH2 |
**Priority:** High | **Depends On:** AI-001 (done, Sprint 7)

---

## Story (verbatim, `Project_Tracker.xlsx`, `AI-002` row — obtained directly by the orchestrator this session)

"As a customer, I want my request handled well even if the AI isn't fully confident in its understanding, so
that I still get a next step instead of a dead end. This story implements the Wizard-of-Oz manual-match
fallback: sessions below a confidence threshold are routed to an admin queue rather than blocking the customer
or silently degrading to a low-quality automated match. Critically, the customer's downstream experience must
look identical whether their result came from the automated matcher or a human — the manual origin is never
surfaced to them. Scope boundary: does not include the admin-side queue UI itself (`ADM-001`) — this story
implements the routing/data model side and the customer-facing continuity guarantee."

## Acceptance Criteria (verbatim, 7 items)

1. Every completed `AI-001` session writes a confidence score tagged with the model/prompt version that
   produced it.
2. Sessions below the configured confidence threshold create a `manual_match_assignments` record and notify an
   admin — the session is never left in limbo with no next step.
3. The customer sees a message consistent with normal processing — never the words "manual," "fallback," or
   "admin" in customer-facing copy.
4. Once an admin resolves the manual assignment, the customer receives the same ranked-results screen as an
   automated match would produce.
5. The system never retries the LLM call in a loop hoping for a higher score — a low score is treated as a
   legitimate signal, not a failure to mask.
6. `search_event_log` records the session's outcome (matched or not) regardless of whether resolution was
   automated or manual.
7. Automated tests assert: below-threshold sessions always produce a `manual_match_assignments` row, and the
   customer-facing response contains no internal routing terminology.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **AC1 and AC5 are already satisfied by `AI-001`'s shipped code — no new backend work needed for either, only
  verification tests.** `backend/app/modules/conversation/models.py`'s `ConfidenceScore.model_version` is
  written on every turn (`conversation_service.py`'s `_advance_turn`) tagged `MODEL_VERSION = "rule_based_v1"`
  (ADR-034) — this satisfies AC1's "tagged with the model/prompt version" literally, for every session, not just
  completed ones. A repo-wide check of `conversation_service.py`/`conversation_ai_client.py` for any retry/loop
  construct (`retry|while True|for _ in range`) found **zero matches** — `_process_turn` is called exactly once
  per turn, confidence is accepted and acted on regardless of value (AC5 is satisfied by construction, not by a
  policy comment). This Plan does not touch either mechanism; the Verification Plan below cites the exact code
  proving both still hold after this story's changes land.
- **`ADR-032`'s own "Consequences" section (recorded at `AI-001`'s closeout) already assigns this story's scope**
  before this Plan was written: *"`AI-002` is now the confirmed owner of `search.search_requests` creation, real
  matching, and `administration.manual_match_assignments` — it reads `conversation_sessions.structured_criteria`
  as its input rather than re-deriving it from raw `messages`."* This Plan executes that already-recorded
  decision; it is not independently re-deriving the `AI-001`/`AI-002` split (settled, ADR-032).
- **`search` schema is completely unbuilt** — confirmed: `backend/app/modules/search/` has `api.py`,
  `schemas.py`, `services/search_service.py` only; no `models.py`, no `repositories/`. `SearchService` (DIR-001)
  is a **stateless** read-layer: `search_providers(category: str | None, latitude, longitude, radius_km, page,
  page_size)` runs a real, working, tested category + geospatial-radius + discoverability + nearest-first query
  via `ProviderService.search_nearby`, but persists nothing. This story is the first to add persisted state to
  `search`.
- **`administration.manual_match_assignments` is spec-only** (`04_DATABASE.md` lines 895–907): `assigned_admin_id
  UUID NOT NULL`, `status VARCHAR(20)` (`pending`/`completed`), `completed_at`. `ADR-030` (recorded during
  `CLM-001`, a different story) already examined this exact table and explicitly rejected reusing it for
  `claim_review_requests` **because** `assigned_admin_id NOT NULL` "doesn't fit 'an unassigned queue, any admin
  may pick up.'" That finding is directly this story's problem now, not a different story's — see Decision 2
  below.
- **`04_DATABASE.md`'s `search_requests` spec** (lines 663–675) has `structured_criteria JSONB NOT NULL` and
  `customer_latitude`/`customer_longitude DOUBLE PRECISION NOT NULL`. Two more schema-vs-reality mismatches,
  both confirmed genuine (not assumed) — see Decision 2.
- **`search_request_status` enum** (`matched`, `unmatched`, `pending_manual_match`) has no "submitted/pending"
  value — this is `ADR-032`'s own evidence that a `search_requests` row must be created with its **final** status
  already known, mirroring `ADR-029`'s "set the final status at creation, never patch an interim one" precedent.
  For the automated path this is trivial (matching runs synchronously, in-process, no job queue exists anywhere
  in this codebase); for the manual path, `pending_manual_match` **is** the enum's own "awaiting a human"
  state — exactly the value this story's low-confidence path needs and the only one of the three that isn't a
  final outcome.
- **No location-collection step exists anywhere in the AI Conversation flow.** `AI-001`'s `POST /conversations`/
  `POST /conversations/{id}/messages` never ask for or persist a customer location — confirmed against
  `conversation/schemas.py` and `conversation_service.py`. `04_DATABASE.md`'s `search_requests.customer_latitude/
  longitude NOT NULL` implicitly assumes a location is always available at request time — true for DIR-001's
  structured search (the caller supplies lat/lng as explicit query parameters), not true for this story's
  AI-conversation-triggered path. See Decision 2.
- **A real, working, precedented admin-review-queue pattern already exists three times in this codebase**
  (`admin_action_log`/VER-002, `claim_review_requests`/CLM-001, and the not-yet-built-but-designed
  `unmatched_query_reports`) — all "backend-API-only, no dashboard UI, admin **pulls** from a queue" (VER-002's
  original precedent, reaffirmed by `ADR-030` explicitly rejecting a push/"notify the admin team" mechanism
  since no such recipient concept exists anywhere in this codebase). This story's own scope boundary ("does not
  include the admin-side queue UI itself") means this precedent is exactly the right shape to reuse, not a new
  design question. `ClaimReviewRequestService` (`create`/`list_open`/`get_by_id`/`resolve`, four explicit
  methods, no generic CRUD) is the closest, most directly analogous precedent and is mirrored file-for-file by
  Decision 3 below.
- **`ClaimService`/`AdminClaimService` (CLM-001) both live in the `provider` module** (the domain the claim is
  *about*), each depending on `administration.ClaimReviewRequestService` (a narrow, passive row-manager) — never
  the reverse. `ClaimService._finalize_claim` is a single shared private helper both the customer-initiated OTP
  path and the admin-approved fallback path call, so "claimed" can never mean two different things
  (`ADR-030`). This is the exact shape this story needs for `provider_matches`/`search_requests.status`
  finalization (Decision 4) and is why `search` — not `administration` — owns the new
  `SearchRequestService` that orchestrates both the automated and the manual-resolution path.
- **Location for automated matching:** `customer.SavedAddressService.list_my_addresses(user_id) ->
  list[SavedAddress]` already exists (CUS-002) and is exactly the "customer's saved location(s)" read this story
  needs — `13_OPEN_DECISIONS.md` item 12 already documents `features/home`/`features/search` reusing the mobile
  equivalent (`SavedAddressRepository`) for the identical "pre-fill the search origin from the default address"
  purpose. No new `customer`-module method is needed; `search`'s new service takes `SavedAddressService` as a
  constructor dependency and filters for `is_default = true` itself.

---

## Architecture Decisions

### Decision 1 — Cross-module wiring: `conversation → search`, `search → administration`, `search → customer`; no cycle

**The problem:** satisfying AC2 (manual assignment + admin visibility), AC4 (real automated matching so a manual
resolution has something to look "the same" as), and AC6 (`search_event_log` regardless of origin) requires
three new pieces of persisted state (`search.search_requests`/`provider_matches`/`search_event_log`,
`administration.manual_match_assignments`) to be created and read from several different call sites without
introducing a circular module dependency.

**Chosen:** a single new outgoing edge from `conversation`, plus two outgoing edges from `search`, mirroring
already-proven shapes (ADR-014/016/030) rather than inventing a new mechanism:

- **`conversation → search`** (new): `ConversationService` gains one new constructor dependency,
  `search_request_service: SearchRequestService`. The **single** call site is inside `_apply_completion_policy`
  (`conversation_service.py`), immediately after a session transitions to `completed` **or** `routed_to_admin` —
  both branches call the same `await self.search_request_service.handle_session_completed(session, category=...)`
  method, which internally branches on `session.status`. `search` has zero imports from `conversation` — it
  receives plain primitives (`session.id`, `session.customer_id`, `category_id`, `category_name: str`,
  `structured_criteria: dict | None`, `language`), never a `ConversationSession` ORM object, so `search` cannot
  and does not depend on `conversation`'s models.
- **`search → administration`** (new): `SearchRequestService` depends on
  `administration.ManualMatchAssignmentService` (Decision 3) to create a `manual_match_assignments` row when
  routing, and to resolve it when an admin acts. `administration` has zero imports from `search` — it only ever
  receives `search_request_id: uuid.UUID` as a plain value.
- **`search → customer`** (new): `SearchRequestService` depends on `customer.SavedAddressService` (already
  shipped, CUS-002) to resolve the customer's default saved address for the automated-matching path. `customer`
  has zero imports from `search`.
- **`search → provider`** (already exists, DIR-001, reused unchanged): `SearchRequestService` depends on the
  existing `SearchService` (which already depends on `ProviderService`) to run the actual matching query — see
  Decision 5.

**Confirmed cycle-free:** `search`, `administration`, and `customer` each have zero imports of `conversation`,
of each other in the reverse direction, or of `conversation`'s models — every edge above is one-directional,
identical in kind to every cross-module edge this codebase has shipped since ADR-014.

**Alternatives considered and rejected:**
- **`conversation → administration` directly** (bypassing `search` for the manual-assignment creation) —
  rejected: this would split "who creates a `manual_match_assignments` row" (conversation) from "who finalizes
  its resolution into `provider_matches`/`search_requests.status`" (would-be `administration → search`), which
  creates the exact cycle risk (`conversation → administration → search → conversation`, or `search →
  administration → search`) this Decision avoids by keeping `search` as the single owner of both creating and
  resolving the assignment, exactly mirroring `provider` owning both `ClaimService` and `AdminClaimService`
  around `administration.ClaimReviewRequestService`.
- **A domain-event bus** — rejected for the same reason ADR-014/016 already rejected it: no event-bus
  infrastructure exists anywhere in this codebase; building one for these call sites would be premature
  abstraction `08_CODING_STANDARDS.md` warns against.

### Decision 2 — Three flagged, necessary nullable-column deviations from `04_DATABASE.md`'s current literal spec

Each of these was confirmed as a genuine mismatch during planning (not assumed), and each is resolved the same
way this codebase has resolved every prior instance of "the locked spec doesn't fit what the real code path can
honestly provide": make the column nullable and report the honest absence, never fabricate a value. All three
are flagged here for a `04_DATABASE.md` update and new ADRs at closeout, per this project's standing convention
(mirrors exactly how `AI-001`'s Decision 1b/5 flagged its own additive column/enum value).

**2a. `administration.manual_match_assignments.assigned_admin_id` → nullable.** `ADR-030` already found, in a
different story's context, that `NOT NULL` here "doesn't fit 'an unassigned queue, any admin may pick up.'" This
story is the one that actually builds this table, so this is the point the fix must land. **Resolution:** the
column is populated **only at resolution** (the admin who resolved it), `NULL` while `status = pending` — the
row is created with `assigned_admin_id = NULL`, mirroring `claim_review_requests.reviewed_by`'s exact
nullable-until-resolved shape.

**2b. `search.search_requests.structured_criteria` → nullable.** A `routed_to_admin` session
(`AI-001`'s Decision 1b/ADR-033) **always** leaves `conversation_sessions.structured_criteria = NULL` — there is
no complete, validated answer set to build it from. A `search_requests` row created for such a session therefore
structurally cannot inherit a non-null payload; the admin resolving it works from the raw transcript context
instead (out of this story's scope to expose richly — see "Explicitly Out of Scope"). Making the column
`NOT NULL` would force this story to fabricate a payload that was never validated, directly contradicting the
platform's anti-fabrication principle (`00_PROJECT_CONTEXT.md` §3) this codebase has upheld consistently since
`AI-001`'s own AC5/Decision 2b.

**2c. `search.search_requests.customer_latitude`/`customer_longitude` → nullable.** No location-collection step
exists anywhere in the AI Conversation flow (verified above), and this story does not add one — the mobile
change required to add a location-capture turn to `AI-001`'s already-shipped chat flow is a materially larger
change than this story's own scope ("routing/data model side and the customer-facing continuity guarantee") and
was never asked for. **Resolution:** `SearchRequestService` resolves the customer's **default** saved address
(Decision 1's `search → customer` edge); if one exists, matching runs with real coordinates exactly as DIR-001's
structured search already does. **If no default address exists, the row is still created** (never blocked, per
AC2's "never left in limbo") with `customer_latitude/longitude = NULL` and `status = unmatched` — an honest "we
could not geolocate this request" outcome, not a guessed `(0, 0)` or the request's own capital-city centroid.
This is deliberately **independent of AC2's confidence-based routing**: a high-confidence session with no
saved address still completes automatically (as `unmatched`, zero results) rather than being silently rerouted
to the manual queue for an unrelated reason — conflating "AI wasn't confident" with "customer has no saved
address" would blur AC5's "a low score is a legitimate, distinct signal" into a second, undocumented trigger for
the same fallback path.

**Alternatives considered and rejected (all three):**
- **Leave the columns `NOT NULL` and block/error when data is missing** — rejected: directly violates AC2's "the
  session is never left in limbo with no next step" for 2a/2b, and would make a customer with no saved address
  unable to ever complete an AI-conversation search, an unrequested new hard requirement on the whole AI intake
  feature.
- **Fabricate a value (e.g. an "unassigned" sentinel UUID, an empty structured-criteria object, a country
  centroid lat/lng)** — rejected outright: this is precisely the "silently degrading to a low-quality automated
  match" / fabrication pattern both the story's own text and `00_PROJECT_CONTEXT.md` §3 prohibit.
- **Require a saved default address before allowing AI intake at all** — rejected as unrequested product/UX
  scope; flagged instead as an open question for the CTO (see Open Questions) rather than assumed.

### Decision 3 — `administration.ManualMatchAssignmentService`: a fourth application of the passive-queue-row pattern, mirroring `ClaimReviewRequestService` file-for-file

`backend/app/modules/administration/models.py` gains `ManualMatchAssignment` (full `CommonColumnsMixin`, matching
`AdminActionLog`/`ClaimReviewRequest`'s precedent — `04_DATABASE.md`'s Soft Delete section exempts only
`audit_logs`/`search_event_log`). `ManualMatchAssignmentRepository` + `ManualMatchAssignmentService` expose
exactly `create(conversation_session_id, search_request_id)`, `list_pending(page, page_size)`, `get_by_id(id)`,
`resolve(id, *, admin_user_id, provider_ids: list[uuid.UUID])` — four explicit methods, no generic CRUD,
identical shape to `ClaimReviewRequestService`. `resolve` sets `status = completed`, `assigned_admin_id =
admin_user_id`, `completed_at = now()`; it does **not** itself touch `provider_matches`/`search_requests` — that
is `search.SearchRequestService`'s job (Decision 1), called by the admin-facing route handler around this
service, exactly mirroring how `AdminClaimService` orchestrates `ClaimReviewRequestService.resolve` and
`ClaimService._finalize_claim` as two separate calls around one admin action.

**"Notify an admin" (AC2) = a pull-based queue, not a push notification.** `ADR-030` already examined and
rejected "notify an admin" as a push/broadcast mechanism, for a directly transferable reason: no "the admin
team" recipient concept exists anywhere in this codebase (every `notification.notifications` row targets one
specific `user_id`), and no flow proactively pushes work to an admin today. `GET /admin/search/manual-matches`
(new, `require_role(ROLE_ADMIN)`, ADR-023's ownerless shape, backend-API-only per this story's own explicit
exclusion of the ADM-001 dashboard UI) is this story's queue — an admin (or a future ADM-001 dashboard) polls it.
This is not a weaker reading of AC2's "notify" than the alternative — it is the only mechanism this codebase has
ever built for "admin becomes aware of new work," reused for a fourth time rather than invented anew.

### Decision 4 — `search.SearchRequestService`: one shared `_finalize_matches` helper for both the automated and the manual-resolution path

**The problem (AC4, AC6):** the customer's ranked-results screen, and the `search_event_log` write recording the
outcome, must be **identical in shape and mechanism** regardless of whether a `search_requests` row was resolved
automatically or by an admin — otherwise "the same ranked-results screen" (AC4) and "regardless of... automated
or manual" (AC6) would be two different code paths that could silently drift, exactly the risk `ADR-030`'s
`_finalize_claim` helper was built to prevent for claims.

**Chosen:** a single private method, `SearchRequestService._finalize_matches(search_request, provider_ids:
list[uuid.UUID])`, is the **only** place in the codebase that ever writes `provider_matches` rows, sets
`search_requests.status` to its final `matched`/`unmatched` value, and writes the corresponding
`search_event_log` row (`was_matched = bool(provider_ids)`, `result_count = len(provider_ids)`). Both call sites
below are thin wrappers around it:
- **Automated path** — `handle_session_completed(session, ...)`, when `status == completed`: resolves the
  customer's default address (Decision 2c), calls the existing `SearchService`'s underlying matching query
  (Decision 5) to get an ordered list of provider ids, then calls `_finalize_matches` **synchronously, in the
  same call** that creates the `search_requests` row — the row is created with its final status already known
  (Decision-1's evidence, mirroring ADR-029), never a "pending" placeholder.
- **Manual path** — `resolve_manual_match(assignment_id, *, admin_user_id, provider_ids)`: fetches the
  assignment via `ManualMatchAssignmentService.get_by_id`, calls `_finalize_matches` on its `search_request_id`
  with the admin-supplied ordered `provider_ids` (an **empty list is valid** — "no viable match found," resolves
  to `unmatched`, not an error), then calls `ManualMatchAssignmentService.resolve(...)` to close out the
  assignment. `rank` in `provider_matches` is simply the 1-based position in the admin's supplied list — the
  admin's own ordering **is** the rank, not re-derived.

`match_score` is left `NULL` for every row this story writes, both paths — see Decision 5 (no real merit-ranking
algorithm exists yet; leaving it `NULL` is honest, not a placeholder `0`/`1.0`).

**Alternatives considered and rejected:**
- **Two separate finalization code paths (one for automated, one for admin-resolved)** — rejected: this is
  exactly the drift risk `ADR-030` already identified and fixed once for claims; no reason to reintroduce the
  same risk here when the shared-helper shape is already this codebase's proven answer.
- **Have `AdminManualMatchService` write `provider_matches` directly** — rejected: would require
  `administration → search`'s repository (not just its service), violating `02_ARCHITECTURE.md`'s "Module →
  Another Module's Repository" prohibition, and would duplicate `_finalize_matches`'s logic.

### Decision 5 — Matching mechanism: reuse `search.SearchService`/`provider.ProviderService.search_nearby` (DIR-001) unchanged; no new ranking algorithm

**The problem:** AC4 requires a real "automated match" to exist for the manual path's output to be compared
against, but no persisted matching mechanism exists yet in `search` (only the stateless DIR-001 query). Building
a **new** merit-ranking algorithm (Flow 4 step 6's literal text: "rank by merit — rating + review volume +
proximity") is not realistic yet: the Review domain (`REV-001`) has not shipped, so `provider.
provider_rating_summaries` is empty/all-zero placeholder data for every provider today — computing a
"merit-weighted rank" against all-zero inputs would produce fake precision, not a real signal.

**Chosen:** `SearchRequestService` takes the already-shipped `SearchService` as a constructor dependency and
calls its existing `search_providers`-equivalent matching query (category + geospatial radius + discoverability,
nearest-first) with: `category` = the resolved `Category.name` (a plain string, matched against
`provider_category_labels` per `ADR-027`'s already-established exact-match posture — this inherits, does not
worsen, `13_OPEN_DECISIONS.md` item 1's already-tracked `provider_category_labels` reconciliation gap), `radius_km
= settings.SEARCH_DEFAULT_RADIUS_KM` (no radius-selection UI exists in the AI Conversation flow, unlike DIR-001's
explicit filter), capped at a new `settings.AI_MATCH_MAX_RESULTS: int = 10` (bounding how many candidates become
`provider_matches` rows — an unbounded write here would be a real, if unlikely, resource concern with no product
value). Ranking = the query's existing nearest-first order (`rank` = 1-based position) — identical to what
DIR-001's structured browse already shows a customer today, not a new algorithm this story invents and cannot
validate.

**Alternatives considered and rejected:**
- **Build a merit-ranking formula now (rating × review-count × inverse-distance)** — rejected: no real rating
  data exists yet to rank by (Review domain unshipped); this would be exactly the "silently degrading to a
  low-quality automated match" pattern the story's own text warns against, just dressed up as a formula instead
  of an admission.
- **Write a brand-new geospatial query independent of `SearchService`** — rejected: `SearchService`'s query is
  already real, tested, and identical in kind to what this story needs; duplicating it violates `08_CODING_
  STANDARDS.md`'s "reuse existing modules" rule for no benefit.

### Decision 6 — `ConversationSessionResponse` gains `search_request_id`, never a confidence value; mobile completion state becomes real

`AI-001`'s `ConversationSessionResponse` (Decision 7, `Plan_S07_AI-001.md`) has no way to point the mobile client
at a results screen, because no `search_requests` row existed at the time it shipped. This story adds exactly one
field, `search_request_id: uuid.UUID | None` (populated once `status` reaches `completed`/`routed_to_admin`,
`NULL` while `active`/`abandoned`) — **no confidence/score field is added**, preserving AC6 of `AI-001` and this
story's own AC3 (Decision 7 below) unchanged. Mobile's `ai_conversation_screen.dart` completion state, previously
an honest static "we're finding matches for you" message with no results mechanism to link to (`AI-001` Decision
1), now navigates to a ranked-results view keyed on this id — see Decision 7.

**A new customer-facing endpoint**, `GET /search-requests/{search_request_id}` (`search` module,
`ensure_owner_or_not_found` against `search_requests.customer_id`, ADR-015's `{id}`-addressable-collection
shape — a customer accumulates many search requests over time, a genuine 1:N collection, not a `/me` singleton),
returns `SearchRequestResultResponse { status, matched_providers: list[MatchedProviderResponse] }`.
`MatchedProviderResponse.distance_meters` is **nullable** (unlike DIR-001's `SearchResultProviderResponse`,
which assumes a location always exists) — `NULL` only for the rare case a manually-resolved request's customer
had no default address (Decision 2c); never estimated. This is a **new** response schema, not a reuse of
DIR-001's `SearchResultProviderResponse`, precisely because of this one honest divergence.

### Decision 7 — Customer-facing copy (AC3): forbidden-word test, not a style guideline

**The problem:** AC3/AC7 are explicit that "manual," "fallback," and "admin" must never appear in any
customer-facing string, and that this must be an automated test, not a review checklist item (mirroring `AI-001`'s
own AC10 grounding-test precedent: prove the structural guarantee, don't just instruct it in a prompt/comment).

**Chosen:** a new backend test, `test_no_forbidden_customer_copy.py`, asserts none of `{"manual", "fallback",
"admin"}` (case-insensitive) appears in: every hardcoded string literal in `conversation/schemas.py`,
`search/schemas.py`, and any hardcoded reply text `RuleBasedConversationAiClient`/`ConversationService` can
produce — plus every string constant defined in the mobile `ai_conversation_screen.dart`/the new ranked-results
view. **Existing copy is already compliant** — `AI-001`'s shipped "Thanks — we're finding matches for you" and
`16_UX_GUIDELINES.md`'s locked "This is taking a moment — we'll notify you as soon as we have matches" both
already avoid all three words; this story adds no new customer-facing string that needs to introduce them
either. The `pending_manual_match`/`manual_match_assignments` *identifiers* themselves are backend-internal
(enum values, table/column names, response field names never exposed as user-facing text) — the test targets
rendered/returned **copy**, not internal identifiers, exactly as AC3's own wording ("in customer-facing copy")
specifies.

**Alternatives considered and rejected:**
- **A manual copy-review checklist only** — rejected: AC7 explicitly requires this be an automated test; a
  checklist can silently regress on the next unrelated change to either file.

---

## Backend — Proposed Changes

### Migration
1. One new, reversible Alembic migration (down-revision = `ef7b7d439f40`, the current head). Creates the
   `search` Postgres schema; the `search_request_status` enum (`matched`, `unmatched`, `pending_manual_match`,
   per `04_DATABASE.md` line 190, unchanged); `search_requests` (with `structured_criteria` and
   `customer_latitude`/`customer_longitude` **nullable** — Decision 2b/2c, flagged deviations),
   `provider_matches`, `search_event_log` — column-for-column otherwise per `04_DATABASE.md` lines 663–705. In
   the same migration, adds `administration.manual_match_assignments` (with `assigned_admin_id` **nullable** —
   Decision 2a) to the existing `administration` schema. No changes to any existing table.

### `search` module (new persisted state)
2. `models.py` — `SearchRequestStatus` enum; `SearchRequest`, `ProviderMatch`, `SearchEventLog` ORM models
   (Decision 2's nullable columns applied).
3. `repositories/search_request_repository.py` — `create`, `get_by_id`, `update_status`.
4. `repositories/provider_match_repository.py` — `bulk_create(search_request_id, ranked_provider_ids)`.
5. `repositories/search_event_log_repository.py` — `create`.
6. `services/search_request_service.py` — `SearchRequestService`: `handle_session_completed(session_id,
   customer_id, status, category_id, category_name, structured_criteria, language) -> SearchRequest` (Decision
   1/4); private `_run_automated_match(...)`, `_finalize_matches(search_request, provider_ids)` (Decision 4);
   `list_pending_manual_matches(page, page_size)`; `resolve_manual_match(assignment_id, *, admin_user_id,
   provider_ids)` (Decision 4). Depends on `SearchService` (existing, Decision 5), `SavedAddressService`
   (`customer`, Decision 2c), `ManualMatchAssignmentService` (`administration`, Decision 3).
7. `schemas.py` — add `MatchedProviderResponse` (nullable `distance_meters`, Decision 6),
   `SearchRequestResultResponse`, `ManualMatchAssignmentSummaryResponse` (admin queue list item), `
   ResolveManualMatchRequest { provider_ids: list[uuid.UUID] }` (empty list valid).
8. `api.py` — add `GET /search-requests/{search_request_id}` (customer, `ensure_owner_or_not_found`, Decision
   6); `GET /admin/search/manual-matches` (admin queue list, Decision 3); `POST
   /admin/search/manual-matches/{assignment_id}/resolve` (admin resolve, Decision 4) — both admin routes
   `require_role(ROLE_ADMIN)`, ownerless shape per ADR-023, mounted alongside the existing `/search` routes in
   this same module (mirrors `provider/api.py` hosting `/admin/claims` alongside its own customer-facing routes).
9. `dependencies.py` — add repository/service DI providers, including `get_search_request_service` which wires
   in `get_saved_address_service` (`customer`) and `get_manual_match_assignment_service` (`administration`).
10. Exceptions: `SearchRequestNotFoundError` (404).
11. Config (`backend/app/core/config.py`): `AI_MATCH_MAX_RESULTS: int = 10` (Decision 5).

### `administration` module
12. `models.py` — add `ManualMatchAssignment` (Decision 3, nullable `assigned_admin_id`).
13. `repositories/manual_match_assignment_repository.py` (new) — `create`, `list_pending`, `get_by_id`, `update`.
14. `services/manual_match_assignment_service.py` (new) — `create`, `list_pending`, `get_by_id`, `resolve`
    (Decision 3, mirrors `ClaimReviewRequestService`).
15. `dependencies.py` — add DI wiring.
16. Exceptions: `ManualMatchAssignmentNotFoundError` (404).

### `conversation` module (small extension)
17. `services/conversation_service.py` — constructor gains `search_request_service: SearchRequestService`;
    `_apply_completion_policy` calls `await self.search_request_service.handle_session_completed(...)` on both
    the `completed` and `routed_to_admin` branches (Decision 1), same flush, same transaction, no new commit.
18. `schemas.py` — `ConversationSessionResponse` gains `search_request_id: uuid.UUID | None` (Decision 6). No
    confidence field added — AC6 of `AI-001` remains intact.
19. `dependencies.py` — wire `get_search_request_service` into `get_conversation_service`.

### Tests
20. `backend/tests/modules/search/test_search_request_service.py` — automated path: a `completed` session with a
    default address produces `matched`/`unmatched` correctly, `provider_matches` ranked, `search_event_log`
    written once; no default address → `customer_latitude/longitude NULL`, `status = unmatched`, still writes
    `search_event_log`, never blocks (AC2's "never left in limbo" extended honestly here too, Decision 2c).
    Manual path: `routed_to_admin` always produces exactly one `manual_match_assignments` row with
    `assigned_admin_id = NULL` at creation (AC2/AC7); `resolve_manual_match` with a non-empty `provider_ids`
    list produces `matched` + ranked `provider_matches` identical in shape to the automated path (AC4); with an
    empty list produces `unmatched`; both write exactly one `search_event_log` row at resolution time, never at
    routing time (AC6).
21. `backend/tests/modules/search/test_search_request_api.py` — `GET /search-requests/{id}`
    `ensure_owner_or_not_found` (404, never 403, for another customer's request); admin routes reject
    non-admin callers; `POST .../resolve` on an already-resolved assignment is rejected (409) rather than
    silently double-finalizing.
22. `backend/tests/modules/administration/test_manual_match_assignment_service.py` — `create`/`list_pending`/
    `resolve` mirrored against `ClaimReviewRequestService`'s existing test shape.
23. `backend/tests/modules/conversation/test_conversation_service.py` (extended) — a session reaching
    `completed` or `routed_to_admin` always has a non-`None` `search_request_id` afterward (AC2's "never left in
    limbo," now provable end-to-end from the conversation side); confirms no change to `AI-001`'s existing
    passing tests (AC1/AC5/AC6/AC8/AC9/AC10/AC11 all re-verified unchanged).
24. `backend/tests/test_no_forbidden_customer_copy.py` (new, Decision 7) — scans the named source files for
    `{"manual", "fallback", "admin"}` (case-insensitive) in string literals; a live HTTP round-trip test also
    asserts a `routed_to_admin` session's full JSON response (message content, `ConversationSessionResponse`,
    `SearchRequestResultResponse` while `pending_manual_match`) contains none of the three words (AC3/AC7).

---

## Mobile — Proposed Changes

### Shared extraction (avoids worsening `13_OPEN_DECISIONS.md` item 12's already-logged debt)
25. `mobile/lib/shared/widgets/ranked_provider_results_list.dart` (new) — the provider-card list rendering
    currently owned by `features/search/presentation/screens/search_results_screen.dart` (S-08), extracted so
    both `features/search` and `features/conversation` depend on the same shared widget rather than one feature
    importing the other's screen directly (the exact shape of problem item 12 already flags for
    `features/customer`; this story must not add a third instance of it). If full extraction proves more
    invasive than this story's scope warrants, `frontend` must explicitly flag the resulting direct import as new,
    documented debt (mirroring item 12's own format) rather than adding it silently.

### `features/conversation` (extends `AI-001`'s existing feature)
26. `data/conversation_repository.dart` — add `getSearchRequestResults(searchRequestId)` (`GET
    /search-requests/{id}`).
27. `presentation/screens/ai_conversation_screen.dart` — the completion state (previously a static message only,
    `AI-001` Decision 1) now reads `session.searchRequestId` and renders the shared ranked-results widget once
    `status` is `matched`/`unmatched`; while `pending_manual_match`, keeps showing the **same** honest waiting
    copy `AI-001` already ships (never new copy that could reintroduce a forbidden word), with light polling
    (a short interval, screen-lifecycle-aware — paused when the app is backgrounded) since no push-notification
    delivery channel exists yet (consistent with the Notification domain's own already-documented interim state,
    `04_DATABASE.md` Notification Domain section).
28. `state/conversation_controller.dart` — owns the poll timer for the `pending_manual_match` state, cancelled on
    dispose/navigation-away.

### Tests
29. `mobile/test/features/conversation/` — extend `ai_conversation_screen_test.dart`: a `matched`/`unmatched`
    `search_request_id` renders the shared ranked-results widget; a `pending_manual_match` state polls and then
    transitions once the fake repository reports a resolved status; no widget in the tree ever renders the words
    "manual," "fallback," or "admin" (AC3/AC7, mirrored from the backend test).
30. `fakes/fake_conversation_repository.dart` — extend to support `getSearchRequestResults` with configurable
    pending/matched/unmatched responses.

---

## Explicitly Out of Scope (do not implement in this story)

- **The `ADM-001` admin-side queue dashboard UI** — the story's own literal scope boundary. `GET
  /admin/search/manual-matches`/`POST .../resolve` are backend-API-only, exactly like `/admin/claims` (CLM-001)
  and `/admin/verification/records` (VER-002) before them.
- **Any admin-facing endpoint that reads/renders a session's full `messages` transcript.** Flow 7 step 1 ("Admin
  opens the assignment, reviews the Conversation Session transcript") is real admin **UX**, which is squarely
  `ADM-001`'s job to design and build — none of this story's 7 verbatim ACs require it, and adding it now would
  require either a new `administration → conversation` edge (a genuine cycle risk against Decision 1's
  `conversation → search → administration` chain) or building a bypass into `AI-001`'s existing
  `ensure_owner_or_not_found`-scoped `GET /conversations/{id}` — both are real design decisions `ADM-001` should
  make deliberately, not something this story should improvise around. The admin queue response does still
  include the raw `conversation_session_id`, so nothing is lost — a future story has everything it needs to add
  this.
- **A merit-based ranking algorithm** (rating + review volume + proximity, Flow 4 step 6's literal text) —
  Decision 5; the Review domain hasn't shipped, so there is no real signal to rank by yet. Nearest-first (already
  shipped by DIR-001) is reused unchanged.
- **A location-collection step added to the AI Conversation flow itself** — Decision 2c; the default-saved-
  address reuse, with an honest `unmatched`/null-location fallback, covers this story's ACs without touching
  `AI-001`'s already-shipped chat UX.
- **A real push-notification delivery channel** for "your matches are ready" — the Notification domain's
  existing, already-documented interim posture (no real WhatsApp/SMS/Email channel yet) is unchanged by this
  story; polling covers the customer-continuity requirement (AC4) without a new dependency.
- **Reconciling `provider.provider_category_labels` into the real `category.provider_categories` join table**
  (`13_OPEN_DECISIONS.md` item 1's still-open remainder) — this story's category-matching (Decision 5) inherits
  the existing free-text posture unchanged; it does not worsen or attempt to fix this separately-tracked gap.

---

## Open Questions (flagged for CTO awareness — do not block `backend` from starting, per this codebase's
established practice of proceeding on a well-precedented interim design while flagging it plainly)

1. **The three nullable-column deviations (Decision 2a/2b/2c)** — each is directly precedented (2a by `ADR-030`'s
   own prior finding; 2b/2c by the platform's standing anti-fabrication principle already applied identically in
   `AI-001`), but all three deviate from `04_DATABASE.md`'s current literal text and should be ratified as ADRs
   at closeout, not silently left as an implementation detail.
2. **Should the app eventually require a customer to have a saved default address before offering AI intake at
   all?** This story does not answer that product question — it degrades honestly (an `unmatched` result,
   Decision 2c) rather than blocking or guessing. If the CTO later decides a location should be mandatory
   up-front, that is a follow-up story touching `AI-001`'s chat flow, not a change to this story's design.
3. **Admin transcript visibility** (Flow 7 step 1) is deliberately not built here (see "Explicitly Out of
   Scope") — confirm this is acceptable to defer fully to `ADM-001` rather than a smaller interim read-only
   endpoint being added now.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

1. **backend** — Items 1–24. Build order: (a) migration first (both `search` schema and the
   `manual_match_assignments` addition to `administration`, including all three Decision-2 nullable deviations);
   (b) `administration.ManualMatchAssignment`/`ManualMatchAssignmentService` (Decision 3, small, mirrors
   `ClaimReviewRequestService` closely — build this before `search` since `search` depends on it); (c) `search`
   module models/repositories, then `SearchRequestService` (Decision 4/5) — pay particular attention to
   `_finalize_matches` being the **only** place `provider_matches`/`search_requests.status`/`search_event_log`
   are written, called from both paths, never duplicated; (d) `search/api.py`/`schemas.py`/`dependencies.py`;
   (e) the small `conversation` extension (Decision 1/6) last, wiring `search_request_service` into
   `ConversationService` and adding `search_request_id` to the response schema — re-run `AI-001`'s existing
   conversation test suite to confirm nothing regresses. Read Decision 1 in full before starting — the
   temptation to have `administration` read `conversation` directly (for transcript context) is exactly the
   cycle risk this Plan deliberately avoids; if that need comes up during implementation, stop and flag it
   rather than adding the edge.
2. **frontend** — Mobile items 25–30, once the backend endpoints exist (or in parallel against a fake
   repository). Particular attention to Decision 7's forbidden-word discipline (no new customer-facing string
   may introduce "manual"/"fallback"/"admin") and to the shared-widget extraction (Item 25) — if extraction is
   skipped, it must be explicitly flagged as new debt, not silently duplicated.
3. **tester** — Verify all 7 verbatim ACs (mapping below). Particular attention to AC2 ("never left in limbo" —
   including the no-default-address edge case, which is a real code path this story adds, not just the
   confidence-threshold case), AC4 (the automated and manually-resolved paths produce byte-for-byte the same
   response shape from `GET /search-requests/{id}`), AC6 (`search_event_log` written exactly once per
   `search_requests`, regardless of origin — not twice, not zero times), and AC7 (the forbidden-word tests
   actually exercise a live `routed_to_admin`/`pending_manual_match` HTTP response, not just static string
   literals). Also re-verify AC1/AC5 remain true post-change (no regression to `AI-001`'s existing guarantees).
4. **architect** — Review Decision 1's cross-module edges for genuine cycle-freedom (this is the review's
   highest-value focus — a subtle cycle here would be easy to introduce in a follow-up fix without careful
   checking); Decision 2's three nullable deviations against `04_DATABASE.md`'s intent and this platform's
   anti-fabrication principle; Decision 4's shared `_finalize_matches` helper for genuine single-ownership (no
   second code path that could write `provider_matches` some other way); Decision 5's reuse of `SearchService`
   for correctness and for not silently duplicating DIR-001's query logic; Decision 3's mirroring of
   `ClaimReviewRequestService` for consistency.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decision 1 (cross-module wiring), Decision 2 (the three nullable-column deviations), Decision 3
     (`ManualMatchAssignmentService`, the fourth passive-queue-row application), Decision 4 (shared
     `_finalize_matches`), and Decision 5 (matching-mechanism reuse) as new ADRs (next available: **ADR-037**
     onward).
   - Update `04_DATABASE.md` (mark `search`'s persisted tables and `manual_match_assignments` as shipped; record
     all three nullable deviations plainly, the same way `AI-001`'s additive column/enum were recorded).
   - Update `13_OPEN_DECISIONS.md` item 10 (degree of Wizard-of-Oz matching) — this story is the first concrete
     implementation of it; update its status/notes accordingly, without resolving the still-open product
     question of exactly how much matching stays manual long-term.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 7 section.

---

## Verification Plan (mapped to the 7 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Already satisfied by `AI-001`'s shipped code (`ConfidenceScore.model_version = "rule_based_v1"`, written every turn) — re-verified unchanged by this story's existing/extended `conversation` tests (item 23). |
| 2 | `test_search_request_service.py`: every `routed_to_admin` transition produces exactly one `manual_match_assignments` row (`assigned_admin_id = NULL`, `status = pending`) and a `search_requests` row (`status = pending_manual_match`) in the same operation — including the no-default-address edge case, which still produces a resolvable outcome, never a blocked/limbo state. `GET /admin/search/manual-matches` makes the row visible to an admin caller (the "notify" mechanism, Decision 3). |
| 3 | `test_no_forbidden_customer_copy.py` (backend) + `ai_conversation_screen_test.dart` (mobile) — a live `routed_to_admin`/`pending_manual_match` response and its rendered widget tree contain none of "manual"/"fallback"/"admin". |
| 4 | `test_search_request_service.py` + `test_search_request_api.py`: `GET /search-requests/{id}` returns byte-for-byte the same `SearchRequestResultResponse` shape whether the request was finalized via the automated path or `resolve_manual_match` (Decision 4's shared `_finalize_matches`). |
| 5 | Already satisfied by construction in `AI-001`'s shipped `ConversationService`/`RuleBasedConversationAiClient` (zero retry/loop constructs, confirmed by direct code search) — unchanged by this story; re-verified via existing `conversation` tests. |
| 6 | `test_search_request_service.py`: exactly one `search_event_log` row per `search_requests` row, written at the point the final outcome becomes known (immediately for automated, at `resolve_manual_match` for manual) — never zero, never duplicated. |
| 7 | `test_search_request_service.py` (the below-threshold-always-produces-a-row assertion, item 20) + `test_no_forbidden_customer_copy.py` (the terminology assertion, item 24) — both automated, per AC7's own explicit requirement that this be tested, not just documented. |

---

## Related Documents

- `docs/AI/00_PROJECT_CONTEXT.md` §3 (anti-fabrication hard constraint, the basis for Decision 2's nullable
  columns rather than fabricated values)
- `docs/AI/03_DOMAIN_MODEL.md` (Administration domain — Manual Match Assignment; Search domain)
- `docs/AI/04_DATABASE.md` (`search_requests`/`provider_matches`/`search_event_log`, lines 663–705;
  `manual_match_assignments`, lines 895–907; `search_request_status` enum, line 190; Conversation domain's
  `structured_criteria`, lines 610–618)
- `docs/AI/09_DECISIONS.md` (ADR-014/016 — cross-module injection precedent, Decision 1; ADR-023 — ownerless
  `require_role(ROLE_ADMIN)` shape, Decision 3; ADR-027 — free-text category-label exact-match posture, Decision
  5; ADR-029 — "set the final status at creation" precedent, Decision 4; ADR-030 — the `claim_review_requests`/
  `_finalize_claim` precedent this Plan mirrors throughout, and its own prior finding about
  `manual_match_assignments.assigned_admin_id`; ADR-032/033/034/035/036 — `AI-001`'s decisions this story builds
  directly on top of)
- `docs/AI/12_TECH_STACK.md` (no LLM vendor named — unrelated to this story, unaffected)
- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy, the `provider_category_labels` gap this story
  inherits unchanged; item 10 — degree of Wizard-of-Oz matching, this story's first concrete implementation,
  updated at closeout; item 12 — the `features/search`/`features/customer` direct-import debt Decision on mobile
  item 25 must not worsen; item 13 — real LLM vendor selection, unrelated to this story)
- `docs/AI/14_USER_FLOWS.md` Flow 4 (steps 5–8, this story's scope), Flow 7 (Wizard-of-Oz Manual Match, Admin
  Side — this story's data-model/routing half; the admin UX half is `ADM-001`), Flow 8 (Notification Triggers —
  "Manual match assignment created | Admin," satisfied via the pull-queue mechanism, Decision 3)
- `docs/AI/15_SCREEN_INVENTORY.md` (`S-07`, `S-08` — the shared ranked-results widget, Decision 6/mobile item 25)
- `docs/AI/16_UX_GUIDELINES.md` (Wizard-of-Oz invisibility rule; the ">8s/timeout" and "we'll notify you" copy
  this story's mobile polling state reuses verbatim, never introducing new customer-facing wording)
- `docs/implementation/plans/Plan_S07_AI-001.md` / `Walkthrough_S07_AI-001.md` (the `conversation` schema and
  `ConversationService` this story extends; Decision 1/1b's scope boundary this story is the confirmed other
  half of)
- `docs/implementation/plans/Plan_S06_CLM-001.md` / `Walkthrough_S06_CLM-001.md` (the `_finalize_claim`/
  `ClaimReviewRequestService` precedent Decisions 3/4 mirror throughout)
- `docs/implementation/plans/Plan_S06_DIR-001.md` (the `SearchService`/`ProviderService.search_nearby` matching
  logic Decision 5 reuses unchanged)

---

**End of Document**
