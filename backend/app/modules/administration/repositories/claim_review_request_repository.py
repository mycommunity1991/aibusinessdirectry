from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import ClaimReviewRequest
from app.repositories.base_repository import BaseRepository

_STATUS_OPEN = "open"


class ClaimReviewRequestRepository(BaseRepository[ClaimReviewRequest]):
    """
    Repository for the `administration.claim_review_requests` table
    (CLM-001, Decision 9, `Plan_S06_CLM-001.md`) -- mirrors
    `AdminActionLogRepository`'s minimal-surface convention, adding only
    the one custom read `ClaimReviewRequestService` needs beyond the
    inherited `create`/`get_by_id`/`update`.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ClaimReviewRequest, session=session)

    async def list_open(
        self, *, offset: int, limit: int
    ) -> tuple[list[ClaimReviewRequest], int]:
        """
        Lists `status=open` review requests, oldest `created_at` first
        (mirrors `VerificationRecordRepository.list_for_review`'s
        identical oldest-first queue ordering), plus a total count for
        `PaginationMeta`.
        """
        filtered = select(ClaimReviewRequest).where(
            ClaimReviewRequest.status == _STATUS_OPEN
        )

        count_result = await self.session.execute(
            select(func.count()).select_from(filtered.subquery())
        )
        total = count_result.scalar_one()

        stmt = (
            filtered.order_by(ClaimReviewRequest.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
