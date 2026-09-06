from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.customer.dependencies import get_customer_service
from app.modules.customer.models import CustomerPreferences, CustomerProfile
from app.modules.customer.schemas import (
    CustomerProfileResponse,
    UpdateCustomerProfileRequest,
)
from app.modules.customer.services.customer_service import CustomerService
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
