# Plan for Story AUTH-003 - Mobile Number + OTP Registration & Login

Implement the mobile-number-and-OTP path of Flow 1 (`14_USER_FLOWS.md`). This story is strictly limited to the mobile OTP path — Google/Apple OAuth is AUTH-004, token issuance mechanics are AUTH-005.

## Goal Description

Wire AUTH-001's `users` model and AUTH-002's `OtpService` into a working registration/login flow: request an OTP for a phone number, verify it, and either create a new `User` (assigning the default `customer` role via `user_roles`) or authenticate an existing one.

## Architecture Decisions

- Two endpoints: `POST /api/v1/auth/mobile/request-otp` and `POST /api/v1/auth/mobile/verify`. A single verify endpoint serves both registration and login — if no `User` exists for the phone number, create one; if one exists, authenticate it. No separate "register" vs "login" branching exposed to the client, matching the no-guest-path, always-registered model.
- On first-time creation: set `auth_provider = mobile_otp`, assign the `customer` role. Per `03_DOMAIN_MODEL.md`'s dual-role rule, this does not preclude a `provider` role being added later on the same account (a separate future story).
- This story does **not** create `customer_profiles`/`customer_preferences` rows — those belong to the Customer domain module (a later sprint), not Identity & Access. Registration here produces an authenticated `User` + role assignment only.
- Service layer only calls `OtpService`; it never handles OTP hashing/expiry itself — no duplicated logic.

## Tasks

1. `AuthService.request_mobile_otp(phone)` → delegates to `OtpService.request_otp(phone, purpose=registration_or_login)`.
2. `AuthService.verify_mobile_otp(phone, code)` → delegates to `OtpService.verify_otp`, then find-or-create the `User`, assign `customer` role if newly created.
3. Pydantic v2 request/response DTOs — never return the ORM model directly.
4. FastAPI router endpoints under `/api/v1/auth/mobile/*`.
5. Integration tests: new-number registration, existing-number login, expired/invalid code rejection.
6. Note in the API docs that this endpoint intentionally has no guest/anonymous variant.
