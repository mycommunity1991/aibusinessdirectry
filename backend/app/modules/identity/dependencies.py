"""Dependency-injection providers for the Identity module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.identity.repositories.otp_verification_repository import (
    OtpVerificationRepository,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.otp_service import OtpService
from app.modules.identity.services.sms_sender import ConsoleSmsSender, SmsSender


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


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
) -> AuthService:
    """Provides an `AuthService` bound to the request-scoped DB session."""
    return AuthService(
        session=db,
        user_repository=UserRepository(db),
        role_repository=RoleRepository(db),
        otp_service=otp_service,
    )
