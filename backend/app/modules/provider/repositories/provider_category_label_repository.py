import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import Provider, ProviderCategoryLabel
from app.repositories.base_repository import BaseRepository


class ProviderCategoryLabelRepository(BaseRepository[ProviderCategoryLabel]):
    """Repository for the `provider.provider_category_labels` table (PRO-002,
    Decision 1, `Plan_S04_PRO-002.md`)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ProviderCategoryLabel, session=session)

    async def list_for_provider(
        self, provider_id: uuid.UUID
    ) -> Sequence[ProviderCategoryLabel]:
        stmt = select(ProviderCategoryLabel).where(
            ProviderCategoryLabel.provider_id == provider_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def replace_all(
        self, provider_id: uuid.UUID, labels: list[dict[str, object]]
    ) -> Sequence[ProviderCategoryLabel]:
        """
        Deletes every existing label for the provider and inserts the new
        set, in one flush (Decision 1) -- mirrors
        `SavedAddressRepository.unset_other_defaults`'s single-flush
        pattern. Count/exactly-one-primary validation happens in
        `ProviderService` before this is called.
        """
        await self.session.execute(
            delete(ProviderCategoryLabel).where(
                ProviderCategoryLabel.provider_id == provider_id
            )
        )
        created = [
            ProviderCategoryLabel(provider_id=provider_id, **label) for label in labels
        ]
        self.session.add_all(created)
        await self.session.flush()
        for row in created:
            await self.session.refresh(row)
        return created

    async def list_distinct_labels_for_discoverable_providers(self) -> list[str]:
        """
        Backs `GET /search/categories` (DIR-001, Decision 1,
        `Plan_S06_DIR-001.md`) -- the distinct set of `label` values
        currently in use across active category labels belonging to
        `is_discoverable=true` providers, case-collapsed
        (`DISTINCT ON (lower(label))`) so "Plumbing" and "plumbing"
        return as a single chip, not two. Deliberately unpaginated
        (mirrors ADR-012's exception): bounded by the number of distinct
        labels real providers have actually typed, not by provider
        count.
        """
        stmt = (
            select(ProviderCategoryLabel.label)
            .distinct(func.lower(ProviderCategoryLabel.label))
            .join(Provider, Provider.id == ProviderCategoryLabel.provider_id)
            .where(
                Provider.is_discoverable.is_(True),
                ProviderCategoryLabel.is_active.is_(True),
            )
            .order_by(
                func.lower(ProviderCategoryLabel.label), ProviderCategoryLabel.label
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
