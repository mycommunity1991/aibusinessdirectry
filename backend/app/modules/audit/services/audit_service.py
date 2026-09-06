"""
Audit-event recording (AUTH-004, AC8).

Exposes four explicit, self-documenting methods rather than one generic
`record(action: str, ...)` -- explicit methods make each call site's
intent unambiguous and remove any risk of a typo'd `action` string.
`identity`'s services depend on this service class, never on
`AuditLogRepository` directly, per `02_ARCHITECTURE.md`'s "modules
communicate through services only" rule.
"""

import uuid

from app.modules.audit.models import AuditLog
from app.modules.audit.repositories.audit_log_repository import AuditLogRepository

_ACTION_REGISTRATION = "registration"
_ACTION_LOGIN = "login"
_ACTION_LOGOUT = "logout"
_ACTION_SESSION_REVOCATION = "session_revocation"

_ENTITY_TYPE_USER = "user"
_ENTITY_TYPE_SESSION = "session"


class AuditService:
    """Records the four tracked event types (AC8/AC9) via `AuditLogRepository`."""

    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    async def record_registration(
        self,
        *,
        user_id: uuid.UUID,
        auth_provider: str,
        ip_address: str | None,
    ) -> AuditLog:
        """
        Records a new-account creation. `actor_user_id` is the newly
        created user's own id -- there is no separate "actor" for a
        self-service registration. Never carries a phone number, email,
        or token -- only the non-PII `auth_provider` value.
        """
        return await self.repository.create(
            actor_user_id=user_id,
            action=_ACTION_REGISTRATION,
            entity_type=_ENTITY_TYPE_USER,
            entity_id=user_id,
            after_state={"auth_provider": str(auth_provider)},
            ip_address=ip_address,
        )

    async def record_login(
        self,
        *,
        user_id: uuid.UUID,
        auth_provider: str,
        ip_address: str | None,
    ) -> AuditLog:
        """Records a successful sign-in, whether the account is new or returning."""
        return await self.repository.create(
            actor_user_id=user_id,
            action=_ACTION_LOGIN,
            entity_type=_ENTITY_TYPE_USER,
            entity_id=user_id,
            after_state={"auth_provider": str(auth_provider)},
            ip_address=ip_address,
        )

    async def record_logout(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        ip_address: str | None,
    ) -> AuditLog:
        """
        Records the caller ending their own current session -- the
        ordinary "log out of this device" action.
        """
        return await self.repository.create(
            actor_user_id=user_id,
            action=_ACTION_LOGOUT,
            entity_type=_ENTITY_TYPE_SESSION,
            entity_id=session_id,
            ip_address=ip_address,
        )

    async def record_session_revocation(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None,
        ip_address: str | None,
        after_state: dict | None = None,
    ) -> AuditLog:
        """
        Records ending a *different* device's session (the more
        security-relevant case than `record_logout`), or a bulk "log out
        everywhere" (`session_id=None`, since it's not a single entity --
        `after_state` then carries `{"scope": "all_sessions",
        "kept_current": <bool>}`).
        """
        return await self.repository.create(
            actor_user_id=user_id,
            action=_ACTION_SESSION_REVOCATION,
            entity_type=_ENTITY_TYPE_SESSION,
            entity_id=session_id,
            after_state=after_state,
            ip_address=ip_address,
        )
