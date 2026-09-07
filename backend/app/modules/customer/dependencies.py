"""Dependency-injection providers for the Customer module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
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


def get_customer_profile_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomerProfileRepository:
    """Provides a `CustomerProfileRepository` bound to the request-scoped DB session."""
    return CustomerProfileRepository(db)


def get_customer_preferences_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomerPreferencesRepository:
    """Provides a `CustomerPreferencesRepository` bound to the
    request-scoped DB session."""
    return CustomerPreferencesRepository(db)


def get_customer_service(
    profile_repository: Annotated[
        CustomerProfileRepository, Depends(get_customer_profile_repository)
    ],
    preferences_repository: Annotated[
        CustomerPreferencesRepository, Depends(get_customer_preferences_repository)
    ],
) -> CustomerService:
    """Provides a `CustomerService` bound to the request-scoped DB session."""
    return CustomerService(
        profile_repository=profile_repository,
        preferences_repository=preferences_repository,
    )


def get_saved_address_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SavedAddressRepository:
    """Provides a `SavedAddressRepository` bound to the request-scoped
    DB session."""
    return SavedAddressRepository(db)


def get_saved_address_service(
    saved_address_repository: Annotated[
        SavedAddressRepository, Depends(get_saved_address_repository)
    ],
    customer_service: Annotated[CustomerService, Depends(get_customer_service)],
) -> SavedAddressService:
    """Provides a `SavedAddressService` bound to the request-scoped DB
    session (Decision 4, `Plan_S03_CUS-002.md`: depends on the
    already-shipped `CustomerService`, not a raw
    `CustomerProfileRepository`)."""
    return SavedAddressService(
        saved_address_repository=saved_address_repository,
        customer_service=customer_service,
    )
