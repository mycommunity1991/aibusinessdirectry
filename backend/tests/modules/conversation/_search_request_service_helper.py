"""
Shared test helper: builds a real, fully-wired `SearchRequestService`
(AI-002, `Plan_S07_AI-002.md`) for `conversation` module tests that
construct `ConversationService` directly (mirrors this test package's
existing `_make_service`/`_seed_category` duplication-across-files
convention).

`ConversationService` gained a required `search_request_service`
constructor dependency in AI-002 (Decision 1); every AI-001 test file
that builds a `ConversationService` by hand now needs one of these.
Building the *real* service (not a mock) keeps these AI-001 tests
genuinely proving no regression: `_apply_completion_policy`'s new
`search_request_service.handle_session_completed(...)` call site
actually runs, against the same real Postgres database, on every
`completed`/`routed_to_admin` transition these tests already exercise.
"""

from app.modules.administration.repositories.manual_match_assignment_repository import (
    ManualMatchAssignmentRepository,
)
from app.modules.administration.services.manual_match_assignment_service import (
    ManualMatchAssignmentService,
)
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


def _make_provider_service(db_session) -> ProviderService:
    from app.modules.identity.repositories.role_repository import RoleRepository
    from app.modules.identity.services.role_assignment_service import (
        RoleAssignmentService,
    )

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
    """Builds a real `SearchRequestService`, fully wired against the
    given (real Postgres) `db_session` -- every dependency is the real
    implementation, mirroring this codebase's established real-DB
    integration-test philosophy (no mocks)."""
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
    provider_service = _make_provider_service(db_session)
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
