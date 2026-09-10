import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.models import Message
from app.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for the `conversation.messages` table (AI-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Message, session=session)

    async def get_active_by_id(self, message_id: uuid.UUID) -> Message | None:
        """
        Retrieves a message by id only if it has not been soft-deleted.
        `ConversationService.revise_answer` uses this (never the generic
        `get_by_id`) so that a `message_id` truncated by an earlier
        revise (`delete_after_sequence`) is treated identically to a
        never-existing one -- exactly the customer-visible behavior a
        hard delete used to produce for free, now preserved explicitly.
        Mirrors `SavedAddressRepository.get_active_by_id`'s pattern.
        """
        stmt = select(Message).where(
            Message.id == message_id, Message.is_active.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_session(
        self, conversation_session_id: uuid.UUID
    ) -> Sequence[Message]:
        """A session's full transcript, ordered by `sequence_number`
        (AC1) -- the ordering the mobile chat screen and
        `ConversationAiClient` both rely on. Excludes soft-deleted rows
        (`is_active.is_(True)`) -- a message truncated by a revise
        (`delete_after_sequence`, Decision 5) must never reappear in the
        transcript, mirroring `SavedAddressRepository.list_for_customer`'s
        soft-delete filtering convention."""
        stmt = (
            select(Message)
            .where(
                Message.conversation_session_id == conversation_session_id,
                Message.is_active.is_(True),
            )
            .order_by(Message.sequence_number.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_next_sequence_number(self, conversation_session_id: uuid.UUID) -> int:
        """The next available `sequence_number` for a session -- `1` for
        a brand-new session's first message, otherwise one past the
        current highest *active* `sequence_number`. Only active rows are
        counted so that, after a revise's `delete_after_sequence`
        soft-deletes every later message, the regenerated turn resumes
        immediately after the last surviving answer -- reusing a
        soft-deleted row's old `sequence_number` where needed, which
        `uq_messages_session_sequence`'s partial-unique-index scoping
        (`WHERE is_active = true`, see `Message`'s docstring) allows
        without a conflict."""
        stmt = select(func.max(Message.sequence_number)).where(
            Message.conversation_session_id == conversation_session_id,
            Message.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    async def delete_after_sequence(
        self, conversation_session_id: uuid.UUID, sequence_number: int
    ) -> None:
        """
        Soft-deletes every message (customer and AI alike) with a
        strictly greater `sequence_number` in the same session (Decision
        5, AC8's truncate-and-regenerate revise mechanism): sets
        `deleted_at`/`is_active`, never a hard `DELETE` -- per
        `04_DATABASE.md`'s "Common Columns" soft-delete rule, permanent
        deletion is an administrative operation, not something a
        customer-initiated revise performs, and `messages` (like every
        `CommonColumnsMixin`-based table) already carries `deleted_at`/
        `is_active` for exactly this purpose. Mirrors
        `SavedAddressRepository.soft_delete`'s exact convention. Flush
        only, never commits -- the caller (`ConversationService
        .revise_answer`) rides the endpoint's single transaction
        alongside the update and the freshly regenerated turn.
        """
        stmt = (
            update(Message)
            .where(
                Message.conversation_session_id == conversation_session_id,
                Message.sequence_number > sequence_number,
            )
            .values(deleted_at=datetime.now(UTC), is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()
