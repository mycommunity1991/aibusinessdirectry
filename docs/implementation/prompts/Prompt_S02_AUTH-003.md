**Active Story:** Sprint 2 | AUTH-003 | Stay Signed In and Manage Active Sessions

**Story:**
As an authenticated user, I want to remain signed in securely across app restarts and see/manage my active sessions, so that I stay logged in conveniently while retaining control if a device is lost or compromised.

This story implements JWT access-token issuance, refresh-token rotation, and per-device session tracking, building on the User records AUTH-001 (mobile OTP) and AUTH-002 (Google/Apple) already create. Access tokens are short-lived and carry no PII; refresh tokens are opaque and stored only as a hash. A device is recorded per login so a user can distinguish and revoke sessions individually.

**Scope boundary:** does NOT include role-based authorization (AUTH-004) — this story only establishes that a session exists and can be trusted, not what it's allowed to do. `roles` rides in the access token payload purely as data.

---

## Technical Context & Architecture Constraints

- `backend/app/modules/identity/models.py` has no `Session`/`RefreshToken` models yet. `Device` already exists (from AUTH-001's migration) but nothing writes to it today — this story is the first to populate it. `docs/AI/04_DATABASE.md` already fully specifies `devices`/`sessions`/`refresh_tokens` at the column level — implement exactly what's documented there; no doc update needed.
- `create_access_token(subject, expires_delta=None)` in `backend/app/core/security.py` currently encodes only `{sub, exp}`. Its signature must change to `create_access_token(subject: str, roles: list[str], jti: str, expires_delta: timedelta | None = None)`, producing a payload of exactly `{sub, exp, iat, jti, roles}` — no email/phone (AC2). Both existing call sites (`AuthService.verify_otp_and_authenticate`, `AuthService.authenticate_with_oauth`) must be updated together. `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` default changes `30` → `15` (AC2's literal "15-minute" requirement).
- A `Session` represents one continuous device sign-in; its access token's `jti` claim IS the session ID (`jti = str(session.id)`) — this is how `GET /sessions` can flag "current" without adding a claim outside AC2's exact 5-field list. Every refresh reissues an access token with the same `jti` (same session) — documented trade-off, not a bug: there's no independent per-access-token blocklist in this design, only sessions/refresh tokens are individually revocable.
- Refresh tokens: `secrets.token_urlsafe(32)` opaque value, hashed with **SHA-256** (`hashlib.sha256`, not Argon2id) before persistence — `04_DATABASE.md`'s column note says so explicitly; Argon2id is for low-entropy human secrets (passwords, OTP codes), not a 256-bit random token.
- New `SessionService` (parallel precedent to AUTH-002's `OAuthService`/`AuthService` split): owns `start_session`, `refresh` (rotation — AC4/AC5), `list_active_sessions` (AC7), `revoke_session` (AC8/AC10), `revoke_all_sessions` (AC9). Backed by new `DeviceRepository`/`SessionRepository`/`RefreshTokenRepository`. `AuthService`'s two existing auth methods gain `device_platform`/`device_name`/`ip_address`/`user_agent` params and delegate to `SessionService` instead of calling `create_access_token` directly.
- **Recommended hardening (not gating on approval, only makes things more restrictive):** when `refresh()` detects an already-rotated-away refresh token being reused, revoke the entire session (all its refresh tokens), not just reject that one call — the existing `replaced_by_token_id` rotation chain exists exactly to support this.
- **Required contract changes — confirm with the user before backend implementation starts** (same category as AUTH-002's flagged schema change): `VerifyOtpRequest`/`OAuthSignInRequest` each gain a required `device: { device_platform: "ios"|"android", device_name: string|null }` field (AC6 needs this data from the client, no other source exists); `AuthTokenResponse` (shared by `verify-otp`/`google`/`apple`/the new `refresh` endpoint) gains a `refresh_token: string` field.
- Device find-or-update key is `(user_id, platform, device_name)` — the fixed, already-documented `devices` schema has no separate client-generated device ID column. Known, acceptable limitation: two installs with identical platform+name collapse to one `Device` row.
- New endpoints in `backend/app/modules/identity/api.py`: `POST /refresh` (public, rate-limited, rotation), `GET /sessions` (requires real auth — see next point), `DELETE /sessions/{session_id}` (ownership-enforced, 404 for both "doesn't exist" and "not yours" — never 403), `POST /sessions/logout-all` (body `{keep_current: bool = false}` — a distinct, separately-named action from single-session delete, per AC9).
- `backend/app/api/dependencies.py`'s `get_current_user` is currently a BF-011 placeholder that unconditionally raises. This story implements it for real: decode the JWT, return `CurrentUser(id, session_id, roles)`.
- `GET /sessions` is intentionally left unpaginated (small, per-owner collection) — flag this for `architect`, don't silently skip mentioning it.
- Mobile: `authSessionProvider` is in-memory only today — a fresh app process always finds it `null`, so "stay signed in across restart" genuinely doesn't work yet. `flutter_secure_storage` is already a dependency (unused) — use it for persistence, no new package. `dio` has no auth interceptor yet — add one (attach `Authorization: Bearer`, one silent refresh-and-retry on 401). Device context (`device_platform`/`device_name`) comes from `dart:io Platform` only — do not add `device_info_plus` or any similar package.
- Mobile UI scope is intentionally minimal: no new "Manage Sessions" screen (none of the 11 ACs require one, and `15_SCREEN_INVENTORY.md` has no such screen nor a Profile/Settings screen yet to host it in) — just secure persistence, splash-screen silent refresh (S-01 already anticipates a "session check"), and a bare "Log out" action added to the existing `HomePlaceholderScreen` stub. Flag this scope call for the user; it's a deliberate, documented choice, not an oversight.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S02_AUTH-003.md` — follow it, including its Architecture Decisions and Verified Current State sections.

---

## Implementation Instructions

### Backend
1. Add a new Alembic migration creating `identity.sessions` and `identity.refresh_tokens` per `04_DATABASE.md` (columns, FKs, indexes exactly as documented). `devices` already exists — don't touch it. Verify upgrade and downgrade both work against a real local Postgres.
2. Change `ACCESS_TOKEN_EXPIRE_MINUTES` default to `15` in `backend/app/core/config.py`.
3. Add `Session`/`RefreshToken` SQLAlchemy models to `backend/app/modules/identity/models.py` (`CommonColumnsMixin`, matching the migration).
4. Update `create_access_token` in `backend/app/core/security.py` to the new `(subject, roles, jti, expires_delta=None)` signature, payload exactly `{sub, exp, iat, jti, roles}`. Add `generate_refresh_token()` (`secrets.token_urlsafe(32)`) and `hash_refresh_token(token)` (`hashlib.sha256(...).hexdigest()`).
5. Add `InvalidRefreshTokenError` (401, generic) and `SessionNotFoundError` (404, generic — covers both not-found and not-owned) to `backend/app/core/exceptions/exceptions.py`.
6. Add `DeviceRepository`, `SessionRepository`, `RefreshTokenRepository` under `backend/app/modules/identity/repositories/`.
7. Add `backend/app/modules/identity/services/session_service.py`: `SessionService` with `start_session`, `refresh` (rotation + reuse-detection cascade), `list_active_sessions`, `revoke_session`, `revoke_all_sessions`.
8. Update `AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth` to accept device/request context and delegate to `SessionService.start_session` instead of calling `create_access_token` directly.
9. Update `backend/app/modules/identity/schemas.py`: `DeviceContext`, `device` field on `VerifyOtpRequest`/`OAuthSignInRequest`, `refresh_token` field on `AuthTokenResponse`, `RefreshTokenRequest`, `SessionSummaryResponse`, `LogoutAllRequest`.
10. Update `backend/app/modules/identity/api.py`: thread device/IP/user-agent through the three existing login endpoints; add `POST /refresh`, `GET /sessions`, `DELETE /sessions/{session_id}`, `POST /sessions/logout-all`. Wire new dependencies in `dependencies.py`.
11. Implement `get_current_user` for real in `backend/app/api/dependencies.py` — decode JWT, return `CurrentUser(id, session_id, roles)`.
12. Write/extend tests: `test_security.py` (new token shape), `test_dependencies.py` (real `get_current_user`), new `test_session_service.py` (rotation, reuse-cascade, revoke-then-refresh-fails, ownership boundary, `list_active_sessions`'s `is_current` flag), extend `test_auth_service.py` and `test_auth_endpoints.py` (device capture, refresh_token in responses, `/refresh`/`/sessions`/`/sessions/{id}`/`/sessions/logout-all` integration coverage including the explicit AC10/AC11 ownership test), extend `test_identity_models.py` for the two new tables.

### Mobile
13. Add `refreshToken` to `AuthToken`; add `DeviceContext.current()` (no new package).
14. Add `SecureTokenStorage` wrapping the existing `flutter_secure_storage` dependency.
15. Add a Dio interceptor to `ApiClient`: attach `Authorization: Bearer`, one silent refresh-and-retry on 401.
16. Update `AuthRepository`: include `device` in `requestOtp`/`verifyOtp`/`signInWithGoogle`/`signInWithApple` bodies; add `refresh()` and `logout()`.
17. Update `auth_session_controller.dart` to persist via `SecureTokenStorage` on login/refresh.
18. Update `splash_screen.dart`: read persisted session → silent refresh → route to `homePlaceholder` or `phoneEntry` accordingly, clearing storage on failure.
19. Add a "Log out" action to the existing `HomePlaceholderScreen` stub — do not build a new "Manage Sessions" screen.
20. Add localized strings needed for the above (`app_en.arb`/`app_ar.arb`).
21. Write `mobile/test/features/auth/session_persistence_test.dart` (splash-screen restart/refresh/failure paths) and extend `fake_auth_repository.dart`.

### Both
22. Confirm `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and `flutter analyze`.
23. Do not implement anything in the Plan's "Explicitly Out of Scope" section (RBAC enforcement, a new Manage Sessions screen, `push_token`/`is_trusted` behavior, access-token blocklisting, proxy-aware IP parsing, any other-domain change, any Quote/messaging/payment feature).

---

## Definition of Done

- All 11 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (AUTH-003 row) are met, verified by `tester` against each one individually.
- `sessions`/`refresh_tokens` tables exist via a working, reversible migration, linked to `users` (and `devices`, already present) — AC1.
- A fresh login returns an access token whose decoded payload is exactly `{sub, exp, iat, jti, roles}` with a 15-minute expiry, plus an opaque refresh token whose raw value is never persisted (AC2/AC3).
- `POST /refresh` rotates successfully with a valid token (AC4) and rejects an already-used or revoked one (AC5).
- A device row is created or updated on login with platform + device name (AC6).
- `GET /sessions` lists active sessions with device name, platform, last-seen time, and flags the current one (AC7).
- `DELETE /sessions/{id}` revokes that session's refresh tokens; a subsequent refresh with that session's token fails (AC8).
- `POST /sessions/logout-all` revokes every session, optionally excluding the current one, as a distinct action from single-session delete (AC9).
- A second user's token cannot list or revoke a first user's session — explicit ownership test passes (AC10).
- Automated tests explicitly cover rotation, revocation-then-refresh-fails, and the ownership boundary (AC11).
- No regression in AUTH-001/AUTH-002's existing test suites.
- Mobile: a signed-in session survives an app restart (persisted, silently refreshed); "Log out" works from the existing home stub. No new "Manage Sessions" screen is built.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- No functionality from AUTH-004, a Manage Sessions UI, or `11_MVP_SCOPE.md`'s excluded list is introduced, even incidentally.
- The two flagged decisions (request/response contract changes to the three existing auth endpoints; the mobile no-new-screen scope call) are explicitly confirmed with the user before their respective implementation work starts.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched.
