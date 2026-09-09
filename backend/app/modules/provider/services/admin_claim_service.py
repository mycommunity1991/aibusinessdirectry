"""
Admin-facing claim-review-queue orchestration (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`, AC6).

A deliberately **separate** class from the customer-facing `ClaimService`
-- mirrors `verification`'s existing `VerificationService`/
`AdminVerificationService` split exactly (a customer-facing service and
a sibling admin-facing service in the same module, not one service
handling both). `require_role(ROLE_ADMIN)` at the API layer is this
surface's entire authorization boundary, ownerless (ADR-023) -- no
"own" review request exists for an Admin, since every request belongs
to some *other* user's claim attempt.

`approve_review_request` calls `ClaimService._finalize_claim` --
the **identical** logic the OTP-success path runs (Decision 6) -- so the
two success paths can never silently drift apart into two different
definitions of "claimed."
"""

import uuid

from app.core.exceptions import ClaimReviewRequestNotFoundError, ProviderNotFoundError
from app.modules.administration.models import ClaimReviewRequest
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewRequestService,
)
from app.modules.provider.models import Provider
from app.modules.provider.services.claim_service import ClaimService
from app.modules.provider.services.provider_service import ProviderService


class AdminClaimService:
    """Orchestrates an Admin's claim-review queue and approve/reject actions."""

    def __init__(
        self,
        claim_review_request_service: ClaimReviewRequestService,
        claim_service: ClaimService,
        provider_service: ProviderService,
    ) -> None:
        self.claim_review_request_service = claim_review_request_service
        self.claim_service = claim_service
        self.provider_service = provider_service

    async def list_open_review_requests(
        self, *, page: int, page_size: int
    ) -> tuple[list[ClaimReviewRequest], dict[uuid.UUID, Provider], int]:
        """
        Returns one page of `status=open` requests (oldest first), plus
        batch-fetched Provider context (mirrors `AdminVerificationService.
        list_pending_for_review`'s identical one-query batching pattern,
        Decision 9 of `Plan_S05_VER-002.md`) and a total count.
        """
        requests, total = await self.claim_review_request_service.list_open(
            page=page, page_size=page_size
        )

        provider_ids = list({request.provider_id for request in requests})
        providers = await self.provider_service.list_by_ids(provider_ids)
        providers_by_id = {provider.id: provider for provider in providers}

        return requests, providers_by_id, total

    async def get_provider(self, provider_id: uuid.UUID) -> Provider:
        """Single-Provider lookup, reused from the batch path above --
        used by the API layer to build the response after approve/reject."""
        providers = await self.provider_service.list_by_ids([provider_id])
        if not providers:
            raise ProviderNotFoundError()
        return providers[0]

    async def approve_review_request(
        self, admin_user_id: uuid.UUID, request_id: uuid.UUID
    ) -> tuple[ClaimReviewRequest, Provider]:
        """
        Approves an open review request: finalizes the claim via the
        **exact same** `ClaimService._finalize_claim` sequence the
        OTP-success path uses (Decision 6/9), then marks the request
        `status=resolved`/`resolution=approved`.

        `_finalize_claim` itself re-checks `is_claimed=False` and the
        one-Provider-per-Account rule -- so an already-claimed listing
        (e.g. claimed via the OTP path in the meantime) or a claimant
        who has since acquired a different Provider correctly raises a
        conflict here too, exactly as it would on the OTP path.
        """
        request = await self._get_open_request_or_404(request_id)

        claimed_provider = await self.claim_service._finalize_claim(  # noqa: SLF001
            request.provider_id, request.claimant_user_id
        )

        resolved_request = await self.claim_review_request_service.resolve(
            request_id,
            admin_user_id=admin_user_id,
            resolution="approved",
            resolution_notes=None,
        )
        return resolved_request, claimed_provider

    async def reject_review_request(
        self,
        admin_user_id: uuid.UUID,
        request_id: uuid.UUID,
        *,
        notes: str | None,
    ) -> ClaimReviewRequest:
        """
        Rejects an open review request: marks it `status=resolved`/
        `resolution=rejected`, leaving the target provider unclaimed --
        no `providers`/`verification_records` write of any kind happens
        here.
        """
        await self._get_open_request_or_404(request_id)
        return await self.claim_review_request_service.resolve(
            request_id,
            admin_user_id=admin_user_id,
            resolution="rejected",
            resolution_notes=notes,
        )

    async def _get_open_request_or_404(
        self, request_id: uuid.UUID
    ) -> ClaimReviewRequest:
        request = await self.claim_review_request_service.get_by_id(request_id)
        if request is None:
            raise ClaimReviewRequestNotFoundError()
        return request
