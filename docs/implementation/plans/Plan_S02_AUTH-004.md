# Plan for Story AUTH-004 - Google & Apple OAuth Registration & Login

Implement the social-sign-in path of Flow 1 (`14_USER_FLOWS.md`). This story is strictly limited to Google and Apple ID token verification — no mobile OTP (AUTH-003), no token issuance mechanics (AUTH-005).

## Goal Description

Verify a Google or Apple ID token server-side and find-or-create the corresponding `User`, per the `third-party-integrations` skill's OAuth rule: never trust a client-asserted identity, always verify against the provider's public keys, and key the account on the provider's durable `sub` claim, not email.

## Architecture Decisions

- One `OAuthVerifier` interface (Infrastructure layer), two adapters: `GoogleOAuthVerifier`, `AppleOAuthVerifier`. Services depend on the interface, never on either SDK directly — swapping or adding a provider later must not touch the Domain or API layers.
- Match on `(auth_provider, external_auth_subject)`, not email — social email addresses can change or be unverified.
- On first-time creation: assign the `customer` role, same as AUTH-003. Same explicit non-goal — no `customer_profiles` row created here.
- If an email from the token matches an existing account created via a different method (e.g. mobile OTP), do **not** silently merge accounts — that's an account-linking decision out of scope for this story and needs its own explicit design later.

## Tasks

1. Define `OAuthVerifier` interface: `verify(id_token: str) -> VerifiedIdentity` (subject, email, email_verified).
2. Implement `GoogleOAuthVerifier` and `AppleOAuthVerifier` against each provider's public key endpoint.
3. `AuthService.login_with_oauth(provider, id_token)` → verify, find-or-create `User`, assign `customer` role if newly created.
4. Endpoints: `POST /api/v1/auth/oauth/google`, `POST /api/v1/auth/oauth/apple`.
5. Integration tests using signed test tokens / mocked provider key endpoints (never call the real Google/Apple endpoints in CI).
6. Explicitly test and document the "different provider, same email" case resulting in two separate accounts, not a merge.
