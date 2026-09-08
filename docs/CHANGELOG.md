# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

Current Version: 0.1.0 (Pre-MVP)

---

## [Unreleased]

### Added
- Verification domain — submit my provider verification (Story VER-001): new `verification` Postgres schema
  with `verification.verification_records` and `verification.verification_documents` tables via a reversible
  Alembic migration. `verification_records.status` reuses `provider.verification_status`'s existing Postgres
  enum type (`create_type=False`) rather than duplicating it. New `POST
  /api/v1/providers/me/verification/documents/preview` (validate + OCR-stub + stash to a private pending slot;
  writes no DB row), `POST`/`GET /api/v1/providers/me/verification` (submit / read latest status), and `GET
  /api/v1/providers/me/verification/documents/{document_id}/file` (authenticated, ownership-checked byte
  stream). A new swappable `DocumentOcrService` Protocol — the only implementation shipped,
  `StubDocumentOcrService`, always returns empty candidate fields, honestly, pending a future real OCR pipeline
  — recorded as ADR-018. `FileStorage` (ADR-017) gains a `public_url_prefix` parameter and a `read()` method so
  verification documents are stored under a separate, never-mounted `VERIFICATION_UPLOAD_DIR` root and are never
  reachable through the existing public `/media` mount — recorded as ADR-019. Submitting creates a `pending`
  `verification_records` row; **this story never reads or writes `providers.verification_status`/
  `is_discoverable`** — discoverability and verification outcome remain entirely VER-002's responsibility, not
  yet built.
- Mobile Verification screens (Story VER-001): a new, sibling `features/verification/` module — S-19 (document
  upload, via a new `file_picker` Flutter dependency since `image_picker` cannot browse an arbitrary PDF), an
  OCR-confirm step (editable fields, copy honestly framed as "we couldn't read this automatically yet"), and
  S-20 (status view with a Resubmit action on rejection). Wired into the end of the Provider onboarding wizard
  and a new status chip on the Storefront screen. Two small shared additions —
  `shared/models/provider_type.dart` (moved from `features/provider/`) and two new minimal accessor
  repositories, `CurrentProviderTypeRepository`/`VerificationStatusSummaryRepository` — keep
  `features/provider/` and `features/verification/` from importing each other's internals directly, per
  `02_ARCHITECTURE.md`'s "features must not depend directly on each other" rule (fixing a real coupling
  violation caught during architect review).
- Provider domain — manage my provider storefront (Story PRO-002): completes the Provider aggregate via a
  reversible Alembic migration adding `provider.provider_availability`, `provider.portfolios`, and
  `provider.service_areas` (all exactly per `04_DATABASE.md`'s pre-existing spec), plus a new,
  deliberately-not-`provider_categories`-named interim table `provider.provider_category_labels`
  (`provider_id`, `label`, `is_primary`, partial unique index enforcing exactly one primary per provider) that
  replaces PRO-001's temporary `providers.category_label` column — the migration backfills every existing value
  into the new table and drops the column in the same step. New `PATCH /api/v1/providers/me` (partial update of
  basic info, category labels, and subtype-specific details; never touches `verification_status`/
  `is_discoverable`), `GET`/`POST /api/v1/providers/me/portfolio`, `DELETE
  /api/v1/providers/me/portfolio/{portfolio_id}`, `PUT /api/v1/providers/me/portfolio/order`, and `GET`/`PUT
  /api/v1/providers/me/availability` — all bare-authenticated, ownership enforced via `ensure_owner_or_not_found`
  on the genuinely `{id}`-addressable portfolio-delete route (ADR-015). **Breaking change** to the pre-launch
  `ProviderResponse` shape: `category_label: str` is replaced by `category_labels: list[CategoryLabelResponse]`
  (acceptable pre-launch, no real API consumers yet). This codebase's first file-upload capability: a
  `FileStorage` protocol with a `LocalFileStorage` implementation (local filesystem, git-ignored `UPLOAD_DIR`,
  served via a new `/media` `StaticFiles` mount), explicitly interim pending real AWS infrastructure — recorded
  as ADR-017 in `09_DECISIONS.md`. Uploads are validated for size, extension, and a magic-byte
  content sniff against the declared MIME type, and always stored under a server-generated filename, never the
  client's original filename.
- Mobile Storefront screen (Story PRO-002): a new ongoing Storefront screen (S-25) in `features/provider/` with
  four independently-saveable sections (basic info incl. category labels, subtype-specific details, portfolio
  manager, availability editor), replacing the "you already have a listing" snackbar from PRO-001 with real
  navigation. New `image_picker` Flutter dependency backs the portfolio manager's "Add Photo" action. A new
  shared `WeeklyHoursEditor` widget was factored out of PRO-001's onboarding screen to avoid duplicating the
  per-weekday hours UI, extended with a per-weekday emergency-availability toggle.
- Provider domain — create my business or freelancer listing (Story PRO-001): new `provider` Postgres schema
  with `providers` (the aggregate root, plus a flagged, temporary `category_label VARCHAR(100) NOT NULL` column
  standing in for the not-yet-built Category domain), `business_profiles`, and `freelancer_profiles` tables via
  a reversible Alembic migration; three new enums (`provider_type`, `listing_source`, `verification_status`)
  scoped to the `provider` schema. A new `RoleAssignmentService` in `identity`
  (`ensure_role_assigned(user_id, role_name)`, idempotent, flush-only) lets `provider` grant `ROLE_PROVIDER` to
  an already-authenticated caller on the same transaction as the new Provider row — the reverse direction of
  ADR-014's `identity → customer`/`identity → audit` edges, recorded as ADR-016; `AuthService`'s own
  registration-time role assignment is untouched. New `GET`/`POST /api/v1/providers/me` (a `/me` singleton per
  ADR-015), gated by bare authentication only. `POST` accepts type, basic info, and subtype-specific details in
  a single submission, generates a server-side `slug`, and unconditionally defaults
  `verification_status=pending`/`is_discoverable=false` regardless of subtype or request input. A caller may
  create at most one Provider per Account — enforced at the service layer (rejects both a same-type and a
  different-type second creation attempt, since no update endpoint for `provider_type` exists anywhere in this
  story).
- Mobile Provider onboarding wizard (Story PRO-001): a new `features/provider/` module — five screens (intro,
  choose type, basic info, business details, freelancer details) backed by an in-memory Riverpod draft
  controller, submitting exactly one `createProvider()` call at the end. Reuses CUS-002's `LocationPickerScreen`
  unmodified for both Business address and Freelancer base-location capture. This codebase's first shared
  `StepIndicator` widget (`shared/widgets/step_indicator.dart`) satisfies the multi-step-form step-indicator
  requirement. A new "List Your Business" tile on Profile & Settings checks for an existing listing first
  (`getMyProvider()`) before entering the wizard.
- Saved service-location addresses (Story CUS-002): new `customer.saved_addresses` table (label, address line,
  city, region, country code, latitude/longitude, default flag), linked to `customer_profiles`, via a
  reversible Alembic migration — this codebase's first genuine soft-delete pattern (`deleted_at`/`is_active`,
  never a hard `session.delete()`; every read path filters `is_active`). Default-address uniqueness is enforced
  transactionally in the service layer (unset every other active default before writing the new one, same
  session) with a partial unique index (`uq_saved_addresses_customer_default`, on `customer_id` WHERE
  `is_default = true AND is_active = true`) as defense-in-depth, not the sole mechanism. New `GET`/`POST
  /api/v1/customers/me/addresses` and `PATCH`/`DELETE /api/v1/customers/me/addresses/{address_id}`, gated by
  `require_role(customer)` — a client-`{id}`-addressable collection (unlike CUS-001's `/me` singleton),
  ownership enforced defensively via AUTH-004's `ensure_owner_or_not_found` (404, never 403, on both a missing
  row and a row owned by another customer). Unpaginated per ADR-012's small/single-owner-scoped carve-out.
- Mobile Saved Addresses feature (Story CUS-002): three new Flutter dependencies (`google_maps_flutter`,
  `geolocator`, `geocoding`) back a new shared, reusable `LocationPickerScreen`
  (`shared/widgets/location_picker/`, zero Customer-domain coupling, built for future Provider-domain reuse) —
  map-pin selection, manual entry, and "use current location," all reverse-geocoded into editable address
  fields. A skippable first-address prompt is now inserted into both registration success paths (mobile OTP and
  Google/Apple sign-in), after session establishment so Skip can never block registration; a temporary "Find a
  Service" button on the Home placeholder screen re-prompts (non-skippable) only when the customer has zero
  addresses and attempts to search — the real AI Conversation/Search feature doesn't exist until Sprint 7/8.
  New Saved Addresses management screen (linked from Profile & Settings) with an Undo-on-delete snackbar and,
  when deleting the current default, either a "choose a new default" bottom sheet or a clear "no default set"
  indicator.
- Customer profile and preferences (Story CUS-001): new `customer` Postgres schema with `customer_profiles`
  and `customer_preferences` tables (one-to-one with `identity.users`) via a reversible Alembic migration;
  `customer_preferences.language` reuses the existing `identity.language_code` enum (`create_type=False`)
  rather than duplicating it, and a new `notification_channel` enum (`whatsapp`/`sms`/`email`, default
  `whatsapp`) is scoped to the `customer` schema as its first consumer. Completing registration via mobile OTP
  (AUTH-001) or Google/Apple sign-in (AUTH-002) now also creates a `customer_profiles` row and a
  `customer_preferences` row in the same database transaction as the `User` row — `AuthService` gained a
  `CustomerService` constructor dependency and calls it inline inside its existing `is_new_user` branch, flush
  only, mirroring the `identity → audit` cross-module pattern already shipped in AUTH-004. Default language is
  derived from the `Accept-Language` request header (q-value aware), falling back to English on a missing or
  malformed header; `identity`'s endpoints now read and forward this header, never interpreting it themselves.
  New `GET`/`PATCH /api/v1/customers/me`, both gated by `require_role(customer)`, resolving the target
  exclusively from the caller's JWT — no `{id}` path parameter exists, so cross-account access is structurally
  impossible rather than defensively checked. Sprint-2 accounts that predate this story are backfilled lazily:
  `get_my_profile`/`update_my_profile` are get-or-create, so a legacy caller's first `GET`/`PATCH` call
  transparently provisions their row instead of 404ing.
- Mobile Profile & Settings screen (Story CUS-001): a new `features/customer/` module (editable display name,
  avatar URL, language toggle, notification-channel picker), reachable via a temporary entry point from the
  Home placeholder screen. Changing language calls the `PATCH` endpoint and updates the existing
  `LanguageController` in the same call, taking effect immediately with no app restart. A new
  `AcceptLanguageInterceptor` was added to `ApiClient`, closing a pre-existing gap where no outgoing request
  ever sent an `Accept-Language` header. First automated RTL test in this codebase (`pumpApp`/`pumpScreen`
  gained an optional `Locale?` parameter), establishing the pattern for future RTL acceptance criteria.
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
