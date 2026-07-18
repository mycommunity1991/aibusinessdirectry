**Active Story:** Sprint 2 | AUTH-001 | Register and Sign In with Mobile OTP

**Story:**
As a new or returning user, I want to register or sign in with my mobile number and a one-time password, so that I can securely access the app without managing a password.

This story covers the mobile OTP path of registration and login only (Google/Apple OAuth is AUTH-002). It establishes the Identity domain's foundational data model (`users`, `roles`, `permissions`, `devices`) and the OTP mechanism reused later by arrival-verification and claim-listing flows. A new phone number creates a `User` and assigns the `customer` role by default; no Customer Profile row is created here — that is explicitly deferred to the Customer domain (CUS-001), since registration only produces an authenticated Account, not a profile.

**Scope boundary:** does NOT include Google/Apple sign-in, session/refresh-token management (AUTH-003), or role-based authorization enforcement (AUTH-004).

---

## Technical Context & Architecture Constraints

- This is the **first business-domain schema** in the project — `backend/app/models/` is currently an empty package and Sprint 1 shipped zero domain models. This story establishes the `CommonColumnsMixin` pattern (`id`, `created_at`/`by`, `updated_at`/`by`, `deleted_at`, `is_active`, `version`) that every later domain migration must reuse. Get this right — it is precedent-setting.
- Follow `docs/AI/04_DATABASE.md`'s Identity Domain section exactly for table/column/constraint/index detail — it is the authoritative persistence-layer spec. Do not add or omit columns.
- Follow `docs/AI/06_SECURITY.md`: OTP codes are never stored in plaintext (hash only), errors never reveal whether a phone number is registered, no stack traces/internal codes/secrets in logs or responses.
- Follow `docs/AI/05_API_GUIDELINES.md` response envelope (`SuccessResponse`/`ErrorResponse` from `app/shared/schemas/response.py`) and existing DI patterns already used in `app/api/v1/endpoints/health.py`.
- Reuse existing infrastructure — do not introduce new dependencies where an existing one already solves the problem:
  - Argon2id hashing utility in `app/core/security.py` (BF-011) for OTP code hashing too (add thin wrapper functions, don't duplicate).
  - `create_access_token`/`SECRET_KEY`/`ALGORITHM` already in `app/core/security.py`/`app/core/config.py` for issuing the post-verification JWT access token.
  - `BaseRepository`/`IBaseRepository` (BF-012) for all new repositories.
  - `SuccessResponse`/`ErrorResponse`/`ErrorDetail` (BF-010) for all new endpoint responses.
- No `sessions`/`refresh_tokens` tables in this story's migration — only `users, roles, permissions, role_permissions, user_roles, devices, otp_verifications`. Full session/device lifecycle management is AUTH-003.
- No Redis-based rate limiting — `REDIS_URL`/Redis client do not exist in the codebase yet. AC5's attempt-cap lockout is a DB-backed counter (`otp_verifications.attempt_count`), fully self-contained.
- No `customer_profiles`/`customer_preferences` rows — Customer domain, out of scope (AC12).
- No permission catalog / `role_permissions` rows — only the 3 roles (`customer`, `provider`, `admin`) are seeded; RBAC enforcement is AUTH-004.
- Mobile: this is the **first real screens** in the Flutter app beyond the default scaffold (`mobile/lib/main.dart` only). Add the already-approved-but-unused dependencies (Riverpod, GoRouter, Dio, Flutter Secure Storage, plus `shared_preferences` for the non-sensitive language choice and `flutter_localizations`/`intl` for bilingual EN/AR) and establish the Feature-First folder structure (`core/`, `shared/`, `features/auth/`) other features will follow.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S02_AUTH-001.md` — follow it.

---

## Implementation Instructions

### Backend
1. Add `CommonColumnsMixin` in `backend/app/database/mixins.py`.
2. Add `backend/app/models/identity.py`: `UserStatus`, `AuthProvider`, `DevicePlatform`, `LanguageCode`, `OtpPurpose` native enums; `User`, `Role`, `Permission`, `RolePermission`, `UserRole`, `Device`, `OtpVerification` models, all in the `identity` Postgres schema, with every constraint and index specified in `04_DATABASE.md`.
3. Generate the Alembic migration creating the `identity` schema, its enums, and its 7 tables. Verify upgrade and downgrade both work.
4. Add an idempotent role-seeding function (`backend/app/database/seed_data.py`) and a small script to invoke it (`backend/scripts/seed_roles.py`). Seed `customer`, `provider`, `admin` only.
5. Extend `backend/app/core/security.py` with `hash_otp_code`/`verify_otp_code` wrappers around the existing Argon2id primitive.
6. Add `SmsSender` interface + a stub implementation (`backend/app/services/sms_sender.py`) that never calls a real provider and never logs the raw code above `DEBUG`.
7. Add `UserRepository`, `RoleRepository`, `OtpVerificationRepository` extending `BaseRepository`.
8. Add `OtpService` (generate/hash/store/dispatch on request; validate/lockout/mark-verified on verify) and `AuthService` (find-or-create `User` by phone, assign `customer` role only on creation, issue JWT access token, never touch `customer_profiles`/`sessions`/`devices`).
9. Add request/response schemas in `backend/app/schemas/auth.py`.
10. Add `POST /auth/request-otp` and `POST /auth/verify-otp` in `backend/app/api/v1/endpoints/auth.py`; register in `backend/app/api/v1/api.py`.
11. Add plain-language exception classes for invalid/expired/locked-out OTP attempts in `backend/app/core/exceptions/exceptions.py` — copy must never expose internal codes (e.g. "That code didn't work — check the digits and try again").
12. Write automated tests covering: new-number registration, existing-number login (no duplicate `User`), expired code rejection, attempt-cap lockout at 5, reused-code rejection, constraint violations, enum validity, and seed idempotency.

### Mobile
13. Add Riverpod, GoRouter, Dio, Flutter Secure Storage, `shared_preferences`, `flutter_localizations`/`intl` to `mobile/pubspec.yaml`.
14. Set up `mobile/lib/core/theme/` (Material 3 `ColorScheme.fromSeed()` using the palette in `15_SCREEN_INVENTORY.md`), `mobile/lib/core/routing/app_router.dart` (GoRouter), `mobile/lib/core/network/api_client.dart` (Dio), and `mobile/lib/l10n/` (EN/AR ARB files).
15. Build `mobile/lib/features/auth/` (Feature-First: `presentation/screens/`, `state/`, `data/`, `domain/models/`) implementing: Splash (S-01, auto-routes), Language Selection (S-02, persisted), Phone Entry (S-03 mobile-number path — Google/Apple shown disabled, wired in AUTH-002), OTP Entry (S-04, 6-digit numeric input, 5:00 resend countdown matching OTP expiry).
16. Wire `phone-entry`/`otp-entry` to the real `request-otp`/`verify-otp` endpoints via `auth_repository.dart`; map backend errors to plain-language copy, never raw HTTP status/codes.
17. Land on a minimal placeholder authenticated route after successful verification (full Home/S-06 is a future story).
18. Write widget tests for all four screens (rendering, validation, countdown behavior, error copy).
19. Every user-facing string must be localized (no hardcoded strings), every color/spacing value must come from the shared theme/tokens (no hardcoded values).

### Both
20. Confirm both `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and `flutter analyze`.
21. Do not implement anything listed in the Plan's "Explicitly Out of Scope" section (OAuth, sessions/refresh tokens, RBAC enforcement, customer profiles, Redis rate limiting, full Home screen, any Quote/messaging/payment feature).

---

## Definition of Done

- All 12 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (AUTH-001 row) are met, verified by `tester` against each one individually.
- `identity` schema, its 5 enums, and its 7 tables exist via a working, reversible Alembic migration, matching `04_DATABASE.md` column-for-column.
- `customer`/`provider`/`admin` roles seed idempotently.
- `request-otp`/`verify-otp` endpoints work end-to-end: new number → new `User` + `customer` role; existing number → same `User`, no duplicate; wrong code → generic error + incrementing attempt counter capped at 5; used code → rejected on reuse.
- No `customer_profiles`, `customer_preferences`, `sessions`, or `refresh_tokens` row is created by this story's code paths.
- Mobile implements Splash → Language Selection → Phone Entry → OTP Entry with a working resend countdown, wired to the real backend, using only localized strings and shared design tokens.
- All error copy is plain-language, per `06_SECURITY.md`/`16_UX_GUIDELINES.md` — no stack traces, HTTP codes, or internal identifiers surfaced to the user.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- No functionality from AUTH-002/003/004, CUS-001, or `11_MVP_SCOPE.md`'s excluded list is introduced, even incidentally.
- `docs/implementation/plans/Plan_S02_AUTH-001.md` reflects the final approach (update in place if implementation deviates from the plan).
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched.
