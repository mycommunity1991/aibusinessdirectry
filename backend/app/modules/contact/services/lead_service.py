"""
`LeadService` (LEAD-001, Backend Proposed Changes item 6,
`Plan_S10_LEAD-001.md`) -- surfaces a provider's own `contact.
contact_views` as a paginated Leads list (AC1/AC2), each row enriched
with an honest category/request context (Decision 3) and a three-state
outcome status (Decision 5), and carrying **zero** customer-identifying
fields (Decision 4).

New cross-module edges for `contact`: `search.SearchRequestRepository`
(already an existing edge via `ContactService`), `category.
CategoryRepository` (new), `provider.ProviderService` (already an
existing edge via `ContactService`) -- mirrors Decision 1's own
reasoning for reusing `contact`'s already-established dependency
direction rather than inventing a new one.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.core.exceptions import ProviderNotFoundError
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.contact.models import ContactView, OutcomeTag
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.contact.schemas import LeadOutcomeStatus
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)


@dataclass(frozen=True)
class LeadItem:
    """
    One row of a provider's own Leads list -- the service layer's raw
    domain data; the API layer builds `LeadResponse` from this (mirrors
    `ProviderService.search_nearby`'s own "service returns raw domain
    data, API layer builds the response schema" convention). Carries
    zero customer-identifying fields (Decision 4) -- no `customer_id`,
    by construction.
    """

    id: uuid.UUID
    viewed_at: datetime
    category_name: str | None
    outcome_status: LeadOutcomeStatus


def _outcome_status_for(outcome_tag: OutcomeTag | None) -> LeadOutcomeStatus:
    """
    Decision 5's exact three-state mapping -- `hired = true` -> `HIRED`;
    `hired = false` -> `NOT_HIRED`; no row at all -> `NOT_YET_REPORTED`.
    Exhaustive by construction (the 1:1 unique constraint on
    `outcome_tags.contact_view_id` guarantees no fourth state is
    possible).
    """
    if outcome_tag is None:
        return LeadOutcomeStatus.NOT_YET_REPORTED
    if outcome_tag.hired:
        return LeadOutcomeStatus.HIRED
    return LeadOutcomeStatus.NOT_HIRED


class LeadService:
    """Orchestrates a provider's own Leads list (AC1/AC2/AC3/AC4)."""

    def __init__(
        self,
        contact_view_repository: ContactViewRepository,
        outcome_tag_repository: OutcomeTagRepository,
        search_request_repository: SearchRequestRepository,
        category_repository: CategoryRepository,
        provider_service: ProviderService,
    ) -> None:
        self.contact_view_repository = contact_view_repository
        self.outcome_tag_repository = outcome_tag_repository
        self.search_request_repository = search_request_repository
        self.category_repository = category_repository
        self.provider_service = provider_service

    async def list_my_leads(
        self, user_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[LeadItem], int]:
        """
        Returns one page of the caller's own leads, most-recent-first
        (AC2), plus the total row count for pagination.

        Raises `ProviderNotFoundError` if the caller has not yet created
        a Provider listing (AC4) -- mirrors `PortfolioService.
        list_my_portfolio`'s `_get_provider_or_404` pattern verbatim; a
        caller with no Provider listing has no leads to see, by
        construction.
        """
        provider = await self.provider_service.get_my_provider(user_id)
        if provider is None:
            raise ProviderNotFoundError()

        total_items = await self.contact_view_repository.count_for_provider(
            provider.id
        )
        contact_views = await self.contact_view_repository.list_for_provider(
            provider.id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        outcome_tags_by_contact_view_id = await self._resolve_outcome_tags(
            contact_views
        )
        category_names_by_search_request_id = await self._resolve_category_context(
            contact_views
        )

        items = [
            LeadItem(
                id=contact_view.id,
                viewed_at=contact_view.viewed_at,
                category_name=(
                    category_names_by_search_request_id.get(
                        contact_view.search_request_id
                    )
                    if contact_view.search_request_id is not None
                    else None
                ),
                outcome_status=_outcome_status_for(
                    outcome_tags_by_contact_view_id.get(contact_view.id)
                ),
            )
            for contact_view in contact_views
        ]
        # `list_for_provider`'s own `viewed_at DESC, id ASC` row order is
        # already final -- no cross-table re-ranking is needed here, so
        # it is preserved verbatim (no re-sort at this layer).
        return items, total_items

    async def _resolve_outcome_tags(
        self, contact_views: list[ContactView]
    ) -> dict[uuid.UUID, OutcomeTag]:
        outcome_tags = await self.outcome_tag_repository.list_by_contact_view_ids(
            [contact_view.id for contact_view in contact_views]
        )
        return {tag.contact_view_id: tag for tag in outcome_tags}

    async def _resolve_category_context(
        self, contact_views: list[ContactView]
    ) -> dict[uuid.UUID, str]:
        """
        Decision 3's two-hop lookup: `contact_views.search_request_id`
        -> `search_requests.category_id` -> `categories.name`, with two
        independent, honest dead-ends (no `search_request_id` at all; or
        a `search_request_id` whose `category_id` is itself `NULL`) --
        both simply produce no entry in the returned map, never a
        fabricated placeholder. Returns a `search_request_id ->
        category_name` map (not keyed by `contact_view_id`) since a
        `search_request_id` is the actual join key to a category name.
        """
        distinct_search_request_ids = list(
            {
                contact_view.search_request_id
                for contact_view in contact_views
                if contact_view.search_request_id is not None
            }
        )
        search_requests = await self.search_request_repository.list_by_ids(
            distinct_search_request_ids
        )

        distinct_category_ids = list(
            {
                search_request.category_id
                for search_request in search_requests
                if search_request.category_id is not None
            }
        )
        categories = await self.category_repository.list_by_ids(
            distinct_category_ids
        )
        category_names_by_id = {category.id: category.name for category in categories}

        category_names_by_search_request_id: dict[uuid.UUID, str] = {}
        for search_request in search_requests:
            if search_request.category_id is None:
                continue
            category_name = category_names_by_id.get(search_request.category_id)
            if category_name is not None:
                category_names_by_search_request_id[search_request.id] = category_name
        return category_names_by_search_request_id
