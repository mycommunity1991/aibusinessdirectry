# Sprint 1 | BF-011 | Security Utilities

## Plan Overview
This plan established the foundational security infrastructure required for future authentication stories. Authentication itself was intentionally not enabled, maintaining the strict scope boundaries of the sprint.

## Proposed Changes

### Dependencies
- Added `pwdlib[argon2]` for modern, secure password hashing.
- Added `python-jose[cryptography]` for JWT creation and validation.

### Core Security & Exceptions
#### `backend/app/core/exceptions/exceptions.py`
- Added `InvalidTokenError`, `ExpiredTokenError`, and `AuthenticationRequiredError`. These inherit from `BusinessException` and return HTTP 401 with `WWW-Authenticate: Bearer` headers.

#### `backend/app/core/security.py`
- `hash_password(password: str) -> str`: Uses `pwdlib` and Argon2id.
- `verify_password(password: str, hashed_password: str) -> bool`: Verifies Argon2id hashes.
- `create_access_token(subject: str, expires_delta: timedelta | None = None) -> str`: JWT creation.
- `decode_token(token: str) -> dict`: Safely parses JWTs, raising custom exceptions on failure.
- `get_token_expiry() -> datetime`: Helper to calculate standard expiry time.

### API Dependencies
#### `backend/app/api/dependencies.py`
- Initialized `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`.
- Implemented `get_token(token: str = Depends(oauth2_scheme))` to extract the token safely.
- Implemented `get_current_user()` as a placeholder dependency that unconditionally raises `AuthenticationRequiredError`. This ensures route signatures can be prepared before full authentication is released.

### Unit Tests
- Password hashing and JWT generation/parsing were heavily tested in `tests/core/test_security.py`.
- `get_current_user` and `get_token` placeholder behavior were tested in `tests/api/test_dependencies.py`.
