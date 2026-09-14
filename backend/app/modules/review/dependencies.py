"""
Dependency-injection providers for the Review module.

Cross-module edges, each justified explicitly (per ADR-047's stated
expectation, mirroring `contact/dependencies.py`'s own docstring for the
identical shape):

- `contact.ContactViewRepository`/`contact.OutcomeTagRepository` (raw,
  not via a service) -- neither `ContactService` nor `OutcomeTagService`
  exposes an equivalent raw-lookup primitive this module needs
  (`get_by_id`/`get_by_contact_view_id`); the exact same justification
  `ContactService`/`OutcomeTagService` themselves already rely on for
  these same two repositories.
- `customer.CustomerProfileRepository` (raw) -- same precedent
  (`ContactService`/`OutcomeTagService` both use it raw; no
  `CustomerService.get_by_user_id`-equivalent exists).
- `provider.ProviderService` (service-only edge, per ADR-047's "modules
  communicate through services only" rule) -- for the two new lock/apply
  methods (`lock_for_rating_recalculation`/`apply_rating_recalculation`),
  never `ProviderRepository` directly.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.contact.dependencies import (
    get_contact_view_repository,
    get_outcome_tag_repository,
)
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.customer.dependencies import get_customer_profile_repository
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.services.provider_service import ProviderService
from app.modules.review.repositories.provider_rating_summary_repository import (
    ProviderRatingSummaryRepository,
)
from app.modules.review.repositories.review_repository import ReviewRepository
from app.modules.review.services.review_service import ReviewService


def get_review_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewRepository:
    """Provides a `ReviewRepository` bound to the request-scoped DB
    session."""
    return ReviewRepository(db)


def get_provider_rating_summary_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRatingSummaryRepository:
    """Provides a `ProviderRatingSummaryRepository` bound to the
    request-scoped DB session."""
    return ProviderRatingSummaryRepository(db)


def get_review_service(
    review_repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    provider_rating_summary_repository: Annotated[
        ProviderRatingSummaryRepository,
        Depends(get_provider_rating_summary_repository),
    ],
    contact_view_repository: Annotated[
        ContactViewRepository, Depends(get_contact_view_repository)
    ],
    outcome_tag_repository: Annotated[
        OutcomeTagRepository, Depends(get_outcome_tag_repository)
    ],
    customer_profile_repository: Annotated[
        CustomerProfileRepository, Depends(get_customer_profile_repository)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ReviewService:
    """
    Provides a `ReviewService` bound to the request-scoped DB session
    (REV-002, Decision 1, `Plan_S09_REV-002.md`).
    """
    return ReviewService(
        review_repository=review_repository,
        provider_rating_summary_repository=provider_rating_summary_repository,
        contact_view_repository=contact_view_repository,
        outcome_tag_repository=outcome_tag_repository,
        customer_profile_repository=customer_profile_repository,
        provider_service=provider_service,
    )
