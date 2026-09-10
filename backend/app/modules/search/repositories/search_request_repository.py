import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.models import SearchRequest, SearchRequestStatus
from app.repositories.base_repository import BaseRepository


class SearchRequestRepository(BaseRepository[SearchRequest]):
    """Repository for the `search.search_requests` table (AI-002,
    `Plan_S07_AI-002.md`)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=SearchRequest, session=session)

    async def update_status(
        self, search_request: SearchRequest, status: SearchRequestStatus
    ) -> SearchRequest:
        """
        Transitions a `search_requests` row to its final `status` --
        called only from `SearchRequestService._finalize_matches`
        (Decision 4), the single place this ever happens.
        """
        return await self.update(search_request, {"status": status})

    async def get_latest_by_conversation_session_id(
        self, conversation_session_id: uuid.UUID
    ) -> SearchRequest | None:
        """
        The most recently created `search_requests` row for a given
        conversation session, if any (Decision 6) -- backs
        `ConversationSessionResponse.search_request_id`. Ordered by
        `created_at DESC` rather than assuming a strict 1:1 relationship:
        `AI-001`'s existing revise-a-previous-answer flow can, in a rare
        edge case, revert a `completed`/`routed_to_admin` session back to
        `active` and later re-complete it, which would create a second
        `search_requests` row for the same session -- the most recent one
        is always the one that reflects the session's current state.
        """
        stmt = (
            select(SearchRequest)
            .where(SearchRequest.conversation_session_id == conversation_session_id)
            .order_by(SearchRequest.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
