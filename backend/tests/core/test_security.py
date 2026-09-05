from datetime import timedelta

import pytest

from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.core.security import (
    create_access_token,
    decode_token,
    generate_refresh_token,
    get_token_expiry,
    hash_password,
    hash_refresh_token,
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
    token = create_access_token(subject=subject, roles=["customer"], jti="session-1")

    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == subject
    assert "exp" in payload


def test_access_token_payload_is_exactly_sub_exp_iat_jti_roles():
    """AC2: the decoded payload must contain exactly `sub`, `exp`, `iat`,
    `jti`, `roles` -- no email, phone, or any other PII."""
    token = create_access_token(
        subject="user_123", roles=["customer", "provider"], jti="session-abc"
    )

    payload = decode_token(token)

    assert set(payload.keys()) == {"sub", "exp", "iat", "jti", "roles"}
    assert payload["sub"] == "user_123"
    assert payload["jti"] == "session-abc"
    assert payload["roles"] == ["customer", "provider"]
    assert "iat" in payload


def test_access_token_defaults_to_a_15_minute_expiry():
    """AC2: a fresh access token expires 15 minutes after issuance."""
    from app.core.config import settings

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    token = create_access_token(subject="user_123", roles=[], jti="session-1")
    payload = decode_token(token)

    assert payload["exp"] - payload["iat"] == 15 * 60


def test_decode_invalid_token():
    with pytest.raises(InvalidTokenError):
        decode_token("invalid.token.string")


def test_decode_expired_token():
    subject = "user_123"
    # Create a token that expired 1 second ago
    expires_delta = timedelta(seconds=-1)
    token = create_access_token(
        subject=subject, roles=[], jti="session-1", expires_delta=expires_delta
    )

    with pytest.raises(ExpiredTokenError):
        decode_token(token)


def test_get_token_expiry():
    expiry = get_token_expiry()
    assert expiry is not None


def test_generate_refresh_token_returns_a_high_entropy_opaque_string():
    """AC3: a refresh token is an opaque random string."""
    token_a = generate_refresh_token()
    token_b = generate_refresh_token()

    assert isinstance(token_a, str)
    assert len(token_a) >= 32
    assert token_a != token_b


def test_hash_refresh_token_is_deterministic_sha256_not_argon2id():
    """AC3/Decision 5: SHA-256, not Argon2id -- a fast, deterministic
    hash of a high-entropy opaque value (the raw value is never itself
    persisted, only its hash)."""
    import hashlib

    token = "some-opaque-refresh-token-value"
    hashed = hash_refresh_token(token)

    assert hashed == hashlib.sha256(token.encode("utf-8")).hexdigest()
    # Deterministic: hashing the same raw value twice yields the same hash
    # (unlike Argon2id, which salts every call) -- required so a
    # presented raw token can be looked up by its hash.
    assert hash_refresh_token(token) == hashed
    assert not hashed.startswith("$argon2id$")
