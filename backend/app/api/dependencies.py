import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.constants import API_PREFIX
from app.core.exceptions import (
    AuthenticationRequiredError,
    InsufficientRoleError,
    InvalidTokenError,
)
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


class RequireRole:
    """
    A parametrized, composable FastAPI dependency enforcing a role check
    (AUTH-004, AC1) on top of `get_current_user` -- not a replacement for
    it. Because this depends on `get_current_user`, a missing/invalid/
    expired token 401s before the role check ever runs; this class only
    ever raises `InsufficientRoleError` (403), for a validly authenticated
    caller whose `roles` claim doesn't intersect the allowed set (AC2/
    AC3 -- 401 and 403 are structurally never used interchangeably).

    Usable on any endpoint via `Depends(require_role(ROLE_ADMIN))`, etc.
    """

    def __init__(self, *allowed_roles: str) -> None:
        self.allowed_roles = frozenset(allowed_roles)

    def __call__(
        self,
        current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    ) -> CurrentUser:
        if not self.allowed_roles.intersection(current_user.roles):
            raise InsufficientRoleError()
        return current_user


def require_role(*allowed_roles: str) -> RequireRole:
    """Builds a `RequireRole` dependency for the given allowed role names."""
    return RequireRole(*allowed_roles)
