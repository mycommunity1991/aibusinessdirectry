"""
OAuth sign-in orchestration (AUTH-002).

Routes an incoming provider ID token to the matching `IdTokenVerifier`
(Decision 5, `Plan_S02_AUTH-002.md`) and collapses *any* verification
failure -- bad signature, expired, wrong audience/issuer, malformed
token, JWKS fetch failure, or an unsupported provider -- into the single
generic `InvalidIdentityTokenError` (AC6). The caller (the API layer)
never learns which specific check failed.
"""

from app.core.exceptions import InvalidIdentityTokenError
from app.modules.identity.models import AuthProvider
from app.modules.identity.services.id_token_verifier import (
    IdentityClaims,
    IdTokenVerifier,
)


class OAuthService:
    """Verifies a provider ID token against the matching `IdTokenVerifier`."""

    def __init__(self, verifiers: dict[AuthProvider, IdTokenVerifier]) -> None:
        self._verifiers = verifiers

    async def verify_identity(
        self, provider: AuthProvider, id_token: str
    ) -> IdentityClaims:
        """
        Verify `id_token` against the verifier configured for `provider`.

        Raises:
            InvalidIdentityTokenError: on any verification failure, or if
                no verifier is configured for `provider` -- always the
                same generic message (AC6).
        """
        verifier = self._verifiers.get(provider)
        if verifier is None:
            raise InvalidIdentityTokenError()

        try:
            return await verifier.verify(id_token)
        except InvalidIdentityTokenError:
            raise
        except Exception as exc:
            # Defense in depth: any unexpected failure from the verifier
            # (a bug, an unhandled edge case) must never leak a detailed
            # error to the caller -- it collapses into the same generic
            # authentication failure as an intentionally rejected token.
            raise InvalidIdentityTokenError() from exc
