"""
Test-only signed ID token factory (AUTH-002, Decision 14 --
`Plan_S02_AUTH-002.md`).

Generates a real RSA keypair at test time, signs test ID tokens shaped
like real Google/Apple identity tokens (`iss`/`aud`/`sub`/`email`/
`email_verified`/`exp`), and serves a matching JWKS document via
`httpx.MockTransport`. This lets tests exercise the *actual*
`JwksIdTokenVerifier` signature/claim-checking code -- not a stubbed-out
verifier -- while guaranteeing zero real network calls to
`googleapis.com`/`appleid.apple.com` (AC8).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from jose.constants import ALGORITHMS


class IdTokenFactory:
    """Owns one RSA keypair and mints RS256-signed test ID tokens with it."""

    def __init__(self, kid: str | None = None) -> None:
        self.kid = kid or f"test-key-{uuid.uuid4().hex[:8]}"
        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        self._jwk_key = jwk.construct(self._private_key, algorithm=ALGORITHMS.RS256)

    def public_jwk(self) -> dict[str, Any]:
        """This keypair's public key, as a JWK dict suitable for a JWKS document."""
        data = self._jwk_key.public_key().to_dict()
        data["kid"] = self.kid
        data["use"] = "sig"
        return data

    def sign(
        self,
        *,
        issuer: str,
        audience: str | list[str],
        subject: str = "test-subject",
        email: str | None = "person@example.com",
        email_verified: bool | str = True,
        expires_delta: timedelta = timedelta(minutes=5),
        extra_claims: Mapping[str, Any] | None = None,
        kid: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> str:
        """
        Signs a test ID token with this factory's private key.

        By default, the token's `kid` header is set to this factory's
        `kid` (or the explicit `kid` argument, if given). Pass `headers`
        directly (e.g. `headers={}`) to produce a token with no `kid`
        header at all, for testing that failure mode specifically.
        """
        now = datetime.now(UTC)
        claims: dict[str, Any] = {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "iat": now,
            "exp": now + expires_delta,
        }
        if email is not None:
            claims["email"] = email
            claims["email_verified"] = email_verified
        if extra_claims:
            claims.update(extra_claims)

        if headers is None:
            headers = {"kid": kid if kid is not None else self.kid}

        return jwt.encode(
            claims,
            self._private_key,
            algorithm=ALGORITHMS.RS256,
            headers=headers,
        )


class JwksTestServer:
    """
    Serves a JWKS document assembled from a mutable set of
    `IdTokenFactory` keys via `httpx.MockTransport`, bound to exactly one
    URL (any other URL yields a 404 -- this also guarantees no request,
    however constructed, ever reaches a real host).

    Tracks how many times the JWKS endpoint has been requested, so tests
    can assert on cache-hit/refetch behavior (e.g. an unrecognized `kid`
    triggering exactly one refetch).
    """

    def __init__(self, jwks_url: str, keys: list[IdTokenFactory] | None = None) -> None:
        self.jwks_url = jwks_url
        self.keys: list[IdTokenFactory] = list(keys) if keys else []
        self.request_count = 0

    def add_key(self, factory: IdTokenFactory) -> None:
        self.keys.append(factory)

    def jwks_document(self) -> dict[str, Any]:
        return {"keys": [factory.public_jwk() for factory in self.keys]}

    def _handle_request(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == self.jwks_url:
            self.request_count += 1
            return httpx.Response(200, json=self.jwks_document())
        # Anything other than the exact configured JWKS URL is rejected
        # rather than silently succeeding -- a defensive guard against a
        # verifier accidentally hitting a different (or real) host.
        return httpx.Response(404, json={"error": "unexpected host"})

    def http_client(self) -> httpx.AsyncClient:
        """A fresh `httpx.AsyncClient` bound to this server's fake transport."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self._handle_request))
