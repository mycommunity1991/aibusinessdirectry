# Plan for Story PRO-002 — Manage My Provider Storefront

**Sprint:** 04 (Provider Storefront) | **Epic:** ML4-EP01 | **Priority:** High | **Depends On:** PRO-001 (done, merged to this branch)

---

## Story

As a provider, I want to upload portfolio photos, set my weekly availability, and edit my listing after
onboarding, so that my storefront stays current and represents my work well.

This story completes the provider aggregate (`portfolios`, `provider_availability`, a categories
representation, `service_areas`) and delivers the ongoing Storefront screen (S-25), distinct from PRO-001's
one-time onboarding wizard. It frames the provider profile as the provider's free digital storefront, per the
product's positioning (`03_DOMAIN_MODEL.md`).

**Scope boundary:** does not include visibility analytics (LEAD-002/S-26) or leads (LEAD-001/S-24) — limited
strictly to editing the storefront's own content. Does not include the Verification gate itself (VER-001) —
`verification_status`/`is_discoverable` remain exactly as PRO-001 set them; this story only documents which
fields *would* interact with a future verification re-check. Does not include the real Category taxonomy
domain (`category.categories`, `category_question_templates`) — still an open decision (see Decision 1). Does
not include Claim-Your-Listing or the Provider Dashboard (S-23)/Leads (S-24)/Visibility Analytics (S-26)
screens.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`)

1. `portfolios`, `provider_availability`, `provider_categories`, and `service_areas` tables exist via migration.
2. Provider can add, remove, and reorder portfolio photos; each upload is validated for MIME type, extension,
   and size, and stored under a generated (never user-supplied) filename.
3. Provider can set open/closed status and hours per weekday, plus a separate emergency/urgent-availability
   flag.
4. Provider can belong to one or more categories via `provider_categories`, with exactly one marked primary.
5. Storefront screen shows editable sections for basic info, subtype-specific details, portfolio, and
   availability, each independently saveable.
6. Edits to basic info, hours, or portfolio do not require re-submitting verification unless the change affects
   a verified field — that boundary is explicitly documented in this story's implementation notes.
7. A provider cannot edit another provider's storefront (ownership enforced).
8. Automated tests cover portfolio reordering persistence, availability CRUD, and the ownership boundary.

---

## Verified Current State (read directly from code and docs, not assumed)

- `docs/AI/04_DATABASE.md` already fully specifies `provider.portfolios` (`media_url`, `caption`, `sort_order`),
  `provider.provider_availability` (`weekday`, `open_time`, `close_time`, `is_emergency_available`, unique on
  `(provider_id, weekday)`), and `provider.service_areas` (`center_latitude`, `center_longitude`,
  `radius_meters`) column-by-column — nothing to design at the column level for these three. `provider_categories`
  is specified too, but **in the Category Domain section**, as `(provider_id, category_id, is_primary)` with
  `category_id` a hard FK to `category.categories.id` — a table that does not exist (see Decision 1).
- **`docs/AI/13_OPEN_DECISIONS.md` is cited by name throughout `03_DOMAIN_MODEL.md`, `04_DATABASE.md`,
  `14_USER_FLOWS.md`, `15_SCREEN_INVENTORY.md`, and `PROJECT_IMPLEMENTATION_STATE.md` (as the home of the
  "Category Taxonomy" critical-path open decision, item 1), but the file does not exist anywhere under
  `docs/AI/`** — confirmed by directory listing and a direct read attempt. This is a pre-existing documentation
  gap, not introduced by this story; it is flagged here because Decision 1 below leans on "Category taxonomy is
  an open, unresolved, critical-path decision" as its premise, and that premise is currently undocumented in
  the one place every other doc points to. Recommend this gap be raised to the user/CTO for a follow-up fix —
  outside this Plan's ownership (`tech-lead` owns `09_DECISIONS.md`, not `13_OPEN_DECISIONS.md`).
- `backend/app/modules/provider/` (PRO-001) currently has: `models.py` (`Provider`, `BusinessProfile`,
  `FreelancerProfile` — no portfolio/availability/category/service-area models yet), one repository per model,
  `ProviderService` (`get_my_provider`, `create_provider`, `get_subtype_profiles`), `schemas.py`
  (`CreateProviderRequest`/`ProviderResponse` and subtype request/response pairs — **no update schema exists**),
  `api.py` (`GET`/`POST /providers/me` only — **no `PATCH`, no sub-resource routes**), `dependencies.py`. This
  story adds to this module rather than creating a new one.
- **No file-upload/storage capability exists anywhere in this codebase.** Confirmed by search: no `boto3`, no
  S3 client, no `StaticFiles` mount, no upload directory, no image-validation utility. `python-multipart` is
  already an approved dependency (`12_TECH_STACK.md`, added at Sprint 1 for FastAPI's own multipart form
  parsing support) but has never actually been exercised by any endpoint yet. `backend/app/core/config.py` has
  no AWS/S3 settings of any kind — `12_TECH_STACK.md` lists AWS as the approved cloud provider architecturally,
  but no AWS credentials, bucket, or SDK integration exist in this codebase or this environment. This story is
  the first to need file upload at all (see Decision 2).
- `backend/app/core/authorization.py`'s `ensure_owner_or_not_found` and ADR-015's shape rule (`/me` singleton
  vs. `{id}`-addressable collection) are directly reusable, unchanged.
- `backend/app/repositories/base_repository.py`'s generic `update()` and `create()` are reusable as-is for the
  new repositories this story adds.
- `backend/app/modules/customer/repositories/saved_address_repository.py`'s `unset_other_defaults` (bulk
  `UPDATE ... WHERE`, flush-only, called before the write that sets the new default, same transaction) is the
  direct precedent for this story's "exactly one primary category" and portfolio-reorder mechanics (see
  Decisions 1 and 5).
- `backend/app/modules/customer/repositories/saved_address_repository.py`'s `soft_delete` (sets
  `deleted_at`/`is_active`, flush only, never a hard `session.delete()`) is the precedent this story follows for
  portfolio-photo deletion (Decision 5) — `04_DATABASE.md`'s Soft Delete section states deletion is never
  permanent except as an administrative operation, and `portfolios` carries the full `CommonColumnsMixin`
  (`deleted_at`/`is_active` included), so nothing about its schema suggests a different (hard-delete) treatment
  here.
- `mobile/lib/features/provider/presentation/screens/business_details_screen.dart` (PRO-001) already contains a
  complete, working weekly operating-hours editor (`_OperatingHoursRow`, per-weekday open/close toggle + time
  pickers) — currently private to that screen, not factored out. This story's availability editor needs
  materially the same UI (per-weekday toggle + times, plus an emergency flag) and should factor this out into a
  shared widget rather than duplicate it a second time (`08_CODING_STANDARDS.md`'s "no duplicate widgets" rule)
  — flagged for `frontend` (see Mobile Proposed Changes).
- `mobile/lib/features/provider/domain/models/provider.dart`'s `Provider.categoryLabel` (singular `String`) and
  the backend's `ProviderResponse.category_label` (singular) will both need to become a `categoryLabels`
  list-shaped field (Decision 1) — a deliberate, coordinated breaking change to this still-young, non-public
  `/providers/me` response shape. Acceptable because this API has no real external consumers yet (pre-launch,
  `05_API_GUIDELINES.md`'s "breaking changes require versioning" is aimed at a live, versioned API surface with
  real consumers to protect — not yet the case here) and because backend and mobile ship together in this same
  story.
- `backend/app/modules/provider/models.py`'s `Provider.category_label VARCHAR(100) NOT NULL` (PRO-001, Decision
  4) is the direct precedent this story's Decision 1 extends rather than replaces with something unrelated.

---

## Architecture Decisions

### Decision 1 — `provider_categories`/Category-domain gap: a distinctly-named, flagged interim table (`provider_category_labels`), not a fake `categories` table, not a silent AC descope

**The problem, stated precisely:** AC4 asks for "one or more categories via `provider_categories`, with exactly
one marked primary" — language lifted directly from `04_DATABASE.md`'s Category Domain section, which specifies
`provider_categories(provider_id, category_id, is_primary)` with a hard FK to `category.categories.id`. That
table does not exist, and building it is explicitly out of this story's reach: Category taxonomy is described
everywhere it's mentioned (`03_DOMAIN_MODEL.md`, `PROJECT_IMPLEMENTATION_STATE.md`) as a **critical-path,
still-open decision that blocks the entire AI question-flow design** — a genuinely separate, larger body of work
(taxonomy design, bilingual names, `category_question_templates`), not something to backfill as a side effect of
a storefront-editing story.

**Chosen:** add a new table, `provider.provider_category_labels` (`provider_id` FK, `label VARCHAR(100) NOT
NULL`, `is_primary BOOLEAN NOT NULL DEFAULT false`, full `CommonColumnsMixin`) — deliberately **not** named
`provider_categories`, so no future reader mistakes it for the real join table `04_DATABASE.md` already reserves
that name for. It stores free-text labels (e.g. "Plumbing", "AC Repair") with no taxonomy validation, exactly
extending PRO-001 Decision 4's already-flagged `category_label` mechanism from a single string to a small,
provider-owned list with a primary flag — satisfying AC4's *structural* shape (multiplicity + exactly-one-
primary) without inventing or pretending to build the real Category entity. "Exactly one primary" is enforced
the same way `saved_addresses.is_default` is (Decision 1, `Plan_S03_CUS-002.md`): transactionally at the service
layer (unset-then-set within one flush) with a partial unique index,
`uq_provider_category_labels_primary (provider_id) WHERE is_primary = true`, as defense-in-depth.

**Migration path:** the existing `providers.category_label` column's data is migrated into this new table (one
`INSERT ... SELECT id, category_label, true FROM provider.providers`, marking the pre-existing value as primary)
and the `providers.category_label` column is then dropped in the same migration — no dual representation is
left behind. This codebase has no production data to protect yet, so a clean replacement is safe and simpler
than maintaining both.

**Editing surface:** category labels are edited as part of the "basic info" section (AC5 names only four
sections — basic info, subtype-specific details, portfolio, availability — with no fifth "categories" section;
category was captured as part of basic info in PRO-001's wizard too, so this is consistent placement, not a new
concept). `PATCH /providers/me`'s optional `category_labels` field, when present, replaces the provider's entire
label set transactionally (delete existing rows, insert the new set) — a small, bounded list (capped at 5 —
flagged, no AC specifies a number; chosen to prevent unbounded abuse of a free-text field with no taxonomy
gate), never a per-label CRUD surface (no AC requires editing one label independently of the set).

**Future migration path (unchanged from PRO-001 Decision 4, just updated for the plural shape):** once the real
Category domain ships, a follow-up story is expected to fuzzy-match/admin-reconcile
`provider_category_labels.label` values into real `provider_categories` rows referencing `category.categories`,
and either retire this interim table or keep it as a free-text fallback/search-boost field alongside the real
relationship — that migration design is deliberately deferred, not decided here, exactly as PRO-001 Decision 4
already deferred it.

**Alternatives considered and rejected:**
- **Build `category.categories` now, even minimally, to satisfy the FK** — rejected outright per the explicit
  task instruction and because Category taxonomy is a genuinely larger, separate decision (bilingual names,
  question templates, taxonomy shape) that this story has no mandate to resolve as a side effect.
- **Leave `category_label` singular and treat AC4 as fully blocked/descoped, doing nothing** — rejected: it
  under-delivers what's actually achievable (multiplicity + primary flag is buildable today without a real
  taxonomy) and leaves a plainly-testable AC unaddressed when a reasonable, honest partial implementation
  exists. This alternative would be the right call only if even the *structural* shape (list + primary) were
  somehow unbuildable without real categories — it isn't.
- **A JSONB array column on `providers` (`category_labels: [{"label": ..., "is_primary": ...}]`)** — rejected:
  this codebase's convention for a genuinely relational, independently-queryable concept (a provider having
  *multiple* rows of the same shape) is a real child table (see `portfolios`, `provider_availability` — never a
  JSON array of structured objects), and a JSONB array would make the primary-uniqueness constraint
  unenforceable at the database level entirely (no partial-index equivalent inside a JSONB blob).

### Decision 2 — File upload/storage: local filesystem under a git-ignored directory, behind a `FileStorage` interface, no S3 in this story

**The problem:** AC2 requires MIME/extension/size-validated uploads stored under a generated filename — this is
the first story in the codebase needing any file-upload capability at all (Verified Current State). `12_TECH_STACK.md`
names AWS as the approved cloud provider, but no AWS SDK, credentials, or bucket configuration exist anywhere in
this codebase or this development environment.

**Chosen:** a small, generic `FileStorage` protocol under `backend/app/shared/storage/interfaces.py` (`async def
save(self, content: bytes, *, filename: str, subdirectory: str) -> str` returning a served, relative URL path;
`async def delete(self, url_path: str) -> None`), with exactly one concrete implementation for this story,
`LocalFileStorage` (`backend/app/shared/storage/local_file_storage.py`), writing under a new `UPLOAD_DIR` setting
(default `uploads/`, git-ignored) on the local filesystem, and served back to clients via a `StaticFiles` mount
at `/media` in `main.py`. `PortfolioService` depends on the `FileStorage` protocol, not `LocalFileStorage`
directly, so a future story can introduce `S3FileStorage` (once real AWS credentials/bucket provisioning exist
in this environment) by adding one new class and one dependency-wiring change, with zero changes to
`PortfolioService` itself.

This is a genuinely new infrastructure capability and is flagged for an ADR at story close (next available:
**ADR-017**), mirroring how PRO-001 flagged its own new cross-module mechanism as ADR-016.

**Validation (`backend/app/shared/storage/image_validation.py`, satisfying AC2 and `06_SECURITY.md`'s File
Upload Security section):**
- **Size:** reject (422) if the uploaded content exceeds a new `MAX_PORTFOLIO_PHOTO_SIZE_BYTES` setting (default
  5 MB) — checked against actual read byte length, not a client-declared `Content-Length` header.
- **Extension:** the *original* client-supplied filename's extension is checked only against an allow-list
  (`.jpg`, `.jpeg`, `.png`, `.webp`) for rejection purposes — it is never used to construct the stored filename
  or path (06_SECURITY.md: "Original filenames must never be trusted").
- **MIME type:** both the client-declared `UploadFile.content_type` **and** a magic-byte sniff of the first
  bytes of the actual content (checking for the JPEG/PNG/WEBP file signatures) must agree with an allowed image
  type; a mismatch (e.g. a `.jpg`-named file whose bytes are actually an executable) is rejected. This uses only
  Python's standard library (byte-signature comparison) — deliberately **not** adding Pillow or another new
  image-processing dependency, since `08_CODING_STANDARDS.md`/`12_TECH_STACK.md` both call for minimizing new
  dependencies and no AC requires thumbnailing/re-encoding, only validation. If virus scanning or
  thumbnail-generation is added in a future story (`06_SECURITY.md` already flags malware scanning as a "future
  enhancement"), that is the natural point to reconsider adding an imaging library.
- **Filename:** always server-generated — `f"{uuid4().hex}{extension}"` where `extension` comes from the
  *validated* detected type (not the client's original filename), stored under
  `uploads/portfolios/{provider_id}/{generated_filename}` on disk, exposed to clients as
  `/media/portfolios/{provider_id}/{generated_filename}` (a relative URL path — never an absolute filesystem
  path, per `06_SECURITY.md`'s "never expose... server paths").
- New exception: `InvalidPortfolioUploadError` (422, plain message — generic like `InvalidOtpError`'s
  non-revealing pattern: never states exactly which check failed, e.g. size vs. type, to avoid giving a bad
  actor a probing oracle).

**Alternatives considered and rejected:**
- **Real AWS S3 integration now** — rejected: no AWS credentials, bucket, or IAM configuration exist in this
  environment; building against a cloud resource that cannot actually be provisioned or tested here would be
  unverifiable, unrequested infrastructure work, not a Sprint-4 storefront story. Explicitly flagged as the
  natural next step once real AWS infrastructure exists.
- **Storing the image bytes directly in Postgres (`bytea`)** — rejected: `04_DATABASE.md`'s own
  `verification_documents.file_url` precedent already establishes "stored file reference, not the file itself"
  as this codebase's convention for uploaded files; no reason to deviate for portfolios.
- **Pillow-based content sniffing** — rejected for now per the dependency-minimization reasoning above; a
  magic-byte check is sufficient to satisfy AC2's "validated for MIME type" requirement without a new package.
- **Hard-deleting the on-disk file immediately on photo removal** — rejected in favor of leaving the file
  in place when the DB row is soft-deleted (see Decision 5); orphaned-file cleanup is a future administrative
  concern, not blocking this story.

### Decision 3 — Endpoint shapes for portfolio and availability sub-resources: `/providers/me/portfolio[...]` and `/providers/me/availability`, following ADR-015 exactly

Neither sub-resource is itself 1:1 with the account (a provider can have zero-to-many portfolio photos; up to
seven availability rows), so per ADR-015 both are collection-shaped, not singleton-shaped — but both are
addressed underneath the existing `/providers/me` singleton (there is no `{provider_id}` anywhere in this
domain's routes; PRO-001 already established there is no route shape through which a caller can address a
*different* provider at all):

- `GET /providers/me/portfolio` — lists the caller's own active photos, ordered by `sort_order`. Deliberately
  unpaginated, citing **ADR-012**: a provider's realistic portfolio size is small and owner-scoped (capped at 20
  — flagged, no AC specifies a number; chosen as a sensible storefront-photo ceiling, enforced at the service
  layer on `POST`), not a platform-wide or unbounded-growth collection.
- `POST /providers/me/portfolio` — `multipart/form-data` (one file + optional caption per call — the simplest
  shape; a multi-file batch endpoint is not requested by any AC and would complicate partial-failure handling
  for no stated benefit). Appends the new photo at `sort_order = max(existing) + 1`.
- `DELETE /providers/me/portfolio/{portfolio_id}` — genuinely `{id}`-addressable (a specific photo among many),
  so per ADR-015 this **is** where `ensure_owner_or_not_found` is required and load-bearing — this is the
  concrete endpoint AC7's/AC8's "ownership boundary" test targets (a second provider account must not be able to
  delete another provider's photo by guessing/reusing its id).
- `PUT /providers/me/portfolio/order` — reorder mechanism (see Decision 4).
- `GET /providers/me/availability` — always returns exactly seven entries (one per weekday), synthesizing
  "closed, not yet configured" for any weekday without a row yet, so the mobile client never has to handle a
  variable-length response.
- `PUT /providers/me/availability` — accepts up to seven weekday entries in one call and **upserts** each
  (creates a missing row, updates an existing one) in a single flush — not incremental
  per-weekday `PATCH`es. AC8's "availability CRUD" is satisfied as Create+Read+Update collapsed into
  `GET`+`PUT`, since availability's realistic editing pattern (per `15_SCREEN_INVENTORY.md`'s "availability
  editor," a single weekly form) is "edit the whole week and save," not per-day incremental mutation; a day
  being "closed" is expressed by `open_time`/`close_time` both null on that weekday's row, never by the row's
  absence, so no separate `DELETE` is needed for availability.

**Alternatives considered and rejected:**
- **`/providers/{provider_id}/portfolio`** — rejected: would introduce the very route shape PRO-001 deliberately
  avoided (a client-suppliable provider id with no legitimate use, since a caller can only ever have one
  Provider); every sub-resource in this domain stays reachable only through the caller's own `/me` anchor.
- **Per-weekday `PATCH /providers/me/availability/{weekday}`** — rejected: adds a genuinely `{id}`-addressable
  (well, `{weekday}`-addressable) shape and its own ownership-check boilerplate for a fixed, seven-value set that
  the UI edits as a whole; the bulk `PUT` is simpler and matches how the screen is actually used, per
  `08_CODING_STANDARDS.md`'s "prefer the simpler solution."
- **A generic `PATCH /providers/me/portfolio/{portfolio_id}` for reordering (send a new `sort_order` per item,
  one call per item)** — rejected: N sequential calls to reorder a list of N items is both chattier and more
  race-prone (a client reordering 5 photos by dragging one to a new position would otherwise need up to 5 network
  calls, each independently retriable, with no atomicity across them) than one call carrying the full new order.

### Decision 4 — Portfolio reordering mechanism: explicit `sort_order` column (already in `04_DATABASE.md`) plus a dedicated bulk reorder endpoint accepting an ordered list of ids

`04_DATABASE.md`'s `portfolios.sort_order SMALLINT DEFAULT 0` already exists in the schema spec — no new column
is needed. `PUT /providers/me/portfolio/order` accepts `{"ordered_ids": [uuid, uuid, ...]}` — the **full**
ordered set of the caller's own active photo ids — and `PortfolioService.reorder` validates that the submitted
id set is exactly equal (same members, no more, no fewer, no duplicates) to the caller's own active photo ids
before writing anything; on success, each id's `sort_order` is set to its index in the list, in one bulk
operation/flush (mirrors `unset_other_defaults`'s single-flush bulk-`UPDATE` pattern from CUS-002). A mismatched
set (a foreign id, a missing id, a duplicate) is rejected (422) before any row is touched — never a partial
reorder. This is the concrete mechanism AC8's "portfolio reordering persistence" test targets: create three
photos, reorder them, `GET` again, and assert the returned order matches exactly what was submitted.

### Decision 5 — Portfolio photo deletion: soft delete (DB row), on-disk file left in place

`portfolios` carries the full `CommonColumnsMixin` (`deleted_at`/`is_active` included) — nothing about its
schema suggests different treatment from `saved_addresses`' established soft-delete convention
(`04_DATABASE.md`'s Soft Delete section: "permanent deletion is an administrative operation"). `DELETE
/providers/me/portfolio/{portfolio_id}` soft-deletes the row (mirrors `SavedAddressRepository.soft_delete`
exactly) and does **not** delete the underlying file from storage in the same request — orphaned-file cleanup
for soft-deleted photos is a future administrative/retention job, out of this story's scope, and leaving the
file in place avoids any race with a future "Undo" affordance the mobile team may add (per
`16_UX_GUIDELINES.md`'s "reversible actions... use an Undo snackbar" pattern, already used for saved-address
deletion in CUS-002) without this story having to build that Undo flow itself.

### Decision 6 — AC6's "verified field" boundary: no field is currently gated, one field (`trade_license_number`) is flagged as the future candidate

VER-001 (Verification) has not shipped — there is no `verification_records`-to-`providers`-field linkage of any
kind in the schema today, and `providers.verification_status`/`is_discoverable` are set exactly once at
creation (PRO-001) with no update path anywhere. Given that, "a change that affects a verified field" is
currently an **empty set** in practice — there is no field on `providers`/`business_profiles`/
`freelancer_profiles` that has ever actually been checked against a verification document, because no
verification document upload/OCR/review exists yet.

**Decision, made explicit rather than left implicit:**
- **Today:** `PATCH /providers/me` and every sub-resource endpoint in this story never read or write
  `verification_status`/`is_discoverable` at all — editing basic info, hours, portfolio, or category labels has
  zero interaction with verification state, satisfying AC6's literal requirement (no re-verification is ever
  triggered, because nothing in this story's surface can trigger it).
- **Documented placeholder rule for the future VER-001 story (not implemented here):** the one field on the
  current schema that conceptually resembles a "verified" field — one that a real verification document would
  plausibly attest to — is `business_profiles.trade_license_number`. Once VER-001 ships and establishes an
  actual document-to-field linkage, editing this field is the most likely candidate to warrant flipping
  `verification_status` back to `pending` (and `is_discoverable` to `false`) until re-approved. Every other
  editable field in this story (`display_name`, `phone_*`, `whatsapp_number`, `description`, `category_labels`,
  operating hours, delivery radius, base location/service radius, skills, years of experience, portfolio
  photos, availability) has no plausible verification linkage today or in the documented future design, and is
  therefore freely editable with no re-verification concern, now or later.
- This placeholder rule is deliberately **not implemented as code** in this story (no field-level "requires
  re-verification" flag or trigger exists) — it is a documented expectation for whoever implements VER-001,
  consistent with the task's instruction to be explicit about what's realistic to enforce now versus what must
  be deferred.

### Decision 7 — Endpoint authentication: bare `get_current_user`, not `require_role(ROLE_PROVIDER)`

All new endpoints in this story (`PATCH /providers/me`, and every `/providers/me/portfolio*`/
`/providers/me/availability` route) are gated by bare authentication only, mirroring PRO-001's own choice for
`GET`/`POST /providers/me` — **not** `require_role(ROLE_PROVIDER)`. Two reasons: (1) every one of these
endpoints already resolves the caller's Provider via `get_by_user_id(current_user.id)` and raises
`ProviderNotFoundError` (404) if none exists — a caller without a Provider gets an equivalent, correctly-scoped
rejection with no security gap from skipping the role check; (2) per ADR-016's own documented consequence, a
caller's JWT is issued *before* `ROLE_PROVIDER` is granted and only reflects it after their next token refresh —
requiring the role here would risk a caller who just finished PRO-001's onboarding wizard hitting a spurious 403
on their *very first* Storefront edit, before their access token has naturally refreshed. Relying on the
existing 404-on-missing-provider check avoids this edge case entirely while providing equivalent protection.

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration, `provider_storefront` (down-revision = current head at implementation time — confirm
   via `alembic heads`; last known head is PRO-001's `6133c77f062e_provider_domain`). Adds:
   - `provider.provider_availability` — exactly per `04_DATABASE.md`'s spec (`provider_id`, `weekday` enum,
     `open_time`, `close_time`, `is_emergency_available`), plus `uq_provider_availability_provider_weekday`. A
     new `weekday` enum scoped to the `provider` schema (first consumer — flagged in a code comment for any
     future domain needing it to reuse via `create_type=False`, mirroring PRO-001's own enum-colocation
     precedent).
   - `provider.portfolios` — exactly per spec (`provider_id`, `media_url`, `caption`, `sort_order`), plus
     `idx_portfolios_provider_id`.
   - `provider.service_areas` — exactly per spec (`provider_id`, `center_latitude`, `center_longitude`,
     `radius_meters`), plus `idx_service_areas_provider_id`. **Deliberately does not** add the `cube`/
     `earthdistance` GiST index from `04_DATABASE.md` Section 13 — no AC in this story performs a geospatial
     query against this table (that begins with the future Search & Matching story); adding an unused index now
     would be premature. `service_areas` rows are populated/kept in sync automatically by `ProviderService`
     whenever `business_profiles`/`freelancer_profiles` location or radius fields are created or edited (derived
     data, not independently provider-editable — matches `03_DOMAIN_MODEL.md`'s "Service Area is derived from...
     location" framing) — no direct API exposes `service_areas` fields for editing in this story.
   - `provider.provider_category_labels` — new table (Decision 1): `provider_id` FK, `label VARCHAR(100) NOT
     NULL`, `is_primary BOOLEAN NOT NULL DEFAULT false`, full `CommonColumnsMixin`. Partial unique index
     `uq_provider_category_labels_primary (provider_id) WHERE is_primary = true`. Data migration step: backfill
     one row per existing `providers.category_label` value (`is_primary = true`), then `DROP COLUMN
     category_label` from `providers`.
2. Verify upgrade and downgrade both work cleanly against a disposable scratch database (ADR-013).

### Models (`backend/app/modules/provider/models.py`)
3. `Weekday(StrEnum)` + `_pg_enum` helper (mirrors the existing `ProviderType`/`ListingSource`/
   `VerificationStatus` pattern). `ProviderAvailability`, `Portfolio`, `ServiceArea`,
   `ProviderCategoryLabel` (all `CommonColumnsMixin`, schema `"provider"`). Remove `Provider.category_label`.

### Repositories (`backend/app/modules/provider/repositories/`)
4. `portfolio_repository.py`: `PortfolioRepository(BaseRepository[Portfolio])` — `list_active_for_provider`,
   `get_active_by_id`, `soft_delete` (mirrors `SavedAddressRepository` exactly), `bulk_set_sort_order(ordered:
   list[tuple[uuid.UUID, int]])` (Decision 4, one flush).
5. `provider_availability_repository.py`: `ProviderAvailabilityRepository(BaseRepository[ProviderAvailability])`
   — `list_for_provider`, `upsert_many(provider_id, entries)` (Decision 3, one flush per call covering up to
   seven rows).
6. `provider_category_label_repository.py`: `ProviderCategoryLabelRepository(BaseRepository[ProviderCategoryLabel])`
   — `list_for_provider`, `replace_all(provider_id, labels)` (delete-existing-then-insert-new, one flush).
7. `service_area_repository.py`: `ServiceAreaRepository(BaseRepository[ServiceArea])` — `get_for_provider`,
   `upsert_for_provider` (called internally by `ProviderService`, never exposed via API).

### Services (`backend/app/modules/provider/services/`)
8. `provider_service.py` gains: `update_basic_info(user_id, *, fields)` — `PATCH /providers/me`'s handler;
   applies `display_name`/`phone_*`/`whatsapp_number`/`description` (only fields present, `exclude_unset`),
   replaces `category_labels` via `ProviderCategoryLabelRepository.replace_all` if present (validating exactly
   one `is_primary=true` and a max of 5 labels), and applies `business_details`/`freelancer_details` partial
   updates onto the correct existing subtype profile (rejecting, 400, if the payload's details object doesn't
   match the provider's actual `provider_type` — a service-layer check, since the schema itself can't know the
   existing type). Also updates `service_areas` (Decision, item 1 above) whenever a location/radius field
   changes, in the same flush.
9. `services/portfolio_service.py` (new): `list_my_portfolio(user_id)`, `add_photo(user_id, *, upload: UploadFile,
   caption)` — validates via `image_validation.py` (Decision 2), enforces the 20-photo cap, calls `FileStorage.save`,
   creates the `portfolios` row; `delete_photo(user_id, portfolio_id)` — `ensure_owner_or_not_found`, soft-delete
   (Decision 5); `reorder(user_id, ordered_ids)` — validates the id-set match, bulk-sets `sort_order` (Decision 4).
10. `services/availability_service.py` (new): `get_my_availability(user_id)` — returns all 7 synthesized entries;
    `update_my_availability(user_id, entries)` — upserts (Decision 3).

### Storage (`backend/app/shared/storage/`, new)
11. `interfaces.py` — `FileStorage` protocol. `local_file_storage.py` — `LocalFileStorage` (Decision 2).
    `image_validation.py` — `validate_image_upload(upload_file) -> tuple[bytes, str]` (returns validated content
    + safe extension).

### Config (`backend/app/core/config.py`)
12. New settings: `UPLOAD_DIR: str = "uploads"`, `MAX_PORTFOLIO_PHOTO_SIZE_BYTES: int = 5_242_880`,
    `MAX_PORTFOLIO_PHOTOS_PER_PROVIDER: int = 20`. `.gitignore`: add the upload directory.

### App wiring
13. `backend/app/main.py`: mount `StaticFiles(directory=settings.UPLOAD_DIR)` at `/media`.
14. `backend/tests/conftest.py`: no new import needed beyond the existing `app.modules.provider.models` (already
    imported by PRO-001; new models live in the same module file).

### Schemas (`backend/app/modules/provider/schemas.py`)
15. `CategoryLabelInput { label: str (max 100), is_primary: bool }` / `CategoryLabelResponse` (same shape).
    `UpdateBusinessDetailsRequest`/`UpdateFreelancerDetailsRequest` — same fields as their `Create*` counterparts,
    all optional. `UpdateProviderRequest { display_name?, phone_country_code?, phone_number?, whatsapp_number?,
    description?, category_labels?: list[CategoryLabelInput], business_details?: UpdateBusinessDetailsRequest,
    freelancer_details?: UpdateFreelancerDetailsRequest }`. `ProviderResponse.category_label: str` →
    `category_labels: list[CategoryLabelResponse]` (breaking change to this pre-launch response shape, see
    Verified Current State). `PortfolioPhotoResponse { id, media_url, caption, sort_order }`. `ReorderPortfolioRequest
    { ordered_ids: list[uuid.UUID] }`. `WeekdayAvailabilityInput`/`WeekdayAvailabilityResponse { weekday,
    is_open, open_time?, close_time?, is_emergency_available }`. `UpdateAvailabilityRequest { entries:
    list[WeekdayAvailabilityInput] }`.

### Exceptions
16. `InvalidPortfolioUploadError` (422), `PortfolioPhotoNotFoundError` (404, ownership-collapsing per ADR-015),
    `PortfolioLimitExceededError` (409), `InvalidCategoryLabelsError` (422 — wrong count of primaries or too many
    labels), `SubtypeDetailsMismatchError` (400 — editing the wrong subtype's details object).

### API (`backend/app/modules/provider/api.py`)
17. `PATCH /providers/me`. `GET`/`POST /providers/me/portfolio`, `DELETE /providers/me/portfolio/{portfolio_id}`,
    `PUT /providers/me/portfolio/order`. `GET`/`PUT /providers/me/availability`. All bare-authenticated (Decision
    7).

### Dependencies (`backend/app/modules/provider/dependencies.py`)
18. `get_portfolio_repository`, `get_provider_availability_repository`, `get_provider_category_label_repository`,
    `get_service_area_repository`, `get_file_storage` (returns `LocalFileStorage`, reading `UPLOAD_DIR` from
    settings), `get_portfolio_service`, `get_availability_service`.

### Tests
19. `backend/tests/modules/provider/test_portfolio_service.py`: upload validation (correct MIME/extension/size
    rejects wrong type, oversized file, extension/content mismatch — AC2); generated filename never equals the
    original client-supplied filename; 20-photo cap enforced; **reorder persists correctly** — create 3 photos,
    reorder, re-fetch, assert exact order (AC8); reorder rejects a mismatched id set; soft-delete excludes a
    photo from subsequent list calls but leaves the file on disk; **ownership** — a second provider cannot delete
    the first provider's photo (404, not 200) (AC7/AC8).
20. `backend/tests/modules/provider/test_availability_service.py`: `PUT` creates all 7 rows on first call;
    a second `PUT` with different values updates (not duplicates) the same rows; `GET` before any `PUT` returns 7
    synthesized "closed" entries; is_open=true requires both times, is_open=false requires neither (AC3); a
    second provider's availability is never returned/affected by the first provider's calls (AC7/AC8 — this
    endpoint has no `{id}` at all, so this test proves ownership is structural, not merely untested).
21. `backend/tests/modules/provider/test_provider_service_update.py`: `PATCH /providers/me` updates only
    fields present in the payload (partial update, AC5); `category_labels` replace enforces exactly one primary
    and the 5-label cap (AC4); editing `business_details` on a Freelancer provider (or vice versa) is rejected
    (Decision 8's mismatch check); `provider_type` is never accepted by the schema at all (still immutable);
    editing basic info/hours/portfolio never touches `verification_status`/`is_discoverable` (AC6).
22. `backend/tests/modules/provider/test_provider_endpoints.py` (extends the existing file): full HTTP-level
    round trip for `PATCH /providers/me`, the four portfolio endpoints (including a real small in-memory
    multipart upload), and the two availability endpoints; unauthenticated → 401 on every new route.
23. `backend/tests/shared/storage/test_image_validation.py`: valid JPEG/PNG/WEBP bytes pass; a text file
    renamed to `.jpg` is rejected (magic-byte mismatch); an oversized payload is rejected; a disallowed extension
    (`.svg`, `.exe`) is rejected regardless of content.

---

## Mobile — Proposed Changes

### Shared (`mobile/lib/shared/widgets/`)
24. Factor `business_details_screen.dart`'s private `_OperatingHoursRow`/weekday-list logic out into a new
    shared `weekly_hours_editor.dart` (Verified Current State) — reused by both the (untouched) onboarding
    screen and the new Storefront availability section, avoiding a second copy of the same UI
    (`08_CODING_STANDARDS.md`). Extended with the per-weekday emergency-availability toggle this story adds.

### Feature: Provider (`mobile/lib/features/provider/`)
25. `domain/models/provider.dart`: `Provider.categoryLabel` (`String`) → `categoryLabels`
    (`List<CategoryLabel>`, mirroring the backend's breaking response-shape change).
26. `domain/models/portfolio_photo.dart`, `domain/models/weekday_availability.dart`,
    `domain/models/update_provider_request.dart` (new) — mirror the backend's new request/response shapes.
27. `data/provider_repository.dart` gains: `updateProvider(UpdateProviderRequest)`, `listPortfolio()`,
    `uploadPortfolioPhoto(File imageFile, {String? caption})` (multipart), `deletePortfolioPhoto(id)`,
    `reorderPortfolio(List<String> orderedIds)`, `getAvailability()`, `updateAvailability(List<WeekdayAvailability>)`.
28. `presentation/screens/storefront_screen.dart` (new, S-25) — the ongoing Storefront/Edit Profile screen: four
    independently-saveable sections (basic info incl. category labels, subtype-specific details, portfolio
    manager, availability editor via the new shared `WeeklyHoursEditor`), each with its own Save action calling
    only the relevant repository method, per-section loading/success/error feedback
    (`16_UX_GUIDELINES.md`'s "every user-initiated action gets acknowledgment" rule).
29. `presentation/widgets/portfolio_manager.dart` (new) — grid/list of existing photos with a remove action per
    photo and drag-to-reorder (or up/down buttons, whichever proves simpler to make accessible per
    `07_UI_GUIDELINES.md`'s touch-target rule), an "Add Photo" action (image picker → upload), empty-state copy
    per `16_UX_GUIDELINES.md`'s empty-state formula.
30. Route/entry point: the existing Profile & Settings "List Your Business" tile's "you already have a listing"
    branch (PRO-001) now navigates to the new `storefront` route instead of only showing a snackbar.

### Tests
31. `mobile/test/features/provider/storefront_screen_test.dart`, `portfolio_manager_test.dart`,
    `weekly_hours_editor_test.dart` (new shared-widget test) — each section saves independently; reorder produces
    the expected repository call with the new order; add/remove photo updates the visible list; a second
    account's provider data is never fetched/displayed (mirrors the backend ownership guarantee at the UI level).
32. `mobile/test/features/provider/fakes/fake_provider_repository.dart` (existing, from PRO-001) extended with
    the new methods.

---

## Explicitly Out of Scope (do not implement in this story)

- Visibility analytics (LEAD-002/S-26) and Leads (LEAD-001/S-24) — not touched by this story at all.
- The real Category taxonomy domain (`category.categories`, `category_question_templates`, the real
  `provider_categories` join table referencing it) — `provider_category_labels` (Decision 1) is a deliberate,
  flagged, temporary structural stand-in, not a preview of the real feature.
- Any code implementing the Decision 6 placeholder rule (flipping `verification_status`/`is_discoverable` on a
  `trade_license_number` edit) — documented as a future VER-001 concern only, not built here.
- Real cloud (S3) file storage — `LocalFileStorage` (Decision 2) is explicitly interim; the `FileStorage`
  protocol exists specifically so a future story can add `S3FileStorage` without touching `PortfolioService`.
- Virus/malware scanning of uploaded photos (`06_SECURITY.md` already calls this out as a future enhancement).
- Image thumbnailing/re-encoding/EXIF stripping — not requested by any AC; a candidate future enhancement once
  an imaging dependency is justified by a real requirement.
- The `cube`/`earthdistance` geospatial index over `service_areas` (`04_DATABASE.md` Section 13) — deferred to
  the future Search & Matching story that actually queries it.
- Orphaned on-disk file cleanup for soft-deleted portfolio photos — a future administrative/retention job.
- The Provider Dashboard (S-23) and any role-gating changes to existing PRO-001 endpoints.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (PRO-001's Checkpoint was deleted at that story's close per the
Continuity & Checkpointing process); this is a fresh start.

1. **backend** — Migration, models, repositories, `PortfolioService`/`AvailabilityService`/`ProviderService`
   extensions, the new `app/shared/storage/` module, config, exceptions, schemas, API routes, dependencies,
   `main.py` static mount, tests (items 1–23 above). ACs to satisfy: 1, 2 (backend half), 3, 4, 6, 7 (backend
   half), 8 (backend half).
2. **frontend** — Shared weekly-hours-editor extraction, Provider feature model/repository updates, the new
   Storefront screen and portfolio manager widget, tests (items 24–32 above), once backend endpoints exist (or
   in parallel against a fake repository). ACs to satisfy: 2 (mobile half — picker + upload UI), 5, 7 (mobile
   half — never fetches/displays another account's data).
3. **tester** — Verify all 8 ACs individually. Particular attention to: AC2 (upload a deliberately mismatched
   file — correct extension, wrong magic bytes — and confirm rejection, not just a happy-path upload test); AC4
   (exactly-one-primary enforced on both the initial set and a subsequent replace); AC7/AC8's ownership boundary
   (read the actual service code for `delete_photo`/`reorder` to confirm `ensure_owner_or_not_found` is genuinely
   exercised, not merely trusted via the DB, mirroring the CUS-002/PRO-001 precedent); AC8's reorder-persistence
   test (re-fetch after reorder, don't just assert the write call succeeded).
4. **architect** — Review Decision 1 (`provider_category_labels` naming/shape vs. the reserved
   `provider_categories` name in `04_DATABASE.md`) for genuine non-conflation with the future real table; Decision
   2 (the new `FileStorage` abstraction and `LocalFileStorage` as an explicitly interim choice) against
   `06_SECURITY.md`'s File Upload Security section and `02_ARCHITECTURE.md`'s "Infrastructure depends on Domain"
   dependency rule; Decision 3/4 (endpoint shapes, reorder mechanism) against ADR-015; Decision 7 (bare-auth
   gating) against ADR-016's documented token-refresh-lag consequence.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 2 as
   **ADR-017** in `09_DECISIONS.md`; update `04_DATABASE.md` (new tables, the `provider_category_labels`
   deviation from the documented `provider_categories` spec, dropped `category_label` column); update
   `12_TECH_STACK.md` if any new setting/dependency was actually introduced; flag the missing
   `13_OPEN_DECISIONS.md` file to the user for a separate follow-up (outside this story's/this Plan's ownership).

---

## Verification Plan (mapped to the 8 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade; `\d provider.portfolios` / `\d provider.provider_availability` / `\d provider.service_areas` / `\d provider.provider_category_labels` match their specs (the last one flagged as a deliberate, documented deviation from `04_DATABASE.md`'s literal `provider_categories` name/shape, per Decision 1). |
| 2 | Service/integration tests: correct-type upload succeeds and is retrievable via the returned `/media/...` URL; wrong extension, wrong MIME, oversized, and magic-byte-mismatched uploads are all rejected (422); the stored filename never equals or contains the original client-supplied filename; remove and reorder both work end-to-end. |
| 3 | Service/integration test: `PUT /providers/me/availability` persists open/closed status, hours, and the emergency flag per weekday; `GET` reflects it; a day set to `closed` has null hours. |
| 4 | Service test: a `category_labels` payload with exactly one `is_primary: true` succeeds; zero or more-than-one primary is rejected (422); replacing the set correctly leaves exactly one primary afterward. |
| 5 | Widget/integration test: each of the four Storefront sections (basic info, subtype details, portfolio, availability) saves independently — changing and saving one section does not require or resubmit the others' fields. |
| 6 | Code-level check + test: no code path in this story's new endpoints reads or writes `verification_status`/`is_discoverable`; documented placeholder rule (Decision 6) reviewed by `architect` for completeness, not enforced in code. |
| 7 | Integration test: a second authenticated provider account cannot fetch, edit, delete-a-photo-from, or reorder-the-photos-of the first provider's storefront — every attempt either 404s (photo id case) or structurally cannot address the other account's data (`/me`-anchored routes). |
| 8 | Three distinct, independently-runnable test cases confirmed: portfolio reorder persistence (re-fetch after reorder), availability CRUD (`GET`/`PUT` round trip, including the closed-day null-hours rule), and the ownership-boundary test named under AC7. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md`
- `docs/AI/03_DOMAIN_MODEL.md`
- `docs/AI/04_DATABASE.md`
- `docs/AI/05_API_GUIDELINES.md`
- `docs/AI/06_SECURITY.md`
- `docs/AI/07_UI_GUIDELINES.md`
- `docs/AI/08_CODING_STANDARDS.md`
- `docs/AI/09_DECISIONS.md` (ADR-015, ADR-016 — both directly extended by this story)
- `docs/AI/12_TECH_STACK.md`
- `docs/AI/14_USER_FLOWS.md`
- `docs/AI/15_SCREEN_INVENTORY.md` (S-25)
- `docs/AI/16_UX_GUIDELINES.md`
- `docs/implementation/plans/Plan_S04_PRO-001.md` (Decision 4 — the `category_label` precedent this story
  extends; ADR-016 origin)
- `docs/implementation/plans/Plan_S03_CUS-002.md` (soft-delete and default-uniqueness precedents this story
  reuses for portfolio deletion and category-label primary enforcement)
- `docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md`
