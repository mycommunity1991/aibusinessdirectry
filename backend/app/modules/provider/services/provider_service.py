"""
Provider creation, self-service lookup, and storefront basic-info
updates (PRO-001/PRO-002).

`create_provider` takes `RoleAssignmentService` (from `identity`) as a
constructor dependency and calls it to grant `ROLE_PROVIDER` on the same
session as the `providers`/subtype-profile rows it just created -- all
flush only, so the endpoint's single `await db.commit()` remains the
only transaction boundary (Decision 1, `Plan_S04_PRO-001.md`). This is
the only cross-module dependency `ProviderService` has: it depends on
`identity`'s service, never on `RoleRepository`/`UserRole` directly, per
`02_ARCHITECTURE.md`'s "modules communicate through services only" rule.

`update_basic_info` (PRO-002) is `PATCH /providers/me`'s handler --
partial update (`exclude_unset`) of basic info, an optional
`category_labels` replace (Decision 1, `Plan_S04_PRO-002.md`), and an
optional subtype-details partial update, rejected (400) if the payload's
details object doesn't match the provider's actual `provider_type`
(Decision 8). Neither this nor `create_provider` ever reads or writes
`verification_status`/`is_discoverable` (AC6) -- VER-001 hasn't shipped.
"""

import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import (
    InvalidCategoryLabelsError,
    ProviderAlreadyExistsError,
    ProviderNotFoundError,
    SubtypeDetailsMismatchError,
)
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    BusinessProfile,
    FreelancerProfile,
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.portfolio_repository import PortfolioRepository
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.provider_search_repository import (
    ProviderSearchRepository,
)
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.schemas import CreateProviderRequest

_MAX_CATEGORY_LABELS = 5

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
        provider_category_label_repository: ProviderCategoryLabelRepository,
        service_area_repository: ServiceAreaRepository,
        role_assignment_service: RoleAssignmentService,
        provider_search_repository: ProviderSearchRepository,
        portfolio_repository: PortfolioRepository,
    ) -> None:
        self.provider_repository = provider_repository
        self.business_profile_repository = business_profile_repository
        self.freelancer_profile_repository = freelancer_profile_repository
        self.provider_category_label_repository = provider_category_label_repository
        self.service_area_repository = service_area_repository
        self.role_assignment_service = role_assignment_service
        self.provider_search_repository = provider_search_repository
        self.portfolio_repository = portfolio_repository

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

    async def get_category_labels(
        self, provider_id: uuid.UUID
    ) -> list[ProviderCategoryLabel]:
        """Fetches a provider's current category labels -- used by the
        API layer to build `ProviderResponse.category_labels`."""
        return list(
            await self.provider_category_label_repository.list_for_provider(provider_id)
        )

    async def get_category_labels_by_provider_id(
        self, provider_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[str]]:
        """
        Batch-resolves each provider's category label strings in one
        query (DIR-001, `Plan_S06_DIR-001.md`) -- `search`'s own
        `SearchService` depends on this method, never on
        `ProviderCategoryLabelRepository` directly (Decision 4), mirroring
        `get_primary_photo_urls`'s identical batching pattern to avoid an
        N+1 query per search result.
        """
        labels = await self.provider_category_label_repository.list_for_provider_ids(
            provider_ids
        )
        labels_by_provider_id: dict[uuid.UUID, list[str]] = {
            provider_id: [] for provider_id in provider_ids
        }
        for label in labels:
            labels_by_provider_id[label.provider_id].append(label.label)
        return labels_by_provider_id

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Provider]:
        """
        Thin pass-through to `ProviderRepository.list_by_ids` (VER-002,
        Decision 9, `Plan_S05_VER-002.md`) -- `verification`'s new
        `AdminVerificationService` depends on `ProviderService`, never on
        `ProviderRepository` directly, per `02_ARCHITECTURE.md`'s
        "modules communicate through services only" rule; the actual
        one-query `WHERE id IN (...)` batch fetch lives in the
        repository.
        """
        return await self.provider_repository.list_by_ids(ids)

    async def search_nearby(
        self,
        *,
        category: str | None,
        origin_lat: float,
        origin_lng: float,
        radius_meters: float,
        limit: int,
        offset: int,
        weight_proximity: float,
        weight_rating: float,
        weight_review_volume: float,
        neutral_average_rating: float,
        review_volume_cap: int,
    ) -> tuple[list[Provider], dict[uuid.UUID, float], int, dict[uuid.UUID, float]]:
        """
        Thin pass-through to `ProviderSearchRepository.search_nearby`
        (DIR-001, Decision 4, `Plan_S06_DIR-001.md`; extended with
        MAT-001's five ranking parameters, Decision 1,
        `Plan_S08_MAT-001.md`) -- `search`'s own `SearchService` depends
        on this method, never on `ProviderSearchRepository` directly, per
        `02_ARCHITECTURE.md`'s "modules communicate through services
        only" rule. This method resolves no `Settings` values itself
        (mirrors the repository's own posture) -- every ranking
        parameter is caller-supplied.

        Hydrates the repository's ordered provider ids into full
        `Provider` rows via `list_by_ids` (VER-002 precedent), while
        preserving the repository's own `match_score DESC, id ASC` order
        -- `list_by_ids`'s own `WHERE id IN (...)` query makes no
        row-order guarantee, so the ordering is reconstructed here from
        the repository's already-ordered id list, not re-derived.
        """
        (
            ordered_ids,
            distances_by_id,
            total_items,
            scores_by_id,
        ) = await self.provider_search_repository.search_nearby(
            category=category,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            radius_meters=radius_meters,
            limit=limit,
            offset=offset,
            weight_proximity=weight_proximity,
            weight_rating=weight_rating,
            weight_review_volume=weight_review_volume,
            neutral_average_rating=neutral_average_rating,
            review_volume_cap=review_volume_cap,
        )
        providers_by_id = {
            provider.id: provider
            for provider in await self.provider_repository.list_by_ids(ordered_ids)
        }
        ordered_providers = [
            providers_by_id[provider_id]
            for provider_id in ordered_ids
            if provider_id in providers_by_id
        ]
        return ordered_providers, distances_by_id, total_items, scores_by_id

    async def list_distinct_category_labels(self) -> list[str]:
        """
        Thin pass-through to `ProviderCategoryLabelRepository.list_
        distinct_labels_for_discoverable_providers` (DIR-001, Decision
        1, `Plan_S06_DIR-001.md`) -- backs `GET /search/categories`.
        """
        repository = self.provider_category_label_repository
        return await repository.list_distinct_labels_for_discoverable_providers()

    async def get_primary_photo_urls(
        self, provider_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str | None]:
        """
        Batch-resolves each provider's primary (first by `sort_order`)
        active portfolio photo URL, or `None` if it has none (DIR-001,
        Backend Proposed Changes item 4, `Plan_S06_DIR-001.md`) --
        `search`'s own `SearchService` depends on this method, never on
        `PortfolioRepository` directly, keeping `search`'s only
        cross-module edge the single `search -> provider` edge via
        `ProviderService` (Decision 4).
        """
        photos = await self.portfolio_repository.list_active_for_provider_ids(
            provider_ids
        )
        urls_by_provider_id: dict[uuid.UUID, str | None] = dict.fromkeys(provider_ids)
        for photo in photos:
            if urls_by_provider_id.get(photo.provider_id) is None:
                urls_by_provider_id[photo.provider_id] = photo.media_url
        return urls_by_provider_id

    async def apply_verification_outcome(
        self,
        provider_id: uuid.UUID,
        *,
        verification_status: VerificationStatus,
        is_discoverable: bool,
    ) -> Provider:
        """
        Applies a verification review outcome to the cached `providers.
        verification_status`/`is_discoverable` columns (VER-002,
        Decision 7, `Plan_S05_VER-002.md`) -- the first write path into
        either column since `create_provider`'s creation-time defaults
        (PRO-001). Called by `AdminVerificationService.approve`/
        `.reject` on the same request-scoped session, flush only, so
        this write lands in the same transaction as the caller's
        `verification_records` status update (AC2/AC4).

        Raises `ProviderNotFoundError` defensively -- should not happen
        in practice, since the caller always resolves `provider_id` from
        an already-loaded `VerificationRecord`, but this method never
        silently no-ops on a missing row.
        """
        provider = await self.provider_repository.get_by_id(provider_id)
        if provider is None:
            raise ProviderNotFoundError()

        return await self.provider_repository.update(
            provider,
            {
                "verification_status": verification_status,
                "is_discoverable": is_discoverable,
            },
        )

    async def create_google_seeded_provider(
        self,
        *,
        google_place_id: str,
        display_name: str,
        phone_country_code: str | None,
        phone_number: str | None,
        country_code: str,
        business_details: dict[str, Any],
        category_label: str | None,
    ) -> Provider:
        """
        Creates a Google-seeded-unclaimed Business listing (CLM-001,
        AC1, Decision 2/3/4, `Plan_S06_CLM-001.md`) -- the import
        job's create path (called only when `ProviderRepository.get_by_
        google_place_id` found no existing row for this place).

        Hardcodes `provider_type=BUSINESS` (Decision 3 -- Google Places
        data never fits a Freelancer), `listing_source=
        GOOGLE_SEEDED_UNCLAIMED`, `is_claimed=False`, `user_id=None`,
        `claimed_at=None`, and -- the load-bearing part of Decision 2 --
        `verification_status=APPROVED`/`is_discoverable=True` set
        directly by this write (never through
        `apply_verification_outcome`, since there is no existing row to
        update yet). Never `listing_source=SELF_REGISTERED` under any
        circumstance.

        Also creates the matching `business_profiles` row and a
        `service_areas` row (Decision 4 -- omitting this would silently
        make the listing invisible to DIR-001's actual geospatial search
        query despite `is_discoverable=True`), plus one best-effort
        primary category label if `category_label` is given. Does
        **not** create the matching `verification.verification_records`
        row itself (this module has no dependency on `verification`) --
        the caller (the import script) creates that row, per Decision 2.
        """
        slug = await self._generate_unique_slug(display_name)

        provider = await self.provider_repository.create(
            {
                "user_id": None,
                "provider_type": ProviderType.BUSINESS,
                "display_name": display_name,
                "slug": slug,
                "description": None,
                "phone_country_code": phone_country_code,
                "phone_number": phone_number,
                "whatsapp_number": None,
                "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
                "is_claimed": False,
                "claimed_at": None,
                "google_place_id": google_place_id,
                "verification_status": VerificationStatus.APPROVED,
                "is_discoverable": True,
                "review_count": 0,
                "country_code": country_code,
            }
        )

        await self.business_profile_repository.create(
            {"provider_id": provider.id, **business_details}
        )
        await self.service_area_repository.upsert_for_provider(
            provider.id,
            center_latitude=business_details["latitude"],
            center_longitude=business_details["longitude"],
            radius_meters=business_details.get("delivery_radius_meters") or 0,
        )

        if category_label:
            await self.provider_category_label_repository.replace_all(
                provider.id, [{"label": category_label, "is_primary": True}]
            )

        return provider

    async def backfill_google_seeded_provider(
        self,
        provider: Provider,
        *,
        display_name: str,
        phone_country_code: str | None,
        phone_number: str | None,
        country_code: str,
        business_details: dict[str, Any],
        category_label: str | None,
    ) -> Provider:
        """
        Re-syncs an already-imported Google-seeded listing with freshly-
        fetched Google data (CLM-001, AC7, Decision 6, `Plan_S06_CLM-
        001.md`'s field-write policy) -- the import job's update path
        (called when `get_by_google_place_id` found an existing row).

        **If `provider.is_claimed` is `False`:** fully overwrites every
        mapped field with the fresh data -- safe, since no owner exists
        yet whose edits could be lost.

        **If `provider.is_claimed` is `True`:** writes **only** fields
        whose current stored value is `NULL`/empty-string, leaving any
        field that already holds a non-empty value untouched regardless
        of what the fresh Google data says (AC7's literal "imported
        data only backfills genuinely empty fields") -- this is the
        one-and-only place in this codebase that ever writes to a
        claimed listing's basic-info fields without the owner having
        asked for it, so the empty-only guard is the entire safety net.

        Never touches `is_claimed`/`user_id`/`claimed_at`/
        `verification_status`/`is_discoverable`/`google_place_id` --
        this method's sole concern is the Google-sourced content
        fields.
        """
        business_profile = await self.business_profile_repository.get_by_provider_id(
            provider.id
        )
        if business_profile is None:
            raise ProviderNotFoundError()

        full_overwrite = not provider.is_claimed

        provider_fields = {
            "display_name": display_name,
            "phone_country_code": phone_country_code,
            "phone_number": phone_number,
            "country_code": country_code,
        }
        applicable_provider_fields = self._select_writable_fields(
            provider, provider_fields, full_overwrite=full_overwrite
        )
        if applicable_provider_fields:
            provider = await self.provider_repository.update(
                provider, applicable_provider_fields
            )

        applicable_business_fields = self._select_writable_fields(
            business_profile, business_details, full_overwrite=full_overwrite
        )
        if applicable_business_fields:
            business_profile = await self.business_profile_repository.update(
                business_profile, applicable_business_fields
            )

        if full_overwrite:
            await self.service_area_repository.upsert_for_provider(
                provider.id,
                center_latitude=business_profile.latitude,
                center_longitude=business_profile.longitude,
                radius_meters=business_profile.delivery_radius_meters or 0,
            )

        if category_label:
            label_repository = self.provider_category_label_repository
            existing_labels = await label_repository.list_for_provider(provider.id)
            if full_overwrite or not existing_labels:
                await self.provider_category_label_repository.replace_all(
                    provider.id, [{"label": category_label, "is_primary": True}]
                )

        return provider

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or (isinstance(value, str) and value.strip() == "")

    @classmethod
    def _select_writable_fields(
        cls,
        current_obj: Any,
        fresh_values: dict[str, Any],
        *,
        full_overwrite: bool,
    ) -> dict[str, Any]:
        """
        AC7's field-write policy, applied generically to any (current
        row, fresh values) pair: with `full_overwrite=True`, every
        key in `fresh_values` is applied unconditionally; otherwise only
        keys whose *current* value on `current_obj` is empty (Decision
        6's `_is_empty`) are applied -- an already-non-empty field is
        never overwritten, regardless of what the fresh value is.
        """
        if full_overwrite:
            return dict(fresh_values)

        return {
            field: value
            for field, value in fresh_values.items()
            if cls._is_empty(getattr(current_obj, field, None))
        }

    async def search_unclaimed_listings(
        self, *, query: str, limit: int, offset: int
    ) -> tuple[list[Provider], int]:
        """
        Thin pass-through to `ProviderRepository.search_unclaimed`
        (CLM-001, AC3, Decision 5, `Plan_S06_CLM-001.md`) -- `provider`'s
        own `ClaimService` depends on this method, never on
        `ProviderRepository` directly, mirroring `search_nearby`'s
        existing shape.
        """
        return await self.provider_repository.search_unclaimed(
            query=query, limit=limit, offset=offset
        )

    async def get_business_profiles_by_provider_id(
        self, provider_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, BusinessProfile]:
        """
        Batch-resolves each provider's `business_profiles` row in one
        query (CLM-001, AC3) -- backs `GET /claims/search`'s
        `address_line`/`city` fields without an N+1 query per result.
        """
        profiles = await self.business_profile_repository.list_by_provider_ids(
            provider_ids
        )
        return {profile.provider_id: profile for profile in profiles}

    async def get_locations_by_provider_id(
        self, provider_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[float, float]]:
        """
        Batch-resolves each provider's `(latitude, longitude)` in one
        query, from `service_areas.center_latitude/center_longitude`
        (AI-002, `Plan_S07_AI-002.md`, Decision 6) -- deliberately not
        `business_profiles`/`freelancer_profiles`: `service_areas` is the
        exact location `ProviderSearchRepository.search_nearby`'s
        geospatial query itself matches/ranks against, so recomputing
        `distance_meters` against it (for `GET /search-requests/{id}`)
        stays consistent with what the automated matcher actually used,
        for both automated- and manually-matched providers alike. A
        provider with no `service_areas` row yet (should not occur for a
        real, discoverable provider) is simply absent from the returned
        mapping -- an honest "location unknown", never a fabricated
        `(0, 0)`.
        """
        service_areas = await self.service_area_repository.list_by_provider_ids(
            provider_ids
        )
        return {
            area.provider_id: (area.center_latitude, area.center_longitude)
            for area in service_areas
        }

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
                "listing_source": ListingSource.SELF_REGISTERED,
                "is_claimed": True,
                "claimed_at": datetime.now(UTC),
                "verification_status": VerificationStatus.PENDING,
                "is_discoverable": False,
                "review_count": 0,
                "country_code": country_code,
            }
        )

        # PRO-002, Decision 1: the single `category_label` string
        # submitted at onboarding becomes the provider's first (and
        # primary) `provider_category_labels` row.
        await self.provider_category_label_repository.replace_all(
            provider.id, [{"label": payload.category_label, "is_primary": True}]
        )

        if payload.provider_type == ProviderType.BUSINESS:
            # enforced by CreateProviderRequest's schema validator
            assert payload.business_details is not None
            await self.business_profile_repository.create(
                self._business_profile_fields(provider.id, payload)
            )
            await self.service_area_repository.upsert_for_provider(
                provider.id,
                center_latitude=payload.business_details.latitude,
                center_longitude=payload.business_details.longitude,
                radius_meters=payload.business_details.delivery_radius_meters or 0,
            )
        else:
            # enforced by CreateProviderRequest's schema validator
            assert payload.freelancer_details is not None
            await self.freelancer_profile_repository.create(
                self._freelancer_profile_fields(provider.id, payload)
            )
            await self.service_area_repository.upsert_for_provider(
                provider.id,
                center_latitude=payload.freelancer_details.base_latitude,
                center_longitude=payload.freelancer_details.base_longitude,
                radius_meters=payload.freelancer_details.service_radius_meters,
            )

        await self.role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)

        return provider

    async def update_basic_info(
        self, user_id: uuid.UUID, *, fields: dict[str, Any]
    ) -> Provider:
        """
        `PATCH /providers/me`'s handler (PRO-002, AC5). `fields` is
        already `exclude_unset`-filtered at the API layer -- only keys
        actually present in the request body are applied here.

        Never touches `verification_status`/`is_discoverable` (AC6) --
        those are not accepted fields on `UpdateProviderRequest` at all.
        `provider_type` is likewise never accepted, so it remains
        immutable (PRO-001, Decision 3).
        """
        provider = await self.provider_repository.get_by_user_id(user_id)
        if provider is None:
            raise ProviderNotFoundError()

        basic_field_names = {
            "display_name",
            "phone_country_code",
            "phone_number",
            "whatsapp_number",
            "description",
        }
        basic_fields = {k: v for k, v in fields.items() if k in basic_field_names}
        if basic_fields:
            provider = await self.provider_repository.update(provider, basic_fields)

        category_labels = fields.get("category_labels")
        if category_labels is not None:
            await self._replace_category_labels(provider.id, category_labels)

        business_details = fields.get("business_details")
        if business_details is not None:
            if provider.provider_type != ProviderType.BUSINESS:
                raise SubtypeDetailsMismatchError()
            await self._apply_business_details_update(provider, business_details)

        freelancer_details = fields.get("freelancer_details")
        if freelancer_details is not None:
            if provider.provider_type != ProviderType.FREELANCER:
                raise SubtypeDetailsMismatchError()
            await self._apply_freelancer_details_update(provider, freelancer_details)

        return provider

    async def _replace_category_labels(
        self, provider_id: uuid.UUID, category_labels: list[dict[str, Any]]
    ) -> None:
        """
        Validates the exactly-one-primary rule and the 5-label cap
        (AC4, Decision 1, `Plan_S04_PRO-002.md`) before replacing the
        provider's entire label set transactionally, in one flush.
        """
        if not category_labels or len(category_labels) > _MAX_CATEGORY_LABELS:
            raise InvalidCategoryLabelsError()

        primary_count = sum(1 for label in category_labels if label.get("is_primary"))
        if primary_count != 1:
            raise InvalidCategoryLabelsError()

        await self.provider_category_label_repository.replace_all(
            provider_id, category_labels
        )

    async def _apply_business_details_update(
        self, provider: Provider, details: dict[str, Any]
    ) -> None:
        business_profile = await self.business_profile_repository.get_by_provider_id(
            provider.id
        )
        if business_profile is None:
            raise ProviderNotFoundError()

        # `details` is already plain-dict-shaped (the API layer builds
        # `fields` via `payload.model_dump(exclude_unset=True)`, which
        # recursively converts nested `OperatingHoursEntry` models into
        # plain dicts matching `business_profiles.operating_hours`'s
        # JSONB shape directly) -- no further conversion needed here.
        updated = await self.business_profile_repository.update(
            business_profile, details
        )

        # Decision, item 1 (`Plan_S04_PRO-002.md`): `service_areas` is
        # derived data, kept in sync whenever the subtype profile's
        # location/radius fields are edited.
        await self.service_area_repository.upsert_for_provider(
            provider.id,
            center_latitude=updated.latitude,
            center_longitude=updated.longitude,
            radius_meters=updated.delivery_radius_meters or 0,
        )

    async def _apply_freelancer_details_update(
        self, provider: Provider, details: dict[str, Any]
    ) -> None:
        freelancer_profile = (
            await self.freelancer_profile_repository.get_by_provider_id(provider.id)
        )
        if freelancer_profile is None:
            raise ProviderNotFoundError()

        updated = await self.freelancer_profile_repository.update(
            freelancer_profile, details
        )

        await self.service_area_repository.upsert_for_provider(
            provider.id,
            center_latitude=updated.base_latitude,
            center_longitude=updated.base_longitude,
            radius_meters=updated.service_radius_meters,
        )

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
