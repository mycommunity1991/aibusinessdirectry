**Active Story:** Sprint 2 | AUTH-002 | Register and Sign In with Google or Apple

**Story:**
As a new or returning user, I want to continue with Google or Apple, so that I can access the app using an identity I already trust, without creating a new credential.

This story adds the OAuth path alongside AUTH-001's mobile OTP path — both lead to the same underlying `User` record shape. Server-side ID-token verification is mandatory; the client's assertion of identity is never trusted directly. Accounts are matched on the `(auth_provider, external_auth_subject)` pair, not on email, because social email addresses can be unverified or change.

**Scope boundary:** does NOT include account linking/merging across providers — a different provider with the same email produces a second, separate Account by design in this story; any future account-linking capability is out of scope here.

---

## Technical Context & Architecture Constraints

- The identity codebase already lives at `backend/app/modules/identity/` (`models.py`, `schemas.py`, `api.py`, `dependencies.py`, `repositories/`, `services/`) — AUTH-001 was refactored into this module layout after architect review. Work inside this layout, not the flat `app/models/`/`app/services/` layout an earlier draft assumed.
- `User.auth_provider`/`external_auth_subject` and the partial unique index `uq_users_external_auth` on `(auth_provider, external_auth_subject)` already exist from AUTH-001 — no migration needed for those columns.
- **Required schema change:** `uq_users_email` (global partial unique index on `email` alone) conflicts with AC5 — two different providers presenting the same email must produce two distinct `User` rows, which the current constraint blocks. Replace it with `uq_users_email_provider`, a partial unique index on `(auth_provider, email)` `WHERE email IS NOT NULL`, via a new Alembic migration. **Confirm this with the user before implementation** — it modifies a constraint AUTH-001 already shipped and tested.
- ID-token verification: one interface, `IdTokenVerifier` (ABC) with a single generic `JwksIdTokenVerifier` implementation parametrized by `jwks_url`/`issuer`/`audience` — Google and Apple are structurally identical (RS256, JWKS-published keys, standard `iss`/`aud`/`exp` claims), so one code path serves both. Use `python-jose` (already a dependency) for JWK/JWT verification — do not add `google-auth` or `PyJWT`. JWKS is fetched over HTTPS and cached in-memory keyed by `kid`, refetching on an unrecognized `kid`.
- Promote `httpx` from a dev-only dependency to a runtime dependency (for JWKS fetching only) — it's already present for `TestClient`, reuse it rather than adding a second HTTP client.
- Two endpoints, `POST /auth/google` and `POST /auth/apple` (not one generic `/auth/oauth`) — the route itself pins the provider rather than trusting a client-supplied value. Both rate-limited via the existing `RateLimitDependency`/Redis setup (added as an AUTH-001 follow-up) reusing the same auth bucket as `request-otp`/`verify-otp`.
- All verification failures (bad signature, expired, wrong audience/issuer, malformed token, JWKS fetch failure) collapse into one generic `InvalidIdentityTokenError` (401, "We couldn't verify your sign-in. Please try again.") — never a detailed validation error (AC6).
- `AuthService` gets a new `authenticate_with_oauth` method mirroring the existing `verify_otp_and_authenticate` shape: find-or-create by `(auth_provider, external_auth_subject)`, assign `customer` role only on creation (AC3), touch `last_login_at` on every login, issue a JWT via the existing `create_access_token`. No `sessions`/`refresh_tokens`/`devices` row — that's still AUTH-003. No `customer_profiles`/`customer_preferences` row — Customer domain, CUS-001.
- Email/claims are only written at `User` creation time; never overwritten on a later login (Apple only guarantees email on the first authorization).
- Mobile: `phone_entry_screen.dart` already renders disabled Google/Apple buttons (`_DisabledAuthOption`, explicitly commented "wired in AUTH-002") — replace with real, tappable buttons. Add `google_sign_in` and `sign_in_with_apple` as **new** Flutter dependencies (neither is on `12_TECH_STACK.md`'s approved list yet) — **flag for explicit user confirmation before mobile implementation starts**, per the project's new-dependency approval rule.
- Google audience validation uses a single configured server/Web OAuth Client ID (`GOOGLE_OAUTH_CLIENT_ID`). Apple audience validation accepts a configurable list (`APPLE_OAUTH_CLIENT_IDS`) since native iOS uses the Bundle ID and the Android/web fallback uses a separate Services ID. Real credential values are external Google Cloud Console / Apple Developer Portal configuration, not available at planning time — add placeholders, real values are a pre-device-testing prerequisite.
- Cancellation (AC7) is a benign, non-error outcome on mobile — caught by its provider-specific cancellation signal and reset to idle with no error message shown, distinct from a real failure (which shows the generic AC6 copy).
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S02_AUTH-002.md` — follow it, including its Architecture Decisions and Verified Current State sections.

---

## Implementation Instructions

### Backend
1. Add a new Alembic migration: drop `uq_users_email`, create `uq_users_email_provider` on `(auth_provider, email)` partial unique; update the corresponding `Index(...)` in `backend/app/modules/identity/models.py`. Verify upgrade and downgrade both work.
2. Move `httpx` from `[dependency-groups].dev` to `[project.dependencies]` in `backend/pyproject.toml`. No other new backend dependency.
3. Add `GOOGLE_OAUTH_CLIENT_ID: str` and `APPLE_OAUTH_CLIENT_IDS: list[str] | str` to `Settings` in `backend/app/core/config.py`, validated at startup, parsed the same way `ALLOWED_ORIGINS` already is.
4. Add `backend/app/modules/identity/services/id_token_verifier.py`: `IdentityClaims`, `IdTokenVerifier` ABC, `JwksIdTokenVerifier` (JWKS fetch via injected `httpx.AsyncClient`, `kid`-keyed cache, `python-jose` RS256 verification).
5. Add `backend/app/modules/identity/services/oauth_service.py`: `OAuthService` routing to the correct verifier per `AuthProvider`, translating any failure into `InvalidIdentityTokenError`.
6. Add `UserRepository.get_by_provider_and_subject(auth_provider, external_auth_subject) -> User | None`.
7. Add `AuthService.authenticate_with_oauth(provider, claims) -> tuple[User, str, list[str]]` per the constraints above.
8. Add `OAuthSignInRequest { id_token: str }` to `backend/app/modules/identity/schemas.py`; reuse the existing `AuthTokenResponse`/`UserSummaryResponse`.
9. Add `POST /google` and `POST /apple` to `backend/app/modules/identity/api.py`, both rate-limited, both returning `SuccessResponse[AuthTokenResponse]`. Wire the two new verifier/service dependencies in `dependencies.py`.
10. Add `InvalidIdentityTokenError` to `backend/app/core/exceptions/exceptions.py`.
11. Add `backend/tests/support/id_token_factory.py`: generates an RSA keypair and signs test ID tokens at test time, serving a matching JWKS via `httpx.MockTransport` — no test may call the real Google/Apple endpoints (AC8).
12. Write tests: `test_id_token_verifier.py` (valid/tampered/expired/wrong-audience/wrong-issuer/unknown-`kid`-refetch), `test_oauth_service.py` (routes correctly, wraps failures generically), extend `test_auth_service.py` (new pair creates User+role, existing pair no duplicate, same-email-different-provider creates two distinct Users, email not overwritten on re-login), extend `test_auth_endpoints.py` (integration tests for both endpoints including the explicit AC9 two-distinct-users check via direct SQL).

### Mobile
13. Add `google_sign_in` and `sign_in_with_apple` to `mobile/pubspec.yaml` (current stable versions) — confirmed with user first.
14. Add `mobile/lib/features/auth/state/oauth_sign_in_controller.dart`: Riverpod controller with per-provider loading/error state, `signInWithGoogle()`/`signInWithApple()`. Cancellation resets to idle with no error surfaced; other failures use a new `AuthErrorType.identityVerificationFailed` localized string mirroring the backend's AC6 copy.
15. Replace `_DisabledAuthOption` in `phone_entry_screen.dart` with real buttons wired to the new controller (AC1).
16. Add `signInWithGoogle()`/`signInWithApple()` to `auth_repository.dart`: invoke the native plugin flow to obtain a provider ID token, then `POST /auth/google` / `POST /auth/apple`, returning the existing `AuthToken` shape.
17. Add the new localized string(s) to `app_en.arb`/`app_ar.arb` (`continueWithGoogle`/`continueWithApple` labels already exist from AUTH-001's disabled buttons).
18. Write `mobile/test/features/auth/oauth_sign_in_test.dart`: successful sign-in navigates and populates session state; cancellation resets with no error (AC7); generic failure shows localized AC6 copy; buttons render enabled, not the AUTH-001 disabled state (AC1).

### Both
19. Confirm `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and `flutter analyze`.
20. Do not implement anything in the Plan's "Explicitly Out of Scope" section (account linking/merging, sessions/refresh tokens/logout, RBAC enforcement, customer profiles, admin email/password login, any Quote/messaging/payment feature).

---

## Definition of Done

- All 9 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (AUTH-002 row) are met, verified by `tester` against each one individually.
- `uq_users_email` is replaced by `uq_users_email_provider` via a working, reversible migration; no regression in AUTH-001's existing tests.
- `POST /auth/google` and `POST /auth/apple` work end-to-end: new `(provider, subject)` pair → new `User` + `customer` role; existing pair → same `User`, `last_login_at` updated, no duplicate; same email across two providers → two distinct `User` rows (AC9, asserted directly); invalid/expired/tampered token → generic 401 with no validation detail (AC6).
- No test makes a real network call to `googleapis.com` or `appleid.apple.com` (AC8).
- Mobile sign-in screen offers working Google/Apple buttons alongside the AUTH-001 mobile-number path; cancellation returns to the sign-in screen with no crash, stuck spinner, or error message (AC7).
- No `sessions`, `refresh_tokens`, `customer_profiles`, or `customer_preferences` row is created by this story's code paths.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- No functionality from AUTH-003/004, CUS-001, account linking, or `11_MVP_SCOPE.md`'s excluded list is introduced, even incidentally.
- The two flagged decisions (email-uniqueness constraint change; new `google_sign_in`/`sign_in_with_apple` dependencies) are explicitly confirmed with the user before their respective implementation work starts.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched.
