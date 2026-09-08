from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.exceptions import ProviderNotFoundError
from app.database.session import get_db
from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.models import BusinessProfile, FreelancerProfile, Provider
from app.modules.provider.schemas import (
    BusinessProfileResponse,
    CreateProviderRequest,
    FreelancerProfileResponse,
    ProviderResponse,
)
from app.modules.provider.services.provider_service import ProviderService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Provider"])


def _to_business_profile_response(
    profile: BusinessProfile,
) -> BusinessProfileResponse:
    return BusinessProfileResponse(
        address_line=profile.address_line,
        city=profile.city,
        region=profile.region,
        latitude=profile.latitude,
        longitude=profile.longitude,
        operating_hours=profile.operating_hours,
        delivery_radius_meters=profile.delivery_radius_meters,
        trade_license_number=profile.trade_license_number,
    )


def _to_freelancer_profile_response(
    profile: FreelancerProfile,
) -> FreelancerProfileResponse:
    return FreelancerProfileResponse(
        base_latitude=profile.base_latitude,
        base_longitude=profile.base_longitude,
        service_radius_meters=profile.service_radius_meters,
        skills=profile.skills,
        years_experience=profile.years_experience,
    )


async def _to_response(
    provider_service: ProviderService, provider: Provider
) -> ProviderResponse:
    business_profile, freelancer_profile = await provider_service.get_subtype_profiles(
        provider
    )
    return ProviderResponse(
        id=provider.id,
        provider_type=provider.provider_type,
        display_name=provider.display_name,
        phone_country_code=provider.phone_country_code,
        phone_number=provider.phone_number,
        whatsapp_number=provider.whatsapp_number,
        category_label=provider.category_label,
        description=provider.description,
        slug=provider.slug,
        verification_status=provider.verification_status,
        is_discoverable=provider.is_discoverable,
        country_code=provider.country_code,
        business_profile=(
            _to_business_profile_response(business_profile)
            if business_profile is not None
            else None
        ),
        freelancer_profile=(
            _to_freelancer_profile_response(freelancer_profile)
            if freelancer_profile is not None
            else None
        ),
    )


@router.get(
    "/me",
    response_model=SuccessResponse[ProviderResponse],
    responses={
        200: {
            "model": SuccessResponse[ProviderResponse],
            "description": "The caller's own provider listing.",
        },
        401: {"description": "Authentication required."},
        404: {
            "description": "The caller has not created a provider listing yet.",
        },
    },
    summary="Get My Provider Listing",
    description=(
        "Returns the authenticated caller's own provider listing (Decision "
        "9, `Plan_S04_PRO-001.md`), or a 404 if none exists yet -- so a "
        "caller who already has a listing can be told so gracefully "
        "before re-entering the onboarding wizard (AC8). Resolved "
        "exclusively from the caller's own `user_id` -- there is no "
        "`{id}`-addressable route. Bare authentication only (not "
        "`require_role(ROLE_CUSTOMER)`): becoming a Provider is not "
        "gated on already holding another role."
    ),
)
async def get_my_provider(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    provider_service: ProviderService = Depends(get_provider_service),  # noqa: B008
) -> SuccessResponse[ProviderResponse]:
    """Return the caller's own provider listing, or 404 if none exists yet."""
    provider = await provider_service.get_my_provider(current_user.id)
    if provider is None:
        raise ProviderNotFoundError()

    response_data = await _to_response(provider_service, provider)
    await db.commit()
    return SuccessResponse[ProviderResponse](
        success=True,
        message="Provider retrieved.",
        data=response_data,
    )


@router.post(
    "/me",
    response_model=SuccessResponse[ProviderResponse],
    status_code=201,
    responses={
        201: {
            "model": SuccessResponse[ProviderResponse],
            "description": "The provider listing was created.",
        },
        401: {"description": "Authentication required."},
        409: {
            "description": (
                "The caller already has a provider listing -- one "
                "Provider per Account, and `provider_type` is immutable "
                "(AC8/AC10)."
            ),
        },
        422: {
            "description": (
                "`business_details`/`freelancer_details` is missing, "
                "extra, or mismatched with `provider_type`."
            ),
        },
    },
    summary="Create My Provider Listing",
    description=(
        "Creates a new provider listing for the authenticated caller "
        "(AC1/AC2), linked to the caller's own existing Account -- no "
        "new registration/OTP/OAuth step is triggered. Captures type "
        "(immutable, AC3), basic info (AC4), and subtype-specific "
        "details (AC5/AC6) in a single submission (Decision 2, "
        "`Plan_S04_PRO-001.md`). Defaults to "
        "`verification_status=pending`/`is_discoverable=false` "
        "unconditionally (AC7) and grants `ROLE_PROVIDER` to the "
        "caller's Account. A caller may create at most one Provider "
        "(AC8) -- a second call, with any `provider_type`, is rejected "
        "(AC10)."
    ),
)
async def create_my_provider(
    payload: CreateProviderRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    provider_service: ProviderService = Depends(get_provider_service),  # noqa: B008
) -> SuccessResponse[ProviderResponse]:
    """Create a new provider listing for the caller."""
    provider = await provider_service.create_provider(current_user.id, payload=payload)
    response_data = await _to_response(provider_service, provider)
    await db.commit()
    return SuccessResponse[ProviderResponse](
        success=True,
        message="Provider created.",
        data=response_data,
    )
