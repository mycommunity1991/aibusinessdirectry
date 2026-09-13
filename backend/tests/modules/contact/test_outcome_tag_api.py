"""
End-to-end integration tests for `POST /api/v1/contact-views/
{contact_view_id}/outcome-tag` (REV-001, AC1/AC2/AC6) -- mirrors
`test_contact_api.py`'s real-Postgres, real-app-DI pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_contact_service,
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


async def _create_contact_view(db_session, *, customer_user_id, provider_id):
    contact_service = make_contact_service(db_session)
    contact_view, _provider = await contact_service.create_contact_view(
        customer_user_id, provider_id=provider_id, search_request_id=None
    )
    await db_session.commit()
    return contact_view


class TestSubmitOutcomeTagHappyPath:
    @pytest.mark.anyio
    async def test_returns_201_for_hired_true(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "602000001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000002")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/outcome-tag",
            json={"hired": True},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["contact_view_id"] == str(contact_view.id)
        assert body["data"]["hired"] is True
        assert uuid.UUID(body["data"]["id"])

    @pytest.mark.anyio
    async def test_returns_201_for_hired_false(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "602000003")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000004")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/outcome-tag",
            json={"hired": False},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 201
        assert response.json()["data"]["hired"] is False


class TestSubmitOutcomeTagNotFoundCases:
    @pytest.mark.anyio
    async def test_returns_404_for_another_customers_contact_view(
        self, client, db_session
    ) -> None:
        owner_customer_user = await create_user(db_session, "602000005")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "602000006")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )
        other_customer_user = await create_user(db_session, "602000007")
        await create_customer_profile(db_session, other_customer_user)

        response = client.post(
            f"/api/v1/contact-views/{contact_view.id}/outcome-tag",
            json={"hired": True},
            headers=_headers(other_customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_404_for_a_nonexistent_contact_view_id(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000008")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/outcome-tag",
            json={"hired": True},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404


class TestSubmitOutcomeTagDuplicate:
    @pytest.mark.anyio
    async def test_returns_409_for_a_second_submission(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000009")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000010")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        first = client.post(
            f"/api/v1/contact-views/{contact_view.id}/outcome-tag",
            json={"hired": True},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )
        assert first.status_code == 201

        second = client.post(
            f"/api/v1/contact-views/{contact_view.id}/outcome-tag",
            json={"hired": False},
            headers=_headers(customer_user.id, [ROLE_CUSTOMER]),
        )
        assert second.status_code == 409


class TestSubmitOutcomeTagAuthBoundaries:
    @pytest.mark.anyio
    async def test_returns_401_when_unauthenticated(self, client, db_session) -> None:
        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/outcome-tag",
            json={"hired": True},
        )

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_returns_403_for_the_wrong_role(self, client, db_session) -> None:
        customer_user = await create_user(db_session, "602000011")
        await create_customer_profile(db_session, customer_user)

        response = client.post(
            f"/api/v1/contact-views/{uuid.uuid4()}/outcome-tag",
            json={"hired": True},
            headers=_headers(customer_user.id, [ROLE_PROVIDER]),
        )

        assert response.status_code == 403
