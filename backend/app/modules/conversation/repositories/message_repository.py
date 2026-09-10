import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.models import Message
from app.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for the `conversation.messages` table (AI-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Message, session=session)

    async def list_for_session(
        self, conversation_session_id: uuid.UUID
    ) -> Sequence[Message]:
        """A session's full transcript, ordered by `sequence_number`
        (AC1) -- the ordering the mobile chat screen and
        `ConversationAiClient` both rely on."""
        stmt = (
            select(Message)
            .where(Message.conversation_session_id == conversation_session_id)
            .order_by(Message.sequence_number.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_next_sequence_number(self, conversation_session_id: uuid.UUID) -> int:
        """The next available `sequence_number` for a session -- `1` for
        a brand-new session's first message, otherwise one past the
        current highest (never reused, even after a revise's
        `delete_after_sequence`, since sequence numbers are only ever
        assigned going forward from the current max)."""
        stmt = select(func.max(Message.sequence_number)).where(
            Message.conversation_session_id == conversation_session_id
        )
        result = await self.session.execute(stmt)
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    async def delete_after_sequence(
        self, conversation_session_id: uuid.UUID, sequence_number: int
    ) -> None:
        """
        Hard-deletes every message (customer and AI alike) with a
        strictly greater `sequence_number` in the same session (Decision
        5, AC8's truncate-and-regenerate revise mechanism). A genuine
        hard delete, not soft-delete -- `messages` has no `deleted_at`
        column (`04_DATABASE.md`'s spec), and a truncated, superseded AI
        question has no audit value worth preserving. Flush only, never
        commits -- the caller (`ConversationService.revise_answer`) rides
        the endpoint's single transaction alongside the update and the
        freshly regenerated turn.
        """
        stmt = delete(Message).where(
            Message.conversation_session_id == conversation_session_id,
            Message.sequence_number > sequence_number,
        )
        await self.session.execute(stmt)
        await self.session.flush()
