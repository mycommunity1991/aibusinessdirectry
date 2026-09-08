"""
End-to-end integration tests for `/api/v1/admin/verification/*` (VER-002).

Mirrors `test_verification_endpoints.py`'s pattern: real Postgres via
`db_session`, `get_db` overridden so the FastAPI app and the test share
one transaction, and access tokens minted directly with an explicit
`roles` claim (no DB role-grant needed -- `require_role` only inspects
the JWT's own `roles` claim).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.verification.dependencies import get_verification_file_storage
from app.shared.storage.local_file_storage import LocalFileStorage

PHONE_COUNTRY_CODE = "+971"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


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


def _token_for(user_id: uuid.UUID, roles: list[str]) -> str:
    return create_access_token(subject=str(user_id), roles=roles, jti=str(uuid.uuid4()))


def _headers(user_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id, roles)}"}


def _admin_headers(user_id: uuid.UUID) -> dict[str, str]:
    return _headers(user_id, [ROLE_ADMIN])


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


def _create_provider(
    client: TestClient, user_id: uuid.UUID, phone_number: str, **overrides
) -> dict:
    response = client.post(
        "/api/v1/providers/me",
        headers=_headers(user_id, [ROLE_CUSTOMER]),
        json=_freelancer_payload(phone_number=phone_number, **overrides),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _submit_pending_verification(
    client: TestClient, provider_user_id: uuid.UUID, *, with_document: bool = True
) -> str:
    """Submits a Freelancer verification cycle for `provider_user_id`
    and returns the new `verification_records.id`."""
    if with_document:
        preview = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_headers(provider_user_id, [ROLE_PROVIDER]),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        assert preview.status_code == 200
        submit_body = {"document_type": "emirates_id", "confirmed_fields": {}}
    else:
        submit_body = {}

    submit = client.post(
        "/api/v1/providers/me/verification",
        headers=_headers(provider_user_id, [ROLE_PROVIDER]),
        json=submit_body,
    )
    assert submit.status_code == 201
    return submit.json()["data"]["id"]


class TestAuthorizationMatrix:
    """AC7: 401 without a token; 403 for a validly authenticated but
    non-admin caller; 200/201 for `ROLE_ADMIN`, on all four new routes."""

    async def test_list_records_matrix(self, client: TestClient, db_session) -> None:
        user = await _create_user(db_session, "1101000001")

        assert client.get("/api/v1/admin/verification/records").status_code == 401
        assert (
            client.get(
                "/api/v1/admin/verification/records",
                headers=_headers(user.id, [ROLE_CUSTOMER]),
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/admin/verification/records",
                headers=_headers(user.id, [ROLE_PROVIDER]),
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/admin/verification/records",
                headers=_admin_headers(user.id),
            ).status_code
            == 200
        )

    async def test_approve_matrix(self, client: TestClient, db_session) -> None:
        provider_owner = await _create_user(db_session, "1101000002")
        admin_and_others = await _create_user(db_session, "1101000003")
        _create_provider(client, provider_owner.id, "509000001")
        record_id = _submit_pending_verification(client, provider_owner.id)
        url = f"/api/v1/admin/verification/records/{record_id}/approve"

        assert client.post(url).status_code == 401
        assert (
            client.post(
                url, headers=_headers(admin_and_others.id, [ROLE_CUSTOMER])
            ).status_code
            == 403
        )
        assert (
            client.post(
                url, headers=_headers(admin_and_others.id, [ROLE_PROVIDER])
            ).status_code
            == 403
        )
        assert (
            client.post(url, headers=_admin_headers(admin_and_others.id)).status_code
            == 200
        )

    async def test_reject_matrix(self, client: TestClient, db_session) -> None:
        provider_owner = await _create_user(db_session, "1101000004")
        admin_and_others = await _create_user(db_session, "1101000005")
        _create_provider(client, provider_owner.id, "509000002")
        record_id = _submit_pending_verification(client, provider_owner.id)
        url = f"/api/v1/admin/verification/records/{record_id}/reject"
        body = {"rejection_reason": "Blurry photo."}

        assert client.post(url, json=body).status_code == 401
        assert (
            client.post(
                url, json=body, headers=_headers(admin_and_others.id, [ROLE_CUSTOMER])
            ).status_code
            == 403
        )
        assert (
            client.post(
                url, json=body, headers=_headers(admin_and_others.id, [ROLE_PROVIDER])
            ).status_code
            == 403
        )
        assert (
            client.post(
                url, json=body, headers=_admin_headers(admin_and_others.id)
            ).status_code
            == 200
        )

    async def test_document_download_matrix(
        self, client: TestClient, db_session
    ) -> None:
        provider_owner = await _create_user(db_session, "1101000006")
        admin_and_others = await _create_user(db_session, "1101000007")
        _create_provider(client, provider_owner.id, "509000003")
        submit = client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_headers(provider_owner.id, [ROLE_PROVIDER]),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        assert submit.status_code == 200
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_headers(provider_owner.id, [ROLE_PROVIDER]),
            json={"document_type": "emirates_id", "confirmed_fields": {}},
        )
        document_id = submit_response.json()["data"]["documents"][0]["id"]
        url = f"/api/v1/admin/verification/documents/{document_id}/file"

        assert client.get(url).status_code == 401
        assert (
            client.get(
                url, headers=_headers(admin_and_others.id, [ROLE_CUSTOMER])
            ).status_code
            == 403
        )
        assert (
            client.get(
                url, headers=_headers(admin_and_others.id, [ROLE_PROVIDER])
            ).status_code
            == 403
        )
        response = client.get(url, headers=_admin_headers(admin_and_others.id))
        assert response.status_code == 200
        assert response.content == _JPEG_BYTES


class TestListRecordsPaginationAndFiltering:
    async def test_only_pending_and_under_review_records_are_listed(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1102000001")
        approved_owner = await _create_user(db_session, "1102000002")
        pending_owner = await _create_user(db_session, "1102000003")
        _create_provider(client, approved_owner.id, "509100001")
        approved_record_id = _submit_pending_verification(client, approved_owner.id)
        client.post(
            f"/api/v1/admin/verification/records/{approved_record_id}/approve",
            headers=_admin_headers(admin.id),
        )
        _create_provider(client, pending_owner.id, "509100002")
        pending_record_id = _submit_pending_verification(client, pending_owner.id)

        response = client.get(
            "/api/v1/admin/verification/records", headers=_admin_headers(admin.id)
        )

        assert response.status_code == 200
        body = response.json()
        ids = [record["id"] for record in body["data"]]
        assert pending_record_id in ids
        assert approved_record_id not in ids

    async def test_pagination_metadata_is_correct_across_multiple_pages(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1102000004")
        for i in range(5):
            owner = await _create_user(db_session, f"51020{i:05d}")
            _create_provider(client, owner.id, f"50920{i:04d}")
            _submit_pending_verification(client, owner.id)

        page_one = client.get(
            "/api/v1/admin/verification/records",
            params={"page": 1, "page_size": 2},
            headers=_admin_headers(admin.id),
        ).json()
        page_two = client.get(
            "/api/v1/admin/verification/records",
            params={"page": 2, "page_size": 2},
            headers=_admin_headers(admin.id),
        ).json()
        page_three = client.get(
            "/api/v1/admin/verification/records",
            params={"page": 3, "page_size": 2},
            headers=_admin_headers(admin.id),
        ).json()

        assert page_one["pagination"]["total_items"] == 5
        assert page_one["pagination"]["total_pages"] == 3
        assert len(page_one["data"]) == 2
        assert len(page_two["data"]) == 2
        assert len(page_three["data"]) == 1

        all_ids = {r["id"] for r in page_one["data"]}
        all_ids.update(r["id"] for r in page_two["data"])
        all_ids.update(r["id"] for r in page_three["data"])
        assert len(all_ids) == 5

    async def test_document_download_url_points_at_the_admin_route(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1102000005")
        owner = await _create_user(db_session, "1102000006")
        _create_provider(client, owner.id, "509100099")
        _submit_pending_verification(client, owner.id)

        response = client.get(
            "/api/v1/admin/verification/records", headers=_admin_headers(admin.id)
        )

        record = response.json()["data"][0]
        assert record["documents"][0]["file_download_url"].startswith(
            "/api/v1/admin/verification/documents/"
        )
        assert record["provider_id"]
        assert record["provider_display_name"] == "Jane the Plumber"
        assert record["provider_type"] == "freelancer"


class TestApproveAndRejectHttpFlows:
    async def test_approve_flow_reflects_in_the_providers_own_status_view(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1103000001")
        owner = await _create_user(db_session, "1103000002")
        _create_provider(client, owner.id, "509200001")
        record_id = _submit_pending_verification(client, owner.id)

        approve_response = client.post(
            f"/api/v1/admin/verification/records/{record_id}/approve",
            headers=_admin_headers(admin.id),
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["data"]["status"] == "approved"

        status_response = client.get(
            "/api/v1/providers/me/verification",
            headers=_headers(owner.id, [ROLE_PROVIDER]),
        )
        assert status_response.json()["data"]["status"] == "approved"

    async def test_reject_flow_reflects_in_the_providers_own_status_view(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1103000003")
        owner = await _create_user(db_session, "1103000004")
        _create_provider(client, owner.id, "509200002")
        record_id = _submit_pending_verification(client, owner.id)

        reject_response = client.post(
            f"/api/v1/admin/verification/records/{record_id}/reject",
            headers=_admin_headers(admin.id),
            json={"rejection_reason": "Illegible document."},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["data"]["status"] == "rejected"
        assert (
            reject_response.json()["data"]["rejection_reason"] == "Illegible document."
        )

        status_response = client.get(
            "/api/v1/providers/me/verification",
            headers=_headers(owner.id, [ROLE_PROVIDER]),
        )
        assert status_response.json()["data"]["status"] == "rejected"

    async def test_reject_without_a_reason_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1103000005")
        owner = await _create_user(db_session, "1103000006")
        _create_provider(client, owner.id, "509200003")
        record_id = _submit_pending_verification(client, owner.id)

        response = client.post(
            f"/api/v1/admin/verification/records/{record_id}/reject",
            headers=_admin_headers(admin.id),
            json={"rejection_reason": ""},
        )

        assert response.status_code == 422

    async def test_second_approve_on_the_same_record_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1103000007")
        owner = await _create_user(db_session, "1103000008")
        _create_provider(client, owner.id, "509200004")
        record_id = _submit_pending_verification(client, owner.id)
        first = client.post(
            f"/api/v1/admin/verification/records/{record_id}/approve",
            headers=_admin_headers(admin.id),
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/v1/admin/verification/records/{record_id}/approve",
            headers=_admin_headers(admin.id),
        )

        assert second.status_code == 409

    async def test_approving_a_business_provider_makes_it_discoverable(
        self, client: TestClient, db_session
    ) -> None:
        """Decision 5: exercised via the full HTTP round trip, not just
        the service layer."""
        admin = await _create_user(db_session, "1103000009")
        owner = await _create_user(db_session, "1103000010")
        client.post(
            "/api/v1/providers/me",
            headers=_headers(owner.id, [ROLE_CUSTOMER]),
            json=_business_payload(phone_number="509200005"),
        )
        submit = client.post(
            "/api/v1/providers/me/verification",
            headers=_headers(owner.id, [ROLE_PROVIDER]),
            json={},
        )
        record_id = submit.json()["data"]["id"]

        client.post(
            f"/api/v1/admin/verification/records/{record_id}/approve",
            headers=_admin_headers(admin.id),
        )

        provider_response = client.get(
            "/api/v1/providers/me", headers=_headers(owner.id, [ROLE_PROVIDER])
        )
        assert provider_response.json()["data"]["is_discoverable"] is True

    async def test_approving_a_nonexistent_record_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1103000011")

        response = client.post(
            f"/api/v1/admin/verification/records/{uuid.uuid4()}/approve",
            headers=_admin_headers(admin.id),
        )

        assert response.status_code == 404


class TestAdminDocumentDownloadCrossesOwnership:
    async def test_admin_can_download_a_document_belonging_to_a_different_user(
        self, client: TestClient, db_session
    ) -> None:
        """
        Decision 6: a `ROLE_ADMIN` caller genuinely can fetch a document
        belonging to a completely different user's provider. This is
        **correct** behavior, not a bug -- `require_role(ROLE_ADMIN)` is
        this route's entire authorization boundary, with no ownership
        check of any kind.
        """
        admin = await _create_user(db_session, "1104000001")
        stranger_owner = await _create_user(db_session, "1104000002")
        _create_provider(client, stranger_owner.id, "509300001")
        client.post(
            "/api/v1/providers/me/verification/documents/preview",
            headers=_headers(stranger_owner.id, [ROLE_PROVIDER]),
            files={"file": ("emirates-id.jpg", _JPEG_BYTES, "image/jpeg")},
            data={"document_type": "emirates_id"},
        )
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            headers=_headers(stranger_owner.id, [ROLE_PROVIDER]),
            json={"document_type": "emirates_id", "confirmed_fields": {}},
        )
        document_id = submit_response.json()["data"]["documents"][0]["id"]

        response = client.get(
            f"/api/v1/admin/verification/documents/{document_id}/file",
            headers=_admin_headers(admin.id),
        )

        assert response.status_code == 200
        assert response.content == _JPEG_BYTES

    async def test_nonexistent_document_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "1104000003")

        response = client.get(
            f"/api/v1/admin/verification/documents/{uuid.uuid4()}/file",
            headers=_admin_headers(admin.id),
        )

        assert response.status_code == 404
