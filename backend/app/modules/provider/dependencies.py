"""Dependency-injection providers for the Provider module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.identity.dependencies import get_role_assignment_service
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.services.provider_service import ProviderService


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
    role_assignment_service: Annotated[
        RoleAssignmentService, Depends(get_role_assignment_service)
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
        role_assignment_service=role_assignment_service,
    )
