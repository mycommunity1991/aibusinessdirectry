"""
End-to-end integration tests for `GET`/`POST /api/v1/customers/me/addresses`
and `PATCH`/`DELETE /api/v1/customers/me/addresses/{address_id}` (CUS-002,
AC1/AC2/AC6/AC8).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as
`test_customer_endpoints.py`, with `get_db` overridden so the FastAPI app
and the test both see the same transaction. Access tokens are minted
directly against a real `identity.users` row created in the same test.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.customer.models import SavedAddress
from app.modules.identity.models import AuthProvider, User

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


def _token_for(user_id: uuid.UUID) -> str:
    return create_access_token(
        subject=str(user_id), roles=[ROLE_CUSTOMER], jti=str(uuid.uuid4())
    )


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}


def _address_payload(**overrides) -> dict:
    payload = {
        "label": "Home",
        "address_line": "Villa 12, Al Wasl Road",
        "city": "Dubai",
        "region": "Dubai",
        "country_code": "AE",
        "latitude": 25.2048,
        "longitude": 55.2708,
    }
    payload.update(overrides)
    return payload


class TestListMyAddresses:
    @pytest.mark.anyio
    async def test_returns_empty_list_for_a_customer_with_no_addresses(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "602000001")

        response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.anyio
    async def test_lists_created_addresses(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "602000002")
        client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        )

        response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["address_line"] == "Villa 12, Al Wasl Road"

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/customers/me/addresses")
        assert response.status_code == 401


class TestCreateMyAddress:
    @pytest.mark.anyio
    async def test_creates_an_address(self, client: TestClient, db_session) -> None:
        """AC1."""
        user = await _create_user(db_session, "602000010")

        response = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        )

        assert response.status_code == 201
        body = response.json()["data"]
        assert body["label"] == "Home"
        assert body["country_code"] == "AE"
        assert body["is_default"] is False

    @pytest.mark.anyio
    async def test_legacy_account_with_no_profile_yet_can_create_its_first_address(
        self, client: TestClient, db_session
    ) -> None:
        """Decision 4: a user who never called `GET`/`PATCH
        /customers/me` (no prior `customer_profiles` row) can still
        create its first address -- no spurious 404/500."""
        user = await _create_user(db_session, "602000011")

        response = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        )

        assert response.status_code == 201

    @pytest.mark.anyio
    async def test_creating_a_second_default_unsets_the_first(
        self, client: TestClient, db_session
    ) -> None:
        """AC2/AC9: default-address uniqueness, create-time path."""
        user = await _create_user(db_session, "602000012")

        first = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Home", is_default=True),
        )
        assert first.json()["data"]["is_default"] is True
        first_id = first.json()["data"]["id"]

        second = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Work", is_default=True),
        )
        assert second.status_code == 201
        assert second.json()["data"]["is_default"] is True

        list_response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )
        addresses = {a["id"]: a["is_default"] for a in list_response.json()["data"]}
        assert addresses[first_id] is False
        assert addresses[second.json()["data"]["id"]] is True

        result = await db_session.execute(
            select(SavedAddress).where(SavedAddress.is_default.is_(True))
        )
        assert len(result.scalars().all()) == 1

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/customers/me/addresses", json=_address_payload()
        )
        assert response.status_code == 401


class TestUpdateMyAddress:
    @pytest.mark.anyio
    async def test_partial_update_only_changes_provided_fields(
        self, client: TestClient, db_session
    ) -> None:
        """AC6."""
        user = await _create_user(db_session, "602000020")
        created = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        ).json()["data"]

        response = client.patch(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
            json={"city": "Abu Dhabi"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["city"] == "Abu Dhabi"
        assert body["address_line"] == created["address_line"]
        assert body["label"] == created["label"]

    @pytest.mark.anyio
    async def test_setting_is_default_unsets_the_prior_default(
        self, client: TestClient, db_session
    ) -> None:
        """AC2/AC9: default-address uniqueness, update-time path."""
        user = await _create_user(db_session, "602000021")
        first = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Home", is_default=True),
        ).json()["data"]
        second = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Work", is_default=False),
        ).json()["data"]

        response = client.patch(
            f"/api/v1/customers/me/addresses/{second['id']}",
            headers=_auth_headers(user.id),
            json={"is_default": True},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_default"] is True

        list_response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )
        addresses = {a["id"]: a["is_default"] for a in list_response.json()["data"]}
        assert addresses[first["id"]] is False
        assert addresses[second["id"]] is True

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.patch(
            f"/api/v1/customers/me/addresses/{uuid.uuid4()}",
            json={"city": "Abu Dhabi"},
        )
        assert response.status_code == 401


class TestDeleteMyAddress:
    @pytest.mark.anyio
    async def test_soft_deletes_and_excludes_from_subsequent_list(
        self, client: TestClient, db_session
    ) -> None:
        """AC6/AC7: soft-delete -- excluded from the list, but the row
        itself survives (per `04_DATABASE.md`'s soft-delete rule)."""
        user = await _create_user(db_session, "602000030")
        created = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        ).json()["data"]

        response = client.delete(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
        )

        assert response.status_code == 200

        list_response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )
        assert list_response.json()["data"] == []

        result = await db_session.execute(
            select(SavedAddress).where(SavedAddress.id == uuid.UUID(created["id"]))
        )
        row = result.scalar_one()
        assert row.is_active is False
        assert row.deleted_at is not None

    @pytest.mark.anyio
    async def test_deleting_the_default_leaves_no_default_set(
        self, client: TestClient, db_session
    ) -> None:
        """AC7: after deleting the default, `GET /me/addresses` clearly
        conveys no default is currently set (no row with
        `is_default: true`) -- the backend never auto-promotes."""
        user = await _create_user(db_session, "602000031")
        default_address = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Home", is_default=True),
        ).json()["data"]
        client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(label="Work", is_default=False),
        )

        client.delete(
            f"/api/v1/customers/me/addresses/{default_address['id']}",
            headers=_auth_headers(user.id),
        )

        list_response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user.id)
        )
        remaining = list_response.json()["data"]
        assert len(remaining) == 1
        assert all(a["is_default"] is False for a in remaining)

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.delete(f"/api/v1/customers/me/addresses/{uuid.uuid4()}")
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_patch_on_an_already_soft_deleted_address_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        """First-soft-delete-in-the-codebase boundary: once an address is
        soft-deleted, `get_active_by_id`'s active-row filter must make it
        indistinguishable from nonexistent for every subsequent verb --
        not just excluded from the list (already covered above)."""
        user = await _create_user(db_session, "602000032")
        created = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        ).json()["data"]

        delete_response = client.delete(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
        )
        assert delete_response.status_code == 200

        patch_response = client.patch(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
            json={"city": "Sharjah"},
        )

        assert patch_response.status_code == 404

    @pytest.mark.anyio
    async def test_delete_on_an_already_soft_deleted_address_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        """Same boundary as above, for a second `DELETE` on the same
        already-deleted address -- must 404, never a silent 200 no-op."""
        user = await _create_user(db_session, "602000033")
        created = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user.id),
            json=_address_payload(),
        ).json()["data"]

        first_delete = client.delete(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
        )
        assert first_delete.status_code == 200

        second_delete = client.delete(
            f"/api/v1/customers/me/addresses/{created['id']}",
            headers=_auth_headers(user.id),
        )

        assert second_delete.status_code == 404


class TestOwnershipIsolation:
    """AC8/AC9: a customer can never view or modify another customer's
    addresses -- 404, never 403, and the cross-customer's list never
    includes it."""

    @pytest.mark.anyio
    async def test_cross_customer_get_patch_delete_all_return_404(
        self, client: TestClient, db_session
    ) -> None:
        user_a = await _create_user(db_session, "602000040")
        user_b = await _create_user(db_session, "602000041")

        address_a = client.post(
            "/api/v1/customers/me/addresses",
            headers=_auth_headers(user_a.id),
            json=_address_payload(),
        ).json()["data"]

        patch_response = client.patch(
            f"/api/v1/customers/me/addresses/{address_a['id']}",
            headers=_auth_headers(user_b.id),
            json={"city": "Sharjah"},
        )
        assert patch_response.status_code == 404

        delete_response = client.delete(
            f"/api/v1/customers/me/addresses/{address_a['id']}",
            headers=_auth_headers(user_b.id),
        )
        assert delete_response.status_code == 404

        list_response = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user_b.id)
        )
        assert list_response.json()["data"] == []

        # User A's address is untouched by user B's failed attempts.
        get_a_list = client.get(
            "/api/v1/customers/me/addresses", headers=_auth_headers(user_a.id)
        )
        assert get_a_list.json()["data"][0]["city"] == "Dubai"

    @pytest.mark.anyio
    async def test_nonexistent_address_id_also_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "602000042")

        response = client.patch(
            f"/api/v1/customers/me/addresses/{uuid.uuid4()}",
            headers=_auth_headers(user.id),
            json={"city": "Sharjah"},
        )

        assert response.status_code == 404
