"""
`SystemSettingService` (ADM-002, Decision 1/3/8, `Plan_S11_ADM-002.md`)
-- mirrors `FeatureFlagService`'s identical shape for the
`system_settings` aggregate (AC1).
"""

import uuid
from typing import Any

from app.core.exceptions import SystemSettingNotFoundError
from app.modules.administration.models import SystemSetting
from app.modules.administration.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)


class SystemSettingService:
    """Reads and updates `system_settings` rows (AC1)."""

    def __init__(
        self,
        repository: SystemSettingRepository,
        admin_action_log_service: AdminActionLogService,
    ) -> None:
        self.repository = repository
        self.admin_action_log_service = admin_action_log_service

    async def list_all(self) -> list[SystemSetting]:
        """Lists every `system_settings` row, ordered by `key` (AC1)."""
        return await self.repository.list_all()

    async def update_value(
        self, key: str, *, value: Any, admin_user_id: uuid.UUID
    ) -> SystemSetting:
        """
        Overwrites an existing setting's `value` (AC1) via a plain
        `update` -- not the `try_*` atomic-conditional pattern (Decision
        8: an idempotent configuration write, "last write wins" under
        concurrent admin writes). Raises `SystemSettingNotFoundError`
        (404) for an unknown key (Decision 3). Records the update to
        `admin_action_log` (AC3, Decision 6) after the write succeeds.
        """
        setting = await self.repository.get_by_key(key)
        if setting is None:
            raise SystemSettingNotFoundError()

        updated = await self.repository.update(setting, {"value": value})
        await self.admin_action_log_service.record_system_setting_update(
            admin_user_id=admin_user_id,
            setting_id=updated.id,
            key=updated.key,
            value=updated.value,
        )
        return updated
