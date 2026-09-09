"""
Integration tests for `AdminClaimService` (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`), exercised against a real Postgres database --
mirrors `test_admin_verification_service.py`'s pattern.

The central assertion this file exists to prove: `approve_review_request`
finalizes a claim via the **identical** `ClaimService._finalize_claim`
logic the OTP-success path uses (same field writes, same role grant),
not a duplicated copy that could silently drift.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import (
    ClaimAlreadyClaimedError,
    ClaimReviewRequestNotFoundError,
)
from app.modules.administration.repositories.claim_review_request_repository import (
    ClaimReviewRequestRepository,
)
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewRequestService,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.identity.services.seed_data import seed_roles
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.portfolio_repository import (
    PortfolioRepository,
)
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.provider_search_repository import (
    ProviderSearchRepository,
)
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.services.admin_claim_service import AdminClaimService
from app.modules.provider.services.claim_service import ClaimService
from app.modules.provider.services.provider_service import ProviderService


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_unclaimed_provider(db_session, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Cafe",
        "slug": f"acme-cafe-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "google_place_id": f"ChIJ_{uuid.uuid4().hex[:10]}",
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


def _provider_service(db_session) -> ProviderService:
    return ProviderService(
        provider_repository=ProviderRepository(db_session),
        business_profile_repository=BusinessProfileRepository(db_session),
        freelancer_profile_repository=FreelancerProfileRepository(db_session),
        provider_category_label_repository=ProviderCategoryLabelRepository(db_session),
        service_area_repository=ServiceAreaRepository(db_session),
        role_assignment_service=RoleAssignmentService(RoleRepository(db_session)),
        provider_search_repository=ProviderSearchRepository(db_session),
        portfolio_repository=PortfolioRepository(db_session),
    )


def _claim_review_request_service(db_session) -> ClaimReviewRequestService:
    return ClaimReviewRequestService(ClaimReviewRequestRepository(db_session))


def _claim_service(db_session) -> ClaimService:
    return ClaimService(
        provider_repository=ProviderRepository(db_session),
        provider_service=_provider_service(db_session),
        otp_service=AsyncMock(),
        role_assignment_service=RoleAssignmentService(RoleRepository(db_session)),
        claim_review_request_service=_claim_review_request_service(db_session),
    )


def _admin_claim_service(db_session) -> AdminClaimService:
    return AdminClaimService(
        claim_review_request_service=_claim_review_request_service(db_session),
        claim_service=_claim_service(db_session),
        provider_service=_provider_service(db_session),
    )


class TestApproveReviewRequestFinalizesIdenticallyToOtp:
    async def test_approve_sets_the_same_fields_the_otp_path_sets(
        self, db_session
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        admin = await _make_user(db_session, "910000001")
        claimant = await _make_user(db_session, "910000002")
        provider = await _make_unclaimed_provider(db_session)
        review_service = _claim_review_request_service(db_session)
        request = await review_service.create(
            provider_id=provider.id, claimant_user_id=claimant.id, reason="otp_failed"
        )
        await db_session.commit()

        admin_claim_service = _admin_claim_service(db_session)
        (
            resolved_request,
            claimed_provider,
        ) = await admin_claim_service.approve_review_request(admin.id, request.id)
        await db_session.commit()

        assert claimed_provider.is_claimed is True
        assert claimed_provider.user_id == claimant.id
        assert claimed_provider.claimed_at is not None
        assert claimed_provider.verification_status == VerificationStatus.PENDING
        assert claimed_provider.is_discoverable is False

        assert resolved_request.status == "resolved"
        assert resolved_request.resolution == "approved"
        assert resolved_request.reviewed_by == admin.id
        assert resolved_request.reviewed_at is not None

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.is_claimed is True
        assert refreshed_provider.user_id == claimant.id

        role_names = await RoleRepository(db_session).get_role_names_for_user(
            claimant.id
        )
        assert ROLE_PROVIDER in role_names

    async def test_approving_a_nonexistent_request_raises_404(self, db_session) -> None:
        admin = await _make_user(db_session, "910000003")
        admin_claim_service = _admin_claim_service(db_session)

        with pytest.raises(ClaimReviewRequestNotFoundError):
            await admin_claim_service.approve_review_request(admin.id, uuid.uuid4())


class TestRejectLeavesProviderUnclaimed:
    async def test_reject_never_writes_to_the_provider(self, db_session) -> None:
        admin = await _make_user(db_session, "910000004")
        claimant = await _make_user(db_session, "910000005")
        provider = await _make_unclaimed_provider(db_session)
        review_service = _claim_review_request_service(db_session)
        request = await review_service.create(
            provider_id=provider.id,
            claimant_user_id=claimant.id,
            reason="no_public_number",
        )
        await db_session.commit()

        admin_claim_service = _admin_claim_service(db_session)
        resolved_request = await admin_claim_service.reject_review_request(
            admin.id, request.id, notes="Doesn't look right."
        )
        await db_session.commit()

        assert resolved_request.status == "resolved"
        assert resolved_request.resolution == "rejected"
        assert resolved_request.resolution_notes == "Doesn't look right."

        refreshed_provider = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed_provider is not None
        assert refreshed_provider.is_claimed is False
        assert refreshed_provider.user_id is None

        role_names = await RoleRepository(db_session).get_role_names_for_user(
            claimant.id
        )
        assert ROLE_PROVIDER not in role_names


class TestConcurrentClaimRace:
    """
    Regression test proving `ClaimService._finalize_claim`'s
    `ProviderRepository.try_claim_for_account` genuinely closes the
    race window (CLM-001, Decision 6) -- two truly concurrent claim
    attempts on the *same* still-unclaimed listing, each via its own
    independent `AsyncSession`/transaction, must result in exactly one
    winner and one `ClaimAlreadyClaimedError`, never both silently
    "succeeding" (which a plain fetch-then-update would allow, since
    neither session would see the other's uncommitted write). Mirrors
    `test_admin_verification_service.py`'s `TestConcurrentApprovalRace`.
    """

    async def test_two_concurrent_claims_on_the_same_listing_only_one_wins(
        self, db_engine: AsyncEngine, db_session
    ) -> None:
        provider = await _make_unclaimed_provider(db_session)
        claimant_a = await _make_user(db_session, "920000001")
        claimant_b = await _make_user(db_session, "920000002")

        session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

        async def _attempt(claimant_id: uuid.UUID) -> str:
            async with session_factory() as session:
                claim_service = _claim_service(session)
                try:
                    await claim_service._finalize_claim(  # noqa: SLF001
                        provider.id, claimant_id
                    )
                    await session.commit()
                    return "claimed"
                except ClaimAlreadyClaimedError:
                    await session.rollback()
                    return "conflict"

        results = await asyncio.gather(_attempt(claimant_a.id), _attempt(claimant_b.id))

        assert sorted(results) == ["claimed", "conflict"]

        # `db_session`'s identity map still holds the pre-claim `provider`
        # object from `_make_unclaimed_provider` above (`expire_on_commit=
        # False`) -- the actual claiming `UPDATE` happened on a completely
        # different session/connection, so a genuinely fresh session (not
        # `db_session`'s own stale identity map) is used to verify the
        # persisted outcome.
        async with session_factory() as verify_session:
            refreshed_provider = await ProviderRepository(verify_session).get_by_id(
                provider.id
            )
        assert refreshed_provider is not None
        assert refreshed_provider.is_claimed is True
        assert refreshed_provider.user_id in {claimant_a.id, claimant_b.id}
