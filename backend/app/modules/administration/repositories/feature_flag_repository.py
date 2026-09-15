from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import FeatureFlag
from app.repositories.base_repository import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    """
    Repository for the `administration.feature_flags` table (ADM-002,
    Decision 1, `Plan_S11_ADM-002.md`) -- mirrors
    `UnmatchedQueryReportRepository`'s minimal-surface convention,
    adding only the two custom reads `FeatureFlagService` needs beyond
    the inherited `create`/`get_by_id`/`update`. Rows are never created
    via this repository's `create` from the API layer (Decision 3) --
    only the migration seed does that.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=FeatureFlag, session=session)

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        """Single-flag lookup by its code-defined `key` (Decision 3) --
        used by both `FeatureFlagService.is_enabled` and `toggle`."""
        stmt = select(FeatureFlag).where(FeatureFlag.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[FeatureFlag]:
        """Lists every `feature_flags` row, ordered by `key` -- this is
        a genuinely small, finite, code-defined set (Decision 3), so no
        filtering is needed beyond `05_API_GUIDELINES.md`'s standard
        pagination."""
        stmt = select(FeatureFlag).order_by(FeatureFlag.key.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
