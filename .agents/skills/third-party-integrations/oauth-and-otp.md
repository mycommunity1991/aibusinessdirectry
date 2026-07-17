# Rule: OAuth & Mobile OTP

## Social Sign-In
* **Verify Server-Side:** Google/Apple ID tokens must be verified against the provider's public keys server-side on every login — never trust a client-asserted user ID.
* **Stable External Subject:** Persist the provider's `sub` claim (`external_auth_subject`) as the durable link to the account; email addresses from social providers can change or be unverified and must not be the join key.

## Mobile OTP
* **Reuse One OTP Table:** Registration, login, arrival-verification, and claim-listing flows all issue OTPs through `identity.otp_verifications` — do not build a parallel OTP mechanism per feature.
* **Hash, Rate-Limit, Expire:** OTP codes are hashed at rest, rate-limited per phone number via Redis, and expire on a short TTL (e.g. 5 minutes). A verified OTP is single-use — mark `verified_at` and reject reuse.
