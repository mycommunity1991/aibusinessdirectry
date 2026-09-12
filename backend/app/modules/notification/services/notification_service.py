"""
Notification generation (VER-002, AC5) -- honestly records "a
notification of this type, with this plain-language content, was
generated for this user." No real WhatsApp/SMS/Email delivery
mechanism exists yet (Decision 3, `Plan_S05_VER-002.md`); this module
does not pretend otherwise.

Exposes `notify_verification_status_change`, with **hardcoded,
plain-language copy** -- never simply interpolating the raw
`VerificationStatus` enum member into `title`/`body` (AC5's literal
"never exposing internal status enum values") -- and
`notify_new_contact_view` (CON-001, AC7, Decision 3,
`Plan_S08_CON-001.md`), the same hardcoded-copy/same-shape pattern
applied to a claimed provider's new Contact View.
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

_TYPE_NEW_CONTACT_VIEW = "new_contact_view"
_RELATED_ENTITY_TYPE_CONTACT_VIEW = "contact_view"
_TITLE_NEW_CONTACT_VIEW = "You have a new lead"
_BODY_NEW_CONTACT_VIEW = "A customer just viewed your contact details."


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

    async def notify_new_contact_view(
        self,
        *,
        user_id: uuid.UUID,
        contact_view_id: uuid.UUID,
    ) -> Notification:
        """
        Records a plain-language "new lead" notification for a claimed
        provider's Account (CON-001, AC7) -- called once, synchronously,
        from `ContactService.create_contact_view`, only when the
        contacted provider has an owning Account (`provider.user_id is
        not None`; a still-unclaimed listing has no Account to notify).

        `contact_view_id` becomes `related_entity_id`, mirroring
        `notify_verification_status_change`'s identical
        `related_entity_id` convention. This story only emits the
        in-app record -- real delivery (push/SMS/email) is ENG-001's
        own, later scope.
        """
        return await self.repository.create(
            {
                "user_id": user_id,
                "type": _TYPE_NEW_CONTACT_VIEW,
                "title": _TITLE_NEW_CONTACT_VIEW,
                "body": _BODY_NEW_CONTACT_VIEW,
                "related_entity_type": _RELATED_ENTITY_TYPE_CONTACT_VIEW,
                "related_entity_id": contact_view_id,
            }
        )
