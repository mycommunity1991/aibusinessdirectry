# Walkthrough S02 AUTH-001

## Story: Register and Sign In with Mobile OTP

**Sprint:** 02 | **Story ID:** AUTH-001 | **Priority:** Critical | **Status:** Done

As a new or returning user, I want to register or sign in with my mobile number and a one-time password, so that I can securely access the app without managing a password.

This is the first business-domain story in the project — Sprint 1 shipped zero domain models. It establishes the Identity & Access domain's data model and OTP mechanism, and stands up the mobile app's Riverpod/GoRouter/Dio/l10n scaffolding from scratch (previously just the default Flutter counter app).

Full context, architecture decisions, and file-by-file scope: `docs/implementation/plans/Plan_S02_AUTH-001.md` (see that plan's Supersession Notice — it replaced a stale schema-only version of this plan written against an outdated 9-story Sprint 2 backlog).

---

## What was implemented

### Backend (`backend/app/modules/identity/`)

- **Database foundation** — `CommonColumnsMixin` (`id`, `created_at`/`created_by`, `updated_at`/`updated_by`, `deleted_at`, `is_active`, `version`) added to `backend/app/database/mixins.py`. This is the pattern every future domain migration will reuse.
- **Models** (`backend/app/modules/identity/models.py`) — native Postgres enums (`UserStatus`, `AuthProvider`, `DevicePlatform`, `LanguageCode`, `OtpPurpose`) and `User`, `Role`, `Permission`, `RolePermission`, `UserRole`, `Device`, `OtpVerification`, all in a new `identity` Postgres schema, matching `docs/AI/04_DATABASE.md` column-for-column, including the partial unique constraints on `email`, `(phone_country_code, phone_number)`, and `(auth_provider, external_auth_subject)`, plus the `chk_users_has_identifier` CHECK constraint.
- **Migration** — `backend/alembic/versions/2026_07_18_1224-19249fb61ae8_identity_domain.py` creates the `identity` schema, its 5 enums, and its 7 tables. Verified reversible (`upgrade` → `downgrade` → `upgrade`, live, non-mocked).
- **Seed data** — `backend/app/modules/identity/services/seed_data.py` (`seed_roles`) idempotently seeds `customer`, `provider`, `admin`; invoked via `backend/scripts/seed_roles.py`.
- **Security** — `hash_otp_code`/`verify_otp_code` added to `backend/app/core/security.py`, thin wrappers delegating to the existing Argon2id `PasswordHash` instance (BF-011) — no second hashing dependency introduced. OTP codes are never persisted in plaintext.
- **SMS stub** — `backend/app/modules/identity/services/sms_sender.py`: `SmsSender` ABC + a stub implementation that never calls a real provider and never logs the raw code above `DEBUG`.
- **Repositories** — `UserRepository`, `RoleRepository`, `OtpVerificationRepository` (`backend/app/modules/identity/repositories/`), all extending `BaseRepository`.
- **Services** — `OtpService` (generate/hash/store/dispatch on request; validate/lockout/mark-verified on verify, 6-digit code via `secrets`, 5-minute expiry, 5-attempt cap) and `AuthService` (find-or-create `User` by phone, assigns `customer` role only on creation, issues a stateless JWT access token via the existing `create_access_token` utility — no `sessions`/`refresh_tokens`/`devices` row is written, per the plan's Decision 8).
- **API** — `POST /api/v1/auth/request-otp` and `POST /api/v1/auth/verify-otp` (`backend/app/modules/identity/api.py`), registered in `backend/app/api/v1/api.py`, using the standard `SuccessResponse`/`ErrorResponse` envelope.
- **Exceptions** — `InvalidOtpError`/`OtpLockedError` added to `backend/app/core/exceptions/exceptions.py`, carrying plain-language messages ("That code didn't work — check the digits and try again") with no internal codes or stack traces.
- **Tests** — mirrored under `backend/tests/modules/identity/` (`test_identity_models.py`, `test_seed_data.py`, `test_otp_service.py`, `test_auth_service.py`, `test_auth_endpoints.py`). **104 tests passing**, `ruff check`/`ruff format --check` clean.

### Mobile (`mobile/lib/`)

- **Scaffolding stood up from nothing**: `flutter_riverpod`, `go_router`, `dio`, `flutter_secure_storage`, `shared_preferences`, `flutter_localizations`/`intl` added to `mobile/pubspec.yaml`.
- **Core** — Material 3 theme/tokens (`mobile/lib/core/theme/`), GoRouter config (`mobile/lib/core/routing/app_router.dart`, `app_routes.dart`), Dio client (`mobile/lib/core/network/api_client.dart`, `api_config.dart`), EN/AR ARB files and generated localizations (`mobile/lib/l10n/`).
- **Shared widgets** — `mobile/lib/shared/widgets/` (primary button, text field, loading indicator, error message) reused across all four screens — no duplicated UI components.
- **Feature: Auth** (`mobile/lib/features/auth/`) — Splash (S-01, auto-routes based on persisted language + in-memory token), Language Selection (S-02, persisted via `shared_preferences`), Phone Entry (S-03, mobile-number path; Google/Apple shown disabled — wired in AUTH-002), OTP Entry (S-04, 6-digit numeric entry with a visible resend countdown matching the 5-minute OTP expiry). Backed by `auth_repository.dart` (Dio calls to `request-otp`/`verify-otp`, maps API errors to plain-language copy), Riverpod state/controllers (`state/`), and thin domain models (`domain/models/`: `AuthUser`, `AuthToken`, `AuthException`, `OtpEntryArgs`).
- **Placeholder landing route** — `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart`, reached after successful verification (full Home/S-06 is a future story).
- **Tests** — `mobile/test/features/auth/` widget tests covering splash auto-routing, language persistence, phone-entry validation, and OTP-entry countdown/error-copy behavior, plus a fake repository/test helpers. **19 tests passing**, `flutter analyze` clean.

---

## Acceptance Criteria — Verification

All 12 acceptance criteria (from `Plan_S02_AUTH-001.md`, sourced from the Tracker) were independently verified by the `tester` agent with live evidence (real endpoint calls, direct SQL inspection against the `identity` schema, and a real non-mocked migration upgrade/downgrade/upgrade cycle) — all 12 passed, no scope creep found.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `devices`, `otp_verifications` tables exist via Alembic migration, with partial unique constraints on email, phone number, `external_auth_subject` | Pass |
| 2 | `customer`, `provider`, `admin` roles seeded and idempotent to re-run | Pass |
| 3 | `POST request-otp` accepts phone number + country code, generates a 6-digit code, stores only its hash, sets a 5-minute expiry | Pass |
| 4 | OTP delivery stubbed behind an `SmsSender` interface; no real provider called | Pass |
| 5 | `POST verify-otp` rejects an incorrect code without revealing registration status, increments an attempt counter capped at 5 before lockout | Pass |
| 6 | Verified OTP for an unrecognized phone number creates a new `User` with `auth_provider=mobile_otp` and assigns `customer` role via `user_roles` | Pass |
| 7 | Verified OTP for an existing phone number authenticates that `User` without creating a duplicate | Pass |
| 8 | A used OTP code cannot be verified a second time (`verified_at` set and checked) | Pass |
| 9 | Mobile screens implement splash, language selection, phone entry, OTP entry with a visible resend countdown matching the 5-minute expiry | Pass |
| 10 | Error states use plain-language copy, no internal error codes or stack traces shown | Pass |
| 11 | Automated tests cover new-number registration, existing-number login, expired code rejection, attempt-cap lockout, reused-code rejection | Pass |
| 12 | No `customer_profiles` or `customer_preferences` row created as a result of this story | Pass |

---

## Important Decisions

- **Unified mobile OTP flow, no client-supplied registration-vs-login distinction** — the service layer always records `otp_purpose.login` and transparently creates-or-fetches the `User` inside `verify-otp`, per `14_USER_FLOWS.md` Flow 1 / `15_SCREEN_INVENTORY.md` S-03/S-04's single "Continue with Mobile Number" path.
- **`verify-otp` issues a stateless JWT access token; it does not create a session.** AC1's required-table list excludes `sessions`/`refresh_tokens` — that persistence-across-restart work is explicitly AUTH-003's job. The mobile app holds the token in memory (Riverpod state) for this story only.
- **Full `users` schema landed now, partial functional scope** — `email`, `password_hash`, `external_auth_subject`, `email_verified_at` columns exist so AUTH-002 (OAuth) doesn't require a breaking follow-up migration, even though only the `mobile_otp` path is wired to service logic in this story.
- **OTP hashing reuses the existing Argon2id primitive** (BF-011) rather than introducing a second hashing dependency.
- **No Redis-based endpoint rate limiting** — `REDIS_URL`/a Redis client don't exist anywhere in the backend yet; AC5's attempt-cap lockout is fully DB-backed and self-contained. SMS-bombing protection on `request-otp` is a real gap, tracked as a follow-up (see below), not an AC of this story.
- **Module-layout refactor to `backend/app/modules/identity/`** (see next section) — done after architect review, per explicit user direction, rather than accepting the flat layout via ADR.

---

## Architect Review — Findings and Resolution

The `architect` agent returned **APPROVED WITH NOTES** (non-blocking). Each finding and its resolution:

1. **Module layout diverged from `02_ARCHITECTURE.md`.** The backend was initially implemented in a flat layout (`backend/app/{models,services,repositories,schemas}/`), inherited from Sprint 1 (which shipped zero domain models, so the divergence pre-dated AUTH-001). The architect flagged that AUTH-001, as the first real domain, would set precedent for every later domain if left flat. **Resolution: refactored.** The user was presented with the finding and explicitly chose to refactor rather than accept the flat layout via ADR. A follow-up `backend` agent pass moved the identity domain into `backend/app/modules/identity/{models.py, schemas.py, api.py, dependencies.py, repositories/, services/}`, matching `02_ARCHITECTURE.md`'s documented `backend/app/modules/<domain>/...` convention exactly. `CommonColumnsMixin` stayed in `backend/app/database/` (shared infrastructure, not identity-specific). `InvalidOtpError`/`OtpLockedError` stayed in `backend/app/core/exceptions/` (judgment call — the module convention has no `exceptions/` subfolder). Tests were mirrored to `backend/tests/modules/identity/`. Post-refactor verification: still 104 tests passing, 0 behavior change, `ruff` clean, API route paths/contracts byte-for-byte unchanged (mobile needed zero changes), confirmed via grep that no stale imports of the old flat paths (`app.models.identity`, `app.services.otp_service`, `app.services.auth_service`, `app.repositories.user_repository`, etc.) remain anywhere in the codebase.
2. **`OtpService` reached into `repository.session.commit()`** rather than taking `session` as an explicit constructor dependency, unlike `AuthService`. **Resolved** — see FU-1 below.
3. **Mobile's OTP countdown duration is a hardcoded constant** mirroring the backend's `OTP_EXPIRY_MINUTES`, not fetched from the response — could desync if the backend value changes. **Resolved** — see FU-2 below.
4. **`InvalidOtpError`/`OtpLockedError` messages are English-only**, shown verbatim to Arabic-locale users, while everything else in the app is properly localized. **Resolved** — see FU-3 below.

A fifth item surfaced during the module-layout refactor pass (not an architect finding on the original submission, but noted by the `backend` agent while doing that work): `alembic check` does not see the `identity` schema in autogenerate diffing because `include_schemas=True` is not set in `backend/alembic/env.py`. Pre-existing, not caused by AUTH-001. **Resolved** — see FU-4 below.

### Tracked Follow-ups — all resolved in a dedicated follow-up pass

The user asked for all five follow-ups to be closed out before AUTH-002 starts, rather than deferring them. Resolution:

- **FU-1 — done.** `OtpService` now takes `session: AsyncSession` as an explicit constructor dependency, matching `AuthService`'s pattern; DI wiring updated in `backend/app/modules/identity/dependencies.py`. No behavior change.
- **FU-2 — done.** Backend: `POST /auth/request-otp` now returns `RequestOtpResponse { expires_in_seconds: int }` (`backend/app/modules/identity/schemas.py`), sourced from `OTP_EXPIRY_MINUTES`. Mobile: `expires_in_seconds` is captured in `PhoneEntryState`, threaded through `OtpEntryArgs` and the route's `extra`, and used to size the OTP-entry countdown — including on `resend()`, which resizes from the *fresh* response. The old hardcoded `kOtpExpiryDuration` was renamed `kOtpExpiryFallbackDuration` and now only applies if the field is unexpectedly absent.
- **FU-3 — done.** Added `otpInvalidCodeMessage`/`otpTooManyAttemptsMessage` to `mobile/lib/l10n/app_en.arb`/`app_ar.arb`; `auth_error_copy.dart` now returns these localized strings instead of the backend's raw English `serverMessage`. `AuthException.serverMessage` was removed entirely (confirmed unused elsewhere). Side effect handled: the backend's new FU-5 rate limiter also returns 429, indistinguishable from `OtpLockedError`'s 429 by any stable machine-readable field — both were deliberately collapsed into one `AuthErrorType.tooManyAttempts` with copy that reads sensibly for either ("Too many attempts. Please wait a moment before trying again.").
- **FU-4 — done.** `include_schemas=True` added to both `context.configure()` calls in `backend/alembic/env.py`. `alembic check` now reports "No new upgrade operations detected" against a DB at head, confirmed.
- **FU-5 — done.** Redis wired end-to-end: `redis` added to `pyproject.toml`, `REDIS_URL` added to `Settings` with startup validation, a real `redis.asyncio.Redis` client replaces the `AppState.redis_client=None` placeholder in `app/core/lifespan.py` (connect on startup, dispose on shutdown). `app/core/rate_limit.py` implements a Redis `INCR`+`EXPIRE` fixed-window `RateLimitDependency` (10 req/min per `05_API_GUIDELINES.md`), applied to both `request-otp` (phone-keyed — the meaningful SMS-bombing protection) and `verify-otp` (IP-keyed, defense in depth). Initially shipped without tests; a dedicated follow-up pass added 15 tests (`backend/tests/core/test_rate_limit.py` + a `TestRateLimiting` class in `test_auth_endpoints.py`) covering under/over-limit behavior, per-key isolation, and fast expiry-reset against real Redis with cleanup — no mocks, consistent with this project's real-service testing philosophy.

None of these were acceptance criteria of AUTH-001 itself and none blocked the story being marked Done — they were closed out as an explicit, separately-scoped follow-up pass at the user's request.

---

## Testing Performed

- `cd backend && uv run pytest -v` — 104 tests passing (post-refactor); **123 passing after the follow-up pass** (108 + 15 new rate-limit tests — the +4 between 104 and 108 came from the FU-1/FU-2/FU-4/FU-5 implementation pass itself).
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — verified live, non-mocked; reversible.
- `cd backend && uv run alembic check` — clean ("No new upgrade operations detected") after FU-4.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- `cd mobile && flutter test` — 19 tests passing; **20 passing after the follow-up pass** (FU-2/FU-3 changes plus one new countdown-source test).
- `cd mobile && flutter analyze` — clean, no new warnings.
- `tester` agent: all 12 ACs independently verified with live evidence (real endpoint calls, direct SQL inspection, real migration cycle) — see table above.
- `architect` agent: APPROVED WITH NOTES (see above) — module-layout finding resolved via refactor; all four remaining findings resolved in the follow-up pass (FU-1 through FU-5).
- Post-refactor regression check: grepped for stale imports of the old flat module paths — none found.
- Rate-limit tests (FU-5) run against a real local Redis instance with per-test key cleanup — no mocks.

**Note on process:** the FU-1/FU-2(backend)/FU-4/FU-5(implementation) work was interrupted mid-session by a session/rate limit and completed by a separate continuation (per the project's new Continuity & Checkpointing convention in `.agents/agents.md`), which also committed the work (`5f723b3`). That pass left FU-5 without test coverage and did not touch the mobile side; those gaps (FU-5 tests, FU-2 mobile, FU-3) were closed in a final follow-up pass and are reflected in the numbers above.

---

## Key Files

### Backend
- `backend/app/database/mixins.py` — `CommonColumnsMixin`
- `backend/app/modules/identity/models.py`
- `backend/app/modules/identity/schemas.py`
- `backend/app/modules/identity/api.py`
- `backend/app/modules/identity/dependencies.py`
- `backend/app/modules/identity/repositories/{user_repository,role_repository,otp_verification_repository}.py`
- `backend/app/modules/identity/services/{otp_service,auth_service,sms_sender,seed_data}.py`
- `backend/app/core/security.py` — `hash_otp_code`/`verify_otp_code`
- `backend/app/core/exceptions/exceptions.py` — `InvalidOtpError`, `OtpLockedError`
- `backend/app/api/v1/api.py` — `auth_router` registration
- `backend/alembic/versions/2026_07_18_1224-19249fb61ae8_identity_domain.py`
- `backend/scripts/seed_roles.py`
- `backend/tests/modules/identity/{test_identity_models,test_seed_data,test_otp_service,test_auth_service,test_auth_endpoints}.py`

### Mobile
- `mobile/pubspec.yaml`
- `mobile/lib/core/theme/{app_colors,app_spacing,app_theme}.dart`
- `mobile/lib/core/routing/{app_router,app_routes}.dart`
- `mobile/lib/core/network/{api_client,api_config}.dart`
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}` + `mobile/lib/l10n/generated/`
- `mobile/lib/shared/widgets/{primary_button,app_text_field,loading_indicator,app_error_message}.dart`
- `mobile/lib/features/auth/presentation/screens/{splash_screen,language_selection_screen,phone_entry_screen,otp_entry_screen}.dart`
- `mobile/lib/features/auth/state/{auth_session_controller,phone_entry_controller,otp_entry_controller,language_controller}.dart`
- `mobile/lib/features/auth/data/auth_repository.dart`
- `mobile/lib/features/auth/domain/models/{auth_user,auth_token,auth_exception,otp_entry_args}.dart`
- `mobile/lib/features/auth/presentation/utils/auth_error_copy.dart`
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart`
- `mobile/test/features/auth/{splash_screen_test,language_selection_screen_test,phone_entry_screen_test,otp_entry_screen_test}.dart` + `fakes/fake_auth_repository.dart`, `test_helpers.dart`

---

## Follow-up Notes

- All five tracked follow-ups (FU-1 through FU-5) are resolved — see "Tracked Follow-ups" above. Nothing outstanding from the architect review remains open.
- `docs/implementation/plans/Plan_S02_AUTH-002.md` through `Plan_S02_AUTH-009.md` describe the superseded 9-story Sprint 2 backlog and no longer correspond 1:1 to the current 4-story tracker (AUTH-001 through AUTH-004). They must be re-planned against the current tracker when AUTH-002/003/004 are picked up — do not implement against them as-is.
- AUTH-002 ("Register and sign in with Google or Apple") is next in the Sprint 2 backlog and depends on this story's `users.external_auth_subject`/`auth_provider` columns, which already exist (Decision 3 in the Plan). It also now has a Redis client and rate-limiting dependency (FU-5) available to reuse if needed.
