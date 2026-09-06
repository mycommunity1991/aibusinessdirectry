"""
End-to-end integration tests for `GET`/`PATCH /api/v1/customers/me`
(CUS-001, AC1/AC4/AC7).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as the
identity-domain tests (`tests/conftest.py`), with `get_db` overridden so
the FastAPI app and the test both see the same transaction. Access
tokens are minted directly (mirrors `TestGetMe`'s roleless-token pattern
in `tests/modules/identity/test_auth_endpoints.py`) against a real
`identity.users` row created in the same test, rather than driving a
full OTP/OAuth login -- this module only needs a valid, real `User` row
to satisfy `customer_profiles.user_id`'s foreign key.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.constants import ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.customer.models import CustomerPreferences, CustomerProfile
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


class TestGetMyProfile:
    @pytest.mark.anyio
    async def test_lazily_provisions_a_default_profile_for_a_legacy_user(
        self, client: TestClient, db_session
    ) -> None:
        """Decision 4: a user with no prior `customer_profiles` row (a
        pre-CUS-001 account) is never 404'd -- one is lazily created with
        default-English preferences on first access."""
        user = await _create_user(db_session, "601000001")

        response = client.get("/api/v1/customers/me", headers=_auth_headers(user.id))

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["display_name"] == "New Customer"
        assert body["avatar_url"] is None
        assert body["language"] == "en"
        assert body["notification_channel"] == "whatsapp"

        result = await db_session.execute(
            select(CustomerProfile).where(CustomerProfile.user_id == user.id)
        )
        profile = result.scalar_one()
        prefs_result = await db_session.execute(
            select(CustomerPreferences).where(
                CustomerPreferences.customer_id == profile.id
            )
        )
        assert prefs_result.scalar_one() is not None

    @pytest.mark.anyio
    async def test_returns_existing_profile_without_creating_a_duplicate(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "601000002")

        first_response = client.get(
            "/api/v1/customers/me", headers=_auth_headers(user.id)
        )
        assert first_response.status_code == 200
        first_id = first_response.json()["data"]["id"]

        second_response = client.get(
            "/api/v1/customers/me", headers=_auth_headers(user.id)
        )
        assert second_response.status_code == 200
        assert second_response.json()["data"]["id"] == first_id

        result = await db_session.execute(
            select(CustomerProfile).where(CustomerProfile.user_id == user.id)
        )
        assert len(result.scalars().all()) == 1

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/customers/me")
        assert response.status_code == 401


class TestPatchMyProfile:
    @pytest.mark.anyio
    async def test_updates_only_the_provided_field(
        self, client: TestClient, db_session
    ) -> None:
        """AC4: partial update -- only the submitted field changes."""
        user = await _create_user(db_session, "601000010")
        # Establish the default profile first.
        client.get("/api/v1/customers/me", headers=_auth_headers(user.id))

        response = client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user.id),
            json={"display_name": "Fatima Al Mansoori"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["display_name"] == "Fatima Al Mansoori"
        # Untouched fields retain their defaults.
        assert body["language"] == "en"
        assert body["notification_channel"] == "whatsapp"
        assert body["avatar_url"] is None

    @pytest.mark.anyio
    async def test_updates_language_and_notification_channel(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "601000011")

        response = client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user.id),
            json={"language": "ar", "notification_channel": "sms"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["language"] == "ar"
        assert body["notification_channel"] == "sms"
        # display_name/avatar_url are untouched.
        assert body["display_name"] == "New Customer"

    @pytest.mark.anyio
    async def test_can_clear_avatar_url_explicitly(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "601000012")
        client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user.id),
            json={"avatar_url": "https://example.com/a.png"},
        )

        response = client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user.id),
            json={"avatar_url": None},
        )

        assert response.status_code == 200
        assert response.json()["data"]["avatar_url"] is None

    def test_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.patch(
            "/api/v1/customers/me", json={"display_name": "Someone"}
        )
        assert response.status_code == 401


class TestOwnershipIsolation:
    """AC7: a caller can never read or affect another user's profile.
    There is no `{id}`-addressable route at all (Decision 5) -- this
    proves the two-different-tokens-get-two-different-results shape
    directly."""

    @pytest.mark.anyio
    async def test_two_users_never_see_or_affect_each_others_profile(
        self, client: TestClient, db_session
    ) -> None:
        user_a = await _create_user(db_session, "601000020")
        user_b = await _create_user(db_session, "601000021")

        patch_a = client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user_a.id),
            json={"display_name": "User A"},
        )
        assert patch_a.status_code == 200
        assert patch_a.json()["data"]["display_name"] == "User A"

        get_b = client.get("/api/v1/customers/me", headers=_auth_headers(user_b.id))
        assert get_b.status_code == 200
        assert get_b.json()["data"]["display_name"] == "New Customer"
        assert get_b.json()["data"]["id"] != patch_a.json()["data"]["id"]

        patch_b = client.patch(
            "/api/v1/customers/me",
            headers=_auth_headers(user_b.id),
            json={"display_name": "User B"},
        )
        assert patch_b.status_code == 200

        # User A's row is untouched by User B's patch.
        get_a_again = client.get(
            "/api/v1/customers/me", headers=_auth_headers(user_a.id)
        )
        assert get_a_again.json()["data"]["display_name"] == "User A"

        result = await db_session.execute(select(CustomerProfile))
        profiles = result.scalars().all()
        assert len(profiles) == 2
        assert {p.user_id for p in profiles} == {user_a.id, user_b.id}
