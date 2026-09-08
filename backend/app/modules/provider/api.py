import uuid
from datetime import datetime, time

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.exceptions import ProviderNotFoundError
from app.database.session import get_db
from app.modules.provider.dependencies import (
    get_availability_service,
    get_portfolio_service,
    get_provider_service,
)
from app.modules.provider.models import (
    BusinessProfile,
    FreelancerProfile,
    Portfolio,
    Provider,
    ProviderCategoryLabel,
)
from app.modules.provider.schemas import (
    BusinessProfileResponse,
    CategoryLabelResponse,
    CreateProviderRequest,
    FreelancerProfileResponse,
    PortfolioPhotoResponse,
    ProviderResponse,
    ReorderPortfolioRequest,
    UpdateAvailabilityRequest,
    UpdateProviderRequest,
    WeekdayAvailabilityResponse,
)
from app.modules.provider.services.availability_service import (
    AvailabilityService,
    WeekdayAvailabilityEntry,
)
from app.modules.provider.services.portfolio_service import PortfolioService
from app.modules.provider.services.provider_service import ProviderService
from app.shared.schemas.response import CollectionResponse, SuccessResponse

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


def _to_category_label_response(
    label: ProviderCategoryLabel,
) -> CategoryLabelResponse:
    return CategoryLabelResponse(label=label.label, is_primary=label.is_primary)


async def _to_response(
    provider_service: ProviderService, provider: Provider
) -> ProviderResponse:
    business_profile, freelancer_profile = await provider_service.get_subtype_profiles(
        provider
    )
    category_labels = await provider_service.get_category_labels(provider.id)
    return ProviderResponse(
        id=provider.id,
        provider_type=provider.provider_type,
        display_name=provider.display_name,
        phone_country_code=provider.phone_country_code,
        phone_number=provider.phone_number,
        whatsapp_number=provider.whatsapp_number,
        category_labels=[
            _to_category_label_response(label) for label in category_labels
        ],
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


def _to_portfolio_photo_response(photo: Portfolio) -> PortfolioPhotoResponse:
    return PortfolioPhotoResponse(
        id=photo.id,
        media_url=photo.media_url,
        caption=photo.caption,
        sort_order=photo.sort_order,
    )


def _format_hour(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value is not None else None


def _parse_hour(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()  # noqa: DTZ007


def _to_availability_response(
    entry: WeekdayAvailabilityEntry,
) -> WeekdayAvailabilityResponse:
    return WeekdayAvailabilityResponse(
        weekday=entry.weekday,
        is_open=entry.open_time is not None and entry.close_time is not None,
        open_time=_format_hour(entry.open_time),
        close_time=_format_hour(entry.close_time),
        is_emergency_available=entry.is_emergency_available,
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


@router.patch(
    "/me",
    response_model=SuccessResponse[ProviderResponse],
    responses={
        200: {
            "model": SuccessResponse[ProviderResponse],
            "description": "The provider listing was updated.",
        },
        400: {
            "description": (
                "The submitted `business_details`/`freelancer_details` "
                "object does not match the provider's actual `provider_type`."
            ),
        },
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        422: {"description": "Invalid `category_labels` (count/primary rules)."},
    },
    summary="Update My Provider Listing",
    description=(
        "Partially updates the caller's own storefront (PRO-002, AC5): "
        "basic info, category labels, and subtype-specific details -- "
        "only fields present in the request body are applied "
        "(`exclude_unset`). `provider_type` is never accepted (immutable, "
        "PRO-001 Decision 3). Never reads or writes "
        "`verification_status`/`is_discoverable` (AC6). Bare "
        "authentication only (Decision 7, `Plan_S04_PRO-002.md`)."
    ),
)
async def update_my_provider(
    payload: UpdateProviderRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    provider_service: ProviderService = Depends(get_provider_service),  # noqa: B008
) -> SuccessResponse[ProviderResponse]:
    """Partially update the caller's own provider listing."""
    fields = payload.model_dump(exclude_unset=True)
    provider = await provider_service.update_basic_info(current_user.id, fields=fields)
    response_data = await _to_response(provider_service, provider)
    await db.commit()
    return SuccessResponse[ProviderResponse](
        success=True,
        message="Provider updated.",
        data=response_data,
    )


@router.get(
    "/me/portfolio",
    response_model=CollectionResponse[PortfolioPhotoResponse],
    responses={
        200: {"description": "The caller's own active portfolio photos."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
    },
    summary="List My Portfolio Photos",
    description=(
        "Lists the caller's own active portfolio photos, ordered by "
        "`sort_order` (PRO-002, AC2). Deliberately unpaginated (ADR-012) "
        "-- a provider's portfolio is capped at "
        "`MAX_PORTFOLIO_PHOTOS_PER_PROVIDER` photos."
    ),
)
async def list_my_portfolio(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    portfolio_service: PortfolioService = Depends(get_portfolio_service),  # noqa: B008
) -> CollectionResponse[PortfolioPhotoResponse]:
    """List the caller's own active portfolio photos."""
    photos = await portfolio_service.list_my_portfolio(current_user.id)
    response_data = [_to_portfolio_photo_response(photo) for photo in photos]
    await db.commit()
    return CollectionResponse[PortfolioPhotoResponse](
        success=True,
        message="Portfolio retrieved.",
        data=response_data,
        pagination={
            "page": 1,
            "page_size": len(response_data),
            "total_items": len(response_data),
            "total_pages": 1,
        },
    )


@router.post(
    "/me/portfolio",
    response_model=SuccessResponse[PortfolioPhotoResponse],
    status_code=201,
    responses={
        201: {"description": "The photo was uploaded."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        409: {"description": "The caller already has the maximum number of photos."},
        422: {"description": "The uploaded file failed validation."},
    },
    summary="Upload A Portfolio Photo",
    description=(
        "Uploads a new portfolio photo (`multipart/form-data`, one file "
        "+ optional caption, PRO-002, AC2). Validated for size, "
        "extension, and MIME type (including a magic-byte content sniff) "
        "before being stored under a server-generated filename -- the "
        "original client-supplied filename is never trusted or used to "
        "build the stored path (`06_SECURITY.md`)."
    ),
)
async def upload_portfolio_photo(
    file: UploadFile = File(...),  # noqa: B008
    caption: str | None = Form(None),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    portfolio_service: PortfolioService = Depends(get_portfolio_service),  # noqa: B008
) -> SuccessResponse[PortfolioPhotoResponse]:
    """Upload a new portfolio photo for the caller."""
    photo = await portfolio_service.add_photo(
        current_user.id, upload=file, caption=caption
    )
    response_data = _to_portfolio_photo_response(photo)
    await db.commit()
    return SuccessResponse[PortfolioPhotoResponse](
        success=True,
        message="Photo uploaded.",
        data=response_data,
    )


@router.delete(
    "/me/portfolio/{portfolio_id}",
    response_model=SuccessResponse[None],
    responses={
        200: {"description": "The photo was removed."},
        401: {"description": "Authentication required."},
        404: {
            "description": (
                "The photo either doesn't exist or is not owned by the "
                "caller (AC7/AC8) -- both collapse into the same 404."
            ),
        },
    },
    summary="Remove A Portfolio Photo",
    description=(
        "Soft-deletes one of the caller's own portfolio photos (PRO-002, "
        "AC2). Genuinely `{id}`-addressable, so `ensure_owner_or_not_found` "
        "is load-bearing here (ADR-015) -- a second provider cannot "
        "delete another provider's photo. The on-disk file is left in "
        "place (Decision 5, `Plan_S04_PRO-002.md`)."
    ),
)
async def delete_portfolio_photo(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    portfolio_service: PortfolioService = Depends(get_portfolio_service),  # noqa: B008
) -> SuccessResponse[None]:
    """Soft-delete one of the caller's own portfolio photos."""
    await portfolio_service.delete_photo(current_user.id, portfolio_id)
    await db.commit()
    return SuccessResponse[None](success=True, message="Photo removed.", data=None)


@router.put(
    "/me/portfolio/order",
    response_model=CollectionResponse[PortfolioPhotoResponse],
    responses={
        200: {"description": "The photos were reordered."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        422: {
            "description": (
                "The submitted `ordered_ids` set does not exactly match "
                "the caller's own active photo ids."
            ),
        },
    },
    summary="Reorder My Portfolio Photos",
    description=(
        "Reorders the caller's own active photos (PRO-002, AC2, Decision "
        "4). `ordered_ids` must be exactly the full set of the caller's "
        "own active photo ids -- a mismatch is rejected (422) before any "
        "row is touched, never a partial reorder."
    ),
)
async def reorder_portfolio(
    payload: ReorderPortfolioRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    portfolio_service: PortfolioService = Depends(get_portfolio_service),  # noqa: B008
) -> CollectionResponse[PortfolioPhotoResponse]:
    """Reorder the caller's own active portfolio photos."""
    photos = await portfolio_service.reorder(current_user.id, payload.ordered_ids)
    response_data = [_to_portfolio_photo_response(photo) for photo in photos]
    await db.commit()
    return CollectionResponse[PortfolioPhotoResponse](
        success=True,
        message="Portfolio reordered.",
        data=response_data,
        pagination={
            "page": 1,
            "page_size": len(response_data),
            "total_items": len(response_data),
            "total_pages": 1,
        },
    )


@router.get(
    "/me/availability",
    response_model=CollectionResponse[WeekdayAvailabilityResponse],
    responses={
        200: {"description": "The caller's weekly availability (always 7 entries)."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
    },
    summary="Get My Weekly Availability",
    description=(
        "Always returns exactly 7 entries (one per weekday, PRO-002, "
        "AC3, Decision 3) -- synthesizing a closed, not-yet-configured "
        "entry for any weekday without a saved row yet."
    ),
)
async def get_my_availability(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    availability_service: AvailabilityService = Depends(  # noqa: B008
        get_availability_service
    ),
) -> CollectionResponse[WeekdayAvailabilityResponse]:
    """Get the caller's weekly availability, synthesizing all 7 weekdays."""
    entries = await availability_service.get_my_availability(current_user.id)
    response_data = [_to_availability_response(entry) for entry in entries]
    await db.commit()
    return CollectionResponse[WeekdayAvailabilityResponse](
        success=True,
        message="Availability retrieved.",
        data=response_data,
        pagination={
            "page": 1,
            "page_size": len(response_data),
            "total_items": len(response_data),
            "total_pages": 1,
        },
    )


@router.put(
    "/me/availability",
    response_model=CollectionResponse[WeekdayAvailabilityResponse],
    responses={
        200: {"description": "The availability was updated."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        422: {"description": "A weekday appears more than once, or times are invalid."},
    },
    summary="Update My Weekly Availability",
    description=(
        "Upserts up to 7 weekday entries in one call (PRO-002, AC3, "
        "Decision 3) -- creates a missing row or updates an existing one. "
        "A closed day is expressed by `is_open=false` with both times "
        "null; `is_open=true` requires both times."
    ),
)
async def update_my_availability(
    payload: UpdateAvailabilityRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    availability_service: AvailabilityService = Depends(  # noqa: B008
        get_availability_service
    ),
) -> CollectionResponse[WeekdayAvailabilityResponse]:
    """Upsert the caller's weekly availability."""
    entries = [
        {
            "weekday": entry.weekday,
            "open_time": _parse_hour(entry.open_time) if entry.open_time else None,
            "close_time": _parse_hour(entry.close_time) if entry.close_time else None,
            "is_emergency_available": entry.is_emergency_available,
        }
        for entry in payload.entries
    ]
    updated = await availability_service.update_my_availability(
        current_user.id, entries
    )
    response_data = [_to_availability_response(entry) for entry in updated]
    await db.commit()
    return CollectionResponse[WeekdayAvailabilityResponse](
        success=True,
        message="Availability updated.",
        data=response_data,
        pagination={
            "page": 1,
            "page_size": len(response_data),
            "total_items": len(response_data),
            "total_pages": 1,
        },
    )
