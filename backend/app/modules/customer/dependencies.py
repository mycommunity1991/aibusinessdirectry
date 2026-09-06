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
from app.modules.customer.services.customer_service import CustomerService


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
