import pytest

from app.api.dependencies import get_current_user, get_token
from app.core.exceptions import AuthenticationRequiredError


def test_get_token_success():
    token = get_token("valid.token.string")
    assert token == "valid.token.string"


def test_get_token_missing():
    with pytest.raises(AuthenticationRequiredError) as exc_info:
        get_token(None)
    assert "Authentication credentials were not provided" in str(exc_info.value.message)


def test_get_current_user_placeholder():
    with pytest.raises(AuthenticationRequiredError) as exc_info:
        get_current_user("some_token")
    assert "Authentication is not yet implemented" in str(exc_info.value.message)
