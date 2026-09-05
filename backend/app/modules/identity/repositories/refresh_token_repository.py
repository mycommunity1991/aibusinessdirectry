import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import RefreshToken
from app.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for the `identity.refresh_tokens` table (AUTH-003)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=RefreshToken, session=session)

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        Persists a new refresh token's hash (never the raw value). Named
        `create_refresh_token` (not `create`) so this doesn't shadow
        `BaseRepository.create`'s generic `(obj_in: dict | Model)`
        signature.
        """
        refresh_token = RefreshToken(
            user_id=user_id,
            session_id=session_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Looks up a `RefreshToken` by its hash. Returns the row regardless
        of its revoked/expired/replaced state -- `SessionService.refresh`
        needs to distinguish "not found at all" from "found but already
        rotated away" (the reuse-detection signal) from "found, valid".
        """
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token_id: uuid.UUID, revoked_at: datetime) -> None:
        """Marks a single refresh token as revoked."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == refresh_token_id)
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(stmt)

    async def revoke_all_for_session(
        self, session_id: uuid.UUID, revoked_at: datetime
    ) -> None:
        """Revokes every non-revoked refresh token in a session's chain --
        used both by explicit session revocation (AC8/AC9) and by the
        reuse-detection cascade (Decision 7, `Plan_S02_AUTH-003.md`)."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(stmt)

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        revoked_at: datetime,
        except_session_id: uuid.UUID | None = None,
    ) -> None:
        """Revokes every non-revoked refresh token belonging to a user
        (AC9's "log out everywhere"), optionally excluding tokens whose
        session is `except_session_id` (the caller's own current
        session, when `keep_current=True`)."""
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
        if except_session_id is not None:
            stmt = stmt.where(RefreshToken.session_id != except_session_id)
        stmt = stmt.values(revoked_at=revoked_at)
        await self.session.execute(stmt)

    async def mark_replaced(
        self, old_id: uuid.UUID, new_id: uuid.UUID, revoked_at: datetime
    ) -> None:
        """Marks `old_id` as rotated away, pointing to its replacement --
        the rotation-chain link the reuse-detection cascade relies on."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == old_id)
            .values(revoked_at=revoked_at, replaced_by_token_id=new_id)
        )
        await self.session.execute(stmt)
