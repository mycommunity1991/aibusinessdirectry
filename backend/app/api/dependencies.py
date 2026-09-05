import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.constants import API_PREFIX
from app.core.exceptions import AuthenticationRequiredError, InvalidTokenError
from app.core.security import decode_token

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{API_PREFIX}/auth/login",
    auto_error=False,
)

TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


def get_token(token: TokenDep) -> str:
    """
    Extracts the JWT token from the Authorization header.
    Raises AuthenticationRequiredError if missing.
    """
    if not token:
        raise AuthenticationRequiredError(
            message="Authentication credentials were not provided"
        )
    return token


@dataclass(frozen=True)
class CurrentUser:
    """
    The authenticated caller, resolved from a valid JWT access token
    (AUTH-003). `session_id` is the token's `jti` claim, which IS the
    session id (Decision 1, `Plan_S02_AUTH-003.md`) -- used by
    `GET /auth/sessions` to flag which listed session is "current".
    """

    id: uuid.UUID
    session_id: uuid.UUID
    roles: list[str]


def get_current_user(token: Annotated[str, Depends(get_token)]) -> CurrentUser:
    """
    Decodes the JWT access token and returns the authenticated caller.

    Replaces the former BF-011 placeholder (which unconditionally
    raised) -- AUTH-003 is the first story needing a real authenticated-
    endpoint dependency.

    Raises:
        InvalidTokenError: if the token is malformed, expired (raised as
            `ExpiredTokenError`, a subclass-sibling status the caller
            already handles identically), or missing any of the required
            `sub`/`jti`/`roles` claims.
    """
    payload = decode_token(token)

    subject = payload.get("sub")
    jti = payload.get("jti")
    roles = payload.get("roles")

    if not subject or not jti or roles is None:
        raise InvalidTokenError()

    try:
        user_id = uuid.UUID(str(subject))
        session_id = uuid.UUID(str(jti))
    except ValueError as exc:
        raise InvalidTokenError() from exc

    return CurrentUser(id=user_id, session_id=session_id, roles=list(roles))
