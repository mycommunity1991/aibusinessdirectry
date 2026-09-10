"""
Integration tests for `ManualMatchAssignmentService`/
`ManualMatchAssignmentRepository` (AI-002, Decision 3,
`Plan_S07_AI-002.md`), exercised against a real Postgres database (see
`tests/conftest.py`'s `db_session` fixture) -- mirrors
`test_claim_review_request_service.py`'s pattern exactly, since this is
the fourth application of the same passive-queue-row shape.
"""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import (
    ManualMatchAssignmentAlreadyResolvedError,
    ManualMatchAssignmentNotFoundError,
)
from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.category.models import Category
from app.modules.conversation.models import ConversationSession
from app.modules.customer.models import CustomerProfile
from app.modules.identity.models import AuthProvider, User


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_customer_profile(db_session, user: User) -> CustomerProfile:
    profile = CustomerProfile(user_id=user.id, display_name="Test Customer")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _make_conversation_session(db_session, customer_id: uuid.UUID):
    category = Category(
        name="Plumbing",
        name_ar=None,
        slug=f"plumbing-{uuid.uuid4().hex[:8]}",
        sort_order=0,
    )
    db_session.add(category)
    await db_session.flush()
    session = ConversationSession(customer_id=customer_id, category_id=category.id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


def _service(db_session) -> ManualMatchAssignmentService:
    return ManualMatchAssignmentService(ManualMatchAssignmentRepository(db_session))


class TestCreate:
    async def test_create_persists_a_pending_assignment_with_no_assigned_admin(
        self, db_session
    ) -> None:
        """Decision 2a: `assigned_admin_id` is `NULL` at creation --
        mirrors `claim_review_requests.reviewed_by`'s nullable-until-
        resolved shape."""
        user = await _make_user(db_session, "910000001")
        profile = await _make_customer_profile(db_session, user)
        session = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)

        assignment = await service.create(
            conversation_session_id=session.id, search_request_id=None
        )
        await db_session.commit()

        assert assignment.id is not None
        assert assignment.status == "pending"
        assert assignment.conversation_session_id == session.id
        assert assignment.search_request_id is None
        assert assignment.assigned_admin_id is None
        assert assignment.completed_at is None


class TestListPending:
    async def test_only_pending_assignments_are_listed(self, db_session) -> None:
        user = await _make_user(db_session, "910000002")
        admin = await _make_user(db_session, "910000003")
        profile = await _make_customer_profile(db_session, user)
        session_a = await _make_conversation_session(db_session, profile.id)
        session_b = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)

        pending = await service.create(
            conversation_session_id=session_a.id, search_request_id=None
        )
        resolved = await service.create(
            conversation_session_id=session_b.id, search_request_id=None
        )
        await service.resolve(resolved.id, admin_user_id=admin.id)
        await db_session.commit()

        assignments, total = await service.list_pending(page=1, page_size=10)

        assert total == 1
        assert [a.id for a in assignments] == [pending.id]

    async def test_oldest_first_ordering(self, db_session) -> None:
        user = await _make_user(db_session, "910000004")
        profile = await _make_customer_profile(db_session, user)
        session_a = await _make_conversation_session(db_session, profile.id)
        session_b = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)

        first = await service.create(
            conversation_session_id=session_a.id, search_request_id=None
        )
        second = await service.create(
            conversation_session_id=session_b.id, search_request_id=None
        )
        await db_session.commit()

        assignments, total = await service.list_pending(page=1, page_size=10)

        assert total == 2
        assert [a.id for a in assignments] == [first.id, second.id]


class TestResolve:
    async def test_resolve_sets_assigned_admin_and_completed_at(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "910000005")
        admin = await _make_user(db_session, "910000006")
        profile = await _make_customer_profile(db_session, user)
        session = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)
        assignment = await service.create(
            conversation_session_id=session.id, search_request_id=None
        )

        resolved = await service.resolve(assignment.id, admin_user_id=admin.id)
        await db_session.commit()

        assert resolved.status == "completed"
        assert resolved.assigned_admin_id == admin.id
        assert resolved.completed_at is not None

    async def test_resolving_a_nonexistent_id_raises_not_found(
        self, db_session
    ) -> None:
        service = _service(db_session)

        with pytest.raises(ManualMatchAssignmentNotFoundError):
            await service.resolve(uuid.uuid4(), admin_user_id=uuid.uuid4())

    async def test_resolving_an_already_resolved_assignment_raises(
        self, db_session
    ) -> None:
        """AC4/AC6's 'identical shape, exactly once' guarantee -- an
        already-resolved assignment can never be silently double-
        finalized."""
        user = await _make_user(db_session, "910000007")
        admin = await _make_user(db_session, "910000008")
        profile = await _make_customer_profile(db_session, user)
        session = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)
        assignment = await service.create(
            conversation_session_id=session.id, search_request_id=None
        )
        await service.resolve(assignment.id, admin_user_id=admin.id)
        await db_session.commit()

        with pytest.raises(ManualMatchAssignmentAlreadyResolvedError):
            await service.resolve(assignment.id, admin_user_id=admin.id)

    async def test_get_by_id_returns_none_for_a_nonexistent_id(
        self, db_session
    ) -> None:
        service = _service(db_session)

        result = await service.get_by_id(uuid.uuid4())

        assert result is None


class TestTryResolveAtomicity:
    """
    Proves `ManualMatchAssignmentRepository.try_resolve`'s conditional
    `UPDATE ... WHERE status = 'pending'` predicate genuinely closes the
    read-then-write race a plain fetch-then-update left open (the
    already-fixed sequential double-call bug, commit `9e92438`, does not
    close this: two truly concurrent `resolve` calls on the *same*
    assignment could still both pass a Python-level status check before
    either committed).
    """

    async def test_second_sequential_try_resolve_call_returns_false(
        self, db_session
    ) -> None:
        """The minimal, single-session proof the atomic predicate itself
        works: once the first `UPDATE` has committed the row out of
        `pending`, a second call's `WHERE status = 'pending'` predicate
        matches zero rows."""
        user = await _make_user(db_session, "910000009")
        admin = await _make_user(db_session, "910000010")
        profile = await _make_customer_profile(db_session, user)
        session = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)
        assignment = await service.create(
            conversation_session_id=session.id, search_request_id=None
        )
        await db_session.commit()

        first = await service.repository.try_resolve(
            assignment.id,
            admin_user_id=admin.id,
            completed_at=datetime.now(UTC),
        )
        await db_session.commit()

        second = await service.repository.try_resolve(
            assignment.id,
            admin_user_id=admin.id,
            completed_at=datetime.now(UTC),
        )
        await db_session.commit()

        assert first is True
        assert second is False

    async def test_two_concurrent_resolve_calls_on_the_same_assignment_only_one_wins(
        self, db_engine: AsyncEngine, db_session
    ) -> None:
        """
        The genuine concurrency proof: two truly concurrent `resolve()`
        calls on the *same* assignment, each via its own independent
        `AsyncSession`/transaction, must result in exactly one winner and
        one `ManualMatchAssignmentAlreadyResolvedError` -- never both
        silently "succeeding" (which would append a second, duplicate
        `provider_matches` batch and a second `search_event_log` row for
        one `search_requests` row). Mirrors `test_admin_claim_service.
        py`'s `TestConcurrentClaimRace` and `test_admin_verification_
        service.py`'s `TestConcurrentApprovalRace`.
        """
        user = await _make_user(db_session, "910000011")
        admin_a = await _make_user(db_session, "910000012")
        admin_b = await _make_user(db_session, "910000013")
        profile = await _make_customer_profile(db_session, user)
        session = await _make_conversation_session(db_session, profile.id)
        service = _service(db_session)
        assignment = await service.create(
            conversation_session_id=session.id, search_request_id=None
        )
        await db_session.commit()

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt(admin_id: uuid.UUID) -> str:
            async with session_factory() as attempt_session:
                attempt_service = ManualMatchAssignmentService(
                    ManualMatchAssignmentRepository(attempt_session)
                )
                try:
                    await attempt_service.resolve(assignment.id, admin_user_id=admin_id)
                    await attempt_session.commit()
                    return "resolved"
                except ManualMatchAssignmentAlreadyResolvedError:
                    await attempt_session.rollback()
                    return "conflict"

        results = await asyncio.gather(_attempt(admin_a.id), _attempt(admin_b.id))

        assert sorted(results) == ["conflict", "resolved"]

        async with session_factory() as verify_session:
            refreshed = await ManualMatchAssignmentRepository(verify_session).get_by_id(
                assignment.id
            )
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.assigned_admin_id in {admin_a.id, admin_b.id}
