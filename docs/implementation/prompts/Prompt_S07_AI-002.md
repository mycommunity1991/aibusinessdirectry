# Implementation Prompt — Story AI-002

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Story:** AI-002 — Receive Matches Even When AI
Confidence Is Low | **Plan:** `docs/implementation/plans/Plan_S07_AI-002.md` (read in full before starting — this
prompt is a pointer to it, not a replacement for it)

---

## Task

Implement Story AI-002 exactly per `docs/implementation/plans/Plan_S07_AI-002.md`. Read `.agents/agents.md` and
the `docs/AI/` documents that Plan's "Related Documents" section names before writing any code — in particular
`docs/AI/04_DATABASE.md`'s `search_requests`/`provider_matches`/`search_event_log`/`manual_match_assignments`
sections and `docs/AI/09_DECISIONS.md` ADR-030 (the `claim_review_requests`/`_finalize_claim` precedent this
story mirrors throughout) and ADR-032/033/034/035/036 (`AI-001`'s decisions this story builds directly on).

## Story Summary

Build the Wizard-of-Oz manual-match fallback and its automated counterpart: every `conversation_sessions` row
that reaches `completed` or `routed_to_admin` (`AI-001`) now produces a real `search.search_requests` row,
resolved either by real (reused, not new) provider matching or by an admin acting on a
`administration.manual_match_assignments` queue row — with the customer's downstream experience identical either
way. Backend-heavy: three new persisted tables in `search`, one new table in `administration`, a small extension
to `conversation`. Mobile: a shared ranked-results widget and light polling added to the existing AI Conversation
screen. Does **not** build the `ADM-001` admin dashboard UI, a merit-ranking algorithm, or a location-collection
step in the chat flow — see the Plan's "Explicitly Out of Scope."

## Acceptance Criteria

See the Plan's "Acceptance Criteria" section — verbatim from `Project_Tracker.xlsx`, obtained directly this
session (not reconstructed). AC1 and AC5 are already satisfied by `AI-001`'s shipped code; this story only needs
to verify they remain true, not implement anything new for them.

## Key Decisions to Follow (do not re-derive — the Plan already resolved these)

1. **Cross-module wiring (Decision 1):** exactly three new edges — `conversation → search` (one call site,
   `_apply_completion_policy`), `search → administration` (create/resolve the manual-match queue row), `search →
   customer` (default saved address). **Do not** add `administration → conversation` (e.g. to read the
   transcript) — this creates a cycle against the `search → administration` edge; if a need for it comes up,
   stop and flag it rather than adding it.
2. **Three nullable-column deviations from `04_DATABASE.md`'s current spec (Decision 2)** —
   `manual_match_assignments.assigned_admin_id`, `search_requests.structured_criteria`,
   `search_requests.customer_latitude`/`customer_longitude` all become nullable, each for a specific, documented
   reason. Do not fabricate a placeholder value for any of them instead.
3. **`ManualMatchAssignmentService` (Decision 3)** mirrors `ClaimReviewRequestService`
   (`administration/services/claim_review_request_service.py`) file-for-file: `create`/`list_pending`/
   `get_by_id`/`resolve`, no generic CRUD. "Notify an admin" (AC2) is satisfied by this being a pull-based queue
   (`GET /admin/search/manual-matches`), not a push notification — do not build a notification-delivery
   mechanism for this.
4. **One shared `_finalize_matches` helper (Decision 4)** in `SearchRequestService` is the **only** place
   `provider_matches`/`search_requests.status`/`search_event_log` are ever written, called by both the automated
   path and `resolve_manual_match`. Do not write two separate finalization code paths.
5. **Matching mechanism (Decision 5):** reuse the existing `search.SearchService`/
   `provider.ProviderService.search_nearby` (DIR-001) unchanged — nearest-first ranking, category passed as the
   resolved `Category.name` string. Do not build a new merit/rating-based ranking algorithm; the Review domain
   hasn't shipped and there's no real signal to rank by yet.
6. **`ConversationSessionResponse` gains `search_request_id` only (Decision 6)** — never a confidence/score field.
   A new `GET /search-requests/{id}` endpoint (owner-checked, ADR-015 collection shape) is the customer-facing
   results read.
7. **Forbidden-word test, not a style guideline (Decision 7):** write the automated test asserting no
   customer-facing string/response ever contains "manual," "fallback," or "admin" (AC3/AC7) — this must be a
   live-response/rendered-widget assertion, not just a review of the copy you wrote.

## Delegation Order

1. **backend** — the entire backend Plan section (Proposed Changes items 1–24, Architecture Decisions 1–5, 7).
   Build order: migration (both `search` schema and the `manual_match_assignments` addition) → `administration`'s
   `ManualMatchAssignmentService` (small, build before `search` since `search` depends on it) → `search` module
   (models → repositories → `SearchRequestService`, with `_finalize_matches` getting the most careful review) →
   `search/api.py`/`schemas.py`/`dependencies.py` → the small `conversation` extension last, re-running `AI-001`'s
   existing test suite to confirm no regression.
2. **frontend** — Mobile Proposed Changes items 25–30, once backend endpoints exist (or in parallel against a
   fake repository). Extract the shared ranked-results widget (item 25) rather than importing `features/search`
   directly from `features/conversation`; if extraction is skipped, flag it explicitly as new debt (mirroring
   `13_OPEN_DECISIONS.md` item 12's format), don't duplicate silently.
3. **tester** — verify all 7 ACs per the Plan's Verification Plan table, with particular attention to AC2's
   no-default-address edge case, AC4's byte-for-byte-identical response shape across both resolution paths, and
   AC6's exactly-once `search_event_log` write.
4. **architect** — review per the Plan's Delegation section step 4, with cross-module cycle-freedom (Decision 1)
   as the single highest-value focus area.

Pause and present to the user once `tester`/`architect` both report clean — do not write the Walkthrough, touch
`docs/CHANGELOG.md`/tracker, or mark the story complete without explicit sign-off.

## Out of Scope

See the Plan's "Explicitly Out of Scope" section — notably the `ADM-001` dashboard UI, any admin endpoint that
reads a session's full transcript, a merit-ranking algorithm, a location-collection step in the chat flow, a real
push-notification channel, and reconciling `provider_category_labels` into `category.provider_categories`.

## Before You Start — Open Questions Worth a Quick CTO Check

The Plan's "Open Questions" section flags three items (the three nullable-column deviations needing ADR
ratification, whether a saved default address should eventually be mandatory before AI intake, and confirming
admin transcript visibility is fully deferred to `ADM-001`). None of these block starting backend work — all
three are documented, precedented interim designs — but confirm no CTO correction has landed before finalizing
the Walkthrough.
