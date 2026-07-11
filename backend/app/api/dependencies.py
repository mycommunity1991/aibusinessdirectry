from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.constants import API_PREFIX
from app.core.exceptions import AuthenticationRequiredError

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


def get_current_user(token: Annotated[str, Depends(get_token)]) -> None:
    """
    Placeholder dependency for extracting the current user.
    Authentication is intentionally not implemented in this sprint.

    Raises:
        AuthenticationRequiredError unconditionally.
    """
    raise AuthenticationRequiredError(
        message="Authentication is not yet implemented. Please refer to BF-011."
    )
