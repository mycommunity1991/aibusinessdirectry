# Walkthrough S03 CUS-001

## Story: Set Up My Customer Profile and Preferences

**Sprint:** 03 | **Story ID:** CUS-001 | **Priority:** High | **Status:** Done

As a newly registered user, I want a customer profile created automatically with sensible defaults, and the
ability to update my display name, avatar, language, and notification channel, so that the app is personalized
to me without extra signup steps.

This is the first story of Sprint 3 ("Customer Profile & Locations") and the first story of a genuinely new
domain (`customer`) — no `backend/app/modules/customer/` or mobile `features/customer/` code existed before
this story. Full context, architecture decisions, and file-by-file scope:
`docs/implementation/plans/Plan_S03_CUS-001.md`.

---

## What was implemented

### Backend (`backend/app/modules/customer/`, `backend/app/modules/identity/`)

- **New `customer` domain module**, mirroring the established per-domain layout (`models.py` →
  `repositories/` → `services/` → `schemas.py` → `api.py` → `dependencies.py`): `CustomerProfile` and
  `CustomerPreferences` (both `CommonColumnsMixin`, schema `"customer"`), a one-to-one pair keyed off
  `identity.users.id`, created via a reversible Alembic migration
  (`backend/alembic/versions/2026_09_06_1400-35cd57521089_customer_domain.py`). `customer_preferences.language`
  reuses the existing `identity.language_code` Postgres enum directly (`create_type=False`) rather than
  duplicating it; `notification_channel` (`whatsapp`/`sms`/`email`) is a new enum, scoped to the `customer`
  schema as its first consumer.
- **Atomic same-transaction provisioning (the core architectural piece)**: `identity → customer` is now a
  second cross-module service dependency in this codebase, deliberately mirroring the already-shipped
  `identity → audit` pattern from AUTH-004 rather than inventing a new mechanism. `AuthService` now takes a
  `CustomerService` constructor dependency and calls `provision_default_profile(user_id, accept_language_header)`
  inline inside the existing `if is_new_user:` branch of both `verify_otp_and_authenticate` (mobile OTP,
  AUTH-001) and `authenticate_with_oauth` (Google/Apple, AUTH-002) — flush only, on the same request-scoped
  `AsyncSession`, never a separate commit. The endpoint's single, pre-existing `await db.commit()` remains the
  only transaction boundary, so the `User` row and the new `customer_profiles`/`customer_preferences` rows
  either all land together or none do. `customer`'s own code has zero imports from `identity`'s services or
  repositories (only a plain FK-by-string and a reuse of `identity.models.LanguageCode`, a plain enum) — a
  one-directional edge, no cycle.
- **Sensible defaults**: notification channel always defaults to WhatsApp. Default language is derived from
  the standard `Accept-Language` HTTP header (q-value aware — parses `"ar-AE,ar;q=0.9,en;q=0.8"` correctly by
  weight, not just first-listed), falling back to English on a missing, empty, or malformed header. `identity`
  stays a pure pass-through of the raw header string; all parsing/fallback logic lives inside `CustomerService`
  since interpreting it as a customer-preference default is a Customer-domain business rule.
- **`GET`/`PATCH /api/v1/customers/me`** — both gated by `require_role(ROLE_CUSTOMER)`, resolve the target
  exclusively from the authenticated caller's JWT `sub`, and take no `{id}` path parameter and no client-supplied
  identifier field anywhere in the request contract. Ownership is therefore structurally guaranteed, not just
  defensively checked — there is no route shape through which a caller could even attempt to address another
  user's profile. `PATCH` is a partial update (`exclude_unset=True`); only fields present in the payload change.
- **Lazy get-or-create backfill for Sprint-2 users**: real `identity.users` rows already existed in `main`
  before this story shipped, with no `customer_profiles` row (the atomic-creation path only covers
  registrations from this point forward). Rather than a one-off DML backfill migration, `get_my_profile`/
  `update_my_profile` are both get-or-create: a legacy caller's first `GET`/`PATCH /customers/me` call
  transparently provisions the row with the same defaults `provision_default_profile` would have used (no
  `Accept-Language` signal available at this point, so it falls back straight to English) — the endpoint never
  404s for an authenticated, `customer`-role caller.
- **Tests**: `backend/tests/modules/customer/test_customer_service.py` (14 tests) and
  `test_customer_endpoints.py` (9 tests, including a direct two-different-tokens-get-two-different-results
  ownership test), plus extensions to `test_auth_service.py`/`test_auth_endpoints.py` proving atomicity by
  querying `customer.customer_profiles`/`customer.customer_preferences` directly in the same test as the `User`
  row check, for both the mobile-OTP and OAuth paths, and confirming no duplicate row is created on a second
  login. **237 backend tests passing** (up from 211 at the end of AUTH-004), `ruff check`/`ruff format --check`
  both clean.

### Mobile (`mobile/lib/features/customer/`, `mobile/lib/core/network/`)

- **New Customer feature module**, following the exact Feature-First layer split already established by
  `features/auth/` (`domain/models`, `data`, `state`, `presentation/screens`, `presentation/utils`):
  `CustomerRepository` (`GET`/`PATCH /customers/me`, never leaks a raw Dio error/status code to the UI —
  maps everything to `CustomerProfileException`), `CustomerProfileController` (`StateNotifier`, loads on
  construction, exposes per-field update methods).
- **Profile & Settings screen** (S-14, scoped to this story only): editable display name, editable avatar URL
  (a plain string field, not a photo-picker/upload flow — file upload is a distinct, out-of-scope feature),
  a language toggle (`SegmentedButton`, EN/AR), and a notification-channel picker (three `RadioListTile`s
  under a `RadioGroup` ancestor — chosen over a second horizontal `SegmentedButton` to avoid a `RenderFlex`
  overflow risk with the longer Arabic labels at narrow widths). Reachable via a temporary `AppBar` icon button
  on the existing Home placeholder screen — deliberately not wired into a bottom-navigation shell, since no
  real Home/Activity screens exist yet to make a shared shell meaningful (that's for whichever future story
  delivers a real Home screen).
- **Live language switching (AC6)**: `CustomerProfileController.updateLanguage(Locale)` calls the `PATCH`
  endpoint **and** the existing `LanguageController` (already built in AUTH-related mobile work, watched
  directly by `MaterialApp.router`'s `locale:`) in the same call, so the server-side preference and the
  immediate in-app effect (no restart) can never land only partially.
- **Along-the-way fix**: the mobile `ApiClient` was not sending an `Accept-Language` header on any outgoing
  request — a genuine, pre-existing gap, not something introduced by this story. A new
  `AcceptLanguageInterceptor` now sets it on every request from `languageControllerProvider`'s current value,
  sending no header at all until the user has made an explicit language choice (preserving device-default
  semantics, matching the backend's own English fallback for "no signal").
- **First RTL automated test in this codebase (AC9)**: `test_helpers.dart`'s `pumpApp`/`pumpScreen` gained an
  optional, backward-compatible `Locale? locale` parameter. The Profile & Settings test suite includes a case
  pumping `Locale('ar')` and asserting `Directionality.of(context) == TextDirection.rtl` plus no
  layout-overflow exception — establishing the reusable pattern for every future story's RTL acceptance
  criterion.
- **Tests**: `mobile/test/features/customer/profile_settings_screen_test.dart` (9 tests) — rendering, editing/
  saving each field, avatar-clearing, the language-toggle test asserting both the repository call and the
  provider's locale change in the same test (no widget-tree rebuild), the notification-channel picker, and the
  RTL case. **40 mobile tests passing** (31 pre-existing AUTH-001–004 + 9 new), `flutter analyze` clean, `dart
  format --output=none --set-exit-if-changed` clean.

---

## Acceptance Criteria — Verification

All 9 acceptance criteria (from `Plan_S03_CUS-001.md`, sourced from the Tracker) were independently verified
by the `tester` agent — full suites re-run from a clean shell, migration reversibility re-derived against a
disposable scratch database (not the shared test DB), atomicity claims confirmed by reading actual test bodies
and the real `AuthService`/`CustomerService` code (not trusted from either engineering report), and the
`Accept-Language` q-value parsing traced by hand against specific header strings. All 9 passed.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `customer_profiles`/`customer_preferences` tables exist via migration, 1:1 with `users` | Pass |
| 2 | Registration (AUTH-001 or AUTH-002) creates both rows in the same DB transaction as the `User` row | Pass |
| 3 | Default notification channel WhatsApp; default language from device locale (`Accept-Language`), English fallback | Pass |
| 4 | `GET`/`PATCH /customers/me` read/update display name, avatar, language, notification channel, partial update | Pass |
| 5 | Profile & Settings screen displays/edits these fields, visible language toggle | Pass |
| 6 | Changing language updates `customer_preferences.language` and takes effect immediately, no restart | Pass |
| 7 | A user cannot read or update another user's customer profile (ownership enforced) | Pass |
| 8 | Automated tests confirm profile auto-creation is atomic with registration | Pass |
| 9 | RTL layout verified for the Profile & Settings screen in Arabic | Pass |

---

## Architect Review — Findings and Resolution

The `architect` agent returned **STORY COMPLETE** — no must-fix items, no architectural-boundary violation, no
scope creep into CUS-002/PRO-001/002/Notification-domain territory. Full findings in the (now-deleted)
`Checkpoint_S03_CUS-001.md`; summary of the review:

1. **`identity → customer` cross-module call (Decision 1, the core architectural question)** — confirmed
   correct on all three sub-points: it genuinely mirrors the `identity → audit` precedent (same constructor-
   injection shape, same `Depends(get_customer_service)` wiring pattern), the same-transaction/flush-only
   claim holds up on direct code read (`BaseRepository.create()` never commits; `AuthService` calls the new
   service inline on the same session; the endpoint's single `db.commit()` is unchanged), and the dependency
   direction is one-directional with zero cycle risk (`customer` imports only a plain enum from `identity`,
   never a service or repository). This is a genuine repeat of an already-shipped pattern, not new precedent —
   recorded as **ADR-014**.
2. **Enum reuse migration (Decision 2)** — confirmed correct: the migration's `create_type=False` on the
   reused `identity.language_code` enum was verified directly in the migration file and independently
   confirmed via a `pg_type`/`pg_namespace` query against a scratch database; `downgrade()` correctly does not
   drop the shared type.
3. **Lazy get-or-create backfill (Decision 4)** — confirmed architecturally sound as the primary design choice
   (avoids mixing schema DDL with a data migration, avoids a table-lock risk against a shared table, is
   trivially testable). One nice-to-have flagged — see Follow-up Notes below.
4. **`/customers/me` ownership design vs. AUTH-004's `ensure_owner_or_not_found` (AC7)** — confirmed the two
   are not competing solutions to the same problem: `ensure_owner_or_not_found` exists for client-addressable-
   by-id resources (e.g. `DELETE /auth/sessions/{session_id}`); CUS-001's `/me`-only endpoint shape has nothing
   for a caller to address except their own row, so a runtime ownership check would be comparing an id that
   doesn't exist in the route against itself. Both are legitimate; this story picked the correct one for its
   shape.
5. **Standard mobile review** — confirmed clean: Feature-First layer split matches `features/auth/` exactly,
   `CustomerRepository` never leaks a raw Dio error to the UI, no hardcoded strings/colors, no new package
   additions needing a `12_TECH_STACK.md` cross-check.
6. **Scope boundary check** — confirmed clean via direct grep: no `saved_addresses`, no
   `notification_preferences`/per-category toggles, no bottom-nav-shell code anywhere in the diff.

### Standard review confirmed clean

Module boundaries/Clean Architecture (no cross-module repository access, business logic stays in services),
database (models match `04_DATABASE.md` column-for-column, enum reuse verified), no hardcoded secrets/colors/
strings, no unapproved dependency additions.

---

## Follow-up Notes (non-blocking, tracked for future work)

1. **`AcceptLanguageInterceptor` has no dedicated test.** Its wiring into `apiClientProvider` and its logic
   (reads `languageControllerProvider`'s current value, sets the header only when non-null) were confirmed
   correct by direct code inspection, but no test in `mobile/test/` exercises it directly (e.g. a
   `Dio`+mock-transport test asserting the header is present/absent depending on the provider's value). This
   is consistent with, not a new regression from, the codebase's existing accepted gap — `AuthInterceptor`
   (AUTH-003, already shipped and signed off) has never had a dedicated interceptor-level test either. Worth
   closing opportunistically for both interceptors in a future story, not treated as a blocker here.
2. **Latent `IntegrityError` race on concurrent first-access to `get_my_profile`.** Two genuinely concurrent
   first `GET`/`PATCH /customers/me` calls from the same never-before-provisioned account could both observe
   "no profile row exists," both attempt to create one, and the loser would hit the `uq_customer_profiles_user_id`
   unique-constraint violation as an unhandled `IntegrityError` — a transient 500 rather than a graceful
   fallback to the row the winner just created. This does not risk duplicate/corrupt data (the DB constraint is
   the actual backstop) and is not a new problem this story introduces — `AuthService`'s own user
   get-or-create from AUTH-001 has the identical shape and the identical latent race, already accepted as a
   pre-existing gap in that story's own walkthrough. Small follow-up: catch `IntegrityError`, re-fetch, return
   the winner's row.
3. **`mypy` still not installed.** Configured in `pyproject.toml`'s `[tool.mypy]` but not present in
   `[dependency-groups].dev` and not runnable (`uv run mypy app` fails to spawn). Pre-existing gap, carried
   forward from AUTH-003/AUTH-004's walkthroughs, still not fixed.

---

## Testing Performed

- `cd backend && uv run pytest -v` — **237/237 passing**, 0 regressions on AUTH-001 through AUTH-004 (re-run
  independently by `backend`, `tester`, both from clean shells, both consistent). `tests/modules/customer/` =
  23 passed.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic downgrade base && uv run alembic upgrade head`
  — verified independently by both `backend` (against the shared `ai_marketplace_test` DB, reset afterward) and
  `tester` (against a dedicated, disposable scratch DB, dropped afterward). Reversible, columns/constraints/
  enum reuse confirmed via `psql \d`/`pg_type` queries to exactly match `04_DATABASE.md`.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- `cd mobile && flutter test` — **40/40 passing** (31 pre-existing AUTH-001–004 + 9 new Customer).
- `cd mobile && flutter analyze` — no issues found.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean.
- Diff review: `test_auth_service.py`/`test_auth_endpoints.py`/`conftest.py` confirmed additive-only (one
  test removal, `test_no_customer_profile_row_is_created`, was a legitimate, necessary removal — that
  assertion became structurally false the moment this story's migration ran, replaced by a strictly stronger
  atomicity test).
- `tester` agent: all 9 ACs independently verified with direct evidence — see table above.
- `architect` agent: STORY COMPLETE — see findings above.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_06_1400-35cd57521089_customer_domain.py` (new)
- `backend/alembic/env.py`
- `backend/app/modules/customer/{models.py,schemas.py,api.py,dependencies.py}` (new)
- `backend/app/modules/customer/repositories/{customer_profile_repository.py,customer_preferences_repository.py}` (new)
- `backend/app/modules/customer/services/customer_service.py` (new)
- `backend/app/api/v1/api.py` — registers the `customer` router
- `backend/app/modules/identity/services/auth_service.py` — injected `CustomerService`; passes
  `accept_language_header` through both registration paths
- `backend/app/modules/identity/api.py` — reads and forwards the `Accept-Language` header
- `backend/app/modules/identity/dependencies.py` — wired `CustomerService` into `get_auth_service()`
- `backend/tests/modules/customer/{test_customer_service.py,test_customer_endpoints.py}` (new)
- `backend/tests/modules/identity/{test_auth_service.py,test_auth_endpoints.py}`
- `backend/tests/conftest.py` — `customer` schema creation/drop, table truncation

### Mobile
- `mobile/lib/features/customer/domain/models/{customer_profile.dart,customer_profile_exception.dart}` (new)
- `mobile/lib/features/customer/data/customer_repository.dart` (new)
- `mobile/lib/features/customer/state/customer_profile_controller.dart` (new)
- `mobile/lib/features/customer/presentation/screens/profile_settings_screen.dart` (new)
- `mobile/lib/features/customer/presentation/utils/customer_error_copy.dart` (new)
- `mobile/lib/core/network/accept_language_interceptor.dart` (new)
- `mobile/lib/core/network/api_client.dart` — registers the new interceptor
- `mobile/lib/core/routing/{app_routes.dart,app_router.dart}` — `AppRoutes.profileSettings`
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` — temporary entry point
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}`
- `mobile/test/features/auth/test_helpers.dart` — optional `Locale? locale` param
- `mobile/test/features/home/home_placeholder_screen_test.dart`
- `mobile/test/features/customer/fakes/fake_customer_repository.dart` (new)
- `mobile/test/features/customer/profile_settings_screen_test.dart` (new)

---

## Follow-up Notes for Sprint Planning

- Sprint 3 (Customer Profile & Locations) is **underway** — 1 of 2 stories done: CUS-001. CUS-002 ("Manage my
  service locations"), which depends on CUS-001, is now unblocked and ready for planning.
- The three non-blocking follow-up items above (`AcceptLanguageInterceptor` test gap, the
  `get_my_profile` `IntegrityError` race, `mypy` not installed) are recorded here for future pickup; none block
  this story's closure.
