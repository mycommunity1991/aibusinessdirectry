"""
Unit tests for `SearchService` (DIR-001, `Plan_S06_DIR-001.md`).

`ProviderService` is mocked so these tests isolate `SearchService`'s own
response-shaping/orchestration logic (mirrors `test_provider_service.py`'s
mock-based pattern) -- see `test_search_endpoints.py` for the full HTTP
round trip against a real database.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InvalidSearchRadiusError
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.search.services.search_service import SearchService

_ORIGIN_LAT = 25.2048
_ORIGIN_LNG = 55.2708


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _provider(**overrides: object) -> Provider:
    payload: dict[str, object] = {
        "id": uuid.uuid4(),
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "slug": "jane-the-plumber-abc123",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "average_rating": None,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    return Provider(**payload)


@pytest.fixture
def mock_provider_service() -> MagicMock:
    service = MagicMock()
    service.search_nearby = AsyncMock(return_value=([], {}, 0))
    service.get_primary_photo_urls = AsyncMock(return_value={})
    service.get_category_labels_by_provider_id = AsyncMock(return_value={})
    service.list_distinct_category_labels = AsyncMock(return_value=[])
    return service


@pytest.fixture
def search_service(mock_provider_service: MagicMock) -> SearchService:
    return SearchService(provider_service=mock_provider_service)


class TestListCategories:
    @pytest.mark.anyio
    async def test_returns_the_distinct_labels_as_options(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        mock_provider_service.list_distinct_category_labels.return_value = [
            "Plumbing",
            "Electrician",
        ]

        result = await search_service.list_categories()

        assert [option.label for option in result] == ["Plumbing", "Electrician"]


class TestSearchProvidersRatingShape:
    """Decision 2: the raw, honestly-nullable `average_rating`/
    `review_count` fields, never a synthesized `0.0` default."""

    @pytest.mark.anyio
    async def test_a_provider_with_no_reviews_returns_null_average_rating(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        """The only state achievable through any real, currently-shipped
        code path (no Review domain exists yet)."""
        provider = _provider(average_rating=None, review_count=0)
        mock_provider_service.search_nearby.return_value = (
            [provider],
            {provider.id: 1234.5},
            1,
        )
        mock_provider_service.get_category_labels_by_provider_id.return_value = {
            provider.id: ["Plumbing"]
        }

        results, total_items = await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=1,
            page_size=20,
        )

        assert total_items == 1
        assert len(results) == 1
        assert results[0].average_rating is None
        assert results[0].review_count == 0

    @pytest.mark.anyio
    async def test_a_provider_with_fixture_injected_reviews_returns_the_raw_values(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        """Fixture-injected `average_rating`/`review_count` (Decision 2's
        "proving the shape is correct" case) -- the raw values pass
        through unchanged; rendering `"4.8 (3 reviews)"` is a mobile
        concern, not this backend's."""
        provider = _provider(average_rating=Decimal("4.80"), review_count=3)
        mock_provider_service.search_nearby.return_value = (
            [provider],
            {provider.id: 500.0},
            1,
        )

        results, _total_items = await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=1,
            page_size=20,
        )

        assert results[0].average_rating == Decimal("4.80")
        assert results[0].review_count == 3


class TestSearchProvidersResponseShaping:
    @pytest.mark.anyio
    async def test_enriches_with_primary_photo_url_and_category_labels(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        provider = _provider()
        mock_provider_service.search_nearby.return_value = (
            [provider],
            {provider.id: 42.0},
            1,
        )
        mock_provider_service.get_primary_photo_urls.return_value = {
            provider.id: "/media/portfolios/abc/photo.jpg"
        }
        mock_provider_service.get_category_labels_by_provider_id.return_value = {
            provider.id: ["Plumbing", "AC Repair"]
        }

        results, _total_items = await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=1,
            page_size=20,
        )

        assert results[0].primary_photo_url == "/media/portfolios/abc/photo.jpg"
        assert results[0].category_labels == ["Plumbing", "AC Repair"]
        assert results[0].distance_meters == 42.0
        assert results[0].id == provider.id
        assert results[0].display_name == provider.display_name
        assert results[0].slug == provider.slug

    @pytest.mark.anyio
    async def test_a_provider_with_no_photos_returns_a_null_primary_photo_url(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        provider = _provider()
        mock_provider_service.search_nearby.return_value = (
            [provider],
            {provider.id: 42.0},
            1,
        )
        mock_provider_service.get_primary_photo_urls.return_value = {
            provider.id: None
        }

        results, _total_items = await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=1,
            page_size=20,
        )

        assert results[0].primary_photo_url is None

    @pytest.mark.anyio
    async def test_empty_results_return_an_empty_list_and_zero_total(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        """AC4's backend half: an empty `data`/`total_items: 0` shape."""
        mock_provider_service.search_nearby.return_value = ([], {}, 0)

        results, total_items = await search_service.search_providers(
            category="Plumbing",
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=1,
            page_size=20,
        )

        assert results == []
        assert total_items == 0

    @pytest.mark.anyio
    async def test_converts_radius_km_to_meters_before_calling_provider_service(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=12.5,
            page=1,
            page_size=20,
        )

        _args, kwargs = mock_provider_service.search_nearby.call_args
        assert kwargs["radius_meters"] == 12_500.0

    @pytest.mark.anyio
    async def test_computes_limit_and_offset_from_page_and_page_size(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=10.0,
            page=3,
            page_size=20,
        )

        _args, kwargs = mock_provider_service.search_nearby.call_args
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 40


class TestRadiusValidation:
    @pytest.mark.anyio
    async def test_zero_radius_raises_invalid_search_radius_error(
        self, search_service: SearchService
    ) -> None:
        with pytest.raises(InvalidSearchRadiusError):
            await search_service.search_providers(
                category=None,
                latitude=_ORIGIN_LAT,
                longitude=_ORIGIN_LNG,
                radius_km=0.0,
                page=1,
                page_size=20,
            )

    @pytest.mark.anyio
    async def test_negative_radius_raises_invalid_search_radius_error(
        self, search_service: SearchService
    ) -> None:
        with pytest.raises(InvalidSearchRadiusError):
            await search_service.search_providers(
                category=None,
                latitude=_ORIGIN_LAT,
                longitude=_ORIGIN_LNG,
                radius_km=-5.0,
                page=1,
                page_size=20,
            )

    @pytest.mark.anyio
    async def test_radius_above_the_configured_max_raises_invalid_search_radius_error(
        self, search_service: SearchService
    ) -> None:
        with pytest.raises(InvalidSearchRadiusError):
            await search_service.search_providers(
                category=None,
                latitude=_ORIGIN_LAT,
                longitude=_ORIGIN_LNG,
                radius_km=1000.0,
                page=1,
                page_size=20,
            )

    @pytest.mark.anyio
    async def test_radius_at_exactly_the_configured_max_is_accepted(
        self, search_service: SearchService, mock_provider_service: MagicMock
    ) -> None:
        from app.core.config import settings

        await search_service.search_providers(
            category=None,
            latitude=_ORIGIN_LAT,
            longitude=_ORIGIN_LNG,
            radius_km=settings.SEARCH_MAX_RADIUS_KM,
            page=1,
            page_size=20,
        )

        mock_provider_service.search_nearby.assert_awaited_once()
