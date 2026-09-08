"""
Provider creation and self-service lookup (PRO-001).

`create_provider` takes `RoleAssignmentService` (from `identity`) as a
constructor dependency and calls it to grant `ROLE_PROVIDER` on the same
session as the `providers`/subtype-profile rows it just created -- all
flush only, so the endpoint's single `await db.commit()` remains the
only transaction boundary (Decision 1, `Plan_S04_PRO-001.md`). This is
the only cross-module dependency `ProviderService` has: it depends on
`identity`'s service, never on `RoleRepository`/`UserRole` directly, per
`02_ARCHITECTURE.md`'s "modules communicate through services only" rule.
"""

import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import ProviderAlreadyExistsError
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    BusinessProfile,
    FreelancerProfile,
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.schemas import CreateProviderRequest

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")
_SLUG_SUFFIX_BYTES = 3  # -> 6 hex characters
_MAX_SLUG_GENERATION_ATTEMPTS = 5
# Reserve room for the "-" separator plus the random suffix within
# `providers.slug`'s VARCHAR(220) limit.
_MAX_SLUG_BASE_LENGTH = 220 - (_SLUG_SUFFIX_BYTES * 2) - 1


def _slugify(display_name: str) -> str:
    """
    Lowercases `display_name` and collapses every run of non-
    alphanumeric characters into a single hyphen, trimming leading/
    trailing hyphens. Falls back to `"provider"` for a display name with
    no alphanumeric characters at all (Decision 6, `Plan_S04_PRO-001.md`).
    """
    slug = _SLUG_INVALID_CHARS.sub("-", display_name.lower()).strip("-")
    return slug[:_MAX_SLUG_BASE_LENGTH] or "provider"


class ProviderService:
    """Orchestrates Provider creation and the caller's own-listing lookup."""

    def __init__(
        self,
        provider_repository: ProviderRepository,
        business_profile_repository: BusinessProfileRepository,
        freelancer_profile_repository: FreelancerProfileRepository,
        role_assignment_service: RoleAssignmentService,
    ) -> None:
        self.provider_repository = provider_repository
        self.business_profile_repository = business_profile_repository
        self.freelancer_profile_repository = freelancer_profile_repository
        self.role_assignment_service = role_assignment_service

    async def get_my_provider(self, user_id: uuid.UUID) -> Provider | None:
        """
        Thin wrapper over `get_by_user_id` (Decision 9,
        `Plan_S04_PRO-001.md`) -- unlike `CustomerService`, this is
        deliberately not get-or-create: a missing Provider is a
        legitimate, expected state (the caller simply hasn't onboarded
        yet), not a backfill case.
        """
        return await self.provider_repository.get_by_user_id(user_id)

    async def get_subtype_profiles(
        self, provider: Provider
    ) -> tuple[BusinessProfile | None, FreelancerProfile | None]:
        """
        Fetches whichever subtype profile matches `provider.provider_type`
        -- used by the API layer to build the nested response payload for
        both `GET` and `POST /providers/me`.
        """
        if provider.provider_type == ProviderType.BUSINESS:
            business_profile = (
                await self.business_profile_repository.get_by_provider_id(provider.id)
            )
            return business_profile, None

        freelancer_profile = (
            await self.freelancer_profile_repository.get_by_provider_id(provider.id)
        )
        return None, freelancer_profile

    async def create_provider(
        self, user_id: uuid.UUID, *, payload: CreateProviderRequest
    ) -> Provider:
        """
        Creates a Provider plus its matching subtype profile, and grants
        `ROLE_PROVIDER` (Decision 1) -- all on the same session, flush
        only.

        (a) One-Provider-per-Account (AC8) and type immutability (AC10,
            Decision 3): rejects outright if the caller already has a
            Provider, regardless of the newly-requested `provider_type`.
        (b) Generates a unique `slug` (Decision 6).
        (c) Hardcodes `listing_source=self_registered`, `is_claimed=True`,
            `claimed_at=now()`, `verification_status=pending`,
            `is_discoverable=False` (AC7/AC10, Decision 5) -- no request
            field can influence either default.
        (d) Creates the matching `business_profiles`/`freelancer_profiles`
            row.
        (e) Grants `ROLE_PROVIDER` via `RoleAssignmentService`.
        """
        existing = await self.provider_repository.get_by_user_id(user_id)
        if existing is not None:
            raise ProviderAlreadyExistsError()

        slug = await self._generate_unique_slug(payload.display_name)
        country_code = (
            payload.business_details.country_code
            if payload.business_details is not None
            else payload.freelancer_details.country_code  # type: ignore[union-attr]
        )

        provider = await self.provider_repository.create(
            {
                "user_id": user_id,
                "provider_type": payload.provider_type,
                "display_name": payload.display_name,
                "slug": slug,
                "description": payload.description,
                "phone_country_code": payload.phone_country_code,
                "phone_number": payload.phone_number,
                "whatsapp_number": payload.whatsapp_number,
                "category_label": payload.category_label,
                "listing_source": ListingSource.SELF_REGISTERED,
                "is_claimed": True,
                "claimed_at": datetime.now(UTC),
                "verification_status": VerificationStatus.PENDING,
                "is_discoverable": False,
                "review_count": 0,
                "country_code": country_code,
            }
        )

        if payload.provider_type == ProviderType.BUSINESS:
            # enforced by CreateProviderRequest's schema validator
            assert payload.business_details is not None
            await self.business_profile_repository.create(
                self._business_profile_fields(provider.id, payload)
            )
        else:
            # enforced by CreateProviderRequest's schema validator
            assert payload.freelancer_details is not None
            await self.freelancer_profile_repository.create(
                self._freelancer_profile_fields(provider.id, payload)
            )

        await self.role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)

        return provider

    @staticmethod
    def _business_profile_fields(
        provider_id: uuid.UUID, payload: CreateProviderRequest
    ) -> dict[str, Any]:
        details = payload.business_details
        assert details is not None
        return {
            "provider_id": provider_id,
            "trade_license_number": details.trade_license_number,
            "address_line": details.address_line,
            "city": details.city,
            "region": details.region,
            "latitude": details.latitude,
            "longitude": details.longitude,
            "operating_hours": (
                {
                    day: (entry.model_dump() if entry is not None else None)
                    for day, entry in details.operating_hours.items()
                }
                if details.operating_hours is not None
                else None
            ),
            "delivery_radius_meters": details.delivery_radius_meters,
        }

    @staticmethod
    def _freelancer_profile_fields(
        provider_id: uuid.UUID, payload: CreateProviderRequest
    ) -> dict[str, Any]:
        details = payload.freelancer_details
        assert details is not None
        return {
            "provider_id": provider_id,
            "base_latitude": details.base_latitude,
            "base_longitude": details.base_longitude,
            "service_radius_meters": details.service_radius_meters,
            "skills": details.skills,
            "years_experience": details.years_experience,
        }

    async def _generate_unique_slug(self, display_name: str) -> str:
        """
        Server-generated: a slugified `display_name` plus a short random
        suffix, with a small bounded retry loop on a uniqueness collision
        (Decision 6, `Plan_S04_PRO-001.md`). Never a client-supplied
        request field.
        """
        base = _slugify(display_name)
        for _ in range(_MAX_SLUG_GENERATION_ATTEMPTS):
            candidate = f"{base}-{secrets.token_hex(_SLUG_SUFFIX_BYTES)}"
            if await self.provider_repository.get_by_slug(candidate) is None:
                return candidate
        raise RuntimeError(
            "Could not generate a unique provider slug after "
            f"{_MAX_SLUG_GENERATION_ATTEMPTS} attempts."
        )
