import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import UnmatchedQueryReport
from app.repositories.base_repository import BaseRepository


class UnmatchedQueryReportRepository(BaseRepository[UnmatchedQueryReport]):
    """
    Repository for the `administration.unmatched_query_reports` table
    (ADM-001, Decision 2/7/8, `Plan_S11_ADM-001.md`) -- mirrors
    `ManualMatchAssignmentRepository`'s minimal-surface convention.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=UnmatchedQueryReport, session=session)

    async def list_filtered(
        self,
        *,
        status: str | None,
        sort_desc: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[UnmatchedQueryReport], int]:
        """
        AC5's filter/sort scope (Decision 7): filters by the report's own
        `status` only when `status is not None` (`status="all"` at the
        service layer maps to `None` here), sorts by the report's own
        `created_at` -- both plain columns on this table itself,
        filterable/sortable directly in SQL with correct pagination.
        """
        filtered = select(UnmatchedQueryReport)
        if status is not None:
            filtered = filtered.where(UnmatchedQueryReport.status == status)

        count_result = await self.session.execute(
            select(func.count()).select_from(filtered.subquery())
        )
        total = count_result.scalar_one()

        order_column = (
            UnmatchedQueryReport.created_at.desc()
            if sort_desc
            else UnmatchedQueryReport.created_at.asc()
        )
        stmt = filtered.order_by(order_column).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def try_transition_status(
        self,
        report_id: uuid.UUID,
        *,
        from_statuses: tuple[str, ...],
        to_status: str,
        admin_user_id: uuid.UUID,
        reviewed_at: datetime,
        category_gap_notes: str | None,
    ) -> bool:
        """
        Atomically transitions a report's `status`, but only if it is
        still one of `from_statuses` at the moment this statement
        executes (Decision 8) -- a single conditional `UPDATE ... WHERE
        id = :id AND status IN :from_statuses`, mirroring
        `ManualMatchAssignmentRepository.try_resolve`'s identical
        "never a read-then-write check" shape: a plain read-then-write
        (fetch the report, check `status` in Python, then `UPDATE` it)
        leaves a race window where two concurrent admin calls on the
        *same* report could both pass the Python-level check before
        either commits. Postgres takes a row lock on the first matching
        writer at this codebase's READ COMMITTED default
        (`app/database/database.py`), so a concurrent second `UPDATE`
        targeting the same row blocks until the first commits, then
        re-evaluates this statement's own `WHERE` clause against the
        now-current row -- at most one caller's `UPDATE` can ever match.

        Returns `True` if this call won the transition, `False`
        otherwise -- the caller is expected to raise
        `UnmatchedQueryReportInvalidTransitionError` in that case.

        `category_gap_notes` is only overwritten when the caller
        supplies a non-`None` value -- a later transition call (e.g.
        `reviewed` -> `actioned`) made without new notes never silently
        wipes out notes an earlier call already recorded.
        """
        values: dict[str, object] = {
            "status": to_status,
            "reviewed_by": admin_user_id,
            "reviewed_at": reviewed_at,
        }
        if category_gap_notes is not None:
            values["category_gap_notes"] = category_gap_notes

        stmt = (
            sql_update(UnmatchedQueryReport)
            .where(
                UnmatchedQueryReport.id == report_id,
                UnmatchedQueryReport.status.in_(from_statuses),
            )
            .values(**values)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        # `Result`'s type stubs don't expose `rowcount` (it's a
        # `CursorResult`-only attribute, always present at runtime for a
        # Core `UPDATE`/`DELETE` statement executed this way) -- mirrors
        # `ManualMatchAssignmentRepository.try_resolve`'s identical
        # pattern.
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount == 1
