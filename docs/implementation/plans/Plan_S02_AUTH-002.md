# Plan for Story AUTH-002 — Register and Sign In with Google or Apple

**Sprint:** 02 | **Story ID:** AUTH-002 | **Priority:** High | **Depends On:** AUTH-001 (Done)

---

## Supersession Notice

This plan **replaces** the previous version of `Plan_S02_AUTH-002.md`, which scoped AUTH-002 as an "OTP Verification Service" story — a layered slice of an old, superseded 9-story Sprint 2 backlog (AUTH-001 through AUTH-009: models → OTP service → mobile auth → OAuth → JWT → sessions → RBAC → rate limiting → audit logging). That backlog no longer exists.

The current `docs/AI/Project_Tracker.xlsx` (source of truth) defines a 4-story Sprint 2 — AUTH-001 through AUTH-004 — each a full vertical slice. Under that tracker, **AUTH-002 is "Register and sign in with Google or Apple"**: the OAuth counterpart to AUTH-001's mobile-OTP path, adding server-verified Google/Apple sign-in to the same `identity.users` table AUTH-001 already shipped. This plan is written against that current, authoritative scope (9 acceptance criteria, reproduced verbatim below) and against the **actual shipped code** from AUTH-001 (verified by reading it directly, not assumed from its plan — see Architecture Decision 1).

`Plan_S02_AUTH-003.md` and `Plan_S02_AUTH-004.md` still describe the old 9-story breakdown and remain stale; they must be re-planned against the current tracker when those stories are picked up, following the same process used here.

---

## Story

As a new or returning user, I want to continue with Google or Apple, so that I can access the app using an identity I already trust, without creating a new credential.

This story adds the OAuth path alongside AUTH-001's mobile OTP path — both lead to the same underlying `User` record shape. Server-side ID-token verification is mandatory; the client's assertion of identity is never trusted directly. Accounts are matched on the `(auth_provider, external_auth_subject)` pair, not on email, because social email addresses can be unverified or change.

**Scope boundary:** does not include account linking/merging across providers — a different provider with the same email produces a second, separate Account by design in this story; any future account-linking capability is out of scope here.

---

## Acceptance Criteria (authoritative — from the Tracker)

1. Sign-in screen offers Google and Apple buttons alongside the mobile-number option from AUTH-001.
2. Backend verifies the Google ID token against Google's public keys and the Apple identity token against Apple's public keys — no token is trusted without verification.
3. A new `(auth_provider, external_auth_subject)` pair creates a new User and assigns the customer role.
4. An existing `(auth_provider, external_auth_subject)` pair authenticates the existing User.
5. A different provider presenting the same email as an existing account creates a second, independent Account — it does not merge or link to the first.
6. Invalid, expired, or tampered ID tokens are rejected with a generic authentication-failure message, not a detailed validation error.
7. User cancellation mid-flow (e.g., closing the Google/Apple consent screen) returns the user to the sign-in screen without a crash or a stuck loading state.
8. Automated tests use signed test tokens or mocked provider key endpoints — no test calls the real Google or Apple endpoints.
9. Integration test explicitly verifies the different-provider-same-email case results in two distinct User rows.

These are the acceptance criteria the tester will test against — no additions, no omissions.

---

## Verified Current State (read directly from code, not assumed)

- Backend identity code lives at `backend/app/modules/identity/` (`models.py`, `schemas.py`, `api.py`, `dependencies.py`, `repositories/`, `services/`) — **not** the flat `backend/app/models/`, `app/services/`, `app/repositories/` layout the old AUTH-001 plan draft described. AUTH-001 was refactored into this module layout post-architect-review (see `Walkthrough_S02_AUTH-001.md`). This plan targets the real, current layout.
- `backend/app/modules/identity/models.py`: `User` already has `auth_provider` (`AuthProvider` enum: `google`, `apple`, `mobile_otp`, `email_password`) and `external_auth_subject` (`String(255)`, nullable) columns, with a partial unique index `uq_users_external_auth` on `(auth_provider, external_auth_subject)` `WHERE external_auth_subject IS NOT NULL`. This confirms the Tracker's dependency note — no migration is needed to add these columns.
- **However**, `User.email` also carries a *separate*, provider-agnostic partial unique index: `uq_users_email` on `email` alone, `WHERE email IS NOT NULL`. This directly conflicts with AC5 (two accounts, different providers, same email, must both be insertable) — see Architecture Decision 2, a schema change this story must make.
- `backend/app/modules/identity/services/auth_service.py`'s `verify_otp_and_authenticate` already implements the exact find-or-create-then-issue-JWT pattern this story needs for OAuth — role assignment only on creation, `last_login_at` touch on existing users, JWT via the existing `create_access_token`. AUTH-002 extends `AuthService` with a parallel method rather than duplicating this pattern.
- `backend/app/core/rate_limit.py`'s `RateLimitDependency` and `backend/app/core/redis.py`'s Redis client (added as an AUTH-001 follow-up, FU-5) are available and already wired into `app/main.py`'s lifespan — reusable here with no new infrastructure.
- `backend/pyproject.toml`: `python-jose[cryptography]` is already a dependency (used for our own JWT encode/decode) — it also supports RS256 verification against an arbitrary JWK, which is exactly what Google/Apple ID token verification needs. `httpx` is currently a **dev-only** dependency (used by `TestClient`); this story promotes it to a runtime dependency for JWKS fetching (see Decision 4) rather than introducing a new HTTP client.
- Mobile: `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart` already renders Google/Apple buttons via a `_DisabledAuthOption` widget, explicitly commented "wired in AUTH-002, not this story." This story replaces that widget with real, tappable buttons.
- `mobile/pubspec.yaml` has no OAuth-plugin dependency yet (`google_sign_in`, `sign_in_with_apple` are both absent) — see Decision 8.
- `mobile/lib/features/auth/domain/models/auth_token.dart` / `auth_exception.dart` / `state/auth_session_controller.dart` are provider-agnostic already (`AuthToken`/`AuthErrorType`/`authSessionProvider` all describe "a session," not "an OTP session") — reused as-is for the OAuth path, no duplication needed.

---

## Architecture Decisions

1. **Target the real `backend/app/modules/identity/` layout, not the flat layout an earlier draft plan assumed.** Confirmed by reading the actual files (see "Verified Current State"). No decision needed here beyond stating it — flagged because the task brief explicitly warned this could have deviated from the AUTH-001 plan, and it did.

2. **Schema change: scope `users.email` uniqueness per `auth_provider` instead of globally.** AC5 requires that a different provider presenting the same email creates a **second, independent** `User` row. The current `uq_users_email` partial unique index (`email` alone, `WHERE email IS NOT NULL`, shipped by AUTH-001) makes this impossible — a second row with the same email would fail the unique constraint regardless of provider. This was never exercised by AUTH-001's own tests because the mobile-OTP flow never populates `email`.
   **Decision:** replace `uq_users_email` with `uq_users_email_provider`, a partial unique index on `(auth_provider, email)` `WHERE email IS NOT NULL`, via a new Alembic migration. This still prevents two rows for the *same* provider claiming the same email (defensive; matching is really done via `external_auth_subject`, not email) while explicitly allowing the cross-provider duplicate AC5 requires. `email_password` (admin) accounts are unaffected in practice — that provider value is only ever used for internal admin accounts, so per-provider scoping still yields effectively-global uniqueness for them.
   **This is a change to a constraint AUTH-001 already shipped and tested — flagged prominently for explicit confirmation before backend implementation starts**, not something to implement silently. `docs/AI/04_DATABASE.md`'s `users` table constraint list will need a corresponding update once approved (out of the orchestrator's `docs/AI/` write boundary — noted here as a required follow-up, not actioned in this pass).

3. **`IdTokenVerifier` abstraction, one interface for both providers, no new verification library.** Mirrors AUTH-001's `SmsSender` seam (Decision 6 in that plan): an abstract interface with a single real implementation shape, easy to fake in tests.
   - `IdTokenVerifier` (ABC): `async def verify(self, id_token: str) -> IdentityClaims` — raises the new `InvalidIdentityTokenError` (Decision 6) on any failure.
   - `JwksIdTokenVerifier(IdTokenVerifier)`: one generic, provider-parametrized implementation (constructed with a `jwks_url`, accepted `issuer`(s), and accepted `audience`(s)) — not two separate hand-written classes — since Google and Apple's ID token verification is structurally identical (RS256, JWKS-published public keys, standard `iss`/`aud`/`exp` claims). Uses `python-jose`'s `jwk`/`jwt` primitives (already a dependency) for signature verification — **no `google-auth` or `PyJWT` dependency is introduced**; one verification code path serves both providers.
   - JWKS is fetched over HTTPS and cached in-memory keyed by `kid` (JSON Web Key ID), with a full refetch on an unrecognized `kid` (handles routine key rotation without a fixed TTL guess) — a standard, minimal caching strategy, not a new architectural component.
   - Two configured instances are constructed in `dependencies.py`: one for Google (`jwks_url="https://www.googleapis.com/oauth2/v3/certs"`, `issuer` accepting both `https://accounts.google.com` and `accounts.google.com`), one for Apple (`jwks_url="https://appleid.apple.com/auth/keys"`, `issuer="https://appleid.apple.com"`).

4. **Promote `httpx` from dev-only to a runtime dependency, for JWKS fetching only.** `httpx` is already present (dev group, used by `TestClient`) and is the natural async-native HTTP client for FastAPI-style code — reusing it avoids introducing a second HTTP client library (`08_CODING_STANDARDS.md`/`12_TECH_STACK.md` "Maintain one standard solution for each responsibility"). Move it from `[dependency-groups].dev` to `[project.dependencies]` in `backend/pyproject.toml`.

5. **`OAuthService`, parallel to `OtpService`, plus a new `AuthService.authenticate_with_oauth` method.** `OAuthService.__init__(self, verifiers: dict[AuthProvider, IdTokenVerifier])` exposes `async def verify_identity(self, provider: AuthProvider, id_token: str) -> IdentityClaims`, delegating to the right verifier and translating any low-level failure (bad signature, expired, wrong audience/issuer, malformed JWT, JWKS fetch failure) into the single generic `InvalidIdentityTokenError` (AC6 — the caller never sees which specific validation failed). `AuthService.authenticate_with_oauth(self, provider: AuthProvider, claims: IdentityClaims) -> tuple[User, str, list[str]]` mirrors `verify_otp_and_authenticate`'s shape exactly: find-or-create by `(auth_provider, external_auth_subject)` via a new `UserRepository.get_by_provider_and_subject`, assign the `customer` role only on creation (AC3), touch `last_login_at` on every authentication, issue a JWT via the existing `create_access_token` (same stateless-token approach as AUTH-001 — no `sessions`/`devices` row, that's still AUTH-003's job).

6. **New, single generic exception: `InvalidIdentityTokenError`.** Added to `backend/app/core/exceptions/exceptions.py`, `status_code=401`, message "We couldn't verify your sign-in. Please try again." (AC6 — plain-language, no detail on *which* validation failed: bad signature vs. expired vs. wrong audience are all indistinguishable to the caller, exactly like `InvalidOtpError`'s non-revealing design in AUTH-001).

7. **Two endpoints, `POST /auth/google` and `POST /auth/apple`, not one generic `/auth/oauth`.** Each accepts `{ "id_token": string }` and returns the existing `AuthTokenResponse`/`UserSummaryResponse` shape unchanged (schema reuse — no new response schema needed). Two endpoints keep provider selection out of the request body (avoids a client-supplied provider value driving which verifier runs — the route itself pins the provider, which is safer) and mirror AUTH-001's precedent of one endpoint per distinct auth action (`request-otp` / `verify-otp`) rather than a single param-dispatched endpoint. Both endpoints reuse `RateLimitDependency` (IP-keyed, `AUTH_RATE_LIMIT_PER_MINUTE`/`AUTH_RATE_LIMIT_WINDOW_SECONDS` — the same bucket already defined for the phone-OTP endpoints) as defense-in-depth, consistent with `06_SECURITY.md`'s blanket "every endpoint must apply rate limiting."

8. **Mobile: add `google_sign_in` and `sign_in_with_apple` as new Flutter dependencies.** Unlike AUTH-001 (which only wired up already-approved-but-unused packages), these two packages are **new** additions — native Google/Apple sign-in is not achievable without a platform-bridging plugin, and neither package appears on `12_TECH_STACK.md`'s "Approved Flutter Packages" list. Both are official, actively-maintained, single-purpose plugins (Google's own `google_sign_in`, Apple's ecosystem-standard `sign_in_with_apple`) with no overlap with an already-approved package, and neither falls in `12_TECH_STACK.md`'s "Packages Requiring Approval" deny-list (GraphQL, Celery, Firebase, etc.). **Flagged for explicit user confirmation before mobile implementation starts**, per `09_DECISIONS.md`'s decision-making rule for new dependencies — this is the one new-dependency decision in this plan that isn't a reuse-of-existing-infrastructure call.

9. **Google audience validation: a single configured Web/server OAuth Client ID (`serverClientId`), not one ID per platform.** `google_sign_in`'s standard cross-platform pattern is to request an ID token scoped to one shared "server client ID" (a Web OAuth client, used purely for audience-scoping, not for a web login flow) regardless of whether the app is running on iOS or Android — this keeps backend audience validation to one configured value (`GOOGLE_OAUTH_CLIENT_ID` in `Settings`) instead of a per-platform list.

10. **Apple audience validation accepts a configurable list, not a single value.** Apple's native iOS/macOS Sign in with Apple issues an identity token with `aud` = the app's Bundle ID; the Android/web fallback flow (`sign_in_with_apple`'s `WebAuthenticationOptions`, since Apple has no native Android SDK) issues a token with `aud` = a separately-registered Apple **Services ID**. Both are legitimate for this app. `Settings.APPLE_OAUTH_CLIENT_IDS` is a list (parsed the same way `ALLOWED_ORIGINS` already parses a comma-separated env value), and `JwksIdTokenVerifier` accepts a set of valid audiences, not just one. **Flagged as a plan-level assumption** (the exact Bundle ID / Services ID values are external Apple Developer Portal configuration not available in this planning pass) — confirm during review if Android Apple sign-in is even needed for MVP launch platforms, or if this can be simplified to iOS-only for v1.

11. **Email/claims are only applied at `User` creation time; never overwritten on a subsequent login.** If `email_verified_at` should be set, it is set from the provider's `email_verified` claim (`true`/`false`, encoded as a string by Apple and a boolean by Google — normalized in `IdentityClaims`) **only when the `User` row is first created**. On every subsequent authentication of an already-existing `(auth_provider, external_auth_subject)` pair, only `last_login_at` is touched — email is never re-written. This avoids a known Apple behavior (email is only guaranteed present on the *first* authorization; a later token may omit it) accidentally nulling out previously-captured data. Not an explicit AC, but a direct consequence of "matched on `(auth_provider, external_auth_subject)`, not email" (Story narrative) — flagged as a deliberate implementation choice, not left implicit.

12. **No `customer_profiles`/`customer_preferences` row creation, same as AUTH-001.** `14_USER_FLOWS.md` Flow 1 describes a fuller registration flow (profile + preferences + saved address) spanning multiple stories; AUTH-001 already established that registration-via-auth produces only an authenticated `User` + `customer` role, deferring profile creation to the Customer domain (CUS-001). AUTH-002's tracker ACs make no mention of `customer_profiles` either — this plan keeps that boundary consistent rather than reintroducing profile creation here.

13. **Cancellation (AC7) is a benign, non-error outcome on the mobile side — not routed through `AuthException`/error copy.** `sign_in_with_apple` throws a stable `SignInWithAppleAuthorizationException` with `AuthorizationErrorCode.canceled` on user cancellation, consistent across its recent versions. `google_sign_in`'s cancellation signal (a specific exception code, or a `null` return, depending on the installed major version) will be confirmed against whichever current stable version is added per Decision 8. Either way, the presentation/state layer catches this specific signal and resets loading state back to idle, returning the user to the sign-in screen with **no error message shown** (distinct from a real failure, which does show the generic AC6 copy) — a new `isCancelled`-style short-circuit in the OAuth sign-in controller, not a new `AuthErrorType` value that would render user-facing text.

14. **Test strategy for AC8: real verification code path, fake network boundary.** A shared test helper (`backend/tests/support/id_token_factory.py`) generates an RSA keypair at test time, builds a JWKS document from the public key, and signs test ID tokens with the private key (via `python-jose`, matching real Google/Apple token shape: `iss`, `aud`, `sub`, `email`, `email_verified`, `exp`). `JwksIdTokenVerifier`'s HTTP fetch is bound to a fake transport (`httpx.MockTransport`) serving the test JWKS instead of the real endpoint — so tests exercise the **actual** signature-verification/claim-checking code, not a stubbed-out verifier, while guaranteeing zero real calls to Google/Apple (AC8's explicit requirement). Reused by both the backend integration tests (AC9) and the verifier's own unit tests.

---

## Backend — Proposed Changes

### Migration (schema change — see Decision 2)
#### [NEW] `backend/alembic/versions/<rev>_identity_email_uniqueness_per_provider.py`
- `DROP INDEX identity.uq_users_email`
- `CREATE UNIQUE INDEX uq_users_email_provider ON identity.users (auth_provider, email) WHERE email IS NOT NULL`
- Update the corresponding `Index(...)` definition in `backend/app/modules/identity/models.py`'s `User.__table_args__` to match (rename `uq_users_email` → `uq_users_email_provider`, add `auth_provider` to the index columns).
- Verify both `upgrade()`/`downgrade()` are complete; note in the migration docstring that `downgrade()` will fail if cross-provider duplicate emails already exist in the target database (expected/acceptable for a dev rollback).

### Dependencies
#### [MODIFY] `backend/pyproject.toml`
Move `httpx` from `[dependency-groups].dev` to `[project.dependencies]` (Decision 4). No other new dependency.

### Config
#### [MODIFY] `backend/app/core/config.py`
Add `GOOGLE_OAUTH_CLIENT_ID: str` and `APPLE_OAUTH_CLIENT_IDS: list[str] | str` (parsed via a validator matching the existing `parse_allowed_origins` pattern) to `Settings`. Both are startup-validated per `06_SECURITY.md` ("Environment variables must be validated during application startup"). Add placeholder values to the local `.env`/CI config — real values are external Google Cloud Console / Apple Developer Portal configuration, not available in this planning pass (Decision 10). Tests never depend on the real values (Decision 14) since test tokens are minted to match whatever `aud` is configured for the test environment.

### Models
#### [MODIFY] `backend/app/modules/identity/models.py`
Rename `uq_users_email` → `uq_users_email_provider`, scoped to `(auth_provider, email)` (Decision 2). No other model changes — `auth_provider`/`external_auth_subject`/`uq_users_external_auth` are unchanged and already correct.

### Identity token verification
#### [NEW] `backend/app/modules/identity/services/id_token_verifier.py`
`IdentityClaims` (subject, email, email_verified — normalized dataclass/Pydantic model), `IdTokenVerifier` ABC, `JwksIdTokenVerifier` (Decision 3) — JWKS fetch via an injected `httpx.AsyncClient`, `kid`-keyed in-memory cache, `python-jose` RS256 verification against `iss`/`aud`/`exp`.
#### [NEW] `backend/app/modules/identity/services/oauth_service.py`
`OAuthService` (Decision 5) — routes to the right verifier per `AuthProvider`, translates any failure into `InvalidIdentityTokenError`.

### Repository
#### [MODIFY] `backend/app/modules/identity/repositories/user_repository.py`
Add `get_by_provider_and_subject(auth_provider: AuthProvider, external_auth_subject: str) -> User | None`.

### Service
#### [MODIFY] `backend/app/modules/identity/services/auth_service.py`
Add `authenticate_with_oauth(provider: AuthProvider, claims: IdentityClaims) -> tuple[User, str, list[str]]` (Decision 5) — find-or-create by `(auth_provider, external_auth_subject)`, assign `customer` role only on creation (AC3), never overwrite email on an existing user (Decision 11), issue JWT.

### Schemas
#### [MODIFY] `backend/app/modules/identity/schemas.py`
Add `OAuthSignInRequest { id_token: str }`. Reuse existing `AuthTokenResponse`/`UserSummaryResponse` — no new response schema.

### API
#### [MODIFY] `backend/app/modules/identity/api.py`
Add `POST /google` and `POST /apple` (Decision 7), both rate-limited (Decision 7), both returning `SuccessResponse[AuthTokenResponse]`.
#### [MODIFY] `backend/app/modules/identity/dependencies.py`
Add `get_google_id_token_verifier()`, `get_apple_id_token_verifier()`, `get_oauth_service()`, and extend `get_auth_service()`'s dependency chain to also receive the `OAuthService`.

### Exceptions
#### [MODIFY] `backend/app/core/exceptions/exceptions.py`
Add `InvalidIdentityTokenError` (Decision 6).

### Tests (AC8, AC9)
#### [NEW] `backend/tests/support/id_token_factory.py`
Shared RSA keypair / JWKS / signed-test-token helper (Decision 14).
#### [NEW] `backend/tests/modules/identity/test_id_token_verifier.py`
Valid signed token verifies; tampered signature rejected; expired token rejected; wrong audience rejected; wrong issuer rejected; unknown `kid` triggers a JWKS refetch — all against the fake transport, zero real network calls (AC8).
#### [NEW] `backend/tests/modules/identity/test_oauth_service.py`
Routes to the correct verifier per provider; wraps any verifier failure into the single generic `InvalidIdentityTokenError` (AC6).
#### [MODIFY] `backend/tests/modules/identity/test_auth_service.py`
New tests: new `(provider, subject)` pair creates a `User` + `customer` role (AC3); existing pair authenticates without duplicating the `User` (AC4); a different provider presenting the same email as an existing `User` creates a second, distinct `User` (AC5); email is not overwritten on a subsequent login where claims omit it (Decision 11).
#### [MODIFY] `backend/tests/modules/identity/test_auth_endpoints.py`
Integration tests for `POST /auth/google`/`POST /auth/apple` against the real FastAPI app + real Postgres session (matching AUTH-001's testing style): valid signed test token → 200 + token, new-user path assigns `customer` role; existing pair → 200, no duplicate; tampered/expired/wrong-audience token → 401 with only the generic AC6 message (assert the response body carries no validation detail); **AC9 — explicit integration test**: two calls, same email, different provider (`google` then `apple`), asserted via direct SQL to produce two distinct `identity.users` rows.

---

## Mobile — Proposed Changes

### Dependencies
#### [MODIFY] `mobile/pubspec.yaml`
Add `google_sign_in` and `sign_in_with_apple` (Decision 8 — flagged for confirmation before implementation), current stable versions at implementation time.

### Platform configuration (implementation-time prerequisite, not a plan-time deliverable)
iOS `Info.plist`/entitlements (Sign in with Apple capability, Google reversed-client-id URL scheme) and Android manifest/Google Cloud Console SHA-1 registration are required for on-device testing. These depend on external credentials (Google OAuth Web Client ID, Apple Bundle ID/Services ID/Team ID) not available in this planning pass — flagged as an explicit prerequisite the user must supply before end-to-end device testing, though automated tests do not depend on them (fakes/mocks at the repository layer, mirroring the mobile side of Decision 14).

### Feature: Auth
#### [MODIFY] `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart` (S-03)
Replace the `_DisabledAuthOption` Google/Apple buttons with real, tappable buttons wired to a new OAuth sign-in controller (AC1).
#### [NEW] `mobile/lib/features/auth/state/oauth_sign_in_controller.dart`
Riverpod controller (separate from `phone_entry_controller.dart` — distinct responsibility, `08_CODING_STANDARDS.md` SRP) exposing per-provider loading/error state and `signInWithGoogle()`/`signInWithApple()` methods. Cancellation (Decision 13) resets to idle with no error surfaced; any other failure surfaces the existing `AuthException`/`AuthErrorType` machinery, extended with a new `AuthErrorType.identityVerificationFailed` mapped to a localized string mirroring the backend's AC6 copy ("We couldn't verify your sign-in. Please try again.") — client-owned and localized, never the backend's raw message, consistent with AUTH-001's FU-3 precedent.
#### [MODIFY] `mobile/lib/features/auth/data/auth_repository.dart`
Add `signInWithGoogle()`/`signInWithApple()`: invoke the respective plugin's native sign-in flow to obtain a provider ID token, then `POST /auth/google` / `POST /auth/apple` with `{ id_token }`, returning the same `AuthToken` shape `verifyOtp` already returns (reused as-is — no new domain model needed, per Decision 5's mirrored return shape).
#### [MODIFY] `mobile/lib/l10n/app_en.arb` / `app_ar.arb`
Add the new identity-verification-failure string (Decision 13) and any button-label strings not already present (`continueWithGoogle`/`continueWithApple` already exist from AUTH-001's disabled buttons — reused, not duplicated).

### Tests
#### [NEW] `mobile/test/features/auth/oauth_sign_in_test.dart`
Using a fake/mocked sign-in-plugin boundary and the existing `fake_auth_repository.dart` pattern (extended with configurable `signInWithGoogle`/`signInWithApple` outcomes): successful sign-in navigates to `AppRoutes.homePlaceholder` and populates `authSessionProvider`; cancellation resets loading state with no error shown (AC7); a generic failure shows the localized AC6 copy, never a raw backend message; Google/Apple buttons render enabled (not the AUTH-001 "coming soon" disabled state) on the phone-entry screen (AC1).

---

## Explicitly Out of Scope (do not implement in this story)

- Account linking/merging across providers — a same-email, different-provider sign-in is a second, independent Account by design (AC5, Story scope boundary).
- `sessions`/`refresh_tokens` tables, token refresh, logout, multi-device session management, persisting the access token across app restarts — AUTH-003.
- RBAC enforcement, permission catalog, `role_permissions` rows — AUTH-004.
- `customer_profiles`/`customer_preferences` creation — Customer domain, CUS-001 (Decision 12).
- Admin `email_password` login flow — separate, not part of this story's scope.
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **Orchestrator** — before backend work starts, confirm with the user: (a) Decision 2's `uq_users_email` → `uq_users_email_provider` schema change (modifies an AUTH-001-shipped constraint), and (b) Decision 8's new Flutter dependencies (`google_sign_in`, `sign_in_with_apple`). Both are flagged above as needing explicit sign-off before implementation, not silent adoption.
2. **`backend`** (`backend/app/`, `backend/alembic/`, `backend/tests/`) — implement the "Backend — Proposed Changes" section, in this order: migration (email constraint) → config → identity token verifier → OAuth service → repository/service extensions → schemas → endpoints → exceptions → tests. Focus ACs: 2, 3, 4, 5, 6, 8, 9.
3. **`frontend`** (`mobile/lib/`, `mobile/test/`) — implement the "Mobile — Proposed Changes" section against the backend contract from step 2. Focus ACs: 1, 7. Platform-config prerequisites (real Google/Apple credentials) may block real-device verification but not the code/tests themselves.
4. **`tester`** — verify all 9 acceptance criteria individually: backend automated tests (id-token verifier, oauth service, auth service, endpoint integration including the AC9 two-distinct-users assertion) plus full regression of the existing suite; mobile widget/unit tests including cancellation and enabled-buttons checks; confirm no test makes a real network call to Google/Apple (AC8).
5. **`architect`** — review: the Decision 2 schema change against `04_DATABASE.md` (and flag that the doc itself needs a follow-up update, out of orchestrator's write boundary); ID-token verification design against `06_SECURITY.md` ("no token trusted without verification") and OWASP guidance on JWT/JWKS handling; Clean Architecture layering (`IdTokenVerifier`/`OAuthService`/`AuthService` boundaries); mobile Feature-First structure and the new-dependency additions against `08_CODING_STANDARDS.md`/`12_TECH_STACK.md`.
6. **Orchestrator** — once `tester` and `architect` both report clean, pause and present the diff + both verdicts to the user for explicit sign-off before writing the Walkthrough or touching the changelog/tracker.

---

## Verification Plan

- `cd backend && uv run pytest -v` — full suite, including new id-token-verifier/oauth-service/auth-service/endpoint tests, must pass; no regression in AUTH-001's existing tests (the email-constraint migration is the main regression risk to watch).
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — migration reversible.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- `cd mobile && flutter test` — new widget/unit tests pass, no regression in AUTH-001's existing auth widget tests.
- `cd mobile && flutter analyze` — no new warnings.
- Manual/API-level check: `POST /api/v1/auth/google` and `POST /api/v1/auth/apple` with a valid signed test token create/authenticate a `User` correctly; a tampered token returns a generic 401; two calls with the same email but different providers produce two distinct `identity.users` rows (direct SQL check).
- Confirm (via test-suite audit, not just code review) that no test in `backend/tests/` makes an outbound HTTPS call to `googleapis.com` or `appleid.apple.com`.

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` — Identity & Access domain
- `docs/AI/04_DATABASE.md` — Identity Domain schema (needs a follow-up update reflecting Decision 2, out of orchestrator's write boundary)
- `docs/AI/05_API_GUIDELINES.md` — response envelope, rate limiting, status codes
- `docs/AI/06_SECURITY.md` — token verification, generic error messages, rate limiting
- `docs/AI/08_CODING_STANDARDS.md` — Flutter/Python structure and naming
- `docs/AI/12_TECH_STACK.md` — approved package lists, package-approval process
- `docs/AI/14_USER_FLOWS.md` — Flow 1 (Customer Registration), Google/Apple step
- `docs/AI/15_SCREEN_INVENTORY.md` — S-03 (Sign In / Sign Up)
- `docs/implementation/plans/Plan_S02_AUTH-001.md` — prior story, shipped `identity` schema/models this story extends
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-001.md` — verified current-state source for this plan
- `docs/implementation/prompts/Prompt_S02_AUTH-002.md`
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-002.md` (to be created on completion)
