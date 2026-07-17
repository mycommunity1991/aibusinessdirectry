# Plan for Story AUTH-005 - JWT Access & Refresh Token Issuance

Issue and rotate tokens after a successful AUTH-003/AUTH-004 authentication. This story is strictly limited to token issuance and rotation — RBAC enforcement on protected routes is AUTH-007, device/session listing UI is AUTH-006.

## Goal Description

Implement `identity.sessions` and `identity.refresh_tokens` (models + migration) and a token service producing short-lived JWT access tokens and long-lived opaque refresh tokens, per `identity-and-jwt.md` (`security-and-auth` skill) and `06_SECURITY.md`.

## Architecture Decisions

- Access tokens: short-lived (15 minutes), JWT, claims limited to `sub` (User UUID), `exp`, `iat`, `jti`, `roles` — no PII (email/phone) in the payload.
- Refresh tokens: opaque random strings, stored as a hash (`token_hash`) in `refresh_tokens`, never as a JWT.
- Refresh rotation: using a refresh token invalidates it and issues a new access/refresh pair; `replaced_by_token_id` chains the rotation for audit purposes.
- A `sessions` row is created per login (per device where known), and `refresh_tokens.session_id` ties back to it — this is the foundation AUTH-006 builds device/session listing on top of.
- Token generation itself lives in a `TokenService` used identically regardless of which auth method (mobile OTP or OAuth) produced the authenticated `User` — one issuance path, not one per auth method.

## Tasks

1. Add `sessions` and `refresh_tokens` models + Alembic migration.
2. `TokenService.issue(user, session)` → access JWT + refresh token pair.
3. `TokenService.refresh(refresh_token)` → validate hash, check `revoked_at`/`expires_at`, rotate, return new pair.
4. Wire AUTH-003 and AUTH-004's successful-auth paths to call `TokenService.issue`.
5. `POST /api/v1/auth/refresh` endpoint.
6. Unit tests: expired token rejection, revoked token rejection, rotation chain correctness, no PII in JWT payload (explicit assertion, not just a code review note).
