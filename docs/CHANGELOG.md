# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

Current Version: 0.1.0 (Pre-MVP)

---

## [Unreleased]

### Added
- Role-based authorization and audit logging (Story AUTH-004): a new `require_role()` FastAPI dependency
  (`app/api/dependencies.py`), composable and layered on top of the existing `get_current_user` — a
  missing/invalid/expired token still 401s inside `get_current_user`; `require_role()` raises the new
  `InsufficientRoleError` (403) only for a validly authenticated caller whose `roles` claim doesn't intersect
  the endpoint's allowed set. New `ensure_owner_or_not_found` helper (`app/core/authorization.py`) collapses
  "resource doesn't exist" and "exists but isn't yours" into the same non-revealing 404; `SessionService`'s
  session-ownership check was refactored to use it (no behavior change). New `audit` module
  (`app/modules/audit/`) with an immutable `audit.audit_logs` table (`identity.users`-linked, no
  soft-delete/version columns) via a reversible Alembic migration, backing a new `AuditService` with four
  explicit event methods (`record_registration`, `record_login`, `record_logout`,
  `record_session_revocation`), wired into `AuthService` (registration/login on every OTP/OAuth
  authentication) and `SessionService` (logout vs. session_revocation, including bulk revoke-all) — no
  secrets, tokens, or PII appear in any audit row. New `GET /api/v1/auth/me`, protected by
  `require_role(customer, provider, admin)`, returning the caller's own id/roles/status via the existing
  `UserSummaryResponse` schema. Auth-endpoint rate limiting (Redis, 10/min, generic 429 message) from
  AUTH-001/AUTH-002 was re-confirmed intact and untouched.
- Session management and refresh-token rotation (Story AUTH-003): `identity.sessions` and
  `identity.refresh_tokens` tables (linked to `users`/`devices`) via a reversible Alembic migration. Access
  tokens are now 15 minutes (down from 30) and their JWT payload is narrowed to exactly `sub`, `exp`, `iat`,
  `jti`, `roles` — no email or phone. Refresh tokens are opaque (`secrets.token_urlsafe(32)`), only their
  SHA-256 hash is persisted. New `SessionService` (device/session/refresh-token lifecycle, separate from
  `AuthService`) backs new endpoints: `POST /api/v1/auth/refresh` (rotation with reuse-detection cascade —
  replaying an already-rotated or revoked refresh token revokes the entire session, not just that call),
  `GET /api/v1/auth/sessions` (lists the caller's active sessions with device/platform/last-seen, flags the
  current one), `DELETE /api/v1/auth/sessions/{session_id}`, and `POST /api/v1/auth/sessions/logout-all`
  (optional `keep_current`). Ownership enforcement collapses "not found" and "not yours" into one non-revealing
  404. `app/api/dependencies.py::get_current_user` is now a real implementation (replacing the BF-011
  placeholder that unconditionally raised), decoding the JWT into a `CurrentUser(id, session_id, roles)`.
- Mobile session persistence (Story AUTH-003): access/refresh token pairs are now persisted securely
  (`flutter_secure_storage`) across app restarts; a Dio `AuthInterceptor` attaches the access token to every
  request and performs one silent refresh-and-retry on a 401; the Splash screen validates a persisted session
  via a real refresh call before routing to Home. A bare "Log out" action was added to the existing Home stub.
  No new "Manage Sessions" UI screen was built this story (backend endpoints are fully built/tested regardless).
- Google and Apple sign-in (Story AUTH-002): `POST /api/v1/auth/google` and `POST /api/v1/auth/apple`, backed by a shared `IdTokenVerifier`/`JwksIdTokenVerifier` (RS256, JWKS-published keys) serving both providers through one verification code path, and `OAuthService`, which collapses any verification failure into a single generic, non-revealing error. `AuthService.authenticate_with_oauth` finds-or-creates a `User` by `(auth_provider, external_auth_subject)`, assigning the `customer` role only on creation, matching AUTH-001's mobile-OTP find-or-create pattern.
- Mobile Google/Apple sign-in buttons on the Phone Entry screen (`google_sign_in`, `sign_in_with_apple` packages), replacing AUTH-001's disabled placeholders, with graceful cancellation handling (no error shown, no stuck loading state) and localized failure copy (EN/AR).
- Identity & Access domain foundation (Story AUTH-001): `identity` Postgres schema with `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `devices`, `otp_verifications` tables via a reversible Alembic migration, native enums (`user_status`, `auth_provider`, `device_platform`, `language_code`, `otp_purpose`), and the reusable `CommonColumnsMixin` (`backend/app/database/mixins.py`) that every future domain migration will inherit.
- Idempotent role seeding (`customer`, `provider`, `admin`) via `backend/app/modules/identity/services/seed_data.py` and `backend/scripts/seed_roles.py`.
- Mobile OTP registration/login: `POST /api/v1/auth/request-otp` and `POST /api/v1/auth/verify-otp`, backed by `OtpService` (6-digit code via `secrets`, Argon2id-hashed, 5-minute expiry, 5-attempt lockout, non-revealing error responses) and `AuthService` (find-or-create `User` by phone, assigns `customer` role on creation, issues a stateless JWT access token — no session/refresh-token/device persistence in this story, deferred to AUTH-003).
- `SmsSender` interface with a stub implementation (`backend/app/modules/identity/services/sms_sender.py`) — no real SMS provider integrated yet; never logs the raw OTP code above `DEBUG`.
- `hash_otp_code`/`verify_otp_code` wrappers in `app/core/security.py`, reusing the existing Argon2id primitive.
- `InvalidOtpError`/`OtpLockedError` plain-language exceptions in `app/core/exceptions/exceptions.py`.
- Mobile app scaffolding stood up from the default Flutter counter app: Riverpod, GoRouter, Dio, `flutter_secure_storage`, `shared_preferences`, and bilingual (EN/AR) `flutter_localizations`/`intl` infrastructure, plus Material 3 theme tokens and a Feature-First `core/`/`shared/`/`features/` layout.
- Mobile auth flow screens: Splash (auto-routing), Language Selection (persisted), Phone Entry, and OTP Entry with a resend countdown matching the backend's 5-minute OTP expiry, wired to the live `request-otp`/`verify-otp` endpoints via `auth_repository.dart`.
- Backend tests under `backend/tests/modules/identity/` and mobile widget tests under `mobile/test/features/auth/` covering new-number registration, existing-number login, expired/reused-code rejection, attempt-cap lockout, and screen-level rendering/validation/countdown behavior.
- API schemas (`HealthResponse`, `DatabaseHealthResponse`) in `app/schemas/health.py` and service class (`HealthService`) in `app/services/health_service.py` to support modular, decoupled health checking (Story BF-007).
- Database health endpoint (`GET /api/v1/health/db`) to verify PostgreSQL connectivity using a lightweight `SELECT 1` query, returning `503 Service Unavailable` on connection failures (Story BF-007).
- Comprehensive unit tests in `tests/test_health.py` validating application and database health check responses, including mock database failure cases.
- URI-based API Versioning infrastructure setting `/api/v1` as the active API root (Story BF-006).
- Centralized API prefix constants defined in `app/core/constants.py`.
- Health check endpoint under Version 1 (`GET /api/v1/health`) returning a status code of 200 and a JSON body `{"status": "healthy"}`.
- Startup verification (`verify_routes`) to recursively check and validate route registration and uniqueness.
- Comprehensive routing and verification unit tests in `tests/test_routing.py`.
- Configure FastAPI lifespan API using the modern context manager in `app/core/lifespan.py` (Story BF-005).
- Application configuration validation on startup, ensuring valid environment settings and required variables.
- Standardized lifecycle logging for startup and shutdown sequences.
- Strongly typed `AppState` container in `app/core/app_state.py` registered under `app.state.services` for centralizing shared resources.
- Graceful cleanup during shutdown, ensuring database engine disposal runs in isolated try-except blocks.
- Comprehensive unit tests in `tests/test_lifespan.py` verifying registration, cycles, config validation, and exception resilience.
- Centralized configuration module in `app/core/config.py` using `pydantic-settings` (Story BF-002).
- Automatic `.env` configuration loading with support for parent directory lookups in monorepo structures.
- Strict startup validation for critical configuration fields (`DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `LOG_LEVEL`, and token expirations).
- Custom configuration validation unit tests in `tests/test_config.py`.
- Formatted, user-friendly CLI validation error reporting on startup.
- Alembic database migration infrastructure in `backend/alembic/` (Story BF-004).
- Added `alembic` and `greenlet` packages to python dependencies list.
- Dynamic connection string resolution in `env.py` using centralized application settings.
- Configured `env.py` to reuse the existing asynchronous database engine and declarative metadata.
- Chronological date-prefixed file naming format for migration version scripts.
- Initial pipeline validation migration script.
- Programmatic unit and integration tests for migrations in `tests/test_migrations.py`.
- Migration developer guidelines and instructions in `backend/README.md`.

### Changed
- Every login (mobile OTP, Google, Apple) now requires a `device: { device_platform, device_name }` field in
  the request body and returns a `refresh_token` alongside `access_token` (Story AUTH-003) — an additive-field
  but conforming-client-affecting contract change to the three endpoints AUTH-001/AUTH-002 previously shipped.
  `request-otp` (unauthenticated, no login outcome) was not changed.
- Replaced the `identity.users` table's global `uq_users_email` unique constraint with `uq_users_email_provider`, scoped to `(auth_provider, email)`, so the same email address under two different sign-in providers can each hold an independent account (Story AUTH-002). Promoted `httpx` from a dev-only to a runtime backend dependency to support JWKS fetching.
- Refactored the backend from a flat `app/{models,services,repositories,schemas}/` layout to the documented modular structure (`app/modules/<domain>/...`), starting with the identity domain (`app/modules/identity/`), to match `02_ARCHITECTURE.md`'s Feature-First/module convention and set the precedent for every future domain (Story AUTH-001, post-architect-review). No behavior change: 104 backend tests still passing, API route paths/contracts unchanged, mobile required zero changes.
- Enhanced `GET /api/v1/health` to use the service layer and return a structured `HealthResponse` schema containing service name and version (Story BF-007).
- Updated `app/api/router.py` to delegate to version routers (Story BF-006).
- Updated `app/core/config.py` default settings prefix to use the centralized prefix constants.
- Updated `.env.example` in the workspace root with the corrected `API_PREFIX`.
- Updated `app/main.py` to initialize FastAPI using the strongly typed config settings (title, version, debug mode, and api prefix).
- Updated `.env.example` in the workspace root with the required and optional config keys.

### Fixed
-


### Removed
-

---

## [0.1.0] - Engineering Platform

### Added

- Initial project structure.
- Flutter application foundation.
- FastAPI backend foundation.
- PostgreSQL database configuration.
- SQLAlchemy integration.
- Alembic migration framework.
- Environment configuration.
- Structured logging.
- Request ID and Correlation ID support.
- Ruff, Black, isort and mypy configuration.
- Pre-commit hooks.
- AI development workflow.
- Documentation framework.

### Changed

- Migrated database driver from psycopg2-binary to psycopg (v3).
- Renamed logging.py to logger.py to avoid namespace collision.

### Fixed

- Database driver compatibility with SQLAlchemy 2.x.
- Python logging namespace conflict.

### Removed

- psycopg2-binary dependency.
