"""Dependency-injection providers for the Contact module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.category.dependencies import get_category_repository
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.contact.services.contact_service import ContactService
from app.modules.contact.services.lead_service import LeadService
from app.modules.contact.services.outcome_tag_service import OutcomeTagService
from app.modules.contact.services.visibility_analytics_service import (
    VisibilityAnalyticsService,
)
from app.modules.customer.dependencies import get_customer_profile_repository
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.notification.dependencies import get_notification_service
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.dependencies import (
    get_provider_match_repository,
    get_search_request_repository,
)
from app.modules.search.repositories.provider_match_repository import (
    ProviderMatchRepository,
)
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


def get_outcome_tag_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OutcomeTagRepository:
    """Provides an `OutcomeTagRepository` bound to the request-scoped DB
    session."""
    return OutcomeTagRepository(db)


def get_outcome_tag_service(
    outcome_tag_repository: Annotated[
        OutcomeTagRepository, Depends(get_outcome_tag_repository)
    ],
    contact_view_repository: Annotated[
        ContactViewRepository, Depends(get_contact_view_repository)
    ],
    customer_profile_repository: Annotated[
        CustomerProfileRepository, Depends(get_customer_profile_repository)
    ],
) -> OutcomeTagService:
    """
    Provides an `OutcomeTagService` bound to the request-scoped DB
    session (REV-001, Decision 1, `Plan_S09_REV-001.md`) -- wires in
    the existing `ContactViewRepository`/`CustomerProfileRepository`,
    the same two raw-repository edges CON-001's `ContactService`
    already uses. No `NotificationService` dependency here -- the
    outcome-tag-prompt notification is emitted at Contact View creation
    time (Decision 5), not at outcome-tag submission time.
    """
    return OutcomeTagService(
        outcome_tag_repository=outcome_tag_repository,
        contact_view_repository=contact_view_repository,
        customer_profile_repository=customer_profile_repository,
    )


def get_lead_service(
    contact_view_repository: Annotated[
        ContactViewRepository, Depends(get_contact_view_repository)
    ],
    outcome_tag_repository: Annotated[
        OutcomeTagRepository, Depends(get_outcome_tag_repository)
    ],
    search_request_repository: Annotated[
        SearchRequestRepository, Depends(get_search_request_repository)
    ],
    category_repository: Annotated[
        CategoryRepository, Depends(get_category_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> LeadService:
    """
    Provides a `LeadService` bound to the request-scoped DB session
    (LEAD-001, Decision 1, `Plan_S10_LEAD-001.md`) -- wires in the
    module's existing `ContactViewRepository`/`OutcomeTagRepository`
    providers, plus `search.SearchRequestRepository` and `provider.
    ProviderService` (both already existing cross-module edges via
    `ContactService`), and a new `category.CategoryRepository` edge.

    `search.SearchRequestRepository` and `category.CategoryRepository`
    are raw Repository dependencies, not Services, per ADR-047's
    exception -- neither `SearchRequestService` nor `CategoryService`
    exposes a batch-by-ids read primitive today.
    """
    return LeadService(
        contact_view_repository=contact_view_repository,
        outcome_tag_repository=outcome_tag_repository,
        search_request_repository=search_request_repository,
        category_repository=category_repository,
        provider_service=provider_service,
    )


def get_visibility_analytics_service(
    contact_view_repository: Annotated[
        ContactViewRepository, Depends(get_contact_view_repository)
    ],
    provider_match_repository: Annotated[
        ProviderMatchRepository, Depends(get_provider_match_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> VisibilityAnalyticsService:
    """
    Provides a `VisibilityAnalyticsService` bound to the request-scoped
    DB session (LEAD-002, Decision 1, `Plan_S10_LEAD-002.md`) -- wires
    in the module's existing `ContactViewRepository` provider, plus
    `provider.ProviderService` (already an existing cross-module edge
    via `ContactService`/`LeadService`), and a new `search.
    ProviderMatchRepository` edge.

    `search.ProviderMatchRepository` is a raw Repository dependency,
    not a Service, per ADR-047's exception -- **the second instance of
    this exception recorded for the `contact` module**, alongside the
    existing `search.SearchRequestRepository`/`category.
    CategoryRepository` edges (`get_lead_service`, LEAD-001): no
    `search`-module Service exposes a per-provider aggregation
    primitive today, so there is no equivalent Service method to depend
    on instead.
    """
    return VisibilityAnalyticsService(
        contact_view_repository=contact_view_repository,
        provider_match_repository=provider_match_repository,
        provider_service=provider_service,
    )
