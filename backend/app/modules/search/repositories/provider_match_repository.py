import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.models import ProviderMatch
from app.repositories.base_repository import BaseRepository


class ProviderMatchRepository(BaseRepository[ProviderMatch]):
    """Repository for the `search.provider_matches` table (AI-002,
    `Plan_S07_AI-002.md`). Written exactly once per `search_requests`
    row, by `SearchRequestService._finalize_matches` (Decision 4)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ProviderMatch, session=session)

    async def bulk_create(
        self,
        search_request_id: uuid.UUID,
        ranked_matches: list[tuple[uuid.UUID, float | None]],
    ) -> list[ProviderMatch]:
        """
        Creates one row per `(provider_id, match_score)` pair, `rank` =
        the 1-based position in `ranked_matches` -- the caller's own
        ordering *is* the rank, never re-derived (Decision 4: merit-
        ranked for the automated path, the admin's own supplied order for
        the manual path).

        `match_score` (MAT-001, Decision 3, `Plan_S08_MAT-001.md`) is the
        tuple's second element, populated as-is: a real `[0, 1]` score
        for the automated path (from `ProviderSearchRepository.
        search_nearby`'s `scores_by_id`), or `None` for every row on the
        manual path -- an admin's own judgment produces that order, so no
        formula-derived score is ever fabricated to fill the column
        (anti-fabrication principle, `00_PROJECT_CONTEXT.md` §3).
        """
        rows = [
            ProviderMatch(
                search_request_id=search_request_id,
                provider_id=provider_id,
                rank=rank,
                match_score=match_score,
            )
            for rank, (provider_id, match_score) in enumerate(ranked_matches, start=1)
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_for_search_request(
        self, search_request_id: uuid.UUID
    ) -> list[ProviderMatch]:
        """All matches for a `search_requests` row, ordered by `rank` --
        backs `GET /search-requests/{id}` (Decision 6)."""
        stmt = (
            select(ProviderMatch)
            .where(ProviderMatch.search_request_id == search_request_id)
            .order_by(ProviderMatch.rank.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
