"""
End-to-end integration tests for `/api/v1/claims/*` (CLM-001,
`Plan_S06_CLM-001.md`) -- mirrors `test_provider_endpoints.py`'s/
`test_auth_endpoints.py`'s real-Postgres + real-Redis pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER
from app.core.redis import get_redis_client
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.dependencies import get_sms_sender
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.services.sms_sender import SmsSender
from app.modules.provider.models import ListingSource, Provider, ProviderType

PHONE_COUNTRY_CODE = "+971"


class SpySmsSender(SmsSender):
    """Test double capturing dispatched OTP codes instead of sending SMS."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, phone_country_code: str, phone_number: str, code: str) -> None:
        self.sent.append((phone_country_code, phone_number, code))

    @property
    def last_code(self) -> str:
        return self.sent[-1][2]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sms_spy() -> SpySmsSender:
    return SpySmsSender()


@pytest.fixture
def client(db_session, sms_spy: SpySmsSender, redis_client):
    from tests.conftest import TEST_REDIS_URL

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_sms_sender] = lambda: sms_spy
    app.dependency_overrides[get_redis_client] = lambda: Redis.from_url(
        TEST_REDIS_URL, decode_responses=True
    )
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


async def _create_unclaimed_provider(db_session, **overrides: object) -> Provider:
    from app.modules.provider.models import BusinessProfile, VerificationStatus

    payload: dict[str, object] = {
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Al Noor Plumbing Services LLC",
        "slug": f"al-noor-plumbing-{uuid.uuid4().hex[:8]}",
        "phone_country_code": "+971",
        "phone_number": "43334455",
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "google_place_id": f"ChIJ_{uuid.uuid4().hex[:10]}",
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

    business_profile = BusinessProfile(
        provider_id=provider.id,
        address_line="Shop 12, Al Wasl Road, Dubai",
        city="Dubai",
        region="Dubai",
        latitude=25.2048,
        longitude=55.2708,
    )
    db_session.add(business_profile)
    await db_session.commit()
    return provider


class TestSearchUnclaimedScoping:
    """AC3: only `google_seeded_unclaimed`/`is_claimed=false` rows appear."""

    async def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/claims/search", params={"query": "Al Noor"})
        assert response.status_code == 401

    async def test_returns_403_for_a_caller_without_the_customer_role(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "600000001")
        response = client.get(
            "/api/v1/claims/search",
            params={"query": "Al Noor"},
            headers=_headers(user.id, [ROLE_ADMIN]),
        )
        assert response.status_code == 403

    async def test_matches_by_substring_name(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "600000002")
        await _create_unclaimed_provider(
            db_session, display_name="Al Noor Plumbing Services LLC"
        )

        response = client.get(
            "/api/v1/claims/search",
            params={"query": "al noor plumb"},
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["display_name"] == "Al Noor Plumbing Services LLC"
        assert data[0]["address_line"] == "Shop 12, Al Wasl Road, Dubai"
        assert data[0]["phone_number_masked"] is not None
        assert "43334455" not in data[0]["phone_number_masked"]

    async def test_a_self_registered_provider_never_appears(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "600000003")
        await _create_unclaimed_provider(
            db_session,
            display_name="Unique Self Registered Match XYZ",
            listing_source=ListingSource.SELF_REGISTERED,
            is_claimed=True,
            user_id=user.id,
        )

        response = client.get(
            "/api/v1/claims/search",
            params={"query": "Unique Self Registered Match"},
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_an_already_claimed_listing_never_appears(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "600000004")
        owner = await _create_user(db_session, "600000005")
        await _create_unclaimed_provider(
            db_session,
            display_name="Unique Already Claimed Match XYZ",
            is_claimed=True,
            user_id=owner.id,
        )

        response = client.get(
            "/api/v1/claims/search",
            params={"query": "Unique Already Claimed Match"},
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_non_matching_query_returns_empty(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "600000006")
        await _create_unclaimed_provider(db_session, display_name="Acme Cafe")

        response = client.get(
            "/api/v1/claims/search",
            params={"query": "no-such-listing-anywhere"},
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestClaimOtpRoundTrip:
    async def test_full_round_trip_request_verify_claims_the_listing(
        self, client: TestClient, db_session, sms_spy: SpySmsSender
    ) -> None:
        claimant = await _create_user(db_session, "601000001")
        provider = await _create_unclaimed_provider(db_session)

        otp_response = client.post(
            f"/api/v1/claims/{provider.id}/request-otp",
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )
        assert otp_response.status_code == 200
        code = sms_spy.last_code
        assert sms_spy.sent[-1][0] == "+971"
        assert sms_spy.sent[-1][1] == "43334455"

        verify_response = client.post(
            f"/api/v1/claims/{provider.id}/verify-otp",
            json={"code": code},
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        assert verify_response.status_code == 200
        data = verify_response.json()["data"]
        assert data["is_claimed"] is True
        assert data["verification_status"] == "pending"

    async def test_request_otp_on_a_provider_with_no_public_number_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "601000002")
        provider = await _create_unclaimed_provider(
            db_session, phone_country_code=None, phone_number=None
        )

        response = client.post(
            f"/api/v1/claims/{provider.id}/request-otp",
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 409

    async def test_request_otp_on_a_nonexistent_listing_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "601000003")

        response = client.post(
            f"/api/v1/claims/{uuid.uuid4()}/request-otp",
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    async def test_verify_otp_with_a_wrong_code_returns_400_and_does_not_claim(
        self, client: TestClient, db_session, sms_spy: SpySmsSender
    ) -> None:
        claimant = await _create_user(db_session, "601000004")
        provider = await _create_unclaimed_provider(db_session)

        client.post(
            f"/api/v1/claims/{provider.id}/request-otp",
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        response = client.post(
            f"/api/v1/claims/{provider.id}/verify-otp",
            json={"code": "000000"},
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 400

        from app.modules.provider.repositories.provider_repository import (
            ProviderRepository,
        )

        refreshed = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed is not None
        assert refreshed.is_claimed is False


class TestRequestAdminReview:
    async def test_creates_a_review_request_and_returns_success(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "602000001")
        provider = await _create_unclaimed_provider(db_session)

        response = client.post(
            f"/api/v1/claims/{provider.id}/request-admin-review",
            json={"reason": "otp_failed"},
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200

        admin_response = client.get(
            "/api/v1/admin/claims",
            headers=_headers(uuid.uuid4(), [ROLE_ADMIN]),
        )
        assert admin_response.status_code == 200
        data = admin_response.json()["data"]
        assert len(data) == 1
        assert data[0]["reason"] == "otp_failed"
        assert data[0]["provider_id"] == str(provider.id)
