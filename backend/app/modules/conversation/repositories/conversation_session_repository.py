import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.models import ConversationSession, ConversationStatus
from app.repositories.base_repository import BaseRepository

_ACTIVE_STATUS = ConversationStatus.ACTIVE


class ConversationSessionRepository(BaseRepository[ConversationSession]):
    """Repository for the `conversation.conversation_sessions` table
    (AI-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ConversationSession, session=session)

    async def get_active_for_customer(
        self, customer_id: uuid.UUID
    ) -> ConversationSession | None:
        """
        A customer's currently-`active` session, if any (Decision 5) --
        used by `start_conversation` to decide whether a prior session
        must be marked `abandoned` before a new one is created. A
        customer can only ever have zero or one `active` session at a
        time by construction (every transition out of `active` is final).
        """
        stmt = select(ConversationSession).where(
            ConversationSession.customer_id == customer_id,
            ConversationSession.status == _ACTIVE_STATUS,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self, session: ConversationSession, status: ConversationStatus
    ) -> ConversationSession:
        """Transitions a session's `status` only -- used for the
        `abandoned` (Decision 5) and `routed_to_admin` (Decision 4,
        turn-cap) transitions, neither of which touches
        `structured_criteria`."""
        return await self.update(session, {"status": status})

    async def set_category(
        self, session: ConversationSession, category_id: uuid.UUID
    ) -> ConversationSession:
        """Records the category `RuleBasedConversationAiClient` resolved
        for this session (Decision 2)."""
        return await self.update(session, {"category_id": category_id})

    async def update_final_confidence(
        self, session: ConversationSession, score: float
    ) -> ConversationSession:
        """Caches the latest computed confidence score on the session
        row itself (`04_DATABASE.md`'s own stated purpose for this
        column: cheap filtering without joining `confidence_scores`)."""
        return await self.update(session, {"final_confidence_score": score})

    async def complete_session(
        self,
        session: ConversationSession,
        *,
        structured_criteria: dict[str, Any],
    ) -> ConversationSession:
        """
        Atomically transitions a session to `completed` (Decision 1b):
        sets `status`, `completed_at`, and the already-Pydantic-validated
        `structured_criteria` payload in a single `UPDATE`, satisfying
        AC9's "produces... a payload... validated... before persistence"
        requirement -- the caller (`ConversationService`) must have
        already called `StructuredCriteria.model_validate(...)` before
        this method is ever invoked.
        """
        return await self.update(
            session,
            {
                "status": ConversationStatus.COMPLETED,
                "completed_at": datetime.now(UTC),
                "structured_criteria": structured_criteria,
            },
        )

    async def clear_structured_criteria(
        self, session: ConversationSession
    ) -> ConversationSession:
        """
        Clears a previously-computed `structured_criteria` payload
        (Decision 5) -- used by `revise_answer` when truncating a
        session that had already completed, so the column is never left
        stale/inconsistent with the actual (now-shorter) answer history.
        Does not itself change `status` -- the caller decides whether the
        session reverts to `active`.
        """
        return await self.update(session, {"structured_criteria": None})
