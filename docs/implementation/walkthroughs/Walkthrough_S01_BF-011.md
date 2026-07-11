# Sprint 1 | BF-011 | Security Utilities

## Implementation Summary
The core security utilities required for future authentication processes were implemented. Following the MVP scope boundaries, no business modules were updated, and authentication remains intentionally disabled in this phase.

## What Was Implemented

1. **Security Exceptions** (`backend/app/core/exceptions/exceptions.py`)
   - Added `InvalidTokenError`, `ExpiredTokenError`, and `AuthenticationRequiredError`.
   - All exceptions inherit from `BusinessException` returning HTTP 401.

2. **Core Utilities** (`backend/app/core/security.py`)
   - Implemented `pwdlib` with `Argon2id` for hashing `hash_password`, `verify_password`.
   - Implemented `python-jose` for JWT tokens with `create_access_token`, `decode_token`, `get_token_expiry`.
   - Safely parses exceptions and translates them to domain-specific errors.

3. **API Dependencies** (`backend/app/api/dependencies.py`)
   - Registered `OAuth2PasswordBearer` to standard authentication route `/api/v1/auth/login`.
   - Implemented `get_token` for authorization header extraction.
   - Added a safe `get_current_user` placeholder dependency that immediately raises `AuthenticationRequiredError`, guaranteeing that no route using this dependency can be accidentally accessed before full authentication is released.

## Changed Files
- `pyproject.toml` (Added `pwdlib[argon2]`, `python-jose[cryptography]`)
- `backend/app/core/exceptions/exceptions.py`
- `backend/app/core/exceptions/__init__.py`
- `backend/app/core/security.py`
- `backend/app/api/dependencies.py`
- `backend/tests/core/test_security.py` (New)
- `backend/tests/api/test_dependencies.py` (New)

## Verification
- Wrote full unit test coverage for token generation, expiration, validation, hashing, and verifying.
- Evaluated `get_current_user` dependency intentionally raising `AuthenticationRequiredError` when called.
- Passed 53 unit tests in the `backend` suite perfectly.

## Future Considerations
- The `get_current_user` dependency will be implemented in future stories to actually validate tokens against user databases. Currently, it prevents any accidental authorized access by rejecting all calls.
- Authentication functionality has **NOT** been enabled.
