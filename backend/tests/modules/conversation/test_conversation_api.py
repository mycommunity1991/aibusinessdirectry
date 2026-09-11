"""
End-to-end HTTP integration tests for `/api/v1/conversations` (AI-001).

Uses the same real-Postgres `db_session`/`db_engine` fixtures as
`test_saved_address_endpoints.py`, with `get_db` overridden so the
FastAPI app and the test both see the same transaction. Access tokens
are minted directly against a real `identity.users` row.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.constants import ROLE_CUSTOMER, ROLE_PROVIDER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.customer.models import CustomerProfile, SavedAddress
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    ServiceArea,
    VerificationStatus,
)

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


_DUBAI_LAT = 25.2048
_DUBAI_LNG = 55.2708


async def _create_customer_profile(db_session, user: User) -> CustomerProfile:
    profile = CustomerProfile(user_id=user.id, display_name="Test Customer")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _create_default_address(db_session, customer_id: uuid.UUID) -> SavedAddress:
    address = SavedAddress(
        customer_id=customer_id,
        address_line="123 Main St",
        country_code="AE",
        latitude=_DUBAI_LAT,
        longitude=_DUBAI_LNG,
        is_default=True,
    )
    db_session.add(address)
    await db_session.commit()
    await db_session.refresh(address)
    return address


async def _create_discoverable_provider(
    db_session,
    *,
    display_name: str,
    latitude: float = _DUBAI_LAT,
    longitude: float = _DUBAI_LNG,
    average_rating: Decimal | None = None,
    review_count: int = 0,
) -> Provider:
    """A real, `is_discoverable=true` provider in the `Plumbing` category,
    with caller-supplied rating/location, for the AC5 end-to-end test
    below (`Plan_S08_MAT-001.md`, Verification Plan item 5) -- mirrors
    `tests/modules/search/_helpers.py::create_discoverable_provider`,
    duplicated locally since this module owns no dependency on
    `search`'s own test helpers."""
    owner = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=f"7{uuid.uuid4().int % 10**8:08d}",
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)

    provider = Provider(
        user_id=owner.id,
        provider_type=ProviderType.FREELANCER,
        display_name=display_name,
        slug=f"{display_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        average_rating=average_rating,
        review_count=review_count,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        ServiceArea(
            provider_id=provider.id,
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=20_000,
        )
    )
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label="Plumbing", is_primary=True
        )
    )
    await db_session.commit()
    return provider


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


class TestAC5ConversationCompletionFlowsIntoRankedResults:
    """MAT-001, AC5 (`Plan_S08_MAT-001.md`, Verification Plan item 5):
    starting a Conversation Session and completing it flows directly
    into a merit-ranked results response with no manual re-search step
    -- a genuine, multi-turn HTTP round trip through `POST
    /conversations` -> `POST /conversations/{id}/messages` (x2) -> `GET
    /search-requests/{search_request_id}`, never a synthetic
    `handle_session_completed(...)` service call. This is the same shape
    of cross-module gap `AI-001`'s own AC5 bug had (a claim of "already
    satisfied" that had never actually been exercised end to end) -- no
    existing test in this codebase (`test_conversation_service.py`'s
    multi-turn tests seed no default address/provider at all; `search`'s
    own `test_search_request_service.py`/`test_search_request_api.py`
    call `handle_session_completed(...)` directly, never through a real
    conversation) drove a real, `matched`-with-providers session through
    the actual HTTP conversation flow before this test."""

    @pytest.mark.anyio
    async def test_full_http_conversation_flow_yields_merit_ranked_results(
        self, client: TestClient, db_session
    ) -> None:
        user = await _create_user(db_session, "704000050")
        profile = await _create_customer_profile(db_session, user)
        await _create_default_address(db_session, profile.id)
        await _seed_category(db_session, question_count=2)

        # A closer-but-unrated provider and a farther-but-top-rated one --
        # the same adversarial combination
        # `test_provider_search_repository.py::TestMeritRanking` proves at
        # the repository layer, now proven end to end through a real HTTP
        # conversation.
        closer_unrated = await _create_discoverable_provider(
            db_session,
            display_name="Closer Unrated",
            average_rating=None,
            review_count=0,
        )
        farther_top_rated = await _create_discoverable_provider(
            db_session,
            display_name="Farther Top Rated",
            latitude=_DUBAI_LAT + 0.03,  # ~3.3km north -- still in radius
            longitude=_DUBAI_LNG,
            average_rating=Decimal("5.00"),
            review_count=50,
        )
        headers = _auth_headers(user.id)

        started = client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"message": "My Plumbing needs fixing"},
        )
        assert started.status_code == 201
        session_id = started.json()["data"]["id"]
        assert started.json()["data"]["search_request_id"] is None

        turn_1 = client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=headers,
            json={"content": "It's a leak"},
        )
        assert turn_1.status_code == 200

        turn_2 = client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=headers,
            json={"content": "Very urgent"},
        )
        assert turn_2.status_code == 200
        turn_2_data = turn_2.json()["data"]
        assert turn_2_data["status"] == "completed"
        search_request_id = turn_2_data["search_request_id"]
        assert search_request_id is not None

        # AC5's literal substance: the client fetches the ranked-results
        # resource directly from the id the conversation response itself
        # handed back -- no manual re-search call of any kind.
        results = client.get(
            f"/api/v1/search-requests/{search_request_id}", headers=headers
        )
        assert results.status_code == 200
        result_data = results.json()["data"]
        assert result_data["status"] == "matched"
        matched_ids = [m["id"] for m in result_data["matched_providers"]]

        # AC3/AC8, proven through this exact end-to-end path: the
        # farther-but-higher-rated provider outranks the closer-but-
        # unrated one.
        assert matched_ids == [str(farther_top_rated.id), str(closer_unrated.id)]
