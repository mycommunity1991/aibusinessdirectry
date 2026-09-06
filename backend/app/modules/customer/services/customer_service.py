"""
Customer profile/preferences provisioning and self-service (CUS-001).

`provision_default_profile` is called by `identity.AuthService` inside
its existing `is_new_user` branches, using the same request-scoped
`AsyncSession` -- flush only, never commit (the endpoint's single
`await db.commit()` remains the only transaction boundary). This mirrors
the already-shipped `identity -> audit` cross-module pattern exactly
(Decision 1, `Plan_S03_CUS-001.md`). `identity`'s services depend on
this service class, never on the Customer repositories directly, per
`02_ARCHITECTURE.md`'s "modules communicate through services only" rule.

`get_my_profile`/`update_my_profile` are both get-or-create (Decision 4)
so a pre-CUS-001 (Sprint 2) account is lazily backfilled with default-
English preferences on its first `GET`/`PATCH /customers/me` call,
instead of a risky data-migration backfill script touching existing
rows.
"""

import uuid
from typing import Any

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
from app.modules.identity.models import LanguageCode

# Decision 6: neither the mobile-OTP path (phone number only) nor the
# current OAuth claims model (`subject`/`email`/`email_verified`, no name
# claim) provides a real display name at registration. A plain,
# obviously-placeholder value, immediately editable via `PATCH`.
DEFAULT_DISPLAY_NAME = "New Customer"

# `customer_profiles.display_name`/`customer_preferences.language`/
# `notification_channel` are the only fields a partial `PATCH` may ever
# touch -- these two sets are how `update_my_profile` routes each
# provided field to the right row.
_PROFILE_FIELDS = frozenset({"display_name", "avatar_url"})
_PREFERENCES_FIELDS = frozenset({"language", "notification_channel"})


class CustomerService:
    """Orchestrates customer profile/preferences provisioning, lookup, and update."""

    def __init__(
        self,
        profile_repository: CustomerProfileRepository,
        preferences_repository: CustomerPreferencesRepository,
    ) -> None:
        self.profile_repository = profile_repository
        self.preferences_repository = preferences_repository

    async def provision_default_profile(
        self, user_id: uuid.UUID, *, accept_language_header: str | None
    ) -> tuple[CustomerProfile, CustomerPreferences]:
        """
        Creates a `customer_profiles` row and a `customer_preferences`
        row for a brand-new Account (AC2/AC3/AC8) with sensible defaults:
        notification channel always WhatsApp; language derived from
        `accept_language_header`, falling back to English.

        Flush only -- never commits. The caller (`AuthService`) shares
        the same `AsyncSession` as the `User` row it just created, so
        both rows ride the endpoint's single, existing
        `await db.commit()` -- a genuine same-transaction guarantee, not
        a "call it right after" pattern that could partially fail.
        """
        profile = await self.profile_repository.create(
            {
                "user_id": user_id,
                "display_name": DEFAULT_DISPLAY_NAME,
                "avatar_url": None,
            }
        )
        preferences = await self.preferences_repository.create(
            {
                "customer_id": profile.id,
                "notification_channel": NotificationChannel.WHATSAPP,
                "language": self._resolve_default_language(accept_language_header),
            }
        )
        return profile, preferences

    async def get_my_profile(
        self, user_id: uuid.UUID
    ) -> tuple[CustomerProfile, CustomerPreferences]:
        """
        Get-or-create (Decision 4): a caller whose account predates
        CUS-001 has no `customer_profiles` row yet -- rather than 404ing,
        one is lazily provisioned here with the same defaults
        `provision_default_profile` would have used (no `Accept-Language`
        signal available at this point, so this falls straight back to
        English -- an acceptable, documented edge case for pre-CUS-001
        accounts only).
        """
        profile = await self.profile_repository.get_by_user_id(user_id)
        if profile is None:
            return await self.provision_default_profile(
                user_id, accept_language_header=None
            )

        preferences = await self.preferences_repository.get_by_customer_id(profile.id)
        if preferences is None:
            # Defensive: `provision_default_profile` always creates both
            # rows together, so this only fires for some already-broken
            # legacy state -- backfilled the same way as a missing
            # profile, rather than ever 404ing on the caller's own data.
            preferences = await self.preferences_repository.create(
                {
                    "customer_id": profile.id,
                    "notification_channel": NotificationChannel.WHATSAPP,
                    "language": LanguageCode.EN,
                }
            )
        return profile, preferences

    async def update_my_profile(
        self, user_id: uuid.UUID, *, fields: dict[str, Any]
    ) -> tuple[CustomerProfile, CustomerPreferences]:
        """
        Get-or-create (Decision 4), then partial-update: only keys
        present in `fields` are changed. The API layer passes
        `payload.model_dump(exclude_unset=True)` (Pydantic v2, Decision
        5) so an omitted field is left untouched, while a field
        explicitly set to `null` (e.g. clearing `avatar_url`) is applied.
        """
        profile, preferences = await self.get_my_profile(user_id)

        profile_updates = {k: v for k, v in fields.items() if k in _PROFILE_FIELDS}
        if profile_updates:
            profile = await self.profile_repository.update(profile, profile_updates)

        preferences_updates = {
            k: v for k, v in fields.items() if k in _PREFERENCES_FIELDS
        }
        if preferences_updates:
            preferences = await self.preferences_repository.update(
                preferences, preferences_updates
            )

        return profile, preferences

    @staticmethod
    def _resolve_default_language(accept_language_header: str | None) -> LanguageCode:
        """
        Parses a raw `Accept-Language` header value (e.g.
        `"ar-AE,ar;q=0.9,en;q=0.8"`) and returns the highest-`q`-weighted
        supported language (`en`/`ar`), falling back to English for a
        missing header, an unsupported/unparseable value, or no
        recognized language tag at all (AC3, Decision 3). This
        interpretation lives here -- a Customer-domain business rule --
        not in `identity`, which only ever passes the raw string through.
        """
        if not accept_language_header:
            return LanguageCode.EN

        weighted: list[tuple[str, float]] = []
        for entry in accept_language_header.split(","):
            entry = entry.strip()
            if not entry:
                continue
            tag, _, q_part = entry.partition(";")
            quality = 1.0
            q_part = q_part.strip()
            if q_part.lower().startswith("q="):
                try:
                    quality = float(q_part[2:].strip())
                except ValueError:
                    quality = 1.0
            primary_subtag = tag.strip().split("-")[0].lower()
            weighted.append((primary_subtag, quality))

        weighted.sort(key=lambda item: item[1], reverse=True)
        supported = {member.value for member in LanguageCode}
        for primary_subtag, _quality in weighted:
            if primary_subtag in supported:
                return LanguageCode(primary_subtag)

        return LanguageCode.EN
