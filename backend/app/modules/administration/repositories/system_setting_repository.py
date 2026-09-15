from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import SystemSetting
from app.repositories.base_repository import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """
    Repository for the `administration.system_settings` table (ADM-002,
    Decision 1, `Plan_S11_ADM-002.md`) -- mirrors
    `FeatureFlagRepository`'s identical minimal-surface convention. Rows
    are never created via this repository's `create` from the API layer
    (Decision 3) -- only the migration seed does that.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=SystemSetting, session=session)

    async def get_by_key(self, key: str) -> SystemSetting | None:
        """Single-setting lookup by its code-defined `key` (Decision 3)
        -- used by `SystemSettingService.update_value`."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SystemSetting]:
        """Lists every `system_settings` row, ordered by `key` -- a
        genuinely small, finite, code-defined set (Decision 3)."""
        stmt = select(SystemSetting).order_by(SystemSetting.key.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
