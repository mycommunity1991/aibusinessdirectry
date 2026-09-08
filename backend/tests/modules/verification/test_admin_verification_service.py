"""
Integration tests for `AdminVerificationService` (VER-002) -- the core
of this story's test coverage, exercised against a real Postgres
database (`tests/conftest.py`'s `db_session` fixture) and a real
`LocalFileStorage` writing to a temporary directory.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import (
    VerificationDocumentNotFoundError,
    VerificationRecordNotActionableError,
    VerificationRecordNotFoundError,
)
from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.notification.models import Notification
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.models import VerificationRecord, VerificationType
from app.modules.verification.repositories.verification_document_repository import (
    VerificationDocumentRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)
from app.modules.verification.services.admin_verification_service import (
    AdminVerificationService,
)
from app.shared.storage.local_file_storage import LocalFileStorage


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_provider(db_session, user: User, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "slug": f"jane-the-plumber-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.PENDING,
        "is_discoverable": False,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


async def _create_record(
    db_session, provider: Provider, **overrides: object
) -> VerificationRecord:
    payload: dict[str, object] = {
        "provider_id": provider.id,
        "verification_type": VerificationType.FREELANCER_ID,
        "status": VerificationStatus.PENDING,
        "submitted_at": datetime.now(UTC),
    }
    payload.update(overrides)
    record = VerificationRecord(**payload)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


def _provider_service(db_session) -> ProviderService:
    return ProviderService(
        provider_repository=ProviderRepository(db_session),
        business_profile_repository=BusinessProfileRepository(db_session),
        freelancer_profile_repository=FreelancerProfileRepository(db_session),
        provider_category_label_repository=ProviderCategoryLabelRepository(db_session),
        service_area_repository=ServiceAreaRepository(db_session),
        role_assignment_service=RoleAssignmentService(RoleRepository(db_session)),
    )


def _admin_verification_service(
    db_session, upload_dir: Path
) -> AdminVerificationService:
    return AdminVerificationService(
        verification_record_repository=VerificationRecordRepository(db_session),
        verification_document_repository=VerificationDocumentRepository(db_session),
        provider_service=_provider_service(db_session),
        admin_action_log_service=AdminActionLogService(
            AdminActionLogRepository(db_session)
        ),
        notification_service=NotificationService(NotificationRepository(db_session)),
        verification_file_storage=LocalFileStorage(
            base_directory=str(upload_dir), public_url_prefix=None
        ),
    )


class TestApproveAtomicUpdate:
    async def test_approving_a_freelancer_record_sets_status_and_discoverable(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC2/AC4/AC8: approving, in one call, results in
        `verification_records.status=approved` AND
        `providers.verification_status=approved` AND
        `providers.is_discoverable=true`, read back from the database
        after commit."""
        admin_user = await _create_user(db_session, "1001000001")
        provider_owner = await _create_user(db_session, "1001000002")
        provider = await _create_provider(
            db_session, provider_owner, provider_type=ProviderType.FREELANCER
        )
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)

        approved = await service.approve(admin_user.id, record_id=record.id)
        await db_session.commit()

        assert approved.status == VerificationStatus.APPROVED
        assert approved.reviewed_by == admin_user.id
        assert approved.reviewed_at is not None

        refreshed_record = await VerificationRecordRepository(db_session).get_by_id(
            record.id
        )
        assert refreshed_record is not None
        assert refreshed_record.status == VerificationStatus.APPROVED

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.verification_status == VerificationStatus.APPROVED
        assert refreshed_provider.is_discoverable is True

    async def test_approving_a_business_record_also_sets_discoverable(
        self, db_session, tmp_path: Path
    ) -> None:
        """Decision 5: approving a Business Provider's record also sets
        `is_discoverable=true` -- the less-obvious case, tested
        explicitly."""
        admin_user = await _create_user(db_session, "1001000003")
        provider_owner = await _create_user(db_session, "1001000004")
        provider = await _create_provider(
            db_session, provider_owner, provider_type=ProviderType.BUSINESS
        )
        record = await _create_record(
            db_session,
            provider,
            verification_type=VerificationType.BUSINESS_LIGHTWEIGHT,
        )
        service = _admin_verification_service(db_session, tmp_path)

        await service.approve(admin_user.id, record_id=record.id)
        await db_session.commit()

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.provider_type == ProviderType.BUSINESS
        assert refreshed_provider.verification_status == VerificationStatus.APPROVED
        assert refreshed_provider.is_discoverable is True


class TestDbLevelInvariant:
    async def test_a_raw_bypassing_update_is_rejected_by_the_check_constraint(
        self, db_session
    ) -> None:
        """
        AC4, the single most important test in this story: a raw SQL
        `UPDATE` attempting to set `is_discoverable = true` while
        `verification_status != 'approved'` -- bypassing the service
        and repository layers entirely -- must be rejected by Postgres
        itself, via `chk_providers_discoverable_requires_approved`.
        """
        owner = await _create_user(db_session, "1002000001")
        await _create_provider(
            db_session,
            owner,
            provider_type=ProviderType.FREELANCER,
            verification_status=VerificationStatus.PENDING,
            is_discoverable=False,
        )

        with pytest.raises(IntegrityError):
            await db_session.execute(
                text(
                    "UPDATE provider.providers SET is_discoverable = true "
                    "WHERE verification_status != 'approved'"
                )
            )
        await db_session.rollback()


class TestReject:
    async def test_rejecting_leaves_is_discoverable_false(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC3: rejecting never sets `is_discoverable=true`, for either
        subtype."""
        admin_user = await _create_user(db_session, "1003000001")
        provider_owner = await _create_user(db_session, "1003000002")
        provider = await _create_provider(
            db_session, provider_owner, provider_type=ProviderType.FREELANCER
        )
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)

        rejected = await service.reject(
            admin_user.id, record_id=record.id, rejection_reason="Blurry photo."
        )
        await db_session.commit()

        assert rejected.status == VerificationStatus.REJECTED
        assert rejected.rejection_reason == "Blurry photo."

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.verification_status == VerificationStatus.REJECTED
        assert refreshed_provider.is_discoverable is False

    async def test_rejecting_a_business_record_also_leaves_it_not_discoverable(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1003000003")
        provider_owner = await _create_user(db_session, "1003000004")
        provider = await _create_provider(
            db_session, provider_owner, provider_type=ProviderType.BUSINESS
        )
        record = await _create_record(
            db_session,
            provider,
            verification_type=VerificationType.BUSINESS_LIGHTWEIGHT,
        )
        service = _admin_verification_service(db_session, tmp_path)

        await service.reject(
            admin_user.id, record_id=record.id, rejection_reason="Expired license."
        )
        await db_session.commit()

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.is_discoverable is False


class TestConflictOnAlreadyReviewedRecord:
    async def test_second_approve_on_an_already_approved_record_raises_409(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1004000001")
        owner = await _create_user(db_session, "1004000002")
        provider = await _create_provider(db_session, owner)
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)
        await service.approve(admin_user.id, record_id=record.id)
        await db_session.commit()

        with pytest.raises(VerificationRecordNotActionableError):
            await service.approve(admin_user.id, record_id=record.id)

    async def test_reject_on_an_already_rejected_record_raises_409(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1004000003")
        owner = await _create_user(db_session, "1004000004")
        provider = await _create_provider(db_session, owner)
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)
        await service.reject(admin_user.id, record_id=record.id, rejection_reason="x")
        await db_session.commit()

        with pytest.raises(VerificationRecordNotActionableError):
            await service.reject(
                admin_user.id, record_id=record.id, rejection_reason="y"
            )

    async def test_approve_on_an_already_rejected_record_raises_409(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1004000005")
        owner = await _create_user(db_session, "1004000006")
        provider = await _create_provider(db_session, owner)
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)
        await service.reject(admin_user.id, record_id=record.id, rejection_reason="x")
        await db_session.commit()

        with pytest.raises(VerificationRecordNotActionableError):
            await service.approve(admin_user.id, record_id=record.id)

    async def test_a_nonexistent_record_raises_404_not_409(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1004000007")
        service = _admin_verification_service(db_session, tmp_path)

        with pytest.raises(VerificationRecordNotFoundError):
            await service.approve(admin_user.id, record_id=uuid.uuid4())


class TestConcurrentApprovalRace:
    """
    Regression test for a genuine, empirically-reproduced race condition
    found during VER-002's independent QA review: with a plain
    read-then-write update, two truly concurrent `approve()` calls on
    the *same* record could both pass the in-Python status check before
    either committed, each going on to write its own
    `admin_action_log`/`notification` row for what should be one
    logical action -- violating AC6/AC8's "exactly one" guarantee.

    Fixed by `VerificationRecordRepository.try_claim_for_review`: a
    single conditional `UPDATE ... WHERE status IN (...)`, which
    Postgres itself serializes via row-level locking, so at most one
    caller's `UPDATE` can ever match regardless of true concurrency.

    Uses two independent `AsyncSession`s bound to the same test engine
    so the two `approve()` calls run as genuinely separate Postgres
    transactions/connections -- two calls sharing one session would
    never have exhibited this race at all.
    """

    async def test_two_concurrent_approve_calls_on_the_same_record_only_one_wins(
        self, db_engine: AsyncEngine, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1004500001")
        owner = await _create_user(db_session, "1004500002")
        provider = await _create_provider(
            db_session, owner, provider_type=ProviderType.FREELANCER
        )
        record = await _create_record(db_session, provider)

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt() -> str:
            async with session_factory() as session:
                service = _admin_verification_service(session, tmp_path)
                try:
                    await service.approve(admin_user.id, record_id=record.id)
                    await session.commit()
                    return "approved"
                except VerificationRecordNotActionableError:
                    await session.rollback()
                    return "conflict"

        results = await asyncio.gather(_attempt(), _attempt())

        assert sorted(results) == ["approved", "conflict"]

        action_logs = (
            (
                await db_session.execute(
                    select(AdminActionLog).where(
                        AdminActionLog.target_entity_id == record.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(action_logs) == 1

        notifications = (
            (
                await db_session.execute(
                    select(Notification).where(
                        Notification.related_entity_id == record.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(notifications) == 1


class TestSideEffectRowCounts:
    async def test_approve_creates_exactly_one_notification_and_one_action_log(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC5/AC6: never zero, never duplicated."""
        admin_user = await _create_user(db_session, "1005000001")
        owner = await _create_user(db_session, "1005000002")
        provider = await _create_provider(db_session, owner)
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)

        await service.approve(admin_user.id, record_id=record.id)
        await db_session.commit()

        notifications = (
            (
                await db_session.execute(
                    select(Notification).where(Notification.user_id == owner.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(notifications) == 1
        assert notifications[0].related_entity_id == record.id

        action_logs = (
            (
                await db_session.execute(
                    select(AdminActionLog).where(
                        AdminActionLog.target_entity_id == record.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(action_logs) == 1
        assert action_logs[0].admin_user_id == admin_user.id
        assert action_logs[0].action_type == "verification_approved"

    async def test_reject_creates_exactly_one_notification_and_one_action_log(
        self, db_session, tmp_path: Path
    ) -> None:
        admin_user = await _create_user(db_session, "1005000003")
        owner = await _create_user(db_session, "1005000004")
        provider = await _create_provider(db_session, owner)
        record = await _create_record(db_session, provider)
        service = _admin_verification_service(db_session, tmp_path)

        await service.reject(
            admin_user.id, record_id=record.id, rejection_reason="Bad scan."
        )
        await db_session.commit()

        notifications = (
            (
                await db_session.execute(
                    select(Notification).where(Notification.user_id == owner.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(notifications) == 1

        action_logs = (
            (
                await db_session.execute(
                    select(AdminActionLog).where(
                        AdminActionLog.target_entity_id == record.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(action_logs) == 1
        assert action_logs[0].action_type == "verification_rejected"


class TestListPendingForReviewBatching:
    async def test_batches_provider_lookup_into_exactly_one_query(
        self, db_session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Decision 9: `list_pending_for_review` batch-fetches Provider
        context with exactly ONE `list_by_ids` query for a page
        spanning multiple providers -- asserted via a spy/mock call
        count, not just correct output.
        """
        owner_a = await _create_user(db_session, "1006000001")
        owner_b = await _create_user(db_session, "1006000002")
        provider_a = await _create_provider(db_session, owner_a, display_name="A")
        provider_b = await _create_provider(db_session, owner_b, display_name="B")
        await _create_record(db_session, provider_a)
        await _create_record(db_session, provider_b)

        call_count = 0
        original_list_by_ids = ProviderRepository.list_by_ids

        async def _spy_list_by_ids(self, ids):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            return await original_list_by_ids(self, ids)

        monkeypatch.setattr(ProviderRepository, "list_by_ids", _spy_list_by_ids)

        service = _admin_verification_service(db_session, tmp_path)
        (
            records,
            providers_by_id,
            documents_by_record_id,
            total,
        ) = await service.list_pending_for_review(page=1, page_size=10)

        assert call_count == 1
        assert total == 2
        assert len(records) == 2
        assert provider_a.id in providers_by_id
        assert provider_b.id in providers_by_id
        assert documents_by_record_id[records[0].id] == []

    async def test_orders_oldest_submitted_at_first(
        self, db_session, tmp_path: Path
    ) -> None:
        owner = await _create_user(db_session, "1006000003")
        provider = await _create_provider(db_session, owner)
        older = await _create_record(
            db_session,
            provider,
            submitted_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        newer = await _create_record(
            db_session,
            provider,
            submitted_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        service = _admin_verification_service(db_session, tmp_path)

        records, _providers, _documents, total = await service.list_pending_for_review(
            page=1, page_size=10
        )

        assert total == 2
        assert [record.id for record in records] == [older.id, newer.id]

    async def test_excludes_already_reviewed_records(
        self, db_session, tmp_path: Path
    ) -> None:
        owner = await _create_user(db_session, "1006000004")
        provider = await _create_provider(db_session, owner)
        await _create_record(db_session, provider, status=VerificationStatus.APPROVED)
        pending = await _create_record(
            db_session, provider, status=VerificationStatus.PENDING
        )
        service = _admin_verification_service(db_session, tmp_path)

        records, _providers, _documents, total = await service.list_pending_for_review(
            page=1, page_size=10
        )

        assert total == 1
        assert [record.id for record in records] == [pending.id]


class TestGetDocumentBytesForAdminHasNoOwnershipCheck:
    async def test_document_not_found_raises_404(
        self, db_session, tmp_path: Path
    ) -> None:
        service = _admin_verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentNotFoundError):
            await service.get_document_bytes_for_admin(uuid.uuid4())
