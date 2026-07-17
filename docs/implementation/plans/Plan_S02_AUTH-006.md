# Plan for Story AUTH-006 - Device & Session Management

Let a user see and revoke their own active sessions. This story is strictly limited to device/session records and their management endpoints — token mechanics are AUTH-005.

## Goal Description

Implement `identity.devices` (model + migration), record a device on login, and expose endpoints to list and revoke sessions, per `06_SECURITY.md`: "Sessions are device specific, revocable, expirable... Users may terminate individual sessions."

## Architecture Decisions

- `devices` columns per `04_DATABASE.md`: `user_id`, `platform` (ios/android), `device_name`, `push_token`, `is_trusted`, `last_seen_at`.
- Login (from AUTH-003/AUTH-004, via AUTH-005's token issuance) accepts optional device metadata and upserts a `devices` row, then links it to the `sessions` row created for that login.
- "Log out this device" revokes one session's refresh tokens; "log out everywhere" revokes all of a user's active sessions — both are explicit, separate actions, not one ambiguous "log out" button.
- Revocation is enforced at `TokenService.refresh` (AUTH-005) by checking `sessions.revoked_at` / `refresh_tokens.revoked_at` — this story adds the management surface, not a second enforcement path.

## Tasks

1. Add `devices` model + Alembic migration.
2. Extend login flows (AUTH-003/AUTH-004) to accept device metadata and upsert `devices`.
3. `GET /api/v1/auth/sessions` — list the caller's active sessions with device info, last-seen, current-session flag.
4. `DELETE /api/v1/auth/sessions/{id}` — revoke one session.
5. `DELETE /api/v1/auth/sessions` — revoke all sessions except the current one ("log out everywhere").
6. Integration tests: revoked session's refresh token is rejected by AUTH-005's refresh endpoint; a user cannot revoke another user's session (ownership check).
