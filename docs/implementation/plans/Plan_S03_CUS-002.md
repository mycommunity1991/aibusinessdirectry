# Plan for Story CUS-002 — Manage My Service Locations

**Sprint:** 03 (Customer Profile & Locations) | **Epic:** ML3-EP01 | **Priority:** High | **Depends On:** CUS-001 (complete, merged to `main`)

---

## Story

As a customer, I want to save, edit, and remove addresses, and optionally add one during onboarding, so that I don't have to re-enter my location every time I search for a service.

This is the second and final story of Sprint 3. It implements Saved Addresses — the location data every future Search Request depends on (Sprint 7/8, not this story). Adding a first address at registration is explicitly skippable per the product's friction-reduction principle; the app must re-prompt only when an address is actually needed (attempting to submit a search), not before.

**Scope boundary:** does **not** include geospatial proximity-matching infrastructure (`earthdistance`/`cube`, `service_areas` GiST index) — that is DIR-001 (Sprint 6) and the Search Request domain (Sprint 7/8). This story only captures and manages plain `latitude`/`longitude` address data. Does not include the AI Conversation / Search Request screens themselves (S-06/S-07) — those don't exist yet and are out of scope for this story; only a minimal, clearly-temporary trigger stub is added so AC5 has something real to gate.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`)

1. `saved_addresses` table exists via migration, linked to `customer_profiles`, with a label, address line, city, region, country code, latitude/longitude, and a default flag.
2. Exactly one address per customer can be marked default at a time (setting a new default un-sets the previous one).
3. Add-address screen supports both map-pin selection and manual entry, plus a "use current location" option.
4. The first-address prompt at registration is skippable; skipping does not block registration completion or any other onboarding step.
5. If skipped, the app does not re-prompt for an address until the customer actually attempts to submit a search request.
6. Saved Addresses management screen lists all addresses with the default clearly indicated, and supports edit and delete.
7. Deleting the currently-default address either prompts the customer to choose a new default or clearly indicates no default is set.
8. A customer cannot view or modify another customer's addresses (ownership enforced).
9. Automated tests cover: default-address uniqueness, skip-then-required-later flow, and the ownership boundary.

---

## Verified Current State (read directly from code, not assumed)

- `docs/AI/04_DATABASE.md` already fully specifies `customer.saved_addresses` column-by-column (`customer_id` FK, `label` VARCHAR(50) nullable, `address_line` VARCHAR(500) NOT NULL, `city`/`region` VARCHAR(100) nullable, `country_code` CHAR(2) NOT NULL, `latitude`/`longitude` DOUBLE PRECISION NOT NULL, `is_default` BOOLEAN default `false`) — nothing to design at the column level, only implement. It lists no uniqueness constraint on `is_default` beyond the plain column — see Decision 2.
- `docs/AI/14_USER_FLOWS.md` Flow 1, step 5 confirms the exact insertion point: "Customer is prompted (optional, skippable) to add a first `saved_addresses` row," positioned between profile/role creation (step 4) and session establishment (step 6). In the actual shipped mobile code, session is established (`authSessionControllerProvider.setSession(token)`) **before** navigation in both registration paths — so inserting the address prompt after `setSession` and before the home placeholder achieves the same effect: the Account/session is already fully live by the time the address screen renders, so "skip" genuinely cannot block registration (AC4) without any backend flow change.
- `docs/AI/15_SCREEN_INVENTORY.md` already names both screens this story builds: **S-05 "Add Your First Address (skippable)"** (map pin / manual entry / "Use current location" / Skip link) in the Onboarding & Auth flow, and **S-12 "Saved Addresses"** (list with default badge, add/edit/delete) under Customer Activity/Profile/Settings, linked from S-14 (Profile & Settings, already shipped by CUS-001).
- `mobile/lib/features/auth/presentation/screens/otp_entry_screen.dart` (`_onVerify`, line ~161) and `phone_entry_screen.dart` (`_handleOAuthResult`, line ~212) are the **only two** places `context.go(AppRoutes.homePlaceholder)` is called after a successful sign-in — both call `setSession` first, then navigate. Both need the same one-line change: route to the new first-address screen instead of directly to home.
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` has no search entry point at all today (S-06/S-07 don't exist yet) — confirms AC5's "attempts to submit a search request" has no real trigger to hook into. See Decision 6.
- `backend/app/modules/customer/` (CUS-001) already has the exact repository/service/schema/api layering to extend: `BaseRepository[T]` (generic create/update/get_by_id/get_all, **hard** `delete()`), `CustomerService.get_my_profile(user_id)` (get-or-create for a `customer_profiles` row), `require_role(ROLE_CUSTOMER)` on `/customers/me`. `SavedAddressService` should depend on the already-shipped `CustomerService` (same-module dependency, not cross-module) to resolve/create the caller's `customer_profiles.id`, rather than duplicating get-or-create logic.
- `backend/app/database/mixins.py`'s `CommonColumnsMixin` gives every business table `deleted_at`/`is_active`/`version`. `docs/AI/04_DATABASE.md`'s "Soft Delete" section is explicit: "Records are never permanently removed during normal operations. Permanent deletion is an administrative operation." `BaseRepository.delete()` does a **hard** `session.delete()` — no repository in this codebase has ever needed a real soft-delete method yet (grepped: no call site does `deleted_at`/`is_active` writes anywhere). This is the first story needing one — see Decision 3.
- `backend/app/core/authorization.py`'s `ensure_owner_or_not_found(owner_id, requester_id, *, not_found_exc)` (built for AUTH-004's `DELETE /auth/sessions/{id}`) is the exact tool for AC8: `saved_addresses` is a client-`{id}`-addressable **collection**, not a `/me`-singleton like `customer_profiles` — the task brief's own framing is correct, confirmed by reading `session_service.py`'s `revoke_session` (looks up by id, then `ensure_owner_or_not_found(session.user_id if session else None, user_id, not_found_exc=SessionNotFoundError())`) side-by-side with CUS-001's `/customers/me` (no `{id}` at all, so nothing to check). This story's endpoints mirror the sessions shape, not the `/me` shape.
- `backend/app/modules/identity/api.py`'s `GET /auth/sessions` is `SuccessResponse[list[SessionSummaryResponse]]`, explicitly **unpaginated** ("a user's realistic session count is small and per-owner") — the exact precedent for `GET /customers/me/addresses`, which is equally small and per-owner. No pagination needed despite `05_API_GUIDELINES.md`'s general collection-endpoint pagination rule, following the same accepted exception already established in this codebase.
- `docs/AI/12_TECH_STACK.md`'s "Approved Flutter Packages" has no map, geolocation, or geocoding package of any kind. No backend geospatial extension is installed or configured (`04_DATABASE.md` Section 13 recommends `cube`/`earthdistance` for a **later** story, DIR-001 — not this one, and not needed here since this story never queries by distance). **New mobile dependencies are required for AC3 — see Decisions Needing Sign-Off below.**
- `docs/AI/16_UX_GUIDELINES.md`'s Feedback/Reversibility section: "Reversible actions (deleting a saved address, for instance) use an 'Undo' snackbar rather than a confirmation dialog" — this is the **explicit, named example** in that doc, confirming the delete-address interaction pattern directly. `07_UI_GUIDELINES.md`: "Bottom Sheets are preferred over dialogs for: Selection" — the tool for AC7's "choose a new default" moment.
- `docs/AI/16_UX_GUIDELINES.md` Form & Input UX: "Skippable is actually skippable: `S-05` (first address) must not silently require the field later — if skipped, the app asks again only when an address is actually needed (submitting the first Search Request), not before" — this is AC4/AC5 verbatim, confirming there is no ambiguity to resolve, only to implement correctly.

---

## Architecture Decisions

### Decision 1 — Endpoint shape: a client-`{id}`-addressable collection under `/customers/me/addresses`, mirroring AUTH-004 sessions, not CUS-001's `/me` singleton

Unlike `customer_profiles` (1:1, no `{id}` ever needed), `saved_addresses` is a genuine 1:N collection the client must address by id (edit one specific address, delete one specific address, set one specific address as default). Endpoints:

```
GET    /api/v1/customers/me/addresses              → list all of the caller's addresses (AC6)
POST   /api/v1/customers/me/addresses               → create (AC1, AC3 backend side)
PATCH  /api/v1/customers/me/addresses/{address_id}  → partial update, incl. is_default (AC2, AC6)
DELETE /api/v1/customers/me/addresses/{address_id}  → soft-delete (AC6, AC7)
```

The `{address_id}` path parameter is real and client-addressable (unlike `/me`), so ownership is enforced defensively via `ensure_owner_or_not_found` — not structurally guaranteed by route shape the way `/customers/me` was. Every read/write first resolves the caller's own `customer_profiles.id` (via `CustomerService.get_my_profile`, get-or-create), then checks the target row's `customer_id` against it, raising `SavedAddressNotFoundError` (404, mirroring `SessionNotFoundError`'s non-revealing design — a row that doesn't exist and a row owned by someone else are indistinguishable to the caller) on mismatch. This satisfies AC8.

No separate `set-default` action endpoint: `PATCH .../addresses/{id}` accepts `is_default: true` as one of its partial-update fields, and `POST .../addresses` also accepts an optional `is_default` on create — both routes through the same service-layer "unset the customer's other defaults first" logic (Decision 2). Keeps the API surface minimal, consistent with "avoid unnecessary endpoints."

### Decision 2 — Default-uniqueness (AC2): service-layer transactional unset-then-set, plus a defense-in-depth partial unique index

**Primary mechanism (required for correctness):** `SavedAddressService` wraps every "set `is_default = true`" path (both `create_address` and `update_address`) in a single flush-only operation: unset `is_default` for every other active address belonging to that `customer_id`, then set the target row. Both writes happen on the same request-scoped `AsyncSession`, inside the same endpoint transaction (the API layer's single `await db.commit()` remains the only boundary) — so a crash mid-operation can never leave two rows both marked default within one committed transaction.

**Defense-in-depth (recommended addition, not required for sign-off):** a partial unique index, `CREATE UNIQUE INDEX uq_saved_addresses_customer_default ON customer.saved_addresses (customer_id) WHERE is_default = true AND is_active = true`, added in the new migration. This is not currently listed in `04_DATABASE.md`'s `saved_addresses` section (which shows no **Constraints** line, only the `idx_saved_addresses_customer_id` index) — it is a genuine addition beyond the literal schema doc. It carries zero migration risk (brand-new table, no pre-existing data to violate it) and mirrors this project's own precedent for partial-unique defaults elsewhere (`uq_users_email_provider`, `uq_providers_user_id`). This is **not** treated as a sign-off-gated decision (no external dependency, no behavior change visible to any existing caller, purely additive safety net for a brand-new table) — but `04_DATABASE.md` must be updated afterward to document the new constraint (a documentation-currency action for `tech-lead` at story close, mirroring the AUTH-002 precedent of flagging doc updates rather than having `backend`/`architect` write to `docs/AI/` directly).

### Decision 3 — Soft delete, not `BaseRepository.delete()`

`DELETE /customers/me/addresses/{id}` must not hard-delete, per `04_DATABASE.md`'s Soft Delete section. `SavedAddressRepository` gets a dedicated `soft_delete(address) -> None` method (`address.deleted_at = now()`, `address.is_active = False`, flush) instead of reusing `BaseRepository.delete()`. Every list/get query (`list_for_customer`, `get_by_id_for_customer`) filters `is_active == True` (equivalently `deleted_at IS NULL`) so a soft-deleted row is invisible to the customer going forward, exactly as if hard-deleted from the API's perspective, while the row itself survives per the project's permanent-deletion-is-admin-only rule. This is the **first** repository in the codebase implementing a real soft-delete method — flag for `architect` review as a new pattern other future "delete" stories should copy, not reinvent.

On delete, the backend does **not** auto-promote another address to default if the deleted one was the default — it simply leaves the customer with no default address. Auto-promotion would silently remove the customer's ability to choose (AC7 explicitly says "prompts the customer to choose... or clearly indicates no default is set" — both outcomes require the *customer*, not the backend, to decide). The mobile client is responsible for detecting "I just deleted what was the default" (from its own cached list, or from the delete response echoing back whether the deleted row `was_default`) and driving the AC7 UX (Decision 8).

### Decision 4 — `SavedAddressService` depends on `CustomerService`, not a raw `CustomerProfileRepository`

Both live in the same `customer` module (no cross-module boundary crossed, unlike CUS-001's `identity → customer` call), but reusing `CustomerService.get_my_profile(user_id)` (already get-or-create, per CUS-001 Decision 4) rather than duplicating that logic in a second repository call avoids a legacy-account edge case gap: a pre-CUS-001 account that has never called `GET`/`PATCH /customers/me` still has no `customer_profiles` row yet, and must still be able to add its first address without a spurious 404/500. `SavedAddressService.__init__` takes `saved_address_repository: SavedAddressRepository, customer_service: CustomerService`.

### Decision 5 — Country code: free-text ISO-3166-1 alpha-2 field, not a hardcoded UAE default or a full country picker

`04_DATABASE.md` deliberately keeps `country_code` generic ("kept generic, not UAE-specific, per country-agnostic requirement") and `providers.country_code` carries the same "deliberately not hardcoded to UAE" note. Building a full searchable country-picker widget is scope creep beyond what any AC requires. This story uses a plain, validated 2-letter text field (`Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` server-side; uppercase-transforming client-side), pre-filled from reverse-geocoding when the address came from a map-pin/current-location pick (Decision 7), always user-editable, with no default value assumed when starting from pure manual entry.

### Decision 6 — AC5's "search request" trigger: a minimal, explicitly temporary stub on the Home placeholder — not a Search feature

The AI Conversation / Search Request screens (S-06/S-07) are Sprint 7/8 stories that do not exist yet. Building any part of that feature now would be scope creep this Plan must not introduce. Instead: `home_placeholder_screen.dart` gains one new button (e.g. "Find a Service"), commented explicitly as *"a temporary stand-in for the real AI Conversation entry point (S-06/S-07, a future story) — its only current behavior is enforcing the address-required gate for AC5; whichever future story builds the real Search feature replaces this button's target, not this gate."* Its wired behavior: call `GET /customers/me/addresses`; if empty, navigate to the same Add Address screen used elsewhere in this story, but in **non-skippable** mode (contextual copy: "Add an address to search for services near you," no Skip link); if non-empty, show a plain "Search coming soon" snackbar (no navigation to anything resembling S-06/S-07). This is the smallest possible real trigger that satisfies AC5's testable behavior ("does not re-prompt until the customer actually attempts to submit a search request... only re-prompts at that moment") without inventing fake Search functionality.

### Decision 7 — One shared, reusable Location Picker; Add/Edit Address screen used for all three entry points (S-05, S-12, and the AC5 re-prompt)

A single `AddressFormScreen` (mode: `add` / `edit`, with an optional `skippable: bool` flag controlling whether a Skip link renders) is used for: the first-address-at-registration prompt (S-05, `skippable: true`), Saved Addresses management add/edit (S-12, `skippable: false`, not applicable — edit always has existing data), and the AC5 re-prompt (`skippable: false`). It contains: `label` (optional text), `address_line`/`city`/`region`/`country_code` (manual-entry text fields, per AC3's "manual entry"), and a location section that is **never** a raw numeric lat/lng input — the user sets the pin exclusively via one of two paths: (a) opening a full-screen map picker (fixed center-pin over a pannable `GoogleMap`, "Confirm this location" primary action) or (b) tapping "Use current location" (device geolocation via `geolocator`, permission-request handled inline). Either path reverse-geocodes the resulting coordinates (via `geocoding`) to prefill `address_line`/`city`/`region`/`country_code`, all still user-editable before Save. `latitude`/`longitude` are required (matching the DB's `NOT NULL`), so Save is disabled until a location has been set by one of the two location paths at least once — manual text entry alone (without ever having picked a pin) cannot satisfy the DB's coordinate requirement.

The full-screen map picker is built as a shared, reusable widget/screen (`mobile/lib/shared/widgets/location_picker/location_picker_screen.dart`, per `07_UI_GUIDELINES.md`'s "shared UI components belong in `shared/widgets`"), deliberately generic (returns `(latitude, longitude, placemark)`, no Customer-domain knowledge baked in) so the future Business/Freelancer location-entry screens (S-18a/b, Provider domain, not this story) can reuse it without rebuilding map/geolocation code from scratch. This is a forward-compatibility note for the `architect`/future planner, not a scope expansion of this story — S-18a/b is not touched here.

### Decision 8 — AC7 UX: Undo snackbar for delete, bottom sheet for default re-selection

Per `16_UX_GUIDELINES.md`'s own named example, deleting an address is a reversible action → an "Undo" snackbar (not a confirmation dialog) on the Saved Addresses screen (S-12). If the deleted address's cached `is_default` was `true`: when the Undo window expires (delete is finalized), check the remaining address list — if non-empty, present a bottom sheet ("Choose a new default address," per `07_UI_GUIDELINES.md`'s "Bottom Sheets preferred for Selection") listing the remaining addresses plus a "Not now" option; if the list is now empty, show an inline "No default address set" state instead of a bottom sheet. "Not now" is a valid, final answer — the list then visibly shows no address carrying the "Default" badge, satisfying AC7's "or clearly indicates no default is set" branch without forcing a choice.

---

## Decisions Needing Explicit User Sign-Off Before Implementation

AC3 ("map-pin selection... plus a 'use current location' option") cannot be built with any currently-approved package — `docs/AI/12_TECH_STACK.md` has no map, geolocation, or geocoding entry at all. Proposing three new Flutter dependencies, mirroring the AUTH-002 precedent (code + automated tests ship now using fakes/mocks at the repository layer; real-device functionality needs external credentials/platform config as a separate, later prerequisite):

1. **`google_maps_flutter`** (Flutter-team-maintained, official plugin) — renders the interactive map and center-pin for map-pin selection. Requires a **Google Maps API key** (separate Android/iOS keys), a Google Cloud Console project with Maps SDK for Android/iOS enabled, **and a billing account attached** (Google requires this even within the free-tier quota) — a real external/financial prerequisite, not just a code change.
2. **`geolocator`** (Baseflow — the most widely used, actively maintained Flutter geolocation plugin) — device permission request + current-position retrieval for "Use current location." Needs `NSLocationWhenInUseUsageDescription` (iOS `Info.plist`) and `ACCESS_FINE_LOCATION`/`ACCESS_COARSE_LOCATION` (Android `AndroidManifest.xml`) — standard platform config, no billing/API key.
3. **`geocoding`** (Baseflow) — reverse-geocodes a lat/lng into address components using each platform's native geocoder (`CLGeocoder`/Android `Geocoder`), to prefill `address_line`/`city`/`region`/`country_code` after a map-pin drop or current-location fix. No API key/billing.

None conflict with `12_TECH_STACK.md`'s "Prohibited Technologies" (no second state-management/routing/HTTP-client solution) or appear on its "Packages Requiring Approval" deny-list, but all three are new capability categories requiring explicit approval before `frontend` starts, per this project's technology-change policy. **No new backend/Python dependency is needed** — reverse geocoding happens client-side; the backend only ever stores/serves plain `latitude`/`longitude` plus text fields already validated by Pydantic.

**If approved:** real Google Maps API keys and platform-native configuration (`AndroidManifest.xml`, iOS `AppDelegate.swift`/`Info.plist`) are external prerequisites the user supplies later for real-device testing — same accepted gap AUTH-002 left for `google_sign_in`/`sign_in_with_apple`. Automated tests do not depend on them.

**Please confirm before `frontend` work begins:** (a) approve all three packages, (b) confirm who/when will provision the Google Maps API key + billing (can be deferred past this story's code-complete/test-passing milestone, matching the AUTH-002 precedent), (c) confirm the partial-unique-index addition in Decision 2 (low-risk, recommended, not requiring the same weight of approval as the mobile dependencies, but flagged for visibility).

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration (down-revision = current head): creates `customer.saved_addresses` per `04_DATABASE.md` (Common Columns + `customer_id` FK → `customer.customer_profiles.id`, `label` VARCHAR(50) nullable, `address_line` VARCHAR(500) NOT NULL, `city`/`region` VARCHAR(100) nullable, `country_code` CHAR(2) NOT NULL, `latitude`/`longitude` DOUBLE PRECISION NOT NULL, `is_default` BOOLEAN NOT NULL default `false`), `idx_saved_addresses_customer_id`, plus the partial unique index from Decision 2. Verify upgrade and downgrade both work cleanly.

### Models (`backend/app/modules/customer/models.py`)
2. `SavedAddress(CommonColumnsMixin, Base)`, schema `"customer"`, mirroring `CustomerProfile`'s style.

### Repository
3. `backend/app/modules/customer/repositories/saved_address_repository.py`: `SavedAddressRepository(BaseRepository[SavedAddress])` with `list_for_customer(customer_id) -> Sequence[SavedAddress]` (filters `is_active`), `get_active_by_id(address_id) -> SavedAddress | None` (filters `is_active`, used before the ownership check), `unset_other_defaults(customer_id, *, except_address_id=None) -> None` (bulk `UPDATE ... SET is_default = false WHERE customer_id = :cid AND is_default = true AND id != :except`, flush only), `soft_delete(address) -> None` (Decision 3).

### Service
4. `backend/app/modules/customer/services/saved_address_service.py`: `SavedAddressService(saved_address_repository, customer_service)` with:
   - `list_my_addresses(user_id) -> Sequence[SavedAddress]`
   - `create_address(user_id, *, fields: dict) -> SavedAddress` — resolves/creates the caller's `customer_profiles.id` via `customer_service.get_my_profile`; if `fields.get("is_default")`, calls `unset_other_defaults` first; creates the row.
   - `update_address(user_id, address_id, *, fields: dict) -> SavedAddress` — resolves profile id; `get_active_by_id`; `ensure_owner_or_not_found(address.customer_id if address else None, profile.id, not_found_exc=SavedAddressNotFoundError())`; if `fields.get("is_default") is True`, `unset_other_defaults(profile.id, except_address_id=address.id)` first; partial-update.
   - `delete_address(user_id, address_id) -> None` — same resolve + ownership check, then `soft_delete`.

### Schemas (`backend/app/modules/customer/schemas.py`)
5. `SavedAddressResponse { id, label, address_line, city, region, country_code, latitude, longitude, is_default }`.
6. `CreateSavedAddressRequest { label?, address_line (required), city?, region?, country_code (required, 2-letter), latitude (required, -90..90), longitude (required, -180..180), is_default? = false }`.
7. `UpdateSavedAddressRequest` — all fields optional (Pydantic v2 `exclude_unset=True`, mirroring `UpdateCustomerProfileRequest`'s partial-update pattern).

### Exceptions (`backend/app/core/exceptions/exceptions.py` + `__init__.py`)
8. `SavedAddressNotFoundError(BusinessException)` — 404, generic message, mirroring `SessionNotFoundError`'s non-revealing design exactly (AC8).

### API (`backend/app/modules/customer/api.py`)
9. `GET`, `POST /customers/me/addresses`; `PATCH`, `DELETE /customers/me/addresses/{address_id}` — all behind `require_role(ROLE_CUSTOMER)`. List and create return `SuccessResponse[...]` (list is unpaginated, per Decision-supporting precedent above). Delete returns `SuccessResponse[None]`, mirroring `DELETE /auth/sessions/{id}`.

### Dependencies (`backend/app/modules/customer/dependencies.py`)
10. `get_saved_address_repository`, `get_saved_address_service` (adds `Depends(get_customer_service)` as a sibling dependency, per Decision 4).

### Tests
11. `backend/tests/modules/customer/test_saved_address_service.py`: create with `is_default=True` unsets a prior default (both via create-time and update-time paths — **AC9's "default-address uniqueness"**); partial update only changes provided fields; soft-deleted rows excluded from `list_for_customer`; deleting a non-default address leaves the existing default untouched.
12. `backend/tests/modules/customer/test_saved_address_endpoints.py`: full CRUD happy path; **AC9's "ownership boundary"** — two different customers' tokens, address A created by customer 1, customer 2's token gets 404 (not 403) on `GET`/`PATCH`/`DELETE .../addresses/{A.id}`, and customer 2's `GET .../addresses` list never includes A; unauthenticated → 401; a legacy account with no prior `customer_profiles` row can still create its first address (get-or-create, Decision 4).

---

## Mobile — Proposed Changes

### Shared (`mobile/lib/shared/widgets/location_picker/`)
13. `location_picker_screen.dart` — full-screen `GoogleMap` with a fixed center pin, "Use current location" button (`geolocator` permission flow), "Confirm this location" primary action; returns `(latitude, longitude, Placemark?)` via `geocoding`'s reverse-lookup. Generic, no Customer-domain imports (Decision 7).

### Feature: Customer — Addresses (extends the existing `features/customer/` module from CUS-001)
14. `domain/models/saved_address.dart` — plain model mirroring `SavedAddressResponse`.
15. `data/saved_address_repository.dart` — `list()`, `create({...})`, `update(id, {...})`, `delete(id)` against `/customers/me/addresses`, following `customer_repository.dart`'s never-leak-raw-Dio-error convention exactly.
16. `state/saved_addresses_controller.dart` — Riverpod `AsyncNotifier<List<SavedAddress>>` backing S-12's list (load, refresh-after-create/edit/delete).
17. `state/address_form_controller.dart` — backs `AddressFormScreen`'s field state (label/address line/city/region/country code/lat-lng-from-picker), save/skip actions.
18. `presentation/screens/address_form_screen.dart` — the shared Add/Edit screen per Decision 7 (`mode`, `skippable` params). Contains the manual-entry text fields plus the "Pick on map" / "Use current location" launchers into `LocationPickerScreen`.
19. `presentation/screens/saved_addresses_screen.dart` (S-12) — list with a "Default" badge on the default row, tap → edit, delete action → Undo snackbar (Decision 8), FAB → add (`AddressFormScreen(mode: add, skippable: false)`). Post-delete-of-default flow per Decision 8 (bottom sheet or "no default set" inline state).
20. New routes: `AppRoutes.addFirstAddress` (S-05, `skippable: true`), `AppRoutes.savedAddresses` (S-12), `AppRoutes.addressForm` (shared add/edit, `extra`-passed args for mode/skippable/prefill).

### Registration flow integration (AC4/AC5)
21. `otp_entry_screen.dart`'s `_onVerify` and `phone_entry_screen.dart`'s `_handleOAuthResult`: change `context.go(AppRoutes.homePlaceholder)` → `context.go(AppRoutes.addFirstAddress)`. `AddFirstAddressScreen` (thin wrapper around `AddressFormScreen(mode: add, skippable: true)`): Skip → `context.go(AppRoutes.homePlaceholder)` with no API call; Save → creates the address (`is_default: true`, since it's necessarily the customer's first) → `context.go(AppRoutes.homePlaceholder)`.
22. Profile & Settings screen (`profile_settings_screen.dart`, CUS-001): add a "Saved Addresses" list tile navigating to `AppRoutes.savedAddresses` — this is the pre-existing S-14 link slot CUS-001's own Plan explicitly deferred ("Saved Addresses link" was named but not built in that story).
23. `home_placeholder_screen.dart`: add the temporary "Find a Service" stub button per Decision 6.

### Core
24. Add `oauthConfig`-equivalent for Maps: a `String.fromEnvironment`-based Google Maps API key config, mirroring `oauth_config.dart`'s pattern — blank by default, real key supplied later (Decisions Needing Sign-Off).
25. Platform config placeholders (Android `AndroidManifest.xml` meta-data key, iOS `AppDelegate.swift`/`Info.plist` entries for Maps API key + location-usage descriptions) — added but left with placeholder/blank values, exactly mirroring AUTH-002's accepted "platform-native configuration not done, external prerequisite" gap.

### Tests
26. `mobile/test/features/customer/address_form_screen_test.dart`: manual-entry field editing; Save disabled until a location has been set via the picker or current-location path (mocked); skip link present/absent per `skippable`; Skip navigates home with no repository call (AC4).
27. `mobile/test/features/customer/saved_addresses_screen_test.dart`: renders list with default badge; delete → Undo snackbar; deleting the default → bottom sheet (remaining non-empty) or inline "no default" state (remaining empty) — **AC9's "skip-then-required-later flow" is proven by a registration-flow-level test**, not this file: see item 28.
28. `mobile/test/features/auth/first_address_prompt_test.dart` (or extends the existing OTP/OAuth flow tests): **AC9's "skip-then-required-later" test** — simulate registration → Skip on the first-address prompt → lands on home with no address created → tap the Home "Find a Service" stub → routed to the (non-skippable) re-prompt screen, not silently let through.
29. `mobile/test/features/customer/fakes/fake_saved_address_repository.dart` mirroring `fake_customer_repository.dart`'s pattern.
30. `mobile/test/shared/widgets/location_picker_screen_test.dart` — map/current-location interactions mocked (no real `GoogleMap`/`geolocator`/`geocoding` platform channel calls in tests), mirroring how `oauth_sign_in_test.dart` fully replaces `AuthRepository` rather than invoking real plugin code.

---

## Explicitly Out of Scope (do not implement in this story)

- Any geospatial proximity-matching infrastructure (`earthdistance`/`cube`, `service_areas` GiST index, "providers within N meters" queries) — DIR-001 (Sprint 6).
- The AI Conversation / Search Request screens themselves (S-06/S-07) — only a minimal address-gate stub is added to Home (Decision 6); do not build any part of the chat/intake UI.
- Business/Freelancer location-entry screens (S-18a/b) — the shared `LocationPickerScreen` is built generically enough for future reuse there, but this story does not touch the Provider domain.
- A one-off `set-default` REST action endpoint — folded into `PATCH .../addresses/{id}` per Decision 1.
- Backend-side reverse geocoding / any new Python HTTP-based geocoding dependency — reverse geocoding is client-side only (Decision 7).
- A full searchable country picker widget — plain validated ISO alpha-2 text field only (Decision 5).
- Any change to `03_DOMAIN_MODEL.md`/`04_DATABASE.md` schema beyond what they already specify for `saved_addresses`, except the Decision 2 partial-unique-index addition (flagged for a follow-up doc update, not a redesign).
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **User sign-off** on the three new Flutter dependencies (`google_maps_flutter`, `geolocator`, `geocoding`) and the Decision 2 partial-unique-index addition, before `frontend` begins (backend work items 1–12 can start in parallel — they have no dependency on the map packages).
2. **backend** — Migration, model, repository, `SavedAddressService`, schemas, exception, API, dependencies (items 1–12). ACs to satisfy: 1, 2, 8, and half of 9 (default-uniqueness + ownership-boundary tests).
3. **frontend** — Shared location picker, Addresses feature, registration-flow rewiring, Home stub, Profile & Settings link, tests (items 13–30), once the backend endpoints exist (or in parallel against a fake repository). ACs to satisfy: 3, 4, 5, 6, 7, and the remaining third of 9 (skip-then-required-later test).
4. **tester** — Verify all 9 ACs individually. Particular attention to: AC2 (test both the create-time and update-time "unset prior default" paths, and confirm the partial unique index alone doesn't silently paper over a missing service-layer unset-first step — i.e. read the actual service code, don't just trust the DB constraint caught it); AC4/AC5 (read the actual registration-flow test to confirm Skip truly reaches the home placeholder with a live session and no address row, and that the Home stub genuinely re-gates on zero addresses); AC7 (both branches — bottom sheet when addresses remain, inline "no default" when they don't); AC8 (404, not 403, on cross-customer access, mirroring AUTH-004's non-revealing-error precedent).
5. **architect** — Review the new client-`{id}`-addressable-collection pattern (Decision 1) against `06_SECURITY.md`/AUTH-004 precedent, the first real soft-delete repository method (Decision 3) as a pattern other future stories should copy, the partial-unique-index addition (Decision 2) against `04_DATABASE.md` currency, the three new Flutter dependencies against `12_TECH_STACK.md`, and the shared `LocationPickerScreen`'s genericness (Decision 7) for future Provider-domain reuse.
6. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 1 (collection-vs-singleton endpoint shape choice) as the next available ADR in `09_DECISIONS.md`; update `04_DATABASE.md` to document the new partial unique index; update `12_TECH_STACK.md`'s "Approved Flutter Packages" with the three new entries.

---

## Verification Plan (mapped to the 9 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade; `\d customer.saved_addresses` shows every column/type/nullability in `04_DATABASE.md`, plus the new partial unique index. |
| 2 | Unit test: creating address B with `is_default=True` while A was default flips A to `false`; same for an `update_address` call flipping the currently-default C off in favor of B. |
| 3 | Widget test: `AddressFormScreen` renders manual-entry fields, a "Pick on map" launcher, and a "Use current location" button; Save stays disabled until the (mocked) location picker/current-location path returns coordinates. |
| 4 | Integration/widget test: registration flow → Skip on the first-address prompt → session is already live (token present) and the customer lands on the home placeholder, with zero `saved_addresses` rows created. |
| 5 | The AC4 test continued: from that skipped state, tapping the Home "Find a Service" stub routes to the non-skippable re-prompt screen — proving the app does not ask again until this specific trigger, and does ask exactly then. |
| 6 | Widget test: Saved Addresses screen lists all active addresses, default row visibly badged, edit and delete both wired to the real repository calls. |
| 7 | Two widget tests: deleting the default with other addresses remaining shows the "choose a new default" bottom sheet; deleting the only (default) address shows the inline "no default set" state. |
| 8 | Integration test: customer 2's token against `GET`/`PATCH`/`DELETE .../addresses/{customer-1's-address-id}` returns 404 for every method; `GET .../addresses` for customer 2 never includes customer 1's rows. |
| 9 | The three tests above (AC2, AC4/5 combined flow, AC8) are the three named "automated tests cover" items — confirmed as three distinct, independently-runnable test cases, not one test doing double duty. |

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md`
- `docs/AI/04_DATABASE.md`
- `docs/AI/05_API_GUIDELINES.md`
- `docs/AI/06_SECURITY.md`
- `docs/AI/07_UI_GUIDELINES.md`
- `docs/AI/11_MVP_SCOPE.md`
- `docs/AI/12_TECH_STACK.md`
- `docs/AI/14_USER_FLOWS.md`
- `docs/AI/15_SCREEN_INVENTORY.md`
- `docs/AI/16_UX_GUIDELINES.md`
- `docs/implementation/plans/Plan_S03_CUS-001.md` (Customer module conventions this story extends)
- `docs/implementation/plans/Plan_S02_AUTH-004.md` (`ensure_owner_or_not_found` / non-revealing 404 origin)
- `docs/implementation/plans/Plan_S02_AUTH-002.md` (new-mobile-dependency sign-off precedent)
