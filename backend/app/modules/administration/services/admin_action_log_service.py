"""
Admin-action recording (VER-002, AC6).

Exposes one explicit method, `record_verification_review`, mirroring
`AuditService`'s "explicit methods, not one generic `record()`"
convention -- `verification`'s new `AdminVerificationService` depends on
this service class, never on `AdminActionLogRepository` directly, per
`02_ARCHITECTURE.md`'s "modules communicate through services only" rule.
"""

import uuid
from typing import Literal

from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)

_ACTION_TYPE_APPROVED = "verification_approved"
_ACTION_TYPE_REJECTED = "verification_rejected"
_TARGET_ENTITY_TYPE_VERIFICATION_RECORD = "verification_record"


class AdminActionLogService:
    """Records admin review actions (AC6) via `AdminActionLogRepository`."""

    def __init__(self, repository: AdminActionLogRepository) -> None:
        self.repository = repository

    async def record_verification_review(
        self,
        *,
        admin_user_id: uuid.UUID,
        verification_record_id: uuid.UUID,
        provider_id: uuid.UUID,
        decision: Literal["approved", "rejected"],
        rejection_reason: str | None,
    ) -> AdminActionLog:
        """
        Records one approve/reject action against a verification record
        (VER-002, AC6). `target_entity_type`/`target_entity_id` point at
        the `verification_records` row itself; `provider_id` (and, for a
        rejection, `rejection_reason`) are carried in `metadata` since
        `target_entity_id` is a single, polymorphic reference
        (`04_DATABASE.md`) and cannot itself hold a second id.
        """
        action_type = (
            _ACTION_TYPE_APPROVED if decision == "approved" else _ACTION_TYPE_REJECTED
        )
        metadata: dict[str, str | None] = {"provider_id": str(provider_id)}
        if decision == "rejected":
            metadata["rejection_reason"] = rejection_reason

        return await self.repository.create(
            {
                "admin_user_id": admin_user_id,
                "action_type": action_type,
                "target_entity_type": _TARGET_ENTITY_TYPE_VERIFICATION_RECORD,
                "target_entity_id": verification_record_id,
                "metadata_": metadata,
            }
        )
