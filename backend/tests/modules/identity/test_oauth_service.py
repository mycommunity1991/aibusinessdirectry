"""
Unit tests for `OAuthService` (AUTH-002, AC6): correct provider routing,
and generic-failure wrapping of any verifier exception.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import InvalidIdentityTokenError
from app.modules.identity.models import AuthProvider
from app.modules.identity.services.id_token_verifier import (
    IdentityClaims,
    IdTokenVerifier,
)
from app.modules.identity.services.oauth_service import OAuthService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _fake_verifier(
    *, return_value: IdentityClaims | None = None, side_effect: Exception | None = None
) -> IdTokenVerifier:
    verifier = AsyncMock(spec=IdTokenVerifier)
    if side_effect is not None:
        verifier.verify.side_effect = side_effect
    else:
        verifier.verify.return_value = return_value
    return verifier


@pytest.mark.anyio
async def test_routes_to_the_google_verifier_for_google_provider() -> None:
    expected_claims = IdentityClaims(
        subject="g-sub", email="a@b.com", email_verified=True
    )
    google_verifier = _fake_verifier(return_value=expected_claims)
    apple_verifier = _fake_verifier(return_value=None)
    service = OAuthService(
        {AuthProvider.GOOGLE: google_verifier, AuthProvider.APPLE: apple_verifier}
    )

    claims = await service.verify_identity(AuthProvider.GOOGLE, "some-token")

    assert claims is expected_claims
    google_verifier.verify.assert_awaited_once_with("some-token")
    apple_verifier.verify.assert_not_awaited()


@pytest.mark.anyio
async def test_routes_to_the_apple_verifier_for_apple_provider() -> None:
    expected_claims = IdentityClaims(subject="a-sub", email=None, email_verified=False)
    google_verifier = _fake_verifier(return_value=None)
    apple_verifier = _fake_verifier(return_value=expected_claims)
    service = OAuthService(
        {AuthProvider.GOOGLE: google_verifier, AuthProvider.APPLE: apple_verifier}
    )

    claims = await service.verify_identity(AuthProvider.APPLE, "some-token")

    assert claims is expected_claims
    apple_verifier.verify.assert_awaited_once_with("some-token")
    google_verifier.verify.assert_not_awaited()


@pytest.mark.anyio
async def test_unconfigured_provider_raises_generic_error() -> None:
    service = OAuthService({AuthProvider.GOOGLE: _fake_verifier(return_value=None)})

    with pytest.raises(InvalidIdentityTokenError):
        await service.verify_identity(AuthProvider.APPLE, "some-token")


@pytest.mark.anyio
async def test_verifier_invalid_identity_token_error_propagates_unchanged() -> None:
    verifier = _fake_verifier(side_effect=InvalidIdentityTokenError())
    service = OAuthService({AuthProvider.GOOGLE: verifier})

    with pytest.raises(InvalidIdentityTokenError):
        await service.verify_identity(AuthProvider.GOOGLE, "bad-token")


@pytest.mark.anyio
async def test_any_other_verifier_exception_is_wrapped_generically() -> None:
    """AC6: even an unexpected, non-`InvalidIdentityTokenError` failure
    from the verifier (a bug, an unhandled edge case) must never leak a
    detailed error -- it collapses into the same generic error."""
    verifier = _fake_verifier(side_effect=ValueError("some internal detail"))
    service = OAuthService({AuthProvider.GOOGLE: verifier})

    with pytest.raises(InvalidIdentityTokenError) as exc_info:
        await service.verify_identity(AuthProvider.GOOGLE, "bad-token")

    assert "some internal detail" not in str(exc_info.value)
