"""
End-to-end integration tests for `/api/v1/admin/unmatched-query-reports/*`
(ADM-001, Decision 6/7/8, `Plan_S11_ADM-001.md`) -- mirrors
`test_admin_claim_api.py`'s real-Postgres, real-app-DI pattern.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)

PHONE_COUNTRY_CODE = "+971"


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


async def _create_report(db_session, *, status: str = "open", result_count: int = 0):
    """Builds a real `unmatched_query_reports` row (plus its underlying
    `search_event_log` row) directly through the real repositories --
    mirrors `test_search_request_api.py`'s "build state directly through
    the real service, not the HTTP layer" convention."""
    log = await SearchEventLogRepository(db_session).create(
        {
            "search_request_id": None,
            "customer_id": None,
            "category_id": None,
            "query_text": None,
            "result_count": result_count,
            "was_matched": False,
        }
    )
    report = await UnmatchedQueryReportRepository(db_session).create(
        {"search_event_log_id": log.id, "status": status}
    )
    await db_session.commit()
    return report, log


class TestAdminUnmatchedQueryReportAuthorization:
    def test_list_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/admin/unmatched-query-reports")
        assert response.status_code == 401

    async def test_list_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "950000001")

        response = client.get(
            "/api/v1/admin/unmatched-query-reports",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403

    async def test_review_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "950000002")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{uuid.uuid4()}/review",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
            json={},
        )

        assert response.status_code == 403

    async def test_action_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "950000003")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{uuid.uuid4()}/action",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
            json={},
        )

        assert response.status_code == 403


class TestListUnmatchedQueryReports:
    async def test_default_status_filter_returns_only_open(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000010")
        open_report, _log = await _create_report(db_session, status="open")
        await _create_report(db_session, status="actioned")

        response = client.get(
            "/api/v1/admin/unmatched-query-reports",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["id"] == str(open_report.id)
        assert body["data"][0]["status"] == "open"

    async def test_status_all_returns_every_status(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000011")
        await _create_report(db_session, status="open")
        await _create_report(db_session, status="actioned")

        response = client.get(
            "/api/v1/admin/unmatched-query-reports?status=all",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        assert response.json()["pagination"]["total_items"] == 2

    async def test_sort_orders(self, client: TestClient, db_session) -> None:
        admin = await _create_user(db_session, "950000012")
        first, _log_a = await _create_report(db_session, status="open")
        second, _log_b = await _create_report(db_session, status="open")

        asc_response = client.get(
            "/api/v1/admin/unmatched-query-reports?sort=created_at_asc",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )
        desc_response = client.get(
            "/api/v1/admin/unmatched-query-reports?sort=created_at_desc",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert [item["id"] for item in asc_response.json()["data"]] == [
            str(first.id),
            str(second.id),
        ]
        assert [item["id"] for item in desc_response.json()["data"]] == [
            str(second.id),
            str(first.id),
        ]

    async def test_row_is_enriched_with_search_event_log_context(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000013")
        report, log = await _create_report(db_session, status="open", result_count=0)

        response = client.get(
            "/api/v1/admin/unmatched-query-reports",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        row = response.json()["data"][0]
        assert row["search_event_log_id"] == str(log.id)
        assert row["result_count"] == 0
        assert row["query_text"] is None


class TestMarkReviewed:
    async def test_open_report_is_marked_reviewed(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000020")
        report, _log = await _create_report(db_session, status="open")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{report.id}/review",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"category_gap_notes": "No plumbers in this area."},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "reviewed"
        assert body["reviewed_by"] == str(admin.id)
        assert body["reviewed_at"] is not None
        assert body["category_gap_notes"] == "No plumbers in this area."

    async def test_a_nonexistent_report_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000021")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{uuid.uuid4()}/review",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 404

    async def test_an_already_reviewed_report_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000022")
        report, _log = await _create_report(db_session, status="reviewed")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{report.id}/review",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 409


class TestMarkActioned:
    async def test_open_report_is_marked_actioned(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000030")
        report, _log = await _create_report(db_session, status="open")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{report.id}/action",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "actioned"

    async def test_reviewed_report_can_be_actioned(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000031")
        report, _log = await _create_report(db_session, status="reviewed")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{report.id}/action",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "actioned"

    async def test_an_already_actioned_report_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000032")
        report, _log = await _create_report(db_session, status="actioned")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{report.id}/action",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 409

    async def test_a_nonexistent_report_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "950000033")

        response = client.post(
            f"/api/v1/admin/unmatched-query-reports/{uuid.uuid4()}/action",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={},
        )

        assert response.status_code == 404
