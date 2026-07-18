# Plan for Story AUTH-001 — Register and Sign In with Mobile OTP

**Sprint:** 02 | **Story ID:** AUTH-001 | **Priority:** Critical | **Depends On:** BF-018 (Done)

---

## Supersession Notice

This plan **replaces** the previous version of `Plan_S02_AUTH-001.md`, which scoped AUTH-001 as a schema-only story ("Identity Domain Models & Migration" — models + migration + seed data, no endpoints, no auth logic). That version matched an outdated 9-story Sprint 2 backlog described in `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` (AUTH-001 through AUTH-009: models → OTP service → mobile auth → OAuth → JWT → sessions → RBAC → rate limiting → audit logging).

The current `docs/AI/Project_Tracker.xlsx` (source of truth for the backlog) defines a smaller, 4-story Sprint 2: **AUTH-001 through AUTH-004**, each a full vertical slice (backend + mobile + tests), not a layered breakdown. Under the current tracker, AUTH-001 itself now covers the full mobile-OTP registration/login slice — models, migration, seed data, OTP mechanism, `request-otp`/`verify-otp` endpoints, **and** the mobile splash/language/phone/OTP screens — in a single story. This plan is written against that current, authoritative scope (see the 12 acceptance criteria in the Stories sheet, reproduced below).

`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`'s Section 8 sprint table and 9-story AUTH-001..009 backlog are stale and should not be used to scope this or future Sprint 2 work; the Tracker governs. Note for later cleanup (not actioned in this pass): `docs/implementation/plans/Plan_S02_AUTH-002.md` through `Plan_S02_AUTH-009.md` also describe the old 9-story breakdown and no longer correspond 1:1 to the current tracker's AUTH-002/003/004 — they will need to be revisited when those stories are planned.

---

## Story

As a new or returning user, I want to register or sign in with my mobile number and a one-time password, so that I can securely access the app without managing a password.

This story covers the mobile OTP path of registration and login only — Google/Apple OAuth is AUTH-002. It establishes the Identity domain's foundational data model (users, roles, permissions, devices) and the OTP mechanism that will be reused later by arrival-verification and claim-listing flows. A new phone number creates a `User` and assigns the `customer` role by default; no `customer_profiles` row is created here — that is explicitly deferred to the Customer domain (CUS-001), since registration only produces an authenticated Account, not a profile.

**Scope boundary:** does NOT include Google/Apple sign-in (AUTH-002), full session/refresh-token/"stay signed in" management (AUTH-003), or role-based authorization enforcement (AUTH-004).

---

## Acceptance Criteria (authoritative — from the Tracker)

1. `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `devices`, and `otp_verifications` tables exist via Alembic migration, with partial unique constraints on email, phone number, and `external_auth_subject`.
2. `customer`, `provider`, and `admin` roles are seeded and idempotent to re-run.
3. `POST request-otp` accepts a phone number and country code, generates a 6-digit code, stores only its hash, and sets a 5-minute expiry.
4. OTP delivery is stubbed behind an `SmsSender` interface; no real provider is called in this story.
5. `POST verify-otp` rejects an incorrect code without revealing whether the phone number is registered, and increments an attempt counter capped at 5 attempts before lockout.
6. A verified OTP for an unrecognized phone number creates a new `User` with `auth_provider=mobile_otp` and assigns the `customer` role via `user_roles`.
7. A verified OTP for an existing phone number authenticates that `User` without creating a duplicate.
8. A used OTP code cannot be verified a second time (`verified_at` is set and checked).
9. Mobile screens implement splash, language selection, phone entry, and OTP entry with a visible resend countdown matching the 5-minute expiry.
10. Error states use plain-language copy (e.g., "That code didn't work — check the digits and try again") with no internal error codes or stack traces shown.
11. Automated tests cover: new-number registration, existing-number login, expired code rejection, attempt-cap lockout, and reused-code rejection.
12. No `customer_profiles` or `customer_preferences` row is created as a result of this story.

These are the acceptance criteria the tester will test against — no additions, no omissions.

---

## Architecture Decisions

1. **CommonColumnsMixin.** Add a reusable mixin (`id` UUID default `gen_random_uuid()`, `created_at`/`created_by`, `updated_at`/`updated_by`, `deleted_at`, `is_active`, `version`) in `backend/app/database/mixins.py`, alongside `Base` in `backend/app/database/base.py`. This is the **first** business-domain schema in the project (Sprint 1 shipped zero domain models, `backend/app/models/` is currently an empty package) — this mixin establishes the pattern every later domain migration must reuse, per `04_DATABASE.md` Common Columns. `role_permissions` and `user_roles` are pure join tables and use a composite PK + `created_at` only, per the documented exception — they do not inherit the mixin.
2. **Native PostgreSQL enums.** `user_status`, `auth_provider`, `device_platform`, `language_code`, `otp_purpose` — defined as native Postgres `ENUM` types via SQLAlchemy, colocated with their owning models in `backend/app/models/identity.py` (not a shared cross-domain enum file — each domain owns its enums, consistent with module isolation in `02_ARCHITECTURE.md`).
3. **Full `users` schema now, partial functional scope.** The migration creates the complete `users` table as specified in `04_DATABASE.md` (including `email`, `password_hash`, `external_auth_subject`, `email_verified_at` — columns not yet exercised by this story's logic) so that AUTH-002 (OAuth) and future admin email/password auth don't require a breaking follow-up migration. Only the `mobile_otp` path is wired to actual service logic in this story.
4. **Partial unique constraints** on `users.email`, `(phone_country_code, phone_number)`, and `(auth_provider, external_auth_subject)` (all `WHERE ... IS NOT NULL`), plus `chk_users_has_identifier` CHECK — per `04_DATABASE.md`.
5. **OTP hashing reuses existing Argon2id primitives.** `backend/app/core/security.py` already provides Argon2id `hash_password`/`verify_password` (BF-011). Add thin, intent-revealing wrappers (e.g. `hash_otp_code` / `verify_otp_code`) that delegate to the same `PasswordHash` instance rather than introducing a second hashing dependency — the 6-digit code is a short-lived secret, and Argon2id is a safe (if intentionally slow) choice for it. No plaintext code is ever persisted (`06_SECURITY.md`).
6. **`SmsSender` interface (AC4).** Define `SmsSender` as an abstract interface (e.g. `backend/app/services/sms_sender.py`) with a single `send(phone_country_code, phone_number, code) -> None` method, and one stub implementation (`ConsoleSmsSender` or `NullSmsSender`) that never calls a real provider, matching the existing DI style already used for `HealthService` in `backend/app/services/health_service.py`. The stub must **not** log the raw code at `INFO`/`WARNING`/`ERROR` level (`06_SECURITY.md` — never log secrets); if a debug aid is needed for local development, gate it explicitly behind `DEBUG`/non-production environment and label it clearly as a stub, and prefer that automated tests assert behavior via a fake/spy `SmsSender` rather than by reading logs.
7. **Unified mobile OTP flow — no client-supplied "registration vs. login" distinction.** `14_USER_FLOWS.md` Flow 1 and `15_SCREEN_INVENTORY.md` (S-03/S-04) model mobile sign-in as a single "Continue with Mobile Number" path, not separate signup/login screens — the client never needs to know in advance whether a number is new. `request-otp`/`verify-otp` therefore do not take a client-supplied `purpose` of `registration` vs. `login`; the service layer always records `otp_purpose.login` for this flow (chosen because "login" is the state ultimately achieved whether or not a `User` pre-existed) and transparently creates-or-fetches the `User` inside `verify-otp`. `registration`/`arrival_verification`/`claim_listing` purpose values remain defined on the enum for other flows (Verified Visit, claim-listing) that do need to disambiguate. **This is a plan-level assumption, not an explicit AC requirement — flag for confirmation during review if a different reading is preferred.**
8. **`verify-otp` issues a stateless JWT access token; it does NOT create a session.** AC1's required-tables list is `users, roles, permissions, role_permissions, user_roles, devices, otp_verifications` — notably **not** `sessions` or `refresh_tokens`. Per the Tracker's own story titles, AUTH-003 ("Stay signed in and manage active sessions") is where persistence-across-app-restart, refresh-token rotation, and `devices`/`sessions` population belong. AUTH-001 issues a short-lived JWT access token on successful verification (reusing the existing `create_access_token` utility from BF-011, `SECRET_KEY`/`ALGORITHM` already in `Settings`) so the app can consider itself "signed in" for the current run, but does not write a `sessions` or `refresh_tokens` row (those tables don't exist yet) and does not populate `devices`. The mobile app holds the token in memory (Riverpod state) for this story; persisting it across restarts is explicitly AUTH-003's job, not this one.
9. **No Redis-based endpoint rate limiting in this story.** `05_API_GUIDELINES.md`/`06_SECURITY.md` describe Redis-based rate limiting (e.g. 10 req/min on auth endpoints), but `REDIS_URL` is not yet present in `Settings` and no Redis client/middleware exists anywhere in the current backend (verified — no Sprint 1 story wired it up). AC5's attempt-cap lockout (5 attempts, DB-backed via `otp_verifications.attempt_count`) is fully self-contained and satisfies the story's actual acceptance criteria without Redis. Endpoint-level request throttling (SMS-bombing protection on `request-otp`) is a real gap but is out of this story's ACs — flag as a follow-up, likely candidate for a future infra/hardening story.
10. **Seed script, not a migration-embedded fixture.** Add an idempotent seed function (`backend/app/database/seed_data.py`, `seed_roles(session)`), invoked via a small script (`backend/scripts/seed_roles.py`) rather than baked into the Alembic migration — matches the existing plan's original reasoning and keeps schema changes and data changes separable.
11. **Permissions/role_permissions tables are created but not populated.** AC2 only requires the three roles to be seeded; AC1 requires the `permissions`/`role_permissions` tables to exist (they're part of the identity schema). The actual permission catalog and role→permission mappings are RBAC enforcement concerns that belong to AUTH-004 ("Access the app according to my role") — do not invent permission codes in this story.

---

## Backend — Proposed Changes

### Database mixin & base
#### [NEW] `backend/app/database/mixins.py`
`CommonColumnsMixin` — `id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at`, `is_active`, `version`, per `04_DATABASE.md` Common Columns. Every future business-domain model inherits this.

### Models
#### [NEW] `backend/app/models/identity.py`
- Enums: `UserStatus`, `AuthProvider`, `DevicePlatform`, `LanguageCode`, `OtpPurpose` (native Postgres enums per `04_DATABASE.md` Enum Types table).
- `User(Base, CommonColumnsMixin)` — all columns per `04_DATABASE.md` `identity.users` (email, email_verified_at, phone_country_code, phone_number, phone_verified_at, password_hash, auth_provider, external_auth_subject, status, preferred_language, last_login_at). Constraints: `uq_users_email`, `uq_users_phone`, `uq_users_external_auth` (all partial), `chk_users_has_identifier`. Indexes: `idx_users_email`, `idx_users_phone_number`, `idx_users_status`.
- `Role(Base, CommonColumnsMixin)` — `name` (unique), `description`.
- `Permission(Base, CommonColumnsMixin)` — `code` (unique), `description`.
- `RolePermission(Base)` — join table, composite PK (`role_id`, `permission_id`), `created_at` only.
- `UserRole(Base)` — join table, composite PK (`user_id`, `role_id`), `created_at` only.
- `Device(Base, CommonColumnsMixin)` — `user_id`, `platform`, `device_name`, `push_token`, `is_trusted`, `last_seen_at`. Index `idx_devices_user_id`. (Table created; not populated by this story's logic.)
- `OtpVerification(Base, CommonColumnsMixin)` — `user_id` (nullable), `phone_country_code`, `phone_number`, `purpose`, `code_hash`, `attempt_count` (default 0), `expires_at`, `verified_at`. Indexes `idx_otp_verifications_phone`, `idx_otp_verifications_user_id`.
- All tables live in the `identity` Postgres schema (`__table_args__ = {"schema": "identity"}` or equivalent), per `04_DATABASE.md` Schema Organization.

### Migration
#### [NEW] `backend/alembic/versions/<rev>_identity_domain.py`
- `CREATE SCHEMA IF NOT EXISTS identity`.
- Create the 5 native enums.
- Create the 7 tables above with all constraints and indexes listed in `04_DATABASE.md`.
- Verify both `upgrade()` and `downgrade()` are complete and reversible.

### Seed data
#### [NEW] `backend/app/database/seed_data.py`
`seed_roles(session: AsyncSession) -> None` — idempotent upsert of `customer`, `provider`, `admin` into `roles` (AC2).
#### [NEW] `backend/scripts/seed_roles.py`
Small CLI entry point that opens a session and calls `seed_roles`.

### Security utility extension
#### [MODIFY] `backend/app/core/security.py`
Add `hash_otp_code(code: str) -> str` / `verify_otp_code(code: str, code_hash: str) -> bool`, delegating to the existing Argon2id `password_hash` instance (Decision 5).

### SMS stub
#### [NEW] `backend/app/services/sms_sender.py`
`SmsSender` ABC + `ConsoleSmsSender` (or `NullSmsSender`) stub implementation (Decision 6, AC4).

### Repositories
#### [NEW] `backend/app/repositories/user_repository.py`
`UserRepository(BaseRepository[User])` + `get_by_phone(phone_country_code, phone_number) -> User | None`.
#### [NEW] `backend/app/repositories/role_repository.py`
`RoleRepository(BaseRepository[Role])` + `get_by_name(name) -> Role | None`.
#### [NEW] `backend/app/repositories/otp_verification_repository.py`
`OtpVerificationRepository(BaseRepository[OtpVerification])` + `get_active_for_phone(phone_country_code, phone_number, purpose) -> OtpVerification | None` (latest unverified, unexpired row).

### Services
#### [NEW] `backend/app/services/otp_service.py`
`OtpService` — `request_otp(phone_country_code, phone_number, purpose) -> None`: generates a 6-digit code (`secrets`-based, not `random`), hashes it, persists an `otp_verifications` row with `expires_at = now + 5 minutes`, and dispatches via the injected `SmsSender`. `verify_otp(phone_country_code, phone_number, purpose, code) -> OtpVerification`: loads the active OTP row; if missing/expired/already-verified/attempts-exhausted or the code doesn't match, increments `attempt_count` (capped at 5) as applicable and raises a generic, non-revealing error (AC5); on success sets `verified_at`.
#### [NEW] `backend/app/services/auth_service.py`
`AuthService` — orchestrates: calls `OtpService.verify_otp`, then finds-or-creates the `User` by phone (AC6/AC7 — no duplicate creation), assigns the `customer` role via `user_roles` only on creation (AC6), and issues a JWT access token via `create_access_token` (Decision 8). Explicitly does **not** touch `customer_profiles`/`customer_preferences` (AC12) or `devices`/`sessions`.

### Schemas
#### [NEW] `backend/app/schemas/auth.py`
`RequestOtpRequest` (phone_country_code, phone_number), `VerifyOtpRequest` (phone_country_code, phone_number, code), `AuthTokenResponse` (access_token, token_type, user), `UserSummaryResponse` (id, phone_country_code, phone_number, status, preferred_language, roles).

### API
#### [NEW] `backend/app/api/v1/endpoints/auth.py`
`POST /auth/request-otp` → `SuccessResponse[None]` or a minimal ack payload (never confirms/denies whether the number is registered). `POST /auth/verify-otp` → `SuccessResponse[AuthTokenResponse]`. Both follow the `SuccessResponse`/`ErrorResponse` envelope from `app/shared/schemas/response.py` and the DI style already used in `health.py`.
#### [MODIFY] `backend/app/api/v1/api.py`
Register `auth_router` with prefix `/auth`, tags `["Auth"]`.

### Exceptions
#### [MODIFY] `backend/app/core/exceptions/exceptions.py`
Add narrowly-scoped exceptions for invalid/expired/locked-out OTP attempts, each carrying a plain-language message matching AC10 (e.g. "That code didn't work — check the digits and try again") and mapped to `400`/`429` as appropriate — never a raw internal code or stack trace (`06_SECURITY.md`, `05_API_GUIDELINES.md`).

### Tests (AC11)
#### [NEW] `backend/tests/models/test_identity_models.py`
Constraint violations (duplicate email/phone, missing identifier), enum validity.
#### [NEW] `backend/tests/test_seed_data.py`
Seeding is idempotent (running twice does not duplicate/error).
#### [NEW] `backend/tests/services/test_otp_service.py`
Code generation/hashing, expiry rejection, attempt-cap lockout at 5, reused-code rejection (`verified_at` check).
#### [NEW] `backend/tests/services/test_auth_service.py`
New-number registration creates a `User` + `customer` role via `user_roles`, no `customer_profiles`/`customer_preferences` row (AC12); existing-number verification authenticates without duplicating the `User`.
#### [NEW] `backend/tests/api/test_auth_endpoints.py`
Integration tests for `request-otp`/`verify-otp` against the FastAPI app, covering the AC11 list end to end, and asserting `verify-otp` never reveals registration status on failure (AC5) and error responses carry only plain-language messages (AC10).

---

## Mobile — Proposed Changes

### Dependencies
#### [MODIFY] `mobile/pubspec.yaml`
Add the already-approved stack that hasn't been wired up yet (per `02_ARCHITECTURE.md`/`08_CODING_STANDARDS.md` — not a new architectural decision, just adopting what's already documented): `flutter_riverpod`, `go_router`, `dio`, `flutter_secure_storage`, `shared_preferences` (for the persisted language choice — not sensitive, so secure storage is unnecessary for it), `flutter_localizations`/`intl` (bilingual EN/AR is a locked launch requirement, `11_MVP_SCOPE.md`).

### Core / Shared
#### [NEW] `mobile/lib/core/theme/` 
Material 3 `ColorScheme.fromSeed()` using the concrete palette from `15_SCREEN_INVENTORY.md` (`#2F54EB` primary, `#14B8A6` secondary, etc.), plus centralized spacing/radius tokens (8-pt spacing, 12/8/16/24 radius scale per `07_UI_GUIDELINES.md`) — no hardcoded colors/spacing in screen code.
#### [NEW] `mobile/lib/core/routing/app_router.dart`
GoRouter configuration: `/splash`, `/language`, `/phone-entry`, `/otp-entry`, plus a minimal placeholder authenticated route (e.g. `/home-placeholder`) to land on after successful verification — full Home (S-06) is a separate future story.
#### [NEW] `mobile/lib/core/network/api_client.dart`
Dio client wrapper pointed at `API_PREFIX` (`/api/v1`), configurable base URL, matching `05_API_GUIDELINES.md`.
#### [NEW] `mobile/lib/l10n/` (`app_en.arb`, `app_ar.arb`)
Localized strings for every string used by this story's screens — no hardcoded UI strings (`07_UI_GUIDELINES.md`, `16_UX_GUIDELINES.md`).
#### [NEW] `mobile/lib/shared/widgets/`
Reusable primary button, text field, and loading-indicator widgets (per "duplicate UI components are prohibited," `07_UI_GUIDELINES.md`) used across all four screens.

### Feature: Auth
#### [NEW] `mobile/lib/features/auth/presentation/screens/splash_screen.dart` (S-01)
Brand moment, auto-routes: checks persisted language choice and any in-memory token, then routes to language selection or phone entry. No user action.
#### [NEW] `mobile/lib/features/auth/presentation/screens/language_selection_screen.dart` (S-02)
EN/AR selection, persisted via `shared_preferences`, applied before further screens render.
#### [NEW] `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart` (S-03, mobile-number path only)
Phone country code + number input, calls `request-otp`. Google/Apple options may be shown per the full `15_SCREEN_INVENTORY.md` S-03 layout but rendered disabled/"coming soon" — they are wired in AUTH-002, not this story.
#### [NEW] `mobile/lib/features/auth/presentation/screens/otp_entry_screen.dart` (S-04)
6-digit code entry (numeric keypad, live validation per `16_UX_GUIDELINES.md`), a single 5:00 resend countdown that gates the "Resend code" action and matches the OTP's actual expiry (AC9, Decision — one timer serves both purposes), calls `verify-otp`.
#### [NEW] `mobile/lib/features/auth/data/auth_repository.dart`
Wraps Dio calls to `/auth/request-otp` and `/auth/verify-otp`, maps API errors to plain-language UI copy (AC10) — never surfaces HTTP status codes or backend error identifiers directly.
#### [NEW] `mobile/lib/features/auth/state/` (Riverpod providers/controllers)
Phone entry state, OTP entry + countdown timer state, request/verify async state (loading/error/success) per `07_UI_GUIDELINES.md` loading-state and error-state rules.
#### [NEW] `mobile/lib/features/auth/domain/models/` 
`AuthUser`, `AuthToken` — thin models matching the backend response contract.

### Tests
#### [NEW] `mobile/test/features/auth/` widget tests
Splash auto-routing, language selection persists choice, phone entry validation, OTP entry countdown visibility and expiry behavior, and error-copy assertions (no raw codes/stack traces rendered) — per `02_ARCHITECTURE.md` Testing Strategy (Widget Tests).

---

## Explicitly Out of Scope (do not implement in this story)

- Google/Apple OAuth (`external_auth_subject` flows) — AUTH-002.
- `sessions`/`refresh_tokens` tables, token refresh, logout, multi-device session management, persisting the access token across app restarts — AUTH-003.
- RBAC enforcement, permission catalog, role_permissions rows — AUTH-004.
- `customer_profiles`/`customer_preferences` creation (AC12) — Customer domain, CUS-001.
- Redis-based endpoint rate limiting (Decision 9) — flagged as a follow-up, not this story's AC.
- Full Home screen (S-06) and anything past the auth flow — future Customer Core Loop story.
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **`backend`** (`backend/app/`, `backend/alembic/`, `backend/tests/`) — implement all items in the "Backend — Proposed Changes" section above, in this order: mixin/base → models → migration → seed script → security utility extension → SMS stub → repositories → services → schemas → endpoints → exception mapping → tests. Backend must land (and its `request-otp`/`verify-otp` contract be stable) before mobile wires up `auth_repository.dart` against it.
2. **`frontend`** (`mobile/lib/`, `mobile/test/`) — implement all items in the "Mobile — Proposed Changes" section, against the backend contract from step 1. Splash/language screens and theming/routing scaffolding have no backend dependency and may be scaffolded early, but the story is not complete until phone-entry/OTP-entry are wired to the real endpoints.
3. **`tester`** — verify all 12 acceptance criteria: run backend automated tests (AC11 list) plus the full backend test suite for regressions, run mobile widget tests, and manually/programmatically exercise `request-otp`/`verify-otp` for the AC5/AC8 non-revealing-error and reused-code behaviors. Report pass/fail per AC.
4. **`architect`** — review: schema conventions against `04_DATABASE.md` (this is the first domain migration — precedent-setting, needs careful scrutiny of the mixin/enum/naming pattern), OTP hashing/lockout against `06_SECURITY.md`, API contract against `05_API_GUIDELINES.md`, Clean Architecture layering (routes → services → repositories, no business logic in routes) against `02_ARCHITECTURE.md`, and mobile Feature-First structure against `08_CODING_STANDARDS.md`. Report a clean verdict or send back specifics.
5. **Orchestrator** — once `tester` and `architect` both report clean, pause and present the diff + both verdicts to the user for explicit sign-off before writing the Walkthrough or touching the changelog/tracker.

---

## Verification Plan

- `cd backend && uv run pytest -v` — full suite, including new identity/OTP/auth tests, must pass.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — migration is reversible.
- `cd backend && uv run ruff check && uv run ruff format --check` — lint/format clean.
- `cd mobile && flutter test` — new widget tests pass.
- `cd mobile && flutter analyze` — no new warnings.
- Manual/API-level check: `POST /api/v1/auth/request-otp` then `POST /api/v1/auth/verify-otp` with a fresh number creates a `User` + `customer` role; repeating with the same number does not duplicate the `User`; a wrong code increments `attempt_count` and returns a generic message; a 6th attempt is rejected as locked out; reusing an already-verified code fails.

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` — Identity & Access domain, dual-role rule
- `docs/AI/04_DATABASE.md` — Identity Domain schema (source of truth for column-level detail above)
- `docs/AI/05_API_GUIDELINES.md` — response envelope, status codes, endpoint organization
- `docs/AI/06_SECURITY.md` — OTP hashing, lockout, error-handling, logging constraints
- `docs/AI/08_CODING_STANDARDS.md` — Flutter/Python structure and naming
- `docs/AI/14_USER_FLOWS.md` — Flow 1 (Customer Registration)
- `docs/AI/15_SCREEN_INVENTORY.md` — S-01 through S-04, visual identity palette
- `docs/AI/16_UX_GUIDELINES.md` — error/empty-state copy formula, OTP form UX
- `docs/implementation/prompts/Prompt_S02_AUTH-001.md`
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-001.md` (to be created on completion)
