import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contact.models import OutcomeTag
from app.repositories.base_repository import BaseRepository


class OutcomeTagRepository(BaseRepository[OutcomeTag]):
    """
    Repository for the `contact.outcome_tags` table (REV-001). Adds one
    custom method, `try_create`, the story's genuine INSERT-shaped
    uniqueness race defense (Decision 3, `Plan_S09_REV-001.md`) --
    `get_by_id` is already available for free (inherited from
    `BaseRepository`).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=OutcomeTag, session=session)

    async def try_create(self, values: dict[str, Any]) -> OutcomeTag | None:
        """
        Atomically inserts a new `outcome_tags` row, but only if no row
        already exists for `values["contact_view_id"]` (AC1/AC6) --
        a single `INSERT ... ON CONFLICT (contact_view_id) DO NOTHING
        ... RETURNING id` statement, never a read-then-write check
        (Decision 3). This is the fourth application of this codebase's
        "atomic conditional write" family
        (`try_claim_for_account`/`try_claim_for_review`/`try_resolve`),
        and the first INSERT-shaped member -- it reuses the exact
        `on_conflict_do_nothing` mechanism `seed_roles` already proven
        for idempotent seeding, applied here to reject a genuine
        conflict instead of silently no-opping a duplicate.

        Returns the new `OutcomeTag` if this call won the race (a row
        was inserted), or `None` if a row for this `contact_view_id`
        already existed -- the caller is expected to raise
        `OutcomeTagAlreadyExistsError` in that case.
        """
        stmt = (
            postgresql.insert(OutcomeTag)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["contact_view_id"])
            .returning(OutcomeTag.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        new_id = result.scalar_one_or_none()
        if new_id is None:
            return None
        return await self.get_by_id(new_id)

    async def get_by_contact_view_id(
        self, contact_view_id: uuid.UUID
    ) -> OutcomeTag | None:
        """
        The read-only counterpart to `try_create` (REV-002, Backend
        Proposed Changes item 7, `Plan_S09_REV-002.md`) -- a plain
        `SELECT ... WHERE contact_view_id = :id`, needed by
        `ReviewService.submit_review` to resolve AC2's anchor-
        verification precondition (does the anchoring Contact View carry
        a `hired=True` Outcome Tag?). REV-001 never needed this lookup
        (it only ever creates, never reads back); this is its first
        consumer.
        """
        stmt = select(OutcomeTag).where(OutcomeTag.contact_view_id == contact_view_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_contact_view_ids(
        self, contact_view_ids: list[uuid.UUID]
    ) -> list[OutcomeTag]:
        """
        Batch counterpart to `get_by_contact_view_id` (LEAD-001, Backend
        Proposed Changes item 4, `Plan_S10_LEAD-001.md`, Decision 5) --
        a plain `WHERE contact_view_id IN (...)` batch fetch, needed by
        `LeadService` to resolve a page of leads' outcome statuses
        without an N+1 query. Any `contact_view_id` with no row here has
        no `OutcomeTag` yet -- the "not yet reported" state (the 1:1
        unique constraint on `contact_view_id` guarantees at most one
        row per id, so callers never need to dedupe the result).
        """
        if not contact_view_ids:
            return []
        stmt = select(OutcomeTag).where(
            OutcomeTag.contact_view_id.in_(contact_view_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
