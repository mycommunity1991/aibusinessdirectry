# Checkpoint — Sprint 08, Story MAT-001 (See Ranked Providers for My Request)

**Written by:** `backend` agent
**Status:** Backend implementation complete. Full backend test suite green (665/665
passed, 0 failures, 0 errors). `ruff check`/`ruff format --check` clean on the full
`backend/` tree. Not yet handed to `tester`/`architect`.

---

## Current Task

Implement the backend half of MAT-001 per `docs/implementation/plans/Plan_S08_MAT-001.md`.
No new migration, no new module — all changes are within the already-shipped `provider`
and `search` modules (Decision 1: modify `ProviderSearchRepository`'s existing
`_SEARCH_NEARBY_SQL` in place; Decision 2: rank using `providers.average_rating`/
`review_count`, not the unbuilt `provider_rating_summaries` table; Decision 3:
`provider_matches.match_score` becomes real for the automated path, stays `NULL` for
the manual path).

## What's Done (backend, complete)

1. **Config** — `backend/app/core/config.py`: added `RANKING_WEIGHT_PROXIMITY: float =
   0.6`, `RANKING_WEIGHT_RATING: float = 0.3`, `RANKING_WEIGHT_REVIEW_VOLUME: float =
   0.1`, `RANKING_NEUTRAL_AVERAGE_RATING: float = 3.0`, `RANKING_REVIEW_VOLUME_CAP: int
   = 50` — the CTO-confirmed launch defaults.
2. **Repository (Decision 1)** — `backend/app/modules/provider/repositories/
   provider_search_repository.py`: `_SEARCH_NEARBY_SQL`'s `SELECT` gains the bounded
   `[0,1]` `match_score` expression; `ORDER BY` changed to `match_score DESC, p.id ASC`.
   `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` are **byte-for-byte unchanged** — confirmed via
   `git diff` showing zero touched lines in that constant. `search_nearby(...)` gains
   five new required parameters (`weight_proximity`, `weight_rating`,
   `weight_review_volume`, `neutral_average_rating`, `review_volume_cap`, all bound SQL
   parameters) and now returns a 4-tuple: `(ordered_provider_ids, distances_by_id,
   total_items, scores_by_id)`.
3. **Repository-level tests** — `backend/tests/modules/provider/
   test_provider_search_repository.py`: all 10 pre-existing `search_nearby(...)` call
   sites updated to the new signature/4-tuple unpacking (ran `ruff format` to normalize
   indentation after a scripted edit); the `EXPLAIN` raw-SQL test's bind-params dict
   extended with the five new keys. Added a new `TestMeritRanking` class (3 new tests,
   AC3/AC4/AC8): a farther-but-higher-rated provider outranks a closer-but-unrated one
   (asserts both the id order and the exact `match_score` formula value); an
   exact-tie-on-rating/distance fixture proving `id ASC` tie-break re-anchored to the
   new score; a regression fixture proving uniform-(null)-rating candidates preserve
   the pre-existing nearest-first order (Decision 1's "Consequences" claim, proven not
   just asserted). **13/13 tests pass** in this file (10 pre-existing + 3 new).
4. **`ProviderService.search_nearby`** — `backend/app/modules/provider/services/
   provider_service.py`: thin pass-through extended with the same five parameters;
   returns the extended 4-tuple, preserving hydration/id-order-reconstruction logic
   unchanged.
5. **`SearchService`** — `backend/app/modules/search/services/search_service.py`:
   refactored `search_providers` into a new `search_providers_ranked(...)` method
   (reads the five `RANKING_*` settings, calls `provider_service.search_nearby`,
   returns the raw 4-tuple) plus a thin `search_providers(...)` wrapper that calls it
   and discards `scores_by_id` when shaping `SearchResultProviderResponse` (no new
   field — `match_score` is never exposed to any API response). This
   `search_providers_ranked` method is the single shared entry point both DIR-001's
   `GET /search/providers` and `SearchRequestService._run_automated_match` now call —
   avoids reaching into a private method across service instances (rejected an earlier
   draft that called `search_service._validate_radius` directly).
6. **`SearchService` tests** — `backend/tests/modules/search/test_search_service.py`:
   updated `mock_provider_service.search_nearby`'s return value at all 7 call sites
   (3-tuple → 4-tuple). Added a new `TestMeritRankingWiring` class (2 new tests): one
   asserting the five `RANKING_*` settings are passed through as kwargs to
   `provider_service.search_nearby`; one asserting `search_providers`'s response order
   is exactly whatever order `provider_service.search_nearby` returns (a
   farther-but-higher-rated provider mocked first in the return value ends up first in
   the response) — proves `search_providers` never re-sorts by `distance_meters` or
   anything else itself. **No pre-existing test's expected order needed changing** —
   every existing fixture in this file used a single provider or identical
   rating/review_count across providers, so the new ranking formula is mathematically
   equivalent to the old distance-only order for all of them (Decision 1's
   "Consequences" claim held in practice for this file). **16/16 tests pass** (14
   pre-existing + 2 new).
7. **`ProviderMatchRepository.bulk_create` (Decision 3)** —
   `backend/app/modules/search/repositories/provider_match_repository.py`: signature
   changed from `ranked_provider_ids: list[uuid.UUID]` to `ranked_matches:
   list[tuple[uuid.UUID, float | None]]`; `match_score` is now the tuple's second
   element, written as-is (real score or `None`), never re-derived.
8. **`SearchRequestService`** — `backend/app/modules/search/services/
   search_request_service.py`: `_run_automated_match` now calls
   `search_service.search_providers_ranked(...)` (reading the same five `RANKING_*`
   settings) and returns `list[tuple[uuid.UUID, float | None]]` using the real
   `scores_by_id`; `_handle_completed`/`_finalize_matches` carry the tuple list through
   to `provider_match_repository.bulk_create`; `resolve_manual_match` builds
   `[(provider_id, None) for provider_id in provider_ids]` before calling
   `_finalize_matches` (the admin's own order is the rank, never a fabricated score).
9. **`SearchRequestService` tests** — `backend/tests/modules/search/
   test_search_request_service.py`: added a `TestMeritRankingPersistence` class (2 new
   tests) — the automated path writes a non-`null`, `[0,1]`-bounded `match_score` for
   every `provider_matches` row; a farther-but-higher-rated-vs-closer-unrated fixture
   proves `get_matched_providers`'s final customer-facing order reflects merit-ranking
   end to end (not just at the repository layer). Extended the existing
   `test_resolving_with_provider_ids_produces_matched_and_ranked_matches` test (manual
   path) with an explicit `match_score is None` assertion for every row (Decision 3's
   regression guard) rather than adding a new, separate test — this is the existing,
   most direct test of the manual path's write behavior. **15/15 tests pass** (13
   pre-existing + 2 new).
10. **Test helper** — `backend/tests/modules/search/_helpers.py`:
    `create_discoverable_provider(...)` gained optional `average_rating: Decimal |
    None = None`, `review_count: int = 0` parameters (defaults preserve every
    pre-existing call site's behavior unchanged).
11. **Docstrings** updated in all touched files to describe the new merit-ranking
    behavior and cross-reference `Plan_S08_MAT-001.md`/the relevant Decision numbers.

## Explicitly NOT done (out of this agent's role boundary — flagged, not actioned)

- **Item 7 of the Plan's Backend Proposed Changes**: the stale code comment in
  `mobile/lib/features/search/data/search_repository.dart` ("results... are ordered
  nearest-first by the backend — this method never re-sorts them") still needs
  correcting to describe merit-ranked ordering instead. This is a comment-only,
  no-functional-change edit, but `mobile/` is outside this agent's (`backend`) file
  boundary (`app/.agents/agents.md`/this session's own system-prompt boundary: "Only
  create, edit, or delete files inside `backend/`... Never touch `mobile/`"). Needs a
  `frontend`-role pass, or explicit user approval to cross the boundary.
- **Documentation updates** the Plan's Delegation section assigns to post-sign-off
  `tech-lead` work (new ADR-042+ entries in `docs/AI/09_DECISIONS.md`,
  `04_DATABASE.md`'s `provider_rating_summaries` cross-reference note,
  `13_OPEN_DECISIONS.md` item 14, `PROJECT_IMPLEMENTATION_STATE.md`/
  `SESSION_HANDOFF.md`) — all outside `backend/`, correctly deferred per the Plan's own
  sequencing (after user sign-off), not this agent's task.

## Verification Run

- `cd backend && source .venv/bin/activate && python -m pytest -q` → **665 passed, 1
  warning (pre-existing `httpx`/`starlette.testclient` deprecation warning,
  unrelated), 0 failures, 0 errors.** (658 baseline + 7 new: 3 repository-level, 2
  `SearchService`-level, 2 `SearchRequestService`-level.)
- `ruff check .` (full `backend/` tree) → all checks passed.
- `ruff format --check .` (full `backend/` tree) → the two files this story touched
  needed reformatting after a scripted multi-site edit (`search_request_service.py`,
  `test_search_request_service.py`) — both reformatted with `ruff format` and
  re-verified clean, and their test files re-run green afterward (15/15). Three
  **other, pre-existing** files also showed as needing reformatting
  (`app/modules/category/dependencies.py`, `tests/modules/category/
  test_category_service.py`, `tests/modules/search/
  test_claim_unclaimed_visibility_integration.py`) — **not touched by this story**,
  confirmed via `git diff` (no changes in this session touch those files); left as-is,
  pre-existing lint debt outside this story's scope.
- No mypy run: this project's `pyproject.toml` `[dependency-groups].dev` does not
  include `mypy` (only `pytest`, `pytest-asyncio`, `ruff`) — not installed in the
  venv, not part of this project's standing toolchain.
- Postgres/Redis were both stopped at session start; started both
  (`service postgresql start`, `service redis-server start`) to run the suite — left
  running.

## What's Explicitly Next

1. Orchestrator/top-level session: hand off to `tester` to verify all 8 verbatim ACs
   with real DB/HTTP round trips per the Plan's Verification Plan table, and to
   `architect` for the Decision 1/2/3 review (SQL bounds/parameterization,
   `_WHERE_CLAUSE` truly unchanged, anti-fabrication check on Decision 2/3, no new
   cross-module edge).
2. Someone with `mobile/` write access (a `frontend`-role pass, or explicit user
   approval) needs to apply the one-line stale-comment fix in
   `mobile/lib/features/search/data/search_repository.dart` (item 7 above).
3. Once `tester`/`architect` are clean and the user signs off, `tech-lead` records
   Decision 1/2 as new ADRs (ADR-042 onward), updates `04_DATABASE.md`'s
   `provider_rating_summaries` cross-reference note, optionally adds
   `13_OPEN_DECISIONS.md` item 14, and updates `PROJECT_IMPLEMENTATION_STATE.md`/
   `SESSION_HANDOFF.md` — all outside this agent's boundary.

## Open Questions / Notes for Next Agent

- The Plan's three Open Questions (Decision 2's rating-source substitution, Decision
  1's in-place upgrade of DIR-001's shipped endpoint, and the specific 0.6/0.3/0.1/3.0/
  50 default values) are marked in the orchestrator's task prompt as **CTO-confirmed
  launch defaults** — treated as already-approved for this implementation pass, not
  re-litigated here.
- `docs/AI/04_DATABASE.md` documents `providers.average_rating`/`review_count` as
  "Denormalized from `review.reviews`; recalculated on Review write" (lines 405-406) —
  confirms Decision 2's choice is consistent with this doc's own already-stated intent
  for a future `REV-001`; no drift introduced by this story.
