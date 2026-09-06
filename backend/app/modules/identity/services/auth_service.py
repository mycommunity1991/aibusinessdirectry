"""
Registration/login orchestration for both the mobile OTP path (AUTH-001)
and the Google/Apple OAuth path (AUTH-002).

Coordinates OTP verification or already-verified OAuth identity claims
with find-or-create User semantics, then delegates device/session/
refresh-token issuance to `SessionService` (AUTH-003). Also provisions a
default `customer_profiles`/`customer_preferences` row for every new
Account (CUS-001, AC2), via `CustomerService.provision_default_profile`
-- called inline inside each `is_new_user` branch, using this same
request-scoped `AsyncSession` (flush only, never commit), mirroring the
already-shipped `identity -> audit` cross-module pattern exactly
(Decision 1, `Plan_S03_CUS-001.md`).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_CUSTOMER
from app.core.exceptions import AuthenticationRequiredError
from app.modules.audit.services.audit_service import AuditService
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import (
    AuthProvider,
    DevicePlatform,
    LanguageCode,
    OtpPurpose,
    User,
    UserRole,
    UserStatus,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.user_repository import UserRepository
from app.modules.identity.services.id_token_verifier import IdentityClaims
from app.modules.identity.services.otp_service import OtpService
from app.modules.identity.services.session_service import SessionService


class AuthService:
    """Orchestrates the mobile OTP and OAuth registration/login flows."""

    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        otp_service: OtpService,
        session_service: SessionService,
        audit_service: AuditService,
        customer_service: CustomerService,
    ) -> None:
        self.session = session
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.otp_service = otp_service
        self.session_service = session_service
        self.audit_service = audit_service
        self.customer_service = customer_service

    async def get_current_user_summary(
        self, user_id: uuid.UUID
    ) -> tuple[User, list[str]]:
        """
        Backs `GET /auth/me` (AUTH-004, AC5): the caller's own id, roles,
        and account status. `user_id` comes from an already-validated
        JWT's `sub` claim (`require_role()`/`get_current_user` ran
        first), so a missing row here would indicate the user was
        deleted after the token was issued -- treated the same as "not
        authenticated" rather than a more specific error, since the
        token itself is no longer meaningful.
        """
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationRequiredError()
        role_names = await self.role_repository.get_role_names_for_user(user_id)
        return user, role_names

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
        self,
        phone_country_code: str,
        phone_number: str,
        code: str,
        device_platform: DevicePlatform,
        device_name: str | None,
        ip_address: str | None,
        user_agent: str | None,
        accept_language_header: str | None = None,
    ) -> tuple[User, str, str, list[str]]:
        """
        Verify the submitted OTP, then transparently find-or-create the
        `User` for this phone number (AC6/AC7), start a new session/
        device/refresh-token (AUTH-003), and return the authenticated
        `User`, the access token, the raw refresh token, and the user's
        current role names. `accept_language_header` is only ever read
        for a brand-new `User` (CUS-001, AC3) -- passed through as-is
        from the request's raw `Accept-Language` header, never parsed
        here.
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
            # CUS-001, AC2: provisions `customer_profiles`/
            # `customer_preferences` in the same transaction as the
            # `User` row above -- flush only, never commit.
            await self.customer_service.provision_default_profile(
                user_id=user.id, accept_language_header=accept_language_header
            )

        role_names = await self.role_repository.get_role_names_for_user(user.id)
        (
            _session,
            access_token,
            refresh_token,
        ) = await self.session_service.start_session(
            user=user,
            roles=role_names,
            device_platform=device_platform,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if is_new_user:
            await self.audit_service.record_registration(
                user_id=user.id,
                auth_provider=AuthProvider.MOBILE_OTP.value,
                ip_address=ip_address,
            )
        await self.audit_service.record_login(
            user_id=user.id,
            auth_provider=AuthProvider.MOBILE_OTP.value,
            ip_address=ip_address,
        )

        return user, access_token, refresh_token, role_names

    async def authenticate_with_oauth(
        self,
        provider: AuthProvider,
        claims: IdentityClaims,
        device_platform: DevicePlatform,
        device_name: str | None,
        ip_address: str | None,
        user_agent: str | None,
        accept_language_header: str | None = None,
    ) -> tuple[User, str, str, list[str]]:
        """
        Find-or-create the `User` for this `(auth_provider,
        external_auth_subject)` pair (AC3/AC4), start a new session/
        device/refresh-token (AUTH-003), and return the authenticated
        `User`, the access token, the raw refresh token, and the user's
        current role names -- mirrors `verify_otp_and_authenticate`'s
        shape exactly (Decision 5, `Plan_S02_AUTH-002.md`). `claims` must
        already be server-verified by `OAuthService`; this method never
        performs its own token verification. `accept_language_header` is
        only ever read for a brand-new `User` (CUS-001, AC3).

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
            # CUS-001, AC2: provisions `customer_profiles`/
            # `customer_preferences` in the same transaction as the
            # `User` row above -- flush only, never commit.
            await self.customer_service.provision_default_profile(
                user_id=user.id, accept_language_header=accept_language_header
            )

        role_names = await self.role_repository.get_role_names_for_user(user.id)
        (
            _session,
            access_token,
            refresh_token,
        ) = await self.session_service.start_session(
            user=user,
            roles=role_names,
            device_platform=device_platform,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if is_new_user:
            await self.audit_service.record_registration(
                user_id=user.id,
                auth_provider=provider.value,
                ip_address=ip_address,
            )
        await self.audit_service.record_login(
            user_id=user.id,
            auth_provider=provider.value,
            ip_address=ip_address,
        )

        return user, access_token, refresh_token, role_names
