import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversation.models import ConfidenceScore
from app.repositories.base_repository import BaseRepository


class ConfidenceScoreRepository(BaseRepository[ConfidenceScore]):
    """
    Repository for the append-only `conversation.confidence_scores` log
    (AI-001, Decision 1's own evidence: "never compute a score without
    persisting it," `ai-conversation-engineering` skill).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ConfidenceScore, session=session)

    async def get_latest_for_session(
        self, conversation_session_id: uuid.UUID
    ) -> ConfidenceScore | None:
        """The most recently computed score for a session, by
        `computed_at` -- a session may be re-scored as more turns
        arrive; this is the value `04_DATABASE.md` describes
        `conversation_sessions.final_confidence_score` as caching."""
        stmt = (
            select(ConfidenceScore)
            .where(ConfidenceScore.conversation_session_id == conversation_session_id)
            .order_by(ConfidenceScore.computed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
