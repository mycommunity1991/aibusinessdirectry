"""Dependency-injection providers for the Provider module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.modules.administration.dependencies import get_claim_review_request_service
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewRequestService,
)
from app.modules.identity.dependencies import (
    get_otp_service,
    get_role_assignment_service,
)
from app.modules.identity.services.otp_service import OtpService
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
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
from app.modules.provider.repositories.provider_availability_repository import (
    ProviderAvailabilityRepository,
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
from app.modules.provider.services.admin_claim_service import AdminClaimService
from app.modules.provider.services.availability_service import AvailabilityService
from app.modules.provider.services.claim_service import ClaimService
from app.modules.provider.services.portfolio_service import PortfolioService
from app.modules.provider.services.provider_service import ProviderService
from app.shared.storage.interfaces import FileStorage
from app.shared.storage.local_file_storage import LocalFileStorage


def get_provider_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRepository:
    """Provides a `ProviderRepository` bound to the request-scoped DB session."""
    return ProviderRepository(db)


def get_business_profile_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessProfileRepository:
    """Provides a `BusinessProfileRepository` bound to the request-scoped
    DB session."""
    return BusinessProfileRepository(db)


def get_freelancer_profile_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FreelancerProfileRepository:
    """Provides a `FreelancerProfileRepository` bound to the
    request-scoped DB session."""
    return FreelancerProfileRepository(db)


def get_portfolio_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PortfolioRepository:
    """Provides a `PortfolioRepository` bound to the request-scoped DB
    session."""
    return PortfolioRepository(db)


def get_provider_availability_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderAvailabilityRepository:
    """Provides a `ProviderAvailabilityRepository` bound to the
    request-scoped DB session."""
    return ProviderAvailabilityRepository(db)


def get_provider_category_label_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderCategoryLabelRepository:
    """Provides a `ProviderCategoryLabelRepository` bound to the
    request-scoped DB session."""
    return ProviderCategoryLabelRepository(db)


def get_service_area_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceAreaRepository:
    """Provides a `ServiceAreaRepository` bound to the request-scoped DB
    session."""
    return ServiceAreaRepository(db)


def get_provider_search_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderSearchRepository:
    """Provides a `ProviderSearchRepository` bound to the request-scoped
    DB session (DIR-001, Decision 4, `Plan_S06_DIR-001.md`)."""
    return ProviderSearchRepository(db)


def get_file_storage() -> FileStorage:
    """
    Provides the `FileStorage` implementation (PRO-002, Decision 2,
    `Plan_S04_PRO-002.md`) -- `LocalFileStorage` today, reading
    `UPLOAD_DIR` from settings. `PortfolioService` depends on the
    `FileStorage` protocol, never on `LocalFileStorage` directly, so a
    future `S3FileStorage` needs only a change here.
    """
    return LocalFileStorage(base_directory=settings.UPLOAD_DIR)


def get_provider_service(
    provider_repository: Annotated[
        ProviderRepository, Depends(get_provider_repository)
    ],
    business_profile_repository: Annotated[
        BusinessProfileRepository, Depends(get_business_profile_repository)
    ],
    freelancer_profile_repository: Annotated[
        FreelancerProfileRepository, Depends(get_freelancer_profile_repository)
    ],
    provider_category_label_repository: Annotated[
        ProviderCategoryLabelRepository, Depends(get_provider_category_label_repository)
    ],
    service_area_repository: Annotated[
        ServiceAreaRepository, Depends(get_service_area_repository)
    ],
    role_assignment_service: Annotated[
        RoleAssignmentService, Depends(get_role_assignment_service)
    ],
    provider_search_repository: Annotated[
        ProviderSearchRepository, Depends(get_provider_search_repository)
    ],
    portfolio_repository: Annotated[
        PortfolioRepository, Depends(get_portfolio_repository)
    ],
) -> ProviderService:
    """
    Provides a `ProviderService` bound to the request-scoped DB session.

    Imports `get_role_assignment_service` from
    `app.modules.identity.dependencies` (Decision 1,
    `Plan_S04_PRO-001.md`) -- the exact same shape
    `identity/dependencies.py`'s `get_auth_service` imports
    `customer/dependencies.py`'s `get_customer_service`, just reversed.
    """
    return ProviderService(
        provider_repository=provider_repository,
        business_profile_repository=business_profile_repository,
        freelancer_profile_repository=freelancer_profile_repository,
        provider_category_label_repository=provider_category_label_repository,
        service_area_repository=service_area_repository,
        role_assignment_service=role_assignment_service,
        provider_search_repository=provider_search_repository,
        portfolio_repository=portfolio_repository,
    )


def get_portfolio_service(
    portfolio_repository: Annotated[
        PortfolioRepository, Depends(get_portfolio_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
) -> PortfolioService:
    """Provides a `PortfolioService` bound to the request-scoped DB session."""
    return PortfolioService(
        portfolio_repository=portfolio_repository,
        provider_service=provider_service,
        file_storage=file_storage,
    )


def get_availability_service(
    provider_availability_repository: Annotated[
        ProviderAvailabilityRepository, Depends(get_provider_availability_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> AvailabilityService:
    """Provides an `AvailabilityService` bound to the request-scoped DB
    session."""
    return AvailabilityService(
        provider_availability_repository=provider_availability_repository,
        provider_service=provider_service,
    )


def get_claim_service(
    provider_repository: Annotated[
        ProviderRepository, Depends(get_provider_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    otp_service: Annotated[OtpService, Depends(get_otp_service)],
    role_assignment_service: Annotated[
        RoleAssignmentService, Depends(get_role_assignment_service)
    ],
    claim_review_request_service: Annotated[
        ClaimReviewRequestService, Depends(get_claim_review_request_service)
    ],
) -> ClaimService:
    """
    Provides a `ClaimService` bound to the request-scoped DB session
    (CLM-001, Decision 7, `Plan_S06_CLM-001.md`).

    Imports `get_otp_service`/`get_role_assignment_service` from
    `identity/dependencies.py` (the same `provider -> identity` shape
    ADR-016 already established) and `get_claim_review_request_service`
    from `administration/dependencies.py` (the same `X ->
    administration` shape VER-002's `get_admin_verification_service`
    already established via `get_admin_action_log_service`).
    """
    return ClaimService(
        provider_repository=provider_repository,
        provider_service=provider_service,
        otp_service=otp_service,
        role_assignment_service=role_assignment_service,
        claim_review_request_service=claim_review_request_service,
    )


def get_admin_claim_service(
    claim_review_request_service: Annotated[
        ClaimReviewRequestService, Depends(get_claim_review_request_service)
    ],
    claim_service: Annotated[ClaimService, Depends(get_claim_service)],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> AdminClaimService:
    """Provides an `AdminClaimService` bound to the request-scoped DB
    session (CLM-001, Decision 9, `Plan_S06_CLM-001.md`)."""
    return AdminClaimService(
        claim_review_request_service=claim_review_request_service,
        claim_service=claim_service,
        provider_service=provider_service,
    )
