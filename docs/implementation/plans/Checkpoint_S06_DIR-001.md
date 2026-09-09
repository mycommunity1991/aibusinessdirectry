# Checkpoint — Sprint 06, DIR-001 (Browse Nearby Providers by Category and Location)

**Owner of this checkpoint:** `frontend` (most recent update)
**Status:** Backend implementation (Plan items 1-16) complete. Mobile implementation (Plan items 17-27)
complete. Awaiting `tester`, then `architect`.

---

## Current task

Implement the backend half of DIR-001 per `docs/implementation/plans/Plan_S06_DIR-001.md` — items 1-16 of
the Plan's "Backend — Proposed Changes" section. Decision 3 (authentication) was pre-confirmed by the CTO:
`require_role(ROLE_CUSTOMER)`, no guest path, exactly as the Plan already specified — no change made there.

## What's done (backend, complete)

1. **Migration** `backend/alembic/versions/2026_09_09_0900-a3f6e9c21d47_enable_geospatial_extensions_and_indexes.py`
   — `down_revision = c415258bcde2` (the prior single head). Enables `cube`/`earthdistance`, creates
   `idx_service_areas_location` and `idx_saved_addresses_location` (GiST, `ll_to_earth(...)`). Downgrade
   drops only the two indexes, never the extensions. Verified upgrade/downgrade end-to-end against a
   disposable scratch Postgres database (`ai_marketplace_migration_scratch`, dropped afterward) — `\dx`/`\d`
   output confirmed exactly matching AC1.
2. **New `search` module** (`backend/app/modules/search/`): `schemas.py`, `dependencies.py`,
   `services/search_service.py`, `api.py`. No `models.py` (Decision 4/5 — no new tables).
   `SearchService` depends on `ProviderService` only (constructor injection), matching the
   ADR-014/016/VER-001/VER-002 cross-module precedent. `search` never imports a `provider`-module
   repository directly.
3. **`ProviderSearchRepository`** (new, `backend/app/modules/provider/repositories/provider_search_repository.py`)
   — owns Decision 8's raw parameterized `text()` query (category `EXISTS` → `earth_box` → `earth_distance`
   → `is_discoverable`/`is_active`, `ORDER BY distance_meters ASC, p.id ASC`), plus a matching `COUNT(*)`
   variant sharing the identical `WHERE` clause. One necessary, non-semantic deviation from the Plan's
   literal SQL text: `:category` is wrapped in `CAST(... AS text)` at its first (`IS NULL`) usage — psycopg3
   raised `AmbiguousParameter` without it (the bare `:category IS NULL` comparison gives the driver no type
   context). Clause order and filter semantics are unchanged; flagged for `architect`'s attention as the one
   place the "read Decision 8 verbatim" instruction required a minimal, driver-forced addition.
4. **`ProviderCategoryLabelRepository.list_distinct_labels_for_discoverable_providers()`** (Decision 1) — added
   to the existing repository, using `select(...).distinct(func.lower(label))` (Postgres `DISTINCT ON`), not
   raw SQL (no `earthdistance` function involved, so the ORM expression language suffices — keeps this
   codebase's "first raw SQL" claim scoped to the one geospatial query).
5. **`ProviderService`** gains `search_nearby(...)` (thin pass-through + `list_by_ids` hydration, preserving
   the repository's own order) and `list_distinct_category_labels()`. **Deviation from the Plan's literal
   item list, flagged explicitly:** `ProviderService` also gained a new `portfolio_repository` constructor
   dependency and a new `get_primary_photo_urls(provider_ids)` method, plus `PortfolioRepository` gained a
   new `list_active_for_provider_ids(...)` batch method. This was necessary to literally satisfy Plan item
   4's text ("enriches each result with its primary portfolio photo... reuses the existing
   `PortfolioRepository.list_active_for_provider`") without violating Decision 4's single `search -> provider`
   edge via `ProviderService` only (`02_ARCHITECTURE.md`'s "Module -> Another Module's Repository: Not
   Allowed" rule) — `SearchService` never holds a `PortfolioRepository` reference itself. Not explicitly
   enumerated in the Plan's items 6-9, but required to implement item 4 without a second cross-module edge.
   **Please have `architect` confirm this reasoning is sound.**
6. **Config** (`backend/app/core/config.py`): `SEARCH_DEFAULT_RADIUS_KM=10.0`, `SEARCH_MAX_RADIUS_KM=100.0`,
   `SEARCH_MAX_PAGE_SIZE=50`, exactly as specified.
7. **`InvalidSearchRadiusError`** (422) added to `backend/app/core/exceptions/exceptions.py` +
   `__init__.py`'s exports.
8. **API wiring**: `backend/app/api/v1/api.py` — `v1_router.include_router(search_router, prefix="/search")`.
   `GET /search/providers` and `GET /search/categories`, both `require_role(ROLE_CUSTOMER)`.
9. **Tests** (all passing, all new — 33 tests):
   - `backend/tests/modules/provider/test_provider_search_repository.py` — filter-precedence (AC2, 6 tests),
     deterministic tie-break with reversed insertion order across two runs (AC7, 2 tests), pagination
     (1 test), and Decision 9's real `EXPLAIN (FORMAT JSON)` test seeding 1,500 scattered `service_areas`
     rows, asserting an `Index Scan`/`Bitmap Index Scan` node on `idx_service_areas_location` and explicitly
     asserting no top-level `Seq Scan` on `service_areas` (AC6, 1 test). The GiST index itself is created by
     a local test fixture (`_geospatial_index`), not by `Base.metadata.create_all()` — see that file's and
     `ServiceArea`'s own docstrings for why.
   - `backend/tests/modules/search/test_search_service.py` — category-list case-collapse, both Decision 2
     rating-shape cases (`NULL` and fixture-injected `4.80`/3), radius bounds validation, response shaping
     (photo/category-label enrichment), limit/offset math (12 tests).
   - `backend/tests/modules/search/test_search_endpoints.py` — unauthenticated 401, wrong-role 403, full
     200 round trip, empty-result shape, non-discoverable exclusion, radius 422s, category-optional browsing,
     and `GET /search/categories` scoping to discoverable providers + case-collapse (11 tests).
10. **Existing test call sites updated** (not new behavior, just constructor-signature follow-through) for
    every `ProviderService(...)` instantiation across the test suite — added `provider_search_repository=`
    and `portfolio_repository=` everywhere: `test_provider_service.py` (mocked), `test_provider_service_update.py`,
    `test_availability_service.py`, `test_portfolio_service.py`, `test_verification_service.py`,
    `test_admin_verification_service.py`.

## Environment note (not story-related, flagged for whoever runs tests next)

This sandbox's Python is `3.14.0rc2` (a pre-release build) and the installed `pydantic` (2.13.4, the latest
release at time of writing) is incompatible with it — importing `pydantic`/`pydantic_settings` at all raises
`TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`, breaking every test's
collection and any direct `alembic`/app invocation, reproducible on a clean checkout before any of this
story's changes. Added a small, clearly-commented, version-gated compatibility shim to the very top of
`backend/tests/conftest.py` (a no-op on any interpreter whose `typing._eval_type()` already accepts the
keyword) so the test suite actually runs. This is an environment defect, not a DIR-001 change — flagged for
`architect`/whoever owns CI to decide whether to keep the shim, pin a different Python, or remove it once a
compatible pydantic/Python 3.14 final ships.

## Full test results (last run)

`uv run pytest -q` → **476 passed** (443 pre-existing + 33 new), 1 pre-existing unrelated deprecation warning.
`uv run ruff check app tests` → all checks passed.
`uv run --with mypy mypy app` → 19 errors, all pre-existing (`app/core/context.py`, `security.py`,
`logging.py`, `middleware/logging_middleware.py`, `exceptions/handlers.py`,
`identity/services/id_token_verifier.py`, `audit/*`) — zero new errors from this story's code. (Note: `mypy`
is not in this project's `[dependency-groups].dev`, only `~/.local/bin/mypy` globally, which lacks this
project's dependencies for its `pydantic.mypy` plugin — ran via `uv run --with mypy mypy app` instead, an
ephemeral overlay, no `pyproject.toml`/`uv.lock` change.)

## What's done (mobile, complete)

17-18. **New `search` feature module** (`mobile/lib/features/search/`): `domain/models/search_result_provider.dart`,
   `category_option.dart`, `search_exception.dart`, `search_filters_args.dart`; `data/search_repository.dart`
   (`searchProviders(...)`, `listCategories()`), mapping every failure to a plain-language `SearchException`,
   mirroring `provider_repository.dart`/`saved_address_repository.dart`'s convention.
19. **`SearchFiltersScreen`** (`presentation/screens/search_filters_screen.dart`) — category chips (from
    `listCategories()`, plus an "All categories" chip clearing the filter), an origin-location field
    pre-filled from the customer's default saved address (via `SavedAddressRepository`, falling back to the
    first saved address if none is marked default, and left unset with zero saved addresses -- "Search"
    stays disabled until a location exists), editable via the existing, reusable `LocationCaptureField`
    (which itself wraps `LocationPickerScreen`/"use current location" from CUS-002 -- no new picker built), a
    radius slider (1-100 km, matching `SEARCH_MAX_RADIUS_KM`), and a single "Search" action.
20. **`SearchResultsScreen`** (S-08, `presentation/screens/search_results_screen.dart`) — provider cards,
    loading state, error state (with retry), pull-to-refresh, and Decision 7's two *textually distinct* empty
    states modeled as a real `SearchResultsStatus.idle` vs. `loaded`-with-empty-results distinction in
    `SearchResultsController` (not merely a synthetic test-only state) -- `idle` is genuinely reachable via
    `AppRoutes.searchResults` with no/invalid `extra` (the route renders `SearchResultsScreen(filters: null)`
    rather than redirecting, unlike `otpEntry`/`addressForm`'s `extra`-required redirect pattern), since
    Decision 7 frames "reached without filters applied" as part of this screen's own contract. Tap-through on
    a card shows a "coming soon" snackbar (S-09 doesn't exist yet) -- mirrors CUS-002's own precedent.
21. **`ProviderSearchCard`** (`presentation/widgets/provider_search_card.dart`) -- photo (falls back to a
    placeholder icon on a null `primaryPhotoUrl` or a load error), name, category labels, rating+count per
    Decision 2's rendering rule (`"No reviews yet"` vs. `"4.8 (3 reviews)"`, ICU plural for the count), and
    distance formatted as `"{n} m away"` under 1 km or `"{n} km away"` at/above 1 km. Renders exactly
    `SearchResultProvider`'s fields with no ranking-specific UI, so MAT-001 can reuse it unchanged.
22. **Controllers**: `SearchFiltersController`/`SearchResultsController` (both `StateNotifierProvider.
    autoDispose`, matching this codebase's established convention -- e.g. `StorefrontController` -- over the
    `AsyncNotifierProvider` shape used for simpler eager-fetch state, since both need explicit, multi-field
    state transitions no plain async fetch captures). No business logic in either screen widget.

## Deviations from the Plan, flagged for `tester`/`architect`

- **Item 19 says "the existing `SavedAddressRepository`"** -- `features/search/state/search_filters_controller.dart`
  imports `features/customer/data/saved_address_repository.dart` (and its `SavedAddress`/`SavedAddressException`
  models) directly, a `search -> customer` feature-to-feature edge. This exactly mirrors the *pre-existing*
  `home -> customer` edge already in `home_placeholder_screen.dart` (unchanged by this story) -- not a new
  category of coupling, and explicitly instructed by the Plan's own item 19 wording. Flagged per point 6's
  instruction to call out any cross-feature import reasoning: `features/search/` imports **only** from
  `customer` (this one, Plan-directed, precedented edge) and `shared/` (`ProviderType` from
  `shared/models/provider_type.dart`, per VER-001's fix) -- it never imports from `features/provider/` or
  `features/verification/`, confirmed by grep.
- **Decision 7's "pre-search" state is real, not test-only**: `AppRoutes.searchResults` accepts a missing/
  invalid `extra` as a supported state (renders the idle empty state) rather than redirecting away, unlike
  every other `extra`-required route in this router (`otpEntry`, `addressForm`, `verificationConfirm`). This
  is a deliberate, narrow exception to that pattern -- flagged for `architect` to confirm it reads as
  intentional rather than an inconsistency, given Decision 7's explicit "if reached without filters applied"
  framing.
- **No `SearchException`/error-copy util was explicitly named in the Plan's items 17-18**, but one was added
  (`domain/models/search_exception.dart`, `presentation/utils/search_error_copy.dart`) to match every other
  repository's established plain-language-failure convention (`ProviderException`/`SavedAddressException` +
  their own `*_error_copy.dart` utils) -- flagged as a consistency-driven addition, not scope creep.
- The now-orphaned `searchComingSoonMessage` l10n key (CUS-002's temporary snackbar, superseded by the real
  `SearchFiltersScreen` navigation) was removed from both `app_en.arb`/`app_ar.arb`, and
  `first_address_prompt_test.dart`'s second test was updated in place (asserts `SearchFiltersScreen` now
  renders, not the old snackbar text) rather than left stale -- no other call site referenced it.

## Full test results (mobile, this session)

Flutter SDK used: a pre-built 3.44.9 checkout found in the sandbox's scratchpad directory (no `flutter` on
`PATH` by default in this environment) -- `flutter pub get` / `analyze` / `test` all ran clean against it.

- `flutter analyze` -> **No issues found.**
- `dart format --output=none --set-exit-if-changed .` -> **0 files would change** (148 files, all
  already formatted).
- `flutter test` (full suite, not just this story's new tests) -> **144 passed**, 0 failed (134
  pre-existing + 10 new: 5 in `search_results_screen_test.dart`, 4 in `search_filters_screen_test.dart`, and
  1 pre-existing `first_address_prompt_test.dart` test updated in place to match the new navigation target
  rather than counted as "new").

## What's explicitly next

1. **`tester`** — verify all 7 ACs; particular attention per the Plan's own Delegation section to AC2's
   literal clause order (read `provider_search_repository.py`'s `_WHERE_CLAUSE` directly), AC6 (independently
   re-run `test_provider_search_repository.py::TestAC6QueryPlanUsesTheGistIndex`), AC7's reversed-insertion
   tie-break tests, and Decision 2's both-rating-states coverage (both backend and, now, mobile -- confirm
   `"0.0 (0 reviews)"` never appears anywhere in `provider_search_card.dart`'s rendering paths). Also verify
   AC4's mobile half: the pre-search and zero-results copy strings are genuinely distinct
   (`search_results_screen_test.dart` covers this, but an independent re-check is worth it given Decision
   7's subtlety).
2. **`architect`** — review Decision 4 (module placement) and Decision 8 (raw `text()` SQL, the `CAST(...
   AS text)` addition) as flagged above; also review the `ProviderService.get_primary_photo_urls`/
   `portfolio_repository` addition (item 5 above) for architectural soundness; review the mobile deviations
   flagged above (the `search -> customer` edge, and the `searchResults` route's non-redirecting `extra`
   handling).

## Files touched (backend)

New:
- `backend/alembic/versions/2026_09_09_0900-a3f6e9c21d47_enable_geospatial_extensions_and_indexes.py`
- `backend/app/modules/search/__init__.py`, `schemas.py`, `dependencies.py`, `api.py`,
  `services/__init__.py`, `services/search_service.py`
- `backend/app/modules/provider/repositories/provider_search_repository.py`
- `backend/tests/modules/provider/test_provider_search_repository.py`
- `backend/tests/modules/search/test_search_service.py`, `test_search_endpoints.py`

Modified:
- `backend/app/api/v1/api.py`, `app/core/config.py`, `app/core/exceptions/exceptions.py`,
  `app/core/exceptions/__init__.py`
- `backend/app/modules/customer/models.py`, `app/modules/provider/models.py` (docstrings only — no schema/
  `__table_args__` change; the GiST indexes are migration-only, deliberately not modeled as ORM `Index()`)
- `backend/app/modules/provider/dependencies.py`, `app/modules/provider/services/provider_service.py`
- `backend/app/modules/provider/repositories/portfolio_repository.py`,
  `provider_category_label_repository.py`
- `backend/tests/conftest.py` (environment shim, see above)
- `backend/tests/modules/provider/test_availability_service.py`, `test_portfolio_service.py`,
  `test_provider_service.py`, `test_provider_service_update.py`
- `backend/tests/modules/verification/test_admin_verification_service.py`, `test_verification_service.py`

## Files touched (mobile)

New:
- `mobile/lib/features/search/domain/models/search_result_provider.dart`, `category_option.dart`,
  `search_exception.dart`, `search_filters_args.dart`
- `mobile/lib/features/search/data/search_repository.dart`
- `mobile/lib/features/search/state/search_filters_controller.dart`, `search_results_controller.dart`
- `mobile/lib/features/search/presentation/screens/search_filters_screen.dart`,
  `search_results_screen.dart`
- `mobile/lib/features/search/presentation/widgets/provider_search_card.dart`
- `mobile/lib/features/search/presentation/utils/search_error_copy.dart`
- `mobile/test/features/search/fakes/fake_search_repository.dart`
- `mobile/test/features/search/search_filters_screen_test.dart`, `search_results_screen_test.dart`

Modified:
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (new `searchFilters`/`searchResults` routes)
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (`_onFindService` rewired to
  `AppRoutes.searchFilters` once a saved address exists; the AC5 address-required gate itself is unchanged)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new Search strings added; the now-orphaned
  `searchComingSoonMessage` key removed)
- `mobile/test/features/auth/first_address_prompt_test.dart` (its second test updated to assert navigation
  to `SearchFiltersScreen` instead of the retired snackbar; `searchRepositoryProvider` overridden with
  `FakeSearchRepository` for hermeticity)
