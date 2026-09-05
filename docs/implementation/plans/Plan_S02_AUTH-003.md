# Plan for Story AUTH-003 — Stay Signed In and Manage Active Sessions

**Sprint:** 02 | **Story ID:** AUTH-003 | **Priority:** High | **Depends On:** AUTH-001 (Done), AUTH-002 (Done)

---

## Supersession Notice

The previous `Plan_S02_AUTH-003.md` described a slice of an old, superseded 9-story Sprint 2 backlog (AUTH-001 through AUTH-009: models → OTP service → mobile auth → OAuth → JWT → sessions → RBAC → rate limiting → audit logging). That backlog no longer exists.

The current `docs/AI/Project_Tracker.xlsx` (source of truth) defines a 4-story Sprint 2 — AUTH-001 through AUTH-004. Under that tracker, **AUTH-003 is "Stay signed in and manage active sessions"**: JWT access-token issuance, refresh-token rotation, and per-device session tracking, layered on top of the `identity.users` rows AUTH-001 (mobile OTP) and AUTH-002 (Google/Apple) already create. This plan is written against that current, authoritative scope (11 acceptance criteria, reproduced verbatim below) and against the **actual shipped code**, verified by reading it directly (see "Verified Current State").

`Plan_S02_AUTH-004.md` remains stale and must be re-planned when that story is picked up, following this same process.

---

## Story

As an authenticated user, I want to remain signed in securely across app restarts and see/manage my active sessions, so that I stay logged in conveniently while retaining control if a device is lost or compromised.

This story is exactly where the "stateless-first" precedent AUTH-001/AUTH-002 established changes: both of those stories issue one stateless JWT access token with no expiry-refresh mechanism and explicitly create no `sessions`/`refresh_tokens`/`devices` row (see both their Walkthroughs' scope boundaries). AUTH-003 introduces statefulness (revocability) into that otherwise fully stateless scheme — a device is recorded per login, a session tracks a rotation chain of refresh tokens, and access tokens stay short-lived and carry no PII.

**Scope boundary:** does not include role-based authorization (AUTH-004) — this story only establishes that a session exists and can be trusted, not what it's allowed to do. `roles` rides in the access token payload (AC2) purely as data; no endpoint in this story enforces a specific role.

---

## Acceptance Criteria (authoritative — from the Tracker)

1. `sessions`, `refresh_tokens`, and `devices` tables exist via migration, linked to `users`.
2. Successful login (via either AUTH-001 or AUTH-002) issues a 15-minute JWT access token containing only `sub`, `exp`, `iat`, `jti`, and `roles` — no email or phone number in the payload.
3. A refresh token is an opaque random string; only its hash is persisted, never the raw value.
4. Calling the refresh endpoint with a valid, unexpired refresh token issues a new access/refresh pair and invalidates the previous refresh token (rotation).
5. Calling the refresh endpoint with an already-used (rotated-away) or revoked refresh token is rejected.
6. A device row is created or updated on login capturing platform (iOS/Android) and a device name.
7. `GET sessions` lists the caller's active sessions with device name, platform, and last-seen time, flagging the current session.
8. `DELETE` on a single session revokes that session's refresh tokens; a subsequent refresh attempt with that session's token fails.
9. A "log out everywhere" action revokes every session except optionally the current one, and is a distinct, separately-labeled action from single-session revocation.
10. A user cannot list or revoke another user's sessions (ownership enforced, tested explicitly).
11. Automated tests cover rotation, revocation-then-refresh-fails, and the ownership boundary.

These are the acceptance criteria the tester will test against — no additions, no omissions.

---

## Verified Current State (read directly from code, not assumed)

- `backend/app/modules/identity/models.py` currently defines `User`, `Role`, `Permission`, `RolePermission`, `UserRole`, `Device`, `OtpVerification` — **no `Session`/`RefreshToken` models yet**. `Device` already exists (created by the AUTH-001 migration) but is never written to by any code path today — this story is the first to populate it.
- `docs/AI/04_DATABASE.md`'s Identity Domain section already fully specifies `devices`, `sessions`, and `refresh_tokens` at the column level (it was written in anticipation of this story) — **no `docs/AI/` schema-doc update is required**, unlike AUTH-002 which had to fix a doc gap. Implement exactly what's already documented there.
- `backend/app/core/security.py`'s `create_access_token(subject, expires_delta=None)` encodes only `{"sub", "exp"}` — no `iat`, `jti`, or `roles`. It's called from exactly two places: `AuthService.verify_otp_and_authenticate` and `AuthService.authenticate_with_oauth` (`backend/app/modules/identity/services/auth_service.py`). Both call sites are updated by this story.
- `backend/app/core/config.py`'s `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` defaults to `30` and `REFRESH_TOKEN_EXPIRE_DAYS` defaults to `7` — the latter is already defined but **completely unused** by any code today. AC2 requires a 15-minute access token; the default must change.
- `backend/app/api/dependencies.py`'s `get_current_user` is a BF-011 placeholder that **unconditionally raises** `AuthenticationRequiredError("Authentication is not yet implemented...")`. This story is the first to need a real authenticated-endpoint dependency (`GET/DELETE/POST /auth/sessions*`) and must implement it for real — not a pre-existing gap being silently worked around, but explicitly in this story's scope.
- `backend/app/modules/identity/schemas.py`'s `AuthTokenResponse` currently has no `refresh_token` field — every login-shaped endpoint (`verify-otp`, `google`, `apple`) must gain one, since a session+refresh token is now minted on every login, not only on a future refresh call. `VerifyOtpRequest`/`OAuthSignInRequest` have no device fields either — both need one to satisfy AC6.
- `backend/app/modules/identity/api.py`'s three existing endpoints (`request-otp`, `verify-otp`, `google`, `apple` — four, not three) all reuse a shared `RateLimitDependency`/Redis setup already wired into the app's lifespan (from AUTH-001's FU-5) — reusable as-is for the new endpoints, no new rate-limit infrastructure needed.
- Mobile: `authSessionProvider` (`mobile/lib/features/auth/state/auth_session_controller.dart`) is an in-memory-only `StateProvider<AuthToken?>` — its own doc comment says persisting across restarts is explicitly AUTH-003's job. `splash_screen.dart` already reads this provider to decide `phoneEntry` vs `homePlaceholder`, but since it's in-memory, a fresh process always finds it `null` — session persistence across restart genuinely does not work today, confirming this is the exact gap this story fills.
- `mobile/pubspec.yaml` already has `flutter_secure_storage: ^9.2.2` as a dependency (added per `12_TECH_STACK.md`'s original approved list) but it is **not used anywhere yet** — no new mobile dependency is needed for token persistence.
- `mobile/lib/core/network/api_client.dart`'s `Dio` instance has no interceptors and never attaches an `Authorization` header — every future authenticated mobile endpoint needs this, and this story is the first to need it.
- `docs/AI/15_SCREEN_INVENTORY.md` (the authoritative screen list — "if a screen doesn't trace back to a flow step, it doesn't belong in v1") has **no dedicated "Manage Sessions" screen**, and the app has no Profile/Settings screen (S-14) yet for one to live inside. None of this story's 11 tracker ACs describe a UI surface — all 11 are backend/API-testable behaviors. See Decision 10.

---

## Architecture Decisions

1. **A `Session` models one continuous device sign-in; its access token's `jti` claim doubles as the session identifier.** AC2 requires the access-token payload to contain *only* `sub`, `exp`, `iat`, `jti`, `roles` — no room for an extra `session_id`/`sid` claim without violating that literal constraint. Setting `jti = str(session.id)` at every issuance (login and every subsequent refresh-rotation) satisfies AC2's exact payload **and** gives `GET /auth/sessions` a free way to flag "is this the caller's current session" — decode the caller's own token (already done by `get_current_user`) and compare its `jti` to each listed session's `id`.
   **Trade-off, called out explicitly:** this means `jti` is not strictly unique *per individual access token* — every access token minted within the same session's lifetime (across refreshes) shares it. This is acceptable because this design has no independent access-token blocklist; only sessions/refresh tokens are individually revocable (AC7–AC9), and an already-issued access token remains valid for up to its remaining ≤15-minute lifetime even after its session is revoked (see Decision 7 for the full trade-off).

2. **Device matching key: `(user_id, platform, device_name)`, not a client-generated device ID.** `docs/AI/04_DATABASE.md`'s `devices` table (already fixed, not to be altered) has no separate stable "install ID" column — only `platform`/`device_name`/`push_token`/`is_trusted`/`last_seen_at`. Find-or-update on `(user_id, platform, device_name)` is the only key available within the documented schema. **Known limitation, not blocking:** two separate installs from the same user on the same platform with an identical (or absent) device name collapse into one `Device` row. A future story could add a client-generated device UUID column if this proves a real problem — not introduced here since it would be an undocumented schema addition requiring its own approval.

3. **Request/response contract changes to three already-shipped endpoints — flagged for explicit confirmation before backend implementation starts, per the same precedent as AUTH-002's schema-change flag.**
   - `VerifyOtpRequest` and `OAuthSignInRequest` (`google`/`apple`) each gain a required nested `device: { device_platform: "ios" | "android", device_name: string | null }` field (AC6 needs this data from somewhere, and there is no other source — no custom header is documented in `05_API_GUIDELINES.md`'s standard-headers list, so a validated JSON body field is used instead, consistent with this module's existing all-JSON-body style).
   - `AuthTokenResponse` (shared by `verify-otp`/`google`/`apple`/the new `refresh` endpoint) gains a `refresh_token: string` field — every login now mints a session + refresh token, not only a hypothetical future refresh call.
   This is an additive-field, non-breaking-for-JSON-parsers change, but it changes what a *conforming* client must send/expect, and modifies contracts AUTH-001/002 already shipped and tested — same category of decision as AUTH-002's Decision 2, flagged the same way.

4. **`create_access_token` signature changes: `roles` and `jti` become required parameters.** `create_access_token(subject: str, roles: list[str], jti: str, expires_delta: timedelta | None = None) -> str`. Both existing call sites (`verify_otp_and_authenticate`, `authenticate_with_oauth`) are updated in the same change — no other production caller exists (verified by search). `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` default changes `30` → `15` to literally satisfy AC2's "15-minute" requirement (still overridable via env var; low-risk, called out for visibility rather than silently changed).

5. **Refresh tokens: `secrets.token_urlsafe(32)` opaque value, hashed with SHA-256 (not Argon2id) before persistence.** `04_DATABASE.md`'s `refresh_tokens.token_hash` column note is explicit: *"SHA-256 hash of the token; raw token never persisted."* This deliberately diverges from the Argon2id pattern `hash_password`/`hash_otp_code` use elsewhere: Argon2id's slow-KDF property defends against brute-forcing a *low-entropy, human-chosen* secret (a password, a 6-digit OTP); a 256-bit `secrets.token_urlsafe` value has no brute-force surface to slow down, so a fast, collision-resistant hash is the correct (and doc-mandated) choice here — using Argon2id would only add needless latency to every refresh call. New `core/security.py` helpers: `generate_refresh_token() -> str` and `hash_refresh_token(token: str) -> str` (`hashlib.sha256(...).hexdigest()`).

6. **New `SessionService`, separate from `AuthService` — same separation-of-concerns precedent as `OAuthService`/`AuthService` in AUTH-002.** `AuthService` stays focused on identity verification and User find-or-create; `SessionService` owns device/session/refresh-token lifecycle:
   - `start_session(user, roles, device_platform, device_name, ip_address, user_agent) -> (session, access_token, raw_refresh_token)` — called at the end of both `verify_otp_and_authenticate` and `authenticate_with_oauth`, replacing their direct `create_access_token(...)` call.
   - `refresh(raw_refresh_token) -> (user, roles, new_access_token, new_raw_refresh_token)` — implements rotation (AC4) and rejection (AC5).
   - `list_active_sessions(user_id, current_session_id) -> list[SessionWithDevice]` (AC7).
   - `revoke_session(user_id, session_id) -> None` — raises `SessionNotFoundError` if the session doesn't exist *or* isn't owned by `user_id` (AC8, AC10).
   - `revoke_all_sessions(user_id, current_session_id, keep_current: bool) -> None` (AC9).
   New repositories back this: `DeviceRepository` (find-or-create/update by `(user_id, platform, device_name)`), `SessionRepository` (create, list active, get-by-id, revoke, revoke-all-for-user), `RefreshTokenRepository` (create, get-by-hash, rotate/revoke, revoke-all-for-session).

7. **Refresh-token reuse detection cascades to a full session revocation — recommended hardening, directly enabled by the schema already provided, not gating implementation on approval.** When `refresh()` finds a `RefreshToken` row that is already rotated-away (`revoked_at IS NOT NULL AND replaced_by_token_id IS NOT NULL`), that's a signal the token may have been stolen and replayed after the legitimate client already rotated past it. Rather than only rejecting that one call (AC5's literal minimum), this revokes the *entire session* (and every refresh token in its chain) — a well-known, low-cost defense-in-depth pattern the `replaced_by_token_id` rotation chain already exists to support. Flagged here for visibility since it's a security-relevant behavior beyond the literal AC text, not because it needs sign-off to proceed (it only ever makes the system *more* restrictive, never less).

8. **New, real `get_current_user` dependency in `app/api/dependencies.py`.** Replaces the BF-011 placeholder. Decodes the JWT via the existing `decode_token`, extracts `sub`/`jti`/`roles`, and returns a small `CurrentUser(id: UUID, session_id: UUID, roles: list[str])` value object. Missing/malformed required claims raise the existing `InvalidTokenError`.
   **Explicit, documented trade-off:** revoking a session (AC8/AC9) does not immediately invalidate any access token already issued under it — that token simply remains valid for up to its remaining ≤15-minute lifetime (Decision 1). Immediate access-token revocation would require either a Redis-backed blocklist or a per-request DB lookup, both of which defeat the stateless-access-token design this project has followed since AUTH-001. This mirrors standard industry practice (short-lived access token + revocable refresh chain, no blocklist) and is the recommended design — flagged for visibility given its security relevance, not held back pending approval.

9. **Ownership enforcement collapses "doesn't exist" and "exists but isn't yours" into the same 404**, never a 403 — consistent with this project's existing non-revealing-error philosophy (OTP/OAuth already never confirm/deny existence for different reasons). `SessionNotFoundError` (404) is used uniformly by `DELETE /auth/sessions/{id}` for both cases (AC10).

10. **"Log out everywhere" is `POST /auth/sessions/logout-all` with an optional `keep_current: bool = False` body flag — a distinct, separately named endpoint from `DELETE /auth/sessions/{id}`**, directly satisfying AC9's explicit "distinct, separately-labeled action" requirement.

11. **Mobile: no new "Manage Sessions" screen is built in this story.** None of the 11 tracker ACs describe a mobile UI surface for listing/revoking sessions, and `15_SCREEN_INVENTORY.md` has no such screen — nor does the app have a Profile/Settings screen (S-14) yet for one to live inside. Mobile scope is limited to what the story's "remain signed in across app restarts" narrative actually requires: secure token persistence, silent refresh, and splash-screen session recovery (S-01 already anticipates exactly this — "Splash | Brand moment + **session check**"), plus a bare "Log out" action wired into the existing `HomePlaceholderScreen` stub (reusing that existing surface rather than building a new one). **Flagged explicitly for user visibility**, since the story's product narrative ("see/manage my active sessions") does suggest a real session-list UI eventually — recommend a follow-up mobile story once Profile/Settings (S-14) is built, consuming the `GET/DELETE/logout-all` endpoints this story ships. `GET /auth/sessions`' full response shape is still exercised end-to-end by backend integration tests regardless of whether mobile renders it yet.

12. **Mobile: a Dio interceptor for `ApiClient` attaches `Authorization: Bearer <access_token>` to every request and performs one silent refresh-and-retry on a `401`.** This is the first piece of shared request-auth plumbing in the mobile app and every future authenticated feature will reuse it — in-scope here since "remain signed in" is meaningless without it. No new package (`dio`'s built-in `Interceptor` API).

13. **Mobile: device context (`device_platform`/`device_name`) is derived from `dart:io Platform` only — no new package.** `device_info_plus` (or similar) is deliberately not added; `Platform.isIOS`/`Platform.isAndroid` plus `Platform.operatingSystemVersion` is sufficient for a best-effort `device_name` and keeps this story's mobile dependency footprint at zero new packages.

---

## Backend — Proposed Changes

### Migration
#### [NEW] `backend/alembic/versions/<ts>-<hash>_identity_sessions_refresh_tokens.py`
- `CREATE TABLE identity.sessions (...)` per `04_DATABASE.md`: `id`, Common Columns, `user_id` FK, `device_id` FK (nullable), `ip_address INET`, `user_agent VARCHAR(500)`, `expires_at`, `revoked_at`; indexes `idx_sessions_user_id`, `idx_sessions_expires_at`.
- `CREATE TABLE identity.refresh_tokens (...)`: `id`, Common Columns, `user_id` FK, `session_id` FK, `token_hash VARCHAR(255)` unique, `expires_at`, `revoked_at`, `replaced_by_token_id` self-referential FK (nullable); index `idx_refresh_tokens_user_id`.
- `devices` already exists (AUTH-001 migration) — not touched by this migration.
- Verify both `upgrade()`/`downgrade()` work against a real local Postgres (matching AUTH-002's precedent of a live, non-mocked reversibility check).

### Config
#### [MODIFY] `backend/app/core/config.py`
`ACCESS_TOKEN_EXPIRE_MINUTES` default `30` → `15` (Decision 4, AC2).

### Models
#### [MODIFY] `backend/app/modules/identity/models.py`
Add `Session` and `RefreshToken` (`CommonColumnsMixin`), exactly matching `04_DATABASE.md` (Decision 6's repositories operate on these). Import `INET` from `sqlalchemy.dialects.postgresql` for `Session.ip_address`.

### Security utilities
#### [MODIFY] `backend/app/core/security.py`
- `create_access_token(subject: str, roles: list[str], jti: str, expires_delta: timedelta | None = None) -> str` (Decision 4) — payload is exactly `{sub, exp, iat, jti, roles}`, nothing else (AC2).
- `generate_refresh_token() -> str` (`secrets.token_urlsafe(32)`), `hash_refresh_token(token: str) -> str` (`hashlib.sha256(...).hexdigest()`) (Decision 5).

### Exceptions
#### [MODIFY] `backend/app/core/exceptions/exceptions.py`
- `InvalidRefreshTokenError` (401) — generic message, covers not-found/expired/revoked/reused alike (AC5, mirrors `InvalidOtpError`/`InvalidIdentityTokenError`'s non-revealing precedent).
- `SessionNotFoundError` (404) — covers both "doesn't exist" and "not yours" (Decision 9, AC10).

### Repositories
#### [NEW] `backend/app/modules/identity/repositories/device_repository.py`
`find_or_create(user_id, platform, device_name) -> Device` (updates `last_seen_at` on every call, whether newly created or found).
#### [NEW] `backend/app/modules/identity/repositories/session_repository.py`
`create(user_id, device_id, ip_address, user_agent, expires_at) -> Session`; `get_active_by_id(session_id) -> Session | None`; `list_active_for_user(user_id) -> list[Session]`; `revoke(session_id) -> None`; `revoke_all_for_user(user_id, except_session_id: uuid.UUID | None) -> None`.
#### [NEW] `backend/app/modules/identity/repositories/refresh_token_repository.py`
`create(user_id, session_id, token_hash, expires_at) -> RefreshToken`; `get_by_token_hash(token_hash) -> RefreshToken | None`; `revoke(refresh_token_id) -> None`; `revoke_all_for_session(session_id) -> None`; `mark_replaced(old_id, new_id) -> None`.

### Service
#### [NEW] `backend/app/modules/identity/services/session_service.py`
`SessionService` (Decisions 1, 6, 7) — `start_session`, `refresh`, `list_active_sessions`, `revoke_session`, `revoke_all_sessions`, including the reuse-detection cascade (Decision 7).
#### [MODIFY] `backend/app/modules/identity/services/auth_service.py`
`verify_otp_and_authenticate` and `authenticate_with_oauth` both gain `device_platform`, `device_name`, `ip_address`, `user_agent` parameters and delegate token/session/device creation to an injected `SessionService` instead of calling `create_access_token` directly.

### Schemas
#### [MODIFY] `backend/app/modules/identity/schemas.py`
- `DeviceContext { device_platform: DevicePlatform, device_name: str | None }` (Decision 3).
- `VerifyOtpRequest`/`OAuthSignInRequest` each gain `device: DeviceContext`.
- `AuthTokenResponse` gains `refresh_token: str`.
- `RefreshTokenRequest { refresh_token: str }`.
- `SessionSummaryResponse { id: uuid.UUID, device_name: str | None, platform: str | None, last_seen_at: datetime | None, created_at: datetime, is_current: bool }`.
- `LogoutAllRequest { keep_current: bool = False }`.

### API
#### [MODIFY] `backend/app/modules/identity/api.py`
- Thread `device: DeviceContext` and request-derived `ip_address`/`user_agent` (via FastAPI's `Request`) through `verify_otp`, `sign_in_with_google`, `sign_in_with_apple`.
- `POST /refresh` — public, rate-limited (ip-keyed, same auth bucket), `RefreshTokenRequest` → `SuccessResponse[AuthTokenResponse]` (AC4/AC5).
- `GET /sessions` — requires `get_current_user`, → `SuccessResponse[list[SessionSummaryResponse]]` (AC7). Not paginated — a user's realistic session count is small and per-owner; flagged for `architect` attention as a deliberate, low-risk deviation from `05_API_GUIDELINES.md`'s blanket pagination rule rather than a silent omission.
- `DELETE /sessions/{session_id}` — requires `get_current_user`, → `SuccessResponse[None]`, `SessionNotFoundError` (404) if not found/not owned (AC8, AC10).
- `POST /sessions/logout-all` — requires `get_current_user`, `LogoutAllRequest` → `SuccessResponse[None]` (AC9).
#### [MODIFY] `backend/app/modules/identity/dependencies.py`
Add `get_device_repository`, `get_session_repository`, `get_refresh_token_repository`, `get_session_service`; extend `get_auth_service`'s dependency chain to also receive the `SessionService`.
#### [MODIFY] `backend/app/api/dependencies.py`
Real `get_current_user` (Decision 8) — `CurrentUser(id, session_id, roles)` value object.

### Tests
#### [MODIFY] `backend/tests/core/test_security.py`
`create_access_token`'s new signature/payload shape (exactly `{sub, exp, iat, jti, roles}`, no more — explicit AC2 test); `generate_refresh_token`/`hash_refresh_token`.
#### [MODIFY] `backend/tests/api/test_dependencies.py`
Real `get_current_user`: valid token → `CurrentUser`; missing/expired/malformed token → the existing exceptions.
#### [NEW] `backend/tests/modules/identity/test_session_service.py`
Rotation success (new pair issued, old refresh token invalidated — AC4); reusing an already-rotated token fails and cascades to full-session revocation (Decision 7, AC5); a revoked/expired token fails (AC5); `list_active_sessions` returns only active sessions with the correct `is_current` flag (AC7); revoking a session then attempting refresh with its token fails (AC8, AC11's explicit "revocation-then-refresh-fails" requirement); `revoke_all_sessions` revokes every session except a kept current one, and a distinct call revokes literally all of them (AC9); a different user's `user_id` cannot list or revoke another user's session — explicit ownership-boundary test (AC10, AC11).
#### [MODIFY] `backend/tests/modules/identity/test_auth_service.py`
`verify_otp_and_authenticate`/`authenticate_with_oauth` now also create a `Device` (created vs. updated on repeat login from the same device info — AC6) and a `Session`+initial `RefreshToken`, and return a `refresh_token` alongside the access token.
#### [MODIFY] `backend/tests/modules/identity/test_auth_endpoints.py`
Integration coverage: `verify-otp`/`google`/`apple` responses now include `refresh_token`; repeated logins from the same device info update rather than duplicate the `Device` row (AC6); `POST /refresh` happy path plus reused/revoked/expired rejection (AC4/AC5); `GET /sessions` response shape including `is_current` (AC7); `DELETE /sessions/{id}` then a refresh attempt with that session's token fails (AC8, explicit integration test per AC11); `POST /sessions/logout-all` with and without `keep_current` (AC9); explicit cross-user ownership test — user A's token cannot list or revoke user B's session, asserted as a 404 that reveals nothing (AC10, AC11).
#### [MODIFY] `backend/tests/modules/identity/test_identity_models.py`
`Session`/`RefreshToken` table/constraint/index assertions, mirroring the existing `Device` coverage.

---

## Mobile — Proposed Changes

### Domain
#### [MODIFY] `mobile/lib/features/auth/domain/models/auth_token.dart`
Add `refreshToken` (parses the new `refresh_token` field).
#### [NEW] `mobile/lib/features/auth/domain/models/device_context.dart`
`DeviceContext.current()` — builds `{device_platform, device_name}` from `dart:io Platform` (Decision 13), no new package.

### Storage
#### [NEW] `mobile/lib/core/storage/secure_token_storage.dart`
Wraps the existing (already-a-dependency, previously-unused) `flutter_secure_storage`: `read() -> AuthToken?`, `write(AuthToken)`, `clear()`.

### Networking
#### [MODIFY] `mobile/lib/core/network/api_client.dart`
Add an `Interceptor` (Decision 12): attaches `Authorization: Bearer <access_token>` from current session state to outgoing requests; on a `401`, attempts one silent `POST /auth/refresh` + retry before giving up.

### Feature: Auth
#### [MODIFY] `mobile/lib/features/auth/data/auth_repository.dart`
- `requestOtp`/`verifyOtp`/`signInWithGoogle`/`signInWithApple` all include `device: DeviceContext.current().toJson()` in their request bodies (Decision 3/13).
- Add `refresh(refreshToken) -> AuthToken` (`POST /auth/refresh`).
- Add `logout()` — reads the current session's `jti` (a plain base64Url decode of the access token's own payload — no signature verification needed client-side, since it's only used to label "my own session," never for authorization) and calls `DELETE /auth/sessions/{sessionId}`, then clears storage.
#### [MODIFY] `mobile/lib/features/auth/state/auth_session_controller.dart`
On successful login/refresh, persist the `AuthToken` via `SecureTokenStorage` in addition to updating in-memory state.
#### [MODIFY] `mobile/lib/features/auth/presentation/screens/splash_screen.dart`
Replace the in-memory-only `authSessionProvider` check with: read persisted tokens from `SecureTokenStorage` → if present, call `refresh()` once to validate/rotate → success populates session state and routes to `homePlaceholder`; failure clears storage and routes to `phoneEntry` (S-01's own doc comment already anticipates this exact "session check").

### Feature: Home (existing stub)
#### [MODIFY] `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart`
Add a bare "Log out" action calling `AuthRepository.logout()`, then routing back to `phoneEntry` — reuses this existing stub rather than building a new screen (Decision 11).

### Localization
#### [MODIFY] `mobile/lib/l10n/app_en.arb` / `app_ar.arb`
Add the "Log out" label and any session-expired copy needed by the splash-screen failure path.

### Tests
#### [NEW] `mobile/test/features/auth/session_persistence_test.dart`
Splash screen: persisted valid session → silent refresh → `homePlaceholder`; no persisted session → `phoneEntry`; persisted-but-rejected session → storage cleared → `phoneEntry`.
#### [MODIFY] `mobile/test/features/auth/fakes/fake_auth_repository.dart`
Extend with configurable `refresh()`/`logout()` outcomes.
#### [MODIFY] existing OTP/OAuth tests (`phone_entry_screen_test.dart`, `oauth_sign_in_test.dart`) as needed if `device` payload changes affect their fakes' call signatures.

---

## Explicitly Out of Scope (do not implement in this story)

- RBAC/permission enforcement — `roles` merely rides in the token payload as data; no endpoint checks a specific role (AUTH-004).
- A dedicated mobile "Manage Sessions" list/detail screen (Decision 11) — deferred until Profile/Settings (S-14) exists; the backend `GET/DELETE/logout-all` endpoints are fully built and tested regardless.
- `devices.push_token` / `is_trusted` — columns exist per the fixed schema but no product behavior in this story's ACs sets them to anything but their defaults.
- Any Redis-backed access-token blocklist or per-request session-validity DB lookup — the documented trade-off in Decision 8 is the deliberate design.
- Proxy-aware IP extraction (`X-Forwarded-For` chain parsing) — best-effort `request.client.host` only.
- Any `customer_profiles`/RBAC/other-domain change.
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **Orchestrator** — before backend work starts, confirm with the user: (a) Decision 3's request/response contract changes to the three already-shipped auth endpoints (`device` field added to `verify-otp`/`google`/`apple` requests; `refresh_token` added to their shared response), and (b) Decision 11's mobile scope call (no new "Manage Sessions" screen this story). Neither is a new external dependency, but both change previously-shipped behavior/contract and are flagged the same way AUTH-002's schema/dependency decisions were.
2. **`backend`** (`backend/app/`, `backend/alembic/`, `backend/tests/`) — implement the "Backend — Proposed Changes" section in this order: migration → config → models → security utilities → exceptions → repositories → `SessionService` → `AuthService` updates → schemas → API endpoints/dependencies → `get_current_user` → tests. Focus ACs: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11.
3. **`frontend`** (`mobile/lib/`, `mobile/test/`) — implement the "Mobile — Proposed Changes" section against the backend contract from step 2. Focus: the "remain signed in across app restarts" narrative and AC6's device-context payload; no new UI screen (Decision 11).
4. **`tester`** — verify all 11 acceptance criteria individually, with particular attention to AC11's explicit trio (rotation, revocation-then-refresh-fails, ownership boundary) and AC2's exact-payload-shape check; full regression of AUTH-001/AUTH-002's existing tests (the `AuthTokenResponse`/request-schema changes are the main regression risk).
5. **`architect`** — review: the Decision 1 `jti`-as-session-id design and Decision 8's access-token-revocation trade-off against `06_SECURITY.md` ("Sessions are device specific, revocable, expirable" / "Users may terminate individual sessions"); the new `sessions`/`refresh_tokens` tables against `04_DATABASE.md` (should already match exactly — flag if not); Clean Architecture layering (`SessionService`/`AuthService`/repository boundaries); the unpaginated `GET /sessions` deviation from `05_API_GUIDELINES.md`; mobile Dio-interceptor and secure-storage usage against `06_SECURITY.md`'s token-handling guidance.
6. **Orchestrator** — once `tester` and `architect` both report clean, pause and present the diff + both verdicts to the user for explicit sign-off before writing the Walkthrough or touching the changelog/tracker.

---

## Verification Plan

- `cd backend && uv run pytest -v` — full suite, including new session-service/endpoint/dependency tests, must pass; no regression in AUTH-001/AUTH-002's existing tests (the `AuthTokenResponse`/request-schema additions are the main regression risk to watch).
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — migration reversible, against a real local Postgres.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- `cd mobile && flutter test` — new session-persistence tests pass, no regression in AUTH-001/AUTH-002's existing auth widget tests.
- `cd mobile && flutter analyze` — no new warnings.
- Manual/API-level check: login (any path) returns `access_token` + `refresh_token`; decode the access token and confirm its payload is exactly `{sub, exp, iat, jti, roles}` (AC2); `POST /refresh` with the returned refresh token issues a new pair and the old one is rejected on reuse (AC4/AC5); `GET /sessions` shows the device/platform/last-seen and flags the current session (AC7); `DELETE /sessions/{id}` then a refresh with that session's token fails (AC8); `POST /sessions/logout-all` revokes every other session (AC9); a second user's token cannot see or revoke the first user's session (AC10).

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` — Identity & Access domain
- `docs/AI/04_DATABASE.md` — Identity Domain schema (`devices`/`sessions`/`refresh_tokens` already fully specified, no update needed this time)
- `docs/AI/05_API_GUIDELINES.md` — response envelope, pagination, rate limiting, status codes
- `docs/AI/06_SECURITY.md` — session management, revocability, token handling
- `docs/AI/08_CODING_STANDARDS.md` — Flutter/Python structure and naming
- `docs/AI/12_TECH_STACK.md` — approved package lists (no new package needed this story)
- `docs/AI/15_SCREEN_INVENTORY.md` — confirms no "Manage Sessions" screen exists in v1's inventory (Decision 11)
- `docs/implementation/plans/Plan_S02_AUTH-001.md` / `Plan_S02_AUTH-002.md` — prior stories, shipped the `identity` schema/models this story extends
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-001.md` / `Walkthrough_S02_AUTH-002.md` — verified current-state source for this plan
- `docs/implementation/prompts/Prompt_S02_AUTH-003.md`
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-003.md` (to be created on completion)
