"""
End-to-end integration tests for `POST /api/v1/contact-views/
{contact_view_id}/review` (REV-002, AC1/AC2/AC3/AC7) -- mirrors
`test_outcome_tag_api.py`'s real-Postgres, real-app-DI pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app

from ._helpers import (
    create_contact_view,
    create_customer_profile,
    create_hired_contact_view,
    create_provider,
    create_user,
    make_outcome_tag_service,
)


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


class TestSubmitReviewHappyPath:
    @pytest.mark.anyio
    async def test_returns_201_with_the_submitted_review(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "702000001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "702000002")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 5, "comment": "Excellent service."},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["contact_view_id"] == str(contact_view.id)
        assert body["data"]["provider_id"] == str(provider.id)
        assert body["data"]["rating"] == 5
        assert body["data"]["comment"] == "Excellent service."
        assert uuid.UUID(body["data"]["id"])

    @pytest.mark.anyio
    async def test_returns_201_without_a_comment(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "702000003")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "702000004")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 4},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 201
        assert response.json()["data"]["comment"] is None


class TestSubmitReviewNotFoundCases:
    @pytest.mark.anyio
    async def test_returns_404_for_another_customers_contact_view(
        self, client, db_session
    ) -> None:
        owner_customer_user = await create_user(db_session, "702000005")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "702000006")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )
        other_customer_user = await create_user(db_session, "702000007")
        await create_customer_profile(db_session, other_customer_user)

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 4},
            headers=_headers(other_customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_404_for_a_nonexistent_contact_view_id(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "702000008")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/review",
            json={"rating": 4},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404


class TestSubmitReviewAnchorNotVerified:
    @pytest.mark.anyio
    async def test_returns_409_when_no_outcome_tag_exists(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "702000009")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "702000010")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 4},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 409

    @pytest.mark.anyio
    async def test_returns_409_when_hired_is_false(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "702000011")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "702000012")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        outcome_tag_service = make_outcome_tag_service(db_session)
        await outcome_tag_service.submit_outcome_tag(
            customer_user.id, contact_view_id=contact_view.id, hired=False
        )
        await db_session.commit()

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 4},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 409


class TestSubmitReviewDuplicate:
    @pytest.mark.anyio
    async def test_returns_409_for_a_second_submission(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "702000013")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "702000014")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        first = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 5},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )
        assert first.status_code == 201

        second = client.post(
            f"/api/v1/contact-views/{contact_view.id}/review",
            json={"rating": 2},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )
        assert second.status_code == 409


class TestSubmitReviewAuthBoundaries:
    @pytest.mark.anyio
    async def test_returns_401_when_unauthenticated(self, client, db_session) -> None:
        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/review",
            json={"rating": 4},
        )

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_returns_403_for_the_wrong_role(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "702000015")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/review",
            json={"rating": 4},
            headers=_headers(customer_user.id, [ROLE_PROVIDER]),
        )

        assert response.status_code == 403


class TestSubmitReviewSchemaValidation:
    """AC3: the first, cheapest validation layer -- a 422 before any DB
    round trip."""

    @pytest.mark.anyio
    async def test_returns_422_for_rating_zero(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "702000016")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/review",
            json={"rating": 0},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_returns_422_for_rating_six(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "702000017")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/review",
            json={"rating": 6},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 422
