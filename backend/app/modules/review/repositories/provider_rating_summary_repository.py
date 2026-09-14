import uuid
from decimal import Decimal

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.models import ProviderRatingSummary
from app.repositories.base_repository import BaseRepository


class ProviderRatingSummaryRepository(BaseRepository[ProviderRatingSummary]):
    """
    Repository for the `review.provider_rating_summaries` table
    (REV-002). Adds one custom method, `upsert` -- Decision 3 step 4's
    `INSERT ... ON CONFLICT (provider_id) DO UPDATE ... RETURNING`, safe
    to call unconditionally (a provider's first review has no existing
    summary row yet; every subsequent review does) because the caller
    always holds `ProviderService.lock_for_rating_recalculation`'s row
    lock on the corresponding `providers` row for the entire duration of
    this call.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ProviderRatingSummary, session=session)

    async def upsert(
        self,
        provider_id: uuid.UUID,
        *,
        average_rating: Decimal,
        review_count: int,
    ) -> ProviderRatingSummary:
        """
        Writes the freshly recomputed aggregate (Decision 3 step 4).
        `recalculated_at` is deliberately not passed in `.values(...)` --
        omitting it lets `recalculated_at`'s own column-level
        `server_default=now()` populate `excluded.recalculated_at` with a
        fresh timestamp on every call (Postgres evaluates column defaults
        for the `excluded` pseudo-row exactly as it would for a genuine
        insert), so both the insert path and the conflict-update path
        always land on "now", never a stale value.
        """
        insert_stmt = postgresql.insert(ProviderRatingSummary).values(
            provider_id=provider_id,
            average_rating=average_rating,
            review_count=review_count,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["provider_id"],
            set_={
                "average_rating": average_rating,
                "review_count": review_count,
                "recalculated_at": insert_stmt.excluded.recalculated_at,
            },
        ).returning(ProviderRatingSummary.id)

        result = await self.session.execute(stmt)
        await self.session.flush()
        summary_id = result.scalar_one()
        return await self.get_by_id(summary_id)
