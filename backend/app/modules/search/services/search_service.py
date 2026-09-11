"""
Structured (pre-AI) provider search (DIR-001, Decision 4,
`Plan_S06_DIR-001.md`).

`SearchService` depends on `ProviderService` via constructor injection --
the identical, now-established cross-module shape ADR-014/ADR-016,
VER-001 Decision 9, and VER-002 Decision 7 already use -- a new,
one-directional `search -> provider` edge, read-only, cycle-free
(`provider` gains zero imports from `search`). `search` never imports a
`provider`-module repository directly (`02_ARCHITECTURE.md`: "Module ->
Another Module's Repository" is "Not Allowed") -- every provider-owned
read (the geospatial/category/discoverability query, category labels,
primary photo urls, the distinct-label picker query) goes through
`ProviderService`.

`search_providers_ranked`'s result order is merit-ranked (MAT-001,
Decision 1, `Plan_S08_MAT-001.md`) -- reads the five `RANKING_*`
`Settings` values and passes them through to `ProviderService.
search_nearby`. `search_providers` (DIR-001's own `GET /search/
providers`) calls it and discards the returned `scores_by_id`:
`SearchResultProviderResponse` exposes no raw `match_score` field to any
caller. `SearchRequestService._run_automated_match` (AI-002/MAT-001)
calls the same `search_providers_ranked` method directly -- the single
shared entry point, not a second, divergent ranking implementation
(AC2).
"""

import uuid

from app.core.config import settings
from app.core.exceptions import InvalidSearchRadiusError
from app.modules.provider.models import Provider
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.schemas import (
    CategoryOptionResponse,
    SearchResultProviderResponse,
)

_METERS_PER_KM = 1000


class SearchService:
    """Orchestrates `GET /search/providers` and `GET /search/categories`."""

    def __init__(self, provider_service: ProviderService) -> None:
        self.provider_service = provider_service

    async def search_providers_ranked(
        self,
        *,
        category: str | None,
        latitude: float,
        longitude: float,
        radius_km: float,
        page: int,
        page_size: int,
    ) -> tuple[list[Provider], dict[uuid.UUID, float], int, dict[uuid.UUID, float]]:
        """
        Runs the shared, merit-ranked category + geospatial-radius +
        discoverability search (AC2/AC3/AC4; MAT-001, Decision 1,
        `Plan_S08_MAT-001.md`) and returns the raw `(providers,
        distances_by_id, total_items, scores_by_id)` tuple, before any
        response shaping. Reads the five `RANKING_*` `Settings` values
        itself and passes them through to `ProviderService.search_nearby`
        -- the single shared entry point both `search_providers` (DIR-
        001's own `GET /search/providers`) and `SearchRequestService.
        _run_automated_match` (AI-002/MAT-001) call, so neither builds a
        second, divergent ranking implementation (AC2).

        Raises `InvalidSearchRadiusError` (422) if `radius_km` is
        outside `(0, settings.SEARCH_MAX_RADIUS_KM]`, before any
        repository query runs.
        """
        self._validate_radius(radius_km)
        radius_meters = radius_km * _METERS_PER_KM
        limit = page_size
        offset = (page - 1) * page_size

        return await self.provider_service.search_nearby(
            category=category,
            origin_lat=latitude,
            origin_lng=longitude,
            radius_meters=radius_meters,
            limit=limit,
            offset=offset,
            weight_proximity=settings.RANKING_WEIGHT_PROXIMITY,
            weight_rating=settings.RANKING_WEIGHT_RATING,
            weight_review_volume=settings.RANKING_WEIGHT_REVIEW_VOLUME,
            neutral_average_rating=settings.RANKING_NEUTRAL_AVERAGE_RATING,
            review_volume_cap=settings.RANKING_REVIEW_VOLUME_CAP,
        )

    async def search_providers(
        self,
        *,
        category: str | None,
        latitude: float,
        longitude: float,
        radius_km: float,
        page: int,
        page_size: int,
    ) -> tuple[list[SearchResultProviderResponse], int]:
        """
        Runs `search_providers_ranked` and shapes each result for the
        response payload -- category label lookup and primary-photo
        enrichment, both via `ProviderService` (Decision 4). Discards the
        returned `scores_by_id`: `SearchResultProviderResponse` exposes
        no raw `match_score` field to any caller (MAT-001, Decision 1).
        """
        (
            providers,
            distances_by_id,
            total_items,
            _scores_by_id,
        ) = await self.search_providers_ranked(
            category=category,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            page=page,
            page_size=page_size,
        )

        provider_ids = [provider.id for provider in providers]
        photo_urls_by_id = await self.provider_service.get_primary_photo_urls(
            provider_ids
        )
        category_labels_by_id = (
            await self.provider_service.get_category_labels_by_provider_id(provider_ids)
        )

        results = [
            SearchResultProviderResponse(
                id=provider.id,
                display_name=provider.display_name,
                slug=provider.slug,
                provider_type=provider.provider_type,
                category_labels=category_labels_by_id.get(provider.id, []),
                primary_photo_url=photo_urls_by_id.get(provider.id),
                average_rating=provider.average_rating,
                review_count=provider.review_count,
                distance_meters=distances_by_id[provider.id],
                is_claimed=provider.is_claimed,
            )
            for provider in providers
        ]
        return results, total_items

    async def list_categories(self) -> list[CategoryOptionResponse]:
        """Backs `GET /search/categories` (Decision 1)."""
        labels = await self.provider_service.list_distinct_category_labels()
        return [CategoryOptionResponse(label=label) for label in labels]

    @staticmethod
    def _validate_radius(radius_km: float) -> None:
        if radius_km <= 0 or radius_km > settings.SEARCH_MAX_RADIUS_KM:
            raise InvalidSearchRadiusError()
