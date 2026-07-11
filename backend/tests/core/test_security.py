from datetime import timedelta

import pytest

from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.core.security import (
    create_access_token,
    decode_token,
    get_token_expiry,
    hash_password,
    verify_password,
)


def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)
    assert hashed.startswith("$argon2id$")

    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_access_token():
    subject = "user_123"
    token = create_access_token(subject=subject)

    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == subject
    assert "exp" in payload


def test_decode_invalid_token():
    with pytest.raises(InvalidTokenError):
        decode_token("invalid.token.string")


def test_decode_expired_token():
    subject = "user_123"
    # Create a token that expired 1 second ago
    expires_delta = timedelta(seconds=-1)
    token = create_access_token(subject=subject, expires_delta=expires_delta)

    with pytest.raises(ExpiredTokenError):
        decode_token(token)


def test_get_token_expiry():
    expiry = get_token_expiry()
    assert expiry is not None
