"""
Admin-action recording (VER-002, AC6; extended ADM-002, Decision 6,
`Plan_S11_ADM-002.md`).

Exposes five explicit methods -- `record_verification_review` (VER-002)
plus four new ones added by ADM-002 (`record_manual_match_resolution`,
`record_unmatched_query_report_transition`, `record_feature_flag_toggle`,
`record_system_setting_update`) -- mirroring `AuditService`'s "explicit
methods, not one generic `record()`" convention. Every module that
performs a loggable admin action depends on this service class, never on
`AdminActionLogRepository` directly, per `02_ARCHITECTURE.md`'s "modules
communicate through services only" rule.
"""

import uuid
from typing import Any, Literal

from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)

_ACTION_TYPE_APPROVED = "verification_approved"
_ACTION_TYPE_REJECTED = "verification_rejected"
_TARGET_ENTITY_TYPE_VERIFICATION_RECORD = "verification_record"

_ACTION_TYPE_MANUAL_MATCH_RESOLVED = "manual_match_resolved"
_TARGET_ENTITY_TYPE_MANUAL_MATCH_ASSIGNMENT = "manual_match_assignment"

_TARGET_ENTITY_TYPE_UNMATCHED_QUERY_REPORT = "unmatched_query_report"

_ACTION_TYPE_FEATURE_FLAG_TOGGLED = "feature_flag_toggled"
_TARGET_ENTITY_TYPE_FEATURE_FLAG = "feature_flag"

_ACTION_TYPE_SYSTEM_SETTING_UPDATED = "system_setting_updated"
_TARGET_ENTITY_TYPE_SYSTEM_SETTING = "system_setting"


class AdminActionLogService:
    """Records admin review/configuration/queue actions (AC3/AC6) via
    `AdminActionLogRepository`."""

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

    async def record_manual_match_resolution(
        self,
        *,
        admin_user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        provider_ids: list[uuid.UUID],
    ) -> AdminActionLog:
        """
        Records an admin resolving a `manual_match_assignments` row
        (ADM-002, Decision 6, AC3) -- closes the real, evidence-based gap
        where `ManualMatchAssignmentService.resolve` previously wrote no
        `admin_action_log` row at all.
        """
        return await self.repository.create(
            {
                "admin_user_id": admin_user_id,
                "action_type": _ACTION_TYPE_MANUAL_MATCH_RESOLVED,
                "target_entity_type": _TARGET_ENTITY_TYPE_MANUAL_MATCH_ASSIGNMENT,
                "target_entity_id": assignment_id,
                "metadata_": {
                    "provider_ids": [str(provider_id) for provider_id in provider_ids]
                },
            }
        )

    async def record_unmatched_query_report_transition(
        self,
        *,
        admin_user_id: uuid.UUID,
        report_id: uuid.UUID,
        to_status: str,
        category_gap_notes: str | None,
    ) -> AdminActionLog:
        """
        Records an admin transitioning an `unmatched_query_reports` row
        (ADM-002, Decision 6, AC3) -- closes the real, evidence-based gap
        where `UnmatchedQueryReportService.mark_reviewed`/`mark_actioned`
        previously wrote no `admin_action_log` row at all.
        `action_type` is `unmatched_query_report_reviewed`/`...actioned`.
        """
        return await self.repository.create(
            {
                "admin_user_id": admin_user_id,
                "action_type": f"unmatched_query_report_{to_status}",
                "target_entity_type": _TARGET_ENTITY_TYPE_UNMATCHED_QUERY_REPORT,
                "target_entity_id": report_id,
                "metadata_": {"category_gap_notes": category_gap_notes},
            }
        )

    async def record_feature_flag_toggle(
        self,
        *,
        admin_user_id: uuid.UUID,
        flag_id: uuid.UUID,
        key: str,
        is_enabled: bool,
    ) -> AdminActionLog:
        """Records an admin toggling a `feature_flags` row (ADM-002,
        Decision 6, AC3/AC4)."""
        return await self.repository.create(
            {
                "admin_user_id": admin_user_id,
                "action_type": _ACTION_TYPE_FEATURE_FLAG_TOGGLED,
                "target_entity_type": _TARGET_ENTITY_TYPE_FEATURE_FLAG,
                "target_entity_id": flag_id,
                "metadata_": {"key": key, "is_enabled": is_enabled},
            }
        )

    async def record_system_setting_update(
        self,
        *,
        admin_user_id: uuid.UUID,
        setting_id: uuid.UUID,
        key: str,
        value: Any,
    ) -> AdminActionLog:
        """Records an admin updating a `system_settings` row (ADM-002,
        Decision 6, AC1/AC3)."""
        return await self.repository.create(
            {
                "admin_user_id": admin_user_id,
                "action_type": _ACTION_TYPE_SYSTEM_SETTING_UPDATED,
                "target_entity_type": _TARGET_ENTITY_TYPE_SYSTEM_SETTING,
                "target_entity_id": setting_id,
                "metadata_": {"key": key, "value": value},
            }
        )
