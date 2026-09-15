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
`SearchService`/`ProviderService` (`search -> provider`, DIR-001;
AI-002's Decision 5 reused this unchanged, and MAT-001's Decision 1/3,
`Plan_S08_MAT-001.md`, extends it in place to be merit-ranked -- still
the same shared query, never a second, divergent one, AC2), `customer.
SavedAddressService`/`CustomerService` (`search -> customer`, Decision
2c), and `administration.ManualMatchAssignmentService`/`administration.
UnmatchedQueryReportService` (`search -> administration`, Decision 3/2
respectively -- the second is ADM-001's write-time-hook edge,
`Plan_S11_ADM-001.md`). ADM-002 (`Plan_S11_ADM-002.md`, Decision 7) adds
a fourth `search -> administration` edge, `administration.
FeatureFlagService` -- the same, already-established direction, gating
`handle_session_completed`'s automated-vs-manual dispatch on
`manual_matching_force_all` (AC4).

`search -> conversation` (ADM-001, Decision 4, `Plan_S11_ADM-001.md`):
the write/orchestration path (`handle_session_completed`,
`_handle_completed`, `_handle_routed_to_admin`, `_finalize_matches`,
`resolve_manual_match`) still has zero imports from `conversation` and
still receives only plain primitives (AI-002's original guarantee,
unchanged) -- `status` remains a plain string compared against this
module's own local constants, never `conversation.models.
ConversationStatus`. `search`'s *only* import from `conversation` is
`conversation.repositories.message_repository.MessageRepository`, a raw
Repository (not `ConversationService`, to avoid a genuine circular
import -- `conversation.dependencies` already imports `search.
dependencies.get_search_request_service`), used exclusively by the
read-only admin-transcript path (`list_pending_manual_matches`) --
never `conversation.services`/`conversation.dependencies`.
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
from app.modules.administration.services.feature_flag_service import FeatureFlagService
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.administration.services.unmatched_query_report_service import (
    UnmatchedQueryReportService,
)
from app.modules.conversation.models import Message
from app.modules.conversation.repositories.message_repository import MessageRepository
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

# ADM-002, Decision 1/7 (`Plan_S11_ADM-002.md`): the one code-defined
# key `FeatureFlagService.is_enabled` is called with here.
_FEATURE_FLAG_MANUAL_MATCHING_FORCE_ALL = "manual_matching_force_all"

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
        message_repository: MessageRepository,
        unmatched_query_report_service: UnmatchedQueryReportService,
        feature_flag_service: FeatureFlagService,
    ) -> None:
        self.search_request_repository = search_request_repository
        self.provider_match_repository = provider_match_repository
        self.search_event_log_repository = search_event_log_repository
        self.search_service = search_service
        self.provider_service = provider_service
        self.saved_address_service = saved_address_service
        self.manual_match_assignment_service = manual_match_assignment_service
        self.customer_service = customer_service
        # Decision 4 (`Plan_S11_ADM-001.md`): the *only* `search ->
        # conversation` edge, a raw Repository (never `ConversationService`)
        # to avoid a genuine circular import, scoped strictly to the
        # read-only admin-transcript path (`list_pending_manual_matches`).
        self.message_repository = message_repository
        # Decision 2 (`Plan_S11_ADM-001.md`): a second `search ->
        # administration` service edge, alongside the existing
        # `ManualMatchAssignmentService` one -- used only by
        # `_finalize_matches`'s write-time hook.
        self.unmatched_query_report_service = unmatched_query_report_service
        # ADM-002, Decision 7 (`Plan_S11_ADM-002.md`): a fourth `search ->
        # administration` service edge -- used only by
        # `handle_session_completed`'s automated-vs-manual dispatch gate.
        self.feature_flag_service = feature_flag_service

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

        ADM-002, Decision 7 (`Plan_S11_ADM-002.md`, AC4): when `status`
        is `completed`, first checks `FeatureFlagService.is_enabled(
        "manual_matching_force_all")` -- if `True`, dispatches to
        `_handle_routed_to_admin` (the existing manual-queue path)
        instead of `_handle_completed` (the existing automated path).
        An already-`routed_to_admin` session is unaffected either way
        (it was always going to the manual queue regardless of this
        flag). This is a marketplace matching-policy decision, a
        separate concern from `conversation`'s own completion-policy
        semantics -- `conversation_sessions.status` can genuinely,
        honestly still read `completed` (the AI really did resolve a
        category) while its `search_requests` row is manually resolved.
        """
        if status == _CONVERSATION_STATUS_COMPLETED:
            if await self.feature_flag_service.is_enabled(
                _FEATURE_FLAG_MANUAL_MATCHING_FORCE_ALL
            ):
                return await self._handle_routed_to_admin(
                    conversation_session_id=conversation_session_id,
                    customer_id=customer_id,
                    category_id=category_id,
                    structured_criteria=structured_criteria,
                )
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
    ) -> tuple[list[ManualMatchAssignment], dict[uuid.UUID, list[Message]], int]:
        """
        Fetches the pending-assignment page from `ManualMatchAssignment
        Service.list_pending` (Decision 3), then batch-fetches every
        assignment's own session transcript via `MessageRepository.
        list_for_sessions` in one query (Decision 3/4, `ADM-001`,
        `Plan_S11_ADM-001.md`) -- page size is capped, so this remains a
        single batched query, never N+1. Lets `search/admin_manual_
        match_api.py`'s admin route depend only on this module's own
        service.
        """
        assignments, total = await self.manual_match_assignment_service.list_pending(
            page=page, page_size=page_size
        )
        transcripts_by_session = await self.message_repository.list_for_sessions(
            [assignment.conversation_session_id for assignment in assignments]
        )
        return assignments, transcripts_by_session, total

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
            assignment_id, admin_user_id=admin_user_id, provider_ids=provider_ids
        )
        # Decision 3 (`Plan_S08_MAT-001.md`): the admin's own supplied
        # order *is* the rank -- never a formula-derived `match_score`,
        # so every row here carries `None`.
        ranked_matches: list[tuple[uuid.UUID, float | None]] = [
            (provider_id, None) for provider_id in provider_ids
        ]
        return await self._finalize_matches(search_request, ranked_matches)

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

        ranked_matches: list[tuple[uuid.UUID, float | None]] = []
        if default_address is not None:
            ranked_matches = await self._run_automated_match(
                default_address, category_name=category_name
            )

        initial_status = (
            SearchRequestStatus.MATCHED
            if ranked_matches
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
        return await self._finalize_matches(search_request, ranked_matches)

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
        self,
        search_request: SearchRequest,
        ranked_matches: list[tuple[uuid.UUID, float | None]],
    ) -> SearchRequest:
        """
        Decision 4's shared helper -- the **only** place `provider_
        matches` rows are written, `search_requests.status` is set to
        its final `matched`/`unmatched` value, and the corresponding
        `search_event_log` row is written. Called by both the automated
        path (immediately, in the same operation that creates the row)
        and the manual path (`resolve_manual_match`, at resolution time).

        `ranked_matches` is a list of `(provider_id, match_score)` pairs
        (MAT-001, Decision 3) -- a real score for the automated path, or
        `None` for every entry on the manual path.
        """
        if ranked_matches:
            await self.provider_match_repository.bulk_create(
                search_request.id, ranked_matches
            )

        final_status = (
            SearchRequestStatus.MATCHED
            if ranked_matches
            else SearchRequestStatus.UNMATCHED
        )
        updated = await self.search_request_repository.update_status(
            search_request, final_status
        )
        search_event_log = await self.search_event_log_repository.create(
            {
                "search_request_id": updated.id,
                "customer_id": updated.customer_id,
                "category_id": updated.category_id,
                "query_text": None,
                "result_count": len(ranked_matches),
                "was_matched": bool(ranked_matches),
            }
        )
        # Decision 2 (`ADM-001`, `Plan_S11_ADM-001.md`): a strict 1:1
        # `unmatched_query_reports` row for every unmatched
        # `search_event_log` row, guaranteed at this one shared write
        # site -- both the automated and manual paths funnel through
        # `_finalize_matches`, so a report can never be missed or
        # double-created.
        if not ranked_matches:
            await self.unmatched_query_report_service.create(
                search_event_log_id=search_event_log.id
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
    ) -> list[tuple[uuid.UUID, float | None]]:
        """
        MAT-001, Decision 1/3 (`Plan_S08_MAT-001.md`): reuses `Search
        Service.search_providers_ranked` -- the same shared, merit-ranked
        query DIR-001's own `GET /search/providers` uses (Decision 5's
        "no second, divergent ranking implementation" still holds, AC2)
        -- capped at `settings.AI_MATCH_MAX_RESULTS`. Calls
        `search_providers_ranked` directly (rather than
        `search_providers`, which discards `scores_by_id`) so the real
        `match_score` per provider is preserved for `provider_matches`
        (Decision 3). Returns an ordered list of `(provider_id,
        match_score)` pairs; `rank` is simply this order's 1-based
        position.
        """
        (
            providers,
            _distances_by_id,
            _total_items,
            scores_by_id,
        ) = await self.search_service.search_providers_ranked(
            category=category_name,
            latitude=address.latitude,
            longitude=address.longitude,
            radius_km=settings.SEARCH_DEFAULT_RADIUS_KM,
            page=1,
            page_size=settings.AI_MATCH_MAX_RESULTS,
        )
        return [(provider.id, scores_by_id.get(provider.id)) for provider in providers]

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
