"""Dependency-injection providers for the Contact module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.services.contact_service import ContactService
from app.modules.customer.dependencies import get_customer_profile_repository
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.notification.dependencies import get_notification_service
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.dependencies import get_search_request_repository
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)


def get_contact_view_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactViewRepository:
    """Provides a `ContactViewRepository` bound to the request-scoped DB
    session."""
    return ContactViewRepository(db)


def get_contact_service(
    contact_view_repository: Annotated[
        ContactViewRepository, Depends(get_contact_view_repository)
    ],
    customer_profile_repository: Annotated[
        CustomerProfileRepository, Depends(get_customer_profile_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    search_request_repository: Annotated[
        SearchRequestRepository, Depends(get_search_request_repository)
    ],
    notification_service: Annotated[
        NotificationService, Depends(get_notification_service)
    ],
) -> ContactService:
    """
    Provides a `ContactService` bound to the request-scoped DB session
    (CON-001, Decision 1, `Plan_S08_CON-001.md`) -- wires in `customer.
    CustomerProfileRepository`, `provider.ProviderService`, `search.
    SearchRequestRepository`, and `notification.NotificationService` as
    cross-module, constructor-injected dependencies. The `provider` edge
    is `ProviderService`, never `ProviderRepository` directly, per
    `02_ARCHITECTURE.md`'s "modules communicate through services only"
    rule -- unlike the `customer`/`search` edges here, which remain raw
    Repositories today because neither `CustomerService` nor an
    equivalent `SearchRequestService` exposes a matching raw-lookup
    primitive this module needs.
    """
    return ContactService(
        contact_view_repository=contact_view_repository,
        customer_profile_repository=customer_profile_repository,
        provider_service=provider_service,
        search_request_repository=search_request_repository,
        notification_service=notification_service,
    )
