# Walkthrough S11 ADM-001

## Story: Resolve Manual-Match and Unmatched-Query Work as an Administrator

**Sprint:** 11 | **Story ID:** ADM-001 | **Milestone:** ML11 | **Epic:** ML11-EP01 | **Priority:** High |
**Status:** Done

As an administrator, I want a queue of low-confidence sessions needing manual matching and a report of searches
that produced no good match, so that I can keep the Wizard-of-Oz fallback working and spot supply/category gaps
early. This story gives admins the operational surface for two things already producing data in earlier
stories: `AI-002`'s `manual_match_assignments` and `MAT-001`'s `search_event_log` unmatched entries. The admin
platform itself (Flutter vs. a separate internal tool) remains an explicitly open decision — this story
implements the API layer, which is platform-agnostic, without assuming the answer. **Scope boundary:** does not
include verification review (`VER-002`, already delivered) or the broader admin dashboard shell (`ADM-002`).

Full context, the 9 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S11_ADM-001.md`.

All work is committed and pushed as a single commit, `c4411c9`.

**This is Sprint 11 / Milestone ML11's first story.** With `ADM-001` done, **Sprint 11 is now 1 of 2 stories
done.** Its second and final story, `ADM-002` ("Operate the marketplace from an admin dashboard"), depends on
`VER-002` (already shipped) + `ADM-001` (now also shipped) — both dependencies are satisfied, making `ADM-002`
the next startable story in this sprint.

---

## The `unmatched_query_reports` contradiction — resolved with direct evidence at planning time

Before any code was written, `docs/AI/SESSION_HANDOFF.md`'s own "Pull-based admin queue pattern" precedent list
(§4) was checked directly against the real code, because it listed `unmatched_query_reports` alongside three
already-shipped tables (`admin_action_log`, `claim_review_requests`, `manual_match_assignments`) as if it were a
fourth already-built application of the pattern. This was confirmed to be a genuine documentation slip, not
fact: `administration/models.py` defined exactly three model classes, no migration anywhere referenced
`unmatched_query_reports`, and `04_DATABASE.md` itself already labeled the table "remain unbuilt" in the same
breath as documenting its full column spec. **AC1 is therefore a genuine new migration, exactly as its literal
text says** — corrected at this story's closeout (see "Documentation updated at story close" below).

Reading the already-shipped `AI-002` code in full (`search/admin_manual_match_api.py`,
`SearchRequestService`/`_finalize_matches`, `ManualMatchAssignmentService`/`Repository`,
`test_search_request_api.py`) also confirmed **AI-002 had already shipped almost all of AC2/AC3/AC4/AC6/AC7's
substance**: the manual-match list endpoint, role gate, and pagination already existed (only the conversation
transcript was missing — the one genuine gap in AC2); `resolve_manual_match` already wrote `provider_matches`
through the exact same `_finalize_matches` helper the automated matcher uses, with the admin's own supplied
order as `rank` (AC3, unchanged by this story); the customer read path was already identical regardless of
resolution method (AC4, true by construction); `require_role(ROLE_ADMIN)` already gated both existing routes
with a passing 403 test each (AC6, for those two routes); and an existing test already proved AC7's first bullet
end-to-end. **This materially narrowed this story's real net-new engineering to AC1, AC2 (the transcript), and
AC5** — the manual-match-side work needed only verification/regression-confirmation, not new write logic.

---

## What was implemented

### A new `administration.unmatched_query_reports` table and admin review workflow

- **New migration** (`backend/alembic/versions/2026_09_15_1000-34cd99dbf8db_unmatched_query_reports.py`) —
  creates `administration.unmatched_query_reports` with the full `CommonColumnsMixin` plus
  `search_event_log_id` (UUID, not null, FK → `search.search_event_log.id`, unique 1:1),
  `category_gap_notes` (TEXT, nullable), `status` (VARCHAR(20), not null, default `'open'`), `reviewed_by`
  (UUID, nullable, FK → `identity.users.id`), `reviewed_at` (TIMESTAMPTZ, nullable) — built exactly to
  `04_DATABASE.md`'s pre-existing spec, no deviation. The tester independently confirmed the shipped columns via
  a direct `psql \d` inspection matching the spec verbatim.
- **`UnmatchedQueryReportRepository`/`Service`** (`administration`'s fourth aggregate root, alongside
  `AdminActionLog`/`ClaimReviewRequest`/`ManualMatchAssignment`) — `list_filtered` (status filter, `created_at`
  sort, correct pagination), `try_transition_status` (a single atomic conditional `UPDATE ... WHERE id = :id AND
  status IN :from_statuses`, mirroring `try_resolve`/`try_claim_for_review`/`try_claim_for_account`), and two
  entry points: `mark_reviewed` (`open → reviewed` only) and `mark_actioned` (`open` **or** `reviewed →
  actioned`, since an admin may action a report directly without a separate review step). Any disallowed
  transition (a repeat call, or a backward move) raises one shared `UnmatchedQueryReportInvalidTransitionError`
  (409).
- **Rows are created automatically, never lazily**: `SearchRequestService._finalize_matches` (the sole writer
  of `search_event_log`, for both the automated and manual match paths — `AI-002`, `ADR-040`) gains one
  additive, in-place call: immediately after writing the `search_event_log` row, if `not ranked_matches` (the
  row's own `was_matched = False`), it calls `UnmatchedQueryReportService.create(search_event_log_id=...)`.
  This guarantees a strict 1:1 correspondence with zero risk of a missed or duplicated report, since both match
  paths already funnel through this one helper (`ADR-058`).
- **`administration`'s first-ever `api.py`** (`GET`/`POST /admin/unmatched-query-reports/...`) — `GET ""` lists
  reports (`status` filter defaulting to `open`, `sort` by `created_at`, paginated); `POST "/{id}/review"` and
  `POST "/{id}/action"` perform the status transitions; all three routes gated by `require_role(ROLE_ADMIN)`,
  the same mechanism every prior admin route in this codebase uses. This is a deliberate placement decision
  (`ADR-059`), not an oversight: `administration`'s three prior aggregates each needed a *cross-module write* to
  resolve their admin action, which is why their routes live in the *other* module receiving that write;
  `unmatched_query_reports`' review/action workflow is entirely self-contained within `administration`'s own
  table, so its routes live in `administration` itself for the first time.
- **A new, minimal `search.SearchEventLogService`** (`get_by_ids`, backed by a new
  `SearchEventLogRepository.list_by_ids`) supplies read-only display context (`category_id`/`customer_id`/
  `query_text`/`result_count`) for each report row — `administration`'s first-ever outgoing cross-module edge
  (`administration -> search`), wired as a Service per `ADR-047`.
- **The response exposes `customer_id`/`query_text`/`category_id` directly** — judged the same category of
  admin operational tool `claim_review_requests` already is (which exposes `claimant_user_id` unmasked), not
  `06_SECURITY.md`'s Analytics-surface restriction, since identifying the specific customer/search is the entire
  point of "spotting a supply/category gap" the story's own text names as its purpose.
- **Flagged, non-blocking, not fixed by this story**: `search_event_log.query_text` is written as a hardcoded
  `None` in every call to `_finalize_matches` today (an `AI-002` gap) — every `unmatched_query_reports` row's
  enriched `query_text` therefore reads `null` until a future story wires the real customer free text through.
  `category_id`/`customer_id`/`result_count` are unaffected.

### Conversation transcript embedded in the existing manual-match list endpoint (AC2)

- **`ManualMatchAssignmentSummaryResponse`** gains `transcript: list[MessageResponse]`, embedded directly in the
  existing `GET /admin/search/manual-matches` list response — directly precedented by
  `verification/admin_api.py`'s own pattern of embedding full context inline rather than behind a second detail
  endpoint, since the pending-manual-match queue is low-volume by design. Reuses
  `conversation.schemas.MessageResponse`/`message_to_response` verbatim, precedented by
  `provider/claim_api.py`'s existing cross-module schema reuse.
- **`MessageRepository.list_for_sessions(session_ids)`** — a new batch method (`WHERE conversation_session_id IN
  (...) AND is_active`, grouped and ordered by `sequence_number` per session) — called once per page inside
  `SearchRequestService.list_pending_manual_matches`, never per-row (no N+1).

### Verification/regression confirmation for the already-shipped AI-002 behavior

No new write logic was needed for AC3, AC4, or AC6-for-manual-matches — `tester` independently re-confirmed each
still holds unmodified after this story's changes: manual-match resolution still writes `provider_matches`
through `_finalize_matches` with the admin's own supplied order as `rank`; the customer-facing
`GET /search-requests/{id}` result is still identical regardless of resolution method; `require_role(ROLE_ADMIN)`
still 403s a non-admin caller on both pre-existing manual-match routes; and the existing end-to-end
resolve-then-fetch test still passes (AC7's first bullet).

---

## The 9 Architecture Decisions, as actually shipped

All 9 decisions from `Plan_S11_ADM-001.md` shipped as planned, with **one implementation-time deviation from the
Plan's own literal text** (Decision 6's actual wiring — see below).

1. **`unmatched_query_reports` did not exist yet; AC1 is a genuine new migration; `SESSION_HANDOFF.md` is
   corrected at this closeout** — resolved above with direct file/line evidence at planning time, not assumed.
2. **`unmatched_query_reports` is `administration`'s fourth aggregate root, auto-created inside
   `_finalize_matches` at write time, never lazily computed.**
3. **AC2's transcript is embedded directly in the existing list-item response** (in-place upgrade), reusing
   `conversation.schemas.MessageResponse` verbatim.
4. **The new `search -> conversation` edge is `MessageRepository` (raw Repository), not `ConversationService`**
   — constructed directly (`MessageRepository(db)`) inside `search/dependencies.py`, never importing
   `conversation.dependencies`/`conversation.services`, since `conversation.dependencies` already imports back
   into `search` (AI-001/AI-002's existing edge) — a same-direction import would have been a genuine circular
   import.
5. **AC3, AC4, and AC6-for-manual-matches needed no new backend write logic** — this story's job there was
   verification/regression-confirmation only.
6. **`administration` gets its first-ever `api.py`; a new, minimal `search.SearchEventLogService` supplies
   read-only display context** — **shipped with one deviation from the Plan's own literal wiring instruction**
   (Backend item 14 had instructed `administration/dependencies.py` to wire in
   `search.dependencies.get_search_event_log_service` directly). By the time this item was implemented, the
   Plan's own item 7/8 had already given `search/dependencies.py` a *second* `search -> administration` edge
   of its own (`UnmatchedQueryReportService`, Decision 2's write-time hook). Following item 14 literally would
   therefore have made `administration.dependencies` and `search.dependencies` import each other at module
   level — a **second**, genuine circular import, created not by either wiring instruction being individually
   wrong, but by the interaction between two of the Plan's own separately-reasoned items once both were actually
   implemented. `backend` caught this during implementation (before `tester`/`architect` ever saw a broken
   import) and resolved it the same way Decision 4 already had: `administration/dependencies.py`'s
   `_get_search_event_log_service_for_administration` constructs `SearchEventLogService(SearchEventLogRepository(db))`
   directly from `search`'s leaf repository/service modules, never importing `search.dependencies` at all. The
   deviation and its reasoning are documented directly in that function's own docstring.
7. **AC5's filter/sort scope is `status` + `created_at` only** — category-level filtering is deliberately
   deferred (visible per-row, not filterable page-wide yet), flagged as Open Question 2, not silently dropped.
8. **Status-transition mechanics: atomic conditional `UPDATE`, forward-only lifecycle, one shared 409
   exception** — `try_transition_status`, mirroring the `try_resolve`/`try_claim_for_review`/
   `try_claim_for_account` family exactly (`ADR-039`).
9. **The response exposes `customer_id`/`query_text`/`category_id` directly** — judged an admin operational
   tool, not `06_SECURITY.md`'s Analytics restriction, matching `claim_review_requests`' own existing precedent.

Grouped at this closeout into **3 new ADRs** by architectural theme (write-time dependent-record creation;
admin-capability HTTP-surface placement; circular-import avoidance): **ADR-058** (Decision 2 — the
`_finalize_matches` write-time hook, extending `ADR-042`'s in-place-upgrade principle to a new-record-creation
case), **ADR-059** (Decision 6's placement reasoning — a new, more specific rule than `ADR-051`/`ADR-054`, for
*where an admin action's HTTP surface lives*, not where a table's model lives), and **ADR-060** (Decision 4 as
planned, and Decision 6's actual, Plan-deviating implementation — the same circular-import-avoidance shape
applied twice in one story, a second, distinct justification under `ADR-047`'s raw-dependency exception).
Decision 1 (a documentation correction, not an architectural shape) is recorded in this Walkthrough and
`SESSION_HANDOFF.md`'s own corrected entry, not given its own ADR. Decisions 3, 5, 7, 8, 9 are direct,
unmodified continuations of already-established precedents (`verification/admin_api.py`'s embed-context-inline
shape; `AI-002`'s own shared-`_finalize_matches` guarantee meaning no new write logic was needed; a deliberately
flagged, non-silent scope deferral; the `try_resolve`-family atomic-conditional-write pattern, `ADR-039`;
`claim_review_requests`' own admin-operational-tool precedent for exposing an unmasked identifying field) and
are recorded in the Plan, not given their own ADR.

---

## Review Process

### `tester` — all 7 verbatim ACs pass, zero gaps, zero regressions

`tester` independently verified every verbatim AC against real infrastructure (real DB, real HTTP round trips):

- **AC1**: the migration applies cleanly; the table's columns/constraints match `04_DATABASE.md`'s spec exactly
  (confirmed via a direct `psql \d` inspection); a genuinely unmatched search creates exactly one report row
  pointing at the correct `search_event_log_id`; a matched search creates zero such rows (the negative case,
  explicitly asserted).
- **AC2**: the list endpoint's `transcript` field genuinely reflects each assignment's own session's real
  messages, oldest first; a multi-assignment, no-cross-contamination fixture confirms assignment A's transcript
  never contains assignment B's messages (the batching correctness check, since `list_for_sessions` groups in
  one query).
- **AC3/AC4/AC6-for-manual-matches/AC7-bullet-1**: independently re-confirmed the already-shipped `AI-002`
  behavior still holds unmodified after this story's changes — not skipped just because it was "already
  tested." Zero regressions found.
- **AC5**: the full status-transition matrix (`open→reviewed` succeeds; `open→actioned` succeeds;
  `reviewed→actioned` succeeds; `reviewed→reviewed`/`actioned→reviewed`/`actioned→actioned` all → 409;
  nonexistent id → 404 for both entry points), plus filter/sort correctness over real HTTP.
- **AC6**: 403 for a non-admin caller on all three new `unmatched_query_reports` routes, plus the pre-existing
  manual-match routes' own 403 tests re-confirmed as a regression gate.
- **AC7**: both required test categories exist and pass (manual-match customer-visible result — already
  existing, re-confirmed; unmatched-report status transitions — newly added).

**Result: all 7 verbatim ACs pass, zero gaps, zero regressions in the already-shipped `AI-002` code.**

### `architect` — zero blocking findings, no fix-and-recheck round needed

`architect`'s review covered: Decision 2's `_finalize_matches` in-place extension for correctness against
`ADR-042` (no divergent parallel write path introduced); Decision 4's circular-import reasoning and the new
`search -> conversation.repositories.MessageRepository` edge (confirmed no accidental import of
`conversation.services`/`conversation.dependencies` anywhere, and that `search_request_service.py`'s own module
docstring genuinely reflects the new, narrower "zero imports from conversation except this one read-only path"
claim); Decision 6's new `administration/api.py` and the new `administration -> search.SearchEventLogService`
edge, including the deviation from the Plan's own literal item 14 — confirmed the deviation was correctly
reasoned, correctly avoided the second circular import, and was correctly named in the wiring function's own
docstring; Decision 8's atomic-transition mechanics for genuine race-safety (not just "tests pass"); Decision 9
against `06_SECURITY.md`'s Sensitive Data section for the Analytics-vs-operational-tool distinction; and a full
`import app.main`-style sanity check confirming no circular import exists anywhere in the final diff.

**Result: zero blocking findings. No fix-and-recheck round needed.**

### Final verdicts

- **`tester`**: all 7 verbatim ACs pass, zero gaps, zero regressions in the already-shipped `AI-002` code.
- **`architect`**: zero blocking findings, no fix-and-recheck round needed.
- **CTO standing instruction**: the CTO gave a standing instruction for this story to proceed straight through
  closeout without an additional sign-off pause once both verdicts were clean — this closeout follows that
  instruction.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `unmatched_query_reports` table exists via migration, sourced from `search_event_log` rows where `was_matched=false`, supporting admin annotation and a status (open/reviewed/actioned) | Pass — migration applies cleanly, columns/constraints match `04_DATABASE.md`'s spec exactly (`psql \d` confirmed); an unmatched search creates exactly one report row, a matched one creates zero |
| 2 | Admin-only endpoint lists pending `manual_match_assignments` with the underlying conversation transcript available for context | Pass — `transcript` field reflects each assignment's real session messages, oldest first; multi-assignment no-cross-contamination fixture confirms correct batching |
| 3 | Admin can select and rank candidate providers for a manual assignment, writing to `provider_matches` exactly as the automated matcher would | Pass — already shipped by `AI-002`, independently re-confirmed unmodified (zero regressions) |
| 4 | Completing a manual assignment updates its status and is reflected in the customer's ranked-results screen without further admin action | Pass — already true by construction (`AI-002`), independently re-confirmed unmodified |
| 5 | Unmatched query reports can be filtered/sorted and marked reviewed/actioned by an admin | Pass — full status-transition matrix and filter/sort HTTP assertions, all passing |
| 6 | Non-admin access to either endpoint returns 403 | Pass — three new `unmatched_query_reports` routes' own dedicated 403 tests, plus pre-existing manual-match routes' 403 tests re-confirmed as a regression gate |
| 7 | Automated tests cover: manual assignment completion producing a customer-visible result, and unmatched-report status transitions | Pass — bullet 1 already existing and re-confirmed; bullet 2 newly added and passing |

**7 of 7 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded three new ADRs:
  - **ADR-058** — the write-time dependent-record-creation hook inside `_finalize_matches`, extending `ADR-042`'s
    in-place-upgrade principle to a new-record-creation case.
  - **ADR-059** — the admin-capability HTTP-surface placement rule (an admin action's routes live wherever the
    write its resolution performs actually lands), a sibling to `ADR-051`/`ADR-054`'s schema-ownership rule for
    a different question.
  - **ADR-060** — the circular-import-avoidance principle, applied twice in this one story (once as planned,
    once as a genuine mid-implementation Plan deviation), a second, distinct justification under `ADR-047`'s
    raw-dependency exception.
- **`docs/AI/04_DATABASE.md`** — `unmatched_query_reports` marked shipped (removed from the "remain unbuilt"
  list alongside `feature_flags`/`system_settings`, which stay there); its own section now notes the automatic
  write-time creation mechanism, `administration`'s first cross-module edge, and first `api.py`, plus the
  flagged `query_text`-always-`null` limitation.
- **`docs/AI/SESSION_HANDOFF.md`** — §4's "Pull-based admin queue pattern" precedent-list entry corrected: all
  four applications (`admin_action_log`, `claim_review_requests`, `manual_match_assignments`,
  `unmatched_query_reports`) are now genuinely shipped as of this story's completion, with an explicit
  documentation-integrity note explaining that the entry was inaccurate prior to `ADM-001` shipping. §1/§2/§7/§8
  updated with this story's outcome, the new ADR numbering (next new ADR starts at ADR-061), the new test count,
  and `ADM-002` as the next startable story.
- **`docs/implementation/PROJECT_IMPLEMENTATION_STATE.md`** — top summary line, Executive Summary, Section 16
  (Overall Progress), and Section 17 (Next Planned Story) all updated: `ADM-001` marked complete, Sprint 11 now
  1 of 2 stories done, `ADM-002` noted as the next startable story.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `ADM-001`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `ADM-001` row** still needs its Status updated to "Done" and rolled up
  through ML11-EP01/ML11/SP11/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML-safe cell-patching procedure, not performed by this closeout.
- **`search_event_log.query_text`'s always-`None` write path** (an `AI-002` gap, not fixed here) — every
  `unmatched_query_reports` row's `query_text` field reads `null` until a future story wires the real customer
  free text through `_finalize_matches`.
- **AC5's category-level filtering** remains deliberately deferred (visible per-row, not filterable page-wide) —
  revisit only if real admin usage shows this filter is actually needed.
- **No Checkpoint file existed for this story** (a fresh start, Sprint 11's first story) — none to delete at
  closeout.

---

## Testing Performed

- `backend` implementation: new `administration`/`search`/`conversation` test coverage
  (`test_unmatched_query_report_service.py`, `test_unmatched_query_report_repository.py`,
  `test_unmatched_query_report_api.py`, extensions to `test_search_request_service.py`,
  `test_search_request_api.py`, and `conversation`'s message-repository tests). Full suite green immediately
  after implementation, `ruff check .` clean.
- `tester` agent: independently verified all 7 verbatim ACs against real infrastructure (real DB, real HTTP
  round trips); zero gaps, zero regressions found in the already-shipped `AI-002` code.
- `architect` agent: zero blocking findings; no fix-and-recheck round needed.
- **Final counts: 864/864 backend tests (821 baseline before this story + 43 new, zero regressions).** No
  mobile work — this story is backend-only, per its own explicit scope boundary.
- CTO gave a standing instruction to proceed straight through closeout once both verdicts were clean, without an
  additional sign-off pause for this story.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_15_1000-34cd99dbf8db_unmatched_query_reports.py` (new migration)
- `backend/app/modules/administration/models.py` (`UnmatchedQueryReport`, new)
- `backend/app/modules/administration/repositories/unmatched_query_report_repository.py` (new —
  `list_filtered`, `try_transition_status`)
- `backend/app/modules/administration/services/unmatched_query_report_service.py` (new — `create`,
  `list_filtered`, `mark_reviewed`, `mark_actioned`)
- `backend/app/modules/administration/schemas.py` (new — `administration`'s first schemas file)
- `backend/app/modules/administration/api.py` (new — `administration`'s first-ever `api.py`)
- `backend/app/modules/administration/dependencies.py`
  (`_get_search_event_log_service_for_administration` — the `ADR-060` circular-import-avoidance construction)
- `backend/app/modules/search/repositories/search_event_log_repository.py` (`list_by_ids`, new)
- `backend/app/modules/search/services/search_event_log_service.py` (new — `get_by_ids`)
- `backend/app/modules/search/dependencies.py` (`get_search_event_log_service`, `get_message_repository`, new;
  `get_search_request_service` extended with `message_repository`/`unmatched_query_report_service`)
- `backend/app/modules/search/services/search_request_service.py` (`_finalize_matches`'s new write-time hook;
  `list_pending_manual_matches`'s new transcript batching; `message_repository` constructor dependency)
- `backend/app/modules/conversation/repositories/message_repository.py` (`list_for_sessions`, new)
- `backend/app/modules/search/schemas.py` (`ManualMatchAssignmentSummaryResponse.transcript`, new field)
- `backend/app/modules/search/admin_manual_match_api.py` (`_to_summary` passes `transcript` through)
- `backend/app/core/config.py` (`UNMATCHED_QUERY_REPORT_MAX_PAGE_SIZE`, new)
- `backend/app/core/exceptions/exceptions.py` (`UnmatchedQueryReportNotFoundError`,
  `UnmatchedQueryReportInvalidTransitionError`, new)
- `backend/app/api/v1/api.py` (`administration.api.router` registered at `/admin/unmatched-query-reports`)
- `backend/tests/modules/administration/test_unmatched_query_report_service.py`,
  `test_unmatched_query_report_repository.py`, `test_unmatched_query_report_api.py` (new)
- `backend/tests/modules/search/test_search_request_service.py`, `test_search_request_api.py` (extended)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-058, ADR-059, ADR-060
- `docs/AI/04_DATABASE.md` — Administration Domain, `unmatched_query_reports` marked shipped
- `docs/AI/SESSION_HANDOFF.md` — §4 precedent-list correction; §1/§2/§7/§8 refreshed
- `docs/implementation/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 11 marked 1 of 2 stories done
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 11 / Milestone ML11 is now 1 of 2 stories done: `ADM-001`.**
- **`ADM-002`** ("Operate the marketplace from an admin dashboard") is the next startable story in this sprint —
  both of its dependencies (`VER-002`, `ADM-001`) are now satisfied. Its full details have not been re-fetched
  from `Project_Tracker.xlsx` this session; a fresh lookup is needed before planning begins.
- **`ADR-058`'s write-time dependent-record-creation pattern is now a documented precedent** for any future
  story needing to react to a specific outcome of an already-shared write, without inventing a second write path
  or a lazy materialize-on-read query.
- **`ADR-059`'s admin-capability HTTP-surface placement rule is now a documented precedent**: check whether
  resolving a new admin action requires a cross-module write; if yes, host the route in that other module (the
  pre-existing pattern); if no, host it in the aggregate's own home module, even at the cost of that module's
  first `api.py`.
- **`ADR-060`'s circular-import-avoidance principle is now a documented precedent**: re-check for a fresh
  circular import whenever a new edge touches a `dependencies.py` file already modified earlier in the same
  story — a Plan can reason correctly about each wiring edge in isolation and still combine two of its own items
  into a cycle neither one alone would have produced.
- **`docs/AI/Project_Tracker.xlsx`'s `ADM-001` row** still needs its Status flipped to "Done" and rolled up
  through ML11-EP01/ML11/SP11/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.

---

**End of Document**
