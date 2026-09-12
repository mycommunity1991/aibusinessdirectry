"""
`ContactService` (CON-001) -- creates a `contact.contact_views` row the
instant a customer taps Contact on a matched provider (AC2), and is this
story's single most safety-critical mechanism: the self-dealing guard
(AC3/AC4, Decision 1, `Plan_S08_CON-001.md`).

Because one `identity.users` Account may hold both a `customer_profiles`
row and a `providers` row (`03_DOMAIN_MODEL.md`'s dual-role rule), a
Contact View must be rejected outright -- before any row is written --
if the requesting Customer's Account is the same Account that owns the
target Provider. Otherwise a provider could inflate their own lead/
contact/review numbers by contacting themselves. This can't be a
database `CHECK` constraint (it requires joining `customer_profiles` and
`providers` through `identity.users`), so it is enforced here, at the
point of write, exactly per AC3's literal wording.

Cross-module edges: `customer.CustomerProfileRepository`, `provider.
ProviderService`, `search.SearchRequestRepository`, `notification.
NotificationService` -- a lot of edges for one module, but each is
required (Decision 1's own "Alternatives considered and rejected"
section): `contact_views` is its own aggregate root, and the future
`outcome_tags`/`visit_verifications`/`reviews` domains all anchor to it.
The `provider` edge is `ProviderService`, never `ProviderRepository`
directly, per `02_ARCHITECTURE.md`'s "modules communicate through
services only" rule -- `get_for_public_profile` (added by this same
story for `GET /providers/{provider_id}`) is reused here rather than
duplicating its "missing or inactive -> 404" lookup inline.
"""

import uuid

from app.core.authorization import ensure_owner_or_not_found
from app.core.exceptions import (
    CustomerProfileNotFoundError,
    SearchRequestNotFoundError,
    SelfDealingContactError,
)
from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.models import Provider
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)


class ContactService:
    """Orchestrates Contact View creation, including the self-dealing guard."""

    def __init__(
        self,
        contact_view_repository: ContactViewRepository,
        customer_profile_repository: CustomerProfileRepository,
        provider_service: ProviderService,
        search_request_repository: SearchRequestRepository,
        notification_service: NotificationService,
    ) -> None:
        self.contact_view_repository = contact_view_repository
        self.customer_profile_repository = customer_profile_repository
        self.provider_service = provider_service
        self.search_request_repository = search_request_repository
        self.notification_service = notification_service

    async def create_contact_view(
        self,
        current_user_id: uuid.UUID,
        *,
        provider_id: uuid.UUID,
        search_request_id: uuid.UUID | None,
    ) -> tuple[ContactView, Provider]:
        """
        Creates a `contact_views` row (AC1/AC2), rejecting the write
        outright (before any row exists) if the caller's Account owns
        the target Provider (AC3/AC4).

        Order of operations (Decision 1):

        1. Resolve the caller's `customer_profiles` row -- expected to
           always succeed (every account gets one at registration,
           CUS-001), but checked defensively.
        2. Resolve the target Provider via `ProviderService.
           get_for_public_profile` -- 404 if missing or soft-deleted.
        3. **Self-dealing guard**: 403 if `provider.user_id ==
           current_user_id`. A still-unclaimed listing
           (`provider.user_id is None`) can never self-deal by
           construction, so the guard is skipped for it.
        4. If `search_request_id` is supplied, validate it belongs to
           this same customer (Decision 4) -- 404 if not, never
           silently dropped to `NULL`.
        5. Create the row (no dedup -- Decision 5).
        6. If the provider is claimed, emit a Notification (Decision 3)
           -- skipped for an unclaimed listing, since there is no
           account to notify.

        Returns the new `ContactView` plus the full `Provider` row, so
        the API layer can build the Contact Reveal response (AC2)
        without a second query.
        """
        customer_profile = await self.customer_profile_repository.get_by_user_id(
            current_user_id
        )
        if customer_profile is None:
            raise CustomerProfileNotFoundError()

        provider = await self.provider_service.get_for_public_profile(provider_id)

        if provider.user_id is not None and provider.user_id == current_user_id:
            raise SelfDealingContactError()

        resolved_search_request_id: uuid.UUID | None = None
        if search_request_id is not None:
            search_request = await self.search_request_repository.get_by_id(
                search_request_id
            )
            ensure_owner_or_not_found(
                search_request.customer_id if search_request is not None else None,
                customer_profile.id,
                not_found_exc=SearchRequestNotFoundError(),
            )
            resolved_search_request_id = search_request_id

        contact_view = await self.contact_view_repository.create(
            {
                "customer_id": customer_profile.id,
                "provider_id": provider.id,
                "search_request_id": resolved_search_request_id,
            }
        )

        if provider.user_id is not None:
            await self.notification_service.notify_new_contact_view(
                user_id=provider.user_id,
                contact_view_id=contact_view.id,
            )

        return contact_view, provider
