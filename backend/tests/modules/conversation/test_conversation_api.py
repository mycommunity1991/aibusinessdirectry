"""
End-to-end HTTP integration tests for `/api/v1/conversations` (AI-001).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as
`test_saved_address_endpoints.py`, with `get_db` overridden so the
FastAPI app and the test both see the same transaction. Access tokens
are minted directly against a real `identity.users` row.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.category.models import Category, CategoryQuestionTemplate
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


async def _seed_category(db_session, *, question_count: int = 2) -> Category:
    category = Category(name="Plumbing", name_ar=None, slug="plumbing", sort_order=0)
    db_session.add(category)
    await db_session.flush()
    for i in range(question_count):
        db_session.add(
            CategoryQuestionTemplate(
                category_id=category.id,
                question_text=f"Question {i}?",
                question_text_ar=None,
                question_type="text",
                options=None,
                is_required=True,
                sort_order=i,
            )
        )
    await db_session.commit()
    return category


def _token_for(user_id: uuid.UUID, *, roles: list[str]) -> str:
    return create_access_token(subject=str(user_id), roles=roles, jti=str(uuid.uuid4()))


def _auth_headers(user_id: uuid.UUID, *, roles: list[str] | None = None) -> dict:
    roles = roles if roles is not None else [ROLE_CUSTOMER]
    return {"Authorization": f"Bearer {_token_for(user_id, roles=roles)}"}


def _assert_no_raw_confidence_anywhere(payload: object) -> None:
    """AC6: `ConversationSessionResponse` never includes a raw numeric
    confidence/score field, at the API-contract level -- checked
    recursively so a future field addition can't silently reintroduce
    one."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert "confidence" not in key.lower(), key
            assert key.lower() != "score", key
            _assert_no_raw_confidence_anywhere(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_raw_confidence_anywhere(item)


class TestStartConversation:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/conversations", json={"message": "My Plumbing needs fixing"}
        )
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_requires_the_customer_role(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000001")
        await _seed_category(db_session)

        response = client.post(
            "/api/v1/conversations",
            headers=_auth_headers(user.id, roles=[ROLE_PROVIDER]),
            json={"message": "My Plumbing needs fixing"},
        )

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_creates_a_session_and_returns_no_raw_confidence(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000002")
        await _seed_category(db_session)

        response = client.post(
            "/api/v1/conversations",
            headers=_auth_headers(user.id),
            json={"message": "My Plumbing needs fixing"},
        )

        assert response.status_code == 201
        body = response.json()
        data = body["data"]
        assert data["status"] == "active"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["sender"] == "customer"
        assert data["messages"][1]["sender"] == "ai"
        _assert_no_raw_confidence_anywhere(body)


class TestSubmitTurn:
    @pytest.mark.anyio
    async def test_submits_a_turn_and_advances_the_conversation(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000010")
        await _seed_category(db_session)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=headers,
            json={"content": "It's a leak"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]["messages"]) == 4
        _assert_no_raw_confidence_anywhere(body)

    @pytest.mark.anyio
    async def test_selected_option_is_mapped_to_content(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000011")
        await _seed_category(db_session)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=headers,
            json={"selected_option": "It's a leak"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["messages"][2]["content"] == "It's a leak"

    @pytest.mark.anyio
    async def test_both_content_and_selected_option_is_rejected(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000012")
        await _seed_category(db_session)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=headers,
            json={"content": "a", "selected_option": "b"},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_cross_customer_submit_turn_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        owner = await _create_user(db_session, "703000013")
        stranger = await _create_user(db_session, "703000014")
        await _seed_category(db_session)
        started = client.post(
            "/api/v1/conversations",
            headers=_auth_headers(owner.id),
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=_auth_headers(stranger.id),
            json={"content": "It's a leak"},
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_nonexistent_session_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000015")

        response = client.post(
            f"/api/v1/conversations/{uuid.uuid4()}/messages",
            headers=_auth_headers(user.id),
            json={"content": "anything"},
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_submitting_to_a_completed_session_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000016")
        await _seed_category(db_session, question_count=1)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]
        completed = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=headers,
            json={"content": "One answer"},
        ).json()["data"]
        assert completed["status"] == "completed"

        response = client.post(
            f"/api/v1/conversations/{started['id']}/messages",
            headers=headers,
            json={"content": "too late"},
        )

        assert response.status_code == 409


class TestReviseAnswer:
    @pytest.mark.anyio
    async def test_revises_a_previous_answer(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000020")
        await _seed_category(db_session, question_count=1)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]
        first_message_id = started["messages"][0]["id"]

        response = client.patch(
            f"/api/v1/conversations/{started['id']}/answers/{first_message_id}",
            headers=headers,
            json={"content": "My Plumbing is still broken, differently"},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["messages"][0]["content"] == (
            "My Plumbing is still broken, differently"
        )
        _assert_no_raw_confidence_anywhere(response.json())

    @pytest.mark.anyio
    async def test_revising_a_nonexistent_message_returns_422(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000021")
        await _seed_category(db_session)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.patch(
            f"/api/v1/conversations/{started['id']}/answers/{uuid.uuid4()}",
            headers=headers,
            json={"content": "anything"},
        )

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_cross_customer_revise_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        owner = await _create_user(db_session, "703000022")
        stranger = await _create_user(db_session, "703000023")
        await _seed_category(db_session)
        started = client.post(
            "/api/v1/conversations",
            headers=_auth_headers(owner.id),
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]
        first_message_id = started["messages"][0]["id"]

        response = client.patch(
            f"/api/v1/conversations/{started['id']}/answers/{first_message_id}",
            headers=_auth_headers(stranger.id),
            json={"content": "anything"},
        )

        assert response.status_code == 404


class TestGetSession:
    @pytest.mark.anyio
    async def test_returns_the_transcript(self, client: TestClient, db_session) -> None:
        user = await _create_user(db_session, "703000030")
        await _seed_category(db_session)
        headers = _auth_headers(user.id)
        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.get(f"/api/v1/conversations/{started['id']}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["id"] == started["id"]
        assert len(body["data"]["messages"]) == 2
        _assert_no_raw_confidence_anywhere(body)

    @pytest.mark.anyio
    async def test_cross_customer_get_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        owner = await _create_user(db_session, "703000031")
        stranger = await _create_user(db_session, "703000032")
        await _seed_category(db_session)
        started = client.post(
            "/api/v1/conversations",
            headers=_auth_headers(owner.id),
            json={"message": "My Plumbing needs fixing"},
        ).json()["data"]

        response = client.get(
            f"/api/v1/conversations/{started['id']}",
            headers=_auth_headers(stranger.id),
        )

        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_nonexistent_session_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "703000033")

        response = client.get(
            f"/api/v1/conversations/{uuid.uuid4()}", headers=_auth_headers(user.id)
        )

        assert response.status_code == 404

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/conversations/{uuid.uuid4()}")
        assert response.status_code == 401


class TestNoRawConfidenceAcrossFullLifecycle:
    @pytest.mark.anyio
    async def test_full_lifecycle_never_leaks_confidence(
        self, client: TestClient, db_session
    ) -> None:
        """AC6, end to end: from session start through completion, no
        response ever surfaces a raw confidence/score value."""
        user = await _create_user(db_session, "703000040")
        await _seed_category(db_session, question_count=2)
        headers = _auth_headers(user.id)

        started_response = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        )
        _assert_no_raw_confidence_anywhere(started_response.json())
        session_id = started_response.json()["data"]["id"]

        turn_1 = client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=headers,
            json={"content": "It's a leak"},
        )
        _assert_no_raw_confidence_anywhere(turn_1.json())

        turn_2 = client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=headers,
            json={"content": "Very urgent"},
        )
        _assert_no_raw_confidence_anywhere(turn_2.json())
        assert turn_2.json()["data"]["status"] == "completed"

        final = client.get(f"/api/v1/conversations/{session_id}", headers=headers)
        _assert_no_raw_confidence_anywhere(final.json())
