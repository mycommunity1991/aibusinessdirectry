# Checkpoint — Sprint 02, Story AUTH-002 (Register and Sign In with Google or Apple)

**Written by:** `architect` agent (updating the `tester` agent's earlier checkpoint)
**Status:** Backend implementation complete. Mobile implementation complete. Tester verification complete. **Architect review complete — VERDICT: STORY COMPLETE (pass).** Ready for orchestrator to present diff + verdicts to the user for explicit sign-off, subject to the mandatory pre-closure documentation updates listed below (owned by `tech-lead`, not a code change).

---

## Architect Review Verdict (this pass)

**Verdict: STORY COMPLETE — no code changes required.** Architecture, security, and
coding-standards review of the diff (`git diff` scoped to files this story touched,
plus the new untracked files) against `docs/AI/02_ARCHITECTURE.md`,
`docs/AI/06_SECURITY.md`, `docs/AI/08_CODING_STANDARDS.md`, and
`docs/AI/04_DATABASE.md` is clean. All 8 specific review items from the review
brief were independently checked by reading the actual code (not re-trusting the
tester's or engineers' self-reports), with the following findings.

### 1. `AuthService.authenticate_with_oauth(provider, claims)` — PASS, not a deviation requiring correction

Read `backend/app/modules/identity/api.py`, `dependencies.py`, `services/auth_service.py`,
`services/oauth_service.py` directly. Two things confirmed:

- Decision 5's own literal text in `Plan_S02_AUTH-002.md` already specifies
  `AuthService.authenticate_with_oauth(self, provider: AuthProvider, claims: IdentityClaims)`
  — i.e. a pre-verified-claims signature, not a raw `id_token`. The shipped method
  signature matches Decision 5 exactly. The only wording this deviates from is a
  single implementation-detail line further down in the Plan's "Backend — Proposed
  Changes" section ("extend `get_auth_service()`'s dependency chain to also receive
  the `OAuthService`") — a lower-precedence, more mechanical instruction that
  conflicts with Decision 5's own method shape.
- The actual wiring (`api.py`'s `_sign_in_with_oauth` receives both `oauth_service`
  and `auth_service` as sibling dependencies and calls
  `oauth_service.verify_identity(...)` before `auth_service.authenticate_with_oauth(...)`)
  is the architecturally cleaner choice: it keeps `AuthService` (account
  persistence/find-or-create orchestration) fully decoupled from `OAuthService`
  (external JWKS/token verification) — two independent concerns, each
  independently unit-testable without mocking the other (confirmed:
  `test_auth_service.py` and `test_oauth_service.py` are fully separate test
  files with no cross-mocking). Injecting an unused `OAuthService` into
  `AuthService`'s constructor merely to match the Plan's literal wording would
  have been the actual coding-standards violation here ("Introduce unnecessary
  abstractions" / unused constructor dependency).
- Grepped `app/` for every call site of `authenticate_with_oauth`: the only
  production caller is `_sign_in_with_oauth`, always preceded by
  `verify_identity(...)` with no bypass branch. AC2 ("no token trusted without
  verification") is enforced by the real call sequence, matching the tester's
  independent finding.
- The two-call sequence inside `_sign_in_with_oauth` contains no conditional
  business-rule logic — it is orchestration ("Routes orchestrate", per
  `02_ARCHITECTURE.md`), not business logic inside a controller.

No fix required. Nice-to-have only: update the Plan's "Backend — Proposed Changes"
prose to describe the DI wiring actually built, for future-reader accuracy.

### 2. Decision 2 schema change — PASS, correctly implemented, not vestigial

- `backend/alembic/versions/2026_08_29_1000-be1f79b6fa2a_identity_email_uniqueness_per_provider.py`:
  `upgrade()` drops `uq_users_email`, creates `uq_users_email_provider` on
  `(auth_provider, email)` partial unique `WHERE email IS NOT NULL`. `downgrade()`
  correctly reverses it, with an explicit docstring caveat that downgrade will
  fail in the presence of cross-provider duplicate emails (correct, expected).
- `backend/app/modules/identity/models.py`'s `User.__table_args__` `Index(...)`
  definition matches the migration exactly (name, columns, partial-index
  predicate).
- The constraint is **not vestigial**: real identity matching is via
  `(auth_provider, external_auth_subject)` as the story narrative says, but
  `uq_users_email_provider` still guards a real integrity concern — it prevents
  two rows for the *same* provider from claiming the same email (defense in
  depth against an application-layer bug in the find-or-create logic), and for
  the `email_password` provider (internal Admin accounts, per `04_DATABASE.md`)
  it still yields effectively-global email uniqueness in practice, since that
  provider value has exactly one real-world use. Correctly scoped, not a
  leftover.

### 3. `docs/AI/04_DATABASE.md` currency — CONFIRMED STALE, must-fix (documentation only, no code change)

`docs/AI/04_DATABASE.md` lines 157 and 170 still describe the old, now-dropped
`uq_users_email` constraint (global, `email` alone). This is stale and must be
updated to describe `uq_users_email_provider` (partial unique on
`(auth_provider, email)`) before the story is marked Done. Confirmed via my own
role boundary (`.claude/agents/architect.md`: read-only except the Checkpoint
file) that I do **not** have write access to `docs/AI/` — flagging for
`tech-lead` to action, not doing it myself. This does not block user sign-off on
the functional/architectural review itself, but should be closed out as part of
story finalization per `app/.agents/agents.md`'s Documentation Rule ("identify
the affected document(s) under `docs/AI/` and recommend the necessary updates
before completing the task").

### 4. JWKS/JWT verification (`id_token_verifier.py`) — PASS, no algorithm-confusion vulnerability; one non-blocking hardening gap

- `jwt.decode(id_token, jwk_key, algorithms=["RS256"], issuer=..., options={"verify_aud": False})`
  — `algorithms` is hard-pinned to `["RS256"]`. `python-jose` validates the
  token header's `alg` against this allow-list before verifying, so neither an
  `alg: none` token nor an HS256-signed token (using the RSA public key bytes as
  an HMAC secret — the classic library-level algorithm-confusion pitfall) can
  ever verify: both would present a header `alg` outside `["RS256"]` and be
  rejected before signature checking. `aud` is deliberately checked manually
  against a `frozenset` (`_audience_is_accepted`) rather than relying on
  `python-jose`'s built-in single-string audience check — correctly reasoned
  for Apple's multi-audience requirement (Decision 10). `iss`/`exp` are
  verified by `python-jose` itself. Signature verification against the fetched
  JWK is real (not stubbed) — confirmed by `test_tampered_signature_is_rejected`.
- `kid`-keyed cache with refetch-on-miss: confirmed via
  `test_persistently_unknown_kid_is_rejected_after_refetch` that a single
  `verify()` call triggers **at most one** refetch, not an unbounded loop —
  no per-request DoS risk. However, there is no cross-request bound (e.g. a
  minimum refetch interval or a short negative-TTL cache for a `kid` just
  proven absent): a client submitting many requests each with a distinct forged
  `kid` will trigger one real JWKS fetch to Google/Apple per request. This is
  already bounded by the endpoint's existing IP-keyed rate limit
  (10 requests/minute per `06_SECURITY.md`), so it is **not** a must-fix, but
  is a legitimate hardening follow-up (e.g. a short negative-cache TTL for
  recently-proven-absent `kid` values) worth a future ticket, not this story.

### 5. Rate limiting — PASS, genuinely wired

`backend/app/modules/identity/api.py`: `POST /google` carries
`dependencies=[Depends(_google_sign_in_rate_limiter)]` and `POST /apple` carries
`dependencies=[Depends(_apple_sign_in_rate_limiter)]`, both real
`RateLimitDependency(limit=AUTH_RATE_LIMIT_PER_MINUTE=10, window_seconds=60, key_by="ip")`
instances (`app/core/constants.py`) — not just documented in a docstring/response
description, actually enforced on the route.

### 6. Secrets/logging — PASS, no leakage found

Grepped `backend/app/modules/identity/` and `backend/app/core/` for every
logging call: no call site logs an ID token, its claims, or the generated JWT at
any level. `business_exception_handler` (`app/core/exceptions/handlers.py`)
logs only `exc.message` at WARNING — for `InvalidIdentityTokenError` this is
always the fixed generic string ("We couldn't verify your sign-in. Please try
again."), never the raw token or a specific failure reason.
`unexpected_exception_handler` logs a fixed string plus `exc_info`/request
method/path at ERROR — no request body (and therefore no token) is included.

### 7. New dependencies vs `docs/AI/12_TECH_STACK.md` — legitimate additions, doc currency gap confirmed

`google_sign_in: ^7.2.0` / `sign_in_with_apple: ^8.2.0` (`mobile/pubspec.yaml`)
and `httpx>=0.28.1` promoted to `[project.dependencies]` (`backend/pyproject.toml`)
are all legitimate: no duplicate HTTP client, no duplicate OAuth/JWT library
introduced (`python-jose` reused, per Decision 3/4), neither package appears on
`12_TECH_STACK.md`'s "Packages Requiring Approval" deny-list, and both were
explicitly user-approved before implementation per this Checkpoint's own
"Current Task" section. However, `12_TECH_STACK.md`'s "Approved Flutter
Packages" list does not yet list `google_sign_in`/`sign_in_with_apple`, and its
"Approved Python Packages" list has never listed `httpx` even though it is now
a runtime (not dev-only) dependency. Same write-boundary situation as item 3 —
flagged for `tech-lead`, not actioned by me.

### 8. Mobile Feature-First structure — PASS, no hardcoded strings/colors, consistent with AUTH-001

- `mobile/lib/features/auth/state/oauth_sign_in_controller.dart`: separate
  `StateNotifier`/`Provider` from `phone_entry_controller.dart`, correct SRP
  split, same pattern AUTH-001 established.
- `mobile/lib/features/auth/data/auth_repository.dart`: `signInWithGoogle()`/
  `signInWithApple()` follow the exact same Dio-call → `_mapOAuthError` →
  plain-language `AuthException` pattern as the existing OTP methods; no raw
  status code, backend message, or exception string ever crosses the
  repository boundary (confirmed by reading `_mapOAuthError`/`_mapError`
  directly).
- `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart`'s
  new `_OAuthOptionButton`: all copy via `AppLocalizations`
  (`l10n.continueWithGoogle`/`continueWithApple`), all spacing via
  `AppSpacing` constants, button styling via the existing themed
  `OutlinedButton` (no `Color(0x...)`/`Colors.*` literals). Confirmed via
  direct grep of the file.
- `mobile/lib/features/auth/domain/models/auth_exception.dart`: new
  `AuthErrorType.identityVerificationFailed` and `OAuthCancelledException`
  follow the existing coarse-grained, non-revealing error-type pattern
  established by AUTH-001 (FU-3) — no new duplicate error-modeling
  abstraction introduced.

### Other confirmed observations (non-blocking)

- Root `.env.example` still lacks `GOOGLE_OAUTH_CLIENT_ID=`/
  `APPLE_OAUTH_CLIENT_IDS=` placeholder lines (confirmed by inspection) — a
  pre-device-testing/deployment prerequisite, not a blocker for this review or
  for automated-test-based sign-off.
- `docs/AI/09_DECISIONS.md` contains only foundational/strategic ADRs (ADR-001
  through ADR-011); it has never recorded story-level schema/dependency
  decisions for AUTH-001 either, so AUTH-002 following the same precedent
  (recording its decisions in the Plan file instead) is consistent with
  existing project practice, not a new gap. Not flagged as an action item.

### Must-fix vs nice-to-have summary

**Must-fix before story is marked Done (documentation only, owned by `tech-lead`, no re-review of code needed once done):**
1. `docs/AI/04_DATABASE.md` — update the `users` table constraint list:
   `uq_users_email` → `uq_users_email_provider` on `(auth_provider, email)`.
2. `docs/AI/12_TECH_STACK.md` — add `google_sign_in`/`sign_in_with_apple` to
   "Approved Flutter Packages" and `httpx` to "Approved Python Packages".

**Nice-to-have (future hardening/follow-up, not required for this story's sign-off):**
3. Add a short negative-cache TTL (or minimum refetch interval) to
   `JwksIdTokenVerifier._get_key` so a stream of requests with distinct forged
   `kid` values can't each force a real JWKS fetch — currently bounded only by
   the endpoint's existing 10/min IP rate limit, which is adequate defense in
   depth but not a dedicated control.
4. Root `.env.example` — add `GOOGLE_OAUTH_CLIENT_ID=`/`APPLE_OAUTH_CLIENT_IDS=`
   placeholder lines (external credential prerequisite, already known/tracked).
5. Optionally update `Plan_S02_AUTH-002.md`'s "Backend — Proposed Changes" >
   "API" section to describe the DI wiring actually implemented (sibling
   dependencies in the API layer, not `OAuthService` injected into
   `AuthService`'s constructor), so the Plan and the shipped code narrate the
   same design for future readers.

No item above required looping this story back to `backend` or `frontend` —
there is no code-level architecture, security, or coding-standards violation.

---

## Tester Verification Results (this pass)

Independently re-ran every suite from a clean shell (did not just trust the
backend/frontend self-reports) and read the actual test bodies/response
payloads for the ACs most likely to be rubber-stamped (AC5/AC9, AC6, AC7,
AC8), plus the flagged `AuthService`/`OAuthService` wiring deviation.

### Suite results (re-run independently)

- **Backend** (`cd backend && uv run pytest -v`): **156/156 passed**, 0
  failures, 0 skips. Matches the backend agent's self-report.
  - `uv run ruff check`: clean ("All checks passed!").
  - `uv run ruff format --check`: clean ("87 files already formatted").
  - Migration reversibility, run against a real local Postgres
    (`ai_marketplace_test`, `dumbo` role): `alembic upgrade head` (base →
    `101b27d7096b` → `19249fb61ae8` → `be1f79b6fa2a`) → `alembic downgrade
    -1` (back to `19249fb61ae8`, confirmed `uq_users_email` — the old
    index — is restored via `\di identity.*`) → `alembic upgrade head`
    (confirmed `uq_users_email_provider` — the new index — is restored).
    All three steps succeeded cleanly. Database left at `downgrade base`
    afterward (clean state, matching how the backend agent left it).
- **Mobile** (`cd mobile && flutter test`): **27/27 passed**, 0 failures,
  0 skips. Matches the frontend agent's self-report.
  - `flutter analyze`: "No issues found!"
  - `dart format --output=none --set-exit-if-changed lib test`: clean, 0
    files needed reformatting (exit 0).

### Per-AC verdicts

1. **PASS** — `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart`
   renders real, tappable `_OAuthOptionButton`s for Google/Apple (wired to
   `OAuthSignInController`) alongside the existing mobile-number path.
   Covered by `mobile/test/features/auth/oauth_sign_in_test.dart`
   (`"Google and Apple buttons render enabled, not \"coming soon\""`) and
   the updated `mobile/test/features/auth/phone_entry_screen_test.dart`
   assertion (`google.onPressed`/`apple.onPressed` now `isNotNull`).
2. **PASS** — `backend/app/modules/identity/services/id_token_verifier.py`'s
   `JwksIdTokenVerifier` fetches each provider's real JWKS URL (Google/Apple
   constants in `dependencies.py`), verifies RS256 signature against the
   fetched public key, and checks `iss`/`exp`/`aud`. Read
   `backend/app/modules/identity/api.py`'s `_sign_in_with_oauth` directly:
   it calls `oauth_service.verify_identity(...)` (line 183) and only passes
   the resulting *already-verified* `IdentityClaims` to
   `auth_service.authenticate_with_oauth(...)` (line 184) if verification
   didn't raise. Grepped for all callers of `authenticate_with_oauth` in
   `app/` — the only production call site is this one, always preceded by
   verification with no bypassing branch. Covered by
   `backend/tests/modules/identity/test_id_token_verifier.py` (signature/
   issuer/audience/expiry all independently tested against a real RSA
   keypair) and the endpoint-level tests below.
3. **PASS** — `test_auth_service.py::TestAuthenticateWithOauth::test_new_pair_creates_user_and_assigns_customer_role`
   (unit) and `test_auth_endpoints.py::TestGoogleSignIn/TestAppleSignIn::test_new_subject_creates_user_with_customer_role`
   (integration) both assert a new DB row with the `customer` role.
4. **PASS** — `test_auth_service.py::test_existing_pair_authenticates_without_duplicating`
   and the endpoint-level `test_existing_subject_authenticates_without_duplicate`
   (Google + Apple) assert the same `user_id` is returned on a second call
   and exactly one DB row exists.
5. **PASS** — `test_identity_models.py::test_duplicate_email_different_provider_is_allowed`
   confirms the DB constraint (`uq_users_email_provider`, scoped to
   `(auth_provider, email)`) permits two rows with the same email under
   different providers, and directly queries for `len(...) == 2`.
   `test_auth_endpoints.py::TestOauthCrossProviderSameEmail::test_same_email_different_provider_creates_two_distinct_users`
   confirms this end-to-end via a **direct SQL query**
   (`SELECT id, auth_provider FROM identity.users WHERE email = :email`),
   asserting exactly 2 rows, one per provider, with 2 distinct `id`s — not
   merely inferred from two successful API responses. `authenticate_with_oauth`
   is keyed only on `(auth_provider, external_auth_subject)`, never email
   (confirmed by `test_looks_up_users_by_provider_and_subject_not_email`),
   so no merge/link logic exists to accidentally trigger.
6. **PASS** — Read the actual HTTP response bodies asserted in
   `test_auth_endpoints.py`: tampered, expired, and wrong-audience Google
   tokens, and a tampered Apple token, all return **status 401** with the
   **exact same message string** (`"We couldn't verify your sign-in.
   Please try again."`), with an explicit `assert "signature" not in
   body["message"].lower()` guard against detail leakage. Root cause of
   the failure is never distinguishable from the response. Also confirmed
   `test_oauth_service.py::test_any_other_verifier_exception_is_wrapped_generically`
   — even an unexpected internal exception (`ValueError("some internal
   detail")`) is collapsed to the same generic error, with an explicit
   assertion that the internal detail string does not leak into the
   exception message.
7. **PASS** — Read `mobile/lib/features/auth/state/oauth_sign_in_controller.dart`:
   on `OAuthCancelledException`, state resets to `const OAuthSignInState()`
   (clears both `loadingProvider` and `error`). The test
   (`oauth_sign_in_test.dart`, "cancelling Google/Apple sign-in resets to
   idle with no error shown and no navigation") explicitly asserts
   `find.byType(AppErrorMessage), findsNothing` (no error message, not
   merely "no crash"), that the Google button's `onPressed` is `isNotNull`
   again (loading state genuinely reset, button re-enabled), and
   `find.byType(HomePlaceholderScreen), findsNothing` (no accidental
   navigation). This is a materially stronger check than "didn't throw."
8. **PASS** — Grepped the entire backend tree for `googleapis.com`/
   `appleid.apple.com`: the only occurrences are (a) the production
   constants in `dependencies.py` (never reached by tests — both verifier
   dependencies are overridden via `app.dependency_overrides` in the
   `client` fixture), and (b) test code reusing those same URL *strings*
   purely as the key the `httpx.MockTransport`-backed `JwksTestServer` is
   bound to (`tests/support/id_token_factory.py`) — no `httpx.AsyncClient`
   in any test is constructed without an injected `MockTransport`, so no
   test can reach a real host even accidentally; `JwksTestServer` 404s
   anything not matching its exact configured URL as a defensive guard.
   On mobile, `oauth_sign_in_test.dart` overrides `authRepositoryProvider`
   with `FakeAuthRepository`, which fully replaces `AuthRepository` (the
   only place `google_sign_in`/`sign_in_with_apple` plugin calls live) —
   the real plugins are never invoked by any test.
9. **PASS** — See AC5 above; the same test
   (`test_same_email_different_provider_creates_two_distinct_users`) is
   the AC9-designated test and performs the required direct-SQL check for
   two distinct `identity.users` rows.

### Regression check (AUTH-001)

Diffed every modified test file against the last commit (`git diff HEAD`)
to check for weakened/deleted assertions, not just "still passes":
- `test_auth_endpoints.py`, `test_auth_service.py`: additive only — no
  existing line was removed except docstring/import housekeeping.
- `test_identity_models.py`: one test renamed
  (`test_duplicate_email_violates_unique_constraint` →
  `test_duplicate_email_same_provider_violates_unique_constraint`) and its
  `match=` string updated from `"uq_users_email"` to
  `"uq_users_email_provider"` — this is the expected, approved
  consequence of Decision 2's constraint rename, not a weakening; the
  test still asserts the same-provider duplicate-email case is still
  blocked.
- `mobile/test/features/auth/phone_entry_screen_test.dart`: one assertion
  flipped from `google.onPressed`/`apple.onPressed` being `isNull`
  (disabled) to `isNotNull` (enabled) — this is AC1's explicit,
  intentional behavior change for this story (AUTH-001 shipped these
  buttons disabled on purpose, commented "wired in AUTH-002"), not a
  hidden weakening.
- `mobile/test/features/auth/fakes/fake_auth_repository.dart`: additive
  only (new configurable error fields/call counts for the OAuth methods).
- Full backend (156/156) and mobile (27/27) suites include all AUTH-001
  tests unmodified in behavior and passing.

### Architectural deviation sanity check

The backend agent flagged that `AuthService.authenticate_with_oauth`
takes pre-verified `IdentityClaims` rather than having `OAuthService`
injected into `AuthService`'s constructor. Read
`backend/app/modules/identity/api.py` directly: the only production
caller of `authenticate_with_oauth` is `_sign_in_with_oauth`, which always
calls `oauth_service.verify_identity(provider, payload.id_token)` first
and only reaches `authenticate_with_oauth` with the result if that call
did not raise. There is no code path — in `api.py` or anywhere else in
`app/` — that calls `authenticate_with_oauth` with unverified claims.
**Conclusion: no behavioral gap.** AC2 ("no token trusted without
verification") is enforced by the real call sequence, not merely by test
mocks. This remains something `architect` may still want to comment on
from a pure DI-pattern-consistency standpoint (it doesn't match
`get_auth_service()`'s literal wording in the Plan), but it is not a
testable-AC failure.

### Other notes (non-blocking, not part of the 9 ACs)

- Confirmed (as already flagged by both engineering agents) that
  `docs/AI/04_DATABASE.md`, `docs/AI/12_TECH_STACK.md`, and the root
  `.env.example` still need follow-up updates (constraint rename, new
  approved Flutter packages, OAuth env placeholders respectively) — out
  of `tester`'s write boundary, carried forward as-is.
- Confirmed no `sessions`/`refresh_tokens`/`customer_profiles`/
  `customer_preferences` table or row is introduced anywhere in the
  identity module's changed files (grep for those terms in
  `app/modules/identity/` only turns up explanatory comments stating they
  are intentionally absent).

## What's Explicitly Next

1. `architect` agent — review the schema-change migration against
   `04_DATABASE.md`, ID-token verification design against
   `06_SECURITY.md`/OWASP JWT guidance, Clean Architecture layering, the
   `AuthService`/`OAuthService` wiring deviation (see tester's sanity
   check above — no behavioral gap found, but architect may still weigh
   in on DI-pattern consistency), and the mobile additions against
   `08_CODING_STANDARDS.md`/`12_TECH_STACK.md`.
2. Orchestrator: once architect is clean, pause for user sign-off before
   `tech-lead` writes `Walkthrough_S02_AUTH-002.md` or touches the
   changelog/tracker.

---

## Current Task

Implement the backend half of AUTH-002 per `docs/implementation/plans/Plan_S02_AUTH-002.md` and
`docs/implementation/prompts/Prompt_S02_AUTH-002.md`. Both decisions requiring user sign-off
(schema change to `uq_users_email_provider`; promoting `httpx` to a runtime dependency) were
pre-approved by the user before this session started.

## What's Done (backend, complete)

- **Migration**: `backend/alembic/versions/2026_08_29_1000-be1f79b6fa2a_identity_email_uniqueness_per_provider.py`
  drops `uq_users_email`, creates `uq_users_email_provider` on `(auth_provider, email)` partial
  unique. Verified upgrade (base → head), downgrade (-1 and full to base), and re-upgrade all work
  cleanly against a real Postgres test database.
- **Model**: `backend/app/modules/identity/models.py` — renamed/rescoped the matching `Index`.
- **Dependency**: `backend/pyproject.toml` — `httpx` moved from `[dependency-groups].dev` to
  `[project.dependencies]`; `uv sync` run, lockfile updated.
- **Config**: `backend/app/core/config.py` — added required `GOOGLE_OAUTH_CLIENT_ID: str` and
  `APPLE_OAUTH_CLIENT_IDS: list[str] | str` (comma/JSON parsing shared with `ALLOWED_ORIGINS` via
  a new `_parse_comma_separated_or_json_list` helper), both startup-validated (required fields +
  non-empty validators). `backend/tests/conftest.py` sets test placeholder values for both.
  **Not done / out of my write scope**: the root `.env.example` (lives outside `backend/`) still
  needs `GOOGLE_OAUTH_CLIENT_ID=`/`APPLE_OAUTH_CLIENT_IDS=` placeholder lines added — flagged for
  the tech-lead/orchestrator, not actioned here (boundary: backend agent may only touch `backend/`).
- **ID token verification**: `backend/app/modules/identity/services/id_token_verifier.py`
  (`IdentityClaims`, `IdTokenVerifier` ABC, `JwksIdTokenVerifier` — JWKS fetch via injected
  `httpx.AsyncClient`, `kid`-keyed in-memory cache with single-refetch-on-miss, `python-jose` RS256
  verification of `iss`/`aud`/`exp`; audience checked manually against a *set* since Apple needs
  more than one accepted value).
- **OAuth orchestration**: `backend/app/modules/identity/services/oauth_service.py`
  (`OAuthService` — routes to the right verifier per `AuthProvider`, collapses any failure into
  `InvalidIdentityTokenError`).
- **Repository**: `backend/app/modules/identity/repositories/user_repository.py` —
  `get_by_provider_and_subject`.
- **Service**: `backend/app/modules/identity/services/auth_service.py` —
  `authenticate_with_oauth(provider, claims)`, mirrors `verify_otp_and_authenticate`; email/
  `email_verified_at` written only at creation, never overwritten on re-login.
- **Schema**: `backend/app/modules/identity/schemas.py` — `OAuthSignInRequest`.
- **Exception**: `backend/app/core/exceptions/exceptions.py` +
  `backend/app/core/exceptions/__init__.py` — `InvalidIdentityTokenError` (401, generic message).
- **Endpoints**: `backend/app/modules/identity/api.py` — `POST /google`, `POST /apple`, both
  rate-limited (IP-keyed, same bucket as OTP endpoints), both `SuccessResponse[AuthTokenResponse]`.
- **DI wiring**: `backend/app/modules/identity/dependencies.py` — `get_google_id_token_verifier`,
  `get_apple_id_token_verifier` (module-level singleton verifiers, so the JWKS cache persists
  across requests), `get_oauth_service`. Deliberately did **not** inject `OAuthService` into
  `AuthService`'s constructor (Decision 5's method signature is `authenticate_with_oauth(provider,
  claims)` — already-verified claims; the API layer calls `OAuthService.verify_identity` first,
  then `AuthService.authenticate_with_oauth`). Flagged as a deliberate deviation from the Plan's
  literal "extend get_auth_service()'s dependency chain" wording, for architect review.
- **Tests** (all passing, 156/156 total suite, 0 regressions):
  - `backend/tests/support/id_token_factory.py` (new) — `IdTokenFactory` (RSA keypair, signs test
    tokens), `JwksTestServer` (serves JWKS via `httpx.MockTransport`, request-counting).
  - `backend/tests/modules/identity/test_id_token_verifier.py` (new, 13 tests) — valid/tampered/
    expired/wrong-audience/wrong-issuer/malformed/missing-kid/unknown-kid-refetch/cached-key/
    JWKS-fetch-failure/multi-audience-accept.
  - `backend/tests/modules/identity/test_oauth_service.py` (new, 5 tests) — provider routing,
    generic-failure wrapping (including non-`InvalidIdentityTokenError` exceptions).
  - `backend/tests/modules/identity/test_auth_service.py` (extended, +4 tests) — new pair creates
    User+role; existing pair no duplicate; email not overwritten; lookup keyed on
    provider+subject not email.
  - `backend/tests/modules/identity/test_auth_endpoints.py` (extended, +11 tests) — both endpoints
    end-to-end (new/existing subject, tampered/expired/wrong-audience → generic 401), explicit
    AC9 direct-SQL two-distinct-rows check.
  - `backend/tests/modules/identity/test_identity_models.py` (extended, +1 test, renamed 1) —
    model-level confirmation that same-provider duplicate email is still blocked and
    different-provider duplicate email is now allowed.
- **Verification run**: `pytest` 156/156 pass; `ruff check` clean; `ruff format --check` clean;
  migration upgrade → downgrade -1 → upgrade → downgrade base all verified against a real local
  Postgres test database (`ai_marketplace_test`), left in a clean base state afterward.

## What's Done (mobile, complete)

- **Dependencies**: `mobile/pubspec.yaml` — added `google_sign_in: ^7.2.0` and
  `sign_in_with_apple: ^8.2.0` (current stable versions at implementation time, confirmed via
  pub.dev; both compatible with the installed Flutter 3.44.4/Dart 3.12.2 SDK). `flutter pub get`
  run, `pubspec.lock` updated. Verified the actual installed API surface against each package's
  README/CHANGELOG/source directly (not assumed) since `google_sign_in` 7.x is a breaking rewrite
  from 6.x (singleton `GoogleSignIn.instance`, explicit `initialize()`, `authenticate()` throwing
  `GoogleSignInException`/`GoogleSignInExceptionCode.canceled` on cancellation) —
  `sign_in_with_apple`'s `SignInWithAppleAuthorizationException`/
  `AuthorizationErrorCode.canceled` matched the Plan's assumption as written.
- **Config**: `mobile/lib/core/network/oauth_config.dart` (new) — `OAuthConfig`, a
  `String.fromEnvironment`-based config (mirrors `ApiConfig`'s pattern) for
  `googleServerClientId`/`appleServiceId`/`appleRedirectUri`. All blank by default; `AuthRepository`
  treats blank as "not configured" and behaves accordingly (`serverClientId: null`, Apple
  `webAuthenticationOptions: null` — iOS/macOS native flow is unaffected by either being blank).
  Real values are the same external Google Cloud Console/Apple Developer Portal prerequisite the
  Plan already flagged — not available in this pass, not needed for automated tests.
- **Domain**: `mobile/lib/features/auth/domain/models/auth_exception.dart` — added
  `AuthErrorType.identityVerificationFailed` (localized AC6 copy) and a new sibling class
  `OAuthCancelledException` (deliberately **not** an `AuthErrorType`/`AuthException` value, so
  cancellation can never accidentally render error copy — Plan Decision 13).
  `docs/AI/06_SECURITY.md` needs no update — no new error-messaging *pattern*, just a new
  instance of the existing one.
  `docs/AI/09_DECISIONS.md` is outside my write boundary (root `.agents/agents.md` restricts me to
  `mobile/`); the two user-approved decisions (schema change, new Flutter deps) are already
  recorded in the Plan and this checkpoint — flagged as a follow-up doc note only, not actioned.
- **Repository**: `mobile/lib/features/auth/data/auth_repository.dart` — added
  `signInWithGoogle()`/`signInWithApple()`. Each obtains a provider ID token via the respective
  plugin's native flow, then exchanges it via `POST /auth/google`/`POST /auth/apple`, returning the
  same `AuthToken` shape `verifyOtp()` already returns (no new domain model). Plugin cancellation
  signals map to `OAuthCancelledException`; every other native-plugin failure or backend rejection
  (401 `InvalidIdentityTokenError`) maps to `AuthException(type: identityVerificationFailed)`; 429
  reuses `tooManyAttempts` (same rate-limit bucket as OTP); network/unknown reuse the existing
  types. `GoogleSignIn.instance.initialize()` is called lazily, exactly once, guarded by a private
  flag.
- **State**: `mobile/lib/features/auth/state/oauth_sign_in_controller.dart` (new) —
  `OAuthSignInController` (`StateNotifier<OAuthSignInState>`), separate from
  `phone_entry_controller.dart` per SRP. Tracks which provider (if any) is loading;
  `signInWithGoogle()`/`signInWithApple()` return the `AuthToken` on success, `null` on
  cancellation (AC7, state reset to fully idle, no error) or failure (state carries the
  `AuthException`, rendered via the existing `auth_error_copy.dart`).
- **Screen**: `mobile/lib/features/auth/presentation/screens/phone_entry_screen.dart` — replaced
  `_DisabledAuthOption` with a real, tappable `_OAuthOptionButton` (AC1): shows a per-button loading
  spinner, disables both OAuth buttons while either is in flight, shows the localized error inline,
  and on success populates `authSessionProvider` and navigates to `AppRoutes.homePlaceholder` —
  mirroring `otp_entry_screen.dart`'s existing post-auth pattern exactly. No hardcoded colors/
  strings/spacing: reuses `OutlinedButton`'s existing theme (`app_theme.dart`, DESIGN.md
  `button-outlined`), `LoadingIndicator`/`AppErrorMessage` shared widgets, and `AppSpacing`
  constants throughout.
- **Localization**: added `identityVerificationFailedMessage` to `mobile/lib/l10n/app_en.arb` and
  `app_ar.arb` (English: "We couldn't verify your sign-in. Please try again."; Arabic translation
  provided). `continueWithGoogle`/`continueWithApple` reused as-is, not duplicated, per the Plan.
  Ran `flutter gen-l10n` to regenerate `AppLocalizations`.
- **Tests**:
  - `mobile/test/features/auth/fakes/fake_auth_repository.dart` (extended) — added
    `signInWithGoogleError`/`signInWithAppleError` (accept any `Object`, so a test can configure
    either an `AuthException` or an `OAuthCancelledException`) and matching call-count fields.
  - `mobile/test/features/auth/oauth_sign_in_test.dart` (new, 7 tests) — buttons render enabled
    (AC1); successful Google/Apple sign-in navigates to the home placeholder and populates
    `authSessionProvider`; Google/Apple cancellation resets to idle with no `AppErrorMessage` shown
    and no navigation (AC7); Google/Apple generic failure shows the localized
    `identityVerificationFailedMessage` copy only, never a raw status code/exception string (AC6).
  - `mobile/test/features/auth/phone_entry_screen_test.dart` (modified) — the old
    "Google and Apple render disabled" assertion (now false under AUTH-002) was updated to assert
    they render **enabled** and that "Coming soon" no longer appears, so the suite stays internally
    consistent rather than leaving a contradictory, failing assertion in place.
- **Verification run** (from `mobile/`): `flutter pub get` clean; `flutter gen-l10n` regenerated
  localizations; `flutter analyze` — **no issues found**; `flutter test` — **27/27 passed, 0
  failures, 0 skips** (full suite, including all pre-existing AUTH-001 widget tests — no
  regression); `dart format --output=none --set-exit-if-changed lib test` — clean (one file was
  reformatted and re-verified clean after).
- **Platform-native configuration — explicitly not done, as flagged by the Plan as an external
  prerequisite not available at implementation time**: iOS `Info.plist`/entitlements (Sign in with
  Apple capability, Google reversed-client-id URL scheme), Android
  `AndroidManifest.xml`/`build.gradle` entries, and real Google Cloud Console/Apple Developer
  Portal credential values are **not configured**. `flutter pub get` did auto-regenerate
  `macos/Flutter/GeneratedPluginRegistrant.swift` to register the two new plugins (a normal,
  automatic build artifact, not manual platform config) — the iOS/Android equivalents
  (`GeneratedPluginRegistrant.h/.m`, `GeneratedPluginRegistrant.java`) will similarly regenerate
  the next time those platforms are built/run, which did not happen in this pass (no Xcode/Android
  SDK build was performed or required for `flutter test`/`flutter analyze`). None of this blocks
  the automated test suite (Decision 14's mobile-side mirror: fakes/mocks at the repository layer)
  — it only blocks real-device Google/Apple sign-in testing, exactly as the Plan anticipated.

## What's Explicitly Next

1. **`tester` agent** — verify all 9 ACs individually now that both backend and mobile are done;
   re-run full backend regression and the full `flutter test` suite.
2. **`architect` agent** — review the schema-change migration against `04_DATABASE.md`, the
   ID-token verification design against `06_SECURITY.md`/OWASP JWT guidance, Clean Architecture
   layering of the three new/changed backend services, the `AuthService`/`OAuthService` wiring
   deviation noted above, and the mobile-side `OAuthSignInController`/`AuthRepository` additions
   against `08_CODING_STANDARDS.md`'s Feature-First/SRP conventions and the two new Flutter
   dependencies against `12_TECH_STACK.md`.
3. Orchestrator: once tester + architect are clean, pause for user sign-off before
   `tech-lead` writes `Walkthrough_S02_AUTH-002.md` or touches the changelog/tracker.

## Open Questions / Notes for Next Agent

- `docs/AI/04_DATABASE.md` line ~170 still documents `uq_users_email` (old, now-removed
  constraint name) — needs a follow-up doc update by whoever holds `docs/AI/` write access.
  `05_API_GUIDELINES.md`/`06_SECURITY.md` don't need changes (no new endpoint pattern, rate-limit
  approach, or auth-failure-messaging pattern was introduced beyond what AUTH-001 already
  documents).
- Root `.env.example` (outside `backend/`) needs `GOOGLE_OAUTH_CLIENT_ID=`/
  `APPLE_OAUTH_CLIENT_IDS=` placeholder lines added by whoever owns that file.
- Real Google/Apple credentials (Web OAuth Client ID, Apple Bundle ID/Services ID) are still
  needed before any real-device testing — out of scope for both backend and mobile automated
  tests (Decision 14), but a prerequisite the user must supply before Sprint sign-off if
  real-device verification is desired.
- `docs/AI/12_TECH_STACK.md`'s "Approved Flutter Packages" list does not yet include
  `google_sign_in`/`sign_in_with_apple` (Plan Decision 8, user-approved for this story) — needs a
  follow-up doc update by whoever holds `docs/AI/` write access; out of my (`frontend`) write
  boundary (`mobile/` only).
- iOS `Info.plist`/entitlements, Android `AndroidManifest.xml`, and the real Google/Apple
  credential values referenced by `mobile/lib/core/network/oauth_config.dart`
  (`GOOGLE_OAUTH_SERVER_CLIENT_ID`, `APPLE_OAUTH_SERVICE_ID`, `APPLE_OAUTH_REDIRECT_URI`
  `--dart-define` values) are still needed before real-device Google/Apple sign-in can be
  exercised — the Dart/Flutter code and its automated tests do not depend on them (fakes/mocks at
  the repository layer), consistent with the Plan's "Platform configuration" note.
