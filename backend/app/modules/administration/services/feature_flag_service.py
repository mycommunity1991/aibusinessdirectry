"""
`FeatureFlagService` (ADM-002, Decision 1/3/7/8, `Plan_S11_ADM-002.md`)
-- the codebase's first real feature-flag consumer surface (AC4).

Exposes three explicit methods (`is_enabled`, `list_all`, `toggle`),
mirroring `AdminActionLogService`'s "explicit methods, not one generic
CRUD surface" convention. `is_enabled` is the method every runtime
consumer (`search.SearchRequestService`, Decision 7) calls -- it never
raises for an unknown key, returning `False` instead (anti-fabrication
default: "absence means disabled," never assumed enabled).
"""

import uuid

from app.core.exceptions import FeatureFlagNotFoundError
from app.modules.administration.models import FeatureFlag
from app.modules.administration.repositories.feature_flag_repository import (
    FeatureFlagRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)


class FeatureFlagService:
    """Reads and toggles `feature_flags` rows (AC1/AC4)."""

    def __init__(
        self,
        repository: FeatureFlagRepository,
        admin_action_log_service: AdminActionLogService,
    ) -> None:
        self.repository = repository
        self.admin_action_log_service = admin_action_log_service

    async def is_enabled(self, key: str) -> bool:
        """
        Returns whether `key` is currently enabled -- `False` for an
        unknown key (Decision 7/8), never raises. This is the single
        method any runtime consumer (e.g. `search.SearchRequestService.
        handle_session_completed`) calls; a flag that doesn't exist is
        honestly reported as "disabled," not assumed "enabled."
        """
        flag = await self.repository.get_by_key(key)
        return flag.is_enabled if flag is not None else False

    async def list_all(self) -> list[FeatureFlag]:
        """Lists every `feature_flags` row, ordered by `key` (AC1) --
        `05_API_GUIDELINES.md`'s pagination is applied at the API layer,
        given the genuinely small, code-bounded row count (Decision 3)."""
        return await self.repository.list_all()

    async def toggle(
        self, key: str, *, is_enabled: bool, admin_user_id: uuid.UUID
    ) -> FeatureFlag:
        """
        Flips `is_enabled` for an existing flag (AC4) via a plain
        `update` -- not the `try_*` atomic-conditional pattern (Decision
        8: this is an idempotent configuration write, not a workflow-
        state transition, so "last write wins" is the correct, expected
        outcome under concurrent admin writes). Raises
        `FeatureFlagNotFoundError` (404) for an unknown key (Decision 3
        -- no "create a new key" API exists). Records the toggle to
        `admin_action_log` (AC3, Decision 6) after the write succeeds.
        """
        flag = await self.repository.get_by_key(key)
        if flag is None:
            raise FeatureFlagNotFoundError()

        updated = await self.repository.update(flag, {"is_enabled": is_enabled})
        await self.admin_action_log_service.record_feature_flag_toggle(
            admin_user_id=admin_user_id,
            flag_id=updated.id,
            key=updated.key,
            is_enabled=updated.is_enabled,
        )
        return updated
