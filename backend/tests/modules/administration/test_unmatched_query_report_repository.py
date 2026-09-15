"""
Repository-level tests for `UnmatchedQueryReportRepository` (ADM-001,
Decision 7/8, `Plan_S11_ADM-001.md`) -- `try_transition_status`'s atomic-
race behavior (mirrors `test_manual_match_assignment_service.py`'s
`TestTryResolveAtomicity`) and `list_filtered`'s SQL-level correctness
independent of the service layer.
"""

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)


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


async def _make_search_event_log(db_session):
    repository = SearchEventLogRepository(db_session)
    log = await repository.create(
        {
            "search_request_id": None,
            "customer_id": None,
            "category_id": None,
            "query_text": None,
            "result_count": 0,
            "was_matched": False,
        }
    )
    await db_session.commit()
    return log


class TestListFiltered:
    async def test_filters_by_status(self, db_session) -> None:
        repository = UnmatchedQueryReportRepository(db_session)
        log_open = await _make_search_event_log(db_session)
        log_actioned = await _make_search_event_log(db_session)
        open_report = await repository.create(
            {"search_event_log_id": log_open.id, "status": "open"}
        )
        await repository.create(
            {"search_event_log_id": log_actioned.id, "status": "actioned"}
        )
        await db_session.commit()

        reports, total = await repository.list_filtered(
            status="open", sort_desc=False, offset=0, limit=10
        )

        assert total == 1
        assert [r.id for r in reports] == [open_report.id]

    async def test_no_status_filter_returns_every_row(self, db_session) -> None:
        repository = UnmatchedQueryReportRepository(db_session)
        log_a = await _make_search_event_log(db_session)
        log_b = await _make_search_event_log(db_session)
        await repository.create({"search_event_log_id": log_a.id, "status": "open"})
        await repository.create(
            {"search_event_log_id": log_b.id, "status": "actioned"}
        )
        await db_session.commit()

        reports, total = await repository.list_filtered(
            status=None, sort_desc=False, offset=0, limit=10
        )

        assert total == 2
        assert len(reports) == 2


class TestTryTransitionStatusAtomicity:
    async def test_second_sequential_call_returns_false(self, db_session) -> None:
        """The minimal, single-session proof the atomic predicate itself
        works: once the first `UPDATE` has committed the row out of
        `open`, a second call's `WHERE status IN ('open',)` predicate
        matches zero rows."""
        admin = await _make_user(db_session, "960000001")
        repository = UnmatchedQueryReportRepository(db_session)
        log = await _make_search_event_log(db_session)
        report = await repository.create(
            {"search_event_log_id": log.id, "status": "open"}
        )
        await db_session.commit()

        first = await repository.try_transition_status(
            report.id,
            from_statuses=("open",),
            to_status="reviewed",
            admin_user_id=admin.id,
            reviewed_at=datetime.now(UTC),
            category_gap_notes=None,
        )
        await db_session.commit()

        second = await repository.try_transition_status(
            report.id,
            from_statuses=("open",),
            to_status="reviewed",
            admin_user_id=admin.id,
            reviewed_at=datetime.now(UTC),
            category_gap_notes=None,
        )
        await db_session.commit()

        assert first is True
        assert second is False

    async def test_two_concurrent_calls_on_the_same_report_only_one_wins(
        self, db_engine: AsyncEngine, db_session
    ) -> None:
        """
        The genuine concurrency proof: two truly concurrent
        `try_transition_status` calls on the *same* report, each via its
        own independent `AsyncSession`/transaction, must result in
        exactly one winner -- never both silently succeeding. Mirrors
        `test_manual_match_assignment_service.py`'s
        `TestTryResolveAtomicity.
        test_two_concurrent_resolve_calls_on_the_same_assignment_only_one_wins`.
        """
        admin_a = await _make_user(db_session, "960000002")
        admin_b = await _make_user(db_session, "960000003")
        repository = UnmatchedQueryReportRepository(db_session)
        log = await _make_search_event_log(db_session)
        report = await repository.create(
            {"search_event_log_id": log.id, "status": "open"}
        )
        await db_session.commit()

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt(admin_id: uuid.UUID) -> bool:
            async with session_factory() as attempt_session:
                attempt_repository = UnmatchedQueryReportRepository(attempt_session)
                won = await attempt_repository.try_transition_status(
                    report.id,
                    from_statuses=("open",),
                    to_status="reviewed",
                    admin_user_id=admin_id,
                    reviewed_at=datetime.now(UTC),
                    category_gap_notes=None,
                )
                await attempt_session.commit()
                return won

        results = await asyncio.gather(_attempt(admin_a.id), _attempt(admin_b.id))

        assert sorted(results) == [False, True]

        async with session_factory() as verify_session:
            refreshed = await UnmatchedQueryReportRepository(verify_session).get_by_id(
                report.id
            )
        assert refreshed is not None
        assert refreshed.status == "reviewed"
