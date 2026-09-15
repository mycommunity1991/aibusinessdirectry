"""
Integration tests for `NotificationService`/`NotificationRepository`
(VER-002, AC5; extended by `ENG-001`, Decision 1, `Plan_S12_ENG-001.md`),
exercised against a real Postgres database.

The original 12 tests (`TestNotifyVerificationStatusChange`/
`TestNotifyNewContactView`/`TestNotifyOutcomeTagPrompt`) are unchanged
in their assertions -- only their service-construction helper changed
(item 18, `Plan_S12_ENG-001.md`) -- re-confirming Decision 1's in-place
extension broke nothing already shipped (every account defaults to
allow-everything, Decision 5/Open Question 1). New test classes below
cover AC4 (preference-disabled blocking), AC5/AC6 (urgent-vs-non-urgent
delivery dispatch), and AC3/Decision 9 (the new admin-broadcast trigger).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.constants import ROLE_ADMIN
from app.modules.customer.models import NotificationChannel
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.identity.services.seed_data import seed_roles
from app.modules.notification.models import Notification, NotificationDelivery
from app.modules.notification.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.modules.notification.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.modules.notification.services.notification_preference_service import (
    NotificationPreferenceService,
)
from app.modules.notification.services.notification_sender import (
    NotificationSender,
    StubEmailSender,
    StubSmsSender,
    StubWhatsAppSender,
)
from app.modules.notification.services.notification_service import NotificationService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _SpySender(NotificationSender):
    """Records every `send` call, always succeeds -- used to prove the
    sender registry is (or is not) invoked, never to force a failure."""

    def __init__(self) -> None:
        self.calls: list[uuid.UUID] = []

    async def send(self, *, recipient_user_id, title, body) -> str | None:
        self.calls.append(recipient_user_id)
        return None


def _make_service(
    db_session, *, whatsapp_sender: NotificationSender | None = None
) -> NotificationService:
    return NotificationService(
        repository=NotificationRepository(db_session),
        preference_service=NotificationPreferenceService(
            NotificationPreferenceRepository(db_session),
            CustomerProfileRepository(db_session),
            CustomerPreferencesRepository(db_session),
        ),
        delivery_service=NotificationDeliveryService(
            NotificationDeliveryRepository(db_session),
            {
                NotificationChannel.WHATSAPP: whatsapp_sender or StubWhatsAppSender(),
                NotificationChannel.SMS: StubSmsSender(),
                NotificationChannel.EMAIL: StubEmailSender(),
            },
        ),
        role_repository=RoleRepository(db_session),
    )


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _set_preferences(
    db_session,
    user_id: uuid.UUID,
    **overrides: object,
) -> None:
    """Pre-creates a `notification_preferences` row with explicit
    overrides -- so a test can exercise a muted category/disabled
    channel without relying on `get_or_create_for_user`'s own defaults."""
    values = {
        "user_id": user_id,
        "channel": NotificationChannel.WHATSAPP,
        "channel_enabled": True,
        "leads_enabled": True,
        "verification_enabled": True,
        "outcome_prompts_enabled": True,
    }
    values.update(overrides)
    row = await NotificationPreferenceRepository(db_session).try_create(values)
    await db_session.commit()
    assert row is not None


class TestNotifyVerificationStatusChange:
    async def test_approved_uses_the_exact_copy_template(self, db_session) -> None:
        user = await _make_user(db_session, "901000001")
        record_id = uuid.uuid4()
        service = _make_service(db_session)

        notification = await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=record_id,
        )
        await db_session.commit()

        assert notification.user_id == user.id
        assert notification.type == "verification_status_change"
        assert notification.title == "Verification approved"
        assert notification.body == (
            "Great news — your verification has been approved. Your "
            "listing is now visible to customers."
        )
        assert notification.related_entity_type == "verification_record"
        assert notification.related_entity_id == record_id

        result = await db_session.execute(
            select(Notification).where(Notification.id == notification.id)
        )
        persisted = result.scalar_one()
        assert persisted.title == "Verification approved"

    async def test_rejected_uses_the_exact_copy_template_with_the_reason(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "901000002")
        record_id = uuid.uuid4()
        service = _make_service(db_session)

        notification = await service.notify_verification_status_change(
            user_id=user.id,
            approved=False,
            rejection_reason="Illegible document.",
            verification_record_id=record_id,
        )

        assert notification.title == "Verification update"
        assert notification.body == (
            "We weren't able to verify your submission. Reason: "
            "Illegible document.. You can review the details and "
            "resubmit your documents."
        )

    async def test_neither_title_nor_body_ever_contains_a_raw_enum_token(
        self, db_session
    ) -> None:
        """AC5: "never exposing internal status enum values" -- neither
        the qualified `VerificationStatus.APPROVED`/`REJECTED` repr nor
        the bare enum member name ever leaks into user-facing copy."""
        user = await _make_user(db_session, "901000003")
        service = _make_service(db_session)

        approved = await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=uuid.uuid4(),
        )
        rejected = await service.notify_verification_status_change(
            user_id=user.id,
            approved=False,
            rejection_reason="Blurry photo.",
            verification_record_id=uuid.uuid4(),
        )

        for notification in (approved, rejected):
            assert "VerificationStatus" not in notification.title
            assert "VerificationStatus" not in notification.body
            assert "PENDING" not in notification.title
            assert "PENDING" not in notification.body
            assert "UNDER_REVIEW" not in notification.title
            assert "UNDER_REVIEW" not in notification.body

        # The word "approved" legitimately appears in the approved
        # template's own plain-language sentence -- but never as a bare,
        # capitalized internal status token like "APPROVED"/"REJECTED".
        assert "APPROVED" not in approved.title
        assert "APPROVED" not in approved.body
        assert "REJECTED" not in rejected.title
        assert "REJECTED" not in rejected.body

    async def test_each_call_creates_exactly_one_row(self, db_session) -> None:
        user = await _make_user(db_session, "901000004")
        service = _make_service(db_session)

        await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=uuid.uuid4(),
        )
        await db_session.commit()

        result = await db_session.execute(select(Notification))
        assert len(result.scalars().all()) == 1


class TestNotifyNewContactView:
    """CON-001, AC7, Decision 3, `Plan_S08_CON-001.md`."""

    async def test_creates_the_expected_row_shape(self, db_session) -> None:
        user = await _make_user(db_session, "901000005")
        contact_view_id = uuid.uuid4()
        service = _make_service(db_session)

        notification = await service.notify_new_contact_view(
            user_id=user.id, contact_view_id=contact_view_id
        )
        await db_session.commit()

        assert notification.user_id == user.id
        assert notification.type == "new_contact_view"
        assert notification.title == "You have a new lead"
        assert notification.body == "A customer just viewed your contact details."
        assert notification.related_entity_type == "contact_view"
        assert notification.related_entity_id == contact_view_id

        result = await db_session.execute(
            select(Notification).where(Notification.id == notification.id)
        )
        persisted = result.scalar_one()
        assert persisted.type == "new_contact_view"

    async def test_each_call_creates_exactly_one_row(self, db_session) -> None:
        user = await _make_user(db_session, "901000006")
        service = _make_service(db_session)

        await service.notify_new_contact_view(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Notification).where(Notification.type == "new_contact_view")
        )
        assert len(result.scalars().all()) == 1


class TestNotifyOutcomeTagPrompt:
    """REV-001, AC3, Decision 5, `Plan_S09_REV-001.md`."""

    async def test_creates_the_expected_row_shape(self, db_session) -> None:
        user = await _make_user(db_session, "901000007")
        contact_view_id = uuid.uuid4()
        service = _make_service(db_session)

        notification = await service.notify_outcome_tag_prompt(
            user_id=user.id, contact_view_id=contact_view_id
        )
        await db_session.commit()

        assert notification.user_id == user.id
        assert notification.type == "outcome_tag_prompt"
        assert notification.title == "Did you hire them?"
        assert notification.body == (
            "Let us know whether you hired the provider you just contacted."
        )
        assert notification.related_entity_type == "contact_view"
        assert notification.related_entity_id == contact_view_id

        result = await db_session.execute(
            select(Notification).where(Notification.id == notification.id)
        )
        persisted = result.scalar_one()
        assert persisted.type == "outcome_tag_prompt"

    async def test_each_call_creates_exactly_one_row(self, db_session) -> None:
        user = await _make_user(db_session, "901000008")
        service = _make_service(db_session)

        await service.notify_outcome_tag_prompt(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Notification).where(Notification.type == "outcome_tag_prompt")
        )
        assert len(result.scalars().all()) == 1


class TestPreferenceEnforcement:
    """`ENG-001`, AC4/AC8, Decision 5."""

    async def test_a_muted_category_blocks_the_entire_send(self, db_session) -> None:
        """A muted `"leads"` category is a full hard stop -- zero
        `notifications` rows, and the sender registry is never
        invoked."""
        user = await _make_user(db_session, "940000001")
        await _set_preferences(db_session, user.id, leads_enabled=False)
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        result = await service.notify_new_contact_view(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        assert result is None
        assert sender.calls == []

        notifications = await db_session.execute(
            select(Notification).where(Notification.user_id == user.id)
        )
        assert notifications.scalars().all() == []
        deliveries = await db_session.execute(select(NotificationDelivery))
        assert deliveries.scalars().all() == []

    async def test_a_disabled_channel_blocks_only_external_delivery(
        self, db_session
    ) -> None:
        """`channel_enabled=False` still creates the in-app row, but no
        `notification_delivery` row is ever created and the sender is
        never called -- the two hard stops are independent."""
        user = await _make_user(db_session, "940000002")
        await _set_preferences(db_session, user.id, channel_enabled=False)
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        notification = await service.notify_new_contact_view(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        assert notification is not None
        assert sender.calls == []

        deliveries = await db_session.execute(select(NotificationDelivery))
        assert deliveries.scalars().all() == []


class TestUrgencyClassification:
    """`ENG-001`, AC5/AC6, Decision 6 -- urgency is fixed by trigger
    type, never a further user preference."""

    async def test_new_contact_view_dispatches_external_delivery(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "940000003")
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        await service.notify_new_contact_view(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        assert sender.calls == [user.id]

    async def test_verification_status_change_dispatches_external_delivery(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "940000004")
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        await service.notify_verification_status_change(
            user_id=user.id,
            approved=True,
            rejection_reason=None,
            verification_record_id=uuid.uuid4(),
        )
        await db_session.commit()

        assert sender.calls == [user.id]

    async def test_outcome_tag_prompt_never_dispatches_external_delivery(
        self, db_session
    ) -> None:
        """Non-urgent, even with every preference enabled (Decision 6):
        `notify_outcome_tag_prompt` never calls
        `NotificationDeliveryService`, regardless of preference state."""
        user = await _make_user(db_session, "940000005")
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        await service.notify_outcome_tag_prompt(
            user_id=user.id, contact_view_id=uuid.uuid4()
        )
        await db_session.commit()

        assert sender.calls == []
        deliveries = await db_session.execute(select(NotificationDelivery))
        assert deliveries.scalars().all() == []

    async def test_manual_match_assignment_created_never_dispatches_external_delivery(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        role_repository = RoleRepository(db_session)
        admin_user = await _make_user(db_session, "940000006")
        await RoleAssignmentService(role_repository).ensure_role_assigned(
            admin_user.id, ROLE_ADMIN
        )
        sender = _SpySender()
        service = _make_service(db_session, whatsapp_sender=sender)

        await service.notify_manual_match_assignment_created(uuid.uuid4())
        await db_session.commit()

        assert sender.calls == []
        deliveries = await db_session.execute(select(NotificationDelivery))
        assert deliveries.scalars().all() == []


class TestNotifyManualMatchAssignmentCreated:
    """`ENG-001`, AC3, Decision 9."""

    async def test_creates_one_row_per_seeded_admin_account(self, db_session) -> None:
        await seed_roles(db_session)
        role_repository = RoleRepository(db_session)
        role_assignment_service = RoleAssignmentService(role_repository)
        admin_one = await _make_user(db_session, "940000007")
        admin_two = await _make_user(db_session, "940000008")
        customer = await _make_user(db_session, "940000009")
        await role_assignment_service.ensure_role_assigned(admin_one.id, ROLE_ADMIN)
        await role_assignment_service.ensure_role_assigned(admin_two.id, ROLE_ADMIN)
        assignment_id = uuid.uuid4()
        service = _make_service(db_session)

        notifications = await service.notify_manual_match_assignment_created(
            assignment_id
        )
        await db_session.commit()

        assert len(notifications) == 2
        recipient_ids = {n.user_id for n in notifications}
        assert recipient_ids == {admin_one.id, admin_two.id}
        for notification in notifications:
            assert notification.type == "manual_match_assignment_created"
            assert notification.related_entity_type == "manual_match_assignment"
            assert notification.related_entity_id == assignment_id

        result = await db_session.execute(select(Notification))
        assert len(result.scalars().all()) == 2
        assert customer.id not in recipient_ids

    async def test_returns_an_empty_list_when_no_admin_account_exists(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        service = _make_service(db_session)

        notifications = await service.notify_manual_match_assignment_created(
            uuid.uuid4()
        )
        await db_session.commit()

        assert notifications == []
