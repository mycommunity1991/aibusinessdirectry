import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contact.models import ContactView
from app.repositories.base_repository import BaseRepository


class ContactViewRepository(BaseRepository[ContactView]):
    """
    Repository for the `contact.contact_views` table (CON-001).
    `ContactService` exposes the one explicit write path this module
    needs today (`create`, inherited from `BaseRepository`); no
    dedup/uniqueness lookup is ever performed (Decision 5,
    `Plan_S08_CON-001.md` -- every Contact tap creates a new row).

    `list_for_provider`/`count_for_provider` (LEAD-001, Backend Proposed
    Changes item 2, `Plan_S10_LEAD-001.md`) are this module's first
    custom read methods -- the paginated, provider-scoped source of a
    provider's own Leads list (AC2/AC4).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ContactView, session=session)

    async def list_for_provider(
        self, provider_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[ContactView]:
        """
        One page of a provider's own Contact Views, most-recent-first
        (AC2) -- `id ASC` is the deterministic tie-break for two rows
        with an identical `viewed_at`, mirroring
        `ProviderSearchRepository`'s own `p.id ASC` tie-break precedent.
        """
        stmt = (
            select(ContactView)
            .where(ContactView.provider_id == provider_id)
            .order_by(ContactView.viewed_at.desc(), ContactView.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_provider(self, provider_id: uuid.UUID) -> int:
        """
        The matching, unpaginated count of a provider's own Contact
        Views, for `PaginationMeta.total_items` -- mirrors
        `ProviderSearchRepository`'s own paired count-query pattern.
        """
        stmt = select(func.count()).select_from(ContactView).where(
            ContactView.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
