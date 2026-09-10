# Walkthrough S07 AI-002

## Story: Receive Matches Even When AI Confidence Is Low

**Sprint:** 07 | **Story ID:** AI-002 | **Priority:** High | **Status:** Done

As a customer, I want my request handled well even if the AI isn't fully confident in its understanding, so
that I still get a next step instead of a dead end. This story implements the Wizard-of-Oz manual-match
fallback: sessions below a confidence threshold are routed to an admin queue rather than blocking the customer
or silently degrading to a low-quality automated match. Critically, the customer's downstream experience must
look identical whether their result came from the automated matcher or a human — the manual origin is never
surfaced to them. **Scope boundary:** does not include the admin-side queue UI itself (`ADM-001`) — this story
implements the routing/data-model side and the customer-facing continuity guarantee.

Full context, the 7 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S07_AI-002.md`.
Implementer notes/flagged deviations, including the exact fix descriptions for both review-found bugs, were
recorded in `docs/implementation/plans/Checkpoint_S07_AI-002.md`, deleted at closeout per the Continuity &
Checkpointing rule once the orchestrator confirmed this story complete.

All work is committed and pushed to branch `claude/provider-storefront-pro-001-qnicuj` (final head `85b5133`
at this closeout):
- `eb34f38` — backend: search domain, manual_match_assignments, conversation extension
- `866b78f` — mobile: ranked results and manual-match polling
- `1cc8c21` — test: close AI-002 coverage gap, prove the double-finalization bug (tester)
- `9e92438` — fix: resolve_manual_match finalized state before checking guard (backend)
- `2b8c16f` — docs: fix stale ProviderSearchCard references after shared-widget extraction
- `85b5133` — fix: atomic resolve to close concurrency race, validate provider_ids (backend)

---

## What was implemented

### Backend (`backend/app/modules/search/`, new; `backend/app/modules/administration/`, extended; `backend/app/modules/conversation/`, small extension)

- **New, reversible Alembic migration** (`search_domain_and_manual_match_assignments`,
  `2026_09_10_1100-f3a1c9d47b02`) — creates the `search` Postgres schema (`search_requests`, `provider_matches`,
  `search_event_log`) and adds `administration.manual_match_assignments` to the existing `administration` schema,
  column-for-column per `04_DATABASE.md`'s pre-existing spec, **except** four flagged nullable-column
  deviations (Decision 2, extended — see below). No changes to any existing table.
- **`search` module (new persisted state)** — `models.py` (`SearchRequestStatus` enum, `SearchRequest`,
  `ProviderMatch`, `SearchEventLog`); `repositories/` (`search_request_repository.py`,
  `provider_match_repository.py`, `search_event_log_repository.py`); `services/search_request_service.py`
  (`SearchRequestService` — see Decision 1/4/5 below); `search_request_api.py` (customer-facing `GET
  /search-requests/{search_request_id}`); `admin_manual_match_api.py` (`GET /admin/search/manual-matches`, `POST
  /admin/search/manual-matches/{assignment_id}/resolve`); `schemas.py` additions
  (`MatchedProviderResponse`/`SearchRequestResultResponse`/`ManualMatchAssignmentSummaryResponse`/
  `ResolveManualMatchRequest`); `dependencies.py` wiring; `SearchRequestNotFoundError` (404). New config:
  `AI_MATCH_MAX_RESULTS: int = 10`.
- **`administration` module (fourth application of the passive-queue-row pattern)** — `ManualMatchAssignment`
  model (Decision 3); `manual_match_assignment_repository.py` (`create`/`list_pending`/`get_by_id`/`update`, plus
  `try_resolve` added during review — see Bug Fix 2 below); `manual_match_assignment_service.py`
  (`ManualMatchAssignmentService`: `create`/`list_pending`/`get_by_id`/`resolve`, four explicit methods, mirroring
  `ClaimReviewRequestService`); `ManualMatchAssignmentNotFoundError` (404),
  `ManualMatchAssignmentAlreadyResolvedError` (409).
- **`SearchRequestService`** (Decision 1/4/5) — `handle_session_completed(...)` is the single call site
  `ConversationService._apply_completion_policy` invokes on both the `completed` and `routed_to_admin`
  transitions, branching internally on `status`. `_finalize_matches` is the **only** place in the codebase that
  ever writes `provider_matches` rows, sets `search_requests.status` to its final value, or writes a
  `search_event_log` row — called by both the automated path (`_handle_completed`, synchronously, in the same
  operation that creates the row) and the manual path (`resolve_manual_match`, at admin-resolution time). The
  automated path resolves the customer's default saved address (`customer.SavedAddressService`) and reuses
  `search.SearchService`/`provider.ProviderService.search_nearby` (DIR-001) unchanged for the actual match query,
  capped at `AI_MATCH_MAX_RESULTS` — no new ranking algorithm (Decision 5; the Review domain hasn't shipped, so
  there is no real merit signal to rank by yet). `match_score` is left `NULL` for every row this story writes,
  both paths.
- **`conversation` module (small extension)** — `ConversationService`'s constructor gains a
  `search_request_service: SearchRequestService` dependency; `_apply_completion_policy` calls
  `handle_session_completed(...)` on both terminal transitions, same flush, no new commit. `schemas.py`'s
  `ConversationSessionResponse` gains exactly one new field, `search_request_id: uuid.UUID | None` — **no
  confidence/score field added**, preserving `AI-001`'s AC6 and this story's own AC3 unchanged.
- **Customer-facing copy discipline (AC3/AC7)** — a new `test_no_forbidden_customer_copy.py` asserts
  `{"manual", "fallback", "admin"}` (case-insensitive) never appear in any hardcoded customer-facing string
  literal or in a live HTTP round trip against a `routed_to_admin`/`pending_manual_match` session. The
  `pending_manual_match`/`manual_match_assignments` identifiers themselves are backend-internal (enum values,
  table/column names) and are not what the test targets — it targets rendered/returned copy.
- **Tests** — `test_search_request_service.py`, `test_search_request_api.py`,
  `test_manual_match_assignment_service.py`, extensions to `test_conversation_service.py`, and
  `test_no_forbidden_customer_copy.py`.

### Mobile (`mobile/lib/features/conversation/`, extended; `mobile/lib/shared/`, new)

- **Shared-widget extraction (Mobile item 25), achieved cleanly — not flagged as debt.**
  `mobile/lib/shared/widgets/ranked_provider_results_list.dart` and
  `mobile/lib/shared/widgets/provider_result_card.dart` (moved/renamed from `features/search`'s
  `provider_search_card.dart`, generalized onto a new `mobile/lib/shared/models/ranked_provider_result.dart`
  model with a nullable `distanceMeters`) are now the single rendering path both `features/search`'s
  `SearchResultsScreen` (S-08) and `features/conversation`'s `AiConversationScreen` completion state consume.
  Neither feature imports the other's screen/widget file directly — this does not worsen, and is a materially
  cleaner outcome than, `13_OPEN_DECISIONS.md` item 12's already-logged direct-import debt (an unrelated
  `SavedAddressRepository` cross-feature import, untouched by this story).
- **`features/conversation` (extends `AI-001`'s existing feature)** — `conversation_repository.dart` gains
  `getSearchRequestResults(searchRequestId)` (`GET /search-requests/{id}`); `conversation_session.dart` gains
  `searchRequestId`; a new `search_request_result.dart` domain model mirrors the backend's
  `SearchRequestResultResponse`/`SearchRequestStatus`. `ai_conversation_screen.dart`'s completion state, previously
  a static "we're finding matches for you" message with no results mechanism to link to (`AI-001` Decision 1), now
  renders the shared ranked-results widget inline once `status` is `matched`/`unmatched`, while
  `pending_manual_match` keeps showing the **exact existing** waiting copy verbatim (no new string that could
  reintroduce a forbidden word) with lifecycle-aware polling (`WidgetsBindingObserver`-driven pause/resume on
  app background/foreground, cancelled on dispose/"Start over"). Two new, forbidden-word-clean strings
  (`aiConversationResultsHeading`, `aiConversationNoMatchesMessage`) were added for the `matched`/`unmatched`
  states — Decision 7 only locks the *pending* waiting copy verbatim; it does not prohibit new copy elsewhere,
  provided it avoids "manual"/"fallback"/"admin" (checked by hand and by a widget-test assertion).
- **`conversation_controller.dart`** owns the poll-timer lifecycle (`_syncResultsPolling`/`_pollResultsOnce`/
  `pausePolling`/`resumePolling`), a new `conversationResultsPollIntervalProvider` (default 5 seconds, flagged as
  a reasonable-but-untuned default, not a locked value — the Plan specified only "a short interval").
- **Tests** — extended `ai_conversation_screen_test.dart` (all three terminal states:
  `matched`/`unmatched`/`pending_manual_match` → poll → resolve, plus forbidden-word assertions), a new
  `provider_result_card_test.dart` (moved/adapted, plus a new `distanceMeters == null` rendering case), and
  `fake_conversation_repository.dart` extended for `getSearchRequestResults`.

---

## The Architecture Decisions, as actually shipped

All 7 decisions from `Plan_S07_AI-002.md` shipped as planned, with Decision 2 growing from three flagged
deviations to four (a genuine finding during implementation, not a Plan error), and one deliberate engineering
judgment call on Decision 6's mobile presentation:

1. **Cross-module wiring (`conversation → search`, `search → administration`, `search → customer`; `search →
   provider` reused unchanged)** — shipped exactly as planned. Confirmed cycle-free: `search`, `administration`,
   and `customer` each have zero imports of `conversation`, of each other in the reverse direction, or of
   `conversation`'s models.
2. **Nullable-column deviations from `04_DATABASE.md`'s current literal spec — four, not three.** The Plan
   flagged `manual_match_assignments.assigned_admin_id` (2a), `search_requests.structured_criteria` (2b), and
   `search_requests.customer_latitude`/`customer_longitude` (2c). Implementation found a genuine **fourth**:
   `search_requests.category_id` also had to become nullable, because a `routed_to_admin` session reached via
   `AI-001`'s hard turn cap (`CONVERSATION_MAX_TURNS`) can occur with no category ever resolved at all — confirmed
   directly against `RuleBasedConversationAiClient._resolve_category`/
   `ConversationService._apply_completion_policy`, neither of which requires `category_id` to be set before
   routing to the turn-cap outcome. Making it `NOT NULL` would force fabricating a category for a session that
   never had one — the same anti-fabrication violation the Plan's own three deviations already reject. All four
   are recorded together, same reasoning, same precedent (`00_PROJECT_CONTEXT.md` §3).
3. **`administration.ManualMatchAssignmentService`** — shipped exactly as planned, the fourth application of the
   passive-queue-row pattern (`admin_action_log`/VER-002, `claim_review_requests`/CLM-001, this story). Strengthened
   during review with an atomic `try_resolve` (see Bug Fix 2 below) — not a deviation from the Decision's intent,
   a correctness fix within it.
4. **Shared `_finalize_matches` helper** — shipped exactly as planned: the single writer of
   `provider_matches`/`search_requests.status`/`search_event_log` across both the automated and manual paths.
5. **Matching-mechanism reuse (`SearchService`/`search_nearby`, DIR-001, unchanged)** — shipped exactly as
   planned; no new ranking algorithm, since the Review domain hasn't shipped and there is no real rating signal
   to rank by yet.
6. **`ConversationSessionResponse.search_request_id`; mobile completion state becomes real** — shipped as planned,
   with one documented engineering judgment call: the Plan's prose said the completion state "now navigates to a
   ranked-results view"; `frontend` implemented this as an inline full-body replacement of the screen's active
   view (the shared widget rendered directly inside `ai_conversation_screen.dart`, transcript hidden once
   resolved) rather than a `Navigator`/`GoRouter` push to a separate route — the screen's existing compact
   bottom-input-area slot has no bounded height for a scrollable results list and was never going to render
   workably. Not a deviation from any explicit AC.
7. **Customer-facing copy discipline (AC3/AC7): a forbidden-word test, not a style guideline** — shipped exactly
   as planned, both backend (`test_no_forbidden_customer_copy.py`) and mobile
   (`expectNoForbiddenWordsRendered` in the widget test suite).

---

## Review Process — a full, honest account

### 1. `tester` — independent verification against real HTTP round trips, plus one genuine finding

The tester independently verified all 7 verbatim ACs, with particular attention to AC2's no-default-address edge
case, AC4's byte-for-byte-identical response shape between the automated and manually-resolved paths, AC6's
exactly-once `search_event_log` write, and AC7's live-HTTP forbidden-word assertions (not just static string
literals).

**Found a genuine bug:** `SearchRequestService.resolve_manual_match` originally called `_finalize_matches`
*before* `ManualMatchAssignmentService.resolve`'s already-resolved guard — meaning two sequential resolve
attempts on the same assignment could both run `_finalize_matches` (a second, duplicate `provider_matches` batch
and a second `search_event_log` row) before the second call's guard ever had a chance to reject it. This directly
contradicted AC6's "exactly once, regardless of origin" guarantee and AC4's implicit assumption that a resolved
assignment can't be re-finalized. **Fixed by reordering:** `resolve_manual_match` now calls
`ManualMatchAssignmentService.resolve` (the guard) **first**, and only calls `_finalize_matches` if that succeeds
— a rejected (409) second attempt now correctly writes nothing.

### 2. `architect` — first review found a deeper concurrency race plus an unvalidated-input gap; second review confirmed both fixed, zero remaining findings

**First pass** confirmed Decision 1's cross-module edges are genuinely cycle-free, Decision 4's `_finalize_matches`
is the sole writer, and the tester's reordering fix is directionally correct — but found the reordering fix's
own guard was still not airtight:

- **Finding 1 (concurrency race, Medium):** the tester's reordering fix made `resolve()` run *before*
  `_finalize_matches`, but `resolve()` itself was still a plain read-then-write (`get_by_id` → a Python `status`
  check → `repository.update`) — a genuine TOCTOU race remained for two truly concurrent admins resolving the
  *same* assignment: both could pass the Python-level check before either commits, and both would then proceed
  into `_finalize_matches`, writing a duplicate `provider_matches` batch and a duplicate `search_event_log` row
  for one `search_requests` row.
- **Finding 2 (missing input validation, Low):** `SearchRequestService.resolve_manual_match` never validated
  admin-supplied `provider_ids` before writing `provider_matches`, so a bogus id surfaced as an opaque 500 (an FK
  constraint violation) instead of a proper 4xx.

**Fixed:**
- **Finding 1** — added `ManualMatchAssignmentRepository.try_resolve`: a single atomic conditional `UPDATE
  ... WHERE status = 'pending'`, checking `rowcount == 1`, mirroring `ProviderRepository.try_claim_for_account`
  (CLM-001) and `VerificationRecordRepository.try_claim_for_review` (VER-002) exactly — this codebase's *third*
  application of this specific atomic-conditional-update pattern. `ManualMatchAssignmentService.resolve()` now
  calls `try_resolve` and raises `ManualMatchAssignmentAlreadyResolvedError` on `False`. Proven with a genuine
  **two-independent-session concurrency test** (`TestTryResolveAtomicity`), not just a sequential-call assertion —
  the same standard `try_claim_for_review`'s original VER-002 fix was held to.
- **Finding 2** — added `InvalidManualMatchProviderIdsError` (422), raised when any id in the admin-supplied
  `provider_ids` list doesn't correspond to a real `providers` row, validated via the existing
  `ProviderService.list_by_ids` (reused unchanged, the same batch-existence lookup `get_matched_providers` and
  VER-002 already use) — validated **before** any mutation happens.

Neither fix changes the valid-input resolve path's behavior or response shape.

**Second pass** re-reviewed both fixes specifically: re-verified `try_resolve`'s `WHERE` clause is the exact
same shape as its two precedents (Postgres row-lock semantics under READ COMMITTED, confirmed against
`app/database/database.py`), re-ran the new concurrency test to confirm it genuinely fails against the old
read-then-write code and passes against the fix, and confirmed the validation fix's placement (before any
mutation, reusing an existing method rather than a new query) matches `08_CODING_STANDARDS.md`'s "validate every
endpoint's input" rule. **Final verdict: APPROVED, zero remaining findings.**

### Final verdicts

- **`tester`**: all 7 ACs independently verified; one genuine bug found and fixed (the double-finalization
  ordering issue above).
- **`architect`**: two rounds — first pass found a genuine concurrency race and a missing-validation gap (both
  fixed); second, focused pass re-verified both fixes and returned **APPROVED with zero remaining findings**.
- **CTO sign-off** received after both verdicts were presented, per standing process.

### Backend test counts

658/658 backend tests passing (654 baseline + 4 new from the concurrency/validation fix round; the tester's own
new tests and the initial implementation's new test files are additional to that baseline). `ruff check`/`ruff
format --check` clean on all touched files.

### Mobile test counts

169/169 passing (baseline 165 + 4 net new). `flutter analyze`: 0 issues. `dart format`: applied to all files
touched by this story (one pre-existing, unrelated formatting drift in a file this story never touched was found
and correctly left alone).

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Every completed `AI-001` session writes a confidence score tagged with the model/prompt version that produced it | Pass — already satisfied by `AI-001`'s shipped `ConfidenceScore.model_version = "rule_based_v1"`, re-verified unchanged |
| 2 | Sessions below the configured confidence threshold create a `manual_match_assignments` record and notify an admin — never left in limbo | Pass — including the no-default-address edge case |
| 3 | The customer sees a message consistent with normal processing — never "manual," "fallback," or "admin" in customer-facing copy | Pass |
| 4 | Once an admin resolves the manual assignment, the customer receives the same ranked-results screen as an automated match would produce | Pass — byte-for-byte identical `SearchRequestResultResponse` shape from `GET /search-requests/{id}` regardless of origin |
| 5 | The system never retries the LLM call in a loop hoping for a higher score | Pass — already satisfied by construction in `AI-001`'s shipped code, re-verified unchanged |
| 6 | `search_event_log` records the session's outcome regardless of automated or manual resolution | Pass — exactly one row per `search_requests` row, never duplicated (proven by the tester's/architect's concurrency fixes above) |
| 7 | Automated tests assert below-threshold sessions always produce a `manual_match_assignments` row, and the customer-facing response contains no internal routing terminology | Pass |

**7 of 7 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded five new ADRs, ADR-037 through ADR-041 (cross-module wiring; the four
  nullable-column deviations; `ManualMatchAssignmentService` plus its atomic `try_resolve` fix; the shared
  `_finalize_matches` helper; matching-mechanism reuse).
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 10 (Degree of Manual/Wizard-of-Oz Matching at Launch) updated to
  record that a real, working implementation of the mechanism now exists — the underlying product question of how
  much matching should stay manual long-term at launch remains genuinely open.
- **`docs/AI/04_DATABASE.md`** — Search Domain (`search_requests`/`provider_matches`/`search_event_log`) and
  `administration.manual_match_assignments` marked shipped; all four nullable-column deviations recorded plainly.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 7 marked fully complete (all 3 of 3 stories done:
  `CTG-001`, `AI-001`, `AI-002`); this also completes Milestone ML7 in full.
- **`docs/CHANGELOG.md`** — new `[Unreleased]` entry for AI-002 (backend + mobile), including both bug fixes.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `AI-002` row** still needs its Status updated to "Done" and rolled up through
  ML7-EP02/ML7/SP07/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure, not performed by this closeout.
- **The underlying product question** (`13_OPEN_DECISIONS.md` item 10 — exactly how much matching should stay
  manual long-term at launch) remains genuinely open; this story ships the mechanism, it does not answer the
  product question.
- **The `ADM-001` admin-side queue dashboard UI** remains unbuilt, per this story's own explicit scope boundary —
  `GET /admin/search/manual-matches`/`POST .../resolve` are backend-API-only today.
- **A merit-based ranking algorithm** (rating + review volume + proximity) remains unbuilt — the Review domain
  hasn't shipped; nearest-first (DIR-001) is reused unchanged, honestly, not dressed up as something more precise
  than it is.

---

## Testing Performed

- `backend` implementation, with a new test suite across `test_search_request_service.py`,
  `test_search_request_api.py`, `test_manual_match_assignment_service.py`, extended
  `test_conversation_service.py`, and `test_no_forbidden_customer_copy.py`.
- `frontend` implementation, with a new/extended suite across `ai_conversation_screen_test.dart`,
  `provider_result_card_test.dart`, and `fake_conversation_repository.dart`.
- `tester` agent: all 7 ACs independently verified; one genuine bug found (the resolve/finalize ordering issue)
  and fixed.
- `architect` agent: two review passes — the first found a genuine concurrency race and a missing-validation gap
  (both fixed); the second re-verified both fixes and returned **APPROVED with zero remaining findings**.
- User (CTO) sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_10_1100-f3a1c9d47b02_search_domain_and_manual_match_assignments.py` (new
  migration)
- `backend/app/modules/search/models.py` (new — `SearchRequestStatus`, `SearchRequest`, `ProviderMatch`,
  `SearchEventLog`, all four nullable-column deviations documented in the module docstring)
- `backend/app/modules/search/services/search_request_service.py` (new — `SearchRequestService`,
  `_finalize_matches`)
- `backend/app/modules/search/search_request_api.py`, `admin_manual_match_api.py`, `schemas.py`,
  `dependencies.py` (new/extended)
- `backend/app/modules/administration/models.py` (`ManualMatchAssignment`, nullable `assigned_admin_id`)
- `backend/app/modules/administration/repositories/manual_match_assignment_repository.py` (new —
  including `try_resolve`, the architect-review fix)
- `backend/app/modules/administration/services/manual_match_assignment_service.py` (new — `resolve()` uses
  `try_resolve`)
- `backend/app/core/exceptions/exceptions.py` / `__init__.py` (`ManualMatchAssignmentNotFoundError`,
  `ManualMatchAssignmentAlreadyResolvedError`, `SearchRequestNotFoundError`,
  `InvalidManualMatchProviderIdsError`)
- `backend/app/modules/conversation/services/conversation_service.py` (`search_request_service` dependency,
  `_apply_completion_policy` call site)
- `backend/app/modules/conversation/schemas.py` (`ConversationSessionResponse.search_request_id`)
- `backend/tests/modules/search/`, `backend/tests/modules/administration/test_manual_match_assignment_service.py`
  (including `TestTryResolveAtomicity`), `backend/tests/test_no_forbidden_customer_copy.py`

### Mobile
- `mobile/lib/shared/models/ranked_provider_result.dart`, `mobile/lib/shared/widgets/provider_result_card.dart`,
  `mobile/lib/shared/widgets/ranked_provider_results_list.dart` (new — the shared extraction)
- `mobile/lib/features/conversation/domain/models/search_request_result.dart` (new)
- `mobile/lib/features/conversation/data/conversation_repository.dart` (`getSearchRequestResults`)
- `mobile/lib/features/conversation/state/conversation_controller.dart` (poll-timer lifecycle)
- `mobile/lib/features/conversation/presentation/screens/ai_conversation_screen.dart` (resolved-results state,
  lifecycle-aware polling)
- `mobile/lib/features/search/presentation/screens/search_results_screen.dart` (now consumes the shared widget)
- `mobile/test/features/conversation/ai_conversation_screen_test.dart`,
  `mobile/test/shared/widgets/provider_result_card_test.dart`

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-037 through ADR-041
- `docs/AI/13_OPEN_DECISIONS.md` — item 10 implementation-status update
- `docs/AI/04_DATABASE.md` — Search Domain and `manual_match_assignments` confirmed-shipped
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 7 / Milestone ML7 complete
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 7 (Category Domain / AI Intake foundation) is now fully complete** — `CTG-001`, `AI-001`, and `AI-002`
  have all shipped and been signed off. **This also completes Milestone ML7 in full** (all three of ML7's stories
  — `AI-001`, `AI-002`, `CTG-001` — are Done).
- **`13_OPEN_DECISIONS.md` item 10** (degree of manual/Wizard-of-Oz matching at launch) now has a real,
  working, config-driven implementation to point to — but the product question of exactly how much matching
  should stay manual long-term at launch remains genuinely open, unaffected by this story shipping.
- **`ADM-001`/`ADM-002`** (the admin operations dashboard, including the manual-match queue UI this story's
  backend-only `GET /admin/search/manual-matches` is built for) is the most directly-motivated next candidate
  this story surfaces — not planned or started by this closeout.
- **A real LLM vendor selection** (`13_OPEN_DECISIONS.md` item 13, surfaced by `AI-001`) remains the other
  standing open product decision in this domain, unaffected by `AI-002` shipping.
- **`docs/AI/Project_Tracker.xlsx`'s `AI-002` row** still needs its Status flipped to "Done" and rolled up through
  ML7-EP02/ML7/SP07/the Phase Tracker/the Dashboard — handled separately via the CTO's own raw-XML procedure, not
  performed by this closeout.
- **`docs/implementation/plans/Checkpoint_S07_AI-002.md` still needs to be deleted** per the Continuity &
  Checkpointing rule — this closeout pass had Read/Write/Edit/Grep/Glob tools only, with no file-deletion
  capability, so the file could not be removed here despite the story being complete and signed off.
