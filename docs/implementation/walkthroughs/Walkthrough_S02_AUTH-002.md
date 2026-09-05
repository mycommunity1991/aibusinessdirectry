# Walkthrough S02 AUTH-002

## Story: Register and Sign In with Google or Apple

**Sprint:** 02 | **Story ID:** AUTH-002 | **Priority:** High | **Status:** Done

As a new or returning user, I want to continue with Google or Apple, so that I can access the app using an identity I already trust, without creating a new credential.

This story adds the OAuth path alongside AUTH-001's mobile OTP path — both lead to the same underlying `User` record shape. Server-side ID-token verification is mandatory; the client's assertion of identity is never trusted directly. Accounts are matched on the `(auth_provider, external_auth_subject)` pair, not on email, because social email addresses can be unverified or change.

Full context, architecture decisions, and file-by-file scope: `docs/implementation/plans/Plan_S02_AUTH-002.md` (see that plan's Supersession Notice — it replaced a stale "OTP Verification Service" plan written against the old, superseded 9-story Sprint 2 backlog).

---

## What was implemented

### Backend (`backend/app/modules/identity/`)

- **Schema change** — `uq_users_email` (global partial unique on `email`) replaced with `uq_users_email_provider`, a partial unique index on `(auth_provider, email)`, via `backend/alembic/versions/2026_08_29_1000-be1f79b6fa2a_identity_email_uniqueness_per_provider.py`. This was required because the old constraint blocked AC5/AC9's requirement that the same email under two different providers produce two independent `User` rows. Verified reversible (upgrade → downgrade → upgrade, live, non-mocked).
- **ID-token verification** — `services/id_token_verifier.py`: `IdentityClaims`, `IdTokenVerifier` ABC, and one generic `JwksIdTokenVerifier` implementation serving both Google and Apple (RS256, JWKS-published keys, standard `iss`/`aud`/`exp` claims — structurally identical for both providers, so no per-provider verifier class was needed). JWKS fetched over HTTPS via an injected `httpx.AsyncClient`, cached in-memory keyed by `kid`, with a single refetch on an unrecognized `kid` (confirmed bounded, not a loop). `algorithms` is hard-pinned to `["RS256"]`, ruling out `alg:none`/HS256-confusion attacks. `httpx` was promoted from a dev-only to a runtime dependency to support this (already present for `TestClient`, no new HTTP client library introduced).
- **OAuth orchestration** — `services/oauth_service.py`: `OAuthService` routes to the correct verifier per `AuthProvider` and collapses any failure (bad signature, expired, wrong audience/issuer, malformed token, JWKS fetch failure) into one generic `InvalidIdentityTokenError` (401, "We couldn't verify your sign-in. Please try again.") — the caller never learns which specific check failed (AC6).
- **Service** — `AuthService.authenticate_with_oauth(provider, claims)` mirrors AUTH-001's `verify_otp_and_authenticate` pattern: find-or-create by `(auth_provider, external_auth_subject)`, assigns the `customer` role only on creation (AC3), authenticates existing pairs without duplication (AC4), touches `last_login_at` on every login, and never overwrites email on a later login (Apple only guarantees email on first authorization). Issues a JWT via the existing `create_access_token` utility — no `sessions`/`devices`/`customer_profiles` row, consistent with AUTH-001's scope boundary.
- **API** — `POST /api/v1/auth/google` and `POST /api/v1/auth/apple` (`api.py`), each accepting `{ id_token }` and returning the existing `AuthTokenResponse`/`UserSummaryResponse` shape unchanged. Both rate-limited via the existing Redis-backed `RateLimitDependency` (IP-keyed, same bucket as `request-otp`/`verify-otp`). The route pins the provider rather than trusting a client-supplied value.
- **Config** — `Settings.GOOGLE_OAUTH_CLIENT_ID`/`APPLE_OAUTH_CLIENT_IDS` added, startup-validated, parsed via a shared helper also reused by the existing `ALLOWED_ORIGINS` setting.
- **Tests** — `tests/support/id_token_factory.py` (new: signs test ID tokens with a test-generated RSA keypair, serves a matching JWKS via `httpx.MockTransport`), `test_id_token_verifier.py` (13 tests: valid/tampered/expired/wrong-audience/wrong-issuer/unknown-kid-refetch/etc.), `test_oauth_service.py` (5 tests: provider routing, generic-failure wrapping), extended `test_auth_service.py` (+4) and `test_auth_endpoints.py` (+11, including the explicit AC9 two-distinct-users direct-SQL check), extended `test_identity_models.py` (+1, 1 renamed to match the new constraint name). **156 tests passing** (full suite, 0 regressions), `ruff check`/`ruff format --check` clean. No test makes a real call to `googleapis.com` or `appleid.apple.com` (AC8, independently confirmed by both `tester` and `architect`).

### Mobile (`mobile/lib/`)

- **Dependencies** — `google_sign_in: ^7.2.0` and `sign_in_with_apple: ^8.2.0` added (new, user-approved additions — neither was previously on the approved package list).
- **State** — `features/auth/state/oauth_sign_in_controller.dart` (new): `OAuthSignInController`, separate from `phone_entry_controller.dart` per single-responsibility. Tracks per-provider loading state; on cancellation (closing the native consent screen), resets fully to idle with **no error shown** (AC7) — a deliberate non-error outcome, distinct from a real failure (which shows the generic AC6 copy via a new `AuthErrorType.identityVerificationFailed`).
- **Screen** — `phone_entry_screen.dart`: the AUTH-001 `_DisabledAuthOption` ("coming soon") placeholders replaced with real, tappable `_OAuthOptionButton`s wired to the new controller (AC1), reusing the app's existing themed button/loading/error-message widgets — no hardcoded colors or strings.
- **Repository** — `auth_repository.dart`: `signInWithGoogle()`/`signInWithApple()` invoke the native plugin flow to obtain a provider ID token, then exchange it via the backend endpoints, returning the same `AuthToken` shape `verifyOtp()` already returns — no new domain model needed.
- **Localization** — new `identityVerificationFailedMessage` string added to `app_en.arb`/`app_ar.arb` (the `continueWithGoogle`/`continueWithApple` labels already existed from AUTH-001's disabled buttons).
- **Tests** — `test/features/auth/oauth_sign_in_test.dart` (new, 7 tests): buttons render enabled, successful sign-in navigates and populates session state, cancellation resets with no error shown, generic failure shows only the localized copy. `phone_entry_screen_test.dart` updated to assert the buttons are now enabled (the intentional, AC1-driven behavior change from AUTH-001's disabled state). **27 tests passing**, `flutter analyze` clean, `dart format` clean.

---

## Acceptance Criteria — Verification

All 9 acceptance criteria (from `Plan_S02_AUTH-002.md`, sourced from the Tracker) were independently verified by the `tester` agent — re-running every suite from a clean shell rather than trusting the engineering agents' self-reports, and reading actual test bodies/response payloads for the criteria most likely to be rubber-stamped. All 9 passed.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Sign-in screen offers Google and Apple buttons alongside the mobile-number option | Pass |
| 2 | Backend verifies Google/Apple ID tokens against each provider's public keys; no token trusted without verification | Pass |
| 3 | A new `(auth_provider, external_auth_subject)` pair creates a new User and assigns the customer role | Pass |
| 4 | An existing `(auth_provider, external_auth_subject)` pair authenticates the existing User | Pass |
| 5 | A different provider presenting the same email creates a second, independent Account | Pass |
| 6 | Invalid/expired/tampered tokens rejected with a generic message, never a detailed validation error | Pass |
| 7 | User cancellation returns to the sign-in screen without a crash or stuck loading state | Pass |
| 8 | Tests use signed test tokens/mocked provider endpoints — no real Google/Apple network calls | Pass |
| 9 | Integration test explicitly verifies the same-email/different-provider case produces two distinct User rows | Pass |

---

## Important Decisions

- **Schema change to an AUTH-001-shipped constraint**: `uq_users_email` → `uq_users_email_provider`, scoped to `(auth_provider, email)`. Explicitly confirmed with the user before implementation, since it modifies a constraint the previous story already shipped and tested.
- **One generic `JwksIdTokenVerifier`, not two provider-specific classes.** Google and Apple ID-token verification is structurally identical (RS256, JWKS, standard claims) — a single, provider-parametrized implementation avoids duplicating verification logic. No new verification library was added; the existing `python-jose` dependency (already used for the app's own JWT issuance) handles it.
- **Two endpoints (`/auth/google`, `/auth/apple`), not one generic `/auth/oauth`.** The route itself pins which verifier runs, rather than trusting a client-supplied provider value — a defense-in-depth choice, and consistent with AUTH-001's precedent of one endpoint per distinct auth action.
- **`AuthService.authenticate_with_oauth` takes pre-verified claims, not an injected `OAuthService`.** This reads as a deviation from one implementation-detail line in the Plan, but matches the Plan's own Decision 5 method signature exactly, and was judged by the `architect` to be the cleaner design: it keeps token verification and account persistence as independently testable, decoupled concerns. Confirmed (by both `tester` and `architect`, reading `api.py` directly) that the only production call site always verifies before authenticating — no bypass path exists.
- **Email/claims are written only at `User` creation time, never overwritten on a later login** — a deliberate consequence of matching on `(auth_provider, external_auth_subject)`, not email, and a defense against Apple's known behavior of only guaranteeing email on the first authorization.
- **New Flutter dependencies (`google_sign_in`, `sign_in_with_apple`)** — explicitly confirmed with the user before implementation, since native OAuth on mobile isn't achievable without a platform-bridging plugin and neither package was previously approved.

---

## Architect Review — Findings and Resolution

The `architect` agent returned **STORY COMPLETE (pass)** — no code changes required. Full findings in `docs/implementation/plans/Checkpoint_S02_AUTH-002.md` (now superseded by this Walkthrough); summary:

1. **The `AuthService`/`OAuthService` wiring "deviation"** — assessed as legitimate, not a defect (see Important Decisions above).
2. **The `uq_users_email_provider` schema change** — correctly implemented, and not vestigial: it still guards against a same-provider duplicate email (defense in depth) and yields effectively-global uniqueness for the internal `email_password` (admin) provider.
3. **JWKS/JWT verification** — no algorithm-confusion vulnerability (`RS256` hard-pinned); the `kid`-keyed cache's refetch-on-miss is bounded to one refetch per call, not an unbounded loop.
4. **Rate limiting** — genuinely wired on both new endpoints via `RateLimitDependency`, not just documented.
5. **Secrets/logging** — no ID token, claims, or generated JWT is ever logged at any level.
6. **Mobile structure** — follows AUTH-001's Feature-First/SRP conventions; no hardcoded strings or colors.

### Documentation gaps found and resolved as part of story finalization

Two `docs/AI/` documents were stale (neither `backend` nor `frontend` nor `architect` had write access there to fix them themselves):
- `04_DATABASE.md` — updated the `users` table constraint list from `uq_users_email` to `uq_users_email_provider` on `(auth_provider, email)`.
- `12_TECH_STACK.md` — added `google_sign_in`/`sign_in_with_apple` to "Approved Flutter Packages" and `httpx` to "Approved Python Packages".

### Tracked, non-blocking follow-ups (not required for this story's sign-off)

- A short negative-cache TTL (or minimum refetch interval) for `JwksIdTokenVerifier._get_key` would harden against a stream of requests each carrying a distinct forged `kid` forcing a real JWKS fetch per request. Currently bounded by the existing 10/min IP rate limit — adequate defense in depth, not a dedicated control. Candidate for a future hardening ticket.
- Root `.env.example` still needs `GOOGLE_OAUTH_CLIENT_ID=`/`APPLE_OAUTH_CLIENT_IDS=` placeholder lines (external credential prerequisite, doesn't block automated-test-based sign-off).
- Real Google/Apple credentials (Web OAuth Client ID, Apple Bundle ID/Services ID) and iOS/Android platform configuration (Info.plist/entitlements, AndroidManifest.xml) are still needed before real-device OAuth sign-in can be exercised — the Dart/Flutter code and its automated tests do not depend on them (fakes/mocks at the repository layer), consistent with the Plan's stated external prerequisite.

---

## Testing Performed

- `cd backend && uv run pytest -v` — 156/156 passing, 0 regressions on AUTH-001.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — verified live, non-mocked, against a real local Postgres test database; reversible.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- `cd mobile && flutter test` — 27/27 passing, 0 regressions.
- `cd mobile && flutter analyze` — clean, no new warnings.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean.
- `tester` agent: all 9 ACs independently verified with direct evidence (real response payloads, direct SQL row counts, grep for real-network-call absence) — see table above.
- `architect` agent: STORY COMPLETE — see findings above.
- Regression check: diffed every modified AUTH-001 test file against the prior commit; all changes additive except two expected, approved consequences of this story's own scope (the renamed constraint's match string, and the disabled→enabled button assertion for AC1).

---

## Key Files

### Backend
- `backend/alembic/versions/2026_08_29_1000-be1f79b6fa2a_identity_email_uniqueness_per_provider.py`
- `backend/app/modules/identity/models.py` (constraint rename)
- `backend/app/modules/identity/services/id_token_verifier.py`
- `backend/app/modules/identity/services/oauth_service.py`
- `backend/app/modules/identity/services/auth_service.py` (`authenticate_with_oauth`)
- `backend/app/modules/identity/repositories/user_repository.py` (`get_by_provider_and_subject`)
- `backend/app/modules/identity/schemas.py` (`OAuthSignInRequest`)
- `backend/app/modules/identity/api.py` (`/google`, `/apple`)
- `backend/app/modules/identity/dependencies.py`
- `backend/app/core/config.py` (`GOOGLE_OAUTH_CLIENT_ID`, `APPLE_OAUTH_CLIENT_IDS`)
- `backend/app/core/exceptions/exceptions.py` (`InvalidIdentityTokenError`)
- `backend/pyproject.toml` (`httpx` promoted to runtime)
- `backend/tests/support/id_token_factory.py`
- `backend/tests/modules/identity/{test_id_token_verifier,test_oauth_service}.py` (new), `{test_auth_service,test_auth_endpoints,test_identity_models}.py` (extended)

### Mobile
- `mobile/pubspec.yaml` (`google_sign_in`, `sign_in_with_apple`)
- `mobile/lib/core/network/oauth_config.dart`
- `mobile/lib/features/auth/state/oauth_sign_in_controller.dart`
- `mobile/lib/features/auth/data/auth_repository.dart` (`signInWithGoogle`/`signInWithApple`)
- `mobile/lib/features/auth/domain/models/auth_exception.dart` (`identityVerificationFailed`, `OAuthCancelledException`)
- `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart` (`_OAuthOptionButton`)
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}`
- `mobile/test/features/auth/oauth_sign_in_test.dart` (new), `phone_entry_screen_test.dart` (updated), `fakes/fake_auth_repository.dart` (extended)

### Documentation
- `docs/AI/04_DATABASE.md` — constraint name/scope updated
- `docs/AI/12_TECH_STACK.md` — new approved packages added

---

## Follow-up Notes

- All nice-to-have items from the architect review are tracked above; none are required to close this story.
- `docs/implementation/plans/Plan_S02_AUTH-003.md` and `Plan_S02_AUTH-004.md` still describe the old, superseded 9-story Sprint 2 backlog and do not correspond 1:1 to the current tracker's AUTH-003 ("Stay signed in and manage active sessions") / AUTH-004 ("Access the app according to my role"). They must be re-planned against the current tracker before being picked up, following the same process used for AUTH-001 and AUTH-002.
- AUTH-003 is next in the Sprint 2 backlog. It depends on both AUTH-001 and AUTH-002 (both now Done) and will build `sessions`/`refresh_tokens`/`devices` tables and JWT refresh/rotation on top of the `User` records both prior stories create.
