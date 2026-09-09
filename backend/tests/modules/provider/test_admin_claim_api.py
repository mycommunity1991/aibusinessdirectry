"""
End-to-end integration tests for `/api/v1/admin/claims/*` (CLM-001,
Decision 9, `Plan_S06_CLM-001.md`) -- mirrors
`test_admin_verification_endpoints.py`'s real-Postgres pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    BusinessProfile,
    ListingSource,
    Provider,
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


async def _create_unclaimed_provider(db_session, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Cafe",
        "slug": f"acme-cafe-{uuid.uuid4().hex[:8]}",
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
        address_line="123 Main St",
        city="Dubai",
        latitude=25.2,
        longitude=55.3,
    )
    db_session.add(business_profile)
    await db_session.commit()
    return provider


async def _create_review_request(
    db_session, provider: Provider, claimant: User, reason: str = "otp_failed"
):
    from app.modules.administration.repositories.claim_review_request_repository import (  # noqa: E501
        ClaimReviewRequestRepository,
    )
    from app.modules.administration.services.claim_review_request_service import (
        ClaimReviewRequestService,
    )

    service = ClaimReviewRequestService(ClaimReviewRequestRepository(db_session))
    request = await service.create(
        provider_id=provider.id, claimant_user_id=claimant.id, reason=reason
    )
    await db_session.commit()
    return request


class TestAuthorizationMatrix:
    async def test_list_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/admin/claims")
        assert response.status_code == 401

    async def test_list_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "700000001")
        response = client.get(
            "/api/v1/admin/claims", headers=_headers(user.id, [ROLE_CUSTOMER])
        )
        assert response.status_code == 403

    async def test_approve_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "700000002")
        response = client.post(
            f"/api/v1/admin/claims/{uuid.uuid4()}/approve",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )
        assert response.status_code == 403


class TestListOpenClaimReviews:
    async def test_lists_an_open_request_with_provider_context(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "700000003")
        admin = await _create_user(db_session, "700000004")
        provider = await _create_unclaimed_provider(db_session)
        await _create_review_request(db_session, provider, claimant)

        response = client.get(
            "/api/v1/admin/claims", headers=_headers(admin.id, [ROLE_ADMIN])
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["provider_display_name"] == "Acme Cafe"
        assert data[0]["status"] == "open"


class TestApprove:
    async def test_approve_finalizes_the_claim(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "700000005")
        admin = await _create_user(db_session, "700000006")
        provider = await _create_unclaimed_provider(db_session)
        request = await _create_review_request(db_session, provider, claimant)

        response = client.post(
            f"/api/v1/admin/claims/{request.id}/approve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "resolved"
        assert data["resolution"] == "approved"

        from app.modules.provider.repositories.provider_repository import (
            ProviderRepository,
        )

        refreshed = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed is not None
        assert refreshed.is_claimed is True
        assert refreshed.user_id == claimant.id
        assert refreshed.verification_status == VerificationStatus.PENDING
        assert refreshed.is_discoverable is False

    async def test_approving_a_nonexistent_request_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "700000007")

        response = client.post(
            f"/api/v1/admin/claims/{uuid.uuid4()}/approve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 404


class TestReject:
    async def test_reject_leaves_the_listing_unclaimed(
        self, client: TestClient, db_session
    ) -> None:
        claimant = await _create_user(db_session, "700000008")
        admin = await _create_user(db_session, "700000009")
        provider = await _create_unclaimed_provider(db_session)
        request = await _create_review_request(
            db_session, provider, claimant, reason="no_public_number"
        )

        response = client.post(
            f"/api/v1/admin/claims/{request.id}/reject",
            json={"resolution_notes": "Not a real match."},
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "resolved"
        assert data["resolution"] == "rejected"

        from app.modules.provider.repositories.provider_repository import (
            ProviderRepository,
        )

        refreshed = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed is not None
        assert refreshed.is_claimed is False
        assert refreshed.user_id is None
