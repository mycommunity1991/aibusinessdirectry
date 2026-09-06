"""
Device/session/refresh-token lifecycle (AUTH-003).

Separate from `AuthService` -- same separation-of-concerns precedent as
`OAuthService`/`AuthService` in AUTH-002 (Decision 6,
`Plan_S02_AUTH-003.md`). `AuthService` stays focused on identity
verification and User find-or-create; `SessionService` owns device,
session, and refresh-token issuance/rotation/revocation.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.authorization import ensure_owner_or_not_found
from app.core.config import settings
from app.core.exceptions import InvalidRefreshTokenError, SessionNotFoundError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.modules.audit.services.audit_service import AuditService
from app.modules.identity.models import DevicePlatform, Session, User
from app.modules.identity.repositories.device_repository import DeviceRepository
from app.modules.identity.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.repositories.session_repository import SessionRepository
from app.modules.identity.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class SessionListItem:
    """A single row of `GET /sessions`' response (AC7), pre-joined with
    its device's name/platform/last-seen and flagged as current or not."""

    id: uuid.UUID
    device_name: str | None
    platform: str | None
    last_seen_at: datetime | None
    created_at: datetime
    is_current: bool


class SessionService:
    """Orchestrates device capture, session creation, refresh-token
    rotation, and session/refresh-token revocation."""

    def __init__(
        self,
        device_repository: DeviceRepository,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        audit_service: AuditService,
    ) -> None:
        self.device_repository = device_repository
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.audit_service = audit_service

    async def start_session(
        self,
        user: User,
        roles: list[str],
        device_platform: DevicePlatform,
        device_name: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[Session, str, str]:
        """
        Records/updates the caller's `Device` row (AC6), creates a new
        `Session`, mints its first `RefreshToken`, and issues an access
        token whose `jti` is the new session's id (Decision 1). Called at
        the end of both `AuthService.verify_otp_and_authenticate` and
        `AuthService.authenticate_with_oauth`.

        Returns the new `Session`, the access token, and the raw
        (unhashed) refresh token -- the only moment the raw refresh token
        value ever exists; only its hash is persisted (AC3).
        """
        device = await self.device_repository.find_or_create(
            user.id, device_platform, device_name
        )

        now = datetime.now(UTC)
        lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = await self.session_repository.create_session(
            user_id=user.id,
            device_id=device.id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + lifetime,
        )

        raw_refresh_token = generate_refresh_token()
        await self.refresh_token_repository.create_refresh_token(
            user_id=user.id,
            session_id=session.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=now + lifetime,
        )

        access_token = create_access_token(
            subject=str(user.id), roles=roles, jti=str(session.id)
        )
        return session, access_token, raw_refresh_token

    async def refresh(self, raw_refresh_token: str) -> tuple[User, list[str], str, str]:
        """
        Rotates a refresh token (AC4): validates it, issues a new
        access/refresh pair, and invalidates the token just used.

        Reuse-detection cascade (Decision 7): if the presented token is
        found but already revoked/rotated-away, that's a signal it may
        have been stolen and replayed after the legitimate client already
        rotated past it -- the entire session (and every refresh token in
        its chain) is revoked in response, not just this one call
        rejected.

        Raises:
            InvalidRefreshTokenError: token not found, expired, revoked,
                already rotated away, or its session is no longer active
                (AC5). Deliberately generic -- never reveals which.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        record = await self.refresh_token_repository.get_by_token_hash(token_hash)
        now = datetime.now(UTC)

        if record is None:
            raise InvalidRefreshTokenError()

        if record.revoked_at is not None:
            # Already used (rotated away) or explicitly revoked -- reject
            # this call and, as hardening, revoke the whole session.
            await self.session_repository.revoke(record.session_id, now)
            await self.refresh_token_repository.revoke_all_for_session(
                record.session_id, now
            )
            raise InvalidRefreshTokenError()

        if record.expires_at <= now:
            raise InvalidRefreshTokenError()

        session = await self.session_repository.get_active_by_id(record.session_id)
        if session is None:
            raise InvalidRefreshTokenError()

        user = await self.user_repository.get_by_id(record.user_id)
        if user is None:
            raise InvalidRefreshTokenError()

        roles = await self.role_repository.get_role_names_for_user(record.user_id)

        lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_raw_refresh_token = generate_refresh_token()
        new_record = await self.refresh_token_repository.create_refresh_token(
            user_id=record.user_id,
            session_id=record.session_id,
            token_hash=hash_refresh_token(new_raw_refresh_token),
            expires_at=now + lifetime,
        )
        await self.refresh_token_repository.mark_replaced(record.id, new_record.id, now)

        new_access_token = create_access_token(
            subject=str(record.user_id), roles=roles, jti=str(record.session_id)
        )
        return user, roles, new_access_token, new_raw_refresh_token

    async def list_active_sessions(
        self, user_id: uuid.UUID, current_session_id: uuid.UUID | None
    ) -> list[SessionListItem]:
        """Lists the caller's active sessions with device info, flagging
        the current one (AC7)."""
        rows = await self.session_repository.list_active_for_user_with_device(user_id)
        return [
            SessionListItem(
                id=session.id,
                device_name=device.device_name if device else None,
                platform=(device.platform.value if device else None),
                last_seen_at=device.last_seen_at if device else None,
                created_at=session.created_at,
                is_current=(session.id == current_session_id),
            )
            for session, device in rows
        ]

    async def revoke_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        current_session_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        Revokes a single session and every refresh token in its chain
        (AC8). Ownership is enforced via `ensure_owner_or_not_found`
        (AUTH-004, AC4): a session that doesn't exist, or exists but
        belongs to a different user, raises the same `SessionNotFoundError`
        (AC10) -- never revealing which.

        Records an audit event (AUTH-004, AC8): `logout` when the
        revoked session IS the caller's own current session (`session_id
        == current_session_id`, the ordinary "log out of this device"
        action), or `session_revocation` when it's a *different* session
        (the more security-relevant case) -- see `Plan_S02_AUTH-004.md`
        Decision 5.
        """
        session = await self.session_repository.get_active_by_id(session_id)
        ensure_owner_or_not_found(
            session.user_id if session is not None else None,
            user_id,
            not_found_exc=SessionNotFoundError(),
        )

        now = datetime.now(UTC)
        await self.session_repository.revoke(session_id, now)
        await self.refresh_token_repository.revoke_all_for_session(session_id, now)

        if current_session_id is not None and session_id == current_session_id:
            await self.audit_service.record_logout(
                user_id=user_id, session_id=session_id, ip_address=ip_address
            )
        else:
            await self.audit_service.record_session_revocation(
                user_id=user_id, session_id=session_id, ip_address=ip_address
            )

    async def revoke_all_sessions(
        self,
        user_id: uuid.UUID,
        current_session_id: uuid.UUID | None,
        keep_current: bool,
        *,
        ip_address: str | None = None,
    ) -> None:
        """
        "Log out everywhere" (AC9) -- revokes every active session for a
        user, optionally excluding the caller's own current session. A
        distinct, separately named action from `revoke_session`.

        Always records a `session_revocation` audit event (AUTH-004,
        AC8), unconditionally -- this is a bulk action, never a plain
        "logout", even when `keep_current=True`. `entity_id=None` since
        it targets every session, not a single one; `after_state`
        records the scope and whether the current session was kept.
        """
        except_session_id = (
            current_session_id if keep_current and current_session_id else None
        )
        now = datetime.now(UTC)
        await self.session_repository.revoke_all_for_user(
            user_id, now, except_session_id=except_session_id
        )
        await self.refresh_token_repository.revoke_all_for_user(
            user_id, now, except_session_id=except_session_id
        )

        await self.audit_service.record_session_revocation(
            user_id=user_id,
            session_id=None,
            ip_address=ip_address,
            after_state={"scope": "all_sessions", "kept_current": keep_current},
        )
