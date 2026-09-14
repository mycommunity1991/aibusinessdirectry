"""
Integration tests for `ReviewService` (REV-002, AC1/AC2/AC3/AC4/AC5/AC7),
exercised against a real Postgres database -- this story's two
safety-critical mechanisms are verified here with direct row-count/
value assertions, not merely an exception check: AC2's anchor-
verification rejection (Decision 5) and AC4's race-safe rating
recalculation (Decision 3), including a genuine concurrency test and a
same-transaction rollback test.
"""

import asyncio
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import (
    ContactViewNotFoundError,
    CustomerProfileNotFoundError,
    ReviewAlreadyExistsError,
    ReviewAnchorNotVerifiedError,
    SelfDealingContactError,
)
from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.provider.models import Provider
from app.modules.review.models import ProviderRatingSummary, Review
from app.modules.review.repositories.provider_rating_summary_repository import (
    ProviderRatingSummaryRepository,
)
from app.modules.review.repositories.review_repository import ReviewRepository
from app.modules.review.services.review_service import ReviewService

from ._helpers import (
    create_contact_view,
    create_customer_profile,
    create_hired_contact_view,
    create_provider,
    create_user,
    make_contact_service,
    make_outcome_tag_service,
    make_provider_service,
    make_review_service,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _count_reviews(db_session) -> int:
    result = await db_session.execute(select(Review))
    return len(result.scalars().all())


async def _get_rating_summary(db_session, provider_id) -> ProviderRatingSummary | None:
    result = await db_session.execute(
        select(ProviderRatingSummary).where(
            ProviderRatingSummary.provider_id == provider_id
        )
    )
    return result.scalar_one_or_none()


async def _get_provider(db_session, provider_id) -> Provider:
    result = await db_session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    return result.scalar_one()


class TestSubmitReviewHappyPath:
    @pytest.mark.anyio
    async def test_with_comment_creates_one_row_and_recalculates_summary(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "701000001")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000002")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_review_service(db_session)

        review = await service.submit_review(
            customer_user.id,
            contact_view_id=contact_view.id,
            rating=5,
            comment="Great job, on time and tidy.",
        )
        await db_session.commit()

        assert review.contact_view_id == contact_view.id
        assert review.provider_id == provider.id
        assert review.rating == 5
        assert review.comment == "Great job, on time and tidy."
        assert await _count_reviews(db_session) == 1

        summary = await _get_rating_summary(db_session, provider.id)
        assert summary is not None
        assert summary.average_rating == Decimal("5.00")
        assert summary.review_count == 1

        refreshed_provider = await _get_provider(db_session, provider.id)
        assert refreshed_provider.average_rating == Decimal("5.00")
        assert refreshed_provider.review_count == 1

    @pytest.mark.anyio
    async def test_without_comment_succeeds(self, db_session) -> None:
        customer_user = await create_user(db_session, "701000003")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000004")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_review_service(db_session)

        review = await service.submit_review(
            customer_user.id,
            contact_view_id=contact_view.id,
            rating=3,
            comment=None,
        )
        await db_session.commit()

        assert review.comment is None
        assert review.rating == 3


class TestAnchorVerificationRejection:
    """AC2, Decision 5: rejection cases, each separately named."""

    @pytest.mark.anyio
    async def test_no_outcome_tag_at_all_is_rejected(self, db_session) -> None:
        customer_user = await create_user(db_session, "701000005")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000006")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_review_service(db_session)

        with pytest.raises(ReviewAnchorNotVerifiedError):
            await service.submit_review(
                customer_user.id,
                contact_view_id=contact_view.id,
                rating=4,
                comment=None,
            )

        assert await _count_reviews(db_session) == 0

    @pytest.mark.anyio
    async def test_hired_false_is_rejected(self, db_session) -> None:
        customer_user = await create_user(db_session, "701000007")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000008")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        outcome_tag_service = make_outcome_tag_service(db_session)
        await outcome_tag_service.submit_outcome_tag(
            customer_user.id, contact_view_id=contact_view.id, hired=False
        )
        await db_session.commit()
        service = make_review_service(db_session)

        with pytest.raises(ReviewAnchorNotVerifiedError):
            await service.submit_review(
                customer_user.id,
                contact_view_id=contact_view.id,
                rating=4,
                comment=None,
            )

        assert await _count_reviews(db_session) == 0

    @pytest.mark.anyio
    async def test_a_different_customers_contact_view_is_rejected_with_404(
        self, db_session
    ) -> None:
        owner_customer_user = await create_user(db_session, "701000009")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "701000010")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )
        other_customer_user = await create_user(db_session, "701000011")
        await create_customer_profile(db_session, other_customer_user)
        service = make_review_service(db_session)

        with pytest.raises(ContactViewNotFoundError):
            await service.submit_review(
                other_customer_user.id,
                contact_view_id=contact_view.id,
                rating=4,
                comment=None,
            )

        assert await _count_reviews(db_session) == 0

    @pytest.mark.anyio
    async def test_a_nonexistent_contact_view_id_is_rejected_with_404(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "701000012")
        await create_customer_profile(db_session, customer_user)
        service = make_review_service(db_session)

        with pytest.raises(ContactViewNotFoundError):
            await service.submit_review(
                customer_user.id,
                contact_view_id=uuid.uuid4(),
                rating=4,
                comment=None,
            )

        assert await _count_reviews(db_session) == 0


class TestUniquenessPerContactView:
    """AC1: one review per Contact View, enforced atomically."""

    @pytest.mark.anyio
    async def test_a_second_submission_is_rejected(self, db_session) -> None:
        customer_user = await create_user(db_session, "701000013")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000014")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )
        service = make_review_service(db_session)

        await service.submit_review(
            customer_user.id, contact_view_id=contact_view.id, rating=5, comment=None
        )
        await db_session.commit()

        with pytest.raises(ReviewAlreadyExistsError):
            await service.submit_review(
                customer_user.id,
                contact_view_id=contact_view.id,
                rating=2,
                comment="Changed my mind.",
            )

        # Exactly one row exists -- the second attempt never wrote a
        # second row, and never mutated the first.
        assert await _count_reviews(db_session) == 1
        result = await db_session.execute(
            select(Review).where(Review.contact_view_id == contact_view.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].rating == 5


class TestRatingDbCheckConstraint:
    """AC3: defense-in-depth -- the DB `CHECK` itself rejects an
    out-of-range value, bypassing the API/service layer entirely."""

    @pytest.mark.anyio
    async def test_an_out_of_range_rating_is_rejected_by_the_db_check(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "701000015")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000016")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider.id
        )

        with pytest.raises(IntegrityError):
            await db_session.execute(
                insert(Review).values(
                    contact_view_id=contact_view.id,
                    customer_id=customer_profile.id,
                    provider_id=provider.id,
                    rating=6,
                    comment=None,
                )
            )
            await db_session.flush()
        await db_session.rollback()

        assert await _count_reviews(db_session) == 0


class TestRecalculationCorrectness:
    """AC4/Decision 3: the running average/count is correct after each
    sequential review, and genuinely race-safe under real concurrency."""

    @pytest.mark.anyio
    async def test_sequential_reviews_produce_the_correct_running_average(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "701000017")
        provider = await create_provider(db_session, user=provider_owner)
        service = make_review_service(db_session)

        ratings = [5, 3, 4]
        for index, rating in enumerate(ratings):
            customer_user = await create_user(db_session, f"70100002{index}")
            await create_customer_profile(db_session, customer_user)
            contact_view = await create_hired_contact_view(
                db_session,
                customer_user_id=customer_user.id,
                provider_id=provider.id,
            )
            await service.submit_review(
                customer_user.id,
                contact_view_id=contact_view.id,
                rating=rating,
                comment=None,
            )
            await db_session.commit()

        summary = await _get_rating_summary(db_session, provider.id)
        assert summary is not None
        assert summary.average_rating == Decimal("4.00")
        assert summary.review_count == 3

        refreshed_provider = await _get_provider(db_session, provider.id)
        assert refreshed_provider.average_rating == Decimal("4.00")
        assert refreshed_provider.review_count == 3

    @pytest.mark.anyio
    async def test_two_concurrent_reviews_for_the_same_provider_both_count(
        self, db_engine: AsyncEngine, db_session
    ) -> None:
        """
        The genuine concurrency proof for Decision 3's lock: two
        independent `AsyncSession`/transactions submitting a review for
        the *same* provider at overlapping times must both land, and the
        final aggregate must reflect both ratings correctly -- never a
        lost update from one write silently overwriting the other's
        contribution. Mirrors REV-001's own
        `TestConcurrentSubmissionRace` shape, applied to a
        recompute-then-write critical section instead of a single atomic
        statement.
        """
        provider_owner = await create_user(db_session, "701000030")
        provider = await create_provider(db_session, user=provider_owner)

        customer_user_a = await create_user(db_session, "701000031")
        await create_customer_profile(db_session, customer_user_a)
        contact_view_a = await create_hired_contact_view(
            db_session, customer_user_id=customer_user_a.id, provider_id=provider.id
        )

        customer_user_b = await create_user(db_session, "701000032")
        await create_customer_profile(db_session, customer_user_b)
        contact_view_b = await create_hired_contact_view(
            db_session, customer_user_id=customer_user_b.id, provider_id=provider.id
        )

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt(customer_user_id, contact_view_id, rating) -> str:
            async with session_factory() as attempt_session:
                attempt_service = ReviewService(
                    review_repository=ReviewRepository(attempt_session),
                    provider_rating_summary_repository=(
                        ProviderRatingSummaryRepository(attempt_session)
                    ),
                    contact_view_repository=ContactViewRepository(attempt_session),
                    outcome_tag_repository=OutcomeTagRepository(attempt_session),
                    customer_profile_repository=CustomerProfileRepository(
                        attempt_session
                    ),
                    provider_service=make_provider_service(attempt_session),
                )
                await attempt_service.submit_review(
                    customer_user_id,
                    contact_view_id=contact_view_id,
                    rating=rating,
                    comment=None,
                )
                await attempt_session.commit()
                return "submitted"

        results = await asyncio.gather(
            _attempt(customer_user_a.id, contact_view_a.id, 5),
            _attempt(customer_user_b.id, contact_view_b.id, 3),
        )

        assert results == ["submitted", "submitted"]

        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(Review).where(Review.provider_id == provider.id)
            )
            rows = result.scalars().all()
            assert len(rows) == 2
            assert sorted(row.rating for row in rows) == [3, 5]

            summary_result = await verify_session.execute(
                select(ProviderRatingSummary).where(
                    ProviderRatingSummary.provider_id == provider.id
                )
            )
            summary = summary_result.scalar_one()
            assert summary.average_rating == Decimal("4.00")
            assert summary.review_count == 2

            provider_result = await verify_session.execute(
                select(Provider).where(Provider.id == provider.id)
            )
            refreshed_provider = provider_result.scalar_one()
            assert refreshed_provider.average_rating == Decimal("4.00")
            assert refreshed_provider.review_count == 2


class TestSameTransactionRollback:
    """AC4's "same transaction" claim: a failure after the `reviews`
    INSERT but before recalculation completes leaves *both* the
    `reviews` row and any partial `provider_rating_summaries`/
    `providers` write rolled back together -- no partial-write window."""

    @pytest.mark.anyio
    async def test_a_failure_during_recalculation_rolls_back_the_review_too(
        self, db_session, monkeypatch
    ) -> None:
        customer_user = await create_user(db_session, "701000040")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "701000041")
        provider = await create_provider(db_session, user=provider_owner)
        provider_id = provider.id
        contact_view = await create_hired_contact_view(
            db_session, customer_user_id=customer_user.id, provider_id=provider_id
        )
        service = make_review_service(db_session)

        async def _boom(*args, **kwargs):
            raise RuntimeError("simulated failure after the review insert")

        monkeypatch.setattr(
            service.provider_rating_summary_repository, "upsert", _boom
        )

        with pytest.raises(RuntimeError):
            await service.submit_review(
                customer_user.id,
                contact_view_id=contact_view.id,
                rating=4,
                comment=None,
            )
        await db_session.rollback()

        # `provider`/`contact_view` are expired by `rollback()` -- every
        # id used below was captured *before* the rollback so that
        # re-fetching doesn't itself trigger a synchronous attribute
        # refresh on an expired ORM object.
        assert await _count_reviews(db_session) == 0
        refreshed_provider = await _get_provider(db_session, provider_id)
        assert refreshed_provider.average_rating is None
        assert refreshed_provider.review_count == 0


class TestSelfDealingTransitivity:
    """
    AC5/Decision 4: because a self-dealing `ContactView` never exists
    (CON-001's guard raises before any row is written), a Review can
    never point back at its own author's Provider -- proven end to end,
    not by a redundant, dedicated self-dealing check inside
    `ReviewService` (the story's own explicit instruction against a
    "second explicit check").
    """

    @pytest.mark.anyio
    async def test_self_dealing_contact_view_never_exists_to_anchor_a_review(
        self, db_session
    ) -> None:
        # The same Account holds both a `customer_profiles` row and a
        # `providers` row -- the exact dual-role fixture CON-001's own
        # `TestSelfDealingRejection` uses.
        shared_user = await create_user(db_session, "701000050")
        await create_customer_profile(db_session, shared_user)
        provider = await create_provider(db_session, user=shared_user)
        contact_service = make_contact_service(db_session)

        with pytest.raises(SelfDealingContactError):
            await contact_service.create_contact_view(
                shared_user.id, provider_id=provider.id, search_request_id=None
            )

        # Reconfirms CON-001's guard is still in force -- the
        # load-bearing precondition for this test's second half.
        result = await db_session.execute(
            select(Provider).where(Provider.id == provider.id)
        )
        assert result.scalar_one() is not None
        contact_view_count = len(
            (await db_session.execute(select(ContactView))).scalars().all()
        )
        assert contact_view_count == 0

        # There is genuinely nothing to anchor a review against -- a
        # fabricated, never-created `contact_view_id` for this same
        # (customer, provider) pairing raises the ordinary "not found"
        # 404, not a self-dealing-specific error, because `ReviewService`
        # never sees a self-dealing case at all (Decision 4).
        review_service = make_review_service(db_session)
        with pytest.raises(ContactViewNotFoundError):
            await review_service.submit_review(
                shared_user.id,
                contact_view_id=uuid.uuid4(),
                rating=5,
                comment=None,
            )

        assert await _count_reviews(db_session) == 0


class TestCustomerProfileDefensiveCheck:
    @pytest.mark.anyio
    async def test_raises_if_the_caller_has_no_customer_profile(
        self, db_session
    ) -> None:
        customer_user_without_profile = await create_user(db_session, "701000060")
        owner_customer_user = await create_user(db_session, "701000061")
        await create_customer_profile(db_session, owner_customer_user)
        provider_owner = await create_user(db_session, "701000062")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await create_hired_contact_view(
            db_session,
            customer_user_id=owner_customer_user.id,
            provider_id=provider.id,
        )
        service = make_review_service(db_session)

        with pytest.raises(CustomerProfileNotFoundError):
            await service.submit_review(
                customer_user_without_profile.id,
                contact_view_id=contact_view.id,
                rating=5,
                comment=None,
            )

