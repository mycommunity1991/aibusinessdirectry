"""
Shared test helpers for the `review` module's REV-002 test files
(`test_review_service.py`, `test_review_api.py`) -- mirrors
`tests/modules/contact/_helpers.py`'s identical "build the real thing,
no mocks" approach.
"""

import uuid

from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.contact.services.contact_service import ContactService
from app.modules.contact.services.outcome_tag_service import OutcomeTagService
from app.modules.customer.models import CustomerProfile, NotificationChannel
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.notification.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.modules.notification.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.modules.notification.services.notification_preference_service import (
    NotificationPreferenceService,
)
from app.modules.notification.services.notification_sender import (
    StubEmailSender,
    StubSmsSender,
    StubWhatsAppSender,
)
from app.modules.notification.services.notification_service import NotificationService
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
from app.modules.review.repositories.provider_rating_summary_repository import (
    ProviderRatingSummaryRepository,
)
from app.modules.review.repositories.review_repository import ReviewRepository
from app.modules.review.services.review_service import ReviewService
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)


def make_provider_service(db_session) -> ProviderService:
    """Mirrors `tests/modules/contact/_helpers.py`'s identical
    `make_provider_service` -- the real thing, no mocks."""
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


def make_notification_service(db_session) -> NotificationService:
    """
    Builds a real, fully-wired `NotificationService` (`ENG-001`,
    `Plan_S12_ENG-001.md`) -- the real preference/delivery pipeline,
    backed only by stub senders (no real vendor exists). Mirrors
    `tests/modules/contact/_helpers.py`'s identical builder.
    """
    return NotificationService(
        repository=NotificationRepository(db_session),
        preference_service=NotificationPreferenceService(
            NotificationPreferenceRepository(db_session),
            CustomerProfileRepository(db_session),
            CustomerPreferencesRepository(db_session),
        ),
        delivery_service=NotificationDeliveryService(
            NotificationDeliveryRepository(db_session),
            {
                NotificationChannel.WHATSAPP: StubWhatsAppSender(),
                NotificationChannel.SMS: StubSmsSender(),
                NotificationChannel.EMAIL: StubEmailSender(),
            },
        ),
        role_repository=RoleRepository(db_session),
    )


def make_contact_service(db_session) -> ContactService:
    return ContactService(
        contact_view_repository=ContactViewRepository(db_session),
        customer_profile_repository=CustomerProfileRepository(db_session),
        provider_service=make_provider_service(db_session),
        search_request_repository=SearchRequestRepository(db_session),
        notification_service=make_notification_service(db_session),
    )


def make_outcome_tag_service(db_session) -> OutcomeTagService:
    return OutcomeTagService(
        outcome_tag_repository=OutcomeTagRepository(db_session),
        contact_view_repository=ContactViewRepository(db_session),
        customer_profile_repository=CustomerProfileRepository(db_session),
    )


def make_review_service(db_session) -> ReviewService:
    return ReviewService(
        review_repository=ReviewRepository(db_session),
        provider_rating_summary_repository=ProviderRatingSummaryRepository(db_session),
        contact_view_repository=ContactViewRepository(db_session),
        outcome_tag_repository=OutcomeTagRepository(db_session),
        customer_profile_repository=CustomerProfileRepository(db_session),
        provider_service=make_provider_service(db_session),
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


async def create_provider(
    db_session, *, user: User | None, **overrides: object
) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id if user is not None else None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Al Noor Plumbing Services LLC",
        "slug": f"al-noor-plumbing-{uuid.uuid4().hex[:8]}",
        "phone_country_code": "+971",
        "phone_number": "43334455",
        "whatsapp_number": "43334455",
        "listing_source": (
            ListingSource.SELF_REGISTERED
            if user is not None
            else ListingSource.GOOGLE_SEEDED_UNCLAIMED
        ),
        "is_claimed": user is not None,
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


async def create_contact_view(
    db_session, *, customer_user_id: uuid.UUID, provider_id: uuid.UUID
) -> ContactView:
    contact_service = make_contact_service(db_session)
    contact_view, _provider = await contact_service.create_contact_view(
        customer_user_id, provider_id=provider_id, search_request_id=None
    )
    await db_session.commit()
    return contact_view


async def create_hired_contact_view(
    db_session, *, customer_user_id: uuid.UUID, provider_id: uuid.UUID
) -> ContactView:
    """A Contact View with a `hired=true` Outcome Tag already submitted
    -- the anchor state AC2 requires for a Review to be submittable."""
    contact_view = await create_contact_view(
        db_session, customer_user_id=customer_user_id, provider_id=provider_id
    )
    outcome_tag_service = make_outcome_tag_service(db_session)
    await outcome_tag_service.submit_outcome_tag(
        customer_user_id, contact_view_id=contact_view.id, hired=True
    )
    await db_session.commit()
    return contact_view
