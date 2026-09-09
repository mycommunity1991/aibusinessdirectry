"""
Customer-facing claim flow for a Google-seeded-unclaimed listing
(CLM-001, Decision 6/7, `Plan_S06_CLM-001.md`).

Lives inside the `provider` module per `02_ARCHITECTURE.md`'s explicit
"Claim flow for Google-seeded unclaimed listings" assignment (Decision
7). Depends on `OtpService`/`RoleAssignmentService` (from `identity`,
the same cross-module shape ADR-016 already established for `provider ->
identity`) and `ClaimReviewRequestService` (from `administration`, the
same `X -> administration` shape VER-002's `AdminVerificationService`
already established for `verification -> administration`).

`_finalize_claim` (Decision 6/9) is the one, shared success path both
this class's own `verify_otp` and `AdminClaimService.approve_review_
request` call -- extracted here specifically so the two success paths
(OTP verification, admin-approved fallback) can never silently drift
apart into two different definitions of "claimed."
"""

import uuid
from datetime import UTC, datetime

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import (
    ClaimAlreadyClaimedError,
    ClaimPublicNumberUnavailableError,
    ClaimTargetNotFoundError,
)
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewReason,
    ClaimReviewRequestService,
)
from app.modules.identity.models import OtpPurpose
from app.modules.identity.services.otp_service import OtpService
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    BusinessProfile,
    ListingSource,
    Provider,
    VerificationStatus,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.services.provider_service import ProviderService


class ClaimService:
    """Orchestrates a customer's search, OTP request/verify, and
    admin-review fallback for claiming a Google-seeded listing."""

    def __init__(
        self,
        provider_repository: ProviderRepository,
        provider_service: ProviderService,
        otp_service: OtpService,
        role_assignment_service: RoleAssignmentService,
        claim_review_request_service: ClaimReviewRequestService,
    ) -> None:
        self.provider_repository = provider_repository
        self.provider_service = provider_service
        self.otp_service = otp_service
        self.role_assignment_service = role_assignment_service
        self.claim_review_request_service = claim_review_request_service

    async def search_unclaimed(
        self, *, query: str, limit: int, offset: int
    ) -> tuple[list[Provider], int]:
        """AC3 -- thin pass-through to `ProviderService.
        search_unclaimed_listings` (Decision 5)."""
        return await self.provider_service.search_unclaimed_listings(
            query=query, limit=limit, offset=offset
        )

    async def get_business_profiles_by_provider_id(
        self, provider_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, BusinessProfile]:
        """
        Thin pass-through to `ProviderService.
        get_business_profiles_by_provider_id` -- used by the API layer
        to build `ClaimSearchResultResponse.address_line`/`city`.
        """
        return await self.provider_service.get_business_profiles_by_provider_id(
            provider_ids
        )

    async def request_otp(self, provider_id: uuid.UUID) -> None:
        """
        AC4's hard requirement, enforced structurally: this method (and
        its endpoint) accepts **no** phone-number parameter of any kind
        -- the number used always comes from the target provider's own
        stored `phone_country_code`/`phone_number` columns. Raises
        `ClaimPublicNumberUnavailableError` without ever calling
        `OtpService` if the provider has no public number on record
        (AC6's "public number is unusable" case).
        """
        provider = await self._get_claimable_provider_or_404(provider_id)
        if provider.phone_number is None or provider.phone_country_code is None:
            raise ClaimPublicNumberUnavailableError()

        await self.otp_service.request_otp(
            provider.phone_country_code,
            provider.phone_number,
            purpose=OtpPurpose.CLAIM_LISTING,
        )

    async def verify_otp(
        self, user_id: uuid.UUID, provider_id: uuid.UUID, code: str
    ) -> Provider:
        """
        AC5: verifies the submitted code against the provider's own
        stored public number, then -- only on success -- runs the
        shared `_finalize_claim` sequence. `InvalidOtpError`/
        `OtpLockedError` from `OtpService.verify_otp` propagate
        unchanged (AC6 -- the admin-review fallback is a distinct,
        user-initiated action via `request_admin_review`, never an
        automatic N-failures trigger) and never finalize a claim.
        """
        provider = await self._get_claimable_provider_or_404(provider_id)
        if provider.phone_number is None or provider.phone_country_code is None:
            raise ClaimPublicNumberUnavailableError()

        await self.otp_service.verify_otp(
            provider.phone_country_code,
            provider.phone_number,
            purpose=OtpPurpose.CLAIM_LISTING,
            code=code,
        )

        return await self._finalize_claim(provider.id, user_id)

    async def request_admin_review(
        self,
        user_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        reason: ClaimReviewReason,
    ) -> None:
        """
        AC6's explicit fallback -- creates a `claim_review_requests` row
        for either `reason="otp_failed"` (verification failed) or
        `reason="no_public_number"` (the listing has no usable public
        number, skipping the OTP step entirely).
        """
        provider = await self._get_claimable_provider_or_404(provider_id)
        await self.claim_review_request_service.create(
            provider_id=provider.id, claimant_user_id=user_id, reason=reason
        )

    async def _get_claimable_provider_or_404(self, provider_id: uuid.UUID) -> Provider:
        """
        Resolves a claim target -- must be a still-unclaimed Google-
        seeded listing. A self-registered or already-claimed provider,
        or a nonexistent id, all collapse into the same 404 rather than
        revealing which.
        """
        provider = await self.provider_repository.get_by_id(provider_id)
        if (
            provider is None
            or provider.listing_source != ListingSource.GOOGLE_SEEDED_UNCLAIMED
            or provider.is_claimed
        ):
            raise ClaimTargetNotFoundError()
        return provider

    async def _finalize_claim(
        self, provider_id: uuid.UUID, user_id: uuid.UUID
    ) -> Provider:
        """
        Decision 6/9's shared five-step finalization sequence -- the
        **only** place in this codebase that ever sets
        `is_claimed=True`. Called by both `verify_otp` above (the OTP-
        success path) and `AdminClaimService.approve_review_request`
        (the admin-approved fallback path), so the two success paths
        can never silently drift apart.

        1. Enforces the existing one-Provider-per-Account rule (PRO-001,
           AC8): rejects if `user_id` already owns a different Provider.
        2. Atomically transitions the provider to claimed via
           `ProviderRepository.try_claim_for_account` -- a single
           conditional `UPDATE ... WHERE is_claimed = false`, the
           genuine defense against two callers racing to claim the
           *same* listing concurrently (mirrors VER-002's
           `try_claim_for_review` fix for the analogous "exactly one
           winner" problem; a plain fetch-then-update here would leave
           a window where the second caller's write could silently
           overwrite the first claimant's `user_id` with no error at
           all). Raises `ClaimAlreadyClaimedError` if the row was no
           longer claimable by the time this executes.
        3. Sets `is_claimed=True`, `user_id`, `claimed_at=now()` (as
           part of the same atomic statement above).
        4. Resets `verification_status=PENDING`/`is_discoverable=False`
           via `ProviderService.apply_verification_outcome` (Decision 2)
           -- the same gate a freshly self-registered Business starts
           in (AC5).
        5. Grants `ROLE_PROVIDER` via `RoleAssignmentService`, reused
           unmodified from `create_provider`'s own call.
        """
        existing_provider_for_claimant = await self.provider_repository.get_by_user_id(
            user_id
        )
        if existing_provider_for_claimant is not None:
            raise ClaimAlreadyClaimedError(
                message=(
                    "Your account already has a provider listing -- only one "
                    "listing is allowed per account."
                )
            )

        claimed_at = datetime.now(UTC)
        won_the_claim = await self.provider_repository.try_claim_for_account(
            provider_id, user_id=user_id, claimed_at=claimed_at
        )
        if not won_the_claim:
            raise ClaimAlreadyClaimedError()

        claimed = await self.provider_service.apply_verification_outcome(
            provider_id,
            verification_status=VerificationStatus.PENDING,
            is_discoverable=False,
        )
        await self.role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)
        return claimed
