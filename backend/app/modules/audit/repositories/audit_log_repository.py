import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditLogRepository:
    """
    Repository for the `audit.audit_logs` table.

    Deliberately does NOT extend `BaseRepository`/`IBaseRepository` and
    exposes only `create(...)` -- no `update`/`delete` method is ever
    defined, so immutability (AC8) is enforced by this class's shape,
    not merely by convention or a docstring.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Inserts a new, immutable audit log row."""
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
        )
        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)
        return audit_log
