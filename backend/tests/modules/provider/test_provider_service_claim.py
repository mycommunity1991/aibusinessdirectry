"""
Unit tests for `ProviderService.create_google_seeded_provider`/
`backfill_google_seeded_provider` (CLM-001, AC1/AC7, Decision 2/3/4,
`Plan_S06_CLM-001.md`).

Repositories are mocked so these tests isolate `ProviderService`'s own
orchestration logic -- mirrors `test_provider_service.py`'s existing
mock-based pattern exactly.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.provider.models import (
    BusinessProfile,
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
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
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_business_profile_repository() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_provider_id = AsyncMock()
    repo.update = AsyncMock()
    repo.list_by_provider_ids = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_freelancer_profile_repository() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_provider_id = AsyncMock()
    return repo


@pytest.fixture
def mock_provider_category_label_repository() -> MagicMock:
    repo = MagicMock()
    repo.list_for_provider = AsyncMock(return_value=[])
    repo.replace_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_service_area_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_for_provider = AsyncMock(return_value=None)
    repo.upsert_for_provider = AsyncMock()
    return repo


@pytest.fixture
def mock_role_assignment_service() -> MagicMock:
    service = MagicMock()
    service.ensure_role_assigned = AsyncMock()
    return service


@pytest.fixture
def mock_provider_search_repository() -> MagicMock:
    repo = MagicMock()
    repo.search_nearby = AsyncMock(return_value=([], {}, 0))
    return repo


@pytest.fixture
def mock_portfolio_repository() -> MagicMock:
    repo = MagicMock()
    repo.list_active_for_provider_ids = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def provider_service(
    mock_provider_repository: MagicMock,
    mock_business_profile_repository: MagicMock,
    mock_freelancer_profile_repository: MagicMock,
    mock_provider_category_label_repository: MagicMock,
    mock_service_area_repository: MagicMock,
    mock_role_assignment_service: MagicMock,
    mock_provider_search_repository: MagicMock,
    mock_portfolio_repository: MagicMock,
) -> ProviderService:
    return ProviderService(
        provider_repository=mock_provider_repository,
        business_profile_repository=mock_business_profile_repository,
        freelancer_profile_repository=mock_freelancer_profile_repository,
        provider_category_label_repository=mock_provider_category_label_repository,
        service_area_repository=mock_service_area_repository,
        role_assignment_service=mock_role_assignment_service,
        provider_search_repository=mock_provider_search_repository,
        portfolio_repository=mock_portfolio_repository,
    )


def _google_seeded_provider(**overrides: object) -> Provider:
    payload: dict[str, object] = {
        "id": uuid.uuid4(),
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Al Noor Plumbing Services LLC",
        "slug": "al-noor-plumbing-services-llc-abc123",
        "description": None,
        "phone_country_code": "+971",
        "phone_number": "43334455",
        "whatsapp_number": None,
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "claimed_at": None,
        "google_place_id": "ChIJ_google_place_id_1",
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "average_rating": None,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    return Provider(**payload)


def _business_details(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "address_line": "Shop 12, Al Wasl Road, Dubai",
        "city": "Dubai",
        "region": "Dubai",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "operating_hours": None,
        "delivery_radius_meters": None,
    }
    payload.update(overrides)
    return payload


class TestCreateGoogleSeededProvider:
    """AC1: exactly `listing_source`/`is_claimed`/`google_place_id`,
    never `self_registered`; a companion `service_areas` row (Decision
    4)."""

    @pytest.mark.anyio
    async def test_sets_the_exact_ac1_fields(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        mock_provider_repository.create.return_value = _google_seeded_provider()

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_1",
            display_name="Al Noor Plumbing Services LLC",
            phone_country_code="+971",
            phone_number="43334455",
            country_code="AE",
            business_details=_business_details(),
            category_label="Plumbing",
        )

        create_fields = mock_provider_repository.create.await_args.args[0]
        assert create_fields["listing_source"] == ListingSource.GOOGLE_SEEDED_UNCLAIMED
        assert create_fields["listing_source"] != ListingSource.SELF_REGISTERED
        assert create_fields["is_claimed"] is False
        assert create_fields["google_place_id"] == "ChIJ_google_place_id_1"
        assert create_fields["user_id"] is None
        assert create_fields["claimed_at"] is None

    @pytest.mark.anyio
    async def test_sets_synthetic_approved_and_discoverable(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        """Decision 2: import-time state is `verification_status=
        approved`/`is_discoverable=true`, set directly (never through
        `apply_verification_outcome`, since there is no existing row)."""
        mock_provider_repository.create.return_value = _google_seeded_provider()

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_2",
            display_name="Acme Cafe",
            phone_country_code=None,
            phone_number=None,
            country_code="AE",
            business_details=_business_details(),
            category_label=None,
        )

        create_fields = mock_provider_repository.create.await_args.args[0]
        assert create_fields["verification_status"] == VerificationStatus.APPROVED
        assert create_fields["is_discoverable"] is True

    @pytest.mark.anyio
    async def test_always_provider_type_business(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
    ) -> None:
        """Decision 3: Google Places data never fits a Freelancer."""
        mock_provider_repository.create.return_value = _google_seeded_provider()

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_3",
            display_name="Acme Cafe",
            phone_country_code=None,
            phone_number=None,
            country_code="AE",
            business_details=_business_details(),
            category_label=None,
        )

        create_fields = mock_provider_repository.create.await_args.args[0]
        assert create_fields["provider_type"] == ProviderType.BUSINESS

    @pytest.mark.anyio
    async def test_creates_a_matching_business_profile_and_service_area(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
        mock_service_area_repository: MagicMock,
    ) -> None:
        created = _google_seeded_provider()
        mock_provider_repository.create.return_value = created

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_4",
            display_name="Acme Cafe",
            phone_country_code="+971",
            phone_number="501234567",
            country_code="AE",
            business_details=_business_details(latitude=25.1, longitude=55.2),
            category_label="Cafe",
        )

        mock_business_profile_repository.create.assert_awaited_once()
        business_fields = mock_business_profile_repository.create.await_args.args[0]
        assert business_fields["provider_id"] == created.id
        assert business_fields["address_line"] == "Shop 12, Al Wasl Road, Dubai"

        mock_service_area_repository.upsert_for_provider.assert_awaited_once_with(
            created.id,
            center_latitude=25.1,
            center_longitude=55.2,
            radius_meters=0,
        )

    @pytest.mark.anyio
    async def test_creates_one_best_effort_primary_category_label(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_provider_category_label_repository: MagicMock,
    ) -> None:
        created = _google_seeded_provider()
        mock_provider_repository.create.return_value = created

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_5",
            display_name="Acme Cafe",
            phone_country_code=None,
            phone_number=None,
            country_code="AE",
            business_details=_business_details(),
            category_label="Cafe",
        )

        mock_provider_category_label_repository.replace_all.assert_awaited_once_with(
            created.id, [{"label": "Cafe", "is_primary": True}]
        )

    @pytest.mark.anyio
    async def test_no_category_label_skips_the_label_write(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_provider_category_label_repository: MagicMock,
    ) -> None:
        mock_provider_repository.create.return_value = _google_seeded_provider()

        await provider_service.create_google_seeded_provider(
            google_place_id="ChIJ_google_place_id_6",
            display_name="Acme Cafe",
            phone_country_code=None,
            phone_number=None,
            country_code="AE",
            business_details=_business_details(),
            category_label=None,
        )

        mock_provider_category_label_repository.replace_all.assert_not_awaited()


class TestBackfillGoogleSeededProviderUnclaimed:
    """AC7: `is_claimed=False` -> full overwrite of every mapped field."""

    @pytest.mark.anyio
    async def test_fully_overwrites_provider_and_business_profile_fields(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
        mock_service_area_repository: MagicMock,
    ) -> None:
        provider = _google_seeded_provider(
            is_claimed=False, display_name="Old Name", phone_number="111"
        )
        existing_profile = BusinessProfile(
            provider_id=provider.id,
            address_line="Old Address",
            city="Old City",
            region=None,
            latitude=1.0,
            longitude=1.0,
            operating_hours=None,
            delivery_radius_meters=None,
        )
        mock_business_profile_repository.get_by_provider_id.return_value = (
            existing_profile
        )
        mock_provider_repository.update.return_value = provider
        mock_business_profile_repository.update.return_value = existing_profile

        await provider_service.backfill_google_seeded_provider(
            provider,
            display_name="New Name",
            phone_country_code="+971",
            phone_number="999",
            country_code="AE",
            business_details=_business_details(
                address_line="New Address", city="New City"
            ),
            category_label="Plumbing",
        )

        provider_update_fields = mock_provider_repository.update.await_args.args[1]
        assert provider_update_fields["display_name"] == "New Name"
        assert provider_update_fields["phone_number"] == "999"

        business_update_call = mock_business_profile_repository.update.await_args
        business_update_fields = business_update_call.args[1]
        assert business_update_fields["address_line"] == "New Address"
        assert business_update_fields["city"] == "New City"

        mock_service_area_repository.upsert_for_provider.assert_awaited_once()


class TestBackfillGoogleSeededProviderClaimed:
    """
    AC7's critical case: `is_claimed=True` -> writes ONLY currently
    empty fields, proven with MATERIALLY DIFFERENT fresh Google data so
    a passing test can't be explained by the fresh data happening to
    match the existing value.
    """

    @pytest.mark.anyio
    async def test_a_non_empty_field_survives_materially_different_fresh_data(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
        mock_service_area_repository: MagicMock,
    ) -> None:
        provider = _google_seeded_provider(
            is_claimed=True,
            user_id=uuid.uuid4(),
            display_name="Owner-Edited Business Name",
            phone_country_code="+971",
            phone_number="500000001",
        )
        existing_profile = BusinessProfile(
            provider_id=provider.id,
            address_line="Owner-Edited Address, Sharjah",
            city="Sharjah",
            region="Sharjah",
            latitude=25.35,
            longitude=55.4,
            operating_hours={"monday": {"open": "08:00", "close": "20:00"}},
            # Deliberately non-empty (an owner-added value post-claim) --
            # every mapped field on this fixture is non-empty, so the
            # entire re-sync should be a complete no-op.
            delivery_radius_meters=3000,
        )
        mock_business_profile_repository.get_by_provider_id.return_value = (
            existing_profile
        )
        mock_provider_repository.update.return_value = provider

        result = await provider_service.backfill_google_seeded_provider(
            provider,
            display_name="Completely Different Fresh Google Name",
            phone_country_code="+971",
            phone_number="599999999",
            country_code="AE",
            business_details=_business_details(
                address_line="A Totally Different Fresh Address, Dubai",
                city="Dubai",
                region="Dubai",
                latitude=1.111,
                longitude=2.222,
                operating_hours={"monday": {"open": "00:00", "close": "01:00"}},
            ),
            category_label="Something Else Entirely",
        )

        # `provider_repository.update` must never even be called with
        # any of the owner-edited, already-non-empty fields -- proving
        # the fresh (materially different) values were never applied.
        assert result is provider
        mock_provider_repository.update.assert_not_awaited()
        mock_business_profile_repository.update.assert_not_awaited()
        mock_service_area_repository.upsert_for_provider.assert_not_awaited()

    @pytest.mark.anyio
    async def test_a_genuinely_empty_field_is_backfilled(
        self,
        provider_service: ProviderService,
        mock_provider_repository: MagicMock,
        mock_business_profile_repository: MagicMock,
    ) -> None:
        provider = _google_seeded_provider(
            is_claimed=True,
            user_id=uuid.uuid4(),
            display_name="Owner-Edited Business Name",
            phone_country_code=None,
            phone_number=None,
        )
        existing_profile = BusinessProfile(
            provider_id=provider.id,
            address_line="Owner-Edited Address",
            city=None,
            region=None,
            latitude=25.35,
            longitude=55.4,
            operating_hours=None,
            delivery_radius_meters=None,
        )
        mock_business_profile_repository.get_by_provider_id.return_value = (
            existing_profile
        )
        mock_provider_repository.update.return_value = provider
        mock_business_profile_repository.update.return_value = existing_profile

        await provider_service.backfill_google_seeded_provider(
            provider,
            display_name="Fresh Google Name",
            phone_country_code="+971",
            phone_number="500000002",
            country_code="AE",
            business_details=_business_details(
                address_line="Fresh Address -- should be ignored",
                city="Fresh City",
            ),
            category_label=None,
        )

        provider_update_fields = mock_provider_repository.update.await_args.args[1]
        # `display_name` already had a non-empty value -- must not be
        # in the write set at all.
        assert "display_name" not in provider_update_fields
        assert provider_update_fields["phone_country_code"] == "+971"
        assert provider_update_fields["phone_number"] == "500000002"

        business_update_call = mock_business_profile_repository.update.await_args
        business_update_fields = business_update_call.args[1]
        assert "address_line" not in business_update_fields
        assert business_update_fields["city"] == "Fresh City"
