"""
End-to-end integration tests for `GET /api/v1/providers/me/
visibility-analytics` (LEAD-002, AC1/AC2/AC3/AC4, `Plan_S10_LEAD-002.md`)
-- mirrors `test_lead_api.py`'s real-Postgres, real-app-DI pattern.
Written last in this story's build order, per the Plan's own
sequencing.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.contact.models import ContactView
from app.modules.customer.models import CustomerProfile
from app.modules.identity.models import AuthProvider, User
from app.modules.search.models import ProviderMatch, SearchRequest, SearchRequestStatus

from ._helpers import create_customer_profile, create_provider, create_user

_PII_CUSTOMER_PHONE_NUMBER = "606000099"
_PII_CUSTOMER_DISPLAY_NAME = "Layla Al Mansoori"
_PII_CUSTOMER_AVATAR_URL = "https://example.com/avatars/layla-al-mansoori.jpg"
_WINDOW_DAYS = settings.VISIBILITY_ANALYTICS_WINDOW_DAYS


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


def _token_for(user_id: uuid.UUID) -> str:
    return create_access_token(
        subject=str(user_id), roles=["customer"], jti=str(uuid.uuid4())
    )


def _headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}


async def _create_pii_bearing_customer(db_session) -> tuple[User, CustomerProfile]:
    """A customer who genuinely HAS a display name, avatar, and phone
    number set -- so the wire-level no-PII assertion proves the
    omission is deliberate, not simply 'no data existed to leak'."""
    user = User(
        phone_country_code="+971",
        phone_number=_PII_CUSTOMER_PHONE_NUMBER,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = CustomerProfile(
        user_id=user.id,
        display_name=_PII_CUSTOMER_DISPLAY_NAME,
        avatar_url=_PII_CUSTOMER_AVATAR_URL,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


async def _create_contact_view(
    db_session, *, customer_id: uuid.UUID, provider_id: uuid.UUID, viewed_at: datetime
) -> ContactView:
    contact_view = ContactView(
        customer_id=customer_id,
        provider_id=provider_id,
        search_request_id=None,
        viewed_at=viewed_at,
    )
    db_session.add(contact_view)
    await db_session.commit()
    await db_session.refresh(contact_view)
    return contact_view


async def _create_provider_match(
    db_session, *, customer_id: uuid.UUID, provider_id: uuid.UUID, created_at: datetime
) -> ProviderMatch:
    search_request = SearchRequest(
        customer_id=customer_id, status=SearchRequestStatus.MATCHED
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)

    provider_match = ProviderMatch(
        search_request_id=search_request.id,
        provider_id=provider_id,
        rank=1,
        match_score=None,
        created_at=created_at,
    )
    db_session.add(provider_match)
    await db_session.commit()
    await db_session.refresh(provider_match)
    return provider_match


_EXPECTED_TOP_LEVEL_KEYS = {
    "has_sufficient_data",
    "search_appearances",
    "contact_views",
    "daily_trend",
}
_EXPECTED_METRIC_KEYS = {"total_last_30_days", "trend"}
_EXPECTED_DAILY_POINT_KEYS = {"date", "search_appearances", "contact_views"}


class TestGetMyVisibilityAnalyticsHappyPath:
    @pytest.mark.anyio
    async def test_returns_200_with_the_exact_response_shape(
        self, client, db_session
    ) -> None:
        customer_user, customer_profile = await _create_pii_bearing_customer(
            db_session
        )
        provider_owner = await create_user(db_session, "606000001")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )
        await _create_provider_match(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            created_at=now - timedelta(days=5),
        )

        response = client.get(
            "/api/v1/providers/me/visibility-analytics",
            headers=_headers(provider_owner.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == _EXPECTED_TOP_LEVEL_KEYS
        assert body["has_sufficient_data"] is True
        assert set(body["search_appearances"].keys()) == _EXPECTED_METRIC_KEYS
        assert set(body["contact_views"].keys()) == _EXPECTED_METRIC_KEYS
        assert body["search_appearances"]["total_last_30_days"] == 1
        assert body["contact_views"]["total_last_30_days"] == 1
        assert body["search_appearances"]["trend"] in {"up", "down", "flat"}
        assert body["contact_views"]["trend"] in {"up", "down", "flat"}
        assert len(body["daily_trend"]) == _WINDOW_DAYS
        for point in body["daily_trend"]:
            assert set(point.keys()) == _EXPECTED_DAILY_POINT_KEYS
        dates = [point["date"] for point in body["daily_trend"]]
        assert dates == sorted(dates)

    @pytest.mark.anyio
    async def test_no_pii_or_query_text_field_or_value_appears_in_the_response_body(
        self, client, db_session
    ) -> None:
        """
        AC3/Decision 8's literal wire-level assertion: the fixture
        customer genuinely HAS a display name, avatar, and phone number
        set, so their absence from the response proves the omission is
        deliberate, not simply 'no data existed to leak'.
        """
        customer_user, customer_profile = await _create_pii_bearing_customer(
            db_session
        )
        provider_owner = await create_user(db_session, "606000002")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=5),
        )
        await _create_provider_match(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            created_at=now - timedelta(days=5),
        )

        response = client.get(
            "/api/v1/providers/me/visibility-analytics",
            headers=_headers(provider_owner.id),
        )

        assert response.status_code == 200
        raw_body_text = response.text

        for forbidden_key in (
            "customer_id",
            "display_name",
            "avatar_url",
            "phone_number",
            "phone_country_code",
            "query_text",
            "category_id",
            "category_name",
        ):
            assert f'"{forbidden_key}"' not in raw_body_text

        assert _PII_CUSTOMER_DISPLAY_NAME not in raw_body_text
        assert _PII_CUSTOMER_AVATAR_URL not in raw_body_text
        assert _PII_CUSTOMER_PHONE_NUMBER not in raw_body_text
        assert str(customer_profile.id) not in raw_body_text
        assert str(customer_user.id) not in raw_body_text

        body = json.loads(raw_body_text)
        assert set(body.keys()) == _EXPECTED_TOP_LEVEL_KEYS


class TestGetMyVisibilityAnalyticsNoProvider:
    @pytest.mark.anyio
    async def test_returns_404_when_the_caller_has_no_provider_listing(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "606000003")
        await create_customer_profile(db_session, customer_user)

        response = client.get(
            "/api/v1/providers/me/visibility-analytics",
            headers=_headers(customer_user.id),
        )

        assert response.status_code == 404


class TestGetMyVisibilityAnalyticsAuthBoundaries:
    @pytest.mark.anyio
    async def test_returns_401_when_unauthenticated(self, client, db_session) -> None:
        response = client.get("/api/v1/providers/me/visibility-analytics")

        assert response.status_code == 401


class TestGetMyVisibilityAnalyticsCrossProviderBoundary:
    @pytest.mark.anyio
    async def test_provider_a_never_reflects_provider_bs_activity_over_http(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "606000004")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "606000005")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "606000006")
        provider_b = await create_provider(db_session, user=provider_b_owner)
        now = datetime.now(UTC)

        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider_a.id,
            viewed_at=now - timedelta(days=5),
        )
        for _ in range(5):
            await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider_b.id,
                viewed_at=now - timedelta(days=5),
            )

        response = client.get(
            "/api/v1/providers/me/visibility-analytics",
            headers=_headers(provider_a_owner.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["contact_views"]["total_last_30_days"] == 1


class TestGetMyVisibilityAnalyticsNotEnoughData:
    @pytest.mark.anyio
    async def test_returns_has_sufficient_data_false_with_real_zero_filled_data(
        self, client, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "606000007")
        await create_provider(db_session, user=provider_owner)

        response = client.get(
            "/api/v1/providers/me/visibility-analytics",
            headers=_headers(provider_owner.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["has_sufficient_data"] is False
        # The real (all-zero) numbers and a fully zero-filled chart
        # series are still returned alongside the flag -- never an
        # omitted/null field set (Decision 6).
        assert body["search_appearances"] == {"total_last_30_days": 0, "trend": "flat"}
        assert body["contact_views"] == {"total_last_30_days": 0, "trend": "flat"}
        assert len(body["daily_trend"]) == _WINDOW_DAYS
        for point in body["daily_trend"]:
            assert point["search_appearances"] == 0
            assert point["contact_views"] == 0
            assert point["date"] is not None
