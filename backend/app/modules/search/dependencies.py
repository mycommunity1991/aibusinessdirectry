"""Dependency-injection providers for the Search module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.administration.dependencies import (
    get_manual_match_assignment_service,
)
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
from app.modules.customer.dependencies import (
    get_customer_service,
    get_saved_address_service,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.customer.services.saved_address_service import SavedAddressService
from app.modules.provider.dependencies import get_provider_service
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


def get_search_service(
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> SearchService:
    """
    Provides a `SearchService` bound to the request-scoped DB session.

    Imports `get_provider_service` from `app.modules.provider.
    dependencies` (DIR-001, Decision 4, `Plan_S06_DIR-001.md`) -- the
    same one-directional cross-module shape ADR-014/ADR-016/VER-001
    Decision 9/VER-002 Decision 7 already established.
    """
    return SearchService(provider_service=provider_service)


def get_search_request_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchRequestRepository:
    """Provides a `SearchRequestRepository` bound to the request-scoped
    DB session (AI-002, `Plan_S07_AI-002.md`)."""
    return SearchRequestRepository(db)


def get_provider_match_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderMatchRepository:
    """Provides a `ProviderMatchRepository` bound to the request-scoped
    DB session (AI-002)."""
    return ProviderMatchRepository(db)


def get_search_event_log_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchEventLogRepository:
    """Provides a `SearchEventLogRepository` bound to the request-scoped
    DB session (AI-002)."""
    return SearchEventLogRepository(db)


def get_search_request_service(
    search_request_repository: Annotated[
        SearchRequestRepository, Depends(get_search_request_repository)
    ],
    provider_match_repository: Annotated[
        ProviderMatchRepository, Depends(get_provider_match_repository)
    ],
    search_event_log_repository: Annotated[
        SearchEventLogRepository, Depends(get_search_event_log_repository)
    ],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    saved_address_service: Annotated[
        SavedAddressService, Depends(get_saved_address_service)
    ],
    manual_match_assignment_service: Annotated[
        ManualMatchAssignmentService, Depends(get_manual_match_assignment_service)
    ],
    customer_service: Annotated[CustomerService, Depends(get_customer_service)],
) -> SearchRequestService:
    """
    Provides a `SearchRequestService` bound to the request-scoped DB
    session (AI-002, Decision 1) -- wires in `customer.
    SavedAddressService`/`CustomerService` (`search -> customer`) and
    `administration.ManualMatchAssignmentService` (`search ->
    administration`) as cross-module, constructor-injected dependencies,
    alongside the already-shipped `SearchService`/`ProviderService`
    (`search -> provider`, DIR-001, reused unchanged -- Decision 5).
    """
    return SearchRequestService(
        search_request_repository=search_request_repository,
        provider_match_repository=provider_match_repository,
        search_event_log_repository=search_event_log_repository,
        search_service=search_service,
        provider_service=provider_service,
        saved_address_service=saved_address_service,
        manual_match_assignment_service=manual_match_assignment_service,
        customer_service=customer_service,
    )
