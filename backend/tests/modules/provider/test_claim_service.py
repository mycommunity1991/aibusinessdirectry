"""
Unit tests for `ClaimService` (CLM-001, AC4/AC5/AC6, Decision 6,
`Plan_S06_CLM-001.md`).

Repositories/services are mocked so these tests isolate `ClaimService`'s
own orchestration logic -- mirrors `test_provider_service.py`'s existing
mock-based pattern. The `OtpService` mock acts as the "spy" AC4's own
test requires: it records exactly which phone number `request_otp`/
`verify_otp` passed it, proving it always comes from the target
provider's own stored columns.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import (
    ClaimAlreadyClaimedError,
    ClaimPublicNumberUnavailableError,
    ClaimTargetNotFoundError,
    InvalidOtpError,
)
from app.modules.identity.models import OtpPurpose
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.services.claim_service import ClaimService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _unclaimed_provider(**overrides: object) -> Provider:
    payload: dict[str, object] = {
        "id": uuid.uuid4(),
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Al Noor Plumbing Services LLC",
        "slug": "al-noor-plumbing-services-llc-abc123",
        "phone_country_code": "+971",
        "phone_number": "43334455",
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "claimed_at": None,
        "google_place_id": "ChIJ_google_place_id_1",
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    return Provider(**payload)


@pytest.fixture
def mock_provider_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_user_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    repo.try_claim_for_account = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_provider_service() -> MagicMock:
    service = MagicMock()
    service.apply_verification_outcome = AsyncMock()
    service.search_unclaimed_listings = AsyncMock(return_value=([], 0))
    service.get_business_profiles_by_provider_id = AsyncMock(return_value={})
    return service


@pytest.fixture
def mock_otp_service() -> MagicMock:
    service = MagicMock()
    service.request_otp = AsyncMock()
    service.verify_otp = AsyncMock()
    return service


@pytest.fixture
def mock_role_assignment_service() -> MagicMock:
    service = MagicMock()
    service.ensure_role_assigned = AsyncMock()
    return service


@pytest.fixture
def mock_claim_review_request_service() -> MagicMock:
    service = MagicMock()
    service.create = AsyncMock()
    return service


@pytest.fixture
def claim_service(
    mock_provider_repository: MagicMock,
    mock_provider_service: MagicMock,
    mock_otp_service: MagicMock,
    mock_role_assignment_service: MagicMock,
    mock_claim_review_request_service: MagicMock,
) -> ClaimService:
    return ClaimService(
        provider_repository=mock_provider_repository,
        provider_service=mock_provider_service,
        otp_service=mock_otp_service,
        role_assignment_service=mock_role_assignment_service,
        claim_review_request_service=mock_claim_review_request_service,
    )


class TestRequestOtpUsesOnlyTheProvidersOwnNumber:
    """AC4/AC8's first requirement."""

    @pytest.mark.anyio
    async def test_uses_the_providers_own_stored_number(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider(
            phone_country_code="+971", phone_number="43334455"
        )
        mock_provider_repository.get_by_id.return_value = provider

        await claim_service.request_otp(provider.id)

        mock_otp_service.request_otp.assert_awaited_once_with(
            "+971", "43334455", purpose=OtpPurpose.CLAIM_LISTING
        )

    @pytest.mark.anyio
    async def test_request_otp_has_no_phone_number_parameter(
        self, claim_service: ClaimService
    ) -> None:
        """AC4's hard, structural requirement: the method accepts no
        phone-number argument of any kind -- there is no way for a
        caller-supplied number to ever reach `OtpService`."""
        import inspect

        signature = inspect.signature(claim_service.request_otp)
        assert list(signature.parameters) == ["provider_id"]

    @pytest.mark.anyio
    async def test_no_public_number_raises_without_calling_otp_service(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider(phone_country_code=None, phone_number=None)
        mock_provider_repository.get_by_id.return_value = provider

        with pytest.raises(ClaimPublicNumberUnavailableError):
            await claim_service.request_otp(provider.id)

        mock_otp_service.request_otp.assert_not_awaited()

    @pytest.mark.anyio
    async def test_a_nonexistent_provider_raises_not_found(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        mock_provider_repository.get_by_id.return_value = None

        with pytest.raises(ClaimTargetNotFoundError):
            await claim_service.request_otp(uuid.uuid4())

        mock_otp_service.request_otp.assert_not_awaited()

    @pytest.mark.anyio
    async def test_an_already_claimed_provider_is_not_a_valid_target(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider(is_claimed=True, user_id=uuid.uuid4())
        mock_provider_repository.get_by_id.return_value = provider

        with pytest.raises(ClaimTargetNotFoundError):
            await claim_service.request_otp(provider.id)

        mock_otp_service.request_otp.assert_not_awaited()

    @pytest.mark.anyio
    async def test_a_self_registered_provider_is_not_a_valid_target(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider(
            listing_source=ListingSource.SELF_REGISTERED,
            is_claimed=True,
            user_id=uuid.uuid4(),
        )
        mock_provider_repository.get_by_id.return_value = provider

        with pytest.raises(ClaimTargetNotFoundError):
            await claim_service.request_otp(provider.id)

        mock_otp_service.request_otp.assert_not_awaited()


class TestVerifyOtpSuccess:
    """AC5: atomic finalize on OTP success, all in one call."""

    @pytest.mark.anyio
    async def test_finalizes_the_claim_and_grants_role_provider(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_provider_service: MagicMock,
        mock_otp_service: MagicMock,
        mock_role_assignment_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider()
        user_id = uuid.uuid4()
        mock_provider_repository.get_by_id.return_value = provider
        mock_provider_repository.get_by_user_id.return_value = None
        mock_provider_repository.try_claim_for_account.return_value = True
        claimed_provider = _unclaimed_provider(
            id=provider.id,
            is_claimed=True,
            user_id=user_id,
            claimed_at=datetime.now(UTC),
            verification_status=VerificationStatus.PENDING,
            is_discoverable=False,
        )
        mock_provider_service.apply_verification_outcome.return_value = claimed_provider

        result = await claim_service.verify_otp(user_id, provider.id, "123456")

        mock_otp_service.verify_otp.assert_awaited_once_with(
            "+971",
            "43334455",
            purpose=OtpPurpose.CLAIM_LISTING,
            code="123456",
        )

        mock_provider_repository.try_claim_for_account.assert_awaited_once()
        claim_call_kwargs = mock_provider_repository.try_claim_for_account.await_args
        assert claim_call_kwargs.args[0] == provider.id
        assert claim_call_kwargs.kwargs["user_id"] == user_id
        assert claim_call_kwargs.kwargs["claimed_at"] is not None

        mock_provider_service.apply_verification_outcome.assert_awaited_once_with(
            provider.id,
            verification_status=VerificationStatus.PENDING,
            is_discoverable=False,
        )
        mock_role_assignment_service.ensure_role_assigned.assert_awaited_once_with(
            user_id, ROLE_PROVIDER
        )
        assert result is claimed_provider

    @pytest.mark.anyio
    async def test_second_claim_attempt_on_an_already_claimed_provider_conflicts(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
        mock_provider_service: MagicMock,
    ) -> None:
        """
        Decision 6's genuine race defense: `_finalize_claim` uses a
        single atomic conditional `UPDATE` (`try_claim_for_account`),
        not a plain fetch-then-write -- simulated here by having the
        atomic update itself report a lost race (`False`), exactly as
        it would if a concurrent caller's `UPDATE` had already won.
        """
        provider = _unclaimed_provider()
        mock_provider_repository.get_by_id.return_value = provider
        mock_provider_repository.try_claim_for_account.return_value = False

        with pytest.raises(ClaimAlreadyClaimedError):
            await claim_service.verify_otp(uuid.uuid4(), provider.id, "123456")

        mock_provider_service.apply_verification_outcome.assert_not_awaited()

    @pytest.mark.anyio
    async def test_one_provider_per_account_rejects_an_existing_owner(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
        mock_provider_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider()
        claimant_id = uuid.uuid4()
        mock_provider_repository.get_by_id.return_value = provider
        mock_provider_repository.get_by_user_id.return_value = _unclaimed_provider(
            id=uuid.uuid4(),
            is_claimed=True,
            user_id=claimant_id,
            listing_source=ListingSource.SELF_REGISTERED,
        )

        with pytest.raises(ClaimAlreadyClaimedError):
            await claim_service.verify_otp(claimant_id, provider.id, "123456")

        mock_provider_repository.try_claim_for_account.assert_not_awaited()
        mock_provider_service.apply_verification_outcome.assert_not_awaited()

    @pytest.mark.anyio
    async def test_no_public_number_raises_without_calling_otp_service(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider(phone_country_code=None, phone_number=None)
        mock_provider_repository.get_by_id.return_value = provider

        with pytest.raises(ClaimPublicNumberUnavailableError):
            await claim_service.verify_otp(uuid.uuid4(), provider.id, "123456")

        mock_otp_service.verify_otp.assert_not_awaited()


class TestOtpFailureNeverFinalizes:
    """AC6/AC8's second requirement: an OTP failure never finalizes a claim."""

    @pytest.mark.anyio
    async def test_invalid_otp_error_propagates_and_does_not_finalize(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_otp_service: MagicMock,
        mock_provider_service: MagicMock,
        mock_role_assignment_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider()
        mock_provider_repository.get_by_id.return_value = provider
        mock_otp_service.verify_otp.side_effect = InvalidOtpError()

        with pytest.raises(InvalidOtpError):
            await claim_service.verify_otp(uuid.uuid4(), provider.id, "000000")

        mock_provider_repository.try_claim_for_account.assert_not_awaited()
        mock_provider_service.apply_verification_outcome.assert_not_awaited()
        mock_role_assignment_service.ensure_role_assigned.assert_not_awaited()


class TestRequestAdminReview:
    """AC6: the explicit fallback path, for both reasons."""

    @pytest.mark.anyio
    async def test_otp_failed_reason_creates_a_correctly_reasoned_row(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_claim_review_request_service: MagicMock,
    ) -> None:
        provider = _unclaimed_provider()
        user_id = uuid.uuid4()
        mock_provider_repository.get_by_id.return_value = provider

        await claim_service.request_admin_review(
            user_id, provider.id, reason="otp_failed"
        )

        mock_claim_review_request_service.create.assert_awaited_once_with(
            provider_id=provider.id, claimant_user_id=user_id, reason="otp_failed"
        )

    @pytest.mark.anyio
    async def test_no_public_number_reason_creates_a_correctly_reasoned_row(
        self,
        claim_service: ClaimService,
        mock_provider_repository: MagicMock,
        mock_claim_review_request_service: MagicMock,
    ) -> None:
        """Skips the OTP step entirely -- never attempted, since there's
        no number to send a code to."""
        provider = _unclaimed_provider(phone_country_code=None, phone_number=None)
        user_id = uuid.uuid4()
        mock_provider_repository.get_by_id.return_value = provider

        await claim_service.request_admin_review(
            user_id, provider.id, reason="no_public_number"
        )

        mock_claim_review_request_service.create.assert_awaited_once_with(
            provider_id=provider.id,
            claimant_user_id=user_id,
            reason="no_public_number",
        )
