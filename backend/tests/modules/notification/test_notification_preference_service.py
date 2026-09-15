"""
Integration tests for `NotificationPreferenceService` (`ENG-001`, AC4,
Decision 4/5, `Plan_S12_ENG-001.md`), exercised against a real Postgres
database.
"""

import pytest

from app.modules.customer.models import (
    CustomerPreferences,
    CustomerProfile,
    NotificationChannel,
)
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.notification.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from app.modules.notification.services.notification_preference_service import (
    NotificationPreferenceService,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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


async def _make_customer_with_preferences(
    db_session, user: User, *, notification_channel: NotificationChannel
) -> None:
    profile = CustomerProfile(user_id=user.id, display_name="Test Customer")
    db_session.add(profile)
    await db_session.flush()
    preferences = CustomerPreferences(
        customer_id=profile.id, notification_channel=notification_channel
    )
    db_session.add(preferences)
    await db_session.commit()


def _make_service(db_session) -> NotificationPreferenceService:
    return NotificationPreferenceService(
        NotificationPreferenceRepository(db_session),
        CustomerProfileRepository(db_session),
        CustomerPreferencesRepository(db_session),
    )


class TestGetOrCreateForUser:
    @pytest.mark.anyio
    async def test_seeds_whatsapp_for_a_provider_or_admin_account(
        self, db_session
    ) -> None:
        """No `customer_profiles` row exists for this user -- falls back
        to `whatsapp`, matching the column's own documented server
        default (Decision 4)."""
        user = await _make_user(db_session, "920000001")
        service = _make_service(db_session)

        preferences = await service.get_or_create_for_user(user.id)

        assert preferences.user_id == user.id
        assert preferences.channel == NotificationChannel.WHATSAPP
        assert preferences.channel_enabled is True
        assert preferences.leads_enabled is True
        assert preferences.verification_enabled is True
        assert preferences.outcome_prompts_enabled is True

    @pytest.mark.anyio
    async def test_seeds_the_customers_own_existing_channel_preference(
        self, db_session
    ) -> None:
        """A customer with an already-set `customer_preferences.
        notification_channel` of `email` (not the default `whatsapp`)
        gets that exact value seeded into the new row -- proving
        Decision 4's seeding genuinely reads the right source, not
        just the column's own default."""
        user = await _make_user(db_session, "920000002")
        await _make_customer_with_preferences(
            db_session, user, notification_channel=NotificationChannel.EMAIL
        )
        service = _make_service(db_session)

        preferences = await service.get_or_create_for_user(user.id)

        assert preferences.channel == NotificationChannel.EMAIL

    @pytest.mark.anyio
    async def test_returns_the_same_row_not_a_second_one_on_a_second_call(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "920000003")
        service = _make_service(db_session)

        first = await service.get_or_create_for_user(user.id)
        second = await service.get_or_create_for_user(user.id)

        assert first.id == second.id

    @pytest.mark.anyio
    async def test_fresh_row_defaults_honor_the_documented_true_defaults(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "920000004")
        service = _make_service(db_session)
        await service.get_or_create_for_user(user.id)

        assert await service.is_category_allowed(user.id, category="leads") is True
        assert (
            await service.is_category_allowed(user.id, category="verification")
            is True
        )
        assert (
            await service.is_category_allowed(user.id, category="outcome_prompts")
            is True
        )
        assert await service.is_channel_enabled(user.id) is True


class TestIsCategoryAllowedAndIsChannelEnabled:
    @pytest.mark.anyio
    async def test_reflects_a_real_rows_stored_values(self, db_session) -> None:
        user = await _make_user(db_session, "920000005")
        preference_repository = NotificationPreferenceRepository(db_session)
        row = await preference_repository.try_create(
            {
                "user_id": user.id,
                "channel": NotificationChannel.SMS,
                "channel_enabled": False,
                "leads_enabled": False,
                "verification_enabled": True,
                "outcome_prompts_enabled": True,
            }
        )
        await db_session.commit()
        assert row is not None
        service = _make_service(db_session)

        assert await service.is_category_allowed(user.id, category="leads") is False
        assert (
            await service.is_category_allowed(user.id, category="verification")
            is True
        )
        assert await service.is_channel_enabled(user.id) is False
