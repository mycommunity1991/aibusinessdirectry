import uuid

import pytest

from app.api.dependencies import CurrentUser, get_current_user, get_token
from app.core.exceptions import AuthenticationRequiredError, InvalidTokenError
from app.core.security import create_access_token


def test_get_token_success():
    token = get_token("valid.token.string")
    assert token == "valid.token.string"


def test_get_token_missing():
    with pytest.raises(AuthenticationRequiredError) as exc_info:
        get_token(None)
    assert "Authentication credentials were not provided" in str(exc_info.value.message)


def test_get_current_user_returns_current_user_for_a_valid_token():
    """AUTH-003: a valid access token resolves to a `CurrentUser` with the
    token's `sub`/`jti`/`roles` claims."""
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = create_access_token(
        subject=str(user_id), roles=["customer"], jti=str(session_id)
    )

    current_user = get_current_user(token)

    assert isinstance(current_user, CurrentUser)
    assert current_user.id == user_id
    assert current_user.session_id == session_id
    assert current_user.roles == ["customer"]


def test_get_current_user_rejects_a_malformed_token():
    with pytest.raises(InvalidTokenError):
        get_current_user("not-a-real-token")


def test_get_current_user_rejects_a_token_missing_required_claims():
    """A token missing `jti`/`roles` (e.g. minted by pre-AUTH-003 code)
    must be rejected, not silently accepted with missing fields."""
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings

    incomplete_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(
        incomplete_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    with pytest.raises(InvalidTokenError):
        get_current_user(token)
