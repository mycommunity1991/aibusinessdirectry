# Walkthrough S08 MAT-001

## Story: See Ranked Providers for My Request

**Sprint:** 08 | **Story ID:** MAT-001 | **Priority:** Critical | **Status:** Done

As a customer, I want the providers matched to my described need ranked by relevance and quality, so that the
best-fit options show up first. This story upgrades DIR-001's structured search into the AI-powered ranking
pipeline, consuming AI-002's structured Search Request output and combining it with the same category →
geospatial → discoverability filter chain, then ranking by proximity plus rating and review volume — never
distance alone. **Scope boundary:** does not include the actual contact/reveal step (`CON-001`) — this story
ends at a ranked results list.

Full context, the 3 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S08_MAT-001.md`.
Implementer notes from the backend agent were recorded in `docs/implementation/plans/Checkpoint_S08_MAT-001.md`,
which should be deleted per the Continuity & Checkpointing rule now that this story is complete and signed off
(see "Flagged, not fixed by this closeout" below for why it was not removed as part of this pass).

All work is committed to branch `claude/provider-storefront-pro-001-qnicuj` (head `2eab29c` at this closeout).

---

## What was implemented

No new migration, no new module — every table/column this story needed (`providers.average_rating`/
`review_count`, `provider_matches.match_score`) already existed. This story's entire scope is a ranking
**algorithm** (repository/service logic) plus five new config values, inside the already-shipped `provider` and
`search` modules.

### Backend (`backend/app/modules/provider/`, `backend/app/modules/search/`)

- **Config (Decision 1)** — `backend/app/core/config.py` gains five new `Settings` fields, the CTO-confirmed
  launch defaults: `RANKING_WEIGHT_PROXIMITY=0.6`, `RANKING_WEIGHT_RATING=0.3`, `RANKING_WEIGHT_REVIEW_VOLUME=0.1`,
  `RANKING_NEUTRAL_AVERAGE_RATING=3.0`, `RANKING_REVIEW_VOLUME_CAP=50`.
- **`ProviderSearchRepository` (Decision 1)** — `_SEARCH_NEARBY_SQL`'s `SELECT` gains a bounded `[0, 1]`
  `match_score` expression (proximity + rating + review-volume, all five settings bound as SQL parameters, never
  string-interpolated); `ORDER BY` changes from `distance_meters ASC, p.id ASC` to `match_score DESC, p.id ASC`.
  `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` are **byte-for-byte unchanged** — confirmed by direct diff during both
  `tester`'s and `architect`'s review, not merely asserted. `search_nearby(...)` gains the five new required
  parameters and returns a 4-tuple (`ordered_provider_ids`, `distances_by_id`, `total_items`,
  `scores_by_id: dict[uuid.UUID, float]`).
- **`ProviderService.search_nearby`** — thin pass-through, extended with the same five parameters, returns the
  extended 4-tuple.
- **`SearchService` (Decision 1)** — `search_providers` was refactored into a new shared entry point,
  `search_providers_ranked(...)` (reads the five `RANKING_*` settings, calls `provider_service.search_nearby`,
  returns the raw 4-tuple), plus a thin `search_providers(...)` wrapper (DIR-001's existing method) that calls it
  and discards `scores_by_id` when shaping `SearchResultProviderResponse` — no new field, `match_score` is never
  exposed to any API response. `search_providers_ranked` is the single method both DIR-001's `GET
  /search/providers` and `SearchRequestService._run_automated_match` now call.
- **`ProviderMatchRepository.bulk_create` (Decision 3)** — signature changed from
  `ranked_provider_ids: list[uuid.UUID]` to `ranked_matches: list[tuple[uuid.UUID, float | None]]`; `match_score`
  is the tuple's second element, written as-is, never re-derived.
- **`SearchRequestService` (Decision 3)** — `_run_automated_match` now calls `search_providers_ranked(...)` and
  returns real `(provider_id, match_score)` tuples using the formula's actual output; `resolve_manual_match`
  continues to build `(provider_id, None)` pairs for every admin-ordered row — an admin's own judgment is never
  assigned a fabricated score.
- **Doc-only bug found and fixed:** a stale "nearest-first" OpenAPI/docstring reference in
  `backend/app/modules/search/api.py` (a leftover description of DIR-001's original, since-superseded ordering)
  was corrected to describe merit-ranked ordering — no functional change.
- **Mobile comment fix:** the one stale code comment in `mobile/lib/features/search/data/search_repository.dart`
  ("results... are ordered nearest-first by the backend") was corrected to describe merit-ranked ordering — no
  widget/functional change.

### Tests

- `backend/tests/modules/provider/test_provider_search_repository.py` — a new `TestMeritRanking` class, 5 tests:
  a farther-but-higher-rated provider outranking a closer-but-unrated one, asserting both the id order and the
  exact formula value (AC3/AC8); an exact-tie-on-rating/distance fixture proving `id ASC` re-anchored to the new
  score (AC4); a regression fixture proving uniform-(null)-rating candidates preserve the pre-existing
  nearest-first order (Decision 1's "Consequences" claim, proven, not just asserted); and two formula-bounds
  tests added during independent test review — a perfect provider (5.0 rating, 50+ reviews, zero distance)
  scoring at or near the formula's true ceiling of `1.0`, and a worst-case provider (unrated, zero reviews, at
  the radius edge) confirmed to floor at `weight_rating * (neutral_average_rating / 5.0) = 0.18`, never at `0`
  outright — proving the neutral-default design decision holds at the formula's actual boundary, not just in the
  middle of its range.
- `backend/tests/modules/search/test_search_service.py` — a new `TestMeritRankingWiring` class, 2 tests: the
  five `RANKING_*` settings are passed through as kwargs to `provider_service.search_nearby`; `search_providers`'s
  response order is exactly whatever order `provider_service.search_nearby` returns, proving `search_providers`
  never re-sorts by distance or anything else itself. No pre-existing test in this file needed its expected order
  changed — every fixture here used uniform rating/review_count across providers.
- `backend/tests/modules/search/test_search_endpoints.py` — a new `TestMeritRankingChangesDirOwnEndpointOrder`
  class: a real HTTP round trip against `GET /api/v1/search/providers` with a deliberately non-uniform
  farther-but-top-rated-vs-closer-unrated fixture, proving DIR-001's own endpoint's result order genuinely
  changes under the new formula — direct proof through the real endpoint, not an inference from the
  repository-layer tests alone. Also asserts `match_score` is never present in the response body.
- `backend/tests/modules/search/test_search_request_service.py` — a new `TestMeritRankingPersistence` class,
  2 tests: the automated path writes a non-`null`, `[0, 1]`-bounded `match_score` for every `provider_matches`
  row; a farther-but-higher-rated-vs-closer-unrated fixture proves `get_matched_providers`'s final customer-facing
  order reflects merit-ranking end to end. The existing manual-path test was extended with an explicit
  `match_score is None` assertion for every row (Decision 3's regression guard).
- `backend/tests/modules/conversation/test_conversation_api.py` — a new
  `TestAC5ConversationCompletionFlowsIntoRankedResults` class: a genuine multi-turn HTTP round trip (`POST
  /conversations` → `POST /conversations/{id}/messages` ×2 → `GET /search-requests/{id}`), never a synthetic
  `handle_session_completed(...)` service call, proving AC5's literal substance end to end. This closed a real
  coverage gap: the Plan's own Verified Current State had claimed AC5 was "already satisfied, zero new mobile
  work needed" by inspecting AI-001/AI-002's shipped mobile code, but no existing test anywhere in the codebase
  had actually driven a real conversation through to a ranked-results response — `test_conversation_service.py`'s
  multi-turn tests seed no default address/provider at all, and `search`'s own service/API tests call
  `handle_session_completed(...)` directly, never through a real conversation. This is the same shape of gap
  AI-001's own AC5 had (a claim of "already satisfied" that had never actually been exercised end to end).
- `backend/tests/modules/search/_helpers.py` — `create_discoverable_provider(...)` gained optional
  `average_rating: Decimal | None = None`, `review_count: int = 0` parameters (defaults preserve every
  pre-existing call site's behavior unchanged).

---

## The Architecture Decisions, as actually shipped

All 3 decisions from `Plan_S08_MAT-001.md` shipped exactly as planned:

1. **Merit-ranking formula, computed in-place inside `ProviderSearchRepository`'s existing shared query** — a
   bounded `[0, 1]` composite (proximity + rating + review-volume, all five weights `Settings`-driven), never a
   second, parallel ranking implementation. `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` stayed byte-for-byte unchanged.
   Recorded as `09_DECISIONS.md` ADR-042.
2. **Rating source: `providers.average_rating`/`review_count`, not the unbuilt `provider_rating_summaries`
   table** — a deliberate, flagged substitution of AC3's literally-named data source, since the Review domain is
   structurally impossible to build meaningfully before `CON-001` ships. Recorded as ADR-043.
3. **`provider_matches.match_score` real for the automated path, `NULL` for the manual path** — an admin's own
   ordering is never assigned a fabricated formula-derived score. Recorded as part of ADR-043.

This story required **zero DIR-001 test order-updates**: every existing `test_search_service.py` fixture used
uniform rating data across candidates, so the new formula reduced to the old distance-only order for all of
them, exactly as Decision 1's "Consequences" section predicted. It also required **zero frontend/mobile work**:
AC5 was already satisfied by AI-002's shipped mobile screens (`AiConversationScreen`'s resolved-results state
rendering the shared `RankedProviderResultsList` widget) — this closeout's job was to confirm that end to end
with a real test, not to build anything new.

---

## Review Process — a full, honest account

### `tester` — independent verification against real HTTP round trips, plus a genuine coverage gap closed

The tester independently verified all 8 verbatim ACs with real DB/HTTP round trips, and found no functional
bugs — but identified a genuine gap in the Plan's own verification posture, not a code defect:

- **AC5's "already satisfied, zero new mobile work needed" claim had never actually been proven end to end.**
  The Plan's Verified Current State section reasoned correctly from reading AI-001/AI-002's shipped mobile code
  that no new frontend work was needed, but no automated test anywhere in the codebase had driven a real,
  multi-turn conversation through to a ranked-results response via the real HTTP API. The tester added
  `TestAC5ConversationCompletionFlowsIntoRankedResults` (`test_conversation_api.py`) to close this — a real
  `POST /conversations` → two turns → `GET /search-requests/{id}` round trip against a genuine
  farther-but-higher-rated-vs-closer-unrated fixture, confirming both AC5 (conversation flows directly into
  ranked results, no manual re-search) and the merit-ranking formula's effect on the final customer-facing order.
- **DIR-001's own endpoint order had never been proven to actually change** under non-uniform rating data,
  despite ADR-042/Decision 1 explicitly making that endpoint's changed order a stated, in-scope consequence. The
  tester added `TestMeritRankingChangesDirOwnEndpointOrder` (`test_search_endpoints.py`) — a real HTTP round trip
  against `GET /api/v1/search/providers` with a deliberately non-uniform rating fixture, directly proving the
  order genuinely changes for DIR-001's own path, not only inferring it from the repository-layer tests.
- **The formula's bounds had only been tested in the middle of its range**, not at its actual ceiling/floor. The
  tester added two tests to `TestMeritRanking` (`test_provider_search_repository.py`): a "perfect provider"
  fixture (top rating, review count at the cap, zero distance) confirming the score reaches its true ceiling of
  `1.0`; and a "worst-case" fixture (unrated, zero reviews, at the radius edge) confirming the score floors at
  `0.18` (the neutral-rating term alone), never at `0` outright — directly proving the neutral-default design
  decision holds at the formula's actual boundary.
- **A trivial doc-only bug**: a stale "nearest-first" OpenAPI/docstring description in
  `backend/app/modules/search/api.py`, left over from DIR-001's original, since-superseded behavior. Corrected —
  no functional change.

No DIR-001 test's expected order needed updating (every existing fixture used uniform rating data), and no
regression was found anywhere in the existing suite.

### `architect` — clean review, zero findings

The architect reviewed Decision 1's in-place query change (the SQL score expression's bounds, the
parameterization/security posture of the five new bound values, and a direct diff confirming `_WHERE_CLAUSE`
truly did not change), Decision 2's rating-source substitution against `00_PROJECT_CONTEXT.md` §3's
anti-fabrication principle and against prematurely building Review-domain schema, Decision 3's
`NULL`-for-manual-path honesty, and confirmed no new cross-module edge was introduced. One documentation-only
observation was flagged, not a code finding: `providers.average_rating` has no DB-level `CHECK` constraint
enforcing the 0–5 rating range today — noted for a future `REV-001` write path to address, recorded in
`04_DATABASE.md` at this closeout, not a schema change for this story.

**Final verdict: APPROVED, zero findings — the cleanest review this project has had.**

### Final verdicts

- **`tester`**: all 8 ACs independently verified; no functional bugs found; a genuine end-to-end coverage gap for
  AC5 closed, plus a DIR-001-order-change proof and formula-bounds tests added; one trivial doc-only bug (stale
  OpenAPI text) found and fixed.
- **`architect`**: **APPROVED, zero findings.**
- **CTO sign-off** received after both verdicts were presented, per standing process.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `search_requests` and `provider_matches` tables exist via migration; `provider_matches` stores rank and match_score per provider per request | Pass — tables already existed (AI-002); `match_score` is now genuinely non-null for automated matches, confirming the column is actually used, not merely present |
| 2 | Filter order is identical to DIR-001's (category, then geospatial radius, then discoverability) — no second, divergent filter implementation | Pass — `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` confirmed byte-for-byte unchanged by direct diff |
| 3 | Ranking combines proximity with rating and review count, never distance alone | Pass — bounded `[0, 1]` composite formula, proven against known rating/distance combinations at both the repository and service layers, and through a real HTTP round trip against DIR-001's own endpoint |
| 4 | Ranking ties break deterministically (e.g., by `provider_id`) | Pass — a genuine exact-tie fixture asserting `id ASC` re-anchored to the new `match_score`-based order |
| 5 | Search Results screen consumes AI-001's conversation output directly — no manual re-search step | Pass — proven end to end via a real multi-turn HTTP conversation flow into `GET /search-requests/{id}`, closing a gap where this claim had previously only been inferred from reading shipped mobile code, never tested |
| 6 | Every search, matched or not, is written to `search_event_log` with an accurate `was_matched` flag | Pass — already true by construction (AI-002's `_finalize_matches`), re-verified unchanged |
| 7 | A provider with `is_discoverable=false` never appears in ranked results | Pass — `_WHERE_CLAUSE`'s discoverability clause confirmed unchanged |
| 8 | Automated tests cover ranking correctness against known rating/distance combinations and deterministic tie-breaking | Pass — repository-level, service-level, and end-to-end HTTP coverage, plus formula-bounds tests at the ceiling and floor |

**8 of 8 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded two new ADRs, ADR-042 (the in-place merit-ranking query upgrade,
  shared by DIR-001 and the AI-conversation path) and ADR-043 (the rating-source substitution and the
  real-vs-`NULL` `match_score` split between the automated and manual paths).
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 14 added: `provider_rating_summaries` remains unbuilt and unused; a
  future `REV-001` should decide whether it's still needed as a distinct table once real reviews exist, or
  whether `providers.average_rating`/`review_count` alone is sufficient.
- **`docs/AI/04_DATABASE.md`** — a cross-reference note added under `provider_rating_summaries`'s existing spec
  (Review Domain section), stating it remains fully unbuilt and that `MAT-001`'s ranking formula instead reads
  `providers.average_rating`/`review_count`, cross-referencing ADR-043; also records the architect's
  documentation-only note that `providers.average_rating` has no DB-level `CHECK` constraint for the 0–5 range
  today, flagged for a future `REV-001` write path.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 8 section added, Milestone ML8 marked started (1 of 2
  stories done: `MAT-001`; `CON-001` is next, gated on an explicit CTO "Start CON-001").
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `MAT-001`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect `MAT-001` shipped, `CON-001` as the sole next candidate,
  ADR numbering advanced to ADR-043, and item 14 added to the Open Decisions summary.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `MAT-001` row** still needs its Status updated to "Done" and rolled up
  through ML8-EP01/ML8/SP08/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure, not performed by this closeout.
- **`13_OPEN_DECISIONS.md` item 14** (whether `provider_rating_summaries` is still needed once real reviews
  exist) remains genuinely open — this story surfaces the question, it does not answer it; that is `REV-001`'s
  job.
- **`CON-001`** ("contact a matched provider directly") is the next story in this epic (ML8-EP02), depends on
  `MAT-001`, and remains unplanned/unstarted, gated on an explicit CTO "Start CON-001" instruction.
- **A real merit signal beyond the neutral placeholder** remains unbuilt — every provider today has
  `average_rating IS NULL`/`review_count=0` in production, since the Review domain hasn't shipped; the formula
  is genuinely ready for real data the moment `REV-001` ships it, but ranks purely on proximity in practice today
  (Decision 1's "Consequences," proven by this story's own regression tests).

---

## Testing Performed

- `backend` implementation, extending `test_provider_search_repository.py`, `test_search_service.py`,
  `test_search_request_service.py`, and `_helpers.py`. Backend's own Checkpoint reported the full suite green
  (665/665 passed) immediately after implementation, before the tester's own additional coverage below.
- `tester` agent: all 8 ACs independently verified with real DB/HTTP round trips; added
  `TestMeritRankingChangesDirOwnEndpointOrder` (`test_search_endpoints.py`),
  `TestAC5ConversationCompletionFlowsIntoRankedResults` (`test_conversation_api.py`), and two formula-bounds
  tests to `TestMeritRanking` (`test_provider_search_repository.py`); found and fixed one trivial doc-only bug
  (stale "nearest-first" OpenAPI text in `search/api.py`). No functional regressions found anywhere in the
  existing suite.
- `architect` agent: single review pass — **APPROVED, zero findings.** One documentation-only observation
  (`providers.average_rating` has no DB-level `CHECK` constraint) recorded in `04_DATABASE.md` at this closeout,
  not treated as a finding requiring a code change for this story.
- User (CTO) sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/app/core/config.py` (five new `RANKING_*` settings)
- `backend/app/modules/provider/repositories/provider_search_repository.py` (the `match_score` expression and
  `ORDER BY` change; `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` unchanged)
- `backend/app/modules/provider/services/provider_service.py` (`search_nearby` thin pass-through extension)
- `backend/app/modules/search/services/search_service.py` (`search_providers_ranked`, the new shared entry
  point)
- `backend/app/modules/search/services/search_request_service.py` (`_run_automated_match` now writes real
  `match_score`)
- `backend/app/modules/search/repositories/provider_match_repository.py` (`bulk_create`'s new tuple signature)
- `backend/app/modules/search/api.py` (stale OpenAPI text fix)
- `backend/tests/modules/provider/test_provider_search_repository.py` (`TestMeritRanking`, 5 tests)
- `backend/tests/modules/search/test_search_service.py` (`TestMeritRankingWiring`, 2 tests)
- `backend/tests/modules/search/test_search_request_service.py` (`TestMeritRankingPersistence`, 2 tests)
- `backend/tests/modules/search/test_search_endpoints.py` (`TestMeritRankingChangesDirOwnEndpointOrder`)
- `backend/tests/modules/conversation/test_conversation_api.py`
  (`TestAC5ConversationCompletionFlowsIntoRankedResults`)
- `backend/tests/modules/search/_helpers.py` (`average_rating`/`review_count` fixture parameters)

### Mobile
- `mobile/lib/features/search/data/search_repository.dart` (stale comment fix only — no functional/widget
  change)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-042, ADR-043
- `docs/AI/13_OPEN_DECISIONS.md` — item 14
- `docs/AI/04_DATABASE.md` — `provider_rating_summaries` cross-reference note
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 8 / Milestone ML8 section
- `docs/AI/SESSION_HANDOFF.md` — refreshed state
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 8 (Matching / Contact) is now 1 of 2 stories done** (`MAT-001`). `CON-001` ("contact a matched
  provider directly," ML8-EP02) is the next story in this epic, depends on `MAT-001`, and is the sole next
  candidate — not planned or started by this closeout, gated on an explicit CTO "Start CON-001" instruction.
- **`13_OPEN_DECISIONS.md` item 14** (whether `provider_rating_summaries` is still needed once real reviews
  exist) is now a real, documented design question for a future `REV-001` — this story surfaces it, does not
  resolve it.
- **The merit-ranking formula is genuinely ready for real data**, not a placeholder dressed up as more precise
  than it is: the moment a future `REV-001` writes real `providers.average_rating`/`review_count` values, no
  `ProviderSearchRepository`/`SearchService`/`SearchRequestService` code needs to change again to start ranking
  on real signal — this is the pattern's stated design intent (ADR-042), worth keeping in mind for `REV-001`'s
  own planning.
- **`docs/AI/Project_Tracker.xlsx`'s `MAT-001` row** still needs its Status flipped to "Done" and rolled up
  through ML8-EP01/ML8/SP08/the Phase Tracker/the Dashboard — per standing process, handled separately via the
  CTO's own raw-XML procedure, not performed by this closeout.
- **`docs/implementation/plans/Checkpoint_S08_MAT-001.md` still needs to be deleted** per the Continuity &
  Checkpointing rule — this closeout pass had Read/Write/Edit/Grep/Glob tools only, with no file-deletion
  capability, so the file could not be removed here despite the story being complete and signed off.

---

**End of Document**
