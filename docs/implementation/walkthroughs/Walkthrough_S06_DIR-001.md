# Walkthrough S06 DIR-001

## Story: Browse Nearby Providers by Category and Location

**Sprint:** 06 | **Story ID:** DIR-001 | **Priority:** Critical | **Status:** Done

As a customer, I want to filter providers by category and distance without needing the AI conversation, so that
basic discovery works end to end — proving the platform's core value with zero dependency on
verification-review turnaround or AI infrastructure being finished.

This is the first story of Sprint 6 ("Directory & Listing Claims") and the first real slice of the "Search
Request & Matching" domain `02_ARCHITECTURE.md` has named since the project's earliest planning. It delivers a
structured (non-conversational) directory — category + geospatial-radius filtering against the
`cube`/`earthdistance` proximity infrastructure `04_DATABASE.md` Section 13 had specified but no story had ever
built or queried — backed by VER-002's `is_discoverable` trust gate. **Scope boundary, stated plainly:** this
story does not touch the AI Conversation (AI-001), AI-ranked results (MAT-001), `CLM-001`, or any Google-seeded/
`is_claimed` listing at all; it searches only self-registered, `is_discoverable=true` providers. Full context,
the 9 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S06_DIR-001.md`. Mid-story
implementer notes and flagged deviations: `docs/implementation/plans/Checkpoint_S06_DIR-001.md` (deleted at the
end of this closeout, per standing process).

All work is committed and pushed to branch `claude/provider-storefront-pro-001-qnicuj`: backend implementation
(`8a908a3`), mobile implementation (`1dbb8e8`), and an architect-recommended follow-up fix plus an open-decisions
log entry (`90f1fc8`).

---

## What was implemented

### Backend (`backend/app/modules/search/`, new; `backend/app/modules/provider/`, extended)

- **New, reversible Alembic migration** (`enable_geospatial_extensions_and_indexes`) — enables the `cube` and
  `earthdistance` Postgres contrib extensions and creates two GiST indexes: `idx_service_areas_location` on
  `provider.service_areas` and `idx_saved_addresses_location` on `customer.saved_addresses`, both exactly per
  `04_DATABASE.md` Section 13's pre-existing (previously unbuilt) spec. Downgrade drops only the two indexes,
  never the extensions (shared, low-risk-to-leave, high-risk-to-drop). Verified upgrade/downgrade end-to-end
  against a disposable scratch Postgres database.
- **New `search` module** (no `models.py` — this domain's first slice creates no new tables) —
  `SearchService` (constructor-injects `ProviderService` only, the same cross-module shape ADR-014/016/VER-001/
  VER-002 already established), `GET /search/providers` and `GET /search/categories`, both
  `require_role(ROLE_CUSTOMER)` (Decision 3 — pre-confirmed by the CTO before implementation began: browsing
  requires authentication, no guest path, per `14_USER_FLOWS.md` Flow 1's explicit "search" naming).
- **New `ProviderSearchRepository`** (`provider` module, not `search`) — owns the actual geospatial/category/
  discoverability query, since `02_ARCHITECTURE.md` prohibits one module reaching into another module's
  repository directly, and every table the query touches (`providers`, `provider_category_labels`,
  `service_areas`) lives in the `provider` schema. Issues a fully parameterized `sqlalchemy.text()` query —
  this codebase's first use of raw SQL, since `earth_box`/`earth_distance`/`ll_to_earth` have no SQLAlchemy
  ORM/Core mapping: category `EXISTS` subquery → `earth_box` GiST-indexed containment (narrows candidates) →
  `earth_distance` exact recheck (`<= :radius_meters`) → `is_discoverable`/`is_active`, `ORDER BY
  distance_meters ASC, id ASC` for deterministic tie-breaking. A matching `COUNT(*)` variant shares the identical
  `WHERE` clause for pagination totals.
- **Category filtering** (`GET /search/providers?category=<value>`) — case-insensitive **exact** match
  (`lower(label) = lower(:category)`) against any of a provider's `provider_category_labels` rows, never
  substring/`ILIKE`, chosen because a free-text field with no taxonomy is exactly the situation where fuzzy
  matching produces silently wrong results. `category` is optional. `GET /search/categories` (unpaginated, per
  ADR-012's exception) returns the distinct, case-normalized set of labels currently in use by
  `is_discoverable=true` providers, backing the mobile category-picker without a hardcoded, drift-prone client
  list.
- **Honest rating rendering** — the response carries the raw `average_rating: Decimal | None` and
  `review_count: int` exactly as stored; since the Review domain has never been built, `average_rating` is
  `NULL` for every real provider today. Rendering rule ("No reviews yet" vs. `"4.8 (3 reviews)"`) is documented
  for and enforced by the mobile widget, never a synthesized `"0.0 (0 reviews)"` anywhere.
- **Config**: `SEARCH_DEFAULT_RADIUS_KM=10.0`, `SEARCH_MAX_RADIUS_KM=100.0`, `SEARCH_MAX_PAGE_SIZE=50`. New
  exception: `InvalidSearchRadiusError` (422).
- **`ProviderService`** gained `search_nearby(...)` (thin pass-through to `ProviderSearchRepository` plus
  `list_by_ids` hydration, preserving distance order) and `list_distinct_category_labels()`. It also gained a
  `portfolio_repository` constructor dependency and `get_primary_photo_urls(provider_ids)` (a new batch method on
  `PortfolioRepository`, `list_active_for_provider_ids`) so `SearchService` can enrich results with a primary
  photo without a second `search → provider-repository` edge — `SearchService` only ever holds a `ProviderService`
  reference.
- **Tests (33 new, all passing)**: filter-precedence (category → geo → discoverability, AC2) and deterministic
  tie-break with reversed insertion order across two runs (AC7) at the repository level; a dedicated
  `EXPLAIN (FORMAT JSON)` test seeding 1,500 scattered `service_areas` rows, asserting an `Index Scan`/`Bitmap
  Index Scan` on `idx_service_areas_location` and explicitly asserting no top-level `Seq Scan` (AC6); both
  Decision-2 rating-shape cases (`NULL` and fixture-injected `4.80`/3); radius-bounds validation; the full
  401/403/200 HTTP matrix; empty-result shape (AC4's backend half); category-list case-collapse and
  discoverable-only scoping.

### Mobile (`mobile/lib/features/search/`, new)

- **`SearchFiltersScreen`** — category chips (from `GET /search/categories`, plus an "All categories" chip), an
  origin-location field pre-filled from the customer's default saved address (via `SavedAddressRepository`,
  editable through the existing, reusable `LocationCaptureField`/`LocationPickerScreen` from CUS-002, "use
  current location" included), a 1–100 km radius slider, and a single "Search" action.
- **`SearchResultsScreen`** (S-08) — provider cards, loading/error/retry states, pull-to-refresh, and Decision
  7's two textually distinct empty states modeled as a real `SearchResultsStatus.idle` vs. loaded-empty
  distinction in `SearchResultsController` — the "no search performed yet" state is genuinely reachable (the
  `searchResults` route renders with `filters: null` rather than redirecting away), not a test-only synthetic
  state.
- **`ProviderSearchCard`** (new, reusable) — photo (placeholder fallback), name, category labels, rating+count
  per the "No reviews yet" / `"4.8 (3 reviews)"` rendering rule, distance formatted as m/km. Built with no
  ranking-specific UI so MAT-001 can reuse it unchanged once results become AI-ranked.
- **`HomePlaceholderScreen`**'s "Find a Service" button rewired to open `SearchFiltersScreen` (once a saved
  address exists), replacing CUS-002's temporary "coming soon" snackbar — the address-required gate itself is
  unchanged.
- **Tests (10 new, all passing)**: both empty states rendered distinctly; both rating-rendering states (`"No
  reviews yet"`/`"4.8 (3 reviews)"`); category chips populate from a fake repository; location field pre-fills
  from a fake default saved address; "Search" navigates with the expected filters.

---

## The 9 Architecture Decisions, as actually shipped

All 9 decisions from `Plan_S06_DIR-001.md` shipped as planned, with two flagged, non-semantic implementation
deviations (both reviewed and accepted — see Review Process below):

1. **Category filter mechanism** — case-insensitive exact match against `provider_category_labels.label`
   (never substring), plus `GET /search/categories` as the picker source. Shipped as planned; recorded as
   **ADR-027**.
2. **Reviews don't exist yet** — `average_rating`/`review_count` render honestly ("No reviews yet" when `NULL`,
   never a fabricated `0.0 (0 reviews)`). Shipped as planned; both states covered by tests on both backend and
   mobile.
3. **Authentication: `require_role(ROLE_CUSTOMER)`, no guest path** — pre-confirmed by the CTO before backend
   work began, exactly as the Plan specified; no change made.
4. **Module placement: a new `search` module, with the actual query owned by `provider`** — shipped as planned.
   One necessary addition beyond the Plan's literal item list: `ProviderService` gained a `portfolio_repository`
   dependency and `get_primary_photo_urls`, so photo enrichment could happen without a second cross-module edge
   — reviewed and accepted by `architect` as sound reasoning, not scope creep. Recorded as **ADR-025**.
5. **Origin point is a raw request lat/lng, never a `saved_addresses` FK; no `search_requests`/`search_event_log`
   write** — shipped as planned. `GET /search/providers` takes `latitude`/`longitude`/`radius_km` directly.
6. **Mobile entry point: a new, minimal Search Filters screen plus the real S-08 Search Results screen** —
   shipped as planned; the full S-06 Home screen (AI input box, mic icon) remains explicitly out of scope.
7. **Empty-state contract: backend returns a plain empty collection; the two AC4 states are client-side** —
   shipped as planned, and — flagged by the implementer, confirmed by `architect` — genuinely reachable at
   runtime (not test-only), via a deliberate, narrow exception to this router's usual `extra`-required redirect
   pattern for the `searchResults` route.
8. **Geospatial SQL: `earth_box` before `earth_distance`, `id ASC` tie-break, raw parameterized `text()`** —
   shipped exactly per the Plan's literal SQL shape, with one driver-forced, non-semantic addition: `:category`
   is wrapped in `CAST(... AS text)` at its first `IS NULL` usage, because psycopg3 raised `AmbiguousParameter`
   without explicit type context on the bare comparison. Clause order and filter semantics are unchanged.
   Reviewed and accepted by `architect` as a pure driver-compatibility fix. Recorded as **ADR-026**.
9. **AC6's query-plan verification: seed representative volume, run real `EXPLAIN`, assert an index scan node**
   — shipped as planned; independently re-run in isolation by `tester`, not merely trusted from the original
   implementation.

---

## Review Process — a full, honest account

Unlike VER-001/VER-002, this story's review did not surface a functional bug — but it did surface two genuine,
substantive architectural findings, one fixed before closeout and one deliberately deferred as logged debt. This
section documents both plainly, per this codebase's established "don't just declare success" review-write-up
precedent.

### 1. `tester` — independent verification of all 7 ACs, including its own real evidence, not just re-running the existing suite

The tester did not simply confirm the existing test suite passed. It independently:

- Ran its own scratch-database migration (`upgrade head` → `downgrade -1` → `upgrade head`) to confirm the
  migration's own reversibility claim, rather than trusting the Checkpoint's account of it.
- Ran a manual `EXPLAIN` sanity check **outside** the automated test suite, directly via `psql` against a
  representative dataset, to independently confirm the planner genuinely chooses `idx_service_areas_location`
  over a sequential scan — not merely that the dedicated pytest assertion passes.
- Re-ran the filter-precedence and tie-break tests in isolation with the fixture insertion order **reversed**,
  confirming the returned order is genuinely driven by `id ASC`, not by insertion or scan order.

All 7 acceptance criteria were verified Pass with this direct evidence, not by inference from a green test run
alone.

### 2. `architect` — APPROVED WITH RECOMMENDATIONS (non-blocking); two findings, one fixed, one deliberately deferred

**Finding 1 — an N+1 query in `SearchService.search_providers`, fixed before closeout.** The original
implementation called `ProviderService.get_category_labels` once per search result (one query per row) to
populate each result's category labels for display, inconsistent with the already-batched photo-URL lookup
(`get_primary_photo_urls`, one query for the whole page) built for the identical purpose one field over. This is
a genuine, if non-critical, performance inconsistency the architect flagged as worth fixing before sign-off
rather than carrying forward as debt, since the batched alternative was already proven correct one field away in
the same method. **Fixed** (commit `90f1fc8`): a new `ProviderService.get_category_labels_by_provider_id`
batch method mirrors `get_primary_photo_urls`'s shape exactly — one query for the whole result page, not one per
row.

**Finding 2 — mobile `features/search`/`features/home` importing `features/customer` directly, deliberately
logged as debt, not fixed in this story.** `features/search/state/search_filters_controller.dart` imports
`features/customer/data/saved_address_repository.dart` directly, to pre-fill the search origin from the
customer's default saved address — a real violation of `02_ARCHITECTURE.md`'s unqualified "features must not
depend directly on each other" rule. The architect's finding, and the reasoning for not fixing it inside this
story, in full:

- This is **not a new pattern**: `features/home/presentation/screens/home_placeholder_screen.dart` (pre-existing,
  shipped with CUS-002, unchanged in its import shape by this story) already imports the same
  `SavedAddressRepository` directly, for its own address-required gate.
- Fixing only the newer `search` edge while leaving the older, identical `home` edge in place would not actually
  resolve the architectural drift — it would just produce two different remediations of the same gap at two
  different times, an inconsistent outcome worse than a single, deliberate fix later.
- The right fix (most likely a trimmed, read-only "default address" accessor moved into `mobile/lib/shared/`,
  mirroring VER-001's own `ProviderType`-extraction precedent for a structurally similar `provider ↔
  verification` coupling) is a small but real design decision that should be made once, deliberately, covering
  both call sites together — not squeezed into either story's review cycle as a one-off patch.
- This was recorded as `docs/AI/13_OPEN_DECISIONS.md` **item 12** (accepted, logged debt — not a decision to
  leave the rule unenforced indefinitely; no new call site should be added without first checking whether item
  12 has been resolved).

Both findings — the fix and the deferral — were reviewed and accepted; the review's final verdict was
**APPROVED WITH RECOMMENDATIONS (non-blocking)**.

### Final test counts

- **Backend: 476 passed** (443 pre-existing + 33 new). `ruff check` clean. `mypy` shows 19 pre-existing errors,
  all outside this story's code (`app/core/context.py`, `security.py`, `logging.py`,
  `middleware/logging_middleware.py`, `exceptions/handlers.py`, `identity/services/id_token_verifier.py`,
  `audit/*`) — zero new errors introduced by DIR-001.
- **Mobile: 144 passed** (134 pre-existing + 10 new). `flutter analyze` — no issues found. `dart format
  --set-exit-if-changed` — 0 files would change.

---

## Acceptance Criteria — Verification

All 7 acceptance criteria (from `Plan_S06_DIR-001.md`, sourced from the Tracker) were independently verified by
the `tester` agent with direct evidence — see the Review Process section above for what "direct evidence" meant
concretely for AC2/AC6/AC7.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `earthdistance`/`cube` extensions enabled via migration; GiST indexes exist on `saved_addresses` and `service_areas` location columns | Pass |
| 2 | Filters apply in order — category, then geo (`earth_box` before `earth_distance`), then discoverability; a non-discoverable provider never appears regardless of fit | Pass |
| 3 | Results show photo, name, category, rating+review count (never rating alone), and distance | Pass |
| 4 | Empty results show a specific empty-state message distinct from "no search performed yet" | Pass |
| 5 | Search Results screen implemented in its structured (pre-AI) form, upgradeable to AI-ranked results without a screen redesign | Pass |
| 6 | Query performance verified to use the GiST index via query-plan check, not a sequential scan, at representative volume | Pass |
| 7 | Automated tests cover filter precedence and deterministic tie-breaking | Pass |

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-025** (new `search` module placement — geospatial/domain-owned
  queries live in the module that owns the queried tables), **ADR-026** (this codebase's first raw parameterized
  `sqlalchemy.text()` SQL precedent — justified specifically when no ORM expression-language mapping exists),
  and **ADR-027** (free-text category exact-match filtering as an interim search-query mechanism, extending
  PRO-002's original `provider_category_labels` storage decision — which had never itself been given an ADR
  entry — to query-time matching). Append-only; no existing entry modified.
- **`docs/AI/04_DATABASE.md`** — Section 13 updated from "recommendation" language to confirm both GiST indexes
  (`idx_service_areas_location`, `idx_saved_addresses_location`) shipped exactly per the pre-existing spec, with
  no deviation; the `service_areas` and `saved_addresses` table sections' Indexes lists and notes updated to
  match (the previous "not yet added, no story queries it yet" note is no longer accurate). Version bumped
  3.4.0 → 3.5.0.
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 12 added during the architect's review (see Review Process above),
  logging the mobile `search`/`home` → `customer` coupling as accepted debt with a recommended remediation
  shape.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — DIR-001 marked done; a new "Sprint 6 — Directory & Listing
  Claims (In Progress)" table added; Executive Summary, Current Backend Capabilities, Repository State
  (a new `search` module bullet), the Flutter mobile paragraph, Current Limitations (Search & Matching now
  partially shipped), Overall Progress, and Next Planned Story all updated. **`CLM-001` is explicitly recorded
  as deferred, not planned** — Section 17 states plainly that `13_OPEN_DECISIONS.md` item 3 (Google Places Data
  Legal Review) remains genuinely open and that no engineering agent should plan or start `CLM-001` until it
  resolves.
- **`docs/CHANGELOG.md`** — new entry under `[Unreleased]`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s Stories sheet still needs its DIR-001 row's Status updated from "Planned"
  to "Done"** — per standing process, this uses a direct raw-XML cell-patching procedure the CTO handles
  separately (a normal `openpyxl` load/save round-trip was previously found to silently drop this workbook's
  conditional-formatting extensions). Not performed by this closeout.
- **`docs/AI/13_OPEN_DECISIONS.md` item 12** remains genuinely Open (accepted debt, not resolved) — any future
  story adding a new mobile feature-to-feature import should check this item first rather than adding a third
  instance of the same coupling.

---

## Testing Performed

- `backend`/`frontend` implementation, each with their own new automated test suites (33 backend, 10 mobile —
  see What Was Implemented above).
- `tester` agent: all 7 ACs independently verified with direct evidence (its own scratch-DB migration run, a
  manual `EXPLAIN` sanity check outside the test suite, and reversed-insertion-order re-runs of the
  filter-precedence/tie-break tests) — see Review Process above.
- `architect` agent: returned **APPROVED WITH RECOMMENDATIONS (non-blocking)** — the N+1 query fix (commit
  `90f1fc8`) and the mobile coupling deferral (`13_OPEN_DECISIONS.md` item 12) — see Review Process above for
  the full reasoning behind each.
- User (CTO) sign-off received after both the tester's and architect's final verdicts, and the follow-up fix
  commit, were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_09_0900-a3f6e9c21d47_enable_geospatial_extensions_and_indexes.py` (new)
- `backend/app/modules/search/{schemas,dependencies,api}.py`, `services/search_service.py` (new module)
- `backend/app/modules/provider/repositories/provider_search_repository.py` (new)
- `backend/app/modules/provider/repositories/provider_category_label_repository.py` — `list_distinct_labels_for_discoverable_providers` (new)
- `backend/app/modules/provider/services/provider_service.py` — `search_nearby`, `list_distinct_category_labels`,
  `get_primary_photo_urls`, `get_category_labels_by_provider_id` (the architect's N+1 fix)
- `backend/app/modules/provider/repositories/portfolio_repository.py` — `list_active_for_provider_ids` (new)
- `backend/app/core/config.py` — `SEARCH_DEFAULT_RADIUS_KM`/`SEARCH_MAX_RADIUS_KM`/`SEARCH_MAX_PAGE_SIZE`
- `backend/app/core/exceptions/exceptions.py` — `InvalidSearchRadiusError`
- `backend/app/api/v1/api.py` — `search` router mounted at `/search`
- `backend/tests/modules/provider/test_provider_search_repository.py` (new — AC2/AC6/AC7)
- `backend/tests/modules/search/test_search_service.py`, `test_search_endpoints.py` (new)

### Mobile
- `mobile/lib/features/search/domain/models/{search_result_provider,category_option,search_exception,search_filters_args}.dart`
- `mobile/lib/features/search/data/search_repository.dart`
- `mobile/lib/features/search/state/{search_filters_controller,search_results_controller}.dart`
- `mobile/lib/features/search/presentation/screens/{search_filters_screen,search_results_screen}.dart`
- `mobile/lib/features/search/presentation/widgets/provider_search_card.dart`
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` — `_onFindService` rewired
- `mobile/lib/core/routing/{app_routes,app_router}.dart` — new `searchFilters`/`searchResults` routes
- `mobile/test/features/search/{search_filters_screen_test,search_results_screen_test}.dart` (new)
- `mobile/test/features/search/fakes/fake_search_repository.dart` (new)

---

## Follow-up Notes for Sprint Planning

- **Sprint 6 (Directory & Listing Claims) is now in progress — 1 of 2 stories done.** `DIR-001` has shipped and
  been signed off. `CLM-001` ("claim my Google-seeded business listing") remains **deferred**, not started or
  planned — blocked on `13_OPEN_DECISIONS.md` item 3 (Google Places Data Legal Review), which requires a real
  legal/UAE-PDPL review no engineering agent can perform. Item 4 (Unclaimed Listing UX)'s design question is
  already resolved, so `CLM-001` has no open design question left once item 3 resolves and it is actually
  planned.
- **`docs/AI/13_OPEN_DECISIONS.md` item 12** (mobile `search`/`home` → `customer` direct import) is open,
  accepted debt with a recommended remediation shape (a shared, read-only "default address" accessor in
  `mobile/lib/shared/`) — a small future story or a piece of a future mobile-architecture cleanup story should
  pick this up, covering both call sites together, not piecemeal.
- Non-blocking follow-up from this story's architect review already addressed at closeout: the `SearchService`
  N+1 category-label query (commit `90f1fc8`) — nothing outstanding from DIR-001 itself.
- **Cross-story documentation items, tracked but not newly created by this closeout**: the xlsx tracker's
  DIR-001 row still needs its Status flipped to "Done" (flagged above, handled separately by the CTO's own
  procedure).
