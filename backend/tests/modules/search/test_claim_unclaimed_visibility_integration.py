"""
End-to-end regression coverage for CLM-001 AC2's backend half: a
Google-seeded-unclaimed listing, created exactly the way
`scripts/import_google_places.py` creates one (Decision 2/4), must
actually appear in the REAL `GET /search/providers` results with
`is_claimed=false` in the payload.

`test_search_service.py`'s own `TestIsClaimedField` proves this at the
`SearchService` unit level with a mocked repository -- this test proves
the full chain a real customer hits: an unclaimed row with a real
`service_areas` row (Decision 4 -- without it, the row would be
invisible to `search_nearby`'s actual geospatial join regardless of
`is_discoverable`) is found by the real query and the response payload
correctly flags it as unclaimed, alongside a claimed provider in the
same result set correctly flagged as claimed.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    BusinessProfile,
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
def anyio_backend() -> str:
    return "asyncio"


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


def _headers(user_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    token = create_access_token(
        subject=str(user_id), roles=roles, jti=str(uuid.uuid4())
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_google_seeded_unclaimed_provider(db_session) -> Provider:
    """Reproduces exactly what `create_google_seeded_provider` writes
    (AC1/Decision 2/3/4): `listing_source=google_seeded_unclaimed`,
    `is_claimed=false`, synthetic `verification_status=approved`/
    `is_discoverable=true`, plus a matching `service_areas` row -- the
    real precondition for actually showing up in `search_nearby`."""
    provider = Provider(
        user_id=None,
        provider_type=ProviderType.BUSINESS,
        display_name="Unclaimed Visibility Test Cafe",
        slug=f"unclaimed-visibility-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        is_claimed=False,
        google_place_id=f"ChIJ_visibility_{uuid.uuid4().hex[:10]}",
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        BusinessProfile(
            provider_id=provider.id,
            address_line="Somewhere in Dubai",
            city="Dubai",
            latitude=_DUBAI_LAT,
            longitude=_DUBAI_LNG,
        )
    )
    db_session.add(
        ServiceArea(
            provider_id=provider.id,
            center_latitude=_DUBAI_LAT,
            center_longitude=_DUBAI_LNG,
            radius_meters=5000,
        )
    )
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label="Cafe", is_primary=True
        )
    )
    await db_session.commit()
    return provider


async def _create_claimed_provider(db_session, phone_number: str) -> Provider:
    user = await _create_user(db_session, phone_number)
    provider = Provider(
        user_id=user.id,
        provider_type=ProviderType.FREELANCER,
        display_name="Claimed Visibility Test Plumber",
        slug=f"claimed-visibility-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        ServiceArea(
            provider_id=provider.id,
            center_latitude=_DUBAI_LAT,
            center_longitude=_DUBAI_LNG,
            radius_meters=5000,
        )
    )
    db_session.add(
        ProviderCategoryLabel(provider_id=provider.id, label="Cafe", is_primary=True)
    )
    await db_session.commit()
    return provider


class TestUnclaimedListingRealSearchVisibility:
    async def test_unclaimed_and_claimed_providers_both_appear_correctly_flagged(
        self, client: TestClient, db_session
    ) -> None:
        unclaimed = await _create_google_seeded_unclaimed_provider(db_session)
        claimed = await _create_claimed_provider(db_session, "604000001")
        caller = await _create_user(db_session, "604000002")

        response = client.get(
            "/api/v1/search/providers",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
            params={
                "latitude": _DUBAI_LAT,
                "longitude": _DUBAI_LNG,
                "radius_km": 10,
                "category": "Cafe",
            },
        )

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        by_id = {item["id"]: item for item in data}

        assert str(unclaimed.id) in by_id, (
            "The unclaimed Google-seeded listing did not appear in real "
            "search results at all -- AC2 requires it to be visible, "
            "not hidden."
        )
        assert by_id[str(unclaimed.id)]["is_claimed"] is False

        assert str(claimed.id) in by_id
        assert by_id[str(claimed.id)]["is_claimed"] is True
