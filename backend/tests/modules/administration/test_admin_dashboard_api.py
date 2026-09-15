"""
End-to-end integration tests for `/api/v1/admin/dashboard/summary`,
`/api/v1/admin/feature-flags[/{key}]`, and
`/api/v1/admin/system-settings[/{key}]` (ADM-002, `Plan_S11_ADM-002.md`)
-- mirrors `test_unmatched_query_report_api.py`'s real-Postgres,
real-app-DI pattern.

This test's DB schema is created directly from the SQLAlchemy models
(`tests/conftest.py`'s `db_engine` fixture), not by running the real
Alembic migration -- so each test seeds its own `feature_flags`/
`system_settings` row directly through the repository, mirroring
`test_feature_flag_service.py`/`test_system_setting_service.py`'s
identical convention.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.administration.repositories.feature_flag_repository import (
    FeatureFlagRepository,
)
from app.modules.administration.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from app.modules.identity.models import AuthProvider, User

PHONE_COUNTRY_CODE = "+971"
_FLAG_KEY = "manual_matching_force_all"
_SETTING_KEY = "support_contact_email"


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


async def _seed_feature_flag(
    db_session, *, key: str = _FLAG_KEY, is_enabled: bool = False
):
    flag = await FeatureFlagRepository(db_session).create(
        {"key": key, "is_enabled": is_enabled, "description": None}
    )
    await db_session.commit()
    return flag


async def _seed_system_setting(
    db_session, *, key: str = _SETTING_KEY, value: dict | None = None
):
    setting = await SystemSettingRepository(db_session).create(
        {
            "key": key,
            "value": value or {"email": "support@aimarketplace.example"},
            "description": None,
        }
    )
    await db_session.commit()
    return setting


class TestAdminDashboardAuthorization:
    """AC5: 403 for a non-admin caller on every one of the five routes."""

    def test_dashboard_summary_returns_401_without_a_token(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/dashboard/summary")
        assert response.status_code == 401

    async def test_dashboard_summary_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "980000001")

        response = client.get(
            "/api/v1/admin/dashboard/summary",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403

    async def test_list_feature_flags_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "980000002")

        response = client.get(
            "/api/v1/admin/feature-flags",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403

    async def test_toggle_feature_flag_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "980000003")

        response = client.patch(
            f"/api/v1/admin/feature-flags/{_FLAG_KEY}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
            json={"is_enabled": True},
        )

        assert response.status_code == 403

    async def test_list_system_settings_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "980000004")

        response = client.get(
            "/api/v1/admin/system-settings",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403

    async def test_update_system_setting_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "980000005")

        response = client.patch(
            f"/api/v1/admin/system-settings/{_SETTING_KEY}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
            json={"value": {"email": "new@example.com"}},
        )

        assert response.status_code == 403


class TestDashboardSummary:
    async def test_returns_the_three_counts_and_queue_paths(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000010")

        response = client.get(
            "/api/v1/admin/dashboard/summary",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pending_verification_count"] == 0
        assert data["pending_verification_queue_path"] == "/admin/verification/records"
        assert data["pending_manual_match_count"] == 0
        assert (
            data["pending_manual_match_queue_path"] == "/admin/search/manual-matches"
        )
        assert data["open_unmatched_query_report_count"] == 0
        assert (
            data["open_unmatched_query_report_queue_path"]
            == "/admin/unmatched-query-reports"
        )


class TestListFeatureFlags:
    async def test_lists_the_seeded_flag(self, client: TestClient, db_session) -> None:
        admin = await _create_user(db_session, "980000020")
        await _seed_feature_flag(db_session)

        response = client.get(
            "/api/v1/admin/feature-flags",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["key"] == _FLAG_KEY
        assert body["data"][0]["is_enabled"] is False


class TestToggleFeatureFlag:
    async def test_toggle_persists_and_returns_the_updated_row(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000021")
        await _seed_feature_flag(db_session, is_enabled=False)

        response = client.patch(
            f"/api/v1/admin/feature-flags/{_FLAG_KEY}",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"is_enabled": True},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_enabled"] is True

        follow_up = client.get(
            "/api/v1/admin/feature-flags",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )
        assert follow_up.json()["data"][0]["is_enabled"] is True

    async def test_toggle_on_an_unknown_key_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000022")

        response = client.patch(
            "/api/v1/admin/feature-flags/unknown_key",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"is_enabled": True},
        )

        assert response.status_code == 404


class TestListSystemSettings:
    async def test_lists_the_seeded_setting(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000030")
        await _seed_system_setting(db_session)

        response = client.get(
            "/api/v1/admin/system-settings",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["key"] == _SETTING_KEY
        assert body["data"][0]["value"] == {"email": "support@aimarketplace.example"}


class TestUpdateSystemSetting:
    async def test_update_persists_and_returns_the_updated_row(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000031")
        await _seed_system_setting(db_session)

        new_value = {"email": "new-support@aimarketplace.example"}
        response = client.patch(
            f"/api/v1/admin/system-settings/{_SETTING_KEY}",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"value": new_value},
        )

        assert response.status_code == 200
        assert response.json()["data"]["value"] == new_value

    async def test_update_on_an_unknown_key_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await _create_user(db_session, "980000032")

        response = client.patch(
            "/api/v1/admin/system-settings/unknown_key",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"value": {"x": 1}},
        )

        assert response.status_code == 404
