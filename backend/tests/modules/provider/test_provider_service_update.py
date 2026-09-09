"""
Integration tests for `ProviderService.update_basic_info` (PRO-002,
`PATCH /providers/me`'s handler), exercised against a real Postgres
database -- partial-update semantics, category-label validation,
subtype-mismatch rejection, and the AC6/immutability guarantees are all
best verified against real repository queries.
"""

import uuid

import pytest

from app.core.exceptions import (
    InvalidCategoryLabelsError,
    ProviderNotFoundError,
    SubtypeDetailsMismatchError,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    BusinessProfile,
    FreelancerProfile,
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
from app.modules.provider.services.provider_service import ProviderService


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_business_provider(db_session, user: User) -> Provider:
    provider = Provider(
        user_id=user.id,
        provider_type=ProviderType.BUSINESS,
        display_name="Acme Plumbing",
        slug=f"acme-plumbing-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.PENDING,
        is_discoverable=False,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    business_profile = BusinessProfile(
        provider_id=provider.id,
        address_line="Shop 4, Al Wasl Road",
        city="Dubai",
        region="Dubai",
        latitude=25.2048,
        longitude=55.2708,
        delivery_radius_meters=5000,
    )
    db_session.add(business_profile)
    await db_session.commit()
    return provider


async def _create_freelancer_provider(db_session, user: User) -> Provider:
    provider = Provider(
        user_id=user.id,
        provider_type=ProviderType.FREELANCER,
        display_name="Jane the Plumber",
        slug=f"jane-the-plumber-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.PENDING,
        is_discoverable=False,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    freelancer_profile = FreelancerProfile(
        provider_id=provider.id,
        base_latitude=25.2048,
        base_longitude=55.2708,
        service_radius_meters=8000,
        skills=["Plumbing"],
        years_experience=3,
    )
    db_session.add(freelancer_profile)
    await db_session.commit()
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


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestPartialUpdateSemantics:
    @pytest.mark.anyio
    async def test_only_updates_fields_present_in_the_payload(self, db_session) -> None:
        """AC5: partial update -- untouched fields keep their prior value."""
        user = await _create_user(db_session, "507000001")
        provider = await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        updated = await service.update_basic_info(
            user.id, fields={"display_name": "Acme Plumbing & AC Repair"}
        )

        assert updated.display_name == "Acme Plumbing & AC Repair"
        assert updated.phone_country_code == provider.phone_country_code
        assert updated.whatsapp_number == provider.whatsapp_number

    @pytest.mark.anyio
    async def test_raises_not_found_for_a_caller_with_no_provider(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000002")
        service = _provider_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.update_basic_info(user.id, fields={"display_name": "X"})


class TestCategoryLabelValidation:
    @pytest.mark.anyio
    async def test_replaces_the_label_set_with_exactly_one_primary(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000003")
        provider = await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        await service.update_basic_info(
            user.id,
            fields={
                "category_labels": [
                    {"label": "Plumbing", "is_primary": True},
                    {"label": "AC Repair", "is_primary": False},
                ]
            },
        )

        labels = await service.get_category_labels(provider.id)
        assert {label.label for label in labels} == {"Plumbing", "AC Repair"}
        primaries = [label for label in labels if label.is_primary]
        assert len(primaries) == 1
        assert primaries[0].label == "Plumbing"

    @pytest.mark.anyio
    async def test_rejects_zero_primary_labels(self, db_session) -> None:
        user = await _create_user(db_session, "507000004")
        await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        with pytest.raises(InvalidCategoryLabelsError):
            await service.update_basic_info(
                user.id,
                fields={
                    "category_labels": [{"label": "Plumbing", "is_primary": False}]
                },
            )

    @pytest.mark.anyio
    async def test_rejects_more_than_one_primary_label(self, db_session) -> None:
        user = await _create_user(db_session, "507000005")
        await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        with pytest.raises(InvalidCategoryLabelsError):
            await service.update_basic_info(
                user.id,
                fields={
                    "category_labels": [
                        {"label": "Plumbing", "is_primary": True},
                        {"label": "AC Repair", "is_primary": True},
                    ]
                },
            )

    @pytest.mark.anyio
    async def test_rejects_more_than_five_labels(self, db_session) -> None:
        user = await _create_user(db_session, "507000006")
        await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        labels = [{"label": f"Label {i}", "is_primary": i == 0} for i in range(6)]

        with pytest.raises(InvalidCategoryLabelsError):
            await service.update_basic_info(user.id, fields={"category_labels": labels})

    @pytest.mark.anyio
    async def test_a_subsequent_replace_leaves_exactly_one_primary(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000007")
        provider = await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        await service.update_basic_info(
            user.id,
            fields={"category_labels": [{"label": "Plumbing", "is_primary": True}]},
        )
        await service.update_basic_info(
            user.id,
            fields={
                "category_labels": [
                    {"label": "Electrical", "is_primary": True},
                    {"label": "Plumbing", "is_primary": False},
                ]
            },
        )

        labels = await service.get_category_labels(provider.id)
        assert len(labels) == 2
        primaries = [label for label in labels if label.is_primary]
        assert len(primaries) == 1
        assert primaries[0].label == "Electrical"


class TestSubtypeDetailsMismatch:
    @pytest.mark.anyio
    async def test_editing_business_details_on_a_freelancer_is_rejected(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000008")
        await _create_freelancer_provider(db_session, user)
        service = _provider_service(db_session)

        with pytest.raises(SubtypeDetailsMismatchError):
            await service.update_basic_info(
                user.id, fields={"business_details": {"city": "Abu Dhabi"}}
            )

    @pytest.mark.anyio
    async def test_editing_freelancer_details_on_a_business_is_rejected(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000009")
        await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        with pytest.raises(SubtypeDetailsMismatchError):
            await service.update_basic_info(
                user.id, fields={"freelancer_details": {"years_experience": 10}}
            )

    @pytest.mark.anyio
    async def test_editing_the_correct_subtype_details_succeeds(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "507000010")
        provider = await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        await service.update_basic_info(
            user.id, fields={"business_details": {"city": "Abu Dhabi"}}
        )

        business_profile = await BusinessProfileRepository(
            db_session
        ).get_by_provider_id(provider.id)
        assert business_profile.city == "Abu Dhabi"


class TestImmutabilityAndVerificationBoundary:
    @pytest.mark.anyio
    async def test_provider_type_is_never_accepted_as_an_update_field(
        self, db_session
    ) -> None:
        """`provider_type` is not in the allowed basic-field set at all
        -- passing it through has no effect (still immutable)."""
        user = await _create_user(db_session, "507000011")
        provider = await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        updated = await service.update_basic_info(
            user.id,
            fields={"provider_type": "freelancer", "display_name": "New Name"},
        )

        assert updated.provider_type == ProviderType.BUSINESS
        assert provider.id == updated.id

    @pytest.mark.anyio
    async def test_never_touches_verification_status_or_is_discoverable(
        self, db_session
    ) -> None:
        """AC6: editing basic info/hours/portfolio never requires
        re-verification -- because nothing in this surface can touch
        these fields at all."""
        user = await _create_user(db_session, "507000012")
        await _create_business_provider(db_session, user)
        service = _provider_service(db_session)

        updated = await service.update_basic_info(
            user.id,
            fields={
                "display_name": "New Name",
                "business_details": {"delivery_radius_meters": 9000},
                "category_labels": [{"label": "Plumbing", "is_primary": True}],
            },
        )

        assert updated.verification_status == VerificationStatus.PENDING
        assert updated.is_discoverable is False
