**Active Story:** Sprint 3 | CUS-002 | Manage My Service Locations

**Story:**
As a customer, I want to save, edit, and remove addresses, and optionally add one during onboarding, so that I don't have to re-enter my location every time I search for a service.

This is the second and final story of Sprint 3, extending the `customer` module CUS-001 already shipped (`backend/app/modules/customer/`, `mobile/lib/features/customer/`). It implements Saved Addresses — the location data every future Search Request depends on. The first-address prompt at registration is explicitly skippable per the product's friction-reduction principle; the app re-prompts only when a search is actually attempted, not before.

**Scope boundary:** does NOT include geospatial proximity-matching (`earthdistance`/`cube`, `service_areas` GiST index — DIR-001, Sprint 6) or the AI Conversation/Search Request screens themselves (S-06/S-07 — Sprint 7/8, don't exist yet). This story only stores/manages plain `latitude`/`longitude` + text address fields, and adds a minimal, explicitly-temporary stub trigger for AC5 — not a Search feature.

---

## Technical Context & Architecture Constraints

- `docs/AI/04_DATABASE.md` already fully specifies `customer.saved_addresses` column-by-column — nothing to design at the column level, only implement.
- **Endpoint shape is a client-`{id}`-addressable collection, unlike CUS-001's `/customers/me` singleton:** `GET`/`POST /customers/me/addresses`, `PATCH`/`DELETE /customers/me/addresses/{address_id}`. Because `{address_id}` is real and client-supplied, ownership must be enforced defensively via `app.core.authorization.ensure_owner_or_not_found` (already built for AUTH-004's `DELETE /auth/sessions/{id}` — reuse it, do not reinvent) — raise a new `SavedAddressNotFoundError` (404, generic, mirroring `SessionNotFoundError`'s non-revealing design) on any ownership mismatch or missing row, never a 403.
- **Default-uniqueness (AC2) is primarily a service-layer concern, not just a DB constraint:** both `create_address` (when `is_default=True`) and `update_address` (when setting `is_default=True`) must first unset every other active address's `is_default` for that customer, in the same flush (never a separate commit) as the write itself. Additionally add a partial unique index (`customer_id`) `WHERE is_default = true AND is_active = true` as a defense-in-depth backstop — this is a genuine addition beyond `04_DATABASE.md`'s literal text for this table (which lists no constraint), flagged for a follow-up doc update, not a redesign; it carries zero migration risk since the table is brand-new.
- **Soft delete, not `BaseRepository.delete()` (which hard-deletes):** `DELETE /customers/me/addresses/{id}` must set `deleted_at`/`is_active` per `04_DATABASE.md`'s Soft Delete rule ("permanent deletion is an administrative operation"). Add a dedicated `SavedAddressRepository.soft_delete()` method; every list/get query filters `is_active`. This is the first soft-delete method in this codebase — a pattern, not a one-off.
- The backend never auto-promotes a new default when the current default is deleted — it leaves the customer with no default. AC7's "prompts the customer to choose... or clearly indicates no default is set" is a **mobile-side** decision after a successful delete, not backend logic.
- `SavedAddressService` should depend on the already-shipped `CustomerService.get_my_profile(user_id)` (get-or-create) to resolve the caller's `customer_profiles.id` — same-module dependency, not cross-module — so a legacy account with no profile row yet can still add its first address without a spurious failure.
- **Registration-flow insertion point (AC4/AC5) is already identified — do not re-derive it:** `mobile/lib/features/auth/presentation/screens/otp_entry_screen.dart`'s `_onVerify` and `phone_entry_screen.dart`'s `_handleOAuthResult` both call `authSessionControllerProvider.setSession(token)` **then** `context.go(AppRoutes.homePlaceholder)`. Change both to route to a new `AppRoutes.addFirstAddress` screen instead — session/registration is already fully complete by that point (the JWT is already set), so Skip genuinely cannot block registration; it only skips creating an address row.
- **AC5's "search request" trigger does not exist as a real feature yet (S-06/S-07 are Sprint 7/8).** Add one small, explicitly-commented-as-temporary "Find a Service" button to `home_placeholder_screen.dart`: on tap, `GET /customers/me/addresses` — if empty, navigate to the same Add Address screen in **non-skippable** mode; if non-empty, show a plain "Search coming soon" snackbar. Do not build any part of the actual AI Conversation UI.
- **AC3 requires new mobile dependencies not currently in `docs/AI/12_TECH_STACK.md` — get explicit user sign-off before starting `frontend` work:** `google_maps_flutter` (map-pin selection; needs a Google Maps API key + billing-enabled Cloud project — external prerequisite, not needed for automated tests), `geolocator` (device current-location + permissions), `geocoding` (reverse-geocode a pin/current-location into address fields — no API key needed, uses native OS geocoders). No new backend/Python dependency is needed — reverse geocoding is client-side only.
- The location-picker UI (full-screen map with a fixed center pin, "Use current location," "Confirm this location") should be built as a generic, reusable shared widget (`mobile/lib/shared/widgets/location_picker/`), not baked into the Customer feature module — the Provider domain's future S-18a/b (business/freelancer location entry, not this story) will need the identical interaction later. Do not touch the Provider domain in this story.
- One shared `AddressFormScreen` (mode: add/edit, optional `skippable` flag) backs all three entry points: S-05 (first-address prompt, skippable), S-12 (Saved Addresses add/edit, not skippable), and the AC5 re-prompt (not skippable). `latitude`/`longitude` are never a raw numeric text input — Save stays disabled until the user has set a pin via the map picker or current-location path at least once (manual entry covers only the text address fields, per AC3's own wording).
- AC7 UX: deleting an address uses an **Undo snackbar** (per `16_UX_GUIDELINES.md`'s own named example — this exact scenario), not a confirmation dialog. If the deleted address was the default and other addresses remain after the Undo window, show a bottom sheet to pick a new default (`07_UI_GUIDELINES.md`: bottom sheets for selection); if none remain, show an inline "no default set" state.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S03_CUS-002.md` — follow it, including all 8 numbered Architecture Decisions and the Verified Current State section.

---

## Implementation Instructions

### Backend
1. New Alembic migration (down-revision = current head — confirm via `alembic heads`): `customer.saved_addresses` per `04_DATABASE.md`, plus `idx_saved_addresses_customer_id` and the partial unique index (`customer_id`) `WHERE is_default = true AND is_active = true`. Verify upgrade and downgrade both work.
2. Add `backend/app/modules/customer/models.py`: `SavedAddress(CommonColumnsMixin, Base)`, schema `"customer"`.
3. Add `backend/app/modules/customer/repositories/saved_address_repository.py`: `list_for_customer(customer_id)`, `get_active_by_id(address_id)`, `unset_other_defaults(customer_id, *, except_address_id=None)`, `soft_delete(address)`.
4. Add `backend/app/modules/customer/services/saved_address_service.py`: `SavedAddressService(saved_address_repository, customer_service)` — `list_my_addresses`, `create_address`, `update_address` (both handling the unset-other-defaults transactional step), `delete_address` (soft-delete + ownership check via `ensure_owner_or_not_found`).
5. Add `backend/app/modules/customer/schemas.py` additions: `SavedAddressResponse`, `CreateSavedAddressRequest`, `UpdateSavedAddressRequest` (partial, `exclude_unset=True`).
6. Add `SavedAddressNotFoundError` to `backend/app/core/exceptions/exceptions.py` + `__init__.py` — 404, generic, mirrors `SessionNotFoundError`.
7. Add `backend/app/modules/customer/api.py` routes: `GET`/`POST /customers/me/addresses`, `PATCH`/`DELETE /customers/me/addresses/{address_id}`, all behind `require_role(ROLE_CUSTOMER)`.
8. Add to `backend/app/modules/customer/dependencies.py`: `get_saved_address_repository`, `get_saved_address_service`.
9. Write tests: `test_saved_address_service.py` (default-uniqueness on both create and update paths, soft-delete excludes from list, partial update semantics), `test_saved_address_endpoints.py` (full CRUD, cross-customer ownership boundary → 404 not 403, unauthenticated → 401, legacy-account get-or-create).

### Mobile
10. Add `mobile/lib/shared/widgets/location_picker/location_picker_screen.dart` — generic map-pin + current-location picker, returns coordinates + reverse-geocoded placemark. No Customer-domain imports.
11. Add `mobile/lib/features/customer/domain/models/saved_address.dart`, `data/saved_address_repository.dart` (list/create/update/delete against `/customers/me/addresses`, following `customer_repository.dart`'s error-mapping conventions), `state/saved_addresses_controller.dart`, `state/address_form_controller.dart`.
12. Add `presentation/screens/address_form_screen.dart` (shared add/edit, `mode`/`skippable` params) and `presentation/screens/saved_addresses_screen.dart` (S-12: list, default badge, edit, delete-with-Undo, AC7 bottom-sheet/inline-no-default flow).
13. Add routes: `AppRoutes.addFirstAddress`, `AppRoutes.savedAddresses`, `AppRoutes.addressForm`.
14. Edit `otp_entry_screen.dart`'s `_onVerify` and `phone_entry_screen.dart`'s `_handleOAuthResult`: navigate to `AppRoutes.addFirstAddress` instead of `AppRoutes.homePlaceholder` directly. Build `AddFirstAddressScreen` (Skip → home, no API call; Save → creates address with `is_default: true` → home).
15. Edit `profile_settings_screen.dart` (CUS-001): add the "Saved Addresses" list tile → `AppRoutes.savedAddresses` (a slot CUS-001's own Plan named but deferred).
16. Edit `home_placeholder_screen.dart`: add the "Find a Service" stub button per the AC5 gate logic above — explicitly commented as temporary.
17. Add a Google Maps API key config (`String.fromEnvironment`, mirroring `oauth_config.dart`'s pattern) and platform-config placeholders (Android manifest meta-data, iOS `AppDelegate.swift`/`Info.plist`) — blank/placeholder values are acceptable; real key is a later external prerequisite (mirrors AUTH-002's accepted gap).
18. Write tests: `address_form_screen_test.dart` (manual-entry, Save gated on a location having been picked, skip-link presence per `skippable`), `saved_addresses_screen_test.dart` (list/badge/edit/delete-Undo/AC7 both branches), a registration-flow test proving **AC9's skip-then-required-later** case end-to-end (skip at registration → home with a live session and zero addresses → tap "Find a Service" → routed to the non-skippable re-prompt, not silently let through), `fake_saved_address_repository.dart`, and a `location_picker_screen_test.dart` with all map/geolocation/geocoding calls mocked (no real platform channel invocations in tests, mirroring `oauth_sign_in_test.dart`'s fully-faked-repository pattern).

### Both
19. Confirm `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and `flutter analyze`.
20. Do not implement anything in the Plan's "Explicitly Out of Scope" section (geospatial matching infrastructure, the real Search/AI Conversation screens, Provider-domain location screens, a separate set-default endpoint, backend-side geocoding, a full country picker, any Quote/messaging/payment feature).

---

## Definition of Done

- All 9 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (CUS-002 row) are met, verified by `tester` against each one individually — see the Plan's Verification Plan table for exactly what each AC's test must prove.
- `saved_addresses` table matches `04_DATABASE.md` column-for-column, plus the new partial unique index; migration upgrade/downgrade both verified.
- Setting a new default address always and only leaves exactly one default per customer, proven by tests on both the create-time and update-time paths (AC2/AC9).
- The Add Address screen offers map-pin selection, manual text entry, and "use current location," with Save gated on a location having actually been set (AC3).
- Skipping the first-address prompt at registration never blocks reaching the home screen with a live session, and the app does not re-prompt until the new "Find a Service" stub is tapped with zero saved addresses (AC4/AC5/AC9).
- Saved Addresses screen lists all addresses, clearly badges the default, supports edit and delete (Undo snackbar), and handles deleting the default via a new-default bottom sheet or a clear "no default set" state (AC6/AC7).
- A customer's token can never view or modify another customer's addresses — 404, not 403, proven directly (AC8/AC9).
- No geospatial-matching infrastructure, real Search/AI Conversation UI, Provider-domain screens, backend geocoding, or Quote/messaging/payment functionality is introduced, even incidentally.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched. If approved: record the endpoint-shape decision as the next ADR in `09_DECISIONS.md`; update `04_DATABASE.md` (new partial unique index) and `12_TECH_STACK.md` (three new Flutter packages).
