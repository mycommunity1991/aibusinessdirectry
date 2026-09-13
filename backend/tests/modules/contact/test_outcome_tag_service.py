"""
Integration tests for `OutcomeTagService` (REV-001, AC1/AC2/AC5/AC6),
exercised against a real Postgres database -- this story's two
safety-critical mechanisms are verified here with direct row-count
assertions, not merely an exception check: AC2's ownership rejection
(Decision 2) and AC1/AC6's atomic uniqueness enforcement (Decision 3).
"""

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import (
    ContactViewNotFoundError,
    CustomerProfileNotFoundError,
    OutcomeTagAlreadyExistsError,
)
from app.modules.contact.models import OutcomeTag
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.contact.services.outcome_tag_service import OutcomeTagService
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_contact_service,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_outcome_tag_service(db_session) -> OutcomeTagService:
    return OutcomeTagService(
        outcome_tag_repository=OutcomeTagRepository(db_session),
        contact_view_repository=ContactViewRepository(db_session),
        customer_profile_repository=CustomerProfileRepository(db_session),
    )


async def _count_outcome_tags(db_session) -> int:
    result = await db_session.execute(select(OutcomeTag))
    return len(result.scalars().all())


async def _create_contact_view(db_session, *, customer_user_id, provider_id):
    contact_service = make_contact_service(db_session)
    contact_view, _provider = await contact_service.create_contact_view(
        customer_user_id, provider_id=provider_id, search_request_id=None
    )
    await db_session.commit()
    return contact_view


class TestSubmitOutcomeTagHappyPath:
    @pytest.mark.anyio
    async def test_hired_true_succeeds_and_is_retained(self, db_session) -> None:
        customer_user = await create_user(db_session, "601000001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000002")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_outcome_tag_service(db_session)

        outcome_tag = await service.submit_outcome_tag(
            customer_user.id, contact_view_id=contact_view.id, hired=True
        )
        await db_session.commit()

        assert outcome_tag.contact_view_id == contact_view.id
        assert outcome_tag.hired is True
        assert await _count_outcome_tags(db_session) == 1

    @pytest.mark.anyio
    async def test_hired_false_succeeds_and_is_retained_not_discarded(
        self, db_session
    ) -> None:
        """AC5: a 'No' outcome tag is still retained as a signal."""
        customer_user = await create_user(db_session, "601000003")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000004")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_outcome_tag_service(db_session)

        outcome_tag = await service.submit_outcome_tag(
            customer_user.id, contact_view_id=contact_view.id, hired=False
        )
        await db_session.commit()

        result = await db_session.execute(
            select(OutcomeTag).where(OutcomeTag.id == outcome_tag.id)
        )
        persisted = result.scalar_one()
        assert persisted.hired is False


class TestOwnershipRejection:
    """AC2, Decision 2: only the owning customer may submit."""

    @pytest.mark.anyio
    async def test_another_customers_contact_view_is_rejected_with_404(
        self, db_session
    ) -> None:
        owner_customer_user = await create_user(db_session, "601000005")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "601000006")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )

        other_customer_user = await create_user(db_session, "601000007")
        await create_customer_profile(db_session, other_customer_user)
        service = make_outcome_tag_service(db_session)

        with pytest.raises(ContactViewNotFoundError):
            await service.submit_outcome_tag(
                other_customer_user.id,
                contact_view_id=contact_view.id,
                hired=True,
            )

        # No row written for the rejected attempt.
        assert await _count_outcome_tags(db_session) == 0

    @pytest.mark.anyio
    async def test_a_nonexistent_contact_view_id_is_rejected_with_404(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601000008")
        await create_customer_profile(db_session, customer_user)
        service = make_outcome_tag_service(db_session)

        with pytest.raises(ContactViewNotFoundError):
            await service.submit_outcome_tag(
                customer_user.id, contact_view_id=uuid.uuid4(), hired=True
            )

        assert await _count_outcome_tags(db_session) == 0


class TestUniquenessPerContactView:
    """AC1/AC6: one outcome tag per Contact View, enforced atomically."""

    @pytest.mark.anyio
    async def test_a_second_submission_by_the_same_customer_is_rejected(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601000009")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000010")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_outcome_tag_service(db_session)

        await service.submit_outcome_tag(
            customer_user.id, contact_view_id=contact_view.id, hired=True
        )
        await db_session.commit()

        with pytest.raises(OutcomeTagAlreadyExistsError):
            await service.submit_outcome_tag(
                customer_user.id, contact_view_id=contact_view.id, hired=False
            )

        # Exactly one row exists -- the second attempt never wrote a
        # second row, and never mutated the first (AC1/AC6, Decision 3).
        assert await _count_outcome_tags(db_session) == 1
        result = await db_session.execute(
            select(OutcomeTag).where(OutcomeTag.contact_view_id == contact_view.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].hired is True


class TestConcurrentSubmissionRace:
    """
    AC1/AC6, Decision 3 -- the genuine concurrency proof QA holds this
    story to, mirroring `test_manual_match_assignment_service.py`'s
    `TestTryResolveAtomicity.
    test_two_concurrent_resolve_calls_on_the_same_assignment_only_one_wins`
    and `test_admin_claim_service.py`'s `TestConcurrentClaimRace`: two
    truly concurrent `submit_outcome_tag` calls against the *same*
    `contact_view_id`, each via its own independent `AsyncSession`/
    transaction (never the same session -- that would only prove the
    Python-level sequencing works, not that the database-level `ON
    CONFLICT` predicate itself closes the race), must result in exactly
    one winner and exactly one persisted row -- never both silently
    succeeding (which would violate `uq_outcome_tags_contact_view_id`
    in spirit even if the unique index itself happened to catch it).
    """

    @pytest.mark.anyio
    async def test_two_concurrent_submissions_for_the_same_contact_view_only_one_wins(
        self, db_engine: AsyncEngine, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601000016")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000017")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt(hired: bool) -> str:
            async with session_factory() as attempt_session:
                attempt_service = OutcomeTagService(
                    outcome_tag_repository=OutcomeTagRepository(attempt_session),
                    contact_view_repository=ContactViewRepository(attempt_session),
                    customer_profile_repository=CustomerProfileRepository(
                        attempt_session
                    ),
                )
                try:
                    await attempt_service.submit_outcome_tag(
                        customer_user.id,
                        contact_view_id=contact_view.id,
                        hired=hired,
                    )
                    await attempt_session.commit()
                    return "submitted"
                except OutcomeTagAlreadyExistsError:
                    await attempt_session.rollback()
                    return "conflict"

        results = await asyncio.gather(_attempt(True), _attempt(False))

        # Exactly one winner, exactly one conflict -- never both
        # "submitted" (which would mean the atomic INSERT genuinely
        # raced) and never both "conflict" (which would mean neither
        # attempt's write actually landed).
        assert sorted(results) == ["conflict", "submitted"]

        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(OutcomeTag).where(
                    OutcomeTag.contact_view_id == contact_view.id
                )
            )
            rows = result.scalars().all()
        assert len(rows) == 1


class TestNoOutcomeTagIsAValidState:
    """AC5: a Contact View with no outcome tag at all is a fine,
    unexceptional state -- nothing is synthesized."""

    @pytest.mark.anyio
    async def test_a_contact_view_with_no_outcome_tag_has_zero_rows(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "601000011")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "601000012")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        result = await db_session.execute(
            select(OutcomeTag).where(OutcomeTag.contact_view_id == contact_view.id)
        )
        assert result.scalars().all() == []


class TestCustomerProfileDefensiveCheck:
    @pytest.mark.anyio
    async def test_raises_if_the_caller_has_no_customer_profile(
        self, db_session
    ) -> None:
        customer_user_without_profile = await create_user(db_session, "601000013")
        owner_customer_user = await create_user(db_session, "601000014")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "601000015")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )
        service = make_outcome_tag_service(db_session)

        with pytest.raises(CustomerProfileNotFoundError):
            await service.submit_outcome_tag(
                customer_user_without_profile.id,
                contact_view_id=contact_view.id,
                hired=True,
            )
