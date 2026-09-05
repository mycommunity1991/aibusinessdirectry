"""
Unit tests for `JwksIdTokenVerifier` (AUTH-002, AC2/AC6/AC8).

Every case runs against a real RSA keypair and a real JWKS document
served over `httpx.MockTransport` (`tests/support/id_token_factory.py`)
-- the actual signature/claim-checking code path is exercised, not a
stubbed-out verifier, and no test ever calls the real Google/Apple
endpoints (AC8).
"""

from datetime import timedelta

import pytest

from app.core.exceptions import InvalidIdentityTokenError
from app.modules.identity.services.id_token_verifier import (
    IdentityClaims,
    JwksIdTokenVerifier,
)
from tests.support.id_token_factory import IdTokenFactory, JwksTestServer

JWKS_URL = "https://example.test/jwks"
ISSUER = "https://accounts.example.com"
AUDIENCE = "test-client-id"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _verifier(client, jwks_url: str = JWKS_URL) -> JwksIdTokenVerifier:
    return JwksIdTokenVerifier(
        http_client=client,
        jwks_url=jwks_url,
        issuers=frozenset({ISSUER}),
        audiences=frozenset({AUDIENCE}),
    )


@pytest.mark.anyio
async def test_valid_token_verifies_and_returns_normalized_claims() -> None:
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(
        issuer=ISSUER,
        audience=AUDIENCE,
        subject="user-123",
        email="person@example.com",
        email_verified=True,
    )

    async with server.http_client() as client:
        claims = await _verifier(client).verify(token)

    assert claims == IdentityClaims(
        subject="user-123", email="person@example.com", email_verified=True
    )


@pytest.mark.anyio
async def test_apple_style_string_email_verified_is_normalized_to_bool() -> None:
    """Apple encodes `email_verified` as the string "true"/"false"."""
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(
        issuer=ISSUER, audience=AUDIENCE, email="a@b.com", email_verified="true"
    )

    async with server.http_client() as client:
        claims = await _verifier(client).verify(token)

    assert claims.email_verified is True


@pytest.mark.anyio
async def test_tampered_signature_is_rejected() -> None:
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(issuer=ISSUER, audience=AUDIENCE)
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(tampered)


@pytest.mark.anyio
async def test_expired_token_is_rejected() -> None:
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(
        issuer=ISSUER, audience=AUDIENCE, expires_delta=timedelta(minutes=-5)
    )

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(token)


@pytest.mark.anyio
async def test_wrong_audience_is_rejected() -> None:
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(issuer=ISSUER, audience="some-other-client-id")

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(token)


@pytest.mark.anyio
async def test_one_of_multiple_accepted_audiences_is_allowed() -> None:
    """Apple's native vs. web-fallback flows issue different `aud` values
    -- a verifier configured with multiple accepted audiences must accept
    a token matching any one of them (Decision 10, Plan_S02_AUTH-002)."""
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(issuer=ISSUER, audience="android-services-id")

    async with server.http_client() as client:
        verifier = JwksIdTokenVerifier(
            http_client=client,
            jwks_url=JWKS_URL,
            issuers=frozenset({ISSUER}),
            audiences=frozenset({"ios-bundle-id", "android-services-id"}),
        )
        claims = await verifier.verify(token)

    assert claims.subject == "test-subject"


@pytest.mark.anyio
async def test_wrong_issuer_is_rejected() -> None:
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(issuer="https://evil.example.com", audience=AUDIENCE)

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(token)


@pytest.mark.anyio
async def test_malformed_token_is_rejected() -> None:
    async with JwksTestServer(JWKS_URL).http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify("not-a-jwt")


@pytest.mark.anyio
async def test_missing_kid_header_is_rejected() -> None:
    """A token signed without a `kid` header can never be matched to a
    JWKS entry -- rejected outright rather than attempting every key."""
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    token = factory.sign(issuer=ISSUER, audience=AUDIENCE, headers={})

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(token)


@pytest.mark.anyio
async def test_unknown_kid_triggers_a_jwks_refetch() -> None:
    """The first verify() call populates the cache from an empty state
    (one fetch). A second token signed with a *new* kid the cache has
    never seen must trigger exactly one more fetch, after which the
    rotated key is found and the token verifies."""
    factory_one = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory_one])
    token_one = factory_one.sign(issuer=ISSUER, audience=AUDIENCE)

    async with server.http_client() as client:
        verifier = _verifier(client)

        await verifier.verify(token_one)
        assert server.request_count == 1

        # Simulate provider key rotation: a new key appears, and a token
        # is signed with it before the verifier has ever seen its kid.
        factory_two = IdTokenFactory(kid="kid-2")
        server.add_key(factory_two)
        token_two = factory_two.sign(issuer=ISSUER, audience=AUDIENCE)

        claims = await verifier.verify(token_two)
        assert server.request_count == 2
        assert claims.subject == "test-subject"


@pytest.mark.anyio
async def test_persistently_unknown_kid_is_rejected_after_refetch() -> None:
    """A `kid` that isn't in the JWKS document even after a refetch (e.g.
    a forged token) is rejected -- not retried indefinitely."""
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])
    forged = IdTokenFactory(kid="kid-does-not-exist")
    token = forged.sign(issuer=ISSUER, audience=AUDIENCE)

    async with server.http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(token)
    assert server.request_count == 1


@pytest.mark.anyio
async def test_jwks_fetch_failure_is_rejected_generically() -> None:
    """A non-200 JWKS response (fetch failure) collapses into the same
    generic error as every other failure mode (AC6)."""
    async with JwksTestServer("https://example.test/other-url").http_client() as client:
        with pytest.raises(InvalidIdentityTokenError):
            await _verifier(client).verify(
                IdTokenFactory(kid="kid-1").sign(issuer=ISSUER, audience=AUDIENCE)
            )


@pytest.mark.anyio
async def test_cached_key_does_not_require_a_second_fetch() -> None:
    """Verifying two different tokens signed by the same already-cached
    key must not trigger a second JWKS fetch."""
    factory = IdTokenFactory(kid="kid-1")
    server = JwksTestServer(JWKS_URL, [factory])

    async with server.http_client() as client:
        verifier = _verifier(client)
        token_a = factory.sign(issuer=ISSUER, audience=AUDIENCE, subject="a")
        token_b = factory.sign(issuer=ISSUER, audience=AUDIENCE, subject="b")
        await verifier.verify(token_a)
        await verifier.verify(token_b)

    assert server.request_count == 1
