"""
`ReviewService` (REV-002) -- submits a `review.reviews` row (AC1) and
recalculates the target Provider's rating aggregate in the same
transaction (AC4).

Two mechanisms make this correct, mirroring `Plan_S09_REV-002.md`'s own
framing of them as this story's two safety-critical pieces:

1. **Anchor verification (AC2, Decision 5)**: a Review may only be
   submitted against a `ContactView` (a) owned by the calling customer
   (`ensure_owner_or_not_found`, the exact `ContactViewNotFoundError`
   404 shape `OutcomeTagService.submit_outcome_tag` already uses), and
   (b) carrying a `contact.outcome_tags` row with `hired=True`
   (`ReviewAnchorNotVerifiedError`, 409, covering both "no outcome tag"
   and "`hired=false`" -- AC2's own wording treats them identically).
   Because CON-001's self-dealing guard rejects a self-dealing
   `ContactView` *before any row is written*, no such Contact View ever
   exists to anchor a Review against -- this transitively blocks
   self-reviews too, without a second, redundant check here (Decision 4;
   the story's own explicit instruction).
2. **Race-safe recalculation (AC4, Decision 3)**: a full recompute
   (`ReviewRepository.compute_rating_aggregate`), guarded by a
   `SELECT ... FOR UPDATE` row lock on the target `providers` row
   (`ProviderService.lock_for_rating_recalculation`), acquired *before*
   the review is inserted and held through the recompute + upsert +
   apply -- never an incremental running-average update (rounding-drift
   rejected, see the Plan's own reasoning).
"""

import uuid
from decimal import Decimal

from app.core.authorization import ensure_owner_or_not_found
from app.core.exceptions import (
    ContactViewNotFoundError,
    CustomerProfileNotFoundError,
    ReviewAlreadyExistsError,
    ReviewAnchorNotVerifiedError,
)
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.provider.services.provider_service import ProviderService
from app.modules.review.models import Review
from app.modules.review.repositories.provider_rating_summary_repository import (
    ProviderRatingSummaryRepository,
)
from app.modules.review.repositories.review_repository import ReviewRepository


class ReviewService:
    """Orchestrates Review submission, including AC2's anchor-
    verification check and AC4's race-safe rating recalculation."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        provider_rating_summary_repository: ProviderRatingSummaryRepository,
        contact_view_repository: ContactViewRepository,
        outcome_tag_repository: OutcomeTagRepository,
        customer_profile_repository: CustomerProfileRepository,
        provider_service: ProviderService,
    ) -> None:
        self.review_repository = review_repository
        self.provider_rating_summary_repository = provider_rating_summary_repository
        self.contact_view_repository = contact_view_repository
        self.outcome_tag_repository = outcome_tag_repository
        self.customer_profile_repository = customer_profile_repository
        self.provider_service = provider_service

    async def submit_review(
        self,
        current_user_id: uuid.UUID,
        *,
        contact_view_id: uuid.UUID,
        rating: int,
        comment: str | None,
    ) -> Review:
        """
        Submits a new Review for `contact_view_id` (AC1), recalculating
        `provider_rating_summaries`/`providers.average_rating`/
        `review_count` in the same transaction (AC4).

        Order of operations (Plan_S09_REV-002.md, Backend Proposed
        Changes item 6):

        1. Resolve the caller's `customer_profiles` row --
           `CustomerProfileNotFoundError` if missing (defensive, mirrors
           `OutcomeTagService`/`ContactService`).
        2. Resolve the target `ContactView` via `ContactViewRepository.
           get_by_id`; `ensure_owner_or_not_found` (Decision 5) -- 404 if
           it doesn't exist or isn't owned by this customer.
        3. Resolve the `OutcomeTag` via `OutcomeTagRepository.
           get_by_contact_view_id`; `ReviewAnchorNotVerifiedError` if
           missing or `hired is not True` (AC2, Decision 5).
        4. Lock the target Provider row (Decision 3 step 1) -- acquired
           *before* the review insert, held through the entire
           recalculation below.
        5. Atomically insert the review (Decision 3 step 2) --
           `ReviewAlreadyExistsError` if a row already exists for this
           `contact_view_id`.
        6. Recompute the rating aggregate (Decision 3 step 3).
        7. Upsert `provider_rating_summaries` with the fresh values
           (Decision 3 step 4).
        8. Apply the same values onto the locked `providers` row
           (Decision 3 step 5).
        """
        customer_profile = await self.customer_profile_repository.get_by_user_id(
            current_user_id
        )
        if customer_profile is None:
            raise CustomerProfileNotFoundError()

        contact_view = await self.contact_view_repository.get_by_id(contact_view_id)
        ensure_owner_or_not_found(
            contact_view.customer_id if contact_view is not None else None,
            customer_profile.id,
            not_found_exc=ContactViewNotFoundError(),
        )
        # `ensure_owner_or_not_found` raises unless `contact_view` is
        # both present and owned -- so it is never `None` past this
        # point (mirrors `OutcomeTagService.submit_outcome_tag`'s
        # identical narrowing).
        assert contact_view is not None

        outcome_tag = await self.outcome_tag_repository.get_by_contact_view_id(
            contact_view_id
        )
        if outcome_tag is None or outcome_tag.hired is not True:
            raise ReviewAnchorNotVerifiedError()

        # Decision 3 step 1: acquired *before* the review insert, held
        # through the recompute + upsert + apply below -- this is what
        # makes concurrent reviews for the *same* provider race-safe.
        locked_provider = await self.provider_service.lock_for_rating_recalculation(
            contact_view.provider_id
        )

        review = await self.review_repository.try_create(
            {
                "contact_view_id": contact_view_id,
                "customer_id": customer_profile.id,
                "provider_id": contact_view.provider_id,
                "rating": rating,
                "comment": comment,
            }
        )
        if review is None:
            raise ReviewAlreadyExistsError()

        average_rating, review_count = (
            await self.review_repository.compute_rating_aggregate(
                contact_view.provider_id
            )
        )
        average_rating = Decimal(average_rating)

        await self.provider_rating_summary_repository.upsert(
            contact_view.provider_id,
            average_rating=average_rating,
            review_count=review_count,
        )
        await self.provider_service.apply_rating_recalculation(
            locked_provider,
            average_rating=average_rating,
            review_count=review_count,
        )

        return review
