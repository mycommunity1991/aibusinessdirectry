# Plan for Story AUTH-008 - Auth Rate Limiting & Brute-Force Protection

Add Redis-backed rate limiting to the authentication endpoints built in AUTH-003/AUTH-004/AUTH-005. This story is strictly limited to auth-endpoint rate limiting — general API-wide rate limiting (if needed later) is a separate, future story.

## Goal Description

Protect OTP request/verify, OAuth login, and refresh endpoints against brute-force and credential-stuffing attacks, per `06_SECURITY.md`'s explicit limits: authentication endpoints at 10 requests/minute, with failed-attempt tracking and temporary lockout.

## Architecture Decisions

- A reusable Redis-backed rate-limit dependency (sliding window or token bucket, keyed by phone number / IP / user id as appropriate per endpoint), not one bespoke implementation per route.
- Applied to: `POST /auth/mobile/request-otp`, `POST /auth/mobile/verify`, `POST /auth/oauth/*`, `POST /auth/refresh`.
- Failed OTP verification attempts already count toward `otp_verifications.attempt_count` (AUTH-002) — this story adds the *endpoint-level* request-rate limit on top, a distinct control from the per-code attempt cap.
- Lockout responses must not leak whether a phone number/account exists — same generic "too many attempts, try again later" message regardless.

## Tasks

1. Implement the Redis-backed rate-limit dependency.
2. Apply it to the four endpoint groups above with the limits from `06_SECURITY.md`.
3. Add failed-login tracking (distinct from OTP attempt tracking) for OAuth/refresh paths.
4. Integration tests: limit triggers a 429 with a generic message; limit resets after the window; legitimate traffic under the limit is unaffected.
5. Confirm rate-limit state lives only in Redis, never in PostgreSQL — Redis is never the source of truth for anything else, but this is exactly the kind of ephemeral data it's for.
