# Rule: Identity & Token Management (JWT)

## Password Hashing
* **Argon2id Mandatory:** All passwords must be hashed using the `argon2-cffi` library implementing the Argon2id algorithm. Legacy hashing algorithms (bcrypt, PBKDF2, SHA-256) are strictly prohibited.
* **Never Log Secrets:** Plaintext passwords, hashes, and OTPs must never be written to application logs or exposed in API error responses.

## JWT Standards
* **Short-Lived Access Tokens:** JWT Access Tokens must be short-lived (e.g., 15 minutes) and signed using asymmetric (RS256) or strong symmetric (HS256) encryption with securely rotated environment secrets.
* **Claims:** JWT payloads must only contain essential claims: `sub` (User UUID), `exp` (Expiration), `iat` (Issued At), `jti` (JWT ID), and basic `roles`. Never embed sensitive PII (like email or phone number) inside the JWT payload.

## Refresh Tokens
* **Opaque Tokens:** Refresh tokens must be long-lived, opaque strings (not JWTs), stored securely in the database (hashed) or Redis to allow for immediate revocation and session invalidation.
* **Rotation:** Implement refresh token rotation. Using a refresh token must invalidate the old one and issue a new access/refresh token pair.