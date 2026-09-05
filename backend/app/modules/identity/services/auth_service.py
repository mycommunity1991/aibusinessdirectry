"""
Registration/login orchestration for both the mobile OTP path (AUTH-001)
and the Google/Apple OAuth path (AUTH-002).

Coordinates OTP verification or already-verified OAuth identity claims
with find-or-create User semantics and JWT issuance. Deliberately does
not touch `customer_profiles`/`customer_preferences` (AC12 — Customer
domain, CUS-001) or `devices`/`sessions` (AUTH-003).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.modules.identity.models import (
    AuthProvider,
    LanguageCode,
    OtpPurpose,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.id_token_verifier import IdentityClaims
from app.modules.identity.services.otp_service import OtpService


class AuthService:
    """Orchestrates the mobile OTP registration/login flow."""

    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        otp_service: OtpService,
    ) -> None:
        self.session = session
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.otp_service = otp_service

    async def request_otp(self, phone_country_code: str, phone_number: str) -> None:
        """
        Trigger delivery of a login OTP. There is no client-supplied
        registration-vs-login distinction (Decision 7 of
        `Plan_S02_AUTH-001.md`) — this always records `otp_purpose.login`.
        """
        await self.otp_service.request_otp(
            phone_country_code, phone_number, OtpPurpose.LOGIN
        )

    async def verify_otp_and_authenticate(
        self, phone_country_code: str, phone_number: str, code: str
    ) -> tuple[User, str, list[str]]:
        """
        Verify the submitted OTP, then transparently find-or-create the
        `User` for this phone number (AC6/AC7) and issue a stateless JWT
        access token (Decision 8 — no session/device row is created here).

        Returns the authenticated `User`, the access token, and the
        user's current role names.
        """
        await self.otp_service.verify_otp(
            phone_country_code, phone_number, OtpPurpose.LOGIN, code
        )

        user = await self.user_repository.get_by_phone(phone_country_code, phone_number)
        is_new_user = user is None
        now = datetime.now(UTC)

        if user is None:
            user = await self.user_repository.create(
                {
                    "phone_country_code": phone_country_code,
                    "phone_number": phone_number,
                    "phone_verified_at": now,
                    "auth_provider": AuthProvider.MOBILE_OTP,
                    "status": UserStatus.ACTIVE,
                    "preferred_language": LanguageCode.EN,
                    "last_login_at": now,
                }
            )
        else:
            user.last_login_at = now
            await self.session.flush()

        if is_new_user:
            customer_role = await self.role_repository.get_by_name(ROLE_CUSTOMER)
            if customer_role is not None:
                self.session.add(UserRole(user_id=user.id, role_id=customer_role.id))
                await self.session.flush()

        role_names = await self._get_role_names(user.id)
        token = create_access_token(subject=str(user.id))
        return user, token, role_names

    async def authenticate_with_oauth(
        self, provider: AuthProvider, claims: IdentityClaims
    ) -> tuple[User, str, list[str]]:
        """
        Find-or-create the `User` for this `(auth_provider,
        external_auth_subject)` pair (AC3/AC4) and issue a stateless JWT
        access token -- mirrors `verify_otp_and_authenticate`'s shape
        exactly (Decision 5, `Plan_S02_AUTH-002.md`). `claims` must
        already be server-verified by `OAuthService`; this method never
        performs its own token verification.

        A different provider presenting the same email as an existing
        account is a distinct row here by design (AC5) -- matching is
        always on `(auth_provider, external_auth_subject)`, never email.

        Email/`email_verified_at` are only ever written at creation time
        (Decision 11) -- a subsequent login never overwrites them, even
        if the provider's claims omit or change the email (a known Apple
        behavior: email is only guaranteed present on first
        authorization).
        """
        user = await self.user_repository.get_by_provider_and_subject(
            provider, claims.subject
        )
        is_new_user = user is None
        now = datetime.now(UTC)

        if user is None:
            user = await self.user_repository.create(
                {
                    "auth_provider": provider,
                    "external_auth_subject": claims.subject,
                    "email": claims.email,
                    "email_verified_at": (
                        now if claims.email and claims.email_verified else None
                    ),
                    "status": UserStatus.ACTIVE,
                    "preferred_language": LanguageCode.EN,
                    "last_login_at": now,
                }
            )
        else:
            user.last_login_at = now
            await self.session.flush()

        if is_new_user:
            customer_role = await self.role_repository.get_by_name(ROLE_CUSTOMER)
            if customer_role is not None:
                self.session.add(UserRole(user_id=user.id, role_id=customer_role.id))
                await self.session.flush()

        role_names = await self._get_role_names(user.id)
        token = create_access_token(subject=str(user.id))
        return user, token, role_names

    async def _get_role_names(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
