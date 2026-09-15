"""
`NotificationPreferenceService` (`ENG-001`, AC4, Decision 4/5,
`Plan_S12_ENG-001.md`) -- resolves, lazily creates, and enforces a
user's notification preferences.

Depends directly on `customer.CustomerProfileRepository`/`customer.
CustomerPreferencesRepository` -- a documented `ADR-047` exception (no
side-effect-free `CustomerService` read primitive exists;
`CustomerService.get_my_profile` auto-provisions a profile as a side
effect, which would be wrong to trigger here for a Provider/Admin
account that legitimately has no customer profile at all). Named
explicitly here and in `notification/dependencies.py`'s own docstring,
per `ADR-054`'s naming-duty precedent.
"""

import uuid
from typing import Literal

from app.modules.customer.models import NotificationChannel
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.notification.models import NotificationPreference
from app.modules.notification.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)

NotificationCategory = Literal["leads", "verification", "outcome_prompts"]

_DEFAULT_CHANNEL = NotificationChannel.WHATSAPP


class NotificationPreferenceService:
    """Resolves/lazily-creates a user's `notification_preferences` row
    and answers the two hard-stop questions AC4 requires."""

    def __init__(
        self,
        repository: NotificationPreferenceRepository,
        customer_profile_repository: CustomerProfileRepository,
        customer_preferences_repository: CustomerPreferencesRepository,
    ) -> None:
        self.repository = repository
        self.customer_profile_repository = customer_profile_repository
        self.customer_preferences_repository = customer_preferences_repository

    async def get_or_create_for_user(
        self, user_id: uuid.UUID
    ) -> NotificationPreference:
        """
        Resolves `user_id`'s `notification_preferences` row, lazily
        creating one with default-allow values (Decision 5, Open
        Question 1) on first touch.

        A customer account's initial `channel` is seeded from their
        already-existing `customer_preferences.notification_channel`
        value (Decision 4) -- a one-time seed at row-creation time only,
        via raw, read-only repository lookups (no side effects, never
        provisioning a new customer profile as a byproduct). A
        provider/admin account (or a customer somehow missing that
        row) defaults to `whatsapp`, matching the column's own
        documented server-default.
        """
        existing = await self.repository.get_by_user_id(user_id)
        if existing is not None:
            return existing

        channel = await self._seed_channel_for_user(user_id)
        created = await self.repository.try_create(
            {"user_id": user_id, "channel": channel}
        )
        if created is not None:
            return created

        # A concurrent first-touch for this same user won the race --
        # resolve the row it created rather than raising.
        row = await self.repository.get_by_user_id(user_id)
        assert row is not None
        return row

    async def _seed_channel_for_user(self, user_id: uuid.UUID) -> NotificationChannel:
        customer_profile = await self.customer_profile_repository.get_by_user_id(
            user_id
        )
        if customer_profile is None:
            return _DEFAULT_CHANNEL

        customer_preferences = (
            await self.customer_preferences_repository.get_by_customer_id(
                customer_profile.id
            )
        )
        if customer_preferences is None:
            return _DEFAULT_CHANNEL

        return NotificationChannel(customer_preferences.notification_channel)

    async def is_category_allowed(
        self, user_id: uuid.UUID, *, category: NotificationCategory
    ) -> bool:
        """
        AC4's first hard stop: is `category` allowed at all? `False`
        means the entire `notify_*` call becomes a no-op (Decision 5) --
        no `notifications` row, no `notification_delivery` row.
        """
        preferences = await self.get_or_create_for_user(user_id)
        return {
            "leads": preferences.leads_enabled,
            "verification": preferences.verification_enabled,
            "outcome_prompts": preferences.outcome_prompts_enabled,
        }[category]

    async def is_channel_enabled(self, user_id: uuid.UUID) -> bool:
        """
        AC4's second, independent hard stop: is any external channel
        currently enabled at all? Gates only the external-delivery
        attempt (Decision 5) -- a muted category and a disabled channel
        are two independently-checkable hard stops, neither bypassable
        by the other.
        """
        preferences = await self.get_or_create_for_user(user_id)
        return preferences.channel_enabled
