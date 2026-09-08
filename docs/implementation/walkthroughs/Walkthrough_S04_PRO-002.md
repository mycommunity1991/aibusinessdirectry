# Walkthrough S04 PRO-002

## Story: Manage My Provider Storefront

**Sprint:** 04 | **Story ID:** PRO-002 | **Priority:** High | **Status:** Done

As a provider, I want to upload portfolio photos, set my weekly availability, and edit my listing after
onboarding, so that my storefront stays current and represents my work well.

This is the second and final story of Sprint 4 ("Provider Storefront"), completing the Provider aggregate
(`portfolios`, `provider_availability`, a categories representation, `service_areas`) and delivering the
ongoing Storefront screen (S-25), distinct from PRO-001's one-time onboarding wizard. Full context,
architecture decisions, and file-by-file scope: `docs/implementation/plans/Plan_S04_PRO-002.md`.

---

## What was implemented

### Backend (`backend/app/modules/provider/`, `backend/app/shared/storage/`)

- **Migration `272b12ab9b2f_provider_storefront`** (down-revision `6133c77f062e`, PRO-001's head), verified
  upgrade/downgrade against a real, disposable scratch Postgres database with an actual data round-trip. Adds
  three tables exactly per `04_DATABASE.md`'s pre-existing Provider Domain spec — `provider.provider_availability`
  (`weekday`, `open_time`, `close_time`, `is_emergency_available`, `uq_provider_availability_provider_weekday`),
  `provider.portfolios` (`media_url`, `caption`, `sort_order`, `idx_portfolios_provider_id`), and
  `provider.service_areas` (`center_latitude`, `center_longitude`, `radius_meters`,
  `idx_service_areas_provider_id`) — plus one new table not in the original literal spec,
  `provider.provider_category_labels` (`provider_id`, `label VARCHAR(100)`, `is_primary`, partial unique index
  `uq_provider_category_labels_primary`). A new `weekday` enum is created scoped to the `provider` schema as its
  first consumer. The migration also backfills every existing `providers.category_label` value into
  `provider_category_labels` (`is_primary=true`) and then drops `providers.category_label` in the same
  migration — no dual representation left behind. Deliberately does **not** add the `cube`/`earthdistance`
  GiST index over `service_areas` (`04_DATABASE.md` Section 13) — no AC in this story performs a geospatial
  query; that begins with the future Search & Matching story.
- **Decision 1 — `provider_category_labels`, not `provider_categories`:** AC4 asks for "one or more categories
  via `provider_categories`, with exactly one marked primary" — language lifted from `04_DATABASE.md`'s
  Category Domain section, which specifies a hard FK to `category.categories.id`, a table that does not exist
  (Category taxonomy remains a critical-path, still-open decision, out of this story's reach). Rather than
  building a fake `categories` table or silently descoping AC4, this story adds a distinctly-named interim
  table, `ProviderCategoryLabel` (`backend/app/modules/provider/models.py`), storing free-text labels with no
  taxonomy validation — satisfying AC4's *structural* shape (multiplicity + exactly-one-primary) without
  pretending to build the real Category entity. "Exactly one primary" is enforced transactionally at the
  service layer (`ProviderCategoryLabelRepository.replace_all`: delete-existing-then-insert-new, one flush,
  mirroring `SavedAddressRepository.unset_other_defaults`'s precedent from CUS-002) with the partial unique
  index as defense-in-depth. Category labels are edited as part of `PATCH /providers/me`'s "basic info" section
  (capped at 5 labels — flagged, no AC specifies a number), never a per-label CRUD surface.
- **Decision 2 — `FileStorage` abstraction, `LocalFileStorage`, no S3 in this story:** this is the first story
  in the codebase needing any file-upload capability at all. A small, generic `FileStorage` protocol
  (`backend/app/shared/storage/interfaces.py`: `save(content, *, filename, subdirectory) -> str`,
  `delete(url_path) -> None`) decouples `PortfolioService` from any concrete storage backend. The only concrete
  implementation shipped is `LocalFileStorage` (`backend/app/shared/storage/local_file_storage.py`), writing
  under a new git-ignored `UPLOAD_DIR` setting (default `uploads/`), with blocking filesystem calls offloaded
  via `asyncio.to_thread`, served back to clients via a new `StaticFiles` mount at `/media` in `app/main.py`.
  Explicitly interim: no AWS credentials/bucket exist in this codebase or dev environment, even though
  `12_TECH_STACK.md` names AWS as the approved cloud provider architecturally — a future `S3FileStorage` can be
  added as one new class and one dependency-wiring change with zero changes to `PortfolioService`. Recorded as
  **ADR-017** (see below).
- **Upload validation** (`backend/app/shared/storage/image_validation.py`, satisfying AC2 and `06_SECURITY.md`'s
  File Upload Security section): rejects (422, via a new `InvalidPortfolioUploadError`, deliberately generic
  like `InvalidOtpError`'s non-revealing pattern) on oversized content (checked against the actual read byte
  length, against `MAX_PORTFOLIO_PHOTO_SIZE_BYTES`, default 5 MB), a disallowed original-filename extension, or
  a magic-byte content sniff (JPEG/PNG/WEBP signatures) that disagrees with the client-declared
  `Content-Type`. Deliberately uses only the standard library — no Pillow or other imaging dependency, since no
  AC requires thumbnailing/re-encoding, only validation. The stored filename is always server-generated
  (`{uuid4().hex}{validated_extension}`), never derived from the client's original filename, stored under
  `uploads/portfolios/{provider_id}/{generated_filename}` and exposed as
  `/media/portfolios/{provider_id}/{generated_filename}`.
- **Decision 3 — sub-resource endpoint shapes**, all reachable only under the existing `/providers/me`
  singleton (no `{provider_id}` anywhere in this domain, per ADR-015): `GET`/`POST /providers/me/portfolio`
  (unpaginated per ADR-012, capped at `MAX_PORTFOLIO_PHOTOS_PER_PROVIDER`, default 20; `POST` is
  `multipart/form-data`, one file + optional caption), `DELETE /providers/me/portfolio/{portfolio_id}`
  (genuinely `{id}`-addressable, so `ensure_owner_or_not_found` is load-bearing here per ADR-015), `PUT
  /providers/me/portfolio/order` (bulk reorder, Decision 4), `GET`/`PUT /providers/me/availability` (always
  returns exactly 7 synthesized weekday entries; `PUT` upserts up to 7 in one call — Create+Read+Update
  collapsed into `GET`+`PUT`, no per-weekday `PATCH`).
- **Decision 4 — portfolio reordering:** `PUT /providers/me/portfolio/order` accepts `{"ordered_ids": [...]}`
  — the caller's **full** ordered set of active photo ids. `PortfolioService.reorder` validates the submitted
  id set is exactly equal (same members, no more, no fewer, no duplicates) to the caller's own active photo ids
  before writing anything (422 on mismatch, never a partial reorder), then bulk-sets `sort_order` to each id's
  index in one flush.
- **Decision 5 — portfolio deletion is soft delete only:** `DELETE /providers/me/portfolio/{portfolio_id}`
  soft-deletes the row (mirrors `SavedAddressRepository.soft_delete` exactly) and does **not** delete the
  on-disk file in the same request — orphaned-file cleanup is a future administrative/retention job, out of
  scope here.
- **Decision 6 — AC6's "verified field" boundary made explicit, not implemented as code:** no field on the
  current schema is gated by verification today — `verification_status`/`is_discoverable` are never read or
  written by any endpoint in this story. `business_profiles.trade_license_number` is documented (not
  implemented) as the most plausible future candidate for a VER-001 re-verification trigger, once that story
  establishes an actual document-to-field linkage.
- **Decision 7 — bare `get_current_user`, not `require_role(ROLE_PROVIDER)`:** every new endpoint resolves the
  caller's Provider via `get_by_user_id` and raises `ProviderNotFoundError` (404) if none exists — an
  equivalent, correctly-scoped rejection with no security gap. This also avoids a caller who just finished
  PRO-001's onboarding wizard hitting a spurious 403 on their very first Storefront edit before their access
  token naturally refreshes (per ADR-016's documented token-refresh-lag consequence).
- **`PATCH /providers/me`** (new): applies `display_name`/`phone_*`/`whatsapp_number`/`description` (only
  fields present, `exclude_unset`), replaces `category_labels` transactionally if present (validating exactly
  one `is_primary=true` and the 5-label cap), and applies `business_details`/`freelancer_details` partial
  updates onto the caller's existing subtype profile — rejecting (400) if the payload's details object doesn't
  match the provider's actual `provider_type`. `provider_type` itself is never accepted by the schema.
  `service_areas` is kept in sync internally whenever a location/radius field changes, in the same flush — no
  direct API exposes `service_areas` for editing.
- **New services**: `PortfolioService` (`list_my_portfolio`, `add_photo`, `delete_photo`, `reorder`),
  `AvailabilityService` (`get_my_availability`, `update_my_availability`) — both under
  `backend/app/modules/provider/services/`. New repositories: `PortfolioRepository`,
  `ProviderAvailabilityRepository`, `ProviderCategoryLabelRepository`, `ServiceAreaRepository`.
- **`ProviderResponse.category_label: str` → `category_labels: list[CategoryLabelResponse]`** — a deliberate,
  coordinated breaking change to this still-young, non-public `/providers/me` response shape (Decision 1),
  acceptable because this API has no real external consumers yet and backend/mobile ship together in this
  story.
- **New exceptions**: `InvalidPortfolioUploadError` (422), `PortfolioPhotoNotFoundError` (404,
  ownership-collapsing per ADR-015), `PortfolioLimitExceededError` (409), `InvalidCategoryLabelsError` (422),
  `SubtypeDetailsMismatchError` (400).
- **Tests**: `test_portfolio_service.py`, `test_availability_service.py`, `test_provider_service_update.py`,
  extensions to `test_provider_endpoints.py`, and `backend/tests/shared/storage/test_image_validation.py` —
  covering upload validation (correct type succeeds; wrong extension, wrong MIME, oversized, and
  magic-byte-mismatched uploads all rejected), generated filenames never equalling the client's original
  filename, the 20-photo cap, portfolio reorder persistence (create 3, reorder, re-fetch, assert exact order —
  AC8), reorder rejecting a mismatched id set, soft-delete excluding a photo from subsequent lists while
  leaving the file on disk, the ownership boundary on delete/reorder (a second provider gets 404, not 200 —
  AC7/AC8), availability CRUD round-trips (`GET` before any `PUT` returns 7 synthesized closed entries; `PUT`
  upserts, not duplicates; a closed day has null hours), `PATCH /providers/me` partial-update semantics,
  category-label primary/cap validation, subtype-details mismatch rejection, and confirmation that no new
  endpoint in this story ever touches `verification_status`/`is_discoverable` (AC6).
- **347 backend tests passing** overall (up from 293 at the end of PRO-001), 0 regressions — independently
  re-run and confirmed by the `tester` agent from a clean shell. `ruff check`/`ruff format --check` both clean
  project-wide.
- **One mypy regression found and fixed during review** (commit `dcfd303`): the `tester` agent's strict-mypy
  pass surfaced a type-checking issue introduced by this story's code, which was fixed and independently
  re-verified clean by the tester before the architect's final pass.

### Mobile (`mobile/lib/shared/widgets/`, `mobile/lib/features/provider/`)

- **New shared `WeeklyHoursEditor` widget** (`mobile/lib/shared/widgets/weekly_hours_editor.dart`) — factored
  out of PRO-001's `business_details_screen.dart` private `_OperatingHoursRow`/weekday-list logic, extended
  with the per-weekday emergency-availability toggle this story adds, and reused by both the (untouched)
  onboarding screen and the new Storefront availability section — avoiding a second copy of the same UI.
- **`Provider.categoryLabel` (`String`) → `categoryLabels` (`List<CategoryLabel>`)** in
  `domain/models/provider.dart`, mirroring the backend's breaking response-shape change. New domain models:
  `portfolio_photo.dart`, `weekday_availability.dart`, `update_provider_request.dart`.
  `ProviderRepository` gains `updateProvider`, `listPortfolio`, `uploadPortfolioPhoto` (multipart),
  `deletePortfolioPhoto`, `reorderPortfolio`, `getAvailability`, `updateAvailability`.
- **New `storefront_screen.dart` (S-25)** — the ongoing Storefront/Edit Profile screen: four
  independently-saveable sections (basic info including category labels, subtype-specific details, portfolio
  manager, availability editor via the new shared `WeeklyHoursEditor`), each with its own Save action calling
  only the relevant repository method and per-section loading/success/error feedback. Backed by a new
  `storefront_controller.dart` state controller.
- **New `portfolio_manager.dart` widget** — list of existing photos with a remove action per photo and
  reorder support, an "Add Photo" action via the new `image_picker` dependency, empty-state copy. The picker is
  injectable so automated tests never depend on real plugin/platform-channel behavior
  (`fake_portfolio_image_picker.dart`).
- The Profile & Settings "List Your Business" tile's "you already have a listing" branch (PRO-001) now
  navigates to the new `storefront` route instead of only showing a snackbar.
- **Tests**: `storefront_screen_test.dart`, `portfolio_manager_test.dart`, and a new
  `weekly_hours_editor_test.dart` under `mobile/test/shared/widgets/` — each section saves independently,
  reorder produces the expected repository call with the new order, add/remove photo updates the visible list.
  `fake_provider_repository.dart` (existing, from PRO-001) extended with the new methods.
- **114 mobile tests passing** overall (up from 96 at the end of PRO-001), independently re-run and confirmed
  by the `tester` agent. `flutter analyze` clean, `dart format --set-exit-if-changed` clean.
- **New Flutter dependency**: `image_picker: ^1.2.3` (`mobile/pubspec.yaml`) — no existing image-picker
  capability was available to reuse; a well-established, widely-used package. Backfilled into
  `12_TECH_STACK.md` at story close (see below).

---

## Acceptance Criteria — Verification

All 8 acceptance criteria (from `Plan_S04_PRO-002.md`, sourced from the Tracker) were independently verified by
the `tester` agent — full suites re-run from a clean shell, migration reversibility re-derived against a
disposable scratch database with an actual data round-trip, and the ownership boundary confirmed by reading
the actual service code (not merely trusting the DB).

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `portfolios`, `provider_availability`, `provider_categories` (as the flagged `provider_category_labels` interim table), and `service_areas` tables exist via migration | Pass |
| 2 | Provider can add, remove, and reorder portfolio photos; each upload validated for MIME type, extension, and size; stored under a generated filename | Pass |
| 3 | Provider can set open/closed status and hours per weekday, plus a separate emergency/urgent-availability flag | Pass |
| 4 | Provider can belong to one or more categories via `provider_category_labels`, with exactly one marked primary | Pass |
| 5 | Storefront screen shows editable sections for basic info, subtype-specific details, portfolio, and availability, each independently saveable | Pass |
| 6 | Edits to basic info, hours, or portfolio do not require re-submitting verification (no field is currently gated; boundary documented for the future VER-001 story) | Pass |
| 7 | A provider cannot edit another provider's storefront (ownership enforced) | Pass |
| 8 | Automated tests cover portfolio reordering persistence, availability CRUD, and the ownership boundary | Pass |

---

## Architect Review — Findings and Resolution

The `architect` agent returned **APPROVED** — no must-fix items, no architectural-boundary violation.

1. **Decision 1 (`provider_category_labels` naming/shape)** — confirmed genuinely non-conflated with the
   reserved `provider_categories` name/shape in `04_DATABASE.md`; the "exactly one primary" transactional
   mechanism correctly mirrors CUS-002's `saved_addresses.is_default` precedent.
2. **Decision 2 (`FileStorage`/`LocalFileStorage`)** — confirmed sound against `06_SECURITY.md`'s File Upload
   Security section (server-generated filenames, magic-byte + extension + size validation, no trust of the
   original filename) and `02_ARCHITECTURE.md`'s "Infrastructure depends on Domain" dependency rule
   (`PortfolioService` depends on the `FileStorage` protocol, not `LocalFileStorage` directly).
3. **Decision 3/4 (endpoint shapes, reorder mechanism)** — confirmed correctly derived from ADR-015 (singleton
   vs. `{id}`-addressable collection rule) and a sound, atomic bulk-reorder design.
4. **Decision 7 (bare-auth gating)** — confirmed consistent with ADR-016's documented token-refresh-lag
   consequence; no security gap, since every endpoint still resolves and scopes strictly to the caller's own
   Provider.

### Non-blocking recommendation (1)

- A documentation-only recommendation regarding the story's own docs (not a code change) — see
  `docs/implementation/plans/Plan_S04_PRO-002.md` and this Walkthrough for the full decision record; nothing
  further to action against the shipped code.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-017**, the `FileStorage`/`LocalFileStorage` file-upload
  abstraction (this codebase's first file-upload capability), explicitly interim pending real AWS
  infrastructure.
- **`docs/AI/04_DATABASE.md`** — documented the four new tables (`portfolios`, `provider_availability`,
  `service_areas` confirmed as shipped exactly per the pre-existing spec; `provider_category_labels` newly
  documented as the flagged interim stand-in, distinct from the reserved `provider_categories` name/shape) and
  removed the now-dropped `providers.category_label` column entry (PRO-001's closeout had documented it; this
  migration drops it).
- **`docs/AI/12_TECH_STACK.md`** — backfilled `image_picker` into the Approved Flutter Packages list and noted
  `python-multipart` as now actually exercised (not merely documented as approved) by this story's file-upload
  endpoints.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 4 marked fully complete; Executive Summary, Current
  Backend Capabilities, Repository State, Current Limitations, Overall Progress, and Next Planned Story
  sections updated.
- `docs/CHANGELOG.md` — new entry under `[Unreleased]`.

### Flagged, not fixed by this closeout (outside tech-lead's tool access / ownership)

- `docs/AI/Project_Tracker.xlsx`'s Stories sheet still needs its PRO-002 row's Status updated from "Planned" to
  "Done" — requires the direct raw-XML cell-patching method established at PRO-001's closeout (a normal
  openpyxl load/save round-trip was found to silently drop this workbook's conditional-formatting extensions).
  Not performed here; no xlsx-editing tool is available to this agent.
- **`docs/AI/13_OPEN_DECISIONS.md` still does not exist anywhere in the repository**, despite being cited by
  name throughout `03_DOMAIN_MODEL.md`, `04_DATABASE.md`, `14_USER_FLOWS.md`, `15_SCREEN_INVENTORY.md`, and
  `PROJECT_IMPLEMENTATION_STATE.md` as the home of the "Category Taxonomy" critical-path open decision (item
  1) — the exact decision both `provider_category_labels` (this story) and `providers.category_label`
  (PRO-001, now dropped and superseded by this story) exist specifically to work around. This is a
  cross-story documentation gap, flagged for a separate follow-up; it is not this Plan's or this closeout's
  ownership to create (`tech-lead` owns `09_DECISIONS.md`, not `13_OPEN_DECISIONS.md`).

---

## Testing Performed

- `cd backend && uv run pytest -q` — **347/347 passing** (293 at the end of PRO-001 + new provider-storefront
  and image-validation tests), 0 regressions — independently re-run by the `tester` agent.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` —
  verified against a disposable scratch database (never the shared dev/test DB), including an actual data
  round-trip of the `category_label` → `provider_category_labels` backfill and back.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- One strict-mypy regression found by the `tester` agent was fixed (commit `dcfd303`) and independently
  re-verified clean.
- `cd mobile && flutter test` — **114/114 passing** (96 at the end of PRO-001 + new storefront/portfolio/
  weekly-hours-editor tests) — independently re-run by the `tester` agent.
- `cd mobile && flutter analyze` — no issues found.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean.
- `tester` agent: all 8 ACs independently verified with direct evidence — see table above.
- `architect` agent: APPROVED, no must-fix items — see findings above.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_08_1100-272b12ab9b2f_provider_storefront.py` (new)
- `backend/app/modules/provider/models.py` — adds `Weekday`, `ProviderAvailability`, `Portfolio`,
  `ServiceArea`, `ProviderCategoryLabel`; removes `Provider.category_label`
- `backend/app/modules/provider/repositories/{portfolio_repository,provider_availability_repository,provider_category_label_repository,service_area_repository}.py` (new)
- `backend/app/modules/provider/services/{portfolio_service,availability_service}.py` (new);
  `provider_service.py` — adds `update_basic_info`, `get_category_labels`
- `backend/app/modules/provider/schemas.py` — `UpdateProviderRequest`, `CategoryLabelInput`/
  `CategoryLabelResponse`, `PortfolioPhotoResponse`, `ReorderPortfolioRequest`,
  `WeekdayAvailabilityInput`/`Response`, `UpdateAvailabilityRequest`; `ProviderResponse.category_labels`
- `backend/app/modules/provider/api.py` — `PATCH /providers/me`; `GET`/`POST /providers/me/portfolio`,
  `DELETE /providers/me/portfolio/{portfolio_id}`, `PUT /providers/me/portfolio/order`; `GET`/`PUT
  /providers/me/availability`
- `backend/app/modules/provider/dependencies.py` — new repository/service providers, `get_file_storage`
- `backend/app/shared/storage/{interfaces,local_file_storage,image_validation}.py` (new)
- `backend/app/core/config.py` — `UPLOAD_DIR`, `MAX_PORTFOLIO_PHOTO_SIZE_BYTES`,
  `MAX_PORTFOLIO_PHOTOS_PER_PROVIDER`
- `backend/app/main.py` — `/media` `StaticFiles` mount
- `backend/app/core/exceptions/{exceptions.py,__init__.py}` — `InvalidPortfolioUploadError`,
  `PortfolioPhotoNotFoundError`, `PortfolioLimitExceededError`, `InvalidCategoryLabelsError`,
  `SubtypeDetailsMismatchError`
- `backend/tests/modules/provider/{test_portfolio_service,test_availability_service,test_provider_service_update}.py` (new); `test_provider_endpoints.py` (extended)
- `backend/tests/shared/storage/test_image_validation.py` (new)

### Mobile
- `mobile/lib/shared/widgets/weekly_hours_editor.dart` (new)
- `mobile/lib/features/provider/domain/models/{provider,portfolio_photo,weekday_availability,update_provider_request}.dart`
- `mobile/lib/features/provider/data/provider_repository.dart` — new methods
- `mobile/lib/features/provider/state/storefront_controller.dart` (new)
- `mobile/lib/features/provider/presentation/screens/storefront_screen.dart` (new)
- `mobile/lib/features/provider/presentation/widgets/portfolio_manager.dart` (new)
- `mobile/pubspec.yaml` — `image_picker: ^1.2.3`
- `mobile/test/shared/widgets/weekly_hours_editor_test.dart` (new)
- `mobile/test/features/provider/{storefront_screen_test,portfolio_manager_test}.dart` (new)
- `mobile/test/features/provider/fakes/fake_portfolio_image_picker.dart` (new);
  `fake_provider_repository.dart` (extended)

---

## Follow-up Notes for Sprint Planning

- **Sprint 4 (Provider Storefront) is now complete** — both PRO-001 and PRO-002 have shipped and been signed
  off.
- Non-blocking follow-ups carried forward: `mypy` still not fully wired as a standard, always-run dev-tool gate
  in the same way `ruff` is (this story's one regression was caught by the `tester` agent's own strict-mypy
  pass, not an automated gate); orphaned on-disk file cleanup for soft-deleted portfolio photos remains a
  future administrative/retention job; the `cube`/`earthdistance` geospatial index over `service_areas` is
  deferred to the future Search & Matching story.
- **Cross-story documentation gap, flagged for follow-up outside this story**: `docs/AI/13_OPEN_DECISIONS.md`
  still does not exist, despite being cited by name across multiple `docs/AI/` documents as the home of the
  "Category Taxonomy" critical-path decision (item 1) that both this story's `provider_category_labels` and
  PRO-001's now-superseded `providers.category_label` exist to work around.
- The real Category domain (`categories`/`category_question_templates`/`provider_categories`) remains the
  critical-path open decision blocking the AI intake work — a future story is expected to reconcile
  `provider_category_labels` with the real taxonomy once that domain ships.
- **Next up: Sprint 5 (Provider Verification)**, first story **VER-001**. Per the Plan's own Verified Current
  State, VER-001 depends on PRO-001 (not on PRO-002) — PRO-002 shipping does not itself newly unblock VER-001,
  but does not block it either; VER-001 was already unblocked once PRO-001 shipped. See
  `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` Section 17 for the current statement of this and a caveat on
  confidence in the tracker's exact dependency wiring.
