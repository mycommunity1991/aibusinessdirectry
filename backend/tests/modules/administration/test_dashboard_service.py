"""
Integration tests for `DashboardService` (ADM-002, Decision 4/5,
`Plan_S11_ADM-002.md`, AC2), exercised against a real Postgres database
-- proves the three headline counts are correct against real fixture
data (never just "endpoint returns 200") and that each `*_queue_path`
matches the real, registered route path exactly.
"""

import uuid
from datetime import UTC, datetime

from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.repositories.unmatched_query_report_repository import (
    UnmatchedQueryReportRepository,
)
from app.modules.administration.services.dashboard_service import (
    OPEN_UNMATCHED_QUERY_REPORT_QUEUE_PATH,
    PENDING_MANUAL_MATCH_QUEUE_PATH,
    PENDING_VERIFICATION_QUEUE_PATH,
    DashboardService,
)
from app.modules.category.models import Category
from app.modules.conversation.models import ConversationSession
from app.modules.customer.models import CustomerProfile
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.verification.models import VerificationRecord, VerificationType
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
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


async def _make_pending_manual_match(db_session, customer_id: uuid.UUID) -> None:
    session = await _make_conversation_session(db_session, customer_id)
    await ManualMatchAssignmentRepository(db_session).create(
        {
            "conversation_session_id": session.id,
            "search_request_id": None,
            "status": "pending",
        }
    )
    await db_session.commit()


async def _make_completed_manual_match(db_session, customer_id: uuid.UUID) -> None:
    session = await _make_conversation_session(db_session, customer_id)
    admin = await _make_user(db_session, f"9{uuid.uuid4().int % 10**8:08d}")
    await ManualMatchAssignmentRepository(db_session).create(
        {
            "conversation_session_id": session.id,
            "search_request_id": None,
            "status": "completed",
            "assigned_admin_id": admin.id,
        }
    )
    await db_session.commit()


async def _make_unmatched_query_report(db_session, *, status: str = "open") -> None:
    log = await SearchEventLogRepository(db_session).create(
        {
            "search_request_id": None,
            "customer_id": None,
            "category_id": None,
            "query_text": None,
            "result_count": 0,
            "was_matched": False,
        }
    )
    await UnmatchedQueryReportRepository(db_session).create(
        {"search_event_log_id": log.id, "status": status}
    )
    await db_session.commit()


async def _make_provider(db_session, owner: User) -> Provider:
    provider = Provider(
        user_id=owner.id,
        provider_type=ProviderType.FREELANCER,
        display_name="Test Provider",
        slug=f"test-provider-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.PENDING,
        is_discoverable=False,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


async def _make_verification_record(
    db_session, provider: Provider, *, status: VerificationStatus
) -> None:
    record = VerificationRecord(
        provider_id=provider.id,
        verification_type=VerificationType.FREELANCER_ID,
        status=status,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(record)
    await db_session.commit()


def _service(db_session) -> DashboardService:
    return DashboardService(
        ManualMatchAssignmentRepository(db_session),
        UnmatchedQueryReportRepository(db_session),
        VerificationRecordRepository(db_session),
    )


class TestGetSummary:
    async def test_counts_are_correct_and_exclude_non_matching_statuses(
        self, db_session
    ) -> None:
        user = await _make_user(db_session, "990000001")
        profile = await _make_customer_profile(db_session, user)

        # Two pending, one completed -- only the pending pair should count.
        await _make_pending_manual_match(db_session, profile.id)
        await _make_pending_manual_match(db_session, profile.id)
        await _make_completed_manual_match(db_session, profile.id)

        # Two open, one actioned -- only the open pair should count.
        await _make_unmatched_query_report(db_session, status="open")
        await _make_unmatched_query_report(db_session, status="open")
        await _make_unmatched_query_report(db_session, status="actioned")

        # One pending, one under_review, one approved -- only the first
        # two should count (`_REVIEWABLE_STATUSES`).
        owner_a = await _make_user(db_session, "990000002")
        owner_b = await _make_user(db_session, "990000003")
        owner_c = await _make_user(db_session, "990000004")
        provider_a = await _make_provider(db_session, owner_a)
        provider_b = await _make_provider(db_session, owner_b)
        provider_c = await _make_provider(db_session, owner_c)
        await _make_verification_record(
            db_session, provider_a, status=VerificationStatus.PENDING
        )
        await _make_verification_record(
            db_session, provider_b, status=VerificationStatus.UNDER_REVIEW
        )
        await _make_verification_record(
            db_session, provider_c, status=VerificationStatus.APPROVED
        )

        service = _service(db_session)
        summary = await service.get_summary()

        assert summary.pending_manual_match_count == 2
        assert summary.open_unmatched_query_report_count == 2
        assert summary.pending_verification_count == 2

    async def test_queue_paths_match_real_registered_routes(self, db_session) -> None:
        service = _service(db_session)

        summary = await service.get_summary()

        assert (
            summary.pending_verification_queue_path == PENDING_VERIFICATION_QUEUE_PATH
        )
        assert summary.pending_verification_queue_path == "/admin/verification/records"
        assert (
            summary.pending_manual_match_queue_path == PENDING_MANUAL_MATCH_QUEUE_PATH
        )
        assert (
            summary.pending_manual_match_queue_path
            == "/admin/search/manual-matches"
        )
        assert (
            summary.open_unmatched_query_report_queue_path
            == OPEN_UNMATCHED_QUERY_REPORT_QUEUE_PATH
        )
        assert (
            summary.open_unmatched_query_report_queue_path
            == "/admin/unmatched-query-reports"
        )

    async def test_zero_counts_when_nothing_exists(self, db_session) -> None:
        service = _service(db_session)

        summary = await service.get_summary()

        assert summary.pending_verification_count == 0
        assert summary.pending_manual_match_count == 0
        assert summary.open_unmatched_query_report_count == 0
