"""
`SearchRequestService` (AI-002) -- the confirmed owner of
`search.search_requests` creation, real matching, and
`administration.manual_match_assignments` (`ADR-032`'s own recorded
`AI-001`/`AI-002` scope split). Orchestrates both the automated-match
path (a `completed` conversation session) and the manual-resolution path
(an admin resolving a `routed_to_admin` session's queue entry) around one
shared, private `_finalize_matches` helper (Decision 4) -- the **only**
place in this codebase that ever writes `provider_matches` rows, sets
`search_requests.status` to its final value, or writes a
`search_event_log` row. This is what makes AC4 ("the same ranked-results
screen") and AC6 ("regardless of... automated or manual") true by
construction, not by convention.

Cross-module edges (Decision 1): depends on the already-shipped
`SearchService`/`ProviderService` (`search -> provider`, DIR-001, reused
unchanged -- Decision 5, no new ranking algorithm), `customer.
SavedAddressService`/`CustomerService` (`search -> customer`, Decision
2c), and `administration.ManualMatchAssignmentService` (`search ->
administration`, Decision 3). `search` has zero imports from
`conversation` -- `handle_session_completed` receives plain primitives
only (never a `ConversationSession` ORM object), and `status` is a plain
string compared against this module's own local constants, not
`conversation.models.ConversationStatus`.
"""

import math
import uuid
from typing import Any

from app.core.authorization import ensure_owner_or_not_found
from app.core.config import settings
from app.core.exceptions import (
    InvalidManualMatchProviderIdsError,
    ManualMatchAssignmentNotFoundError,
    SearchRequestNotFoundError,
)
from app.modules.administration.models import ManualMatchAssignment
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.customer.models import SavedAddress
from app.modules.customer.services.customer_service import CustomerService
from app.modules.customer.services.saved_address_service import SavedAddressService
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.models import SearchRequest, SearchRequestStatus
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)
from app.modules.search.schemas import MatchedProviderResponse
from app.modules.search.services.search_service import SearchService

# Plain string constants, deliberately not an import of
# `conversation.models.ConversationStatus` -- `search` has zero imports
# from `conversation` (Decision 1). `ConversationStatus` is a `StrEnum`,
# so the caller's `session.status.value` (or the enum member itself)
# compares equal to these regardless.
_CONVERSATION_STATUS_COMPLETED = "completed"
_CONVERSATION_STATUS_ROUTED_TO_ADMIN = "routed_to_admin"

_EARTH_RADIUS_METERS = 6_371_000.0


def _haversine_distance_meters(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """
    Great-circle distance between two points, in meters -- used only to
    *display* an honest `distance_meters` for an already-fixed matched-
    provider list (Decision 6), never to filter/rank (that remains
    `SearchService`/`ProviderService.search_nearby`'s job, Decision 5).
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


class SearchRequestService:
    """Orchestrates `search_requests` creation and resolution for both
    the automated and manual-match paths (AI-002)."""

    def __init__(
        self,
        search_request_repository: SearchRequestRepository,
        provider_match_repository: ProviderMatchRepository,
        search_event_log_repository: SearchEventLogRepository,
        search_service: SearchService,
        provider_service: ProviderService,
        saved_address_service: SavedAddressService,
        manual_match_assignment_service: ManualMatchAssignmentService,
        customer_service: CustomerService,
    ) -> None:
        self.search_request_repository = search_request_repository
        self.provider_match_repository = provider_match_repository
        self.search_event_log_repository = search_event_log_repository
        self.search_service = search_service
        self.provider_service = provider_service
        self.saved_address_service = saved_address_service
        self.manual_match_assignment_service = manual_match_assignment_service
        self.customer_service = customer_service

    async def handle_session_completed(
        self,
        *,
        conversation_session_id: uuid.UUID,
        customer_id: uuid.UUID,
        status: str,
        category_id: uuid.UUID | None,
        category_name: str | None,
        structured_criteria: dict[str, Any] | None,
    ) -> SearchRequest:
        """
        The single call site `ConversationService._apply_completion_
        policy` invokes on both the `completed` and `routed_to_admin`
        transitions (Decision 1) -- branches on `status` to run the
        automated-match path or create a manual-match assignment. Either
        way, a `search_requests` row always exists afterward (AC2's
        "never left in limbo with no next step").
        """
        if status == _CONVERSATION_STATUS_COMPLETED:
            return await self._handle_completed(
                conversation_session_id=conversation_session_id,
                customer_id=customer_id,
                category_id=category_id,
                category_name=category_name,
                structured_criteria=structured_criteria,
            )
        if status == _CONVERSATION_STATUS_ROUTED_TO_ADMIN:
            return await self._handle_routed_to_admin(
                conversation_session_id=conversation_session_id,
                customer_id=customer_id,
                category_id=category_id,
                structured_criteria=structured_criteria,
            )
        raise ValueError(
            f"handle_session_completed called with an unexpected status: {status!r}"
        )

    async def get_search_request_id_for_session(
        self, conversation_session_id: uuid.UUID
    ) -> uuid.UUID | None:
        """
        The `search_requests.id` created for a given conversation session,
        if any yet (Decision 6) -- backs `ConversationSessionResponse.
        search_request_id`. `None` for a still-`active` session (no
        `search_requests` row exists yet).
        """
        search_request = (
            await self.search_request_repository.get_latest_by_conversation_session_id(
                conversation_session_id
            )
        )
        return search_request.id if search_request is not None else None

    async def get_result_for_customer(
        self, user_id: uuid.UUID, search_request_id: uuid.UUID
    ) -> SearchRequest:
        """
        Resolves a `search_requests` row for `GET /search-requests/{id}`
        (Decision 6, ADR-015) -- `ensure_owner_or_not_found` against the
        caller's own `customer_profiles.id`, never a 403.
        """
        profile, _preferences = await self.customer_service.get_my_profile(user_id)
        search_request = await self.search_request_repository.get_by_id(
            search_request_id
        )
        ensure_owner_or_not_found(
            search_request.customer_id if search_request is not None else None,
            profile.id,
            not_found_exc=SearchRequestNotFoundError(),
        )
        assert search_request is not None  # narrows for type-checkers; guaranteed above
        return search_request

    async def get_matched_providers(
        self, search_request: SearchRequest
    ) -> list[MatchedProviderResponse]:
        """
        Builds the ranked `MatchedProviderResponse` list for a
        `search_requests` row -- identical shape/mechanism regardless of
        whether it was resolved automatically or manually (AC4), since
        both paths write `provider_matches` through the same
        `_finalize_matches` helper.
        """
        matches = await self.provider_match_repository.list_for_search_request(
            search_request.id
        )
        if not matches:
            return []

        provider_ids = [match.provider_id for match in matches]
        providers_by_id = {
            provider.id: provider
            for provider in await self.provider_service.list_by_ids(provider_ids)
        }
        photo_urls_by_id = await self.provider_service.get_primary_photo_urls(
            provider_ids
        )
        category_labels_by_id = (
            await self.provider_service.get_category_labels_by_provider_id(provider_ids)
        )
        locations_by_id = await self.provider_service.get_locations_by_provider_id(
            provider_ids
        )

        results: list[MatchedProviderResponse] = []
        for match in matches:
            provider = providers_by_id.get(match.provider_id)
            if provider is None:
                # Defensive: a provider referenced by a `provider_matches`
                # row should always still resolve; skip rather than fail
                # the whole response if it somehow doesn't.
                continue
            results.append(
                MatchedProviderResponse(
                    id=provider.id,
                    display_name=provider.display_name,
                    slug=provider.slug,
                    provider_type=provider.provider_type,
                    category_labels=category_labels_by_id.get(provider.id, []),
                    primary_photo_url=photo_urls_by_id.get(provider.id),
                    average_rating=provider.average_rating,
                    review_count=provider.review_count,
                    distance_meters=self._distance_for(
                        search_request, locations_by_id.get(provider.id)
                    ),
                    is_claimed=provider.is_claimed,
                )
            )
        return results

    async def list_pending_manual_matches(
        self, *, page: int, page_size: int
    ) -> tuple[list[ManualMatchAssignment], int]:
        """Thin pass-through to `ManualMatchAssignmentService.
        list_pending` (Decision 3) -- lets `search/api.py`'s admin route
        depend only on this module's own service."""
        return await self.manual_match_assignment_service.list_pending(
            page=page, page_size=page_size
        )

    async def resolve_manual_match(
        self,
        assignment_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
        provider_ids: list[uuid.UUID],
    ) -> SearchRequest:
        """
        The manual-resolution path (Decision 4): fetches the assignment,
        closes it out via `ManualMatchAssignmentService.resolve` **first**
        -- so its already-resolved guard (`ManualMatchAssignmentAlready
        ResolvedError`, 409) is the first thing that can fail, before any
        `search_requests`/`provider_matches`/`search_event_log` mutation
        happens -- then finalizes the `search_requests` row via the
        **same** `_finalize_matches` helper the automated path uses (an
        empty `provider_ids` list is valid -- "no viable match found",
        resolves to `unmatched`, not an error). `rank` is simply the
        admin's own supplied order -- never re-derived.

        Raises `ManualMatchAssignmentNotFoundError` (404) for an unknown
        id, or `ManualMatchAssignmentAlreadyResolvedError` (409, raised
        by `ManualMatchAssignmentService.resolve` itself) if the
        assignment was already resolved -- never silently
        double-finalizing: a rejected (409) second attempt must not
        write a second `search_event_log` row or append a second set of
        `provider_matches` rows.

        Validates every id in `provider_ids` against a real `providers`
        row **before** any of the above mutations happen (`08_CODING_
        STANDARDS.md`'s "validate every endpoint's input" rule) --
        raises `InvalidManualMatchProviderIdsError` (422) for a bogus id
        rather than letting `ProviderMatchRepository.bulk_create`'s FK
        constraint surface it as an opaque 500. Reuses `ProviderService.
        list_by_ids` (the same batch-existence lookup `get_matched_
        providers` and VER-002 already use) rather than a new query.
        """
        if provider_ids:
            existing_providers = await self.provider_service.list_by_ids(provider_ids)
            existing_ids = {provider.id for provider in existing_providers}
            if any(provider_id not in existing_ids for provider_id in provider_ids):
                raise InvalidManualMatchProviderIdsError()

        assignment = await self.manual_match_assignment_service.get_by_id(assignment_id)
        if assignment is None:
            raise ManualMatchAssignmentNotFoundError()

        search_request = await self.search_request_repository.get_by_id(
            assignment.search_request_id
        )
        if search_request is None:
            raise SearchRequestNotFoundError()

        await self.manual_match_assignment_service.resolve(
            assignment_id, admin_user_id=admin_user_id
        )
        return await self._finalize_matches(search_request, provider_ids)

    # -- internal helpers -----------------------------------------------

    async def _handle_completed(
        self,
        *,
        conversation_session_id: uuid.UUID,
        customer_id: uuid.UUID,
        category_id: uuid.UUID | None,
        category_name: str | None,
        structured_criteria: dict[str, Any] | None,
    ) -> SearchRequest:
        """
        Automated path (Decision 4): resolves the customer's default
        address (Decision 2c), runs the existing `SearchService` query
        (Decision 5) if one exists, then creates the `search_requests`
        row with its final status already known before calling
        `_finalize_matches` -- never a `pending` placeholder (mirrors
        ADR-029).
        """
        default_address = await self._get_default_address(customer_id)

        provider_ids: list[uuid.UUID] = []
        if default_address is not None:
            provider_ids = await self._run_automated_match(
                default_address, category_name=category_name
            )

        initial_status = (
            SearchRequestStatus.MATCHED
            if provider_ids
            else SearchRequestStatus.UNMATCHED
        )
        search_request = await self.search_request_repository.create(
            {
                "customer_id": customer_id,
                "conversation_session_id": conversation_session_id,
                "category_id": category_id,
                "structured_criteria": structured_criteria,
                "customer_latitude": (
                    default_address.latitude if default_address is not None else None
                ),
                "customer_longitude": (
                    default_address.longitude if default_address is not None else None
                ),
                "status": initial_status,
            }
        )
        return await self._finalize_matches(search_request, provider_ids)

    async def _handle_routed_to_admin(
        self,
        *,
        conversation_session_id: uuid.UUID,
        customer_id: uuid.UUID,
        category_id: uuid.UUID | None,
        structured_criteria: dict[str, Any] | None,
    ) -> SearchRequest:
        """
        Manual path (AC2): creates a `search_requests` row with its
        final-for-now `pending_manual_match` status (the enum's own
        "awaiting a human" state, not an interim placeholder -- see
        `Plan_S07_AI-002.md`'s Verified Current State), plus exactly one
        `manual_match_assignments` row (`assigned_admin_id=NULL`,
        Decision 2a) -- the session is never left with no next step.
        """
        default_address = await self._get_default_address(customer_id)

        search_request = await self.search_request_repository.create(
            {
                "customer_id": customer_id,
                "conversation_session_id": conversation_session_id,
                "category_id": category_id,
                "structured_criteria": structured_criteria,
                "customer_latitude": (
                    default_address.latitude if default_address is not None else None
                ),
                "customer_longitude": (
                    default_address.longitude if default_address is not None else None
                ),
                "status": SearchRequestStatus.PENDING_MANUAL_MATCH,
            }
        )
        await self.manual_match_assignment_service.create(
            conversation_session_id=conversation_session_id,
            search_request_id=search_request.id,
        )
        return search_request

    async def _finalize_matches(
        self, search_request: SearchRequest, provider_ids: list[uuid.UUID]
    ) -> SearchRequest:
        """
        Decision 4's shared helper -- the **only** place `provider_
        matches` rows are written, `search_requests.status` is set to
        its final `matched`/`unmatched` value, and the corresponding
        `search_event_log` row is written. Called by both the automated
        path (immediately, in the same operation that creates the row)
        and the manual path (`resolve_manual_match`, at resolution time).
        """
        if provider_ids:
            await self.provider_match_repository.bulk_create(
                search_request.id, provider_ids
            )

        final_status = (
            SearchRequestStatus.MATCHED
            if provider_ids
            else SearchRequestStatus.UNMATCHED
        )
        updated = await self.search_request_repository.update_status(
            search_request, final_status
        )
        await self.search_event_log_repository.create(
            {
                "search_request_id": updated.id,
                "customer_id": updated.customer_id,
                "category_id": updated.category_id,
                "query_text": None,
                "result_count": len(provider_ids),
                "was_matched": bool(provider_ids),
            }
        )
        return updated

    async def _get_default_address(self, customer_id: uuid.UUID) -> SavedAddress | None:
        """
        Resolves the customer's `is_default=true` saved address, if any
        (Decision 2c) -- `SearchRequestService` does the filtering
        itself; `SavedAddressService.list_for_customer` returns every
        active address unfiltered.
        """
        addresses = await self.saved_address_service.list_for_customer(customer_id)
        return next((address for address in addresses if address.is_default), None)

    async def _run_automated_match(
        self, address: SavedAddress, *, category_name: str | None
    ) -> list[uuid.UUID]:
        """
        Decision 5: reuses `SearchService`'s existing nearest-first
        query unchanged, capped at `settings.AI_MATCH_MAX_RESULTS` --
        no new ranking algorithm. Returns an ordered list of provider
        ids; `rank` is simply this order's 1-based position.
        """
        results, _total_items = await self.search_service.search_providers(
            category=category_name,
            latitude=address.latitude,
            longitude=address.longitude,
            radius_km=settings.SEARCH_DEFAULT_RADIUS_KM,
            page=1,
            page_size=settings.AI_MATCH_MAX_RESULTS,
        )
        return [result.id for result in results]

    @staticmethod
    def _distance_for(
        search_request: SearchRequest, location: tuple[float, float] | None
    ) -> float | None:
        """
        Decision 6: `distance_meters` is nullable, computed honestly
        whenever both the request's origin and the provider's location
        are known -- `None` otherwise, never estimated.
        """
        if (
            location is None
            or search_request.customer_latitude is None
            or search_request.customer_longitude is None
        ):
            return None
        return _haversine_distance_meters(
            search_request.customer_latitude,
            search_request.customer_longitude,
            location[0],
            location[1],
        )
