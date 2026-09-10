"""
End-to-end integration tests for `/api/v1/search-requests/*` and
`/api/v1/admin/search/manual-matches/*` (AI-002, `Plan_S07_AI-002.md`).

Mirrors `test_admin_claim_api.py`'s real-Postgres, real-app-DI pattern --
`get_db` overridden so the FastAPI app and the test share one
transaction; every other dependency (including `SearchRequestService`
and its own cross-module dependencies) resolves through the real
production wiring.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.constants import ROLE_ADMIN, ROLE_CUSTOMER
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.models import User
from app.modules.search.models import SearchEventLog

from ._helpers import (
    create_category,
    create_conversation_session,
    create_customer_profile,
    create_default_address,
    create_discoverable_provider,
    create_user,
    make_search_request_service,
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


async def _create_completed_search_request(db_session, user: User, *, matched: bool):
    """Builds a real, completed `search_requests` row owned by `user`,
    via the real `SearchRequestService` -- mirrors `test_admin_claim_
    api.py`'s `_create_review_request` helper's "build state directly
    through the real service, not the HTTP layer" convention."""
    profile = await create_customer_profile(db_session, user)
    await create_default_address(db_session, profile.id)
    category = await create_category(db_session, name="Plumbing")
    if matched:
        await create_discoverable_provider(db_session, category_label="Plumbing")
    session = await create_conversation_session(
        db_session, profile.id, category_id=category.id
    )
    service = make_search_request_service(db_session)
    search_request = await service.handle_session_completed(
        conversation_session_id=session.id,
        customer_id=profile.id,
        status="completed",
        category_id=category.id,
        category_name="Plumbing",
        structured_criteria={"category_id": str(category.id), "answers": []},
    )
    await db_session.commit()
    return search_request


async def _create_pending_manual_match(db_session, user: User):
    """Builds a real, `pending_manual_match` `search_requests` row plus
    its `manual_match_assignments` row, owned by `user`."""
    from sqlalchemy import select

    from app.modules.administration.models import ManualMatchAssignment

    profile = await create_customer_profile(db_session, user)
    category = await create_category(db_session, name="Plumbing")
    session = await create_conversation_session(
        db_session, profile.id, category_id=category.id
    )
    service = make_search_request_service(db_session)
    search_request = await service.handle_session_completed(
        conversation_session_id=session.id,
        customer_id=profile.id,
        status="routed_to_admin",
        category_id=category.id,
        category_name="Plumbing",
        structured_criteria=None,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(ManualMatchAssignment).where(
            ManualMatchAssignment.conversation_session_id == session.id
        )
    )
    assignment = result.scalar_one()
    return search_request, assignment


class TestGetSearchRequestAuthorization:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/search-requests/{uuid.uuid4()}")
        assert response.status_code == 401

    async def test_requires_the_customer_role(
        self, client: TestClient, db_session
    ) -> None:
        from app.core.constants import ROLE_PROVIDER

        user = await create_user(db_session, "930000001")

        response = client.get(
            f"/api/v1/search-requests/{uuid.uuid4()}",
            headers=_headers(user.id, [ROLE_PROVIDER]),
        )

        assert response.status_code == 403


class TestGetSearchRequest:
    async def test_owner_gets_the_matched_result(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000010")
        search_request = await _create_completed_search_request(
            db_session, user, matched=True
        )

        response = client.get(
            f"/api/v1/search-requests/{search_request.id}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "matched"
        assert len(body["matched_providers"]) == 1
        assert body["matched_providers"][0]["distance_meters"] is not None

    async def test_unmatched_result_has_an_empty_matched_providers_list(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000011")
        search_request = await _create_completed_search_request(
            db_session, user, matched=False
        )

        response = client.get(
            f"/api/v1/search-requests/{search_request.id}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "unmatched"
        assert body["matched_providers"] == []

    async def test_another_customers_search_request_returns_404_never_403(
        self, client: TestClient, db_session
    ) -> None:
        owner = await create_user(db_session, "930000012")
        stranger = await create_user(db_session, "930000013")
        search_request = await _create_completed_search_request(
            db_session, owner, matched=False
        )

        response = client.get(
            f"/api/v1/search-requests/{search_request.id}",
            headers=_headers(stranger.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    async def test_a_nonexistent_search_request_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000014")

        response = client.get(
            f"/api/v1/search-requests/{uuid.uuid4()}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 404

    async def test_pending_manual_match_has_an_empty_matched_providers_list(
        self, client: TestClient, db_session
    ) -> None:
        """AC3: the customer's response for a still-pending manual match
        looks like ordinary processing -- no forbidden terminology, an
        honest empty result, never an error."""
        user = await create_user(db_session, "930000015")
        search_request, _assignment = await _create_pending_manual_match(
            db_session, user
        )

        response = client.get(
            f"/api/v1/search-requests/{search_request.id}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "pending_manual_match"
        assert body["matched_providers"] == []


class TestAdminManualMatchAuthorization:
    def test_list_returns_401_without_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/admin/search/manual-matches")
        assert response.status_code == 401

    async def test_list_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000020")

        response = client.get(
            "/api/v1/admin/search/manual-matches",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )

        assert response.status_code == 403

    async def test_resolve_returns_403_for_a_non_admin(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000021")

        response = client.post(
            f"/api/v1/admin/search/manual-matches/{uuid.uuid4()}/resolve",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
            json={"provider_ids": []},
        )

        assert response.status_code == 403


class TestAdminListPendingManualMatches:
    async def test_lists_the_pending_assignment(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000030")
        admin = await create_user(db_session, "930000031")
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )

        response = client.get(
            "/api/v1/admin/search/manual-matches",
            headers=_headers(admin.id, [ROLE_ADMIN]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total_items"] == 1
        assert body["data"][0]["id"] == str(assignment.id)
        assert body["data"][0]["status"] == "pending"


class TestAdminResolveManualMatch:
    async def test_resolving_with_provider_ids_returns_matched_result(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000040")
        admin = await create_user(db_session, "930000041")
        provider = await create_discoverable_provider(
            db_session, category_label="Plumbing"
        )
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )

        response = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": [str(provider.id)]},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "matched"
        assert [p["id"] for p in body["matched_providers"]] == [str(provider.id)]

        # AC4: the customer now sees the identical response shape via the
        # customer-facing endpoint too.
        customer_response = client.get(
            f"/api/v1/search-requests/{_search_request.id}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )
        assert customer_response.json()["data"] == body

    async def test_resolving_with_an_empty_list_returns_unmatched(
        self, client: TestClient, db_session
    ) -> None:
        user = await create_user(db_session, "930000042")
        admin = await create_user(db_session, "930000043")
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )

        response = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": []},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "unmatched"
        assert body["matched_providers"] == []

    async def test_resolving_an_already_resolved_assignment_returns_409(
        self, client: TestClient, db_session
    ) -> None:
        """Never silently double-finalizing (AC4/AC6)."""
        user = await create_user(db_session, "930000044")
        admin = await create_user(db_session, "930000045")
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )
        first = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": []},
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": []},
        )

        assert second.status_code == 409

    async def test_a_rejected_second_resolve_does_not_double_finalize(
        self, client: TestClient, db_session
    ) -> None:
        """
        BUG regression test (found during AI-002 QA verification): AC4/AC6
        and `SearchRequestService.resolve_manual_match`'s own docstring
        both promise "never silently double-finalizing" for a rejected
        (409) second resolve attempt. The current implementation does not
        honor this -- `resolve_manual_match` calls `self._finalize_matches`
        *before* `ManualMatchAssignmentService.resolve` raises
        `ManualMatchAssignmentAlreadyResolvedError` (409), so the shared
        `_finalize_matches` helper (Decision 4) -- the "only place
        `provider_matches`/`search_requests.status`/`search_event_log` are
        ever written" -- actually runs a second time on every rejected
        409 attempt, before the rejection is raised.

        This test uses two *different* non-empty `provider_ids` on the
        first vs. second call specifically so the bug is visible as data
        corruption (an extra `search_event_log` row, and a second,
        different `provider_matches` set silently appended) rather than
        being masked by the `provider_matches` table's own
        `uq_provider_matches_request_provider` unique constraint (which
        would otherwise turn an identical-provider-ids second call into a
        500 instead, hiding the real bug).
        """
        user = await create_user(db_session, "930000050")
        admin = await create_user(db_session, "930000051")
        provider_first = await create_discoverable_provider(
            db_session, category_label="Plumbing", display_name="Provider First"
        )
        provider_second = await create_discoverable_provider(
            db_session, category_label="Plumbing", display_name="Provider Second"
        )
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )

        first = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": [str(provider_first.id)]},
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": [str(provider_second.id)]},
        )
        assert second.status_code == 409

        # AC6: exactly one `search_event_log` row must exist for this
        # `search_requests` row, regardless of how many resolve attempts
        # were made -- a rejected (409) attempt must not write a second
        # one.
        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == _search_request.id
            )
        )
        assert len(log_result.scalars().all()) == 1

        # AC4: the customer-visible result must still be exactly what the
        # first (accepted) resolve produced -- the rejected second call
        # must not have appended `provider_second` to `provider_matches`.
        customer_response = client.get(
            f"/api/v1/search-requests/{_search_request.id}",
            headers=_headers(user.id, [ROLE_CUSTOMER]),
        )
        matched_ids = [
            p["id"] for p in customer_response.json()["data"]["matched_providers"]
        ]
        assert matched_ids == [str(provider_first.id)]

    async def test_resolving_a_nonexistent_assignment_returns_404(
        self, client: TestClient, db_session
    ) -> None:
        admin = await create_user(db_session, "930000046")

        response = client.post(
            f"/api/v1/admin/search/manual-matches/{uuid.uuid4()}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": []},
        )

        assert response.status_code == 404

    async def test_a_bogus_provider_id_returns_422_not_500(
        self, client: TestClient, db_session
    ) -> None:
        """
        `08_CODING_STANDARDS.md`'s "validate every endpoint's input"
        rule: a non-existent `provider_id` in the admin-supplied
        `provider_ids` list must be rejected as an actionable 422
        *before* `ProviderMatchRepository.bulk_create`'s FK constraint
        would otherwise surface it as an opaque 500.
        """
        user = await create_user(db_session, "930000047")
        admin = await create_user(db_session, "930000048")
        _search_request, assignment = await _create_pending_manual_match(
            db_session, user
        )
        bogus_provider_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/admin/search/manual-matches/{assignment.id}/resolve",
            headers=_headers(admin.id, [ROLE_ADMIN]),
            json={"provider_ids": [str(bogus_provider_id)]},
        )

        assert response.status_code == 422

        # The assignment must still be `pending` -- a rejected (422)
        # payload must not have resolved it or written anything.
        from app.modules.administration.models import ManualMatchAssignment

        refreshed = await db_session.get(ManualMatchAssignment, assignment.id)
        assert refreshed.status == "pending"
