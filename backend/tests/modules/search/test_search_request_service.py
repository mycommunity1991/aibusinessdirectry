"""
Integration tests for `SearchRequestService` (AI-002, Decision 4,
`Plan_S07_AI-002.md`), exercised against a real Postgres database.

Covers both the automated-match path (`handle_session_completed` with
`status="completed"`) and the manual-resolution path (`status=
"routed_to_admin"` -> `resolve_manual_match`) around the shared
`_finalize_matches` helper -- the concrete proof behind AC2 ("never left
in limbo"), AC4 ("the same ranked-results screen" regardless of origin),
and AC6 (`search_event_log` written exactly once, regardless of origin).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import (
    InvalidManualMatchProviderIdsError,
    ManualMatchAssignmentNotFoundError,
    SearchRequestNotFoundError,
)
from app.modules.administration.models import ManualMatchAssignment
from app.modules.search.models import SearchEventLog, SearchRequestStatus

from ._helpers import (
    create_category,
    create_conversation_session,
    create_customer_profile,
    create_default_address,
    create_discoverable_provider,
    create_user,
    make_search_request_service,
)


class TestHandleSessionCompletedAutomatedPath:
    async def test_with_a_default_address_and_a_matching_provider_is_matched(
        self, db_session
    ) -> None:
        user = await create_user(db_session, "920000001")
        profile = await create_customer_profile(db_session, user)
        await create_default_address(db_session, profile.id)
        category = await create_category(db_session, name="Plumbing")
        provider = await create_discoverable_provider(
            db_session, category_label="Plumbing"
        )
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

        assert search_request.status == SearchRequestStatus.MATCHED
        assert search_request.customer_latitude is not None
        assert search_request.customer_longitude is not None

        matched = await service.get_matched_providers(search_request)
        assert [m.id for m in matched] == [provider.id]
        assert matched[0].distance_meters is not None

        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == search_request.id
            )
        )
        logs = log_result.scalars().all()
        assert len(logs) == 1
        assert logs[0].was_matched is True
        assert logs[0].result_count == 1

    async def test_no_matching_provider_is_unmatched_but_still_creates_a_request(
        self, db_session
    ) -> None:
        user = await create_user(db_session, "920000002")
        profile = await create_customer_profile(db_session, user)
        await create_default_address(db_session, profile.id)
        category = await create_category(db_session, name="Electrical")
        session = await create_conversation_session(
            db_session, profile.id, category_id=category.id
        )
        service = make_search_request_service(db_session)

        search_request = await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=profile.id,
            status="completed",
            category_id=category.id,
            category_name="Electrical",
            structured_criteria={"category_id": str(category.id), "answers": []},
        )
        await db_session.commit()

        assert search_request.status == SearchRequestStatus.UNMATCHED
        matched = await service.get_matched_providers(search_request)
        assert matched == []

        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == search_request.id
            )
        )
        logs = log_result.scalars().all()
        assert len(logs) == 1
        assert logs[0].was_matched is False
        assert logs[0].result_count == 0

    async def test_no_default_address_is_unmatched_with_null_coordinates(
        self, db_session
    ) -> None:
        """Decision 2c: a customer with no default saved address still
        completes automatically (as `unmatched`) -- never blocked, never
        a guessed `(0, 0)`."""
        user = await create_user(db_session, "920000003")
        profile = await create_customer_profile(db_session, user)
        category = await create_category(db_session, name="Cleaning")
        session = await create_conversation_session(
            db_session, profile.id, category_id=category.id
        )
        service = make_search_request_service(db_session)

        search_request = await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=profile.id,
            status="completed",
            category_id=category.id,
            category_name="Cleaning",
            structured_criteria={"category_id": str(category.id), "answers": []},
        )
        await db_session.commit()

        assert search_request.status == SearchRequestStatus.UNMATCHED
        assert search_request.customer_latitude is None
        assert search_request.customer_longitude is None

        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == search_request.id
            )
        )
        assert len(log_result.scalars().all()) == 1

    async def test_a_routed_to_admin_session_with_no_resolved_category_is_honest(
        self, db_session
    ) -> None:
        """The fourth flagged nullable deviation found during
        implementation: `category_id`/`category_name` can legitimately be
        `None` for a `routed_to_admin` session that never resolved a
        category at all -- never fabricated."""
        user = await create_user(db_session, "920000004")
        profile = await create_customer_profile(db_session, user)
        session = await create_conversation_session(db_session, profile.id)
        service = make_search_request_service(db_session)

        search_request = await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=profile.id,
            status="routed_to_admin",
            category_id=None,
            category_name=None,
            structured_criteria=None,
        )
        await db_session.commit()

        assert search_request.category_id is None
        assert search_request.status == SearchRequestStatus.PENDING_MANUAL_MATCH


class TestHandleSessionCompletedManualPath:
    async def test_routed_to_admin_creates_exactly_one_pending_manual_match_assignment(
        self, db_session
    ) -> None:
        user = await create_user(db_session, "920000010")
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

        assert search_request.status == SearchRequestStatus.PENDING_MANUAL_MATCH
        assert search_request.structured_criteria is None

        result = await db_session.execute(
            select(ManualMatchAssignment).where(
                ManualMatchAssignment.conversation_session_id == session.id
            )
        )
        assignments = result.scalars().all()
        assert len(assignments) == 1
        assert assignments[0].status == "pending"
        assert assignments[0].assigned_admin_id is None
        assert assignments[0].search_request_id == search_request.id

        # AC6: no `search_event_log` row yet -- only written at resolution.
        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == search_request.id
            )
        )
        assert log_result.scalars().all() == []


class TestResolveManualMatch:
    async def test_resolving_with_provider_ids_produces_matched_and_ranked_matches(
        self, db_session
    ) -> None:
        user = await create_user(db_session, "920000020")
        profile = await create_customer_profile(db_session, user)
        category = await create_category(db_session, name="Plumbing")
        provider_a = await create_discoverable_provider(
            db_session, category_label="Plumbing", display_name="Provider A"
        )
        provider_b = await create_discoverable_provider(
            db_session, category_label="Plumbing", display_name="Provider B"
        )
        session = await create_conversation_session(
            db_session, profile.id, category_id=category.id
        )
        service = make_search_request_service(db_session)

        await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=profile.id,
            status="routed_to_admin",
            category_id=category.id,
            category_name="Plumbing",
            structured_criteria=None,
        )
        await db_session.commit()

        assignment_result = await db_session.execute(
            select(ManualMatchAssignment).where(
                ManualMatchAssignment.conversation_session_id == session.id
            )
        )
        assignment = assignment_result.scalar_one()

        admin = await create_user(db_session, "920000021")
        resolved = await service.resolve_manual_match(
            assignment.id,
            admin_user_id=admin.id,
            provider_ids=[provider_b.id, provider_a.id],
        )
        await db_session.commit()

        assert resolved.status == SearchRequestStatus.MATCHED
        matched = await service.get_matched_providers(resolved)
        assert [m.id for m in matched] == [provider_b.id, provider_a.id]

        refreshed_assignment = await db_session.get(
            ManualMatchAssignment, assignment.id
        )
        assert refreshed_assignment.status == "completed"
        assert refreshed_assignment.assigned_admin_id == admin.id

        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == resolved.id
            )
        )
        logs = log_result.scalars().all()
        assert len(logs) == 1
        assert logs[0].was_matched is True
        assert logs[0].result_count == 2

    async def test_resolving_with_an_empty_list_produces_unmatched_not_an_error(
        self, db_session
    ) -> None:
        """Decision 4: an empty `provider_ids` list is valid -- 'no
        viable match found' resolves to `unmatched`, never an error."""
        user = await create_user(db_session, "920000022")
        profile = await create_customer_profile(db_session, user)
        category = await create_category(db_session, name="Plumbing")
        session = await create_conversation_session(
            db_session, profile.id, category_id=category.id
        )
        service = make_search_request_service(db_session)

        await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=profile.id,
            status="routed_to_admin",
            category_id=category.id,
            category_name="Plumbing",
            structured_criteria=None,
        )
        await db_session.commit()

        assignment_result = await db_session.execute(
            select(ManualMatchAssignment).where(
                ManualMatchAssignment.conversation_session_id == session.id
            )
        )
        assignment = assignment_result.scalar_one()
        admin = await create_user(db_session, "920000023")

        resolved = await service.resolve_manual_match(
            assignment.id, admin_user_id=admin.id, provider_ids=[]
        )
        await db_session.commit()

        assert resolved.status == SearchRequestStatus.UNMATCHED
        matched = await service.get_matched_providers(resolved)
        assert matched == []

    async def test_resolving_a_nonexistent_assignment_raises_not_found(
        self, db_session
    ) -> None:
        service = make_search_request_service(db_session)

        try:
            await service.resolve_manual_match(
                uuid.uuid4(), admin_user_id=uuid.uuid4(), provider_ids=[]
            )
            raise AssertionError("expected ManualMatchAssignmentNotFoundError")
        except ManualMatchAssignmentNotFoundError:
            pass

    async def test_a_bogus_provider_id_raises_invalid_provider_ids_before_any_write(
        self, db_session
    ) -> None:
        """A non-existent `provider_id` is rejected before any of
        `_finalize_matches`'s mutations happen -- the assignment must
        still be `pending` and no `search_event_log` row is written."""
        user = await create_user(db_session, "920000024")
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

        assignment_result = await db_session.execute(
            select(ManualMatchAssignment).where(
                ManualMatchAssignment.conversation_session_id == session.id
            )
        )
        assignment = assignment_result.scalar_one()
        admin = await create_user(db_session, "920000025")

        with pytest.raises(InvalidManualMatchProviderIdsError):
            await service.resolve_manual_match(
                assignment.id,
                admin_user_id=admin.id,
                provider_ids=[uuid.uuid4()],
            )

        refreshed_assignment = await db_session.get(
            ManualMatchAssignment, assignment.id
        )
        assert refreshed_assignment.status == "pending"

        log_result = await db_session.execute(
            select(SearchEventLog).where(
                SearchEventLog.search_request_id == search_request.id
            )
        )
        assert log_result.scalars().all() == []


class TestGetResultForCustomer:
    async def test_a_stranger_cannot_read_another_customers_search_request(
        self, db_session
    ) -> None:
        owner_user = await create_user(db_session, "920000030")
        owner_profile = await create_customer_profile(db_session, owner_user)
        stranger_user = await create_user(db_session, "920000031")
        await create_customer_profile(db_session, stranger_user)
        category = await create_category(db_session, name="Plumbing")
        session = await create_conversation_session(
            db_session, owner_profile.id, category_id=category.id
        )
        service = make_search_request_service(db_session)

        search_request = await service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=owner_profile.id,
            status="completed",
            category_id=category.id,
            category_name="Plumbing",
            structured_criteria={"category_id": str(category.id), "answers": []},
        )
        await db_session.commit()

        try:
            await service.get_result_for_customer(stranger_user.id, search_request.id)
            raise AssertionError("expected SearchRequestNotFoundError")
        except SearchRequestNotFoundError:
            pass

    async def test_the_owner_can_read_their_own_search_request(
        self, db_session
    ) -> None:
        user = await create_user(db_session, "920000032")
        profile = await create_customer_profile(db_session, user)
        category = await create_category(db_session, name="Plumbing")
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

        fetched = await service.get_result_for_customer(user.id, search_request.id)
        assert fetched.id == search_request.id


class TestGetSearchRequestIdForSession:
    async def test_returns_none_for_a_session_with_no_search_request_yet(
        self, db_session
    ) -> None:
        service = make_search_request_service(db_session)

        result = await service.get_search_request_id_for_session(uuid.uuid4())

        assert result is None

    async def test_returns_the_id_once_one_exists(self, db_session) -> None:
        user = await create_user(db_session, "920000040")
        profile = await create_customer_profile(db_session, user)
        category = await create_category(db_session, name="Plumbing")
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

        result = await service.get_search_request_id_for_session(session.id)

        assert result == search_request.id
