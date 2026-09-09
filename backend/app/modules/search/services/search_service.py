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
"""

from app.core.config import settings
from app.core.exceptions import InvalidSearchRadiusError
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
        Runs the structured category + geospatial-radius +
        discoverability search (AC2/AC3/AC4) and shapes each result for
        the response payload -- category label lookup and primary-photo
        enrichment, both via `ProviderService` (Decision 4).

        Raises `InvalidSearchRadiusError` (422) if `radius_km` is
        outside `(0, settings.SEARCH_MAX_RADIUS_KM]`, before any
        repository query runs.
        """
        self._validate_radius(radius_km)
        radius_meters = radius_km * _METERS_PER_KM
        limit = page_size
        offset = (page - 1) * page_size

        providers, distances_by_id, total_items = (
            await self.provider_service.search_nearby(
                category=category,
                origin_lat=latitude,
                origin_lng=longitude,
                radius_meters=radius_meters,
                limit=limit,
                offset=offset,
            )
        )

        provider_ids = [provider.id for provider in providers]
        photo_urls_by_id = await self.provider_service.get_primary_photo_urls(
            provider_ids
        )

        results = []
        for provider in providers:
            category_label_rows = await self.provider_service.get_category_labels(
                provider.id
            )
            results.append(
                SearchResultProviderResponse(
                    id=provider.id,
                    display_name=provider.display_name,
                    slug=provider.slug,
                    provider_type=provider.provider_type,
                    category_labels=[row.label for row in category_label_rows],
                    primary_photo_url=photo_urls_by_id.get(provider.id),
                    average_rating=provider.average_rating,
                    review_count=provider.review_count,
                    distance_meters=distances_by_id[provider.id],
                )
            )
        return results, total_items

    async def list_categories(self) -> list[CategoryOptionResponse]:
        """Backs `GET /search/categories` (Decision 1)."""
        labels = await self.provider_service.list_distinct_category_labels()
        return [CategoryOptionResponse(label=label) for label in labels]

    @staticmethod
    def _validate_radius(radius_km: float) -> None:
        if radius_km <= 0 or radius_km > settings.SEARCH_MAX_RADIUS_KM:
            raise InvalidSearchRadiusError()
