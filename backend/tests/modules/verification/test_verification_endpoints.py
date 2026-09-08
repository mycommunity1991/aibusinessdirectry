"""
End-to-end integration tests for `/api/v1/providers/me/verification` and
its sub-resources (VER-001).

Mirrors `test_provider_endpoints.py`'s pattern: real Postgres via
`db_session`, `get_db` overridden so the FastAPI app and the test share
one transaction, and access tokens minted directly against a real
`identity.users` row. `get_verification_file_storage` is overridden to a
per-test temporary directory (Decision 7: a **private** `LocalFileStorage`,
distinct from `get_file_storage`, which stays wired to `/media`).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.verification.dependencies import get_verification_file_storage
from app.shared.storage.local_file_storage import LocalFileStorage

PHONE_COUNTRY_CODE = "+971"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PDF_BYTES = b"%PDF-1.4\n" + b"\x00" * 32


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client(db_session, tmp_path):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_verification_file_storage] = lambda: LocalFileStorage(
        base_directory=str(tmp_path), public_url_prefix=None
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
            "delivery_radius_meters": 5000,
            "trade_license_number": "TL-12345",
        },
    }
    payload.update(overrides)
    return payload


def _create_provider(client: TestClient, user_id: uuid.UUID, **overrides) -> dict:
    response = client.post(
        "/api/v1/providers/me",
        headers=_auth_headers(user_id),
        json=_freelancer_payload(**overrides),
    )
    assert response.status_code == 201
    return response.json()["data"]


class TestPreviewEndpoint:
    @pytest.mark.anyio
    async def test_preview_a_real_multipart_upload_returns_empty_stub_fields(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "701000001")
        _create_provider(client, user.id)

        response = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["document_type"] == "emirates_id"
        assert body["full_name"] is None
        assert body["id_number"] is None
        assert body["confidence"] == 0.0

    @pytest.mark.anyio
    async def test_preview_with_invalid_content_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "701000002")
        _create_provider(client, user.id)

        response = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("fake.jpg", b"not a real image" * 4, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )

        assert response.status_code == 422

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        assert response.status_code == 401


class TestSubmitAndGetStatus:
    @pytest.mark.anyio
    async def test_full_round_trip_freelancer_preview_then_submit_then_get(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000001")
        _create_provider(client, user.id)

        preview_response = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        assert preview_response.status_code == 200

        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={
                "document_type": "emirates_id",
                "confirmed_fields": {
                    "full_name": "Jane Doe",
                    "id_number": "784-1111-1111111-1",
                },
            },
        )
        assert submit_response.status_code == 201
        submitted = submit_response.json()["data"]
        assert submitted["status"] == "pending"
        assert submitted["verification_type"] == "freelancer_id"
        assert len(submitted["documents"]) == 1
        document = submitted["documents"][0]
        assert document["ocr_extracted_data"]["full_name"] == "Jane Doe"
        assert document["file_download_url"].startswith(
            "/api/v1/providers/me/verification/documents/"
        )

        get_response = client.get(
            "/api/v1/providers/me/verification", headers=_auth_headers(user.id)
        )
        assert get_response.status_code == 200
        assert get_response.json()["data"]["id"] == submitted["id"]

    @pytest.mark.anyio
    async def test_business_with_a_pdf_trade_license_round_trips(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000002")
        response = client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        assert response.status_code == 201

        preview_response = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("trade-license.pdf", _PDF_BYTES, "application/pdf")},
            data={"document_type": "trade_license"},
        )
        assert preview_response.status_code == 200

        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={"document_type": "trade_license", "confirmed_fields": {}},
        )
        assert submit_response.status_code == 201
        assert submit_response.json()["data"]["verification_type"] == (
            "business_lightweight"
        )

    @pytest.mark.anyio
    async def test_business_with_no_document_succeeds(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000003")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={},
        )

        assert response.status_code == 201
        assert response.json()["data"]["documents"] == []

    @pytest.mark.anyio
    async def test_freelancer_without_a_document_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000004")
        _create_provider(client, user.id)

        response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_second_submit_while_pending_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000005")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )
        first = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={},
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={},
        )

        assert second.status_code == 409

    @pytest.mark.anyio
    async def test_get_before_any_submission_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "702000006")
        _create_provider(client, user.id)

        response = client.get(
            "/api/v1/providers/me/verification", headers=_auth_headers(user.id)
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_stray_status_field_in_submit_payload_is_ignored(
        self, client: TestClient, db_session
    ) -> None:
        """AC6: no route accepts a `status`/`reviewed_*` field at all --
        a stray one in the request body has no effect whatsoever."""
        user = await _create_user(db_session, "702000007")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(user.id),
            json=_business_payload(),
        )

        response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={"status": "approved", "reviewed_at": "2020-01-01T00:00:00Z"},
        )

        assert response.status_code == 201
        assert response.json()["data"]["status"] == "pending"

    def test_endpoints_return_401_without_a_token(self, client: TestClient) -> None:
        assert (
            client.post("/api/v1/providers/me/verification", json={}).status_code == 401
        )
        assert client.get("/api/v1/providers/me/verification").status_code == 401


class TestDocumentDownloadAndOwnership:
    @pytest.mark.anyio
    async def test_owner_can_download_their_own_document(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000001")
        _create_provider(client, user.id)
        client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={"document_type": "emirates_id", "confirmed_fields": {}},
        )
        document_id = submit_response.json()["data"]["documents"][0]["id"]

        response = client.get(
            f"/api/v1/providers/me/verification/documents/{document_id}/file",
            headers=_auth_headers(user.id),
        )

        assert response.status_code == 200
        assert response.content == _JPEG_BYTES
        assert response.headers["content-type"] == "image/jpeg"

    @pytest.mark.anyio
    async def test_a_second_provider_cannot_get_the_first_providers_status(
        self, client: TestClient, db_session
    ) -> None:
        owner = await _create_user(db_session, "703000002")
        client.post(
            "/api/v1/providers/me",
            headers=_auth_headers(owner.id),
            json=_business_payload(),
        )
        client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(owner.id),
            json={},
        )
        other = await _create_user(db_session, "703000003")
        _create_provider(client, other.id, display_name="Someone Else")

        response = client.get(
            "/api/v1/providers/me/verification", headers=_auth_headers(other.id)
        )

        # The second provider has no verification record of their own --
        # never the first provider's.
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_a_second_provider_cannot_download_the_first_providers_document(
        self, client: TestClient, db_session
    ) -> None:
        owner = await _create_user(db_session, "703000004")
        _create_provider(client, owner.id)
        client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(owner.id),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(owner.id),
            json={"document_type": "emirates_id", "confirmed_fields": {}},
        )
        document_id = submit_response.json()["data"]["documents"][0]["id"]

        other = await _create_user(db_session, "703000005")
        _create_provider(client, other.id, display_name="Someone Else")

        response = client.get(
            f"/api/v1/providers/me/verification/documents/{document_id}/file",
            headers=_auth_headers(other.id),
        )

        assert response.status_code == 404

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get(
            f"/api/v1/providers/me/verification/documents/{uuid.uuid4()}/file"
        )
        assert response.status_code == 401


class TestNeverReachableViaThePublicMediaMount:
    @pytest.mark.anyio
    async def test_the_public_media_mount_never_serves_a_verification_document(
        self, client: TestClient, db_session
    ) -> None:
        """
        The single most important guarantee of Decision 7: even a
        correctly-guessed `/media/verification/...`-shaped path 404s,
        since a verification document is never written under the public
        `UPLOAD_DIR`/`/media` mount at all -- it lives in a completely
        separate, never-mounted private root.
        """
        user = await _create_user(db_session, "704000001")
        _create_provider(client, user.id)
        client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_auth_headers(user.id),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_auth_headers(user.id),
            json={"document_type": "emirates_id", "confirmed_fields": {}},
        )
        record = submit_response.json()["data"]
        document_id = record["documents"][0]["id"]
        provider = client.get(
            "/api/v1/providers/me", headers=_auth_headers(user.id)
        ).json()["data"]

        # No file_url/media path is ever exposed to the client at all --
        # only the authenticated `file_download_url`. Guessing the
        # shape PortfolioService would have used for an equivalent
        # public file must still 404.
        guessed_paths = [
            f"/media/verification/{provider['id']}/{record['id']}/{document_id}.jpg",
            f"/media/pending/{provider['id']}.jpg",
        ]
        for path in guessed_paths:
            response = client.get(path)
            assert response.status_code == 404
