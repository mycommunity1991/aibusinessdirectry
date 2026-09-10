"""
Manual-match-assignment-queue recording/listing/resolution (AI-002,
Decision 3, `Plan_S07_AI-002.md`, AC2).

Exposes four explicit methods (`create`, `list_pending`, `get_by_id`,
`resolve`), mirroring `ClaimReviewRequestService`'s "explicit methods,
not one generic CRUD surface" convention -- `search.SearchRequestService`
depends on this service class, never on
`ManualMatchAssignmentRepository` directly, per `02_ARCHITECTURE.md`'s
"modules communicate through services only" rule (the same `X ->
administration` edge shape `provider -> administration` already
established via `ClaimReviewRequestService`).

**Deliberately does not itself touch `search.search_requests`/
`provider_matches`** -- that is `SearchRequestService._finalize_matches`'s
job (Decision 4), called by the admin-facing route handler around this
service, exactly mirroring how `AdminClaimService` orchestrates
`ClaimReviewRequestService.resolve` and `ClaimService._finalize_claim`
as two separate calls around one admin action.
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    ManualMatchAssignmentAlreadyResolvedError,
    ManualMatchAssignmentNotFoundError,
)
from app.modules.administration.models import ManualMatchAssignment
from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)

_STATUS_PENDING = "pending"
_STATUS_COMPLETED = "completed"


class ManualMatchAssignmentService:
    """Creates, lists, and resolves `manual_match_assignments` rows."""

    def __init__(self, repository: ManualMatchAssignmentRepository) -> None:
        self.repository = repository

    async def create(
        self,
        *,
        conversation_session_id: uuid.UUID,
        search_request_id: uuid.UUID | None,
    ) -> ManualMatchAssignment:
        """
        Creates a new `status=pending`, `assigned_admin_id=NULL` row
        (AC2, Decision 2a) -- one row per low-confidence session routed
        to the admin queue.
        """
        return await self.repository.create(
            {
                "conversation_session_id": conversation_session_id,
                "search_request_id": search_request_id,
                "status": _STATUS_PENDING,
            }
        )

    async def list_pending(
        self, *, page: int, page_size: int
    ) -> tuple[list[ManualMatchAssignment], int]:
        """Lists one page of `status=pending` assignments, oldest first
        (the pull-based "notify an admin" mechanism, Decision 3)."""
        offset = (page - 1) * page_size
        return await self.repository.list_pending(offset=offset, limit=page_size)

    async def get_by_id(self, assignment_id: uuid.UUID) -> ManualMatchAssignment | None:
        """
        Single-assignment lookup -- used by `SearchRequestService.
        resolve_manual_match` to resolve an assignment's
        `search_request_id` before finalizing (Decision 4), and to 404
        on a nonexistent id before attempting `resolve`.
        """
        return await self.repository.get_by_id(assignment_id)

    async def resolve(
        self, assignment_id: uuid.UUID, *, admin_user_id: uuid.UUID
    ) -> ManualMatchAssignment:
        """
        Marks an assignment `status=completed` with the given
        `assigned_admin_id`/`completed_at=now()`. Raises
        `ManualMatchAssignmentNotFoundError` if the assignment doesn't
        exist, `ManualMatchAssignmentAlreadyResolvedError` (409) if it
        has already been resolved -- an already-resolved assignment is
        rejected rather than silently double-finalizing the underlying
        `search_requests`/`provider_matches` state (AC4/AC6's "identical
        shape, exactly once" guarantee).
        """
        assignment = await self.repository.get_by_id(assignment_id)
        if assignment is None:
            raise ManualMatchAssignmentNotFoundError()
        if assignment.status != _STATUS_PENDING:
            raise ManualMatchAssignmentAlreadyResolvedError()

        return await self.repository.update(
            assignment,
            {
                "status": _STATUS_COMPLETED,
                "assigned_admin_id": admin_user_id,
                "completed_at": datetime.now(UTC),
            },
        )
