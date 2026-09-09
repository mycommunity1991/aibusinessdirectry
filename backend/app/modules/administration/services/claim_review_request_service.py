"""
Claim-review-queue recording/listing/resolution (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`, AC6).

Exposes three explicit methods (`create`, `list_open`, `resolve`),
mirroring `AdminActionLogService`'s "explicit methods, not one generic
CRUD surface" convention -- `provider`'s new `ClaimService`/
`AdminClaimService` depend on this service class, never on
`ClaimReviewRequestRepository` directly, per `02_ARCHITECTURE.md`'s
"modules communicate through services only" rule (the same `provider ->
administration` edge shape `verification -> administration` already
established via `AdminActionLogService`).
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from app.core.exceptions import ClaimReviewRequestNotFoundError
from app.modules.administration.models import ClaimReviewRequest
from app.modules.administration.repositories.claim_review_request_repository import (
    ClaimReviewRequestRepository,
)

ClaimReviewReason = Literal["otp_failed", "no_public_number"]
ClaimReviewResolution = Literal["approved", "rejected"]

_STATUS_OPEN = "open"
_STATUS_RESOLVED = "resolved"


class ClaimReviewRequestService:
    """Creates, lists, and resolves `claim_review_requests` rows."""

    def __init__(self, repository: ClaimReviewRequestRepository) -> None:
        self.repository = repository

    async def create(
        self,
        *,
        provider_id: uuid.UUID,
        claimant_user_id: uuid.UUID,
        reason: ClaimReviewReason,
    ) -> ClaimReviewRequest:
        """
        Creates a new `status=open` review request (AC6) -- one row per
        fallback attempt; a claimant may create more than one over time
        (e.g. retries), each tracked independently.
        """
        return await self.repository.create(
            {
                "provider_id": provider_id,
                "claimant_user_id": claimant_user_id,
                "reason": reason,
                "status": _STATUS_OPEN,
            }
        )

    async def list_open(
        self, *, page: int, page_size: int
    ) -> tuple[list[ClaimReviewRequest], int]:
        """Lists one page of `status=open` requests, oldest first."""
        offset = (page - 1) * page_size
        return await self.repository.list_open(offset=offset, limit=page_size)

    async def get_by_id(self, request_id: uuid.UUID) -> ClaimReviewRequest | None:
        """
        Single-request lookup -- used by `AdminClaimService` (`provider`
        module) to resolve a request's `provider_id`/`claimant_user_id`
        before finalizing a claim (Decision 9), and to 404 on a
        nonexistent id before attempting `resolve`.
        """
        return await self.repository.get_by_id(request_id)

    async def resolve(
        self,
        request_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
        resolution: ClaimReviewResolution,
        resolution_notes: str | None,
    ) -> ClaimReviewRequest:
        """
        Marks a review request `status=resolved` with the given
        `resolution` (`approved`/`rejected`), `reviewed_by`, and
        `reviewed_at=now()`. Raises `ClaimReviewRequestNotFoundError` if
        the request doesn't exist.

        Deliberately does not itself finalize the underlying claim --
        `AdminClaimService` (Decision 9, `provider` module) orchestrates
        calling `ClaimService._finalize_claim` (on `approved`) or
        leaving the provider unclaimed (on `rejected`) around this call,
        on the same request-scoped session/transaction.
        """
        request = await self.repository.get_by_id(request_id)
        if request is None:
            raise ClaimReviewRequestNotFoundError()

        return await self.repository.update(
            request,
            {
                "status": _STATUS_RESOLVED,
                "resolution": resolution,
                "resolution_notes": resolution_notes,
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.now(UTC),
            },
        )
