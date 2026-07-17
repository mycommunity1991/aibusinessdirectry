# Plan for Story AUTH-002 - OTP Verification Service

Build the shared OTP generation, persistence, and verification service. This story is strictly limited to the OTP mechanism itself — no registration/login endpoints, and no concrete SMS provider integration (delivery is stubbed behind an interface).

## Goal Description

Implement `identity.otp_verifications` (model + migration) and an `OtpService` reusable across every OTP use case in the product — registration, login, arrival-verification ("Verified Visit"), and claim-listing — per `03_DOMAIN_MODEL.md` and the `third-party-integrations` skill. One OTP mechanism, not one per feature.

## Architecture Decisions

- `otp_verifications` columns per `04_DATABASE.md`: `user_id` (nullable — OTP can precede account creation), `phone_country_code`, `phone_number`, `purpose` (enum: `registration`, `login`, `arrival_verification`, `claim_listing`), `code_hash`, `attempt_count`, `expires_at`, `verified_at`.
- Codes are hashed at rest (never store plaintext) and never logged, per `06_SECURITY.md`.
- Short TTL (5 minutes) and a per-phone-number attempt cap, enforced in the service layer, not just documented as a rule.
- SMS delivery sits behind an `SmsSender` interface (Infrastructure layer) with a logging/no-op stub implementation for this story — wiring a real provider (Twilio or equivalent) is explicitly out of scope and should be a follow-up story once a provider is contracted.
- `OtpService` is called by other stories (AUTH-003 for registration/login, later stories for arrival-verification and claim-listing) — it must not assume a specific caller context.

## Tasks

1. Add `otp_verifications` model + Alembic migration.
2. Implement `OtpService`: `request_otp(phone, purpose)`, `verify_otp(phone, code, purpose)` — hashing, expiry, attempt tracking, single-use enforcement (`verified_at` set, reuse rejected).
3. Define the `SmsSender` interface and a stub implementation that logs the code in development only (never in production config).
4. Unit tests: expiry, attempt-limit lockout, single-use rejection, wrong-purpose rejection.
5. Do not add rate limiting here — that's AUTH-008, applied at the endpoint layer once endpoints exist.
