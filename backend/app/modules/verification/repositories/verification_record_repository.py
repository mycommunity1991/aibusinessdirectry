import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import VerificationStatus
from app.modules.verification.models import VerificationRecord
from app.repositories.base_repository import BaseRepository

_REVIEWABLE_STATUSES = (VerificationStatus.PENDING, VerificationStatus.UNDER_REVIEW)


class VerificationRecordRepository(BaseRepository[VerificationRecord]):
    """Repository for the `verification.verification_records` table (VER-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=VerificationRecord, session=session)

    async def get_latest_for_provider(
        self, provider_id: uuid.UUID
    ) -> VerificationRecord | None:
        """
        Returns a provider's single latest verification cycle, ordered by
        `submitted_at` descending -- used by both `GET
        /providers/me/verification` (AC6, reads this directly, never
        `providers.verification_status`, Decision 2) and
        `VerificationService.submit`'s resubmission-eligibility check
        (Decision 4/AC7).
        """
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.provider_id == provider_id)
            .order_by(VerificationRecord.submitted_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_review(
        self, *, offset: int, limit: int
    ) -> tuple[list[VerificationRecord], int]:
        """
        Lists `pending`/`under_review` records for the admin review
        queue (VER-002, AC1), oldest `submitted_at` first -- a review
        queue shouldn't let an old submission be perpetually skipped by
        newer ones jumping the line -- plus a total count for
        `PaginationMeta`.
        """
        filtered = select(VerificationRecord).where(
            VerificationRecord.status.in_(_REVIEWABLE_STATUSES)
        )

        count_result = await self.session.execute(
            select(func.count()).select_from(filtered.subquery())
        )
        total = count_result.scalar_one()

        stmt = (
            filtered.order_by(VerificationRecord.submitted_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def try_claim_for_review(
        self,
        record_id: uuid.UUID,
        *,
        new_status: VerificationStatus,
        reviewed_by: uuid.UUID,
        reviewed_at: datetime,
        rejection_reason: str | None = None,
    ) -> bool:
        """
        Atomically transitions a record out of `pending`/`under_review`
        into `new_status`, but only if it is *still* in one of those
        states at the moment this statement executes (VER-002, AC6/AC8
        concurrency fix).

        A plain read-then-write (fetch the record, check its status in
        Python, then `UPDATE` it) leaves a window where two concurrent
        `approve`/`reject` calls on the *same* record can both pass the
        Python-level check before either commits, each going on to write
        its own `admin_action_log`/`notification` row for what should be
        one logical action. A single conditional `UPDATE ... WHERE status
        IN (...)` closes that window: Postgres takes a row lock on the
        first matching writer, and a concurrent second `UPDATE` targeting
        the same row blocks until the first commits, then re-evaluates
        this statement's own `WHERE` clause against the now-current
        (already-transitioned) row -- so at most one caller's `UPDATE`
        can ever match, even under true concurrency. This relies on
        Postgres's READ COMMITTED default (this codebase's engine sets
        no other isolation level, `app/database/database.py`); under
        SERIALIZABLE/REPEATABLE READ the losing transaction would instead
        raise a serialization failure rather than affect zero rows --
        either outcome still prevents the duplicate write this fix
        targets.

        Returns `True` if this call won the race and applied the
        transition, `False` if the record was no longer actionable
        (already claimed by a concurrent call, or already reviewed) --
        the caller is expected to raise `VerificationRecordNotActionableError`
        in that case.
        """
        stmt = (
            sql_update(VerificationRecord)
            .where(
                VerificationRecord.id == record_id,
                VerificationRecord.status.in_(_REVIEWABLE_STATUSES),
            )
            .values(
                status=new_status,
                reviewed_by=reviewed_by,
                reviewed_at=reviewed_at,
                rejection_reason=rejection_reason,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        # `Result`'s type stubs don't expose `rowcount` (it's a
        # `CursorResult`-only attribute, always present at runtime for a
        # Core `UPDATE`/`DELETE` statement executed this way).
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount == 1
