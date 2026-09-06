# Plan for Story CUS-001 — Set Up My Customer Profile and Preferences

**Sprint:** 03 (Customer Profile & Locations) | **Epic:** ML3-EP01 | **Priority:** High | **Depends On:** AUTH-004 (complete, merged to `main`)

---

## Story

As a newly registered user, I want a customer profile created automatically with sensible defaults, and the ability to update my display name, avatar, language, and notification channel, so that the app is personalized to me without extra signup steps.

This is the first story of Sprint 3 and the first story of a genuinely new domain (`customer`) — no `backend/app/modules/customer/` or mobile `features/customer/` code exists yet. It wires the Customer domain's auto-provisioning into the registration flows AUTH-001/AUTH-002 already shipped: every new `Account` now also gets a `customer_profiles` row and a `customer_preferences` row, in the same database transaction as the `User` row.

**Scope boundary:** does not include saved addresses (CUS-002) or the Provider-side profile equivalent (PRO-001/002). Does not include a full 3-tab bottom-navigation shell (Home/Activity/Profile) — see Decision 7. Does not include account deletion, avatar file upload, or notification-category toggles (`notification.notification_preferences` — a separate, not-yet-built domain table) — see Decision 6.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`)

1. `customer_profiles` and `customer_preferences` tables exist via migration, one-to-one with `users`.
2. Completing registration via AUTH-001 or AUTH-002 creates a `customer_profiles` row and a `customer_preferences` row in the same database transaction as the `User` creation — never as a separate, possibly-failing follow-up call.
3. Default notification channel is WhatsApp; default language is derived from device locale, falling back to English.
4. `GET`/`PATCH` endpoints allow reading and updating display name, avatar, language, and notification channel/category preferences.
5. Profile & Settings screen displays and allows editing these fields, plus a visible language toggle.
6. Changing language updates `customer_preferences.language` and is reflected immediately in the UI without requiring app restart.
7. A user cannot read or update another user's customer profile (ownership enforced).
8. Automated tests confirm profile auto-creation happens atomically with registration.
9. RTL layout verified for the Profile & Settings screen in Arabic.

---

## Verified Current State (read directly from code, not assumed)

- `docs/AI/04_DATABASE.md` already fully specifies `customer.customer_profiles` (`user_id` FK unique, `display_name` NOT NULL, `avatar_url`) and `customer.customer_preferences` (`customer_id` FK unique, `notification_channel` enum default `whatsapp`, `language` enum default `en`) — nothing to design at the schema level, only to implement.
- `backend/app/modules/identity/services/auth_service.py`'s `verify_otp_and_authenticate` (AUTH-001) and `authenticate_with_oauth` (AUTH-002) both already carry an explicit `is_new_user` branch that assigns the `customer` role — this is the exact insertion point for the new provisioning call. The file's own module docstring already says: *"Deliberately does not touch `customer_profiles`/`customer_preferences` (AC12 — Customer domain, CUS-001)."*
- Transaction boundary is confirmed: `backend/app/modules/identity/api.py` calls `await db.commit()` exactly once per endpoint, after the service call returns (e.g. line 263 for `verify-otp`, line 313 for `google`/`apple`). `backend/app/repositories/base_repository.py` explicitly forbids repositories from calling `commit()` themselves. So anything added to the same `AsyncSession` before that one `db.commit()` — via `flush()`, never `commit()` — is atomic with the `User` row by construction.
- **Precedent for the cross-module call already exists in this codebase**: `AuthService` already takes `audit_service: AuditService` (a different module's service) as a constructor dependency and calls it inline, and `audit_service.py`'s own docstring states the rule this follows: *"`identity`'s services depend on this service class, never on `AuditLogRepository` directly, per `02_ARCHITECTURE.md`'s 'modules communicate through services only' rule."* `AuditService`/`AuditLogRepository` never import anything from `identity` (they take a plain `user_id: uuid.UUID`, not a `User` object) — a one-directional dependency, `identity → audit`, with zero cycle risk. This is the model to reuse for `identity → customer` (Decision 1 below).
- `backend/app/database/mixins.py`'s `CommonColumnsMixin` already hardcodes `created_by`/`updated_by` as `ForeignKey("identity.users.id")` on every business table across every domain — confirms cross-schema FK-by-string (no Python model import needed) is the established, already-precedented pattern for `customer_profiles.user_id`.
- `backend/app/modules/identity/models.py`'s `language_code_enum` is a **native Postgres enum already created in the `identity` schema** (`postgresql.ENUM("en", "ar", name="language_code", schema="identity")`, confirmed directly in `backend/alembic/versions/2026_07_18_1224-19249fb61ae8_identity_domain.py`). `customer_preferences.language` must reuse this exact type, not create a duplicate — see Decision 2.
- `backend/app/core/authorization.py`'s `ensure_owner_or_not_found()` (built for AUTH-004) is a generic, reusable ownership-check helper — available for reuse here, though (see Decision 5) this story's endpoint shape makes it structurally unnecessary.
- Mobile already has a working, immediate-effect locale mechanism: `mobile/lib/features/auth/state/language_controller.dart`'s `LanguageController` (`AsyncNotifier<Locale?>`), watched directly by `MaterialApp.router`'s `locale:` in `main.dart`. Setting it calls `setState` synchronously with no restart — this is the exact mechanism AC6 needs; it does not need to be rebuilt, only reused/extended.
- No domain-event/message-bus infrastructure exists anywhere in the backend (verified: no publisher/subscriber code under any `modules/*/events/` path, despite `02_ARCHITECTURE.md`'s per-module folder layout listing an `events/` directory as a placeholder). Confirms Decision 1's rejection of an event-based trigger is not a hypothetical — there is nothing to plug into today.
- Mobile has no bottom-navigation shell yet — only a `home_placeholder_screen.dart` stub exists (`features/home/`). `15_SCREEN_INVENTORY.md`'s 3-tab IA (Home/Activity/Profile) needs Home and Activity to exist as real screens to make a shared shell meaningful — see Decision 7.
- `IdentityClaims` (Google/Apple, `id_token_verifier.py`) carries only `subject`/`email`/`email_verified` — no name claim is parsed. Combined with the mobile-OTP path having no name at all, **no real display name is available at registration from either path** — see Decision 6 (default value).
- `mobile/test/features/auth/test_helpers.dart`'s `pumpApp`/`pumpScreen` have no `locale` parameter today — AC9 is the first RTL-specific test requirement in this codebase; the helper needs a small, additive extension (Decision 8).

---

## Architecture Decisions

### Decision 1 — Cross-module provisioning trigger (the hard one)

**Chosen: direct service-to-service call**, mirroring the already-shipped `identity → audit` pattern exactly. `AuthService` gains a new constructor dependency, `customer_service: CustomerService` (from the new `customer` module), and calls `await self.customer_service.provision_default_profile(user_id=user.id, accept_language_header=accept_language_header)` inside the existing `if is_new_user:` block, in both `verify_otp_and_authenticate` and `authenticate_with_oauth`, using the same request-scoped `AsyncSession` (flush only, never commit — the endpoint's single `await db.commit()` remains the only transaction boundary). Wired in `identity/dependencies.py`'s `get_auth_service()` via `Depends(get_customer_service)`, exactly like `Depends(get_audit_service)` is wired today.

**Dependency direction, resolved explicitly:** this creates one Python import edge, `identity → customer` (a service depending on another module's service). This is not a new architectural pattern — it is the identical shape identity already has with `audit`. It is not a cycle: `customer`'s models/repositories/services need **zero** imports from `identity`'s services or repositories (only a plain FK-by-string to `identity.users.id`, per the `CommonColumnsMixin` precedent, and a reuse of `identity.models.LanguageCode` — a pure value enum, not a service or ORM-mapped class, see Decision 2). Two independent one-directional edges (`identity → customer` for the trigger; `customer → identity` for the FK/enum) do not form a cycle since they involve different files and different kinds of objects (service class vs. plain enum/string).

Alternatives considered and rejected:
- **SQLAlchemy `after_insert` ORM event listener** registered by `customer` on `identity.User`: rejected because (a) the language default needs the `Accept-Language` header, which is HTTP-request context invisible to a low-level ORM mapper event; (b) it makes the trigger implicit and untraceable from `AuthService` itself, violating this project's "prefer explicit code over implicit behavior" rule (`app/.agents/agents.md`); (c) it still requires `customer` to import `identity`'s mapped `User` class at import time — trading one coupling for a worse, "spooky action at a distance" one, for no atomicity benefit over Option A.
- **Domain event** (`CustomerRegistered`, already named in `03_DOMAIN_MODEL.md`'s Domain Events list) via an in-process event bus: rejected because no event-bus infrastructure exists in this codebase today (confirmed above), building one solely for this single call site is exactly the kind of premature abstraction `08_CODING_STANDARDS.md`/`agents.md` warn against, and a synchronous, same-transaction event handler would be functionally identical to Option A with an extra indirection layer and no isolation benefit. Revisit if a second, unrelated module later needs to react to the same registration event.

This should be recorded as an ADR (next available: **ADR-014**) once the user signs off on the story, per the tech-lead's standing responsibility to record approved architectural decisions in `09_DECISIONS.md`.

### Decision 2 — Reusing the `language_code` Postgres enum across schemas

`customer_preferences.language` reuses the exact `identity.language_code` Postgres type already created by the identity-domain migration — not a duplicate type. The new customer-domain migration must declare the column as `postgresql.ENUM("en", "ar", name="language_code", schema="identity", create_type=False)` (the `create_type=False` is critical — omitting it would attempt a duplicate `CREATE TYPE` and fail). The SQLAlchemy model in `customer/models.py` imports `identity.models.LanguageCode` (the plain `StrEnum`, not any service/repository/mapped-class) for the same reason — one canonical Python representation of one canonical Postgres type, consistent with `04_DATABASE.md`'s enum table listing `language_code` once, and with the "never create duplicate models" rule.

`notification_channel` has no prior schema presence anywhere (the Notification domain itself hasn't been built yet — it's Stage 4 of `11_MVP_SCOPE.md`'s build sequence). This migration is the first to need it; it is created scoped to the `customer` schema (`schema="customer"`) since `customer_preferences` is its first consumer. **Flag for the future Notification-domain story:** when `notification.notification_preferences.channel` is built, it must reference this same type via `create_type=False, schema="customer"` rather than creating a second, duplicate enum — worth a one-line note added to `04_DATABASE.md`'s Enum Types table at that time. Not a blocker for CUS-001, just a forward-compatibility note.

### Decision 3 — Default language source: `Accept-Language` header, not a new request field

AC3 requires the default language to derive from "device locale." Rather than adding a new field to `identity`'s `DeviceContext`/`VerifyOtpRequest`/`OAuthSignInRequest` schemas (an AUTH-owned contract, and a mobile contract change to already-shipped AUTH-001/002 request bodies), this story uses the standard `Accept-Language` HTTP header — already listed as a standard header in `05_API_GUIDELINES.md`. `identity/api.py`'s registration endpoints already receive a `Request` object (used today for `_client_context`); they read `request.headers.get("accept-language")` and pass the raw string down through `AuthService` to `CustomerService.provision_default_profile(..., accept_language_header=raw_string)`. All parsing/fallback logic (e.g. `"ar-AE,ar;q=0.9,en;q=0.8"` → `LanguageCode.AR`; missing/anything else → `LanguageCode.EN`) lives inside `CustomerService`, since interpreting this as a *customer preference default* is a Customer-domain business rule, not an Identity-domain concern — `identity` stays a pure pass-through of a raw string it never interprets.

Mobile side: `ApiClient` (`core/network/api_client.dart`) gets an interceptor that sets `Accept-Language` on every outgoing request from the current value of `languageControllerProvider` (falling back to no header — i.e. device default — if the user hasn't made an explicit S-02 choice yet). This is a small, general-purpose addition (every future endpoint benefits, not just registration) rather than a one-off header set inside `AuthRepository` alone.

### Decision 4 — Legacy-user backfill via lazy get-or-create, not a data migration

Sprint 2 already shipped and merged — real `identity.users` rows already exist in `main` with **no** `customer_profiles` row (AC2's atomic-creation path only covers users registering *after* this story ships). Rather than writing a one-off DML backfill script inside the Alembic migration (mixing schema DDL with data migration, and riskier to test/roll back), `CustomerService.get_my_profile(user_id)` and `update_my_profile(user_id, ...)` are both **get-or-create**: if no `customer_profiles` row exists for the caller, one is lazily created with the same defaults `provision_default_profile` would have used (no `Accept-Language` signal available at this point — falls back straight to English, which is an acceptable, documented edge case for pre-CUS-001 accounts only). This makes `GET /customers/me` never return a 404 for an authenticated, `customer`-role caller — the endpoint is unconditionally self-healing.

### Decision 5 — Endpoint shape: `/customers/me`, no `{id}` path parameter, ever

`GET /api/v1/customers/me` and `PATCH /api/v1/customers/me` — both resolve the target profile exclusively from `CurrentUser.id` (the validated JWT `sub`), never from a client-supplied identifier. This satisfies AC7 structurally rather than defensively: there is no route shape through which a caller could even attempt to address another user's profile, so there is nothing for `ensure_owner_or_not_found()` to guard against at the API layer. (`ensure_owner_or_not_found` remains available and is the right tool if a future story ever needs an `{id}`-addressable customer lookup, e.g. an admin view — not needed here.) Every repository method in this story takes `user_id`/`customer_id` derived only from the authenticated caller, never from request input.

Both endpoints require `require_role(ROLE_CUSTOMER)` — every registered account already receives the `customer` role at registration (existing AUTH-001/002 behavior), so this is a correctness-preserving gate, not a new restriction in practice.

Response/request shape is a single combined resource (not separate `/profile` and `/preferences` resources), since `customer_profiles` and `customer_preferences` are always 1:1, always created together, and always edited together on one screen (S-14):

```
GET /api/v1/customers/me → CustomerProfileResponse { id, display_name, avatar_url, language, notification_channel }
PATCH /api/v1/customers/me ← UpdateCustomerProfileRequest { display_name?, avatar_url?, language?, notification_channel? } (partial update, only fields present in the payload are changed — Pydantic v2 `exclude_unset=True`)
```

**Interpreting AC4's "notification channel/category preferences":** `04_DATABASE.md`'s pre-specified `customer_preferences` table has exactly two fields beyond `language`: `notification_channel` (an enum of *categories of channel* — WhatsApp/SMS/Email). There is no per-notification-type toggle (`leads_enabled`/`verification_enabled`/`outcome_prompts_enabled`) in the Customer domain — those columns belong to `notification.notification_preferences`, a different, not-yet-built domain table (Notification domain, Stage 4 of `11_MVP_SCOPE.md`). This story implements exactly what `04_DATABASE.md` specifies for `customer_preferences`: the channel *category* (WhatsApp/SMS/Email), not separate per-category toggles. Flagging this reading explicitly so the tester/architect verify against the schema that is actually authoritative here, not a broader reading of the AC's wording.

### Decision 6 — Sensible defaults for fields with no real signal at registration

- `notification_channel` defaults to `whatsapp` — directly per AC3, no ambiguity.
- `language` defaults per Decision 3.
- `display_name` is `NOT NULL` in the schema, but neither the mobile-OTP path (phone number only) nor the current OAuth claims model (`subject`/`email`/`email_verified`, no name) provides a real name. Default: a plain, obviously-placeholder value (`"New Customer"`), immediately editable via `PATCH`. This is a deliberate, low-risk simplification — not a blocker requiring sign-off, but flagged so the tester doesn't mistake it for a bug.
- `avatar_url` defaults to `NULL`. This story treats "avatar" as a plain string URL field (settable/clearable via `PATCH`), **not** a photo-picker/file-upload flow — actual image upload is a distinct feature (multipart handling, `06_SECURITY.md`'s file-upload validation requirements, storage) that isn't implied by AC4's wording and isn't part of this story's scope. Flagging this interpretation explicitly, since it does shape what "editing avatar" means on the Profile & Settings screen (a URL text field, not an image picker) — reasonable, but worth the user's awareness.

### Decision 7 — No bottom-navigation shell in this story

`15_SCREEN_INVENTORY.md`'s Customer-mode IA (Home / Activity / Profile, 3 tabs) needs real Home and Activity screens to make a shared shell meaningful — neither exists yet (`home_placeholder_screen.dart` is a stub). Building a 3-tab shell for one real tab would be premature scaffolding for screens that don't exist. This story adds the Profile & Settings screen (S-14) as a directly-routable screen (`AppRoutes.profileSettings` or similar), reachable via a temporary entry point from the existing home placeholder (e.g. an app-bar icon button) — not wired into a persistent bottom-nav bar. The real 3-tab shell should be built in whichever future story delivers a real Home screen, and should then absorb this screen as its "Profile" tab without needing to be rebuilt. Flagging this as a scope call, not asking for sign-off — it avoids scope creep into Home/Activity, which are separate, not-yet-planned stories.

### Decision 8 — RTL test infrastructure (first-of-its-kind for this codebase)

AC9 is the first acceptance criterion in this project explicitly requiring an automated RTL check. `mobile/test/features/auth/test_helpers.dart`'s `pumpApp`/`pumpScreen` get a small additive change: an optional `Locale? locale` parameter (defaulting to `null`, preserving all existing call sites unchanged), passed through to `MaterialApp.router`'s `locale:`. The new Profile & Settings widget test suite includes a case that pumps with `locale: const Locale('ar')` and asserts `Directionality.of(context) == TextDirection.rtl` plus no layout-overflow exceptions (`tester.takeException()` is null). This establishes the reusable pattern for every future story's RTL acceptance criterion, not just this one.

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration, `customer_domain` (down-revision = current head — confirm via `alembic heads` at implementation time; last known head is `d81be77c601d`, the AUTH-004 audit-domain migration). Creates the `customer` Postgres schema, the `notification_channel` enum (`whatsapp`/`sms`/`email`, scoped to `customer` schema per Decision 2), `customer_profiles` (`user_id` FK → `identity.users.id` unique, `display_name` VARCHAR(150) NOT NULL, `avatar_url` VARCHAR(500) nullable, + Common Columns), and `customer_preferences` (`customer_id` FK → `customer_profiles.id` unique, `notification_channel` enum default `whatsapp`, `language` enum — reusing `identity.language_code` via `create_type=False` per Decision 2, default `en`, + Common Columns). Mirror the exact style of `2026_09_06_0900-d81be77c601d_audit_domain.py` (explicit `sa.ForeignKeyConstraint`, explicit indexes, working `downgrade()`).
2. Add `idx_customer_profiles_user_id` (covered by the unique constraint, but confirm), `idx_customer_preferences_customer_id` per `04_DATABASE.md`.

### Models (`backend/app/modules/customer/models.py`)
3. `CustomerProfile(CommonColumnsMixin, Base)` and `CustomerPreferences(CommonColumnsMixin, Base)`, schema `"customer"`, mirroring `identity/models.py`'s style exactly (FK-by-string, `_pg_enum`-equivalent handling with `create_type=False` for the reused `language_code`).

### Repositories
4. `backend/app/modules/customer/repositories/customer_profile_repository.py`: `CustomerProfileRepository(BaseRepository[CustomerProfile])` with `get_by_user_id(user_id) -> CustomerProfile | None`.
5. `backend/app/modules/customer/repositories/customer_preferences_repository.py`: `CustomerPreferencesRepository(BaseRepository[CustomerPreferences])` with `get_by_customer_id(customer_id) -> CustomerPreferences | None`.

### Services
6. `backend/app/modules/customer/services/customer_service.py`: `CustomerService` with:
   - `provision_default_profile(user_id, *, accept_language_header) -> tuple[CustomerProfile, CustomerPreferences]` — creates both rows with defaults per Decision 6, flush only (Decision 1). Called by `identity.AuthService` on `is_new_user`.
   - `get_my_profile(user_id) -> tuple[CustomerProfile, CustomerPreferences]` — get-or-create (Decision 4).
   - `update_my_profile(user_id, *, display_name=UNSET, avatar_url=UNSET, language=UNSET, notification_channel=UNSET) -> tuple[CustomerProfile, CustomerPreferences]` — get-or-create then partial update, flush, no commit (API layer commits).
   - Private `_resolve_default_language(accept_language_header) -> LanguageCode` per Decision 3.

### Schemas (`backend/app/modules/customer/schemas.py`)
7. `CustomerProfileResponse { id, display_name, avatar_url, language, notification_channel }`.
8. `UpdateCustomerProfileRequest { display_name: str | None = None, avatar_url: str | None = None, language: LanguageCode | None = None, notification_channel: NotificationChannel | None = None }` with field validators (`display_name` max 150, `avatar_url` max 500).

### API (`backend/app/modules/customer/api.py`)
9. `GET /customers/me` and `PATCH /customers/me`, both behind `get_current_user` + `require_role(ROLE_CUSTOMER)`, both returning `SuccessResponse[CustomerProfileResponse]`. Register the router in the app's main API router alongside `identity`'s.
10. `backend/app/modules/customer/dependencies.py`: `get_customer_profile_repository`, `get_customer_preferences_repository`, `get_customer_service` (mirrors `identity/dependencies.py` exactly).

### Identity module edits
11. `AuthService.__init__` gains `customer_service: CustomerService`. Both `verify_otp_and_authenticate` and `authenticate_with_oauth` gain an `accept_language_header: str | None = None` parameter and call `await self.customer_service.provision_default_profile(user_id=user.id, accept_language_header=accept_language_header)` inside their existing `if is_new_user:` blocks.
12. `identity/api.py`'s `verify-otp`/`google`/`apple` endpoints read `request.headers.get("accept-language")` and pass it through.
13. `identity/dependencies.py`'s `get_auth_service()` gains `Depends(get_customer_service)`, imported from `app.modules.customer.dependencies` (mirrors the existing `Depends(get_audit_service)` line exactly).
14. Update `auth_service.py`'s module docstring to remove the now-outdated "deliberately does not touch customer_profiles" note.

### Tests
15. `backend/tests/modules/customer/test_customer_service.py`: `provision_default_profile` creates both rows with correct defaults (WhatsApp, English-fallback, Arabic-from-header); `get_my_profile` get-or-create for a legacy user; `update_my_profile` partial-update semantics (only provided fields change).
16. `backend/tests/modules/customer/test_customer_endpoints.py`: `GET`/`PATCH /customers/me` happy path; unauthenticated → 401; a second user's token never sees/affects the first user's data (AC7); RTL/language header end-to-end.
17. Extend `backend/tests/modules/identity/test_auth_service.py` and `test_auth_endpoints.py`: **new registration via either path creates exactly one `customer_profiles` row and one `customer_preferences` row, queried directly against the DB in the same test, in the same assertion block as the `User` row check** (AC2/AC8 — this is the one test that must prove atomicity, not just presence). Also assert a returning/existing user does **not** get a second profile row.

---

## Mobile — Proposed Changes

### Feature: Customer (new)
18. `mobile/lib/features/customer/domain/models/customer_profile.dart`: plain model mirroring `CustomerProfileResponse`.
19. `mobile/lib/features/customer/data/customer_repository.dart`: `getMyProfile()`, `updateMyProfile({...})` against `/customers/me`, following `auth_repository.dart`'s error-mapping conventions (never leak raw Dio/status codes to the UI).
20. `mobile/lib/features/customer/state/customer_profile_controller.dart`: Riverpod `AsyncNotifier` wrapping the repository; `updateLanguage(Locale)` calls the repository **and** `ref.read(languageControllerProvider.notifier).setLanguage(locale)` together, so the PATCH and the immediate in-app effect (AC6) happen from one call site.
21. `mobile/lib/features/customer/presentation/screens/profile_settings_screen.dart` (S-14, scoped to this story only): display name (editable text field), avatar (editable URL text field per Decision 6), language toggle (EN/AR, immediate effect per AC6), notification channel picker (WhatsApp/SMS/Email). Do **not** add Saved Addresses, "List Your Business," delete-account, or legal-link entries yet — those belong to their own not-yet-built stories (CUS-002, PRO-001, and a future account-deletion story); adding non-functional placeholders for them would violate the "no dead-end/no incidental scope" rules.
22. New route (e.g. `AppRoutes.profileSettings`) reachable from the existing `home_placeholder_screen.dart` via a temporary entry point (Decision 7) — not a bottom-nav tab.

### Core
23. `ApiClient` interceptor: attach `Accept-Language` from `languageControllerProvider`'s current value to every outgoing request (Decision 3).
24. `test_helpers.dart`: add optional `Locale? locale` param to `pumpApp`/`pumpScreen` (Decision 8), fully backward-compatible with existing call sites.

### Tests
25. `mobile/test/features/customer/profile_settings_screen_test.dart`: renders current values; editing + saving each field calls the repository with the right payload; language toggle updates `languageControllerProvider` immediately (assert without a widget rebuild-from-scratch); **RTL case** using `locale: const Locale('ar')` per Decision 8 (AC9).
26. `mobile/test/features/customer/fakes/fake_customer_repository.dart` mirroring `fake_auth_repository.dart`'s pattern.

---

## Explicitly Out of Scope (do not implement in this story)

- Saved addresses / `saved_addresses` table — CUS-002.
- Provider-side profile equivalent — PRO-001/002.
- A full bottom-navigation shell (Home/Activity/Profile tabs) — Decision 7.
- Avatar file upload / photo picker — Decision 6; `avatar_url` is a plain string field only.
- Per-notification-type toggles (leads/verification/outcome-prompt) — belongs to the future Notification domain (`notification.notification_preferences`), not `customer_preferences` — Decision 5.
- Account deletion, legal links, "List Your Business" CTA on the Profile screen — future stories.
- Any change to `03_DOMAIN_MODEL.md`/`04_DATABASE.md` schema beyond what they already specify — this story implements the pre-specified schema, it does not redesign it.
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **backend** — Migration, models, repositories, `CustomerService`, schemas, API, dependencies, the `identity` module edits (items 1–17 above). ACs to satisfy: 1, 2, 3, 4, 7, 8.
2. **frontend** — Profile & Settings screen, customer repository/state, `ApiClient` header interceptor, `LanguageController` integration, RTL test-helper extension (items 18–26 above), once the backend endpoints exist (or in parallel against a fake repository, then wired to the real one). ACs to satisfy: 5, 6, 9 (and consumes 3/4/7 via the real API).
3. **tester** — Verify all 9 ACs individually, with particular attention to AC2/AC8 (the atomicity test must query the DB directly in the same test as the `User`-creation check, not just call the service and trust it) and AC7 (cross-account isolation) and AC9 (RTL).
4. **architect** — Review the cross-module dependency direction (Decision 1) specifically, plus the enum-reuse migration (Decision 2) and the get-or-create backfill (Decision 4).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved, record Decision 1 as ADR-014 in `09_DECISIONS.md`.

---

## Verification Plan (mapped to the 9 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade; `\d customer.customer_profiles` / `\d customer.customer_preferences` show the exact columns/constraints in `04_DATABASE.md`. |
| 2 | New integration test: register via `verify-otp` (and separately via `/google`) with a fresh phone/subject, then query `customer.customer_profiles`/`customer_preferences` directly in the same test — both rows exist, tied to the new `user_id`. |
| 3 | Unit test: `Accept-Language: ar-AE` → `language=ar`; missing/garbage header → `language=en`; `notification_channel` is always `whatsapp` on creation. |
| 4 | `GET`/`PATCH /customers/me` return `CustomerProfileResponse` with the correct current values; `PATCH` with a single field only changes that field (others unchanged). |
| 5 | Widget test: Profile & Settings screen renders display name/avatar/language toggle/notification channel picker, all editable. |
| 6 | Widget/integration test: toggling language calls `PATCH`, then asserts `languageControllerProvider`'s locale (and thus `MaterialApp`'s effective locale) changed within the same test, with no widget-tree rebuild-from-scratch/restart. |
| 7 | Integration test: user A's token against `GET`/`PATCH /customers/me` never returns/affects user B's row — since the endpoint has no `{id}` param, this is really "two different tokens always get two different, correct results," asserted directly. |
| 8 | The AC2 test above, plus an explicit "existing/returning user does not get a second profile row" test. |
| 9 | Widget test pumping the screen with `Locale('ar')`; asserts `Directionality.of(context) == TextDirection.rtl` and no overflow/exception. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md`
- `docs/AI/03_DOMAIN_MODEL.md`
- `docs/AI/04_DATABASE.md`
- `docs/AI/05_API_GUIDELINES.md`
- `docs/AI/06_SECURITY.md`
- `docs/AI/07_UI_GUIDELINES.md`
- `docs/AI/11_MVP_SCOPE.md`
- `docs/AI/15_SCREEN_INVENTORY.md`
- `docs/AI/16_UX_GUIDELINES.md`
- `docs/implementation/plans/Plan_S02_AUTH-002.md` (Decision 12 reference)
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md` (`ensure_owner_or_not_found` origin)
