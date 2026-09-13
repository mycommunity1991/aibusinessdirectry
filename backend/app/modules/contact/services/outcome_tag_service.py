"""
`OutcomeTagService` (REV-001) -- submits a `contact.outcome_tags` row
(AC1), the platform's only conversion signal ("did you hire them?").

Two mechanisms make this correct, mirroring `Plan_S09_REV-001.md`'s own
framing of them as this story's most safety-critical pieces:

1. **Ownership (AC2, Decision 2)**: only the Customer who owns the
   target `ContactView` may submit against it. Enforced via
   `ensure_owner_or_not_found`, the exact same helper (and non-
   revealing-404 posture) `ContactService.create_contact_view` already
   uses for `search_request_id` ownership -- collapsing "doesn't
   exist" and "exists but belongs to someone else" into one
   `ContactViewNotFoundError` (404), never a 403.
2. **Uniqueness (AC1/AC6, Decision 3)**: enforced by
   `OutcomeTagRepository.try_create`'s atomic `INSERT ... ON CONFLICT
   DO NOTHING ... RETURNING`, never a read-then-write check -- a
   genuine timing conflict raises `OutcomeTagAlreadyExistsError` (409).

An Outcome Tag is immutable/one-shot (Decision 4) -- this service
exposes only `submit_outcome_tag`, no update/resubmission path.
"""

import uuid

from app.core.authorization import ensure_owner_or_not_found
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
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)


class OutcomeTagService:
    """Orchestrates Outcome Tag submission, including AC2's ownership
    check and AC1/AC6's atomic uniqueness enforcement."""

    def __init__(
        self,
        outcome_tag_repository: OutcomeTagRepository,
        contact_view_repository: ContactViewRepository,
        customer_profile_repository: CustomerProfileRepository,
    ) -> None:
        self.outcome_tag_repository = outcome_tag_repository
        self.contact_view_repository = contact_view_repository
        self.customer_profile_repository = customer_profile_repository

    async def submit_outcome_tag(
        self,
        current_user_id: uuid.UUID,
        *,
        contact_view_id: uuid.UUID,
        hired: bool,
    ) -> OutcomeTag:
        """
        Submits a new Outcome Tag for `contact_view_id` (AC1).

        Order of operations:

        1. Resolve the caller's `customer_profiles` row --
           `CustomerProfileNotFoundError` if missing (defensive,
           mirrors `ContactService.create_contact_view`).
        2. Resolve the target `ContactView` via `ContactViewRepository.
           get_by_id`.
        3. `ensure_owner_or_not_found` (AC2, Decision 2) -- 404 if the
           Contact View doesn't exist or isn't owned by this customer.
        4. Atomically insert (Decision 3) -- 409 if a row already
           exists for this `contact_view_id`.
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

        outcome_tag = await self.outcome_tag_repository.try_create(
            {"contact_view_id": contact_view_id, "hired": hired}
        )
        if outcome_tag is None:
            raise OutcomeTagAlreadyExistsError()

        return outcome_tag
