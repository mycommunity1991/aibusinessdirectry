"""
Shared test helpers for the `search` module's AI-002/MAT-001 test files
(`test_search_request_service.py`, `test_search_request_api.py`) --
mirrors `tests/modules/conversation/_search_request_service_helper.py`'s
identical "build the real thing, no mocks" approach.
"""

import uuid
from decimal import Decimal

from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.category.models import Category
from app.modules.conversation.models import ConversationSession
from app.modules.customer.models import CustomerProfile, SavedAddress
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.customer.repositories.saved_address_repository import (
    SavedAddressRepository,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.customer.services.saved_address_service import SavedAddressService
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderCategoryLabel,
    ProviderType,
    ServiceArea,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.portfolio_repository import PortfolioRepository
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
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)
from app.modules.search.repositories.search_event_log_repository import (
    SearchEventLogRepository,
)
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)
from app.modules.search.services.search_request_service import SearchRequestService
from app.modules.search.services.search_service import SearchService

_DUBAI_LAT = 25.2048
_DUBAI_LNG = 55.2708


def make_provider_service(db_session) -> ProviderService:
    role_assignment_service = RoleAssignmentService(RoleRepository(db_session))
    return ProviderService(
        provider_repository=ProviderRepository(db_session),
        business_profile_repository=BusinessProfileRepository(db_session),
        freelancer_profile_repository=FreelancerProfileRepository(db_session),
        provider_category_label_repository=ProviderCategoryLabelRepository(db_session),
        service_area_repository=ServiceAreaRepository(db_session),
        role_assignment_service=role_assignment_service,
        provider_search_repository=ProviderSearchRepository(db_session),
        portfolio_repository=PortfolioRepository(db_session),
    )


def make_search_request_service(db_session) -> SearchRequestService:
    customer_service = CustomerService(
        CustomerProfileRepository(db_session),
        CustomerPreferencesRepository(db_session),
    )
    saved_address_service = SavedAddressService(
        saved_address_repository=SavedAddressRepository(db_session),
        customer_service=customer_service,
    )
    manual_match_assignment_service = ManualMatchAssignmentService(
        ManualMatchAssignmentRepository(db_session)
    )
    provider_service = make_provider_service(db_session)
    search_service = SearchService(provider_service=provider_service)

    return SearchRequestService(
        search_request_repository=SearchRequestRepository(db_session),
        provider_match_repository=ProviderMatchRepository(db_session),
        search_event_log_repository=SearchEventLogRepository(db_session),
        search_service=search_service,
        provider_service=provider_service,
        saved_address_service=saved_address_service,
        manual_match_assignment_service=manual_match_assignment_service,
        customer_service=customer_service,
    )


async def create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def create_customer_profile(db_session, user: User) -> CustomerProfile:
    profile = CustomerProfile(user_id=user.id, display_name="Test Customer")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def create_default_address(
    db_session,
    customer_id: uuid.UUID,
    *,
    latitude: float = _DUBAI_LAT,
    longitude: float = _DUBAI_LNG,
) -> SavedAddress:
    address = SavedAddress(
        customer_id=customer_id,
        address_line="123 Main St",
        country_code="AE",
        latitude=latitude,
        longitude=longitude,
        is_default=True,
    )
    db_session.add(address)
    await db_session.commit()
    await db_session.refresh(address)
    return address


async def create_conversation_session(
    db_session, customer_id: uuid.UUID, *, category_id: uuid.UUID | None = None
) -> ConversationSession:
    """A real `conversation_sessions` row -- `search_requests.
    conversation_session_id` is a real FK, so a plain `uuid.uuid4()`
    placeholder is not enough."""
    session = ConversationSession(customer_id=customer_id, category_id=category_id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


async def create_category(db_session, *, name: str = "Plumbing") -> Category:
    category = Category(
        name=name,
        name_ar=None,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
        sort_order=0,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


async def create_discoverable_provider(
    db_session,
    *,
    category_label: str = "Plumbing",
    latitude: float = _DUBAI_LAT,
    longitude: float = _DUBAI_LNG,
    radius_meters: int = 20_000,
    display_name: str = "Jane the Plumber",
    average_rating: Decimal | None = None,
    review_count: int = 0,
) -> Provider:
    """
    `average_rating`/`review_count` (MAT-001, Backend Proposed Changes
    item 11, `Plan_S08_MAT-001.md`) let ranking tests construct providers
    with deliberately varied rating/distance combinations -- default to
    the same honest, unrated/`0`-review state every real provider has
    today (no Review domain exists yet).
    """
    owner = await create_user(db_session, f"9{uuid.uuid4().int % 10**8:08d}")
    provider = Provider(
        user_id=owner.id,
        provider_type=ProviderType.FREELANCER,
        display_name=display_name,
        slug=f"{display_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.SELF_REGISTERED,
        is_claimed=True,
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        average_rating=average_rating,
        review_count=review_count,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        ServiceArea(
            provider_id=provider.id,
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=radius_meters,
        )
    )
    db_session.add(
        ProviderCategoryLabel(
            provider_id=provider.id, label=category_label, is_primary=True
        )
    )
    await db_session.commit()
    return provider
