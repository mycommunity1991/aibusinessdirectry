"""
Shared test helpers for the `contact` module's CON-001 test files
(`test_contact_service.py`, `test_contact_api.py`) -- mirrors
`tests/modules/search/_helpers.py`'s identical "build the real thing,
no mocks" approach.
"""

import uuid

from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.services.contact_service import ContactService
from app.modules.customer.models import CustomerProfile
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)


def make_contact_service(db_session) -> ContactService:
    return ContactService(
        contact_view_repository=ContactViewRepository(db_session),
        customer_profile_repository=CustomerProfileRepository(db_session),
        provider_repository=ProviderRepository(db_session),
        search_request_repository=SearchRequestRepository(db_session),
        notification_service=NotificationService(NotificationRepository(db_session)),
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
