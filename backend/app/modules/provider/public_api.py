"""
Customer-facing Provider Profile endpoint (CON-001, Decision 2,
`Plan_S08_CON-001.md`) -- mounted as a *second* router at the
`/providers` prefix, registered in `app/api/v1/api.py` **after** the
existing owner-only `provider_router` (`provider/api.py`) so `/me`,
`/me/portfolio`, `/me/availability` continue to match their literal
paths before this new `/{provider_id}` path-parameter route is ever
reached (Starlette matches routes in registration order).

`require_role(ROLE_CUSTOMER)` gates the route -- viewing a matched
provider's profile is a Customer-initiated action, mirroring
`claim_api.py`'s identical reasoning: every registered Account already
holds `ROLE_CUSTOMER`, so this imposes no extra friction.

Reuses `_format_hour`/`_to_availability_response`/
`_to_category_label_response` from `provider/api.py` rather than
duplicating them -- both routers build the exact same response shapes
for these fields.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.provider.api import (
    _to_availability_response,
    _to_category_label_response,
)
from app.modules.provider.dependencies import (
    get_availability_service,
    get_provider_service,
)
from app.modules.provider.models import BusinessProfile, FreelancerProfile, Provider
from app.modules.provider.schemas import PublicProviderProfileResponse
from app.modules.provider.services.availability_service import AvailabilityService
from app.modules.provider.services.provider_service import ProviderService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Provider"])


async def _to_public_profile_response(
    provider_service: ProviderService,
    availability_service: AvailabilityService,
    provider: Provider,
) -> PublicProviderProfileResponse:
    business_profile, freelancer_profile = await provider_service.get_subtype_profiles(
        provider
    )
    category_labels = await provider_service.get_category_labels(provider.id)
    photo_urls_by_id = await provider_service.get_primary_photo_urls([provider.id])
    availability = await availability_service.get_availability_for_provider(provider.id)

    return PublicProviderProfileResponse(
        id=provider.id,
        provider_type=provider.provider_type,
        display_name=provider.display_name,
        category_labels=[
            _to_category_label_response(label) for label in category_labels
        ],
        description=provider.description,
        primary_photo_url=photo_urls_by_id.get(provider.id),
        average_rating=provider.average_rating,
        review_count=provider.review_count,
        is_claimed=provider.is_claimed,
        verification_status=provider.verification_status,
        weekly_availability=[
            _to_availability_response(entry) for entry in availability
        ],
        city=(
            business_profile.city
            if isinstance(business_profile, BusinessProfile)
            else None
        ),
        region=(
            business_profile.region
            if isinstance(business_profile, BusinessProfile)
            else None
        ),
        delivery_radius_meters=(
            business_profile.delivery_radius_meters
            if isinstance(business_profile, BusinessProfile)
            else None
        ),
        service_radius_meters=(
            freelancer_profile.service_radius_meters
            if isinstance(freelancer_profile, FreelancerProfile)
            else None
        ),
    )


@router.get(
    "/{provider_id}",
    response_model=SuccessResponse[PublicProviderProfileResponse],
    responses={
        200: {
            "model": SuccessResponse[PublicProviderProfileResponse],
            "description": "The provider's public profile.",
        },
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the customer role."},
        404: {"description": "The provider doesn't exist (or is soft-deleted)."},
    },
    summary="Get A Provider's Public Profile",
    description=(
        "The Provider Profile screen's data (CON-001, AC5): name, "
        "category, description, primary photo, rating together with "
        "review count (never alone), weekly hours, and a subtype-"
        "specific service-area field. Does **not** require "
        "`is_discoverable=true` (Decision 7, `Plan_S08_CON-001.md`) -- "
        "only that the listing exist and be active. Deliberately "
        "excludes the phone/WhatsApp numbers -- those are only ever "
        "revealed via `POST /contact-views` (AC2)."
    ),
)
async def get_provider_public_profile(
    provider_id: uuid.UUID,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    provider_service: ProviderService = Depends(get_provider_service),  # noqa: B008
    availability_service: AvailabilityService = Depends(  # noqa: B008
        get_availability_service
    ),
) -> SuccessResponse[PublicProviderProfileResponse]:
    """Return a provider's public, customer-facing profile."""
    provider = await provider_service.get_for_public_profile(provider_id)
    response_data = await _to_public_profile_response(
        provider_service, availability_service, provider
    )
    await db.commit()
    return SuccessResponse[PublicProviderProfileResponse](
        success=True,
        message="Provider profile retrieved.",
        data=response_data,
    )
