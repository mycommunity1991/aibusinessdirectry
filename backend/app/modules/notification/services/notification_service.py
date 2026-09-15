"""
Notification generation (VER-002, AC5; extended in place by `ENG-001`,
Decision 1, `Plan_S12_ENG-001.md`) -- honestly records "a notification
of this type, with this plain-language content, was generated for this
user," now layered with real preference enforcement (AC4) and
multi-channel delivery dispatch (AC2/AC5/AC7) for the two urgent
trigger types.

Exposes `notify_verification_status_change`, with **hardcoded,
plain-language copy** -- never simply interpolating the raw
`VerificationStatus` enum member into `title`/`body` (AC5's literal
"never exposing internal status enum values") -- `notify_new_contact_view`
(CON-001, AC7, Decision 3, `Plan_S08_CON-001.md`), the same
hardcoded-copy/same-shape pattern applied to a claimed provider's new
Contact View, `notify_outcome_tag_prompt` (REV-001, AC3, Decision
5, `Plan_S09_REV-001.md`), the same shape again, applied to prompting
the *customer* to tag whether a Contact View led to a hire, and
`notify_manual_match_assignment_created` (`ENG-001`, AC3, Decision 9),
a genuinely new fourth trigger broadcasting an in-app-only notification
to every `ROLE_ADMIN` account.

**In-place extension, not a parallel mechanism (Decision 1):** the
three original methods' existing signatures, existing copy templates,
and existing callers (`AdminVerificationService`, `ContactService`) are
unchanged -- each now additionally runs a preference check (Decision 5)
*before* creating its `notifications` row (a muted category is a full
hard stop -- no row at all), and, only for the two urgent trigger types
(Decision 6), a channel-enabled check plus a delivery-dispatch call
*after* the row is created. `notify_outcome_tag_prompt` and
`notify_manual_match_assignment_created` never call
`NotificationDeliveryService`, regardless of preference state --
urgency is a fixed, code-level property, never a further user
preference (Decision 6).
"""

import uuid

from app.core.authorization import ensure_owner_or_not_found
from app.core.constants import ROLE_ADMIN
from app.core.exceptions import NotificationNotFoundError
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.notification.models import Notification
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.modules.notification.services.notification_preference_service import (
    NotificationPreferenceService,
)

_TYPE_VERIFICATION_STATUS_CHANGE = "verification_status_change"
_RELATED_ENTITY_TYPE_VERIFICATION_RECORD = "verification_record"
_CATEGORY_VERIFICATION = "verification"

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
_CATEGORY_LEADS = "leads"

_TYPE_OUTCOME_TAG_PROMPT = "outcome_tag_prompt"
_TITLE_OUTCOME_TAG_PROMPT = "Did you hire them?"
_BODY_OUTCOME_TAG_PROMPT = (
    "Let us know whether you hired the provider you just contacted."
)
_CATEGORY_OUTCOME_PROMPTS = "outcome_prompts"

_TYPE_MANUAL_MATCH_ASSIGNMENT_CREATED = "manual_match_assignment_created"
_RELATED_ENTITY_TYPE_MANUAL_MATCH_ASSIGNMENT = "manual_match_assignment"
_TITLE_MANUAL_MATCH_ASSIGNMENT_CREATED = "New manual match assignment"
_BODY_MANUAL_MATCH_ASSIGNMENT_CREATED = (
    "A conversation session was routed to the manual match queue and "
    "needs review."
)


def _rejected_body(rejection_reason: str | None) -> str:
    return (
        f"We weren't able to verify your submission. Reason: "
        f"{rejection_reason}. You can review the details and resubmit "
        "your documents."
    )


class NotificationService:
    """Generates in-app notification rows (AC5) via `NotificationRepository`,
    enforcing preference hard stops (AC4) and dispatching external
    delivery (AC2/AC5/AC7) for urgent trigger types (Decision 6)."""

    def __init__(
        self,
        repository: NotificationRepository,
        preference_service: NotificationPreferenceService,
        delivery_service: NotificationDeliveryService,
        role_repository: RoleRepository,
    ) -> None:
        self.repository = repository
        self.preference_service = preference_service
        self.delivery_service = delivery_service
        self.role_repository = role_repository

    async def notify_verification_status_change(
        self,
        *,
        user_id: uuid.UUID,
        approved: bool,
        rejection_reason: str | None,
        verification_record_id: uuid.UUID,
    ) -> Notification | None:
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

        `ENG-001` (Decision 5/6): a muted `"verification"` category is
        a full hard stop -- returns `None`, no row of any kind is
        created. Otherwise the row is always created, then (urgent,
        Decision 6) dispatched externally if the recipient's channel is
        enabled.
        """
        if not await self.preference_service.is_category_allowed(
            user_id, category=_CATEGORY_VERIFICATION
        ):
            return None

        title = _TITLE_APPROVED if approved else _TITLE_REJECTED
        body = _BODY_APPROVED if approved else _rejected_body(rejection_reason)

        notification = await self.repository.create(
            {
                "user_id": user_id,
                "type": _TYPE_VERIFICATION_STATUS_CHANGE,
                "title": title,
                "body": body,
                "related_entity_type": _RELATED_ENTITY_TYPE_VERIFICATION_RECORD,
                "related_entity_id": verification_record_id,
            }
        )
        await self._dispatch_if_channel_enabled(notification)
        return notification

    async def notify_new_contact_view(
        self,
        *,
        user_id: uuid.UUID,
        contact_view_id: uuid.UUID,
    ) -> Notification | None:
        """
        Records a plain-language "new lead" notification for a claimed
        provider's Account (CON-001, AC7) -- called once, synchronously,
        from `ContactService.create_contact_view`, only when the
        contacted provider has an owning Account (`provider.user_id is
        not None`; a still-unclaimed listing has no Account to notify).

        `contact_view_id` becomes `related_entity_id`, mirroring
        `notify_verification_status_change`'s identical
        `related_entity_id` convention.

        `ENG-001` (Decision 5/6): a muted `"leads"` category is a full
        hard stop -- returns `None`, no row of any kind is created.
        Otherwise the row is always created, then (urgent, Decision 6)
        dispatched externally if the recipient's channel is enabled.
        """
        if not await self.preference_service.is_category_allowed(
            user_id, category=_CATEGORY_LEADS
        ):
            return None

        notification = await self.repository.create(
            {
                "user_id": user_id,
                "type": _TYPE_NEW_CONTACT_VIEW,
                "title": _TITLE_NEW_CONTACT_VIEW,
                "body": _BODY_NEW_CONTACT_VIEW,
                "related_entity_type": _RELATED_ENTITY_TYPE_CONTACT_VIEW,
                "related_entity_id": contact_view_id,
            }
        )
        await self._dispatch_if_channel_enabled(notification)
        return notification

    async def notify_outcome_tag_prompt(
        self,
        *,
        user_id: uuid.UUID,
        contact_view_id: uuid.UUID,
    ) -> Notification | None:
        """
        Records a plain-language "did you hire them?" prompt
        notification for the *customer* who just generated a Contact
        View (REV-001, AC3, Decision 5, `Plan_S09_REV-001.md`) -- called
        once, synchronously, unconditionally, from `ContactService.
        create_contact_view`, immediately after the `contact_views` row
        is created. Unconditional (unlike `notify_new_contact_view`)
        because the calling customer always has an owning Account --
        there is no "unclaimed listing" equivalent gap on this side.

        `type="outcome_tag_prompt"`, already the exact value
        `04_DATABASE.md`'s own `notifications.type` column documentation
        names. `contact_view_id` becomes `related_entity_id`, mirroring
        `notify_new_contact_view`'s identical convention.

        `ENG-001` (Decision 5/6): a muted `"outcome_prompts"` category
        is a full hard stop -- returns `None`. Otherwise the row is
        created, but **never** dispatched externally -- this is a
        fixed, non-urgent trigger type (Decision 6): the outcome-tag
        prompt is already surfaced inline, immediately, via the
        existing mobile bottom-sheet, so a duplicate external push
        would be redundant.
        """
        if not await self.preference_service.is_category_allowed(
            user_id, category=_CATEGORY_OUTCOME_PROMPTS
        ):
            return None

        return await self.repository.create(
            {
                "user_id": user_id,
                "type": _TYPE_OUTCOME_TAG_PROMPT,
                "title": _TITLE_OUTCOME_TAG_PROMPT,
                "body": _BODY_OUTCOME_TAG_PROMPT,
                "related_entity_type": _RELATED_ENTITY_TYPE_CONTACT_VIEW,
                "related_entity_id": contact_view_id,
            }
        )

    async def notify_manual_match_assignment_created(
        self, assignment_id: uuid.UUID
    ) -> list[Notification]:
        """
        `ENG-001`, AC3, Decision 9 -- a genuinely new fourth trigger.
        Looks up every current `ROLE_ADMIN` user id (`identity.
        RoleRepository.get_user_ids_for_role`, the reverse of the
        existing `get_role_names_for_user`) and creates one
        `notifications` row per admin -- **and nothing else**: no
        preference check (no admin-specific category flag exists or is
        needed), no `NotificationDeliveryService` call, no external
        channel dispatch of any kind, ever. Purely an in-app row,
        consistent with every existing admin capability in this
        codebase being pull-based -- never a new, invented "admin team"
        push mechanism.
        """
        admin_user_ids = await self.role_repository.get_user_ids_for_role(ROLE_ADMIN)
        return [
            await self.repository.create(
                {
                    "user_id": admin_user_id,
                    "type": _TYPE_MANUAL_MATCH_ASSIGNMENT_CREATED,
                    "title": _TITLE_MANUAL_MATCH_ASSIGNMENT_CREATED,
                    "body": _BODY_MANUAL_MATCH_ASSIGNMENT_CREATED,
                    "related_entity_type": (
                        _RELATED_ENTITY_TYPE_MANUAL_MATCH_ASSIGNMENT
                    ),
                    "related_entity_id": assignment_id,
                }
            )
            for admin_user_id in admin_user_ids
        ]

    async def list_for_user(
        self, user_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[Notification], int]:
        """
        `ENG-001`, AC6, Decision 10 -- one page of `user_id`'s own
        notifications, newest first, plus a total count for
        `PaginationMeta`. Backs `GET /notifications`.
        """
        return await self.repository.list_for_user(
            user_id, page=page, page_size=page_size
        )

    async def count_unread(self, user_id: uuid.UUID) -> int:
        """`ENG-001`, AC5, Decision 10 -- backs `GET /notifications/
        unread-count`."""
        return await self.repository.count_unread(user_id)

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        """
        `ENG-001`, AC6, Decision 10 -- backs `PATCH /notifications/
        {id}/read`. `NotificationRepository.mark_read` is a plain,
        ownership-scoped `UPDATE ... RETURNING` with no business logic
        of its own -- it returns `None` both when the row is already
        read (idempotent no-op) and when `notification_id` doesn't
        exist at all or isn't owned by `user_id`. On that `None`, this
        method re-fetches via a plain, ownership-agnostic `get_by_id`
        and calls `ensure_owner_or_not_found` (mirroring `SavedAddress
        Service.update_address`/`delete_address`'s identical shape) to
        tell those two cases apart: an already-read row owned by
        `user_id` is returned as-is (idempotent), while a missing/not-
        owned row raises `NotificationNotFoundError` (404, never a 403
        -- `ADR-015`) -- both of *those* sub-cases collapsed into the
        same non-revealing 404 by `ensure_owner_or_not_found` itself.
        """
        notification = await self.repository.mark_read(notification_id, user_id)
        if notification is not None:
            return notification

        existing = await self.repository.get_by_id(notification_id)
        ensure_owner_or_not_found(
            existing.user_id if existing is not None else None,
            user_id,
            not_found_exc=NotificationNotFoundError(),
        )
        assert existing is not None  # narrows for type-checkers; guaranteed above
        return existing

    async def _dispatch_if_channel_enabled(self, notification: Notification) -> None:
        """
        Shared by the two urgent trigger types (Decision 6): if the
        recipient's channel is currently enabled, dispatches the
        already-created `notification` via `NotificationDeliveryService`
        over their preferred channel. Never called by
        `notify_outcome_tag_prompt`/`notify_manual_match_assignment_
        created` -- those are fixed, non-urgent trigger types that never
        reach external delivery, regardless of preference state.
        """
        if not await self.preference_service.is_channel_enabled(notification.user_id):
            return
        preferences = await self.preference_service.get_or_create_for_user(
            notification.user_id
        )
        await self.delivery_service.send(notification, channel=preferences.channel)
