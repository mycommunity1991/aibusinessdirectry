"""
End-to-end integration tests for `GET /api/v1/providers/me/leads`
(LEAD-001, AC1/AC2/AC3/AC4, `Plan_S10_LEAD-001.md`) -- mirrors
`test_contact_api.py`'s real-Postgres, real-app-DI pattern. Written
last in this story's build order, per the Plan's own sequencing.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.category.models import Category
from app.modules.contact.models import ContactView
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.customer.models import CustomerProfile
from app.modules.identity.models import AuthProvider, User
from app.modules.search.models import SearchRequest, SearchRequestStatus

from ._helpers import create_customer_profile, create_provider, create_user

_PII_CUSTOMER_PHONE_NUMBER = "603000099"
_PII_CUSTOMER_DISPLAY_NAME = "Zara Al Fahim"
_PII_CUSTOMER_AVATAR_URL = "https://example.com/avatars/zara-al-fahim.jpg"


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


async def _create_category(db_session, *, name: str) -> Category:
    category = Category(
        name=name,
        name_ar=None,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
        sort_order=0,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


async def _create_search_request(
    db_session, *, customer_id: uuid.UUID, category_id: uuid.UUID | None
) -> SearchRequest:
    search_request = SearchRequest(
        customer_id=customer_id,
        category_id=category_id,
        status=SearchRequestStatus.MATCHED,
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)
    return search_request


async def _create_contact_view(
    db_session,
    *,
    customer_id: uuid.UUID,
    provider_id: uuid.UUID,
    search_request_id: uuid.UUID | None = None,
    viewed_at: datetime | None = None,
) -> ContactView:
    contact_view = ContactView(
        customer_id=customer_id,
        provider_id=provider_id,
        search_request_id=search_request_id,
        viewed_at=viewed_at or datetime.now(UTC),
    )
    db_session.add(contact_view)
    await db_session.commit()
    await db_session.refresh(contact_view)
    return contact_view


class TestListMyLeadsHappyPath:
    @pytest.mark.anyio
    async def test_returns_200_with_all_three_outcome_states_and_both_category_cases(
        self, client, db_session
    ) -> None:
        customer_user, customer_profile = await _create_pii_bearing_customer(
            db_session
        )
        provider_owner_user = await create_user(db_session, "603000001")
        provider = await create_provider(db_session, user=provider_owner_user)

        category = await _create_category(db_session, name="Landscaping")
        resolvable_search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id, category_id=category.id
        )
        null_category_search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id, category_id=None
        )

        now = datetime.now(UTC)
        hired_view = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=resolvable_search_request.id,
            viewed_at=now,
        )
        not_hired_view = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=null_category_search_request.id,
            viewed_at=now - timedelta(hours=1),
        )
        not_yet_reported_view = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=None,
            viewed_at=now - timedelta(hours=2),
        )
        outcome_tag_repository = OutcomeTagRepository(db_session)
        await outcome_tag_repository.try_create(
            {"contact_view_id": hired_view.id, "hired": True}
        )
        await outcome_tag_repository.try_create(
            {"contact_view_id": not_hired_view.id, "hired": False}
        )
        await db_session.commit()

        response = client.get(
            "/api/v1/providers/me/leads",
            headers=_headers(provider_owner_user.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        items = body["data"]
        assert len(items) == 3
        by_id = {item["id"]: item for item in items}

        hired_item = by_id[str(hired_view.id)]
        assert hired_item["outcome_status"] == "hired"
        assert hired_item["category_name"] == "Landscaping"
        assert set(hired_item.keys()) == {
            "id",
            "category_name",
            "viewed_at",
            "outcome_status",
        }

        not_hired_item = by_id[str(not_hired_view.id)]
        assert not_hired_item["outcome_status"] == "not_hired"
        assert not_hired_item["category_name"] is None

        not_yet_reported_item = by_id[str(not_yet_reported_view.id)]
        assert not_yet_reported_item["outcome_status"] == "not_yet_reported"
        assert not_yet_reported_item["category_name"] is None

        pagination = body["pagination"]
        assert pagination["total_items"] == 3
        assert pagination["page"] == 1

    @pytest.mark.anyio
    async def test_no_pii_field_or_value_appears_anywhere_in_the_response_body(
        self, client, db_session
    ) -> None:
        """
        AC3's literal wire-level assertion: the fixture customer
        genuinely HAS a display name, avatar, and phone number set, so
        their absence from the response proves the omission is
        deliberate, not simply 'no data existed to leak'.
        """
        customer_user, customer_profile = await _create_pii_bearing_customer(
            db_session
        )
        provider_owner_user = await create_user(db_session, "603000002")
        provider = await create_provider(db_session, user=provider_owner_user)
        await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider.id
        )

        response = client.get(
            "/api/v1/providers/me/leads",
            headers=_headers(provider_owner_user.id),
        )

        assert response.status_code == 200
        raw_body_text = response.text

        # No PII key anywhere in the payload.
        for forbidden_key in (
            "customer_id",
            "display_name",
            "avatar_url",
            "phone_number",
            "phone_country_code",
            "customer_display_name",
            "customer_avatar_url",
        ):
            assert f'"{forbidden_key}"' not in raw_body_text

        # No PII *value* anywhere in the payload either -- not merely
        # the key names.
        assert _PII_CUSTOMER_DISPLAY_NAME not in raw_body_text
        assert _PII_CUSTOMER_AVATAR_URL not in raw_body_text
        assert _PII_CUSTOMER_PHONE_NUMBER not in raw_body_text
        assert str(customer_profile.id) not in raw_body_text
        assert str(customer_user.id) not in raw_body_text

        # Every item's field set is exactly `LeadResponse`'s own shape.
        for item in json.loads(raw_body_text)["data"]:
            assert set(item.keys()) == {
                "id",
                "category_name",
                "viewed_at",
                "outcome_status",
            }


class TestListMyLeadsNoProvider:
    @pytest.mark.anyio
    async def test_returns_404_when_the_caller_has_no_provider_listing(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "603000003")
        await create_customer_profile(db_session, customer_user)

        response = client.get(
            "/api/v1/providers/me/leads",
            headers=_headers(customer_user.id),
        )

        assert response.status_code == 404


class TestListMyLeadsAuthBoundaries:
    @pytest.mark.anyio
    async def test_returns_401_when_unauthenticated(self, client, db_session) -> None:
        response = client.get("/api/v1/providers/me/leads")

        assert response.status_code == 401


class TestListMyLeadsCrossProviderBoundary:
    @pytest.mark.anyio
    async def test_provider_a_never_sees_provider_bs_leads_over_http(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "603000004")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "603000005")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "603000006")
        provider_b = await create_provider(db_session, user=provider_b_owner)

        contact_view_a = await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider_a.id
        )
        await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider_b.id
        )

        response = client.get(
            "/api/v1/providers/me/leads",
            headers=_headers(provider_a_owner.id),
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == str(contact_view_a.id)


class TestListMyLeadsPagination:
    @pytest.mark.anyio
    async def test_page_and_page_size_query_params_behave_per_pagination_meta(
        self, client, db_session
    ) -> None:
        customer_user = await create_user(db_session, "603000007")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "603000008")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        created_ids = []
        for offset_minutes in range(5):
            view = await _create_contact_view(
                db_session,
                customer_id=customer_profile.id,
                provider_id=provider.id,
                viewed_at=now - timedelta(minutes=offset_minutes),
            )
            created_ids.append(str(view.id))

        response_page_one = client.get(
            "/api/v1/providers/me/leads",
            params={"page": 1, "page_size": 2},
            headers=_headers(provider_owner.id),
        )
        response_page_two = client.get(
            "/api/v1/providers/me/leads",
            params={"page": 2, "page_size": 2},
            headers=_headers(provider_owner.id),
        )

        assert response_page_one.status_code == 200
        body_one = response_page_one.json()
        assert [item["id"] for item in body_one["data"]] == created_ids[0:2]
        assert body_one["pagination"] == {
            "page": 1,
            "page_size": 2,
            "total_items": 5,
            "total_pages": 3,
        }

        assert response_page_two.status_code == 200
        body_two = response_page_two.json()
        assert [item["id"] for item in body_two["data"]] == created_ids[2:4]
