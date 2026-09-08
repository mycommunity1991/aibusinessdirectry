"""
Unit tests for `ProviderService` (PRO-001).

Repositories and `RoleAssignmentService` are mocked so these tests
isolate `ProviderService`'s own orchestration logic: one-provider-per-
account enforcement (AC8), type immutability (AC10), correct defaulting
(AC7/AC10), the `ROLE_PROVIDER` grant (Decision 1), and slug generation
(Decision 6). See `test_provider_endpoints.py` for end-to-end coverage
against a real database.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import ROLE_PROVIDER
from app.core.exceptions import ProviderAlreadyExistsError
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.schemas import (
    CreateBusinessDetailsRequest,
    CreateFreelancerDetailsRequest,
    CreateProviderRequest,
)
from app.modules.provider.services.provider_service import ProviderService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_provider_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=None)
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_business_profile_repository() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_provider_id = AsyncMock()
    return repo


@pytest.fixture
def mock_freelancer_profile_repository() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_provider_id = AsyncMock()
    return repo


@pytest.fixture
def mock_role_assignment_service() -> MagicMock:
    service = MagicMock()
    service.ensure_role_assigned = AsyncMock()
    return service


@pytest.fixture
def provider_service(
    mock_provider_repository: MagicMock,
    mock_business_profile_repository: MagicMock,
    mock_freelancer_profile_repository: MagicMock,
    mock_role_assignment_service: MagicMock,
) -> ProviderService:
    return ProviderService(
        provider_repository=mock_provider_repository,
        business_profile_repository=mock_business_profile_repository,
        freelancer_profile_repository=mock_freelancer_profile_repository,
        role_assignment_service=mock_role_assignment_service,
    )


def _business_details(**overrides: object) -> CreateBusinessDetailsRequest:
    payload: dict[str, object] = {
        "address_line": "Shop 4, Al Wasl Road",
        "city": "Dubai",
        "region": "Dubai",
        "country_code": "AE",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "operating_hours": None,
        "delivery_radius_meters": None,
        "trade_license_number": None,
    }
    payload.update(overrides)
    return CreateBusinessDetailsRequest(**payload)


def _freelancer_details(**overrides: object) -> CreateFreelancerDetailsRequest:
    payload: dict[str, object] = {
        "base_latitude": 25.2048,
        "base_longitude": 55.2708,
        "country_code": "AE",
        "service_radius_meters": 5000,
        "skills": ["Plumbing"],
        "years_experience": 3,
    }
    payload.update(overrides)
    return CreateFreelancerDetailsRequest(**payload)


def _business_provider_request(**overrides: object) -> CreateProviderRequest:
    payload: dict[str, object] = {
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Plumbing",
        "phone_country_code": "+971",
        "phone_number": "501234567",
        "whatsapp_number": None,
        "category_label": "Plumbing",
        "description": None,
        "business_details": _business_details(),
        "freelancer_details": None,
    }
    payload.update(overrides)
    return CreateProviderRequest(**payload)


def _freelancer_provider_request(**overrides: object) -> CreateProviderRequest:
    payload: dict[str, object] = {
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "phone_country_code": "+971",
        "phone_number": "509876543",
        "whatsapp_number": None,
        "category_label": "Plumbing",
        "description": None,
        "business_details": None,
        "freelancer_details": _freelancer_details(),
    }
    payload.update(overrides)
    return CreateProviderRequest(**payload)


def _provider(**overrides: object) -> Provider:
    payload: dict[str, object] = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Plumbing",
        "slug": "acme-plumbing-abc123",
        "description": None,
        "phone_country_code": "+971",
        "phone_number": "501234567",
        "whatsapp_number": None,
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "claimed_at": datetime.now(UTC),
        "google_place_id": None,
        "verification_status": VerificationStatus.PENDING,
        "is_discoverable": False,
        "average_rating": None,
        "review_count": 0,
        "country_code": "AE",
        "category_label": "Plumbing",
    }
    payload.update(overrides)
    return Provider(**payload)


class TestCreateProviderDefaults:
    """AC7/AC10: defaults asserted for both subtypes, separately."""

    @pytest.mark.anyio
    async def test_creates_business_provider_with_correct_defaults(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
        mock_freelancer_profile_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        created = _provider(user_id=user_id, provider_type=ProviderType.BUSINESS)
        mock_provider_repository.create.return_value = created

        result = await provider_service.create_provider(
            user_id, payload=_business_provider_request()
        )

        create_fields = mock_provider_repository.create.await_args.args[0]
        assert create_fields["user_id"] == user_id
        assert create_fields["provider_type"] == ProviderType.BUSINESS
        assert create_fields["listing_source"] == ListingSource.SELF_REGISTERED
        assert create_fields["is_claimed"] is True
        assert create_fields["verification_status"] == VerificationStatus.PENDING
        assert create_fields["is_discoverable"] is False
        assert create_fields["country_code"] == "AE"
        mock_business_profile_repository.create.assert_awaited_once()
        mock_freelancer_profile_repository.create.assert_not_awaited()
        assert result is created

    @pytest.mark.anyio
    async def test_creates_freelancer_provider_with_correct_defaults(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
        mock_freelancer_profile_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        created = _provider(user_id=user_id, provider_type=ProviderType.FREELANCER)
        mock_provider_repository.create.return_value = created

        result = await provider_service.create_provider(
            user_id, payload=_freelancer_provider_request()
        )

        create_fields = mock_provider_repository.create.await_args.args[0]
        assert create_fields["user_id"] == user_id
        assert create_fields["provider_type"] == ProviderType.FREELANCER
        assert create_fields["listing_source"] == ListingSource.SELF_REGISTERED
        assert create_fields["is_claimed"] is True
        assert create_fields["verification_status"] == VerificationStatus.PENDING
        assert create_fields["is_discoverable"] is False
        assert create_fields["country_code"] == "AE"
        mock_freelancer_profile_repository.create.assert_awaited_once()
        mock_business_profile_repository.create.assert_not_awaited()
        assert result is created


class TestOneProviderPerAccount:
    """AC8 (same-type duplicate) and AC10 (type immutability, different type)."""

    @pytest.mark.anyio
    async def test_second_create_with_same_type_raises_already_exists(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        existing = _provider(provider_type=ProviderType.BUSINESS)
        mock_provider_repository.get_by_user_id.return_value = existing

        with pytest.raises(ProviderAlreadyExistsError):
            await provider_service.create_provider(
                existing.user_id, payload=_business_provider_request()
            )

        mock_provider_repository.create.assert_not_awaited()

    @pytest.mark.anyio
    async def test_second_create_with_a_different_type_also_raises_already_exists(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        """Decision 3: a caller cannot "switch" subtype via a second
        creation attempt -- the same 409 fires regardless of the
        newly-requested `provider_type`."""
        existing = _provider(provider_type=ProviderType.BUSINESS)
        mock_provider_repository.get_by_user_id.return_value = existing

        with pytest.raises(ProviderAlreadyExistsError):
            await provider_service.create_provider(
                existing.user_id, payload=_freelancer_provider_request()
            )

        mock_provider_repository.create.assert_not_awaited()


class TestRoleGrant:
    """Decision 1: `create_provider` grants `ROLE_PROVIDER`."""

    @pytest.mark.anyio
    async def test_create_provider_grants_role_provider(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_role_assignment_service: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        mock_provider_repository.create.return_value = _provider(user_id=user_id)

        await provider_service.create_provider(
            user_id, payload=_business_provider_request()
        )

        mock_role_assignment_service.ensure_role_assigned.assert_awaited_once_with(
            user_id, ROLE_PROVIDER
        )


class TestGenerateUniqueSlug:
    """Decision 6: server-generated slug, bounded retry on collision."""

    @pytest.mark.anyio
    async def test_retries_on_slug_collision_until_unique(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        collision = _provider(display_name="Acme Plumbing")
        mock_provider_repository.get_by_slug.side_effect = [collision, None]
        suffixes = iter(["aaaaaa", "bbbbbb"])
        monkeypatch.setattr(
            "app.modules.provider.services.provider_service.secrets.token_hex",
            lambda _n: next(suffixes),
        )

        slug = await provider_service._generate_unique_slug("Acme Plumbing")

        assert slug == "acme-plumbing-bbbbbb"
        assert mock_provider_repository.get_by_slug.await_count == 2

    @pytest.mark.anyio
    async def test_two_providers_with_the_same_display_name_get_different_slugs(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_provider_repository.get_by_slug.return_value = None
        suffixes = iter(["aaaaaa", "bbbbbb"])
        monkeypatch.setattr(
            "app.modules.provider.services.provider_service.secrets.token_hex",
            lambda _n: next(suffixes),
        )

        first_slug = await provider_service._generate_unique_slug("Acme Plumbing")
        second_slug = await provider_service._generate_unique_slug("Acme Plumbing")

        assert first_slug != second_slug
        assert first_slug == "acme-plumbing-aaaaaa"
        assert second_slug == "acme-plumbing-bbbbbb"


class TestGetMyProvider:
    """Decision 9: thin wrapper, not get-or-create."""

    @pytest.mark.anyio
    async def test_returns_none_when_no_provider_exists(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        mock_provider_repository.get_by_user_id.return_value = None

        result = await provider_service.get_my_provider(uuid.uuid4())

        assert result is None

    @pytest.mark.anyio
    async def test_returns_the_existing_provider(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        existing = _provider()
        mock_provider_repository.get_by_user_id.return_value = existing

        result = await provider_service.get_my_provider(existing.user_id)

        assert result is existing


class TestGetSubtypeProfiles:
    @pytest.mark.anyio
    async def test_business_provider_returns_only_the_business_profile(
        self,
        provider_service: ProviderService,
        mock_business_profile_repository: MagicMock,
        mock_freelancer_profile_repository: MagicMock,
    ) -> None:
        provider = _provider(provider_type=ProviderType.BUSINESS)
        business_profile = MagicMock()
        mock_business_profile_repository.get_by_provider_id.return_value = (
            business_profile
        )

        business, freelancer = await provider_service.get_subtype_profiles(provider)

        assert business is business_profile
        assert freelancer is None
        mock_freelancer_profile_repository.get_by_provider_id.assert_not_awaited()

    @pytest.mark.anyio
    async def test_freelancer_provider_returns_only_the_freelancer_profile(
        self,
        provider_service: ProviderService,
        mock_business_profile_repository: MagicMock,
        mock_freelancer_profile_repository: MagicMock,
    ) -> None:
        provider = _provider(provider_type=ProviderType.FREELANCER)
        freelancer_profile = MagicMock()
        mock_freelancer_profile_repository.get_by_provider_id.return_value = (
            freelancer_profile
        )

        business, freelancer = await provider_service.get_subtype_profiles(provider)

        assert freelancer is freelancer_profile
        assert business is None
        mock_business_profile_repository.get_by_provider_id.assert_not_awaited()
