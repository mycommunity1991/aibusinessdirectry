import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.customer.dependencies import (
    get_customer_service,
    get_saved_address_service,
)
from app.modules.customer.models import (
    CustomerPreferences,
    CustomerProfile,
    SavedAddress,
)
from app.modules.customer.schemas import (
    CreateSavedAddressRequest,
    CustomerProfileResponse,
    SavedAddressResponse,
    UpdateCustomerProfileRequest,
    UpdateSavedAddressRequest,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.customer.services.saved_address_service import SavedAddressService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Customer"])


def _to_response(
    profile: CustomerProfile, preferences: CustomerPreferences
) -> CustomerProfileResponse:
    return CustomerProfileResponse(
        id=profile.id,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        language=preferences.language,
        notification_channel=preferences.notification_channel,
    )


@router.get(
    "/me",
    response_model=SuccessResponse[CustomerProfileResponse],
    responses={
        200: {
            "model": SuccessResponse[CustomerProfileResponse],
            "description": "The caller's own customer profile and preferences.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="Get My Customer Profile",
    description=(
        "Returns the authenticated caller's own display name, avatar, "
        "language, and notification channel (AC4). Resolved exclusively "
        "from the caller's own `user_id` -- there is no `{id}`-addressable "
        "route, so another user's profile can never be requested (AC7). "
        "Self-healing for any pre-CUS-001 account: lazily provisions a "
        "default profile on first access instead of ever 404ing (Decision "
        "4, `Plan_S03_CUS-001.md`)."
    ),
)
async def get_my_profile(
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    customer_service: CustomerService = Depends(get_customer_service),  # noqa: B008
) -> SuccessResponse[CustomerProfileResponse]:
    """Return the caller's own customer profile and preferences."""
    profile, preferences = await customer_service.get_my_profile(current_user.id)
    await db.commit()
    return SuccessResponse[CustomerProfileResponse](
        success=True,
        message="Profile retrieved.",
        data=_to_response(profile, preferences),
    )


@router.patch(
    "/me",
    response_model=SuccessResponse[CustomerProfileResponse],
    responses={
        200: {
            "model": SuccessResponse[CustomerProfileResponse],
            "description": "The caller's customer profile was updated.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="Update My Customer Profile",
    description=(
        "Partially updates the authenticated caller's own display name, "
        "avatar, language, and/or notification channel -- only fields "
        "present in the request body are changed (AC4). Resolved "
        "exclusively from the caller's own `user_id` -- there is no "
        "`{id}`-addressable route, so another user's profile can never "
        "be affected (AC7)."
    ),
)
async def update_my_profile(
    payload: UpdateCustomerProfileRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    customer_service: CustomerService = Depends(get_customer_service),  # noqa: B008
) -> SuccessResponse[CustomerProfileResponse]:
    """Partially update the caller's own customer profile and preferences."""
    profile, preferences = await customer_service.update_my_profile(
        current_user.id, fields=payload.model_dump(exclude_unset=True)
    )
    await db.commit()
    return SuccessResponse[CustomerProfileResponse](
        success=True,
        message="Profile updated.",
        data=_to_response(profile, preferences),
    )


def _to_address_response(address: SavedAddress) -> SavedAddressResponse:
    return SavedAddressResponse(
        id=address.id,
        label=address.label,
        address_line=address.address_line,
        city=address.city,
        region=address.region,
        country_code=address.country_code,
        latitude=address.latitude,
        longitude=address.longitude,
        is_default=address.is_default,
    )


@router.get(
    "/me/addresses",
    response_model=SuccessResponse[list[SavedAddressResponse]],
    responses={
        200: {
            "model": SuccessResponse[list[SavedAddressResponse]],
            "description": "The caller's own saved addresses.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="List My Saved Addresses",
    description=(
        "Lists all of the authenticated caller's own active saved "
        "addresses, with the default clearly flagged (AC6). Resolved "
        "exclusively from the caller's own `user_id` -- another "
        "customer's addresses are never included. Deliberately "
        "unpaginated, mirroring `GET /auth/sessions` -- a customer's "
        "realistic address count is small and per-owner."
    ),
)
async def list_my_addresses(
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    saved_address_service: SavedAddressService = Depends(  # noqa: B008
        get_saved_address_service  # noqa: B008
    ),
) -> SuccessResponse[list[SavedAddressResponse]]:
    """List the caller's own active saved addresses."""
    addresses = await saved_address_service.list_my_addresses(current_user.id)
    await db.commit()
    return SuccessResponse[list[SavedAddressResponse]](
        success=True,
        message="Saved addresses retrieved.",
        data=[_to_address_response(address) for address in addresses],
    )


@router.post(
    "/me/addresses",
    response_model=SuccessResponse[SavedAddressResponse],
    status_code=201,
    responses={
        201: {
            "model": SuccessResponse[SavedAddressResponse],
            "description": "The saved address was created.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="Create a Saved Address",
    description=(
        "Creates a new saved address for the authenticated caller "
        "(AC1). If `is_default` is `true`, any previously-default "
        "address for this customer is unset in the same transaction "
        "(AC2) -- exactly one address per customer can be marked "
        "default at a time."
    ),
)
async def create_my_address(
    payload: CreateSavedAddressRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    saved_address_service: SavedAddressService = Depends(  # noqa: B008
        get_saved_address_service  # noqa: B008
    ),
) -> SuccessResponse[SavedAddressResponse]:
    """Create a new saved address for the caller."""
    address = await saved_address_service.create_address(
        current_user.id, fields=payload.model_dump()
    )
    await db.commit()
    return SuccessResponse[SavedAddressResponse](
        success=True,
        message="Address created.",
        data=_to_address_response(address),
    )


@router.patch(
    "/me/addresses/{address_id}",
    response_model=SuccessResponse[SavedAddressResponse],
    responses={
        200: {
            "model": SuccessResponse[SavedAddressResponse],
            "description": "The saved address was updated.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The address does not exist, or does not belong to the "
                "caller -- the response never reveals which (AC8)."
            ),
        },
    },
    summary="Update a Saved Address",
    description=(
        "Partially updates one of the caller's own saved addresses -- "
        "only fields present in the request body are changed (AC6). "
        "If `is_default` is set to `true`, any previously-default "
        "address for this customer is unset in the same transaction "
        "(AC2). `{address_id}` is a real, client-supplied identifier -- "
        "ownership is enforced defensively (AC8), unlike `PATCH /me` "
        "which has no `{id}` at all."
    ),
)
async def update_my_address(
    address_id: uuid.UUID,
    payload: UpdateSavedAddressRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    saved_address_service: SavedAddressService = Depends(  # noqa: B008
        get_saved_address_service  # noqa: B008
    ),
) -> SuccessResponse[SavedAddressResponse]:
    """Partially update one of the caller's own saved addresses."""
    address = await saved_address_service.update_address(
        current_user.id,
        address_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    await db.commit()
    return SuccessResponse[SavedAddressResponse](
        success=True,
        message="Address updated.",
        data=_to_address_response(address),
    )


@router.delete(
    "/me/addresses/{address_id}",
    response_model=SuccessResponse[None],
    responses={
        200: {
            "model": SuccessResponse[None],
            "description": "The address was deleted.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The address does not exist, or does not belong to the "
                "caller -- the response never reveals which (AC8)."
            ),
        },
    },
    summary="Delete a Saved Address",
    description=(
        "Soft-deletes one of the caller's own saved addresses (AC6): "
        "the row is never permanently removed, only excluded from all "
        "future list/get results (Decision 3, `Plan_S03_CUS-002.md`). "
        "Never auto-promotes another address to default if the deleted "
        "one was the default -- the customer is left with no default "
        "address; a subsequent `GET /me/addresses` clearly shows no row "
        "with `is_default: true` (AC7)."
    ),
)
async def delete_my_address(
    address_id: uuid.UUID,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    saved_address_service: SavedAddressService = Depends(  # noqa: B008
        get_saved_address_service  # noqa: B008
    ),
) -> SuccessResponse[None]:
    """Soft-delete one of the caller's own saved addresses."""
    await saved_address_service.delete_address(current_user.id, address_id)
    await db.commit()
    return SuccessResponse[None](success=True, message="Address deleted.", data=None)
