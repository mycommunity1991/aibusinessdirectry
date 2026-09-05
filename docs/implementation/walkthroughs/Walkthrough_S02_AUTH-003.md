# Walkthrough S02 AUTH-003

## Story: Stay Signed In and Manage Active Sessions

**Sprint:** 02 | **Story ID:** AUTH-003 | **Priority:** High | **Status:** Done

As an authenticated user, I want to remain signed in securely across app restarts and see/manage my active
sessions, so that I stay logged in conveniently while retaining control if a device is lost or compromised.

This story is where the "stateless-first" precedent AUTH-001/AUTH-002 established changes: both of those
stories issued one stateless JWT access token with no refresh mechanism and no `sessions`/`refresh_tokens`/
`devices` row. AUTH-003 introduces statefulness (revocability) into that scheme — a device is recorded per
login, a session tracks a rotation chain of refresh tokens, and access tokens stay short-lived and carry no
PII.

Full context, architecture decisions, and file-by-file scope: `docs/implementation/plans/Plan_S02_AUTH-003.md`
(see that plan's Supersession Notice — it replaced a stale slice of the old, superseded 9-story Sprint 2
backlog).

---

## What was implemented

### Backend (`backend/app/modules/identity/`, `backend/app/core/`, `backend/app/api/`)

- **Migration** — `backend/alembic/versions/2026_09_05_1000-bc69dfa02341_identity_sessions_refresh_tokens.py`
  creates `identity.sessions` and `identity.refresh_tokens`, both linked to `users` (and `sessions` to
  `devices`), exactly matching `04_DATABASE.md`'s already-fixed column-level spec. Verified reversible
  (upgrade → downgrade → upgrade → downgrade-base) against a real local Postgres by both `backend` and
  `tester`, independently.
- **JWT payload narrowed** — `create_access_token(subject, roles, jti, expires_delta=None)` now encodes
  exactly `{sub, exp, iat, jti, roles}` — no email or phone number ever reaches the token. Default expiry
  shortened `30` → `15` minutes (`Settings.ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Refresh tokens** — opaque (`secrets.token_urlsafe(32)`), only their SHA-256 hash is persisted
  (`generate_refresh_token`/`hash_refresh_token` in `app/core/security.py`) — deliberately not Argon2id, since
  a 256-bit random value has no brute-force surface to slow down.
- **`SessionService`** (new, `services/session_service.py`) — owns device/session/refresh-token lifecycle,
  separate from `AuthService` (same separation-of-concerns precedent as `OAuthService`/`AuthService` in
  AUTH-002): `start_session` (called from both login paths), `refresh` (rotation, with a reuse-detection
  cascade — replaying an already-rotated/revoked token revokes the *entire* session, not just that call),
  `list_active_sessions` (flags the caller's current session), `revoke_session` (404 for both "not found" and
  "not yours"), `revoke_all_sessions` (optional `keep_current`). Backed by three new repositories
  (`DeviceRepository`, `SessionRepository`, `RefreshTokenRepository`).
- **`AuthService`** — `verify_otp_and_authenticate` and `authenticate_with_oauth` now accept
  `device_platform`/`device_name`/`ip_address`/`user_agent` and delegate token/session/device creation to an
  injected `SessionService`, returning `(user, access_token, refresh_token, roles)`.
- **API** — `verify-otp`/`google`/`apple` now require a `device` field and return a `refresh_token` alongside
  the existing `access_token`. New endpoints: `POST /auth/refresh` (rotation), `GET /auth/sessions` (lists
  device name/platform/last-seen, flags current — deliberately unpaginated, see Important Decisions),
  `DELETE /auth/sessions/{session_id}`, `POST /auth/sessions/logout-all` (`keep_current` flag).
- **`get_current_user`** (`app/api/dependencies.py`) — replaced the BF-011 placeholder that unconditionally
  raised. Now a real implementation: decodes the JWT, returns `CurrentUser(id, session_id, roles)`
  (`session_id` = the token's `jti`); missing/malformed claims raise `InvalidTokenError`. Does not consult
  session/revocation state (see Important Decisions — the documented access-token-revocation trade-off).
- **Bug fixed during implementation** — `request.client.host` under Starlette's `TestClient` is the literal
  string `"testclient"`, not a real IP, which the `sessions.ip_address` `INET` column rejects outright. Fixed
  by validating the host with `ipaddress.ip_address(...)` in `_client_context()` and falling back to `None`
  if it doesn't parse — a real, permanent fix (a production deployment behind a misconfigured proxy could hit
  the same DB error), not test-only scaffolding.
- **Tests** — `test_session_service.py` (new), extended `test_security.py`, `test_auth_service.py`,
  `test_auth_endpoints.py`, `test_identity_models.py`, `test_dependencies.py`. **192 tests passing** (full
  suite, 0 regressions on AUTH-001/AUTH-002), `ruff check`/`ruff format --check` clean.

### Mobile (`mobile/lib/`)

- **Domain** — `AuthToken` gained a required `refreshToken` field and a `toJson()` (for secure-storage
  round-tripping); new `DeviceContext` model derives `device_platform`/`device_name` from `dart:io Platform`
  only — no new package.
- **Storage** — `SecureTokenStorage` (new) wraps the previously-added-but-unused `flutter_secure_storage`
  dependency, persisting the whole `AuthToken` as one JSON blob.
- **Networking** — `AuthInterceptor` (new): attaches `Authorization: Bearer <access_token>` to every request;
  on a 401, calls `POST /auth/refresh` via a separate interceptor-free `Dio` instance, persists the new pair,
  retries the original request once (guarded against a second retry loop), and clears the local session on
  refresh failure. A deliberate, documented exception to "`core/` never depends on `features/`" — every
  authenticated request needs session awareness.
- **Feature: Auth** — `verifyOtp`/`_exchangeIdToken` now send `device: DeviceContext.current().toJson()`.
  Added `AuthRepository.refresh()` and `logout()` (decodes the access token's own `jti` client-side, no
  signature verification, only to label "my own session"; best-effort, never blocks local logout).
  `AuthSessionController` (new) is the single place in-memory session state and `SecureTokenStorage`'s
  persisted copy stay in sync. `SplashScreen` now reads persisted storage on launch and, if present, calls
  `refresh()` once to validate/rotate before routing to Home; any failure clears storage and routes to Phone
  Entry.
- **Feature: Home** — the existing `HomePlaceholderScreen` stub gained a bare "Log out" button (calls
  `logout()`, clears session, routes to Phone Entry). No new screen was built (see Important Decisions).
- **Localization** — `logOutLabel` added to `app_en.arb`/`app_ar.arb`.
- **Tests** — `session_persistence_test.dart` (new, 3 splash-restart scenarios), `home_placeholder_screen_test.dart`
  (new), extended fakes/`test_helpers.dart`. **30 tests passing**, `flutter analyze` clean, `dart format`
  clean.

---

## Acceptance Criteria — Verification

All 11 acceptance criteria (from `Plan_S02_AUTH-003.md`, sourced from the Tracker) were independently verified
by the `tester` agent — re-running every suite from a clean shell, reading the actual bodies of the highest-
risk tests (the AC11 trio and the AC2 exact-payload assertion) rather than trusting either engineering agent's
self-report, and independently re-deriving the migration's up/down/up reversibility against a real local
Postgres. All 11 passed.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `sessions`/`refresh_tokens`/`devices` tables exist via migration, linked to `users` | Pass |
| 2 | Login issues a 15-min JWT containing only `sub`, `exp`, `iat`, `jti`, `roles` — no email/phone | Pass |
| 3 | Refresh token is opaque random string; only its hash is persisted | Pass |
| 4 | Valid refresh rotates: new pair issued, old refresh token invalidated | Pass |
| 5 | Already-used (rotated-away) or revoked refresh token rejected | Pass |
| 6 | Device row created/updated on login, capturing platform and device name | Pass |
| 7 | `GET /sessions` lists device name/platform/last-seen, flags the current session | Pass |
| 8 | `DELETE` on a session revokes its refresh tokens; subsequent refresh fails | Pass |
| 9 | "Log out everywhere" revokes all sessions (optionally except current), distinct action | Pass |
| 10 | A user cannot list or revoke another user's sessions (ownership enforced) | Pass |
| 11 | Automated tests explicitly cover rotation, revoke-then-refresh-fails, ownership boundary | Pass |

---

## Important Decisions

- **`jti`-as-session-id design.** AC2 requires the access-token payload to contain *only* `sub`, `exp`, `iat`,
  `jti`, `roles` — no room for a separate `session_id` claim. `jti` is server-set to `str(session.id)` at
  every issuance/rotation, letting `GET /sessions` flag "is this the caller's current session" for free. This
  means every access token minted within one session's lifetime shares the same `jti` (by design). Reviewed
  by `architect` and confirmed sound: `jti` is never client-influenced, so it cannot be forged into colliding
  with another session.
- **Access-token-revocation trade-off (Decision 8).** `get_current_user` decodes/validates the JWT only — it
  never consults session/revocation state. Revoking a session (AC8/AC9) does not immediately invalidate any
  access token already issued under it; that token remains usable for up to its remaining ≤15-minute
  lifetime. This is the standard industry trade-off for a stateless-access-token design with no blocklist
  (the alternative — a Redis blocklist or per-request DB lookup — was explicitly out of scope). `architect`
  confirmed this is an accepted design trade-off, not a defect, adequately mitigated by the short 15-minute
  window.
- **Refresh-token reuse-detection cascade.** Replaying an already-rotated-away or revoked refresh token
  revokes the *entire* session and every refresh token in its chain, not just that one call — a well-known
  defense-in-depth pattern (OWASP-style rotation-with-reuse-detection), confirmed by `architect` to only ever
  make the system more restrictive, never less.
- **Contract change to three already-shipped endpoints — pre-approved by the user before implementation
  started.** `verify-otp`/`google`/`apple` each gained a required `device: { device_platform, device_name }`
  field, and their shared `AuthTokenResponse` gained `refresh_token: string`. `architect` confirmed this
  matches exactly what was approved, no other field changed, `request-otp` (still unauthenticated, no login
  outcome) was correctly left untouched.
- **No new mobile "Manage Sessions" screen this story — pre-approved by the user before implementation
  started.** None of the 11 tracker ACs describe a UI surface for listing/revoking sessions, and
  `15_SCREEN_INVENTORY.md` has no such screen (nor a Profile/Settings screen for one to live inside yet).
  Mobile scope was limited to secure token persistence, silent refresh, splash-screen session recovery, and a
  bare "Log out" action on the existing Home stub. `GET/DELETE/logout-all` are fully built and tested on the
  backend regardless of mobile UI. A follow-up mobile story (a real session-list/management screen) is
  recommended once Profile/Settings (S-14) exists.

---

## Architect Review — Findings and Resolution

The `architect` agent returned **STORY COMPLETE** — no must-fix items, no security defect, no architectural-
boundary violation, no scope creep. Full findings in the (now-deleted) `Checkpoint_S02_AUTH-003.md`; summary
of the seven flagged review items:

1. **`jti`-as-session-id** — confirmed sound (see Important Decisions).
2. **Refresh-token reuse-detection cascade** — confirmed sound, matches OWASP pattern (see Important
   Decisions).
3. **Unpaginated `GET /sessions`** — reasoning agreed with on the merits (a user's realistic session count is
   small and per-owner-bounded, never "thousands"), but flagged as undocumented drift against
   `05_API_GUIDELINES.md`'s blanket "all collection endpoints must support pagination" rule. Recommended
   recording it as a formal ADR rather than leaving it as an inline code comment.
4. **Real `get_current_user`** — confirmed correct, no auth bypass reintroduced; requires a valid Bearer
   token, decodes/validates it fully, never silently accepts a missing/malformed/expired token.
5. **Contract change to the three existing endpoints** — matches exactly what was pre-approved, no scope
   creep.
6. **Mobile `AuthInterceptor` untested gap** — confirmed a real, legitimate coverage gap (not testing-effort
   negligence): `AuthInterceptor` constructs its own internal `_refreshDio` inline with no injection seam, so
   its 401→refresh→retry-once and 401→refresh-fails→clear-session branches cannot currently be given a real,
   dedicated test. Correctly non-blocking for this story (none of the 11 tracker ACs describe this
   interceptor — it's supporting mobile plumbing, per the Plan's own scope boundary), but flagged as a
   tracked follow-up rather than a stray Checkpoint comment.
7. **Pre-existing `config.py` silent-`sys.exit(1)` bug** — confirmed pre-existing (this story's only change
   to that file was the one-line `30`→`15` default), not introduced or worsened by this story. A real
   usability/debuggability bug (any missing required env var fails every process invocation with zero
   diagnostic output), but not a security defect — does not block sign-off.

### Standard review confirmed clean

Module boundaries/Clean Architecture (no cross-module repository access, no business logic in routes),
database (`Session`/`RefreshToken` models match `04_DATABASE.md` column-by-column), no hardcoded
secrets/colors/strings, no unapproved dependency additions (mobile reuses the already-approved
`flutter_secure_storage`; backend adds none), and security review (no PII in the JWT, refresh tokens
correctly SHA-256-hashed not Argon2id, ownership enforcement collapses "not found"/"not yours" into one
non-revealing 404).

---

## Follow-up Notes (non-blocking, tracked for future work)

1. **Mobile `AuthInterceptor` test gap.** Refactor `mobile/lib/core/network/auth_interceptor.dart` to accept
   an injectable `Dio`/`HttpClientAdapter` (defaulting to today's inline construction for production callers)
   so a real interceptor-level test can exercise the 401→refresh→retry-once and
   401→refresh-fails→clear-session paths against a fake adapter. No new package needed.
2. **`backend/app/core/config.py`'s silent `except ValidationError` block.** Builds a `loc` string per
   validation error but never logs/prints it before `sys.exit(1)` — any missing/invalid required env var
   fails every `python -c ...`/`alembic ...` invocation with zero diagnostic output. Pre-existing (predates
   this story), low-risk, worth a quick fix (add a `print`/`logger.error` before `sys.exit`) whenever
   `backend` next touches that file.
3. **Unpaginated `GET /sessions` as a recorded pattern.** Recorded as ADR-012 in `docs/AI/09_DECISIONS.md`
   (see below) so future small-owner-scoped-collection endpoints don't need to re-litigate this reasoning.
4. **No `audit.audit_logs` writes exist yet for auth events**, despite `06_SECURITY.md`'s audit-logging
   section listing Login/Logout as tracked events. This is a platform-wide gap spanning AUTH-001, AUTH-002,
   and AUTH-003 alike (no `AuditLog` model/repository exists anywhere in the codebase yet) — not a regression
   introduced by this story, and not reasonable to fix as a side effect of any single auth story. Recommend
   its own dedicated future story.

---

## Testing Performed

- `cd backend && uv run pytest -v` — 192/192 passing, 0 regressions on AUTH-001/AUTH-002.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic downgrade base`
  — verified live, non-mocked, against a real local Postgres test database (independently re-run by both
  `backend` and `tester`); reversible, DB left clean afterward.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- `cd mobile && flutter test` — 30/30 passing, 0 regressions.
- `cd mobile && flutter analyze` — clean, no new warnings.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean.
- `tester` agent: all 11 ACs independently verified with direct evidence (real encode/decode round trips,
  genuine two-distinct-user ownership tests, direct reading of the reuse-detection cascade logic) — see table
  above. Also confirmed no silent weakening in any modified test file (diffed every one against the prior
  commit).
- `architect` agent: STORY COMPLETE — see findings above.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_05_1000-bc69dfa02341_identity_sessions_refresh_tokens.py`
- `backend/app/modules/identity/repositories/{device_repository,session_repository,refresh_token_repository}.py` (new)
- `backend/app/modules/identity/services/session_service.py` (new)
- `backend/app/modules/identity/services/auth_service.py` (`verify_otp_and_authenticate`/`authenticate_with_oauth`)
- `backend/app/modules/identity/models.py` (`Session`, `RefreshToken`)
- `backend/app/modules/identity/schemas.py` (`DeviceContext`, `RefreshTokenRequest`, `SessionSummaryResponse`, `LogoutAllRequest`)
- `backend/app/modules/identity/api.py` (`POST /refresh`, `GET /sessions`, `DELETE /sessions/{id}`, `POST /sessions/logout-all`)
- `backend/app/modules/identity/dependencies.py`
- `backend/app/core/security.py` (`create_access_token` new signature, `generate_refresh_token`, `hash_refresh_token`)
- `backend/app/core/config.py` (`ACCESS_TOKEN_EXPIRE_MINUTES` 30 → 15)
- `backend/app/core/exceptions/{exceptions.py,__init__.py}` (`InvalidRefreshTokenError`, `SessionNotFoundError`)
- `backend/app/api/dependencies.py` (real `get_current_user`)
- `backend/tests/modules/identity/test_session_service.py` (new), extended `test_security.py`,
  `test_auth_service.py`, `test_auth_endpoints.py`, `test_identity_models.py`, `test_dependencies.py`
- `backend/tests/conftest.py` (truncate order for `Session`/`RefreshToken`)

### Mobile
- `mobile/lib/features/auth/domain/models/device_context.dart` (new)
- `mobile/lib/core/storage/secure_token_storage.dart` (new)
- `mobile/lib/core/network/auth_interceptor.dart` (new)
- `mobile/lib/features/auth/domain/models/{auth_token,auth_user}.dart` (`toJson`/`refreshToken`)
- `mobile/lib/features/auth/data/auth_repository.dart` (`refresh`, `logout`, `device` payload)
- `mobile/lib/features/auth/state/auth_session_controller.dart`
- `mobile/lib/features/auth/presentation/screens/splash_screen.dart` (session recovery)
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` ("Log out")
- `mobile/lib/core/network/api_client.dart` (interceptor wiring)
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}` (`logOutLabel`)
- `mobile/test/features/auth/session_persistence_test.dart` (new),
  `mobile/test/features/home/home_placeholder_screen_test.dart` (new), extended fakes/`test_helpers.dart`

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-012 added, ratifying the unpaginated-small-owner-scoped-collection pattern
  used by `GET /sessions`.

---

## Follow-up Notes

- All nice-to-have items from the architect review are tracked above; none are required to close this story.
- `docs/implementation/plans/Plan_S02_AUTH-004.md` still describes the old, superseded 9-story Sprint 2
  backlog and does not correspond 1:1 to the current tracker's AUTH-004 ("Access the app according to my
  role"). It must be re-planned against the current tracker before being picked up, following the same
  process used for AUTH-001, AUTH-002, and AUTH-003.
- AUTH-004 is next and last in the Sprint 2 backlog. It depends on the `roles` claim this story's access
  tokens already carry (AC2) and on AUTH-001/002/003's shipped `User`/session infrastructure, and will add
  role-based authorization enforcement on top of it.
