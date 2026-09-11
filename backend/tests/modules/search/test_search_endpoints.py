"""
End-to-end integration tests for `/api/v1/search/*` (DIR-001,
`Plan_S06_DIR-001.md`).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as the
other end-to-end suites, with `get_db` overridden so the FastAPI app and
the test share one transaction. Providers are seeded directly via the
ORM (bypassing `POST /providers/me`, which can never itself produce a
discoverable provider -- `is_discoverable` only ever flips to `true`
through VER-002's admin-approval flow) -- mirrors `test_admin_
verification_service.py`'s `_create_provider` precedent.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    ServiceArea,
    VerificationStatus,
)

_DUBAI_LAT = 25.2048
_DUBAI_LNG = 55.2708


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _token_for(user_id: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(subject=str(user_id), roles=roles, jti=str(uuid.uuid4()))


def _headers(user_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id, roles)}"}


async def _create_discoverable_provider(
    db_session,
    phone_number: str,
    *,
    category_label: str = "Plumbing",
    latitude: float = _DUBAI_LAT,
    longitude: float = _DUBAI_LNG,
    **overrides,
) -> Provider:
    user = await _create_user(db_session, phone_number)
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "slug": f"jane-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        ServiceArea(
            provider_id=provider.id,
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=5000,
        )
    )
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label=category_label, is_primary=True
        )
    )
    await db_session.commit()
    return provider


class TestSearchProvidersAuthorization:
    async def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/search/providers",
            params={"latitude": _DUBAI_LAT, "longitude": _DUBAI_LNG},
        )
        assert response.status_code == 401

    async def test_returns_403_for_a_caller_without_the_customer_role(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "601000001")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(user.id, [ROLE_PROVIDER]),
            params={"latitude": _DUBAI_LAT, "longitude": _DUBAI_LNG},
        )

        assert response.status_code == 403


class TestSearchProviders:
    async def test_a_matching_provider_is_returned_with_the_expected_fields(
        self, client: TestClient, db_session
    ) -> None:
        provider = await _create_discoverable_provider(db_session, "601000010")
        caller = await _create_user(db_session, "601000011")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "radius_km": 10,
                "category": "Plumbing",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        result = body["data"][0]
        assert result["id"] == str(provider.id)
        assert result["display_name"] == provider.display_name
        assert result["category_labels"] == ["Plumbing"]
        assert result["average_rating"] is None
        assert result["review_count"] == 0
        assert "distance_meters" in result
        assert "primary_photo_url" in result

    async def test_empty_result_set_returns_an_empty_data_list(
        self, client: TestClient, db_session
    ) -> None:
        """AC4's backend half: an empty `data`/`total_items: 0` shape."""
        caller = await _create_user(db_session, "601000020")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "category": "NoSuchCategoryAnywhere",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total_items"] == 0

    async def test_a_non_discoverable_provider_never_appears(
        self, client: TestClient, db_session
    ) -> None:
        await _create_discoverable_provider(
            db_session,
            "601000030",
            is_discoverable=False,
            verification_status=VerificationStatus.PENDING,
        )
        caller = await _create_user(db_session, "601000031")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "category": "Plumbing",
            },
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_radius_km_at_or_below_zero_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        caller = await _create_user(db_session, "601000040")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={"latitude": _DUBAI_LAT, "longitude": _DUBAI_LNG, "radius_km": 0},
        )

        assert response.status_code == 422

    async def test_radius_km_above_the_configured_max_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        caller = await _create_user(db_session, "601000041")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "radius_km": 100_000,
            },
        )

        assert response.status_code == 422

    async def test_category_is_optional_and_browses_across_all_categories(
        self, client: TestClient, db_session
    ) -> None:
        await _create_discoverable_provider(
            db_session, "601000050", category_label="Plumbing"
        )
        await _create_discoverable_provider(
            db_session, "601000051", category_label="Electrician"
        )
        caller = await _create_user(db_session, "601000052")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={"latitude": _DUBAI_LAT, "longitude": _DUBAI_LNG},
        )

        assert response.status_code == 200
        assert response.json()["pagination"]["total_items"] == 2


class TestMeritRankingChangesDirOwnEndpointOrder:
    """MAT-001, Decision 1 (`Plan_S08_MAT-001.md`): DIR-001's own `GET
    /search/providers` result order is a legitimate, in-scope behavioral
    change under MAT-001, not just the AI-conversation path -- both
    callers share the identical `ProviderSearchRepository.search_nearby`
    query (`search_providers_ranked`), never a second, divergent
    ranking implementation (AC2). Every pre-existing fixture in this
    file happens to use uniform `average_rating`/`review_count`, so none
    of them alone proves the order-changing claim -- this test
    deliberately uses non-uniform rating data through the real HTTP
    endpoint to prove it directly, not just infer it from the
    repository-layer tests."""

    async def test_a_farther_but_higher_rated_provider_outranks_a_closer_unrated_one(
        self, client: TestClient, db_session
    ) -> None:
        closer_unrated = await _create_discoverable_provider(
            db_session,
            "601000080",
            category_label="Plumbing",
            average_rating=None,
            review_count=0,
        )
        farther_top_rated = await _create_discoverable_provider(
            db_session,
            "601000081",
            category_label="Plumbing",
            latitude=_DUBAI_LAT + 0.03,  # ~3.3km north -- still in radius
            longitude=_DUBAI_LNG,
            average_rating=Decimal("5.00"),
            review_count=50,
        )
        caller = await _create_user(db_session, "601000082")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "radius_km": 10,
                "category": "Plumbing",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 2
        ordered_ids = [result["id"] for result in body["data"]]
        # If this were still DIR-001's old distance-only order, the
        # closer (unrated) provider would come first. Under MAT-001's
        # merit-ranking, the farther-but-top-rated one outranks it
        # instead -- direct proof, through the real HTTP endpoint, that
        # this query's order genuinely changed for DIR-001's own path,
        # not only the AI-conversation path.
        assert ordered_ids == [str(farther_top_rated.id), str(closer_unrated.id)]
        # The endpoint still never exposes a raw `match_score` field.
        for result in body["data"]:
            assert "match_score" not in result


class TestListCategoriesEndpoint:
    async def test_returns_401_without_a_token(self, client: TestClient) -> None:
        assert client.get("/api/v1/search/categories").status_code == 401

    async def test_only_labels_from_discoverable_providers_are_returned(
        self, client: TestClient, db_session
    ) -> None:
        await _create_discoverable_provider(
            db_session, "601000060", category_label="Plumbing"
        )
        await _create_discoverable_provider(
            db_session,
            "601000061",
            category_label="OnlyOnAHiddenProvider",
            is_discoverable=False,
            verification_status=VerificationStatus.PENDING,
        )
        caller = await _create_user(db_session, "601000062")

        response = client.get(
            "/api/v1/search/categories", headers=_headers(caller.id, [ROLE_CUSTOMER])
        )

        assert response.status_code == 200
        labels = {option["label"] for option in response.json()["data"]}
        assert "Plumbing" in labels
        assert "OnlyOnAHiddenProvider" not in labels

    async def test_case_variants_of_the_same_label_collapse_to_one_entry(
        self, client: TestClient, db_session
    ) -> None:
        await _create_discoverable_provider(
            db_session, "601000070", category_label="Plumbing"
        )
        await _create_discoverable_provider(
            db_session, "601000071", category_label="plumbing"
        )
        caller = await _create_user(db_session, "601000072")

        response = client.get(
            "/api/v1/search/categories", headers=_headers(caller.id, [ROLE_CUSTOMER])
        )

        assert response.status_code == 200
        labels = [option["label"] for option in response.json()["data"]]
        assert len([label for label in labels if label.lower() == "plumbing"]) == 1
