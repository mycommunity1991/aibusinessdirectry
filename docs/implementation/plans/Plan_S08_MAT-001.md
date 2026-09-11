# Plan for Story MAT-001 — See Ranked Providers for My Request

**Sprint:** 08 (Matching / Contact) | **Epic:** ML8-EP01 | **Milestone:** ML8 | **Phase:** PH2 | **Priority:**
Critical | **Depends On:** AI-002 (done, Sprint 7)

---

## Story (verbatim, `Project_Tracker.xlsx`, `MAT-001` row — relayed by the orchestrator this session)

"As a customer, I want the providers matched to my described need ranked by relevance and quality, so that the
best-fit options show up first. This story upgrades DIR-001's structured search into the AI-powered ranking
pipeline, consuming AI-002's structured Search Request output and combining it with the same category →
geospatial → discoverability filter chain, then ranking by proximity plus rating and review volume — never
distance alone. Scope boundary: does not include the actual contact/reveal step (CON-001) — this story ends at a
ranked results list."

## Acceptance Criteria (verbatim, 8 items)

1. `search_requests` and `provider_matches` tables exist via migration; `provider_matches` stores rank and
   match_score per provider per request.
2. Filter order is identical to DIR-001's (category, then geospatial radius, then discoverability) — this story
   does not introduce a second, divergent filter implementation.
3. Ranking combines proximity with `provider_rating_summaries` (average rating and review count) and is never
   based on distance alone.
4. Ranking ties break deterministically (e.g., by `provider_id`) so identical searches return stable,
   reproducible ordering.
5. Search Results screen consumes AI-001's conversation output directly — Home's search entry point starts a
   Conversation Session, which flows into this screen without a manual re-search step.
6. Every search, matched or not, is written to `search_event_log` with an accurate `was_matched` flag.
7. A provider with `is_discoverable=false` never appears in ranked results, mirroring DIR-001's rule.
8. Automated tests cover ranking correctness against known rating/distance combinations and deterministic
   tie-breaking.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **AC1, AC2, AC6, AC7 are already fully satisfied by `AI-002`'s shipped code — no new schema or filter work
  needed, only regression verification.** Confirmed directly against `backend/app/modules/search/models.py`,
  `services/search_request_service.py`, and `backend/app/modules/provider/repositories/
  provider_search_repository.py`:
  - `search.search_requests`/`provider_matches`/`search_event_log` exist via the real migration
    `2026_09_10_1100-f3a1c9d47b02_search_domain_and_manual_match_...py` (head as of this Plan). `provider_matches`
    already has `rank SMALLINT NOT NULL` and `match_score NUMERIC(5,4) NULL` — AC1's literal schema requirement
    is met; only `match_score` is currently always written `NULL` (`ProviderMatchRepository.bulk_create`,
    `AI-002` Decision 5/ADR-041) — the gap this story closes.
  - `ProviderSearchRepository._WHERE_CLAUSE` (the single, shared string constant used by both the row query and
    its `COUNT` variant) applies category → geospatial radius (`earth_box` GiST pre-filter, then exact
    `earth_distance`) → `is_discoverable`/`is_active`, in that literal order, with a code comment stating this
    order is "load-bearing, not cosmetic (AC2)". `SearchRequestService._run_automated_match` calls this same
    query, unchanged, via `SearchService`/`ProviderService.search_nearby` (`AI-002` ADR-041, Decision 5) — AC2 is
    already true by construction, not by convention.
  - `SearchRequestService._finalize_matches` is confirmed as the **only** place in the codebase that writes
    `provider_matches`/`search_requests.status`/`search_event_log`, called identically from both the automated
    and manual-resolution paths (`AI-002` Decision 4, ADR-040) — AC6 is already true, including for
    manually-resolved requests.
  - `_WHERE_CLAUSE`'s `AND p.is_discoverable = true AND p.is_active = true` clause, applied last, already
    satisfies AC7 — confirmed unchanged by this Plan's proposed edits (see Decision 1 below: only the query's
    `ORDER BY`/`SELECT` change, never `_WHERE_CLAUSE`).
- **AC4's literal example (tie-break "by provider_id") already exists today, but only for the current
  distance-only ordering.** `_SEARCH_NEARBY_SQL`'s `ORDER BY distance_meters ASC, p.id ASC` already gives
  deterministic tie-breaking for two providers at an identical distance (DIR-001, Decision 8). Once ranking
  becomes a composite score (Decision 1 below), this tie-break must be re-anchored to the new score column,
  which this Plan does explicitly (`ORDER BY match_score DESC, p.id ASC`).
- **AC5 is already fully satisfied by `AI-002`'s shipped mobile work — confirmed directly against
  `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` and `mobile/lib/features/
  conversation/presentation/screens/ai_conversation_screen.dart`.** Home's "aiConversationEntryPointLabel" button
  (`AI-001`, Decision 7) opens `AiConversationScreen` directly, which starts a Conversation Session; once that
  session's search request resolves (`matched`/`unmatched`), the **same screen's** `_ResolvedResultsView` renders
  the shared `RankedProviderResultsList` widget in place — no navigation to a separate screen, no manual
  re-search step, no distinguishing "AI" vs. "manual" origin (`AI-002` Decision 6, Mobile items 25–30). This
  satisfies AC5's substance (conversation output flows straight into a results view) even though the rendering
  widget lives inside `AiConversationScreen` rather than a literal, separately-named "Search Results screen" —
  the same shared `RankedProviderResultsList`/`ProviderResultCard` widgets DIR-001's own `SearchResultsScreen`
  (S-08) uses. **Conclusion: this story needs zero new mobile work for AC5.** If `tester`'s end-to-end pass finds
  a genuine gap here, that is a regression to report back, not a sign this Plan under-scoped frontend work.
- **`ProviderResultCard`/`RankedProviderResult` (mobile) already render `average_rating`/`review_count` per
  provider** ("No reviews yet" when `averageRating == null`, never a synthesized `0.0`) — confirmed directly. A
  ranking-order change with no new field is therefore invisible to mobile at the code level; no widget/schema
  change is needed on the client side for this story's ranking work either.
- **AC3's literal `provider_rating_summaries` table does not exist, and cannot exist yet — confirmed by two
  independent, converging facts, not assumed:**
  1. `04_DATABASE.md`'s Review Domain section (lines 811–839) fully specs `review.reviews` and
     `review.provider_rating_summaries`, but no `backend/app/modules/review/` directory exists anywhere in this
     repository (`Glob` returned zero files), and no migration creates the `review` schema. The domain is
     spec'd, not built — exactly the same shape of gap `AI-002`'s own ADR-041 already documented for this exact
     table ("the Review domain (`REV-001`) has not shipped, so `provider.provider_rating_summaries` is
     empty/all-zero placeholder data for every provider today").
  2. **The Review domain is structurally impossible to build, even minimally, before this story**, not merely
     unscheduled: `03_DOMAIN_MODEL.md`'s Review domain business rules require "A Review can only be created
     against a Contact View with a 'Yes' Outcome Tag" — i.e. a real `contact.contact_views` row (CON-001, not yet
     built) plus a real Outcome Tag mechanism (not yet built, not even named as a story anywhere in the visible
     tracker). CON-001 is the very next story after this one and itself explicitly depends on MAT-001. There is
     no code path, today or by the time this story ships, that could ever populate a real `reviews` row, which
     means a freshly-built `provider_rating_summaries` table would be permanently empty until at least two more
     stories ship — building it now would be pure premature schema, not a usable minimal stub.
- **A separate, already-existing, already-wired placeholder for rating data exists on `providers` itself**,
  confirmed directly in `backend/app/modules/provider/models.py`: `average_rating: Decimal | None` (nullable,
  `NUMERIC(3,2)`) and `review_count: int` (`NOT NULL`, default `0`), shipped by `PRO-001` (2026-09-08), long before
  any Review domain work. `04_DATABASE.md` line 405–406 documents these as "Denormalized from `review.reviews`;
  recalculated on Review write" — i.e. **`04_DATABASE.md` already assigns a future `REV-001` the job of writing
  to these exact columns**, independently of whether `provider_rating_summaries` is ever also populated. These
  columns are already read into every provider-facing response (`SearchResultProviderResponse`,
  `MatchedProviderResponse`) and are always `None`/`0` in production today (confirmed: no writer exists anywhere
  in the codebase for `average_rating`; `review_count` is only ever set to its `0` default at provider creation).
  This is the same honest, real, already-wired placeholder DIR-001 and AI-002 already display today — this story
  is the first to also **rank by** it, not just display it.
- **`04_DATABASE.md` itself appears to carry two overlapping denormalized-rating specs** (the `providers.
  average_rating`/`review_count` cache, and the separate `provider_rating_summaries` table, both described as
  "recalculated on/whenever a Review is written"). This looks like undocumented drift from the schema's evolution
  (the `provider_rating_summaries` section's own text says it "replaces" an earlier "ratings" placeholder from
  v2.0.0, but the `providers` table's own column notes were not correspondingly updated). This is not this
  story's decision to resolve (that is `REV-001`'s design question — which table is truly the source of truth vs.
  a read-optimization cache), but it directly informs the choice below: since both are equally denormalized,
  equally sourced from the same underlying `reviews` writes, and equally placeholder-empty today, using the one
  that **already exists and is already wired into this exact query path** is the correct interim choice, not an
  arbitrary substitution.
- **DIR-001's own Plan explicitly pre-announces this story as its own future upgrade path** — confirmed directly
  in `Plan_S06_DIR-001.md`: its AC5 states "Search Results screen is implemented in its structured (pre-AI) form,
  **ready to be upgraded to AI-ranked matching in a future story (MAT-001)**," and its own Decision text names
  "AC7... no merit/ranking algorithm of any kind" as a deliberate, temporary posture, explicitly citing MAT-001 as
  the story that adds it. This is direct, textual, prior-approved evidence that this story is expected to modify
  the **same, shared** `ProviderSearchRepository`/`SearchService` mechanism DIR-001 built and AI-002 reused
  unchanged — not to build a second, parallel ranking implementation that only the AI-conversation path uses.
  This directly informs Decision 1 below and is the strongest piece of evidence resolving how literally to read
  AC2's "does not introduce a second, divergent filter implementation."
- **No customer-facing "sort by" control exists anywhere in the mobile search UI** (confirmed:
  `mobile/lib/features/search/data/search_repository.dart`'s only related text is a code comment, "results... are
  ordered nearest-first by the backend — this method never re-sorts them," not a UI element). Changing the
  backend's ranking order is therefore a pure backend change with no UI to update, only a stale code comment to
  correct (Decision 1's Backend Proposed Changes list this explicitly).
- **No new Alembic migration is needed for this story.** Every table/column AC3/AC8 need already exists
  (`providers.average_rating`/`review_count`, `provider_matches.match_score`) — this story's real work is a
  ranking **algorithm** (service/repository logic) plus new `Settings` values, not new schema. Current migration
  head is `f3a1c9d47b02` (`search_domain_and_manual_match_...`) — unchanged by this Plan.

---

## Architecture Decisions

### Decision 1 — Merit-ranking formula, computed in-place inside the existing, shared `ProviderSearchRepository.search_nearby` query — not a second, parallel ranking implementation

**The problem:** AC3 requires ranking that "combines proximity with... average rating and review count," never
distance alone, and AC4 requires deterministic tie-breaking on the resulting order. The ranking must apply
identically to both callers of the shared matching query — DIR-001's own `GET /search/providers` (per its own
pre-announced AC5, see Verified Current State) and `SearchRequestService._run_automated_match` (AI-002/this
story) — without duplicating the filter chain AC2 protects.

**Chosen:** modify `ProviderSearchRepository`'s existing `_SEARCH_NEARBY_SQL` query **in place** — `_WHERE_CLAUSE`
stays byte-for-byte unchanged (AC2's guarantee is now provably true: the same shared string constant, unmodified,
still gates both the row query and its `COUNT` twin) — and change only the `SELECT`/`ORDER BY` to compute and
sort by a bounded, deterministic composite score:

```
match_score =
      :weight_proximity      * (1.0 - (distance_meters / :radius_meters))
    + :weight_rating         * (COALESCE(p.average_rating, :neutral_average_rating) / 5.0)
    + :weight_review_volume  * (LEAST(p.review_count, :review_volume_cap)::numeric / :review_volume_cap)

ORDER BY match_score DESC, p.id ASC
```

Every term is bound to `[0, 1]` by construction: `distance_meters <= :radius_meters` is already guaranteed by
`_WHERE_CLAUSE`'s own `earth_distance(...) <= :radius_meters` condition, `average_rating` is on a 1–5 scale (or
the config neutral default when `NULL`), and `review_count` is capped before normalizing. With the default
weights (Decision 1's config values, below) summing to `1.0`, `match_score` itself is always in `[0, 1]` and fits
`provider_matches.match_score NUMERIC(5,4)` comfortably. `p.id ASC` is the final, literal AC4 tie-break, now
anchored to the new score instead of raw distance.

`ProviderSearchRepository.search_nearby(...)` gains five new required parameters (`weight_proximity,
weight_rating, weight_review_volume, neutral_average_rating, review_volume_cap` — all plain `float`/`int`, bound
as parameters, mirroring this file's existing "every caller-influenced value is a bound parameter" security
posture) and returns one new value: `scores_by_id: dict[uuid.UUID, float]`, alongside the existing
`ordered_provider_ids`/`distances_by_id`/`total_items`. `ProviderService.search_nearby` passes these through
unchanged (thin pass-through, per its own docstring's existing framing) and returns the extended tuple.
`SearchService.search_providers` (DIR-001) reads the five new values from `settings` itself and passes them
down, but **discards** the returned `scores_by_id` — `SearchResultProviderResponse` gains no new field, since no
AC (DIR-001's or this story's) asks to expose a raw score to the structured-browse customer.
`SearchRequestService._run_automated_match` also reads the same `settings` values and **uses** the returned
scores to populate `provider_matches.match_score` for the first time (see Decision 3).

**Config, not schema** (mirrors `CONVERSATION_CONFIDENCE_THRESHOLD`/`AI_MATCH_MAX_RESULTS`'s established
precedent — a business-tunable numeric input, not a hardcoded constant or a new column): five new `Settings`
fields.

| Setting | Default | Reasoning |
|---|---|---|
| `RANKING_WEIGHT_PROXIMITY` | `0.6` | Proximity remains the dominant, always-real signal today (rating/volume are currently placeholder for every provider) — weighted highest so today's real customer experience does not regress relative to DIR-001/AI-002's existing nearest-first behavior on equal-rating data (see "Consequences" below for the proof this holds). |
| `RANKING_WEIGHT_RATING` | `0.3` | Second-highest — the literal AC3 signal this story exists to add. |
| `RANKING_WEIGHT_REVIEW_VOLUME` | `0.1` | Smallest — review *volume* is a confidence multiplier on the rating signal, not an independent quality signal on its own (a provider with 1 five-star review should not automatically outrank one with a real, larger sample at 4.5). |
| `RANKING_NEUTRAL_AVERAGE_RATING` | `3.0` | The literal midpoint of the 1–5 rating scale — an unrated provider (`average_rating IS NULL`) is treated as neither better nor worse than a typical mid-scale rating, never assumed to be best (5) or worst (1). This is a single, fixed, transparent business constant applied identically to every unrated provider — not a fabricated per-provider value (`00_PROJECT_CONTEXT.md` §3's anti-fabrication principle is about inventing facts *about a specific record*; a documented, uniform default weight is a different, permitted thing, the same way `RANKING_REVIEW_VOLUME_CAP` and `AI_MATCH_MAX_RESULTS` are uniform, documented business constants). |
| `RANKING_REVIEW_VOLUME_CAP` | `50` | Diminishing returns after 50 reviews — an arbitrary but reasonable, clearly-documented business default; flagged as CTO-tunable, not derived from any locked spec. |

These five default values are **not** derived from any documented product requirement (none exists) — they are
this Plan's own defensible starting point, explicitly flagged in Open Questions below for CTO awareness before
`backend` starts, per this codebase's established practice of proceeding on a well-reasoned interim design while
flagging it plainly (mirrors AI-002 Decision 5's own posture) rather than blocking on a decision nobody has been
asked to make yet.

**Alternatives considered and rejected:**
- **A second, parallel ranking-only repository method (e.g. `search_nearby_ranked`), leaving DIR-001's own
  `search_nearby`/`GET /search/providers` completely untouched.** Rejected on direct, textual evidence: DIR-001's
  own `Plan_S06_DIR-001.md` AC5 explicitly names this exact upgrade as MAT-001's expected job ("ready to be
  upgraded to AI-ranked matching in a future story (MAT-001)"), and AC2's "does not introduce a second, divergent
  filter implementation" reads most literally as "the same query, not a second one" — a parallel method, even one
  reusing `_WHERE_CLAUSE`, would still be a second SQL statement/method, closer to the exact pattern AC2 warns
  against than the in-place upgrade is.
- **Compute the composite score in Python after fetching a wider, unranked candidate set, instead of in SQL.**
  Rejected: `LIMIT`/`OFFSET` pagination is baked into the same query for a real, tested reason (DIR-001 Decision
  9's GiST-index-backed query-plan verification) — reranking in Python after fetching would require either
  fetching every matching row (defeating the point of `LIMIT`) or reranking only within one already-paginated
  page (silently wrong: a later page could contain a higher-scoring row than an earlier page's lowest-scoring
  row). Computing the score in the same `ORDER BY` the database already uses for `LIMIT`/`OFFSET` avoids both
  failure modes.
- **A raw, unnormalized linear combination (e.g. `rating * review_count - distance_meters`) instead of a bounded
  `[0,1]` composite.** Rejected: units would be incompatible (meters vs. a 1–5 scale vs. an unbounded count) and
  the result would not fit `match_score NUMERIC(5,4)`'s intent as a normalized quality indicator; a bounded,
  weighted convex combination is both simpler to reason about and directly testable against "known
  rating/distance combinations" (AC8).

**Consequences:**
- **Today, in production, this formula is mathematically equivalent to the existing nearest-first order for any
  set of candidates that all share the same `average_rating`/`review_count`** (true for essentially every real
  provider today, since no Review domain exists to populate real values) — when the rating and volume terms are
  identical across all candidates, ordering by the composite score reduces exactly to ordering by the proximity
  term alone, which is itself a monotonically decreasing function of `distance_meters`. This is a real,
  structural guarantee (provable, and tested — see Backend Proposed Changes' test list), not an assumption: no
  DIR-001/AI-002 shipped behavior regresses for any current, real dataset. The difference from AI-002's own
  Decision 5 (which built no formula at all) is that this formula is genuinely ready the moment real rating data
  exists — no `SearchRequestService`/`ProviderSearchRepository` code needs to change again once `REV-001` starts
  writing real `providers.average_rating`/`review_count` values (already `04_DATABASE.md`'s own documented job
  for that future story, line 405–406 — this Plan invents no new obligation for `REV-001`).
- DIR-001's own shipped `GET /search/providers` endpoint's result order is a legitimate, in-scope behavioral
  change under this Plan (not just the AI-conversation path) — direct consequence of Decision 1's "same query,
  not two" choice. Its existing order-dependent tests must be reviewed; any fixture using non-uniform
  `average_rating`/`review_count` across otherwise-tied-by-distance providers may need its expected order updated
  to reflect the new, intentional behavior (flagged in Backend Proposed Changes; not a regression to silently
  paper over).
- The stale "ordered nearest-first by the backend" code comment in `mobile/lib/features/search/data/
  search_repository.dart` needs a one-line correction (no functional mobile change) — included in Backend
  Proposed Changes rather than a frontend delegation, since it is a comment only.

### Decision 2 — Rating source: `providers.average_rating`/`review_count`, not the unbuilt `provider_rating_summaries` table; explicitly not building any part of the Review domain in this story

**The problem:** AC3's literal text names `provider_rating_summaries` — a table that does not exist and, per
Verified Current State above, structurally cannot yet hold any real data (Review anchors to a Contact View with a
"Yes" Outcome Tag, and Contact View is CON-001, which depends on *this* story).

**Chosen:** implement Decision 1's formula against the already-existing, already-wired `providers.average_rating`
(nullable) and `providers.review_count` (default `0`) columns instead. This is a **deliberate, flagged
substitution of AC3's named data source**, not a silent reinterpretation — recorded here for a new ADR at
closeout and a `04_DATABASE.md` cross-reference note, mirroring exactly how AI-001/AI-002 each flagged their own
AC-vs-reality gaps rather than guessing silently. Building `review.reviews`/`review.provider_rating_summaries`
(the real Review domain: anchor-verification against `contact_views` + a "Yes" Outcome Tag, self-dealing
inheritance, recalculation-on-write) remains entirely `REV-001`'s scope — a genuinely separate, sizable domain
(a new schema, a new module, a write-path with real business-rule enforcement), not a "minimal one-table stub"
this story could responsibly absorb, especially given it cannot be exercised end-to-end (no reviews can exist)
until CON-001 and an Outcome Tag mechanism also ship.

**Alternatives considered and rejected:**
- **Build an empty `review.provider_rating_summaries` table now, populated by nothing, just so AC3's literal
  table name exists.** Rejected: this is schema for schema's sake — an empty table with no writer provides zero
  additional testability over the already-existing `providers.average_rating`/`review_count` columns (both are
  equally empty/placeholder today), while creating a second, disconnected "rating storage" concept for a future
  `REV-001` to reconcile against, redundant with `04_DATABASE.md`'s own already-documented plan for `REV-001` to
  write to `providers.average_rating`/`review_count` directly.
- **Build a minimal, real Review domain slice now** (a bare `reviews` table with no anchor-verification, so a
  test could insert a real row) — rejected outright: this would ship a Review write path that skips the
  self-dealing-inheriting anchor-verification business rule `03_DOMAIN_MODEL.md` explicitly requires ("Because a
  Review always anchors to a Contact View, the self-dealing restriction on Contact View... transitively blocks a
  Provider from reviewing their own listing"). Shipping an unverified, anchor-free `reviews` table just to
  satisfy this story's own literal AC wording would be a real, unrequested security/product regression baked in
  ahead of `REV-001`'s actual design work.
- **Defer AC3 entirely, ship nearest-first only again (repeat AI-002's Decision 5 verbatim).** Rejected: AC8
  explicitly requires "automated tests cover ranking correctness against known rating/distance combinations,"
  which is only meaningful if a real, testable ranking formula exists to exercise — tests can inject arbitrary
  `average_rating`/`review_count`/`distance` fixture combinations regardless of whether *production* data is
  populated yet (exactly how `test_search_service.py`'s existing fixtures already work, confirmed in Verified
  Current State). Deferring the formula entirely would leave this story's own central, named purpose ("See ranked
  providers for my request") largely unmet, duplicating what AI-002 already shipped with no new customer-facing
  value — inconsistent with the story's own explicit reason for existing in this sprint.

### Decision 3 — `provider_matches.match_score` becomes real for the automated path; stays `NULL` for the manual path

**The problem:** AC1 says `provider_matches` "stores rank and match_score per provider per request" — currently
always `NULL` (AI-002 Decision 5). Once Decision 1's formula exists, the automated path can honestly populate it;
the manual (admin) path has no computed formula at all (an admin's own judgment produces the order), so it must
stay honestly `NULL`, not backfilled with a fabricated value.

**Chosen:** `ProviderMatchRepository.bulk_create`'s signature changes from `ranked_provider_ids: list[uuid.UUID]`
to `ranked_matches: list[tuple[uuid.UUID, float | None]]` — `rank` is still the 1-based position in the list
(unchanged), `match_score` is the tuple's second element. `SearchRequestService._run_automated_match` returns
`list[tuple[uuid.UUID, float]]` (using Decision 1's `scores_by_id`) instead of a bare id list;
`resolve_manual_match` builds `[(provider_id, None) for provider_id in provider_ids]` before calling
`_finalize_matches`, preserving the existing, correct behavior that an admin's manual ordering carries no
computed score.

**Alternatives considered and rejected:**
- **Also compute and store a (fabricated) score for the manual path**, e.g. by re-running Decision 1's formula
  against the admin's chosen providers just to fill the column — rejected outright: the admin's ordering is not
  produced by the formula, so a formula-derived score displayed or stored alongside it would misrepresent how
  that particular row was actually ranked, a direct anti-fabrication violation.

---

## Backend — Proposed Changes

No new migration. No new module. All changes are within the already-shipped `provider` and `search` modules.

1. `backend/app/core/config.py` — add `RANKING_WEIGHT_PROXIMITY: float = 0.6`, `RANKING_WEIGHT_RATING: float =
   0.3`, `RANKING_WEIGHT_REVIEW_VOLUME: float = 0.1`, `RANKING_NEUTRAL_AVERAGE_RATING: float = 3.0`,
   `RANKING_REVIEW_VOLUME_CAP: int = 50` (Decision 1).
2. `backend/app/modules/provider/repositories/provider_search_repository.py` — `_SEARCH_NEARBY_SQL`'s `SELECT`
   gains the `match_score` expression (Decision 1); `ORDER BY` changes to `match_score DESC, p.id ASC`;
   `_WHERE_CLAUSE`/`_COUNT_NEARBY_SQL` stay byte-for-byte unchanged (AC2). `search_nearby(...)` gains the five new
   parameters and returns `scores_by_id: dict[uuid.UUID, float]` as a fourth return value. Update the module's own
   docstring to describe the new ranking behavior (mirrors this file's existing practice of a load-bearing
   docstring explaining clause/order intent).
3. `backend/app/modules/provider/services/provider_service.py` — `search_nearby(...)` gains the same five
   parameters, thin-passes them to the repository, returns the extended 4-tuple.
4. `backend/app/modules/search/services/search_service.py` — `search_providers(...)` reads the five `Settings`
   values itself and passes them to `provider_service.search_nearby(...)`; discards the returned `scores_by_id`
   (no schema change to `SearchResultProviderResponse`).
5. `backend/app/modules/search/services/search_request_service.py` — `_run_automated_match(...)` reads the same
   five `Settings` values, calls the extended `search_service`/`provider_service` chain (or a small internal
   helper if duplication with item 4 becomes awkward — a shared private helper is acceptable as long as it stays
   inside one module boundary; do not create a new cross-module edge for this), returns `list[tuple[uuid.UUID,
   float]]`; `_handle_completed`/`_finalize_matches` updated to carry the tuple list through to
   `provider_match_repository.bulk_create`; `resolve_manual_match` builds `(provider_id, None)` pairs (Decision
   3).
6. `backend/app/modules/search/repositories/provider_match_repository.py` — `bulk_create(...)` signature change
   per Decision 3.
7. `mobile/lib/features/search/data/search_repository.dart` — correct the one stale code comment ("ordered
   nearest-first by the backend") to describe merit-ranked ordering instead; no functional/widget change.

### Tests

8. `backend/tests/modules/provider/test_provider_search_repository.py` — new tests, direct against
   `_SEARCH_NEARBY_SQL`/`search_nearby(...)`: (a) a farther-but-higher-rated provider outranks a closer-but-
   unrated one under the default weights (a concrete "known rating/distance combination," AC8); (b) two providers
   with identical `average_rating`/`review_count`/distance produce a stable tie-break on `id ASC` (AC4); (c) a
   regression fixture confirming that when all candidates share the same (null) rating/review_count, the order
   is identical to the pre-existing nearest-first order (proves Decision 1's "Consequences" claim, not just
   asserts it); (d) `_WHERE_CLAUSE`'s existing filter-precedence/GiST-index tests are re-run unchanged to confirm
   AC2/AC7 still hold.
9. `backend/tests/modules/search/test_search_service.py` — update the existing tuple-unpacking call sites for the
   new 4-tuple return; add one explicit merit-ranking-order assertion at this layer (not just the repository
   layer) so `GET /search/providers`'s actual response order is directly proven, not only inferred.
10. `backend/tests/modules/search/test_search_request_service.py` — extend: the automated path now writes a
    non-`null` `match_score` on every `provider_matches` row it creates; a rating/distance-combination fixture
    proves the customer's final ranked list (via `get_matched_providers`) reflects merit-ranking, not just
    proximity; the manual path continues to write `match_score = NULL` for every row (Decision 3, explicit
    regression test).
11. `backend/tests/modules/search/_helpers.py` — extend `create_discoverable_provider(...)` with optional
    `average_rating: Decimal | None = None`, `review_count: int = 0` parameters, so ranking tests can construct
    providers with deliberately varied rating/distance combinations.
12. Full existing suite re-run (not just new tests) — particular attention to any DIR-001 test whose expected
    order assumed distance-only ranking with non-uniform fixture rating/review_count data; update the expected
    order where the change is real and intentional per Decision 1's Consequences (flag any such change plainly in
    the PR/Walkthrough, do not silently adjust an assertion without noting why).

---

## Explicitly Out of Scope (do not implement in this story)

- **Any part of the real Review domain** — `review.reviews`, `review.provider_rating_summaries`, Outcome Tags, or
  any write path for `providers.average_rating`/`review_count` beyond their existing `PRO-001` creation-time
  defaults. This is `REV-001`/`REV-002`'s job, and (per Verified Current State) is structurally impossible to
  build meaningfully before `CON-001` ships anyway.
- **`CON-001`'s contact/reveal step** — the story's own explicit scope boundary; this story ends at a ranked
  results list, never a phone number.
- **Exposing `match_score` to the mobile client or any API response.** No AC (this story's or DIR-001's)
  requires it; it stays an internal `provider_matches` column, matching the existing precedent of not exposing
  raw internal scoring to customers.
- **A customer-facing "sort by" control** (e.g. toggling between "nearest" and "top-rated"). No AC requests it;
  ranking is a single, server-driven order, exactly as DIR-001/AI-002 already established for distance-only
  ordering.
- **Reconciling `provider.provider_category_labels` into `category.provider_categories`** (`13_OPEN_DECISIONS.md`
  item 1's still-open remainder) — this story's category filtering is entirely unchanged (Decision 1 leaves
  `_WHERE_CLAUSE` byte-for-byte untouched); inherited as-is, not worsened, exactly as AI-002 already did.
- **Any change to the AI Conversation chat flow itself** (`AI-001`) — this story touches only the
  matching/ranking layer downstream of an already-completed session.

---

## Open Questions (flagged for CTO awareness — do not block `backend` from starting, per this codebase's
established practice of proceeding on a well-precedented interim design while flagging it plainly)

1. **Decision 2 (rating source substitution)** — confirm it's acceptable for this story to satisfy AC3's
   substance using `providers.average_rating`/`review_count` rather than building any part of
   `provider_rating_summaries` now. Strongly precedented (mirrors AI-001/AI-002's own flagged AC-vs-reality gaps)
   and, per Verified Current State, the only structurally possible choice today — but it is a genuine
   interpretive call on an explicitly-named AC and should be ratified, not silently assumed correct.
2. **Decision 1 (in-place upgrade of DIR-001's own shipped query)** — confirm it's acceptable for this story to
   change the customer-facing result order of DIR-001's already-signed-off `GET /search/providers` endpoint, not
   only the AI-conversation path. Directly evidenced by DIR-001's own pre-announced AC5, but since it changes
   previously-approved, shipped behavior, it should be an explicit, visible decision rather than an implicit
   side effect discovered later.
3. **Decision 1's default weights (0.6/0.3/0.1) and neutral-rating default (3.0)** — these are this Plan's own
   reasoned starting point, not derived from any existing product spec. Confirm they're acceptable as launch
   defaults (all five are `Settings` values, tunable without a code change once a real product answer exists).

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

1. **backend** — Items 1–12 above. Build order: (a) `Settings` fields first (Decision 1's weights/neutral/cap);
   (b) `ProviderSearchRepository`'s query change, with its own direct repository-level tests (item 8) written
   alongside it, before touching any caller — this is the highest-risk, most load-bearing change in the story;
   (c) `ProviderService.search_nearby`'s thin pass-through extension; (d) `SearchService.search_providers`
   (DIR-001's own endpoint) — re-run its existing tests immediately after this change to catch any order-dependent
   fixture that needs updating, per Decision 1's Consequences; (e) `SearchRequestService`/`ProviderMatchRepository`
   (Decision 3) last, since it depends on (b)–(d) already being correct. Read Decision 1 and Decision 2 in full
   before starting — both contain the reasoning for why this story does not build any part of the Review domain
   and does not create a second, parallel ranking query.
2. **frontend** — not needed for this story (see Verified Current State: AC5 is already fully satisfied by
   AI-002's shipped mobile work, and no new field/response shape is introduced for mobile to render). If
   `tester`'s end-to-end pass finds a genuine AC5 gap this Plan missed, loop back with a scoped frontend
   delegation at that point rather than speculatively building anything now.
3. **tester** — verify all 8 verbatim ACs with real evidence (real DB, real HTTP round trips through both `GET
   /search/providers` and `GET /search-requests/{id}`). Particular attention to: AC3/AC8 (construct real fixture
   providers with deliberately varied rating/distance combinations and confirm the actual returned order matches
   the formula, not just that a `match_score` column is non-null); AC4 (a genuine exact-tie fixture, not just
   "different scores happen not to collide"); AC2/AC7 (re-verify DIR-001's existing filter-precedence/
   discoverability guarantees still hold unchanged, since `_WHERE_CLAUSE` itself must be provably untouched); AC5
   (an end-to-end conversation-to-results flow, confirming no manual re-search step, even though no code changed
   for it — a regression check, not a re-implementation check); AC1/AC6 (confirm `match_score` is genuinely
   non-null for automated matches and genuinely `null` for manual ones, and `search_event_log` is still written
   exactly once per request regardless of path).
4. **architect** — review Decision 1's in-place query change for genuine correctness (the SQL score expression's
   bounds, the parameterization/security posture of the five new bound values, and that `_WHERE_CLAUSE` truly did
   not change); Decision 2's rating-source substitution against `00_PROJECT_CONTEXT.md` §3's anti-fabrication
   principle and against prematurely building Review-domain schema; Decision 3's `NULL`-for-manual-path honesty;
   and confirm no new cross-module edge was introduced (this story adds zero new module dependencies — `search`
   still only depends on `provider`/`customer`/`administration`, unchanged from AI-002).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decision 1 (in-place merit-ranking query upgrade, shared by DIR-001 and the AI-conversation path) and
     Decision 2 (rating-source substitution: `providers.average_rating`/`review_count`, not
     `provider_rating_summaries`) as new ADRs (next available: **ADR-042** onward).
   - Update `04_DATABASE.md`: note under `provider_rating_summaries`'s existing spec that it remains fully
     unbuilt and owned by a future `REV-001`, and that `MAT-001`'s ranking formula instead reads
     `providers.average_rating`/`review_count` (already documented as `REV-001`'s eventual write target) — cross-
     reference the new ADR.
   - Consider adding a new numbered item to `13_OPEN_DECISIONS.md` (next available: item 14) recording that
     `provider_rating_summaries` remains unbuilt/unused, and that a future `REV-001` should decide whether it is
     still needed as a distinct table once it ships real reviews, or whether `providers.average_rating`/
     `review_count` alone (already this story's and `REV-001`'s documented target) is sufficient — this is a real
     design question for that future story, not resolved here.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 8 section and `docs/AI/SESSION_HANDOFF.md`.

---

## Verification Plan (mapped to the 8 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Already true (tables/columns exist, confirmed against the real migration) — re-verified; `match_score` is now genuinely non-null for automated matches (item 10's test), confirming the column is actually used, not merely present. |
| 2 | `_WHERE_CLAUSE` confirmed byte-for-byte unchanged (a direct diff/identity check, not just "tests still pass") — DIR-001's existing filter-precedence tests (item 8d) re-run and passing. |
| 3 | New repository-level and service-level tests (items 8a, 9) with concrete rating/distance fixture combinations proving the formula, not just that a score exists. |
| 4 | A genuine exact-tie fixture (item 8b) asserting `id ASC` as the deterministic final tie-break on the new `match_score`-based order. |
| 5 | Re-verified via existing, unchanged mobile code (`AiConversationScreen`/`RankedProviderResultsList`) plus a live end-to-end conversation-to-results HTTP/widget test — no new implementation, a regression proof. |
| 6 | Already true (`_finalize_matches` unchanged as sole writer) — re-verified via existing + extended `search_event_log` tests (item 10). |
| 7 | Already true (`_WHERE_CLAUSE`'s discoverability clause unchanged) — re-verified via existing DIR-001 tests (item 8d). |
| 8 | Items 8a/8b/9/10 collectively: known rating/distance combinations (correctness) and an exact-tie fixture (determinism), at both the repository and service layers. |

---

## Related Documents

- `docs/AI/00_PROJECT_CONTEXT.md` §3 (anti-fabrication principle — basis for Decision 1's neutral-rating default
  being a uniform, documented constant rather than a per-provider fabrication, and for Decision 2 rejecting a
  bare, unverified `reviews` table)
- `docs/AI/03_DOMAIN_MODEL.md` (Review domain — Contact-View/Outcome-Tag anchor requirement, the direct evidence
  a minimal Review domain cannot yet exist; Provider domain — `average_rating`/`review_count`)
- `docs/AI/04_DATABASE.md` (`providers.average_rating`/`review_count`, lines 405–406; Review Domain —
  `reviews`/`provider_rating_summaries`, lines 811–839; Search Domain, lines 674–709)
- `docs/AI/09_DECISIONS.md` (ADR-025/026/027 — DIR-001's original `SearchService`/`ProviderSearchRepository`
  design this Plan modifies in place; ADR-037–041 — AI-002's `search` schema and matching-mechanism-reuse
  decisions this Plan builds directly on top of, especially ADR-041's Decision-5 reasoning this Plan revisits and
  resolves)
- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy/`provider_category_labels` gap, inherited unchanged;
  a new item 14 to be added at closeout for `provider_rating_summaries`'s continued non-use)
- `docs/AI/14_USER_FLOWS.md` Flow 4 step 6 ("rank by merit — rating + review volume + proximity"), step 7
  (`search_event_log`), step 8 (ranked list display); Flow 7 (Wizard-of-Oz manual match, unaffected by this
  story's ranking change per Decision 3)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-07, S-08 — the shared ranked-results widget this story's ordering change
  affects with no widget-level change)
- `docs/implementation/plans/Plan_S06_DIR-001.md` / `Walkthrough_S06_DIR-001.md` (the `ProviderSearchRepository`/
  `SearchService` design this Plan modifies in place, including its own AC5's direct pre-announcement of this
  story)
- `docs/implementation/plans/Plan_S07_AI-002.md` / `Walkthrough_S07_AI-002.md` (Decision 4/5 — the
  `_finalize_matches` helper and matching-mechanism-reuse this Plan extends; the `search`/`administration`/
  `customer` cross-module wiring this story does not change)

---

**End of Document**
