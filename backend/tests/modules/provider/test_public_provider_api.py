"""
End-to-end integration tests for `GET /api/v1/providers/{provider_id}`
(CON-001, AC5, Decision 2/7/8, `Plan_S08_CON-001.md`) -- mirrors
`test_claim_api.py`'s real-Postgres, real-app-DI pattern.

Also proves Decision 2's route-registration-order claim: `/me` still
resolves to the pre-existing owner-only router even though this new
`/{provider_id}` route is registered second.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    BusinessProfile,
    FreelancerProfile,
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    VerificationStatus,
)

PHONE_COUNTRY_CODE = "+971"


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


def _token_for(user_id: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(subject=str(user_id), roles=roles, jti=str(uuid.uuid4()))


def _headers(user_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id, roles)}"}


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_business_provider(
    db_session, *, user: User | None, **overrides: object
) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id if user is not None else None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Al Noor Plumbing Services LLC",
        "slug": f"al-noor-plumbing-{uuid.uuid4().hex[:8]}",
        "phone_country_code": "+971",
        "phone_number": "43334455",
        "listing_source": (
            ListingSource.SELF_REGISTERED
            if user is not None
            else ListingSource.GOOGLE_SEEDED_UNCLAIMED
        ),
        "is_claimed": user is not None,
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    if user is None:
        payload["google_place_id"] = f"ChIJ_{uuid.uuid4().hex[:10]}"
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    business_profile = BusinessProfile(
        provider_id=provider.id,
        address_line="Shop 12, Al Wasl Road, Dubai",
        city="Dubai",
        region="Dubai",
        latitude=25.2048,
        longitude=55.2708,
        delivery_radius_meters=5000,
    )
    db_session.add(business_profile)
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label="Plumbing", is_primary=True
        )
    )
    await db_session.commit()
    return provider


async def _create_freelancer_provider(
    db_session, *, user: User, **overrides: object
) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "slug": f"jane-the-plumber-{uuid.uuid4().hex[:8]}",
        "phone_country_code": "+971",
        "phone_number": "43334455",
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
        FreelancerProfile(
            provider_id=provider.id,
            base_latitude=25.2048,
            base_longitude=55.2708,
            service_radius_meters=15000,
        )
    )
    await db_session.commit()
    return provider


class TestGetProviderPublicProfileHappyPath:
    async def test_business_provider_returns_expected_fields(
        self, client, db_session
    ) -> None:
        owner = await _create_user(db_session, "603000001")
        caller = await _create_user(db_session, "603000002")
        provider = await _create_business_provider(
            db_session,
            user=owner,
            average_rating=Decimal("4.80"),
            review_count=12,
        )

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(provider.id)
        assert data["provider_type"] == "business"
        assert data["display_name"] == provider.display_name
        assert data["category_labels"] == [{"label": "Plumbing", "is_primary": True}]
        # AC5: rating together with review count, never alone.
        assert data["average_rating"] == "4.80"
        assert data["review_count"] == 12
        assert len(data["weekly_availability"]) == 7
        assert data["city"] == "Dubai"
        assert data["region"] == "Dubai"
        assert data["delivery_radius_meters"] == 5000
        assert data["service_radius_meters"] is None
        # Never on the profile read -- only via the Contact Reveal flow.
        assert "phone_number" not in data
        assert "whatsapp_number" not in data

    async def test_freelancer_provider_returns_service_radius(
        self, client, db_session
    ) -> None:
        owner = await _create_user(db_session, "603000003")
        caller = await _create_user(db_session, "603000004")
        provider = await _create_freelancer_provider(db_session, user=owner)

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["provider_type"] == "freelancer"
        assert data["service_radius_meters"] == 15000
        assert data["delivery_radius_meters"] is None
        assert data["city"] is None
        assert data["region"] is None


class TestBadgePrecedenceFixtures:
    """Decision 8: the server returns the raw fields unchanged; the
    client renders exactly one of three states off them."""

    async def test_unclaimed_listing_is_claimed_false(self, client, db_session) -> None:
        caller = await _create_user(db_session, "603000005")
        provider = await _create_business_provider(db_session, user=None)

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        data = response.json()["data"]
        assert data["is_claimed"] is False
        # A Google-seeded-unclaimed listing is `verification_status=
        # approved` purely to be searchable -- confirming the two
        # fields are never conflated into one contradictory badge.
        assert data["verification_status"] == "approved"

    async def test_claimed_and_approved(self, client, db_session) -> None:
        owner = await _create_user(db_session, "603000006")
        caller = await _create_user(db_session, "603000007")
        provider = await _create_business_provider(
            db_session,
            user=owner,
            verification_status=VerificationStatus.APPROVED,
            is_discoverable=True,
        )

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        data = response.json()["data"]
        assert data["is_claimed"] is True
        assert data["verification_status"] == "approved"

    async def test_claimed_and_pending(self, client, db_session) -> None:
        owner = await _create_user(db_session, "603000008")
        caller = await _create_user(db_session, "603000009")
        provider = await _create_business_provider(
            db_session,
            user=owner,
            verification_status=VerificationStatus.PENDING,
            is_discoverable=False,
        )

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        data = response.json()["data"]
        assert data["is_claimed"] is True
        assert data["verification_status"] == "pending"


class TestNotFoundCases:
    async def test_returns_404_for_a_nonexistent_provider(
        self, client, db_session
    ) -> None:
        caller = await _create_user(db_session, "603000010")

        response = client.get(
            f"/api/v1/providers/{uuid.uuid4()}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    async def test_returns_404_for_a_soft_deleted_provider(
        self, client, db_session
    ) -> None:
        owner = await _create_user(db_session, "603000011")
        caller = await _create_user(db_session, "603000012")
        provider = await _create_business_provider(
            db_session, user=owner, is_active=False
        )

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404


class TestDecision7NonDiscoverableStillViewable:
    """Explicit regression test for the deliberately looser posture:
    `is_discoverable=false` alone must never 404 this endpoint."""

    async def test_a_non_discoverable_but_active_provider_is_still_viewable(
        self, client, db_session
    ) -> None:
        owner = await _create_user(db_session, "603000013")
        caller = await _create_user(db_session, "603000014")
        provider = await _create_business_provider(
            db_session,
            user=owner,
            is_discoverable=False,
            verification_status=VerificationStatus.APPROVED,
        )

        response = client.get(
            f"/api/v1/providers/{provider.id}",
            headers=_headers(caller.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200


class TestRouteRegistrationOrder:
    """Decision 2: `/me` must keep matching the pre-existing owner-only
    router even though `/{provider_id}` is registered afterward."""

    async def test_me_route_still_resolves_to_the_owner_only_router(
        self, client, db_session
    ) -> None:
        caller_with_no_provider = await _create_user(db_session, "603000015")

        response = client.get(
            "/api/v1/providers/me",
            headers=_headers(caller_with_no_provider.id, [ROLE_CUSTOMER]),
        )

        # `/me` resolved as the literal path (404, "no provider yet"),
        # never as `/{provider_id}` with `provider_id="me"` (which would
        # instead 422 on UUID parsing).
        assert response.status_code == 404
