"""
End-to-end integration tests for `GET /notifications`, `GET
/notifications/unread-count`, and `PATCH /notifications/{id}/read`
(`ENG-001`, AC5/AC6, Decision 10, `Plan_S12_ENG-001.md`) -- mirrors
`test_outcome_tag_api.py`'s real-Postgres, real-app-DI pattern.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import AuthProvider, User
from app.modules.notification.models import Notification
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
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


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_notification(
    db_session, user_id: uuid.UUID, *, read: bool = False
) -> Notification:
    notification = await NotificationRepository(db_session).create(
        {
            "user_id": user_id,
            "type": "new_contact_view",
            "title": "You have a new lead",
            "body": "A customer just viewed your contact details.",
            "related_entity_type": "contact_view",
            "related_entity_id": uuid.uuid4(),
            "read_at": datetime.now(UTC) if read else None,
        }
    )
    await db_session.commit()
    return notification


class TestListNotifications:
    @pytest.mark.anyio
    async def test_returns_200_newest_first_with_correct_read_at(
        self, client, db_session
    ) -> None:
        user = await _create_user(db_session, "950000001")
        older = await _create_notification(db_session, user.id)
        # Ensure a distinct `created_at` ordering.
        older.created_at = datetime.now(UTC) - timedelta(minutes=5)
        db_session.add(older)
        await db_session.commit()
        newer = await _create_notification(db_session, user.id, read=True)

        response = client.get(
            "/api/v1/notifications", headers=_headers(user.id, [ROLE_CUSTOMER])
        )

        assert response.status_code == 200
        body = response.json()
        ids = [row["id"] for row in body["data"]]
        assert ids == [str(newer.id), str(older.id)]
        assert body["data"][0]["read_at"] is not None
        assert body["data"][1]["read_at"] is None
        assert body["pagination"]["total_items"] == 2

    @pytest.mark.anyio
    async def test_paginates(self, client, db_session) -> None:
        user = await _create_user(db_session, "950000002")
        for _ in range(3):
            await _create_notification(db_session, user.id)

        response = client.get(
            "/api/v1/notifications?page=1&page_size=2",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 2
        assert body["pagination"]["total_items"] == 3
        assert body["pagination"]["total_pages"] == 2

    @pytest.mark.anyio
    async def test_returns_401_for_an_unauthenticated_caller(self, client) -> None:
        response = client.get("/api/v1/notifications")
        assert response.status_code == 401


class TestUnreadCount:
    @pytest.mark.anyio
    async def test_returns_200_matching_the_known_unread_count(
        self, client, db_session
    ) -> None:
        user = await _create_user(db_session, "950000003")
        await _create_notification(db_session, user.id, read=False)
        await _create_notification(db_session, user.id, read=False)
        await _create_notification(db_session, user.id, read=True)

        response = client.get(
            "/api/v1/notifications/unread-count",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    @pytest.mark.anyio
    async def test_returns_401_for_an_unauthenticated_caller(self, client) -> None:
        response = client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 401


class TestMarkNotificationRead:
    @pytest.mark.anyio
    async def test_returns_200_and_persists_read_at(self, client, db_session) -> None:
        user = await _create_user(db_session, "950000004")
        notification = await _create_notification(db_session, user.id)

        response = client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        assert response.json()["data"]["read_at"] is not None

        await db_session.refresh(notification)
        assert notification.read_at is not None

    @pytest.mark.anyio
    async def test_is_idempotent_on_a_second_call(self, client, db_session) -> None:
        user = await _create_user(db_session, "950000005")
        notification = await _create_notification(db_session, user.id)

        first = client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )
        second = client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["read_at"] == second.json()["data"]["read_at"]

    @pytest.mark.anyio
    async def test_returns_404_never_403_for_another_users_notification(
        self, client, db_session
    ) -> None:
        owner = await _create_user(db_session, "950000006")
        other = await _create_user(db_session, "950000007")
        notification = await _create_notification(db_session, owner.id)

        response = client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers=_headers(other.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_404_for_a_nonexistent_notification(
        self, client, db_session
    ) -> None:
        user = await _create_user(db_session, "950000008")

        response = client.patch(
            f"/api/v1/notifications/{uuid.uuid4()}/read",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_returns_401_for_an_unauthenticated_caller(
        self, client, db_session
    ) -> None:
        user = await _create_user(db_session, "950000009")
        notification = await _create_notification(db_session, user.id)

        response = client.patch(f"/api/v1/notifications/{notification.id}/read")

        assert response.status_code == 401
