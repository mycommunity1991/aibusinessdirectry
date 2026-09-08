"""Dependency-injection providers for the Identity module."""

from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.modules.audit.dependencies import get_audit_service
from app.modules.audit.services.audit_service import AuditService
from app.modules.customer.dependencies import get_customer_service
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import AuthProvider
from app.modules.identity.repositories.device_repository import DeviceRepository
from app.modules.identity.repositories.otp_verification_repository import (
    OtpVerificationRepository,
)
from app.modules.identity.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.session_repository import SessionRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.id_token_verifier import (
    IdTokenVerifier,
    JwksIdTokenVerifier,
)
from app.modules.identity.services.oauth_service import OAuthService
from app.modules.identity.services.otp_service import OtpService
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.identity.services.session_service import SessionService
from app.modules.identity.services.sms_sender import ConsoleSmsSender, SmsSender

# Google/Apple JWKS endpoints and accepted issuers (Decision 3,
# `Plan_S02_AUTH-002.md`). Exposed as module-level constants so tests can
# point a fake transport at the exact same URL a `JwksIdTokenVerifier`
# instance is configured with.
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUERS = frozenset({"https://appleid.apple.com"})

# Module-level singleton, mirroring `app.core.redis.redis_client` --
# created once at import time (no I/O until the first request) and
# reused across requests so `JwksIdTokenVerifier`'s in-memory JWKS cache
# actually persists between calls instead of refetching every request.
_oauth_http_client = httpx.AsyncClient()


def _apple_client_ids() -> frozenset[str]:
    ids = settings.APPLE_OAUTH_CLIENT_IDS
    return frozenset(ids if isinstance(ids, list) else [ids])


_google_id_token_verifier = JwksIdTokenVerifier(
    http_client=_oauth_http_client,
    jwks_url=GOOGLE_JWKS_URL,
    issuers=GOOGLE_ISSUERS,
    audiences=frozenset({settings.GOOGLE_OAUTH_CLIENT_ID}),
)
_apple_id_token_verifier = JwksIdTokenVerifier(
    http_client=_oauth_http_client,
    jwks_url=APPLE_JWKS_URL,
    issuers=APPLE_ISSUERS,
    audiences=_apple_client_ids(),
)


def get_google_id_token_verifier() -> IdTokenVerifier:
    """
    Provides the Google `IdTokenVerifier`. Overridden in tests with a
    `JwksIdTokenVerifier` bound to an `httpx.MockTransport` (AC8 -- no
    test may call the real Google endpoint).
    """
    return _google_id_token_verifier


def get_apple_id_token_verifier() -> IdTokenVerifier:
    """
    Provides the Apple `IdTokenVerifier`. Overridden in tests with a
    `JwksIdTokenVerifier` bound to an `httpx.MockTransport` (AC8 -- no
    test may call the real Apple endpoint).
    """
    return _apple_id_token_verifier


def get_oauth_service(
    google_verifier: Annotated[IdTokenVerifier, Depends(get_google_id_token_verifier)],
    apple_verifier: Annotated[IdTokenVerifier, Depends(get_apple_id_token_verifier)],
) -> OAuthService:
    """Provides an `OAuthService` routing to the correct verifier per provider."""
    return OAuthService(
        {
            AuthProvider.GOOGLE: google_verifier,
            AuthProvider.APPLE: apple_verifier,
        }
    )


def get_sms_sender() -> SmsSender:
    """
    Provides the `SmsSender` implementation. Only a stub (`ConsoleSmsSender`)
    is wired up in this story (AUTH-001, AC4) — no real provider is called.
    """
    return ConsoleSmsSender()


def get_otp_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    sms_sender: Annotated[SmsSender, Depends(get_sms_sender)],
) -> OtpService:
    """Provides an `OtpService` bound to the request-scoped DB session."""
    return OtpService(OtpVerificationRepository(db), sms_sender, db)


def get_device_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeviceRepository:
    """Provides a `DeviceRepository` bound to the request-scoped DB session."""
    return DeviceRepository(db)


def get_session_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionRepository:
    """Provides a `SessionRepository` bound to the request-scoped DB session."""
    return SessionRepository(db)


def get_refresh_token_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshTokenRepository:
    """Provides a `RefreshTokenRepository` bound to the request-scoped DB session."""
    return RefreshTokenRepository(db)


def get_session_service(
    device_repository: Annotated[DeviceRepository, Depends(get_device_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    refresh_token_repository: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SessionService:
    """Provides a `SessionService` bound to the request-scoped DB session."""
    return SessionService(
        device_repository=device_repository,
        session_repository=session_repository,
        refresh_token_repository=refresh_token_repository,
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
        audit_service=audit_service,
    )


def get_role_assignment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleAssignmentService:
    """
    Provides a `RoleAssignmentService` bound to the request-scoped DB
    session (PRO-001, Decision 1). Imported into `provider/dependencies.py`
    exactly the way `customer/dependencies.py`'s `get_customer_service` is
    imported here today -- same shape, reversed direction.
    """
    return RoleAssignmentService(RoleRepository(db))


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    customer_service: Annotated[CustomerService, Depends(get_customer_service)],
) -> AuthService:
    """Provides an `AuthService` bound to the request-scoped DB session."""
    return AuthService(
        session=db,
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
        otp_service=otp_service,
        session_service=session_service,
        audit_service=audit_service,
        customer_service=customer_service,
    )
