from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import ManualMatchAssignment
from app.repositories.base_repository import BaseRepository

_STATUS_PENDING = "pending"


class ManualMatchAssignmentRepository(BaseRepository[ManualMatchAssignment]):
    """
    Repository for the `administration.manual_match_assignments` table
    (AI-002, Decision 3, `Plan_S07_AI-002.md`) -- mirrors
    `ClaimReviewRequestRepository`'s minimal-surface convention, adding
    only the one custom read `ManualMatchAssignmentService` needs beyond
    the inherited `create`/`get_by_id`/`update`.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ManualMatchAssignment, session=session)

    async def list_pending(
        self, *, offset: int, limit: int
    ) -> tuple[list[ManualMatchAssignment], int]:
        """
        Lists `status=pending` assignments, oldest `created_at` first
        (mirrors `ClaimReviewRequestRepository.list_open`'s identical
        oldest-first queue ordering), plus a total count for
        `PaginationMeta`.
        """
        filtered = select(ManualMatchAssignment).where(
            ManualMatchAssignment.status == _STATUS_PENDING
        )

        count_result = await self.session.execute(
            select(func.count()).select_from(filtered.subquery())
        )
        total = count_result.scalar_one()

        stmt = (
            filtered.order_by(ManualMatchAssignment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
