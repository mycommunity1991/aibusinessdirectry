import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.models import Review
from app.repositories.base_repository import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """
    Repository for the `review.reviews` table (REV-002). Adds two custom
    methods, mirroring `Plan_S09_REV-002.md`'s Decision 3:

    - `try_create`: the story's genuine INSERT-shaped uniqueness race
      defense (AC1, Decision 3 step 2), the exact same `ON CONFLICT DO
      NOTHING ... RETURNING` pattern `OutcomeTagRepository.try_create`
      (REV-001, ADR-049) already established.
    - `compute_rating_aggregate`: the full-recompute read (Decision 3
      step 3) `ReviewService.submit_review` runs immediately after a
      successful insert, while still holding `ProviderService.
      lock_for_rating_recalculation`'s row lock -- this is what makes the
      recompute race-safe.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Review, session=session)

    async def try_create(self, values: dict[str, Any]) -> Review | None:
        """
        Atomically inserts a new `reviews` row, but only if no row
        already exists for `values["contact_view_id"]` (AC1) -- a single
        `INSERT ... ON CONFLICT (contact_view_id) DO NOTHING ...
        RETURNING id` statement, never a read-then-write check.

        Returns the new `Review` if this call won the race (a row was
        inserted), or `None` if a row for this `contact_view_id` already
        existed -- the caller is expected to raise
        `ReviewAlreadyExistsError` in that case.
        """
        stmt = (
            postgresql.insert(Review)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["contact_view_id"])
            .returning(Review.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        new_id = result.scalar_one_or_none()
        if new_id is None:
            return None
        return await self.get_by_id(new_id)

    async def compute_rating_aggregate(
        self, provider_id: uuid.UUID
    ) -> tuple[Decimal, int]:
        """
        `SELECT AVG(rating), COUNT(*) FROM review.reviews WHERE
        provider_id = :id` (Decision 3 step 3) -- a full recompute over
        the raw `rating` values, never an incremental running-average
        update, so rounding error never compounds over a provider's
        review history (Decision 3's own rejected-alternative reasoning).

        Returns `(Decimal("0.00"), 0)` if no rows exist yet for this
        provider -- should not occur mid-write, since this always runs
        immediately after this same transaction's own successful
        insert, but handled honestly rather than assuming `AVG()`'s
        `NULL` result away.
        """
        stmt = select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        average_rating, review_count = result.one()
        if average_rating is None:
            return Decimal("0.00"), 0
        return Decimal(average_rating).quantize(Decimal("0.01")), review_count
