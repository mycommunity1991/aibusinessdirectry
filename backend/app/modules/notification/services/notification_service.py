"""
Notification generation (VER-002, AC5) -- honestly records "a
notification of this type, with this plain-language content, was
generated for this user." No real WhatsApp/SMS/Email delivery
mechanism exists yet (Decision 3, `Plan_S05_VER-002.md`); this module
does not pretend otherwise.

Exposes one explicit method, `notify_verification_status_change`, with
**hardcoded, plain-language copy** -- never simply interpolating the
raw `VerificationStatus` enum member into `title`/`body` (AC5's literal
"never exposing internal status enum values").
"""

import uuid

from app.modules.notification.models import Notification
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)

_TYPE_VERIFICATION_STATUS_CHANGE = "verification_status_change"
_RELATED_ENTITY_TYPE_VERIFICATION_RECORD = "verification_record"

_TITLE_APPROVED = "Verification approved"
_BODY_APPROVED = (
    "Great news — your verification has been approved. Your listing is "
    "now visible to customers."
)
_TITLE_REJECTED = "Verification update"


def _rejected_body(rejection_reason: str | None) -> str:
    return (
        f"We weren't able to verify your submission. Reason: "
        f"{rejection_reason}. You can review the details and resubmit "
        "your documents."
    )


class NotificationService:
    """Generates in-app notification rows (AC5) via `NotificationRepository`."""

    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    async def notify_verification_status_change(
        self,
        *,
        user_id: uuid.UUID,
        approved: bool,
        rejection_reason: str | None,
        verification_record_id: uuid.UUID,
    ) -> Notification:
        """
        Records a plain-language notification for a verification
        status change (AC5). `verification_record_id` becomes
        `related_entity_id` (`04_DATABASE.md`'s own example value for
        this table) -- required here (beyond the Plan's own abbreviated
        signature) since `related_entity_id` cannot otherwise be set;
        see the Walkthrough's noted deviation.

        Copy is always one of the two exact, hardcoded templates below
        -- never the raw `VerificationStatus` enum value, satisfying
        AC5's "never exposing internal status enum values" literally.
        """
        title = _TITLE_APPROVED if approved else _TITLE_REJECTED
        body = _BODY_APPROVED if approved else _rejected_body(rejection_reason)

        return await self.repository.create(
            {
                "user_id": user_id,
                "type": _TYPE_VERIFICATION_STATUS_CHANGE,
                "title": title,
                "body": body,
                "related_entity_type": _RELATED_ENTITY_TYPE_VERIFICATION_RECORD,
                "related_entity_id": verification_record_id,
            }
        )
