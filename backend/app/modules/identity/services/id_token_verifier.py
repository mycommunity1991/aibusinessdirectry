"""
Generic JWKS-backed ID token verification (AUTH-002).

One verifier implementation serves both Google and Apple sign-in --
their ID tokens are structurally identical (RS256, JWKS-published public
keys, standard `iss`/`aud`/`exp` claims); only the configured
`jwks_url`, accepted issuer(s), and accepted audience(s) differ
(Decision 3, `Plan_S02_AUTH-002.md`). No `google-auth`/`PyJWT` dependency
is introduced -- `python-jose` (already a dependency for our own JWT
encode/decode) does the RS256 verification here too.

No token is ever trusted without full server-side verification
(`06_SECURITY.md`) -- signature, issuer, audience, and expiry are all
checked. Every failure mode (bad signature, expired, wrong audience/
issuer, malformed token, JWKS fetch failure, unknown key ID even after a
refetch) raises the single, generic `InvalidIdentityTokenError` (AC6) --
callers never learn which specific check failed.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt

from app.core.exceptions import InvalidIdentityTokenError


@dataclass(frozen=True)
class IdentityClaims:
    """Normalized identity claims extracted from a verified ID token."""

    subject: str
    email: str | None
    email_verified: bool


class IdTokenVerifier(ABC):
    """Verifies a provider ID token and returns its normalized claims."""

    @abstractmethod
    async def verify(self, id_token: str) -> IdentityClaims:
        """
        Verify `id_token`'s signature and standard claims.

        Raises:
            InvalidIdentityTokenError: if the token cannot be verified for
                any reason -- never reveals which specific check failed
                (AC6).
        """


def _normalize_email_verified(value: object) -> bool:
    """
    Google sends `email_verified` as a real bool; Apple sends it as the
    string "true"/"false" -- normalize both to an actual `bool`.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


class JwksIdTokenVerifier(IdTokenVerifier):
    """
    Verifies RS256-signed ID tokens against a provider's published JWKS.

    JWKS is fetched over HTTPS via the injected `httpx.AsyncClient` and
    cached in-memory keyed by `kid` (JSON Web Key ID), with a single
    refetch triggered by an unrecognized `kid` -- a minimal caching
    strategy that transparently handles routine provider key rotation
    without guessing a fixed TTL.
    """

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        jwks_url: str,
        issuers: frozenset[str],
        audiences: frozenset[str],
    ) -> None:
        self._http_client = http_client
        self._jwks_url = jwks_url
        self._issuers = issuers
        self._audiences = audiences
        self._keys_by_kid: dict[str, dict[str, object]] = {}
        self._refresh_lock = asyncio.Lock()

    async def verify(self, id_token: str) -> IdentityClaims:
        try:
            header = jwt.get_unverified_header(id_token)
        except JWTError as exc:
            raise InvalidIdentityTokenError() from exc

        kid = header.get("kid")
        if not kid:
            raise InvalidIdentityTokenError()

        jwk_key = await self._get_key(str(kid))
        if jwk_key is None:
            raise InvalidIdentityTokenError()

        try:
            claims = jwt.decode(
                id_token,
                jwk_key,
                algorithms=["RS256"],
                issuer=list(self._issuers),
                # `aud` is validated manually below against a *set* of
                # acceptable audiences -- python-jose's built-in audience
                # check only supports a single string (see Decision 10,
                # `Plan_S02_AUTH-002.md`, for why Apple needs more than
                # one accepted audience).
                options={"verify_aud": False},
            )
        except JWTError as exc:
            raise InvalidIdentityTokenError() from exc

        if not self._audience_is_accepted(claims.get("aud")):
            raise InvalidIdentityTokenError()

        subject = claims.get("sub")
        if not subject:
            raise InvalidIdentityTokenError()

        return IdentityClaims(
            subject=str(subject),
            email=claims.get("email"),
            email_verified=_normalize_email_verified(claims.get("email_verified")),
        )

    def _audience_is_accepted(self, audience_claim: object) -> bool:
        if isinstance(audience_claim, list):
            audiences_in_token = {str(item) for item in audience_claim}
        elif audience_claim is None:
            audiences_in_token: set[str] = set()
        else:
            audiences_in_token = {str(audience_claim)}
        return bool(audiences_in_token & self._audiences)

    async def _get_key(self, kid: str) -> dict[str, object] | None:
        if kid in self._keys_by_kid:
            return self._keys_by_kid[kid]
        await self._refresh_keys()
        return self._keys_by_kid.get(kid)

    async def _refresh_keys(self) -> None:
        async with self._refresh_lock:
            try:
                response = await self._http_client.get(self._jwks_url)
                response.raise_for_status()
                document = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise InvalidIdentityTokenError() from exc

            keys = document.get("keys", []) if isinstance(document, dict) else []
            self._keys_by_kid = {
                key["kid"]: key
                for key in keys
                if isinstance(key, dict) and "kid" in key
            }
