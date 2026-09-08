"""
End-to-end integration tests for `/api/v1/providers/me` and its PRO-002
sub-resources (`/me` PATCH, `/me/portfolio*`, `/me/availability`).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as the
customer-domain endpoint tests, with `get_db` overridden so the FastAPI
app and the test both see the same transaction. Access tokens are
minted directly against a real `identity.users` row created in the same
test -- no `/auth/*` endpoint is ever called (AC2: the caller reuses
their existing Account, no new registration/OTP/OAuth step).
`get_file_storage` is overridden to a per-test temporary directory so
portfolio-upload tests never write into the real `backend/uploads/`.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, Role, User, UserRole
from app.modules.identity.services.seed_data import seed_roles
from app.modules.provider.dependencies import get_file_storage
from app.modules.provider.models import Provider
from app.shared.storage.local_file_storage import LocalFileStorage

PHONE_COUNTRY_CODE = "+971"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client(db_session, tmp_path):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_file_storage] = lambda: LocalFileStorage(
        base_directory=str(tmp_path)
    )
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


def _business_payload(**overrides) -> dict:
    payload = {
        "provider_type": "business",
        "display_name": "Acme Plumbing",
        "phone_country_code": "+971",
        "phone_number": "501234567",
        "whatsapp_number": "501234567",
        "category_label": "Plumbing",
        "description": "24/7 residential plumbing services.",
        "business_details": {
            "address_line": "Shop 4, Al Wasl Road",
            "city": "Dubai",
            "region": "Dubai",
            "country_code": "AE",
            "latitude": 25.2048,
            "longitude": 55.2708,
            "operating_hours": {
                "monday": {"open": "09:00", "close": "18:00"},
                "sunday": None,
            },
            "delivery_radius_meters": 5000,
            "trade_license_number": "TL-12345",
        },
    }
    payload.update(overrides)
    return payload


def _freelancer_payload(**overrides) -> dict:
    payload = {
        "provider_type": "freelancer",
        "display_name": "Jane the Plumber",
        "phone_country_code": "+971",
        "phone_number": "509876543",
        "whatsapp_number": None,
        "category_label": "Plumbing",
        "description": None,
        "freelancer_details": {
            "base_latitude": 25.2048,
            "base_longitude": 55.2708,
            "country_code": "AE",
            "service_radius_meters": 8000,
            "skills": ["Plumbing", "AC Repair"],
            "years_experience": 5,
        },
    }
    payload.update(overrides)
    return payload


class TestCreateMyProvider:
    @pytest.mark.anyio
    async def test_creates_a_business_provider(
        self, client: TestClient, db_session
    ) -> None:
        """AC1/AC2/AC4/AC5/AC7: happy path, Business subtype -- and the
        resulting `providers.user_id` equals the caller's own id, with
        no new `/auth/*` call anywhere in this test."""
        user = await _create_user(db_session, "504000001")

        response = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        assert response.status_code == 201
        body = response.json()["data"]
        assert body["provider_type"] == "business"
        assert body["display_name"] == "Acme Plumbing"
        assert body["verification_status"] == "pending"
        assert body["is_discoverable"] is False
        assert body["country_code"] == "AE"
        assert body["business_profile"]["address_line"] == "Shop 4, Al Wasl Road"
        assert body["business_profile"]["delivery_radius_meters"] == 5000
        assert body["business_profile"]["trade_license_number"] == "TL-12345"
        assert body["freelancer_profile"] is None
        assert body["slug"]

        result = await db_session.execute(
            select(Provider).where(Provider.id == uuid.UUID(body["id"]))
        )
        provider = result.scalar_one()
        assert provider.user_id == user.id

    @pytest.mark.anyio
    async def test_creates_a_freelancer_provider(
        self, client: TestClient, db_session
    ) -> None:
        """AC1/AC2/AC4/AC6/AC7: happy path, Freelancer subtype."""
        user = await _create_user(db_session, "504000002")

        response = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_freelancer_payload(),
        )

        assert response.status_code == 201
        body = response.json()["data"]
        assert body["provider_type"] == "freelancer"
        assert body["verification_status"] == "pending"
        assert body["is_discoverable"] is False
        assert body["business_profile"] is None
        assert body["freelancer_profile"]["service_radius_meters"] == 8000
        assert body["freelancer_profile"]["skills"] == ["Plumbing", "AC Repair"]
        assert body["freelancer_profile"]["years_experience"] == 5

        result = await db_session.execute(
            select(Provider).where(Provider.id == uuid.UUID(body["id"]))
        )
        provider = result.scalar_one()
        assert provider.user_id == user.id

    @pytest.mark.anyio
    async def test_second_create_for_the_same_caller_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        """AC8: one Provider per Account, enforced end-to-end."""
        user = await _create_user(db_session, "504000003")
        first = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_freelancer_payload(),
        )

        assert second.status_code == 409

    @pytest.mark.anyio
    async def test_creating_a_provider_grants_role_provider(
        self, client: TestClient, db_session
    ) -> None:
        """Decision 1: `POST /providers/me` grants `ROLE_PROVIDER` to
        the caller's Account, alongside their existing `ROLE_CUSTOMER`."""
        await seed_roles(db_session)
        await db_session.commit()
        user = await _create_user(db_session, "504000004")

        response = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        assert response.status_code == 201

        result = await db_session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        role_names = set(result.scalars().all())
        assert ROLE_PROVIDER in role_names

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.post("/api/v1/providers/me", json=_business_payload())
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_business_type_with_freelancer_details_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        """Schema cross-validation: `provider_type` must match whichever
        subtype details object is present."""
        user = await _create_user(db_session, "504000005")
        payload = _business_payload()
        payload["freelancer_details"] = _freelancer_payload()["freelancer_details"]

        response = client.post(
            "/api/v1/providers/me", headers=_auth_headers(user.id), json=payload
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_business_type_with_no_details_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "504000006")
        payload = _business_payload()
        del payload["business_details"]

        response = client.post(
            "/api/v1/providers/me", headers=_auth_headers(user.id), json=payload
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_freelancer_type_with_business_details_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "504000007")
        payload = _freelancer_payload()
        payload["business_details"] = _business_payload()["business_details"]

        response = client.post(
            "/api/v1/providers/me", headers=_auth_headers(user.id), json=payload
        )

        assert response.status_code == 422


class TestGetMyProvider:
    @pytest.mark.anyio
    async def test_returns_404_before_creation(
        self, client: TestClient, db_session
    ) -> None:
        """Decision 9: a caller with no Provider yet gets a plain 404."""
        user = await _create_user(db_session, "504000010")

        response = client.get("/api/v1/providers/me", headers=_auth_headers(user.id))

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_200_with_the_created_provider_after_creation(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "504000011")
        created = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        ).json()["data"]

        response = client.get("/api/v1/providers/me", headers=_auth_headers(user.id))

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["id"] == created["id"]
        assert body["business_profile"]["address_line"] == "Shop 4, Al Wasl Road"

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/providers/me")
        assert response.status_code == 401


class TestSlugUniqueness:
    @pytest.mark.anyio
    async def test_two_providers_with_the_same_display_name_get_unique_slugs(
        self, client: TestClient, db_session
    ) -> None:
        user_a = await _create_user(db_session, "504000020")
        user_b = await _create_user(db_session, "504000021")

        response_a = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user_a.id),
            json=_business_payload(display_name="Acme Plumbing"),
        )
        response_b = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user_b.id),
            json=_business_payload(display_name="Acme Plumbing"),
        )

        assert response_a.status_code == 201
        assert response_b.status_code == 201
        slug_a = response_a.json()["data"]["slug"]
        slug_b = response_b.json()["data"]["slug"]
        assert slug_a != slug_b


class TestUpdateMyProvider:
    """`PATCH /providers/me` (PRO-002, AC5)."""

    @pytest.mark.anyio
    async def test_partial_update_of_basic_info(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "508000001")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={"display_name": "Acme Plumbing & AC"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["display_name"] == "Acme Plumbing & AC"
        # AC6: verification fields untouched by this endpoint.
        assert body["verification_status"] == "pending"
        assert body["is_discoverable"] is False

    @pytest.mark.anyio
    async def test_category_labels_round_trip(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "508000002")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={
                "category_labels": [
                    {"label": "Plumbing", "is_primary": True},
                    {"label": "AC Repair", "is_primary": False},
                ]
            },
        )

        assert response.status_code == 200
        labels = response.json()["data"]["category_labels"]
        assert {label["label"] for label in labels} == {"Plumbing", "AC Repair"}
        primaries = [label for label in labels if label["is_primary"]]
        assert len(primaries) == 1

    @pytest.mark.anyio
    async def test_category_labels_with_no_primary_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "508000003")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={"category_labels": [{"label": "Plumbing", "is_primary": False}]},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_business_details_operating_hours_update_persists(
        self, client: TestClient, db_session
    ) -> None:
        """Regression guard: `exclude_unset` recursion through the nested
        `operating_hours` dict must land as plain JSONB-ready data, not
        raw pydantic model instances."""
        user = await _create_user(db_session, "508000006")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={
                "business_details": {
                    "operating_hours": {
                        "monday": {"open": "08:00", "close": "17:00"},
                        "sunday": None,
                    }
                }
            },
        )

        assert response.status_code == 200
        hours = response.json()["data"]["business_profile"]["operating_hours"]
        assert hours["monday"] == {"open": "08:00", "close": "17:00"}
        assert hours["sunday"] is None

    @pytest.mark.anyio
    async def test_editing_freelancer_details_on_a_business_provider_returns_400(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "508000004")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={"freelancer_details": {"years_experience": 5}},
        )

        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_returns_404_for_a_caller_with_no_provider(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "508000005")

        response = client.patch(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json={"display_name": "X"},
        )

        assert response.status_code == 404

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.patch("/api/v1/providers/me", json={"display_name": "X"})
        assert response.status_code == 401


class TestPortfolioEndpoints:
    """`GET`/`POST /providers/me/portfolio`, `DELETE
    /providers/me/portfolio/{id}`, `PUT /providers/me/portfolio/order`
    (PRO-002, AC2/AC7/AC8)."""

    @pytest.mark.anyio
    async def test_list_is_empty_before_any_upload(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "509000001")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.get(
            "/api/v1/providers/me/portfolio", headers=_auth_headers(user.id)
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.anyio
    async def test_upload_list_and_delete_round_trip(
        self, client: TestClient, db_session
    ) -> None:
        """A real, small in-memory multipart upload (AC2)."""
        user = await _create_user(db_session, "509000002")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        upload_response = client.post(
            "/api/v1/providers/me/portfolio",
            headers=_auth_headers(user.id),
            files={"file": ("my-photo.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"caption": "Recent job"},
        )
        assert upload_response.status_code == 201
        photo = upload_response.json()["data"]
        assert photo["caption"] == "Recent job"
        assert "my-photo" not in photo["media_url"]
        assert photo["media_url"].startswith("/media/portfolios/")

        list_response = client.get(
            "/api/v1/providers/me/portfolio", headers=_auth_headers(user.id)
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["data"]) == 1

        delete_response = client.delete(
            f"/api/v1/providers/me/portfolio/{photo['id']}",
            headers=_auth_headers(user.id),
        )
        assert delete_response.status_code == 200

        list_after_delete = client.get(
            "/api/v1/providers/me/portfolio", headers=_auth_headers(user.id)
        )
        assert list_after_delete.json()["data"] == []

    @pytest.mark.anyio
    async def test_upload_with_invalid_content_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "509000003")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.post(
            "/api/v1/providers/me/portfolio",
            headers=_auth_headers(user.id),
            files={"file": ("fake.jpg", b"not a real image" * 4, "image/jpeg")},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_reorder_persists(self, client: TestClient, db_session) -> None:
        user = await _create_user(db_session, "509000004")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        ids = []
        for _ in range(3):
            upload_response = client.post(
                "/api/v1/providers/me/portfolio",
                headers=_auth_headers(user.id),
                files={"file": ("photo.jpg", _JPEG_BYTES, "image/jpeg")},
            )
            ids.append(upload_response.json()["data"]["id"])

        new_order = [ids[2], ids[0], ids[1]]
        reorder_response = client.put(
            "/api/v1/providers/me/portfolio/order",
            headers=_auth_headers(user.id),
            json={"ordered_ids": new_order},
        )
        assert reorder_response.status_code == 200

        list_response = client.get(
            "/api/v1/providers/me/portfolio", headers=_auth_headers(user.id)
        )
        refetched_ids = [photo["id"] for photo in list_response.json()["data"]]
        assert refetched_ids == new_order

    @pytest.mark.anyio
    async def test_reorder_with_a_mismatched_id_set_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "509000005")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        client.post(
            "/api/v1/providers/me/portfolio",
            headers=_auth_headers(user.id),
            files={"file": ("photo.jpg", _JPEG_BYTES, "image/jpeg")},
        )

        response = client.put(
            "/api/v1/providers/me/portfolio/order",
            headers=_auth_headers(user.id),
            json={"ordered_ids": [str(uuid.uuid4())]},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_a_second_provider_cannot_delete_the_first_providers_photo(
        self, client: TestClient, db_session
    ) -> None:
        """AC7/AC8: ownership enforced -- a 404, never a 200."""
        owner = await _create_user(db_session, "509000006")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(owner.id),
            json=_business_payload(),
        )
        other = await _create_user(db_session, "509000007")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(other.id),
            json=_freelancer_payload(),
        )
        upload_response = client.post(
            "/api/v1/providers/me/portfolio",
            headers=_auth_headers(owner.id),
            files={"file": ("photo.jpg", _JPEG_BYTES, "image/jpeg")},
        )
        photo_id = upload_response.json()["data"]["id"]

        response = client.delete(
            f"/api/v1/providers/me/portfolio/{photo_id}",
            headers=_auth_headers(other.id),
        )

        assert response.status_code == 404

    def test_endpoints_return_401_without_a_token(self, client: TestClient) -> None:
        assert client.get("/api/v1/providers/me/portfolio").status_code == 401
        assert client.post("/api/v1/providers/me/portfolio").status_code == 401
        assert (
            client.delete(f"/api/v1/providers/me/portfolio/{uuid.uuid4()}").status_code
            == 401
        )
        assert (
            client.put(
                "/api/v1/providers/me/portfolio/order", json={"ordered_ids": []}
            ).status_code
            == 401
        )


class TestAvailabilityEndpoints:
    """`GET`/`PUT /providers/me/availability` (PRO-002, AC3)."""

    @pytest.mark.anyio
    async def test_get_before_any_put_returns_seven_synthesized_entries(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "510000001")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.get(
            "/api/v1/providers/me/availability", headers=_auth_headers(user.id)
        )

        assert response.status_code == 200
        entries = response.json()["data"]
        assert len(entries) == 7
        assert all(entry["is_open"] is False for entry in entries)

    @pytest.mark.anyio
    async def test_put_persists_hours_and_emergency_flag(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "510000002")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.put(
            "/api/v1/providers/me/availability",
            headers=_auth_headers(user.id),
            json={
                "entries": [
                    {
                        "weekday": "monday",
                        "is_open": True,
                        "open_time": "09:00",
                        "close_time": "18:00",
                        "is_emergency_available": True,
                    },
                    {
                        "weekday": "sunday",
                        "is_open": False,
                        "open_time": None,
                        "close_time": None,
                        "is_emergency_available": False,
                    },
                ]
            },
        )

        assert response.status_code == 200
        entries = {entry["weekday"]: entry for entry in response.json()["data"]}
        assert entries["monday"]["is_open"] is True
        assert entries["monday"]["open_time"] == "09:00"
        assert entries["monday"]["close_time"] == "18:00"
        assert entries["monday"]["is_emergency_available"] is True
        assert entries["sunday"]["is_open"] is False
        assert entries["sunday"]["open_time"] is None

        get_response = client.get(
            "/api/v1/providers/me/availability", headers=_auth_headers(user.id)
        )
        refetched = {entry["weekday"]: entry for entry in get_response.json()["data"]}
        assert refetched["monday"]["open_time"] == "09:00"

    @pytest.mark.anyio
    async def test_is_open_true_without_times_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "510000003")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.put(
            "/api/v1/providers/me/availability",
            headers=_auth_headers(user.id),
            json={"entries": [{"weekday": "monday", "is_open": True}]},
        )

        assert response.status_code == 422

    def test_endpoints_return_401_without_a_token(self, client: TestClient) -> None:
        assert client.get("/api/v1/providers/me/availability").status_code == 401
        assert (
            client.put(
                "/api/v1/providers/me/availability", json={"entries": []}
            ).status_code
            == 401
        )
