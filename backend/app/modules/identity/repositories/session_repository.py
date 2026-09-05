import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Device, Session
from app.repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for the `identity.sessions` table (AUTH-003)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Session, session=session)

    async def create_session(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID | None,
        ip_address: str | None,
        user_agent: str | None,
        expires_at: datetime,
    ) -> Session:
        """
        Creates a new active `Session` row. Named `create_session` (not
        `create`) so this doesn't shadow `BaseRepository.create`'s
        generic `(obj_in: dict | Model)` signature.
        """
        db_session = Session(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        self.session.add(db_session)
        await self.session.flush()
        await self.session.refresh(db_session)
        return db_session

    async def get_active_by_id(self, session_id: uuid.UUID) -> Session | None:
        """
        Retrieves a `Session` by id only if it has not been revoked.
        Deliberately does not filter on `expires_at` here -- token-level
        expiry is enforced by `RefreshTokenRepository`/`SessionService`;
        an expired-but-not-yet-revoked session is still a real row for
        listing/ownership purposes.
        """
        stmt = select(Session).where(
            Session.id == session_id, Session.revoked_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        """Lists every non-revoked `Session` row for a user (AC7)."""
        stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_for_user_with_device(
        self, user_id: uuid.UUID
    ) -> list[tuple[Session, Device | None]]:
        """
        Same as `list_active_for_user`, left-joined with each session's
        `Device` row so `GET /sessions` (AC7) can report device name and
        platform without an N+1 lookup per session.
        """
        stmt = (
            select(Session, Device)
            .outerjoin(Device, Device.id == Session.device_id)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [(row.Session, row.Device) for row in result.all()]

    async def revoke(self, session_id: uuid.UUID, revoked_at: datetime) -> None:
        """Marks a single session as revoked (AC8)."""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(stmt)

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        revoked_at: datetime,
        except_session_id: uuid.UUID | None = None,
    ) -> None:
        """
        Revokes every active session for a user (AC9's "log out
        everywhere"), optionally excluding one (the caller's own current
        session, when `keep_current=True`).
        """
        stmt = update(Session).where(
            Session.user_id == user_id, Session.revoked_at.is_(None)
        )
        if except_session_id is not None:
            stmt = stmt.where(Session.id != except_session_id)
        stmt = stmt.values(revoked_at=revoked_at)
        await self.session.execute(stmt)
