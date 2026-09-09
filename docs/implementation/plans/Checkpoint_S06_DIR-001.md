# Checkpoint — Sprint 06, DIR-001 (Browse Nearby Providers by Category and Location)

**Owner of this checkpoint:** `backend` (most recent update)
**Status:** Backend implementation (Plan items 1-16) complete. Awaiting `frontend` (mobile, items 17-27),
then `tester`, then `architect`.

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

## What's explicitly next

1. **`frontend`** — mobile items 17-27 (Search Filters screen, Search Results screen S-08, provider card,
   repository/models/controllers, `HomePlaceholderScreen` rewire, routing, mobile tests). Backend endpoints
   are live: `GET /api/v1/search/providers`, `GET /api/v1/search/categories`.
2. **`tester`** — verify all 7 ACs; particular attention per the Plan's own Delegation section to AC2's
   literal clause order (read `provider_search_repository.py`'s `_WHERE_CLAUSE` directly), AC6 (independently
   re-run `test_provider_search_repository.py::TestAC6QueryPlanUsesTheGistIndex`), AC7's reversed-insertion
   tie-break tests, and Decision 2's both-rating-states coverage.
3. **`architect`** — review Decision 4 (module placement) and Decision 8 (raw `text()` SQL, the `CAST(...
   AS text)` addition) as flagged above; also review the `ProviderService.get_primary_photo_urls`/
   `portfolio_repository` addition (item 5 above) for architectural soundness.

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
