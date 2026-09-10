import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import ManualMatchAssignment
from app.repositories.base_repository import BaseRepository

_STATUS_PENDING = "pending"
_STATUS_COMPLETED = "completed"


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

    async def try_resolve(
        self,
        assignment_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
        completed_at: datetime,
    ) -> bool:
        """
        Atomically transitions an assignment to `status=completed`, but
        only if it is *still* `status=pending` at the moment this
        statement executes (AI-002, the genuine race-condition defense
        for two admins concurrently resolving the *same* queue item).

        A plain read-then-write (fetch the assignment, check `status` in
        Python, then `UPDATE` it) leaves a window where two concurrent
        `POST .../resolve` calls on the *same* assignment can both pass
        the Python-level check before either commits -- both would then
        proceed into `SearchRequestService._finalize_matches`, writing a
        second, duplicate `provider_matches` batch and a second
        `search_event_log` row for one `search_requests` row. A single
        conditional `UPDATE ... WHERE status = 'pending'` closes that
        window exactly the way `ProviderRepository.try_claim_for_account`
        (CLM-001) and `VerificationRecordRepository.try_claim_for_review`
        (VER-002) already established for the analogous "exactly one
        caller wins" problem: Postgres takes a row lock on the first
        matching writer, and a concurrent second `UPDATE` targeting the
        same row blocks until the first commits, then re-evaluates this
        statement's own `WHERE` clause against the now-current
        (already-completed) row -- so at most one caller's `UPDATE` can
        ever match, even under true concurrency (this codebase's engine
        runs at Postgres's READ COMMITTED default,
        `app/database/database.py`).

        Returns `True` if this call won the race and applied the
        transition, `False` if the row was no longer resolvable (already
        resolved by a concurrent call, or by the time this executes) --
        the caller is expected to raise
        `ManualMatchAssignmentAlreadyResolvedError` in that case.
        """
        stmt = (
            sql_update(ManualMatchAssignment)
            .where(
                ManualMatchAssignment.id == assignment_id,
                ManualMatchAssignment.status == _STATUS_PENDING,
            )
            .values(
                status=_STATUS_COMPLETED,
                assigned_admin_id=admin_user_id,
                completed_at=completed_at,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        # `Result`'s type stubs don't expose `rowcount` (it's a
        # `CursorResult`-only attribute, always present at runtime for a
        # Core `UPDATE`/`DELETE` statement executed this way) -- mirrors
        # `ProviderRepository.try_claim_for_account`'s/
        # `VerificationRecordRepository.try_claim_for_review`'s identical
        # pattern.
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount == 1
