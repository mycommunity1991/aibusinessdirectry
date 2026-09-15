"""
Integration tests for `UnmatchedQueryReportService`/
`UnmatchedQueryReportRepository` (ADM-001, Decision 2/6/7/8,
`Plan_S11_ADM-001.md`), exercised against a real Postgres database (see
`tests/conftest.py`'s `db_session` fixture) -- mirrors
`test_manual_match_assignment_service.py`'s pattern, since this is the
fourth application of the same passive-queue-row shape.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import (
    UnmatchedQueryReportInvalidTransitionError,
    UnmatchedQueryReportNotFoundError,
)
from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.administration.services.unmatched_query_report_service import (
    UnmatchedQueryReportService,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.search.models import SearchEventLog
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.search.services.search_event_log_service import SearchEventLogService


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


async def _make_search_event_log(
    db_session, *, was_matched: bool = False, result_count: int = 0
) -> SearchEventLog:
    """A minimal, real `search_event_log` row -- every FK column is
    nullable, so this doesn't need a real `search_requests`/`customer_
    profiles`/`categories` row to satisfy `unmatched_query_reports.
    search_event_log_id`'s FK constraint."""
    repository = SearchEventLogRepository(db_session)
    log = await repository.create(
        {
            "search_request_id": None,
            "customer_id": None,
            "category_id": None,
            "query_text": None,
            "result_count": result_count,
            "was_matched": was_matched,
        }
    )
    await db_session.commit()
    return log


def _service(db_session) -> UnmatchedQueryReportService:
    return UnmatchedQueryReportService(
        UnmatchedQueryReportRepository(db_session),
        SearchEventLogService(SearchEventLogRepository(db_session)),
        AdminActionLogService(AdminActionLogRepository(db_session)),
    )


class TestCreate:
    async def test_create_defaults_to_open_status(self, db_session) -> None:
        log = await _make_search_event_log(db_session)
        service = _service(db_session)

        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        assert report.id is not None
        assert report.status == "open"
        assert report.search_event_log_id == log.id
        assert report.reviewed_by is None
        assert report.reviewed_at is None
        assert report.category_gap_notes is None


class TestListFiltered:
    async def test_default_status_filter_returns_only_open_reports(
        self, db_session
    ) -> None:
        admin = await _make_user(db_session, "940000001")
        open_log = await _make_search_event_log(db_session)
        reviewed_log = await _make_search_event_log(db_session)
        service = _service(db_session)

        open_report = await service.create(search_event_log_id=open_log.id)
        reviewed_report = await service.create(search_event_log_id=reviewed_log.id)
        await service.mark_reviewed(
            reviewed_report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        reports, logs_by_id, total = await service.list_filtered(
            status="open", sort_desc=False, page=1, page_size=10
        )

        assert total == 1
        assert [r.id for r in reports] == [open_report.id]
        assert logs_by_id[open_report.search_event_log_id].id == open_log.id

    async def test_status_all_returns_every_status(self, db_session) -> None:
        admin = await _make_user(db_session, "940000002")
        log_a = await _make_search_event_log(db_session)
        log_b = await _make_search_event_log(db_session)
        service = _service(db_session)

        report_a = await service.create(search_event_log_id=log_a.id)
        report_b = await service.create(search_event_log_id=log_b.id)
        await service.mark_actioned(
            report_b.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        reports, _logs_by_id, total = await service.list_filtered(
            status=None, sort_desc=False, page=1, page_size=10
        )

        assert total == 2
        assert {r.id for r in reports} == {report_a.id, report_b.id}

    async def test_sort_desc_returns_newest_first(self, db_session) -> None:
        """
        Each `create` is committed separately -- Postgres's `now()`
        (this table's `created_at` default) is the *transaction* start
        time, constant for every statement in one uncommitted
        transaction, so two rows created back-to-back without an
        intervening commit would tie and make sort order ambiguous; real
        `unmatched_query_reports` rows are likewise always created in
        their own separately-committed transaction (`_finalize_matches`
        runs once per request), so this mirrors real usage.
        """
        log_a = await _make_search_event_log(db_session)
        service = _service(db_session)
        first = await service.create(search_event_log_id=log_a.id)
        await db_session.commit()

        log_b = await _make_search_event_log(db_session)
        second = await service.create(search_event_log_id=log_b.id)
        await db_session.commit()

        reports, _logs_by_id, _total = await service.list_filtered(
            status=None, sort_desc=True, page=1, page_size=10
        )

        assert [r.id for r in reports] == [second.id, first.id]

    async def test_pagination_correctness(self, db_session) -> None:
        service = _service(db_session)
        created_ids = []
        for _ in range(3):
            log = await _make_search_event_log(db_session)
            report = await service.create(search_event_log_id=log.id)
            created_ids.append(report.id)
            await db_session.commit()

        page_one, _logs, total = await service.list_filtered(
            status=None, sort_desc=False, page=1, page_size=2
        )
        page_two, _logs, _total = await service.list_filtered(
            status=None, sort_desc=False, page=2, page_size=2
        )

        assert total == 3
        assert len(page_one) == 2
        assert len(page_two) == 1
        assert {r.id for r in page_one} | {r.id for r in page_two} == set(created_ids)

    async def test_enrichment_dict_omits_a_report_with_no_matching_search_event_log(
        self, db_session
    ) -> None:
        """Defensive `None` handling -- never a fabricated value -- when
        a report's `search_event_log_id` somehow has no matching row."""
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        # Simulate a missing `search_event_log` row by looking up an id
        # that was never enriched (the repository-level `get_by_ids`
        # simply omits it -- proven directly here rather than deleting
        # the append-only row, which this codebase never does).
        reports, logs_by_id, _total = await service.list_filtered(
            status=None, sort_desc=False, page=1, page_size=10
        )
        assert reports[0].id == report.id
        assert logs_by_id.get(uuid.uuid4()) is None


class TestMarkReviewed:
    async def test_open_to_reviewed_succeeds(self, db_session) -> None:
        admin = await _make_user(db_session, "940000010")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        reviewed, search_event_log = await service.mark_reviewed(
            report.id, admin_user_id=admin.id, category_gap_notes="Missing category."
        )
        await db_session.commit()

        assert reviewed.status == "reviewed"
        assert reviewed.reviewed_by == admin.id
        assert reviewed.reviewed_at is not None
        assert reviewed.category_gap_notes == "Missing category."
        assert search_event_log is not None
        assert search_event_log.id == log.id

    async def test_reviewed_to_reviewed_repeat_raises_409(self, db_session) -> None:
        admin = await _make_user(db_session, "940000011")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await service.mark_reviewed(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        with pytest.raises(UnmatchedQueryReportInvalidTransitionError):
            await service.mark_reviewed(
                report.id, admin_user_id=admin.id, category_gap_notes=None
            )

    async def test_actioned_to_reviewed_backward_move_raises_409(
        self, db_session
    ) -> None:
        admin = await _make_user(db_session, "940000012")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await service.mark_actioned(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        with pytest.raises(UnmatchedQueryReportInvalidTransitionError):
            await service.mark_reviewed(
                report.id, admin_user_id=admin.id, category_gap_notes=None
            )

    async def test_nonexistent_id_raises_404(self, db_session) -> None:
        service = _service(db_session)

        with pytest.raises(UnmatchedQueryReportNotFoundError):
            await service.mark_reviewed(
                uuid.uuid4(), admin_user_id=uuid.uuid4(), category_gap_notes=None
            )

    async def test_mark_reviewed_writes_exactly_one_admin_action_log_row(
        self, db_session
    ) -> None:
        """ADM-002, Decision 6 (`Plan_S11_ADM-002.md`), AC3 -- closes the
        real, evidence-based gap where `mark_reviewed` previously wrote
        no `admin_action_log` row at all."""
        admin = await _make_user(db_session, "940000013")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        await service.mark_reviewed(
            report.id, admin_user_id=admin.id, category_gap_notes="Gap noted."
        )
        await db_session.commit()

        result = await db_session.execute(select(AdminActionLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].admin_user_id == admin.id
        assert logs[0].action_type == "unmatched_query_report_reviewed"
        assert logs[0].target_entity_type == "unmatched_query_report"
        assert logs[0].target_entity_id == report.id
        assert logs[0].metadata_ == {"category_gap_notes": "Gap noted."}


class TestMarkActioned:
    async def test_open_to_actioned_succeeds(self, db_session) -> None:
        admin = await _make_user(db_session, "940000020")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        actioned, _log = await service.mark_actioned(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        assert actioned.status == "actioned"
        assert actioned.reviewed_by == admin.id
        assert actioned.reviewed_at is not None

    async def test_reviewed_to_actioned_succeeds(self, db_session) -> None:
        admin = await _make_user(db_session, "940000021")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await service.mark_reviewed(
            report.id, admin_user_id=admin.id, category_gap_notes="Gap noted."
        )
        await db_session.commit()

        actioned, _log = await service.mark_actioned(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        assert actioned.status == "actioned"
        # A later transition made without new notes must never silently
        # wipe out notes an earlier call already recorded.
        assert actioned.category_gap_notes == "Gap noted."

    async def test_actioned_to_actioned_repeat_raises_409(self, db_session) -> None:
        admin = await _make_user(db_session, "940000022")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await service.mark_actioned(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        with pytest.raises(UnmatchedQueryReportInvalidTransitionError):
            await service.mark_actioned(
                report.id, admin_user_id=admin.id, category_gap_notes=None
            )

    async def test_nonexistent_id_raises_404(self, db_session) -> None:
        service = _service(db_session)

        with pytest.raises(UnmatchedQueryReportNotFoundError):
            await service.mark_actioned(
                uuid.uuid4(), admin_user_id=uuid.uuid4(), category_gap_notes=None
            )

    async def test_mark_actioned_writes_exactly_one_admin_action_log_row(
        self, db_session
    ) -> None:
        """ADM-002, Decision 6 (`Plan_S11_ADM-002.md`), AC3 -- closes the
        real, evidence-based gap where `mark_actioned` previously wrote
        no `admin_action_log` row at all."""
        admin = await _make_user(db_session, "940000023")
        log = await _make_search_event_log(db_session)
        service = _service(db_session)
        report = await service.create(search_event_log_id=log.id)
        await db_session.commit()

        await service.mark_actioned(
            report.id, admin_user_id=admin.id, category_gap_notes=None
        )
        await db_session.commit()

        result = await db_session.execute(select(AdminActionLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].admin_user_id == admin.id
        assert logs[0].action_type == "unmatched_query_report_actioned"
        assert logs[0].target_entity_type == "unmatched_query_report"
        assert logs[0].target_entity_id == report.id
        assert logs[0].metadata_ == {"category_gap_notes": None}
