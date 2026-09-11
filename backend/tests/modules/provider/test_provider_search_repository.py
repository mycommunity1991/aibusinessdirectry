"""
Integration tests for `ProviderSearchRepository` (DIR-001, Decision 8/9,
`Plan_S06_DIR-001.md`) -- exercised against a real Postgres database
(`tests/conftest.py`'s `db_session` fixture).

Covers:
  * AC2/AC7 (filter precedence, deterministic tie-break) via direct
    fixtures -- one provider failing exactly one of
    category/radius/discoverability, plus a fully-matching one; two
    equally-near providers returned in `id ASC` order regardless of
    insertion order.
  * AC6 (query-plan verification, Decision 9) -- seeds >=1,000
    `service_areas` rows scattered across a wide geographic spread,
    runs `EXPLAIN (FORMAT JSON)` against the repository's own query
    through the same `AsyncSession`, and asserts a real Index Scan/
    Bitmap Index Scan node targeting `idx_service_areas_location` --
    and explicitly asserts the top-level scan of `service_areas` is not
    a `Seq Scan`.
  * MAT-001 AC3/AC8/AC4 (`TestMeritRanking`, `Plan_S08_MAT-001.md`) --
    known rating/distance combinations proving the composite
    `match_score` formula (a farther-but-higher-rated provider outranks
    a closer-but-unrated one), a genuine exact-tie fixture re-anchored
    to `match_score DESC, id ASC`, and a regression fixture proving
    uniform-rating candidates preserve the pre-existing nearest-first
    order.

The GiST index itself is not created by `Base.metadata.create_all()`
(`db_engine`'s fixture setup) -- it is a functional index over an
`earthdistance`-extension function (`ll_to_earth`), created by the real
migration only (`alembic/versions/..._enable_geospatial_extensions_and_
indexes.py`), never modeled as an ORM `Index()` (see `ServiceArea`'s
docstring in `app/modules/provider/models.py`). The `_geospatial_setup`
fixture below recreates the same extension + index directly, mirroring
Decision 9's own "a raw fixture, not a claim real onboardings were
exercised" framing for the >=1,000-row seed.
"""

import json
import random
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    ServiceArea,
    VerificationStatus,
)
from app.modules.provider.repositories.provider_search_repository import (
    _SEARCH_NEARBY_SQL,
    ProviderSearchRepository,
)

_DUBAI_LAT = 25.2048
_DUBAI_LNG = 55.2708
_ONE_KM_METERS = 1_000.0
_FAR_AWAY_LAT = 40.7128  # New York -- thousands of km from Dubai
_FAR_AWAY_LNG = -74.0060


async def _create_user(db_session: AsyncSession) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=f"5{uuid.uuid4().int % 10**8:08d}",
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_provider(db_session: AsyncSession, **overrides: object) -> Provider:
    user = await _create_user(db_session)
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Test Provider",
        "slug": f"test-provider-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "is_active": True,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


async def _add_service_area(
    db_session: AsyncSession,
    provider: Provider,
    *,
    latitude: float = _DUBAI_LAT,
    longitude: float = _DUBAI_LNG,
    radius_meters: int = 5000,
) -> ServiceArea:
    service_area = ServiceArea(
        provider_id=provider.id,
        center_latitude=latitude,
        center_longitude=longitude,
        radius_meters=radius_meters,
    )
    db_session.add(service_area)
    await db_session.commit()
    await db_session.refresh(service_area)
    return service_area


async def _add_category_label(
    db_session: AsyncSession, provider: Provider, label: str, *, is_primary: bool = True
) -> None:
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label=label, is_primary=is_primary
        )
    )
    await db_session.commit()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def repository(db_session: AsyncSession) -> ProviderSearchRepository:
    return ProviderSearchRepository(db_session)


class TestFilterPrecedence:
    """AC2: category, then geospatial radius, then discoverability --
    each fixture below fails exactly one condition."""

    @pytest.mark.anyio
    async def test_matching_all_three_conditions_is_returned(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        provider = await _create_provider(db_session)
        await _add_service_area(db_session, provider)
        await _add_category_label(db_session, provider, "Plumbing")

        ids, distances, total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == [provider.id]
        assert distances[provider.id] == pytest.approx(0.0, abs=1.0)
        assert total == 1

    @pytest.mark.anyio
    async def test_wrong_category_is_excluded_even_when_in_radius_and_discoverable(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        provider = await _create_provider(db_session)
        await _add_service_area(db_session, provider)
        await _add_category_label(db_session, provider, "Electrician")

        ids, _distances, total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == []
        assert total == 0

    @pytest.mark.anyio
    async def test_outside_radius_is_excluded_despite_category_and_discoverable_match(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        provider = await _create_provider(db_session)
        await _add_service_area(
            db_session, provider, latitude=_FAR_AWAY_LAT, longitude=_FAR_AWAY_LNG
        )
        await _add_category_label(db_session, provider, "Plumbing")

        ids, _distances, total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == []
        assert total == 0

    @pytest.mark.anyio
    async def test_not_discoverable_is_excluded_regardless_of_category_and_radius_fit(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """AC2's literal "never appears... regardless of category/
        distance fit" -- a provider matching category and radius
        perfectly, but `is_discoverable=false`, must never appear."""
        provider = await _create_provider(db_session, is_discoverable=False)
        await _add_service_area(db_session, provider)
        await _add_category_label(db_session, provider, "Plumbing")

        ids, _distances, total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == []
        assert total == 0

    @pytest.mark.anyio
    async def test_category_match_is_case_insensitive_exact_not_substring(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """Decision 1: `lower(label) = lower(:category)` -- an exact,
        case-insensitive match. "AC" must never match "AC Repair"."""
        exact_match = await _create_provider(db_session, display_name="Cool Air Co")
        await _add_service_area(db_session, exact_match)
        await _add_category_label(db_session, exact_match, "ac repair")

        substring_only = await _create_provider(db_session, display_name="AC Only")
        await _add_service_area(db_session, substring_only)
        await _add_category_label(db_session, substring_only, "AC Repair Specialist")

        ids, _distances, total, _scores = await repository.search_nearby(
            category="AC Repair",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == [exact_match.id]
        assert total == 1

    @pytest.mark.anyio
    async def test_no_category_filter_browses_across_all_categories(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """Decision 1: `category` is optional -- omitting it (`None`)
        browses across all categories, still filtered by geo +
        discoverability."""
        plumber = await _create_provider(db_session, display_name="Plumber")
        await _add_service_area(db_session, plumber)
        await _add_category_label(db_session, plumber, "Plumbing")

        electrician = await _create_provider(db_session, display_name="Electrician")
        await _add_service_area(db_session, electrician)
        await _add_category_label(db_session, electrician, "Electrician")

        ids, _distances, total, _scores = await repository.search_nearby(
            category=None,
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert set(ids) == {plumber.id, electrician.id}
        assert total == 2


class TestDeterministicTieBreak:
    """AC7: `distance_meters ASC, id ASC` -- two providers at an
    identical distance always come back in `id ASC` order, regardless of
    insertion order."""

    @pytest.mark.anyio
    async def test_equal_distance_providers_are_ordered_by_id_ascending_order_1(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        first = await _create_provider(db_session, display_name="Provider A")
        second = await _create_provider(db_session, display_name="Provider B")
        await _add_service_area(db_session, first)
        await _add_service_area(db_session, second)
        await _add_category_label(db_session, first, "Plumbing")
        await _add_category_label(db_session, second, "Plumbing")

        ids, _distances, _total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == sorted([first.id, second.id])

    @pytest.mark.anyio
    async def test_equal_distance_providers_are_ordered_by_id_ascending_order_2(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """Same scenario, but the *second*-created provider happens to
        sort first by id -- proving the order is driven by `id`, not
        insertion order."""
        providers = [
            await _create_provider(db_session, display_name=f"Provider {i}")
            for i in range(2)
        ]
        # Whichever of the two has the smaller id, insert it *second* --
        # if the result were actually insertion-order-driven, this would
        # produce the opposite of `id ASC`.
        providers_by_id_desc = sorted(providers, key=lambda p: p.id, reverse=True)
        for provider in providers_by_id_desc:
            await _add_service_area(db_session, provider)
            await _add_category_label(db_session, provider, "Plumbing")

        ids, _distances, _total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=10,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert ids == sorted(provider.id for provider in providers)


class TestMeritRanking:
    """AC3/AC8 (MAT-001, Decision 1, `Plan_S08_MAT-001.md`): ranking
    combines proximity with rating and review volume, never distance
    alone -- known rating/distance combinations, computed against the
    default (CTO-confirmed launch) weights (`RANKING_WEIGHT_
    PROXIMITY=0.6`, `RANKING_WEIGHT_RATING=0.3`, `RANKING_WEIGHT_REVIEW_
    VOLUME=0.1`, `RANKING_NEUTRAL_AVERAGE_RATING=3.0`, `RANKING_REVIEW_
    VOLUME_CAP=50`). AC4's tie-break is re-anchored to the new
    `match_score`-based order here too."""

    _RADIUS_METERS = 10 * _ONE_KM_METERS
    _WEIGHTS: dict[str, float | int] = {
        "weight_proximity": 0.6,
        "weight_rating": 0.3,
        "weight_review_volume": 0.1,
        "neutral_average_rating": 3.0,
        "review_volume_cap": 50,
    }

    @staticmethod
    def _expected_score(
        *,
        distance_meters: float,
        radius_meters: float,
        average_rating: float,
        review_count: int,
    ) -> float:
        proximity = 0.6 * (1.0 - (distance_meters / radius_meters))
        rating = 0.3 * (average_rating / 5.0)
        review_volume = 0.1 * (min(review_count, 50) / 50)
        return proximity + rating + review_volume

    @pytest.mark.anyio
    async def test_a_farther_but_higher_rated_provider_outranks_a_closer_unrated_one(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        closer_unrated = await _create_provider(
            db_session,
            display_name="Closer Unrated",
            average_rating=None,
            review_count=0,
        )
        await _add_service_area(db_session, closer_unrated)
        await _add_category_label(db_session, closer_unrated, "Plumbing")

        farther_top_rated = await _create_provider(
            db_session,
            display_name="Farther Top Rated",
            average_rating=Decimal("5.00"),
            review_count=50,
        )
        # ~3.3km north of the search origin -- well within the 10km
        # radius, but genuinely farther than `closer_unrated`.
        await _add_service_area(
            db_session,
            farther_top_rated,
            latitude=_DUBAI_LAT + 0.03,
            longitude=_DUBAI_LNG,
        )
        await _add_category_label(db_session, farther_top_rated, "Plumbing")

        ids, distances, _total, scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=self._RADIUS_METERS,
            limit=10,
            offset=0,
            **self._WEIGHTS,
        )

        # Sanity check: the fixture is genuinely farther, not accidentally tied.
        assert distances[farther_top_rated.id] > distances[closer_unrated.id]

        # AC3/AC8: the higher-rated, more-reviewed provider outranks the
        # merely-closer one under the default launch weights.
        assert ids == [farther_top_rated.id, closer_unrated.id]

        # The returned `match_score` matches the documented formula
        # exactly (not just "some score exists").
        assert scores[closer_unrated.id] == pytest.approx(
            self._expected_score(
                distance_meters=distances[closer_unrated.id],
                radius_meters=self._RADIUS_METERS,
                average_rating=3.0,  # neutral default for `average_rating IS NULL`
                review_count=0,
            )
        )
        assert scores[farther_top_rated.id] == pytest.approx(
            self._expected_score(
                distance_meters=distances[farther_top_rated.id],
                radius_meters=self._RADIUS_METERS,
                average_rating=5.0,
                review_count=50,
            )
        )

    @pytest.mark.anyio
    async def test_equal_rating_and_distance_providers_tie_break_on_id_ascending(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """AC4: two providers with identical `average_rating`/
        `review_count`/distance produce a stable tie-break on `id ASC`
        -- re-anchored to the new `match_score`-based order, not just
        the old `distance_meters`-based one."""
        first = await _create_provider(
            db_session,
            display_name="Provider A",
            average_rating=Decimal("4.50"),
            review_count=10,
        )
        second = await _create_provider(
            db_session,
            display_name="Provider B",
            average_rating=Decimal("4.50"),
            review_count=10,
        )
        await _add_service_area(db_session, first)
        await _add_service_area(db_session, second)
        await _add_category_label(db_session, first, "Plumbing")
        await _add_category_label(db_session, second, "Plumbing")

        ids, _distances, _total, scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=self._RADIUS_METERS,
            limit=10,
            offset=0,
            **self._WEIGHTS,
        )

        assert ids == sorted([first.id, second.id])
        assert scores[first.id] == pytest.approx(scores[second.id])

    @pytest.mark.anyio
    async def test_uniform_rating_and_review_count_preserves_nearest_first_order(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        """Decision 1's Consequences: when every candidate shares the
        same (null) `average_rating`/`review_count` -- true for
        essentially every real provider today, since no Review domain
        exists -- the merit-ranked order is identical to the pre-
        existing nearest-first order. Proven, not just asserted: three
        unrated providers at three genuinely different distances."""
        near = await _create_provider(db_session, display_name="Near")
        await _add_service_area(db_session, near)
        await _add_category_label(db_session, near, "Plumbing")

        mid = await _create_provider(db_session, display_name="Mid")
        await _add_service_area(
            db_session, mid, latitude=_DUBAI_LAT + 0.02, longitude=_DUBAI_LNG
        )
        await _add_category_label(db_session, mid, "Plumbing")

        far = await _create_provider(db_session, display_name="Far")
        await _add_service_area(
            db_session, far, latitude=_DUBAI_LAT + 0.05, longitude=_DUBAI_LNG
        )
        await _add_category_label(db_session, far, "Plumbing")

        ids, distances, _total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=self._RADIUS_METERS,
            limit=10,
            offset=0,
            **self._WEIGHTS,
        )

        expected_nearest_first_order = sorted(
            [near.id, mid.id, far.id], key=lambda provider_id: distances[provider_id]
        )
        assert ids == expected_nearest_first_order


class TestPagination:
    @pytest.mark.anyio
    async def test_limit_and_offset_page_through_results(
        self, db_session: AsyncSession, repository: ProviderSearchRepository
    ) -> None:
        providers = [
            await _create_provider(db_session, display_name=f"Provider {i}")
            for i in range(3)
        ]
        for provider in providers:
            await _add_service_area(db_session, provider)
            await _add_category_label(db_session, provider, "Plumbing")
        expected_order = sorted(provider.id for provider in providers)

        first_page, _distances, total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=2,
            offset=0,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )
        second_page, _distances, _total, _scores = await repository.search_nearby(
            category="Plumbing",
            origin_lat=_DUBAI_LAT,
            origin_lng=_DUBAI_LNG,
            radius_meters=10 * _ONE_KM_METERS,
            limit=2,
            offset=2,
            weight_proximity=0.6,
            weight_rating=0.3,
            weight_review_volume=0.1,
            neutral_average_rating=3.0,
            review_volume_cap=50,
        )

        assert total == 3
        assert first_page == expected_order[:2]
        assert second_page == expected_order[2:]


@pytest.fixture
async def _geospatial_index(db_session: AsyncSession) -> None:
    """
    Recreates the DIR-001 migration's extension + GiST index directly
    (Decision 9's own "a raw fixture" framing) -- `Base.metadata.
    create_all()` (used by `db_engine`'s setup) never creates this
    functional index, since it depends on `earthdistance`-extension
    functions the real migration alone is responsible for enabling. See
    `ServiceArea`'s docstring in `app/modules/provider/models.py`.
    """
    await db_session.execute(text("CREATE EXTENSION IF NOT EXISTS cube"))
    await db_session.execute(text("CREATE EXTENSION IF NOT EXISTS earthdistance"))
    await db_session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_service_areas_location "
            "ON provider.service_areas USING gist "
            "(ll_to_earth(center_latitude, center_longitude))"
        )
    )
    await db_session.commit()


def _walk_plan_nodes(node: dict) -> list[dict]:
    """Flattens an `EXPLAIN (FORMAT JSON)` plan tree into a flat list of
    every node (the root plus every descendant)."""
    nodes = [node]
    for child in node.get("Plans", []):
        nodes.extend(_walk_plan_nodes(child))
    return nodes


class TestAC6QueryPlanUsesTheGistIndex:
    @pytest.mark.anyio
    async def test_explain_shows_an_index_scan_not_a_seq_scan_at_volume(
        self,
        db_session: AsyncSession,
        repository: ProviderSearchRepository,
        _geospatial_index: None,
    ) -> None:
        """
        Decision 9: seeds >=1,000 `service_areas` rows scattered across a
        wide geographic spread (not clustered at one point), then runs
        `EXPLAIN (FORMAT JSON)` against the repository's own query
        through this same session, and asserts a real Index Scan/Bitmap
        Index Scan node targeting `idx_service_areas_location` -- and
        explicitly asserts the top-level scan of `service_areas` is
        *not* a `Seq Scan`. A single provider backs every row (bulk
        fixture data, not 1,000 real onboardings, per Decision 9's own
        framing) -- the index's selectivity advantage comes from the
        `service_areas` row volume itself, not from provider count.
        """
        provider = await _create_provider(db_session)
        await _add_category_label(db_session, provider, "Plumbing")

        random.seed(42)
        rows = [
            {
                "provider_id": provider.id,
                "center_latitude": random.uniform(-80.0, 80.0),
                "center_longitude": random.uniform(-170.0, 170.0),
                "radius_meters": 5000,
            }
            for _ in range(1500)
        ]
        # One of them is genuinely near the search origin, so the query
        # still returns a real result.
        rows[0] = {
            "provider_id": provider.id,
            "center_latitude": _DUBAI_LAT,
            "center_longitude": _DUBAI_LNG,
            "radius_meters": 5000,
        }
        await db_session.execute(insert(ServiceArea), rows)
        await db_session.commit()
        await db_session.execute(text("ANALYZE provider.service_areas"))

        explain_sql = text(f"EXPLAIN (FORMAT JSON) {_SEARCH_NEARBY_SQL.text}")
        result = await db_session.execute(
            explain_sql,
            {
                "category": "Plumbing",
                "origin_lat": _DUBAI_LAT,
                "origin_lng": _DUBAI_LNG,
                "radius_meters": 10 * _ONE_KM_METERS,
                "limit": 10,
                "offset": 0,
                "weight_proximity": 0.6,
                "weight_rating": 0.3,
                "weight_review_volume": 0.1,
                "neutral_average_rating": 3.0,
                "review_volume_cap": 50,
            },
        )
        raw_plan = result.scalar_one()
        plan_data = json.loads(raw_plan) if isinstance(raw_plan, str) else raw_plan
        root_plan = plan_data[0]["Plan"]
        nodes = _walk_plan_nodes(root_plan)

        service_area_scan_nodes = [
            node for node in nodes if node.get("Relation Name") == "service_areas"
        ]
        assert service_area_scan_nodes, (
            "expected at least one scan node against service_areas in the plan"
        )
        assert all(
            node["Node Type"] != "Seq Scan" for node in service_area_scan_nodes
        ), f"expected no top-level Seq Scan on service_areas, got: {nodes}"

        index_scan_nodes = [
            node
            for node in nodes
            if node.get("Index Name") == "idx_service_areas_location"
            and node["Node Type"] in ("Index Scan", "Bitmap Index Scan")
        ]
        assert index_scan_nodes, (
            "expected an Index Scan/Bitmap Index Scan node against "
            f"idx_service_areas_location, got: {nodes}"
        )
