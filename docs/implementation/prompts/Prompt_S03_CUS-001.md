**Active Story:** Sprint 3 | CUS-001 | Set Up My Customer Profile and Preferences

**Story:**
As a newly registered user, I want a customer profile created automatically with sensible defaults, and the ability to update my display name, avatar, language, and notification channel, so that the app is personalized to me without extra signup steps.

This is the first story of a brand-new domain (`customer`) — no `backend/app/modules/customer/` or mobile `features/customer/` code exists yet. It wires the Customer domain's auto-provisioning trigger into the registration flows AUTH-001/AUTH-002 already shipped: every new `Account` now also gets a `customer_profiles` row and a `customer_preferences` row, created in the same database transaction as the `User` row — never a separate, possibly-failing follow-up call.

**Scope boundary:** does NOT include saved addresses (CUS-002), the Provider-side profile equivalent (PRO-001/002), a full bottom-navigation shell, avatar file upload, or per-notification-type toggles (that's a different, not-yet-built Notification-domain table).

---

## Technical Context & Architecture Constraints

- `docs/AI/04_DATABASE.md` already fully specifies both tables column-by-column — nothing to design at the schema level, only implement: `customer.customer_profiles` (`user_id` FK unique, `display_name` NOT NULL, `avatar_url` nullable) and `customer.customer_preferences` (`customer_id` FK unique, `notification_channel` enum default `whatsapp`, `language` enum default `en`).
- **The hardest decision in this story is already made — follow it exactly, do not re-derive it:** `backend/app/modules/identity/services/auth_service.py`'s `AuthService` gains a new constructor dependency, `customer_service: CustomerService` (new `customer` module), called inline inside the existing `if is_new_user:` blocks of both `verify_otp_and_authenticate` and `authenticate_with_oauth`, using the same request-scoped `AsyncSession` (flush only, never commit — `identity/api.py`'s existing single `await db.commit()` per endpoint remains the only transaction boundary). This exactly mirrors the already-shipped `identity → audit` pattern (`AuthService` already takes `audit_service: AuditService` the same way) — do not build an ORM event listener or a domain-event bus for this; both were considered and rejected (see Plan Decision 1).
- `customer_preferences.language` must reuse the **exact same Postgres enum type** `identity.users.preferred_language` already uses (`identity.language_code`, confirmed created in the `identity` schema by the AUTH-001 migration) — via `postgresql.ENUM(..., schema="identity", create_type=False)` in the new migration. Do not create a second, duplicate `language_code` type. `notification_channel` has no prior schema presence anywhere (first consumer) — create it scoped to the `customer` schema.
- Default language derives from the `Accept-Language` HTTP request header (already a standard header per `05_API_GUIDELINES.md`), not a new field added to `identity`'s `DeviceContext`/request schemas. `identity/api.py`'s registration endpoints already receive a `Request` object — read `request.headers.get("accept-language")` and pass the raw string through `AuthService` → `CustomerService.provision_default_profile(..., accept_language_header=...)`. All parsing/fallback logic lives in `CustomerService`, not in `identity`.
- Existing Sprint 2 users in `main` have **no** `customer_profiles` row yet. Do not write a data-migration backfill script. Instead, `CustomerService.get_my_profile`/`update_my_profile` are both get-or-create: lazily provision a default-English profile for any legacy caller on first `GET`/`PATCH /customers/me`.
- Endpoints are `GET /api/v1/customers/me` and `PATCH /api/v1/customers/me` — no `{id}` path parameter, ever. The target is always `CurrentUser.id` from the validated JWT. This satisfies AC7 (ownership) structurally — there is no route shape through which another user's profile could even be requested. Gate both with `require_role(ROLE_CUSTOMER)` (`app.api.dependencies`).
- `display_name` is `NOT NULL` but no real name is available from either registration path (mobile OTP has only a phone number; `IdentityClaims` from Google/Apple carries only `subject`/`email`/`email_verified`, no name claim). Default to a plain placeholder (`"New Customer"`), immediately editable via `PATCH`.
- `avatar_url` is a plain string field in this story — not a photo-picker/upload flow. Do not add multipart file-upload handling; that's a distinct, unscoped feature.
- Mobile already has the exact mechanism AC6 needs: `mobile/lib/features/auth/state/language_controller.dart`'s `LanguageController` (`AsyncNotifier<Locale?>`), watched directly by `MaterialApp.router`'s `locale:` in `main.dart` — setting it takes effect immediately, no restart. Reuse it; do not build a second locale mechanism. The Profile screen's language toggle must call both the `PATCH` endpoint and `languageControllerProvider.setLanguage(locale)`.
- No bottom-navigation shell (Home/Activity/Profile tabs) in this story — Home/Activity don't exist yet beyond a placeholder. Route the new Profile & Settings screen directly (e.g. from a temporary entry point on the existing home placeholder), not as a nav-bar tab.
- AC9 (RTL) is the first automated RTL requirement in this codebase. `mobile/test/features/auth/test_helpers.dart`'s `pumpApp`/`pumpScreen` need a small additive `Locale? locale` parameter (default `null`, fully backward-compatible) so the new Profile screen test suite can pump with `Locale('ar')` and assert `Directionality.of(context) == TextDirection.rtl`.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S03_CUS-001.md` — follow it, including all 8 numbered Architecture Decisions and the Verified Current State section.

---

## Implementation Instructions

### Backend
1. New Alembic migration (`customer_domain`, down-revision = current head — confirm via `alembic heads`): create `customer` schema, `notification_channel` enum (`customer` schema), `customer_profiles`, `customer_preferences` tables per `04_DATABASE.md`, reusing `identity.language_code` with `create_type=False`. Verify upgrade and downgrade both work.
2. Add `backend/app/modules/customer/models.py`: `CustomerProfile`, `CustomerPreferences` (`CommonColumnsMixin`, schema `"customer"`), mirroring `identity/models.py`'s style.
3. Add `backend/app/modules/customer/repositories/customer_profile_repository.py` and `customer_preferences_repository.py`.
4. Add `backend/app/modules/customer/services/customer_service.py`: `CustomerService.provision_default_profile(user_id, *, accept_language_header)`, `get_my_profile(user_id)` (get-or-create), `update_my_profile(user_id, **fields)` (get-or-create + partial update).
5. Add `backend/app/modules/customer/schemas.py`: `CustomerProfileResponse`, `UpdateCustomerProfileRequest` (all fields optional, partial-update semantics).
6. Add `backend/app/modules/customer/api.py`: `GET`/`PATCH /customers/me`, both behind `get_current_user` + `require_role(ROLE_CUSTOMER)`. Register the router with the app.
7. Add `backend/app/modules/customer/dependencies.py`: `get_customer_profile_repository`, `get_customer_preferences_repository`, `get_customer_service`.
8. Edit `backend/app/modules/identity/services/auth_service.py`: add `customer_service: CustomerService` to `__init__`; add `accept_language_header: str | None = None` param to both `verify_otp_and_authenticate` and `authenticate_with_oauth`; call `provision_default_profile` inside each `if is_new_user:` block. Update the module docstring (remove the now-outdated "does not touch customer_profiles" note).
9. Edit `backend/app/modules/identity/api.py`: extract `Accept-Language` header on `verify-otp`/`google`/`apple`, pass through to the service call.
10. Edit `backend/app/modules/identity/dependencies.py`: `get_auth_service()` gains `Depends(get_customer_service)` (import from `app.modules.customer.dependencies`), mirroring the existing `Depends(get_audit_service)` line.
11. Write tests: `test_customer_service.py`, `test_customer_endpoints.py` (happy path, 401, cross-account isolation AC7, get-or-create). Extend `test_auth_service.py`/`test_auth_endpoints.py`: **new registration creates exactly one `customer_profiles` row + one `customer_preferences` row, asserted via a direct DB query in the same test as the `User` check** (this is the AC2/AC8 atomicity proof, not just a service-level trust check); existing/returning user does not get a second row.

### Mobile
12. Add `mobile/lib/features/customer/domain/models/customer_profile.dart`, `data/customer_repository.dart` (`getMyProfile`/`updateMyProfile` against `/customers/me`, following `auth_repository.dart`'s error-mapping conventions), `state/customer_profile_controller.dart` (Riverpod `AsyncNotifier`; `updateLanguage(Locale)` calls both the repository and `languageControllerProvider.setLanguage`).
13. Add `presentation/screens/profile_settings_screen.dart` (S-14, scoped to this story's fields only): display name field, avatar URL field, language toggle (immediate effect), notification channel picker. Do not add Saved Addresses/List Your Business/delete-account/legal-link entries.
14. Add a new route reachable from the existing home placeholder (temporary entry point, not a nav-bar tab).
15. Add an `Accept-Language`-setting interceptor to `ApiClient` (`core/network/api_client.dart`), sourced from `languageControllerProvider`'s current value.
16. Extend `mobile/test/features/auth/test_helpers.dart`'s `pumpApp`/`pumpScreen` with an optional `Locale? locale` param (backward-compatible).
17. Write `mobile/test/features/customer/profile_settings_screen_test.dart` (+ a `fake_customer_repository.dart`): renders/edits/saves each field; language toggle updates `languageControllerProvider` immediately; **RTL case** pumping with `Locale('ar')`, asserting `Directionality.of(context) == TextDirection.rtl` and no overflow/exception (AC9).

### Both
18. Confirm `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and `flutter analyze`.
19. Do not implement anything in the Plan's "Explicitly Out of Scope" section (saved addresses, Provider-side profile, bottom-nav shell, avatar upload, per-notification-type toggles, account deletion, any Quote/messaging/payment feature).

---

## Definition of Done

- All 9 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (CUS-001 row) are met, verified by `tester` against each one individually — see the Plan's Verification Plan table for exactly what each AC's test must prove.
- Registering via either AUTH-001 (mobile OTP) or AUTH-002 (Google/Apple) creates exactly one `customer_profiles` row and one `customer_preferences` row in the same transaction as the `User` row — proven by a test that queries the database directly, not one that merely trusts the service call succeeded (AC2/AC8).
- `GET`/`PATCH /customers/me` work end-to-end, gated to the caller's own data only, with no `{id}`-addressable route existing at all (AC4/AC7).
- Default `notification_channel` is `whatsapp`; default `language` derives from `Accept-Language`, falling back to English (AC3).
- Profile & Settings screen displays and edits display name, avatar (URL field), language (toggle), and notification channel; changing language takes effect immediately, no restart (AC5/AC6).
- Screen is verified in Arabic/RTL via an automated widget test (AC9).
- No `saved_addresses`, Provider-profile, bottom-nav shell, avatar-upload, or notification-category-toggle functionality is introduced, even incidentally.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched. If approved, record the cross-module provisioning-trigger decision as ADR-014 in `docs/AI/09_DECISIONS.md`.
