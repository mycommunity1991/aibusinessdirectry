"""
End-to-end integration tests for `POST /api/v1/contact-views` (CON-001,
AC2/AC3/AC4) -- mirrors `test_claim_api.py`'s real-Postgres,
real-app-DI pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app

from ._helpers import create_customer_profile, create_provider, create_user


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


class TestCreateContactViewHappyPath:
    @pytest.mark.anyio
    async def test_returns_201_with_the_providers_phone_number(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "502000001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "502000002")
        provider = await create_provider(
            db_session,
            user=provider_owner,
            phone_country_code="+971",
            phone_number="43334455",
        )

        response = client.post(
            "/api/v1/contact-views",
            json={"provider_id": str(provider.id)},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["provider_id"] == str(provider.id)
        assert body["data"]["phone_country_code"] == "+971"
        assert body["data"]["phone_number"] == "43334455"
        assert uuid.UUID(body["data"]["id"])


class TestCreateContactViewSelfDealing:
    @pytest.mark.anyio
    async def test_returns_403_when_the_caller_owns_the_target_listing(
        self, client, db_session
    ) -> None:
        shared_user = await create_user(db_session, "502000003")
        await create_customer_profile(db_session, shared_user)
        provider = await create_provider(db_session, user=shared_user)

        response = client.post(
            "/api/v1/contact-views",
            json={"provider_id": str(provider.id)},
            headers=_headers(shared_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403


class TestCreateContactViewNotFoundCases:
    @pytest.mark.anyio
    async def test_returns_404_for_a_nonexistent_provider(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "502000004")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            "/api/v1/contact-views",
            json={"provider_id": str(uuid.uuid4())},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_404_for_a_mismatched_search_request_id(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "502000005")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "502000006")
        provider = await create_provider(db_session, user=provider_owner)

        response = client.post(
            "/api/v1/contact-views",
            json={
                "provider_id": str(provider.id),
                "search_request_id": str(uuid.uuid4()),
            },
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404


class TestCreateContactViewAuthBoundaries:
    @pytest.mark.anyio
    async def test_returns_401_when_unauthenticated(self, client, db_session) -> None:
        provider_owner = await create_user(db_session, "502000007")
        provider = await create_provider(db_session, user=provider_owner)

        response = client.post(
            "/api/v1/contact-views",
            json={"provider_id": str(provider.id)},
        )

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_returns_403_for_the_wrong_role(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "502000008")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "502000009")
        provider = await create_provider(db_session, user=provider_owner)

        response = client.post(
            "/api/v1/contact-views",
            json={"provider_id": str(provider.id)},
            headers=_headers(customer_user.id, [ROLE_PROVIDER]),
        )

        assert response.status_code == 403
