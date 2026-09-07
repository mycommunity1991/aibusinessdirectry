# Walkthrough S03 CUS-002

## Story: Manage My Service Locations

**Sprint:** 03 | **Story ID:** CUS-002 | **Priority:** High | **Status:** Done

As a customer, I want to save, edit, and remove addresses, and optionally add one during onboarding, so that I
don't have to re-enter my location every time I search for a service.

This is the second and final story of Sprint 3 ("Customer Profile & Locations"). **Sprint 3 is now fully
complete** (CUS-001 + CUS-002). Full context, architecture decisions, and file-by-file scope:
`docs/implementation/plans/Plan_S03_CUS-002.md`.

---

## What was implemented

### Backend (`backend/app/modules/customer/`)

- **New `customer.saved_addresses` table** via a reversible Alembic migration
  (`backend/alembic/versions/2026_09_06_1500-9f47869ca8bb_saved_addresses.py`): `customer_id` FK →
  `customer_profiles.id`, `label`, `address_line`, `city`, `region`, `country_code` (ISO 3166-1 alpha-2, plain
  validated text — no full country picker, deliberately kept country-agnostic), `latitude`/`longitude`, and an
  `is_default` flag, plus `idx_saved_addresses_customer_id` and a new partial unique index,
  `uq_saved_addresses_customer_default`.
- **Default-address uniqueness (AC2): transactional service-layer unset-then-set, plus a partial unique index
  as defense-in-depth.** Both `create_address` and `update_address` unset every other active address's
  `is_default` for that customer *before* writing the new default, on the same request-scoped session — so the
  partial unique index (`customer_id` WHERE `is_default = true AND is_active = true`) never actually has to
  reject a legitimate write; it exists purely as a backstop against a future bug, not as the mechanism doing
  the real work. Confirmed genuine (not a same-request illusion) by both `tester` and `architect` reading real
  post-write `SELECT` queries directly.
- **This codebase's first genuine soft-delete pattern.** Every prior "delete" in the codebase (`BaseRepository.delete()`)
  is a hard delete; `04_DATABASE.md`'s Soft Delete section requires deletion to be reversible/administrative
  only. `SavedAddressRepository.soft_delete()` sets `deleted_at`/`is_active` and flushes — never
  `session.delete()`. Every read path (`list_for_customer`, `get_active_by_id`) filters `is_active`, so a
  soft-deleted row is indistinguishable from nonexistent to every subsequent verb, closed with two dedicated
  boundary tests added during the review cycle (see Bugs Found During Review below). On delete, the backend
  never auto-promotes another address to default — that decision belongs to the customer, driven by the
  mobile UX (AC7).
- **Endpoints — a client-`{id}`-addressable collection, not a `/me` singleton.** `GET`/`POST
  /customers/me/addresses`, `PATCH`/`DELETE /customers/me/addresses/{address_id}`, all behind
  `require_role(customer)`, unpaginated (per ADR-012's small/single-owner-scoped carve-out — same reasoning as
  `GET /auth/sessions`). Unlike CUS-001's `/me` singleton (no `{id}` exists to defend, so nothing to check),
  `saved_addresses` is a genuine 1:N collection the client addresses by id, so ownership is enforced
  defensively via AUTH-004's `ensure_owner_or_not_found` — a missing row and a row owned by someone else both
  collapse into the same non-revealing `SavedAddressNotFoundError` (404, never 403). This distinction between
  the two endpoint shapes is now recorded as **ADR-015** (see below) since it is a recurring decision every
  future collection-vs-singleton endpoint will need to make the same way.
- **Tests**: `test_saved_address_service.py` and `test_saved_address_endpoints.py` — default-uniqueness on
  both create-time and update-time paths (real-DB `SELECT` confirming exactly one `is_default = true` row),
  soft-delete excludes from list while the row survives, deleting the default leaves no auto-promoted
  replacement, cross-customer 404-not-403 on every verb, unauthenticated → 401, a legacy pre-CUS-001 account
  can still create its first address (get-or-create via `CustomerService`, reused rather than duplicated).
  **265 backend tests passing** (up from 263 at self-report, +2 from the soft-delete boundary follow-up — see
  below).

### Mobile (`mobile/lib/shared/widgets/location_picker/`, `mobile/lib/features/customer/`)

- **Three new, user-approved Flutter dependencies**: `google_maps_flutter`, `geolocator`, `geocoding` — no
  approved package existed for map rendering, device geolocation, or reverse geocoding before this story.
  Platform config (`AndroidManifest.xml` permissions + blank Maps API key placeholder, iOS
  `NSLocationWhenInUseUsageDescription` + blank `GMSServices.provideAPIKey`) mirrors AUTH-002's accepted gap:
  real API key/billing provisioning is an external prerequisite, deferred past this story's code-complete
  milestone; no automated test depends on it.
- **A shared, reusable `LocationPickerScreen`** (`mobile/lib/shared/widgets/location_picker/`) — zero
  Customer-domain coupling by design, built so the future Provider-domain location screens (S-18a/b, not this
  story) can reuse it without modification. Full-screen map with a fixed center pin, "Use current location,"
  "Confirm this location." The real `GoogleMap` widget is injected via a `mapViewBuilder` parameter (default:
  real map; test override: a plain placeholder) — the one deliberate seam needed to keep a platform-view
  widget testable, since `google_maps_flutter` cannot run inside `flutter_test`.
- **Registration-flow integration (AC4/AC5)**: `otp_entry_screen.dart`'s `_onVerify` and
  `phone_entry_screen.dart`'s `_handleOAuthResult` now route to a new, skippable `AddFirstAddressScreen`
  instead of straight to Home, inserted after `setSession` completes — so Skip can never block registration by
  construction, and the session is already fully live by the time the address screen renders. A temporary
  "Find a Service" stub button was added to the Home placeholder screen as the AC5 re-prompt trigger, since the
  real AI Conversation / Search Request screens (S-06/S-07) don't exist until Sprint 7/8 — explicitly commented
  as a stand-in whose only current job is enforcing the address-required gate; a future story replaces its
  target, not this gate.
- **Saved Addresses management screen** (S-12, reachable from Profile & Settings, the S-14 link slot CUS-001
  deferred): list with a "Default" badge, edit, and delete via an Undo snackbar (per `16_UX_GUIDELINES.md`'s
  own named reversible-action example). Deleting the default either shows a "choose a new default" bottom
  sheet (if others remain, including a valid "Not now") or an inline "No default address set" indicator (if
  the list is now empty) — never a forced choice.
- **Tests**: 23 new mobile tests (4 location picker, 9 address form, 8 saved addresses, 2 first-address-prompt
  end-to-end flow), plus updates to the existing OTP/OAuth sign-in tests' post-registration destination
  assertions. **64 mobile tests passing** (63 at self-report + 1 from the Undo/finalize race fix below).

---

## Bugs found during tester review and fixed

Both were found by `tester` reading the real implementation/framework behavior directly, not from a failing
test in the original suite — both are now fixed and re-confirmed correct.

1. **Mobile: Undo/finalize race.** `saved_addresses_screen.dart`'s delete flow started its own
   `Future.delayed(_undoWindow)` finalize timer at the same instant it called `showSnackBar`, but Flutter's
   real `SnackBar` only starts counting its own `duration` after its entrance animation completes and needs a
   further exit animation before it's actually gone — leaving a real ~250-500ms window where the on-screen
   Undo button was still tappable after the finalize timer had already fired and made the delete permanent, so
   a user's "Undo" tap would silently no-op with no error shown. **Fix:** added a `_finalizeSafetyMargin`
   (500ms) on top of `_undoWindow`, so finalize now fires at 4.5s instead of 4s — covering both animation legs.
   A new regression test asserts `deleteCallCount` is still `0` at the exact instant the *old* buggy timing
   would have fired, then confirms Undo still works at that instant. Confirmed correct by `tester`'s re-check.
2. **Backend: untested soft-delete boundary.** The first soft-delete pattern in the codebase was being
   blessed as a template for future stories, but no test directly exercised `PATCH`/`DELETE` against an
   already-soft-deleted address — the 404 behavior was only inferred from code plus a list-exclusion test.
   **Fix:** two new real-DB tests (`test_patch_on_an_already_soft_deleted_address_returns_404`,
   `test_delete_on_an_already_soft_deleted_address_returns_404`) directly confirm both verbs 404 on a
   soft-deleted row, not 200/500. No production code changed — the behavior was already correct; only test
   coverage closed the gap. Confirmed correct by `tester`'s re-check.

---

## Acceptance Criteria — Verification

All 9 acceptance criteria (from `Plan_S03_CUS-002.md`, sourced from the Tracker) were independently verified by
`tester` — full suites re-run from a clean shell each time, migration reversibility re-derived against a
disposable scratch database, default-uniqueness confirmed via direct post-write `SELECT` queries (not just
response bodies), and the skip-then-required-later flow (AC4/AC5/AC9) traced through a single, genuinely
continuous registration → skip → re-prompt test rather than three independent assumptions. All 9 passed, both
before and after the two follow-up fixes above.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `saved_addresses` table exists via migration, linked to `customer_profiles`, with label/address/city/region/country/lat-lng/default flag | Pass |
| 2 | Exactly one address per customer can be default at a time (setting a new default un-sets the previous one) | Pass |
| 3 | Add-address screen supports map-pin selection, manual entry, and "use current location" | Pass |
| 4 | First-address prompt at registration is skippable; skipping never blocks registration | Pass |
| 5 | If skipped, the app does not re-prompt until the customer attempts to submit a search request | Pass |
| 6 | Saved Addresses screen lists all addresses, default clearly indicated, supports edit and delete | Pass |
| 7 | Deleting the default either prompts for a new default or clearly indicates no default is set | Pass |
| 8 | A customer cannot view or modify another customer's addresses (ownership enforced) | Pass |
| 9 | Automated tests cover default-uniqueness, skip-then-required-later, and the ownership boundary | Pass |

---

## Architect Review — Findings and Resolution

The `architect` agent returned **STORY COMPLETE** — no must-fix items. Full findings in the (now-deleted)
`Checkpoint_S03_CUS-002.md`; summary:

1. **Collection endpoint pattern.** Confirmed correct: every `{address_id}`-addressable write resolves the
   caller's own profile first, then collapses "row missing" and "row owned by someone else" into the identical
   404 via `ensure_owner_or_not_found` — no code path can leak a 403 or an owner-revealing signal. Correctly
   mirrors AUTH-004's session-revocation precedent and correctly diverges from CUS-001's `/me` singleton (no
   `{id}` to defend there in the first place).
2. **First genuine soft-delete pattern.** Sound and consistent with `04_DATABASE.md`. `BaseRepository.delete()`
   (hard delete) is never called anywhere in the new code; every read path filters `is_active`. The two new
   boundary tests genuinely close the gap tester flagged. A good, minimal, reusable pattern for future
   soft-delete stories to copy as-is.
3. **Default-uniqueness defense-in-depth.** Confirmed the sequencing (unset-then-set, same transaction) makes
   the partial unique index a true backstop, not a mechanism papering over a missing service-layer step.
4. **Undo/finalize race fix — sound for single-delete; one new, non-blocking gap found for rapid multi-delete.**
   The per-address bookkeeping is correct (each delete's timer/state is independently keyed), but
   `ScaffoldMessenger`'s default snackbar queuing (no `removeCurrentSnackBar()` call anywhere) means a *second*
   rapid delete's own Undo affordance could become visible at almost the same instant its own finalize timer
   fires — a narrow, adjacent version of the same bug class the fix closed for the single-delete case. No AC
   exercises multi-delete; not blocking. Recommended follow-up: `removeCurrentSnackBar()` before showing a new
   delete snackbar, plus a regression test for two overlapping deletes.
5. **Shared `LocationPickerScreen` genericness.** Confirmed zero Customer-domain coupling — genuinely ready for
   future Provider-domain (S-18a/b) reuse without modification. The `mapViewBuilder` injectable-widget pattern
   is a narrowly-scoped, necessary testing seam (keeps a platform-view widget out of the test tree), not a code
   smell.
6. **AC4/AC5 registration-flow rewiring.** Confirmed the only change from AUTH-001–004's own shipped behavior
   is the post-session navigation target — no identity-module file touched, no AUTH-001–004 acceptance
   criterion weakened or reinterpreted.
7. **Standard mobile/backend review.** Feature-First/SRP conventions followed throughout; no hardcoded
   colors/strings; `app_en.arb`/`app_ar.arb` key sets match exactly (85/85); new dependencies match exactly
   what the Plan's sign-off section named, no drift.
8. **New finding (not in the original review brief):** `mobile/lib/core/network/maps_config.dart` has zero
   current call sites — the Maps API key is actually consumed natively (`AndroidManifest.xml`/
   `AppDelegate.swift`), not through this Dart constant. Low severity, small and well-documented, flagged for
   cleanup at a natural follow-up point rather than blocking.

### Must-fix vs nice-to-have (architect's final tally)

**Must-fix:** none — every AC is genuinely satisfied by real code and real tests; both tester-flagged issues
are confirmed correctly closed.

**Non-blocking follow-ups:**
1. Rapid back-to-back delete of two different addresses — `removeCurrentSnackBar()` fix + regression test
   (`frontend`).
2. `04_DATABASE.md` doc-currency: document `uq_saved_addresses_customer_default` (closed by this Walkthrough —
   see below).
3. `05_API_GUIDELINES.md`'s pagination rule has now been deviated from twice (`GET /auth/sessions`, `GET
   /customers/me/addresses`) under ADR-012's carve-out without that carve-out being visible from the guidelines
   doc itself — worth a one-line cross-reference at some point, not urgent.
4. `mobile/lib/core/network/maps_config.dart` — currently dead code, remove or wire up whenever native config
   is threaded through Dart.
5. `mypy` still not installed — carried forward from every prior story (AUTH-003, AUTH-004, CUS-001).

---

## Documentation updated at story close

- **`docs/AI/04_DATABASE.md`** — `saved_addresses`' "Constraints" section (previously blank) now documents
  `uq_saved_addresses_customer_default`, the partial unique index on `customer_id` WHERE `is_default = true AND
  is_active = true`.
- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-015**, generalizing the collection-vs-singleton endpoint-shape
  decision (client-`{id}`-addressable collection + `ensure_owner_or_not_found`, vs. an implicit-self `/me`
  singleton with no ownership check needed) as a durable rule future stories should follow rather than
  re-deriving each time.
- `docs/CHANGELOG.md` — new entry under `[Unreleased]`.
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 3 marked fully complete; Sprint 4 (Provider Storefront),
  first story PRO-001, named as next and unblocked.

---

## Testing Performed

- `cd backend && uv run pytest -q` — **265/265 passing** (263 at self-report + 2 from the soft-delete boundary
  follow-up), 0 regressions on AUTH-001–004/CUS-001.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` —
  verified independently by `backend`, `tester`, and `architect`, each against a disposable scratch database
  (never the shared dev/test DB), column-for-column match against `04_DATABASE.md` plus both new indexes.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- `cd mobile && flutter test` — **64/64 passing** (63 at self-report + 1 from the Undo/finalize regression
  test).
- `cd mobile && flutter analyze` — no issues found.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean, 76 files, 0 changed.
- `tester` agent: all 9 ACs independently verified with direct evidence, both before and after the two
  follow-up fixes — see table above.
- `architect` agent: STORY COMPLETE — see findings above.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_06_1500-9f47869ca8bb_saved_addresses.py` (new)
- `backend/app/modules/customer/models.py` — `SavedAddress`
- `backend/app/modules/customer/repositories/saved_address_repository.py` (new)
- `backend/app/modules/customer/services/saved_address_service.py` (new)
- `backend/app/modules/customer/schemas.py` — `SavedAddressResponse`/`CreateSavedAddressRequest`/`UpdateSavedAddressRequest`
- `backend/app/modules/customer/api.py` — `GET`/`POST /customers/me/addresses`, `PATCH`/`DELETE /customers/me/addresses/{address_id}`
- `backend/app/modules/customer/dependencies.py` — `get_saved_address_repository`/`get_saved_address_service`
- `backend/app/core/exceptions/{exceptions.py,__init__.py}` — `SavedAddressNotFoundError`
- `backend/tests/modules/customer/{test_saved_address_service.py,test_saved_address_endpoints.py}` (new)
- `backend/tests/conftest.py` — registered `SavedAddress` in the schema/cleanup lifecycle

### Mobile
- `mobile/pubspec.yaml` — `google_maps_flutter`, `geolocator`, `geocoding`
- `mobile/android/app/src/main/AndroidManifest.xml`, `mobile/ios/Runner/{AppDelegate.swift,Info.plist}` — platform config placeholders
- `mobile/lib/shared/widgets/location_picker/` (new) — `location_picker_screen.dart`, `location_service.dart`, `location_pick_result.dart`, `location_error_copy.dart`
- `mobile/lib/features/customer/domain/models/{saved_address.dart,saved_address_exception.dart,address_form_mode.dart,address_form_args.dart}` (new)
- `mobile/lib/features/customer/data/saved_address_repository.dart` (new)
- `mobile/lib/features/customer/state/{saved_addresses_controller.dart,address_form_controller.dart}` (new)
- `mobile/lib/features/customer/presentation/screens/{address_form_screen.dart,add_first_address_screen.dart,saved_addresses_screen.dart}` (new)
- `mobile/lib/features/customer/presentation/screens/profile_settings_screen.dart` — added Saved Addresses link
- `mobile/lib/features/customer/presentation/utils/saved_address_error_copy.dart` (new)
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` — temporary "Find a Service" stub
- `mobile/lib/features/auth/presentation/screens/{otp_entry_screen.dart,phone_entry_screen.dart}` — post-registration routing to `AddFirstAddressScreen`
- `mobile/lib/core/routing/{app_routes.dart,app_router.dart}` — `addFirstAddress`/`savedAddresses`/`addressForm`
- `mobile/lib/core/network/maps_config.dart` (new — flagged as currently dead code, see follow-ups)
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}`
- `mobile/test/shared/widgets/location_picker/` (new)
- `mobile/test/features/customer/{address_form_screen_test.dart,saved_addresses_screen_test.dart,fakes/fake_saved_address_repository.dart}` (new)
- `mobile/test/features/auth/first_address_prompt_test.dart` (new)
- `mobile/test/features/auth/{otp_entry_screen_test.dart,oauth_sign_in_test.dart,test_helpers.dart}` — updated post-sign-in destination assertions

---

## Follow-up Notes for Sprint Planning

- **Sprint 3 (Customer Profile & Locations) is now complete** — 2 of 2 stories done: CUS-001, CUS-002.
- Non-blocking follow-ups carried forward: the rapid multi-delete Undo-snackbar-queuing gap (`frontend`), the
  `05_API_GUIDELINES.md` pagination-carve-out cross-reference, the dead `maps_config.dart` cleanup, and `mypy`
  still not installed (carried forward from every prior story since AUTH-003).
- **Sprint 4 (Provider Storefront)** is next. Its first story, **PRO-001 — "Create my business or freelancer
  listing"**, depends on AUTH-004 and CUS-002 (both now done) and is unblocked. No stale `Plan_S04_PRO-001.md`
  was found from any old backlog numbering — it needs a fresh Plan against the current
  `docs/AI/Project_Tracker.xlsx`, same as every AUTH-00x/CUS-00x story before it.
