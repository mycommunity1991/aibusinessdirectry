"""
Customer-facing Contact View endpoint (CON-001) -- mounted at
`/contact-views`.

`require_role(ROLE_CUSTOMER)` gates the route: contacting a matched
provider is a Customer-initiated action, mirroring DIR-001/CLM-001's
identical reasoning -- every registered Account already holds
`ROLE_CUSTOMER`, so this imposes no extra friction.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.contact.dependencies import get_contact_service
from app.modules.contact.schemas import (
    ContactViewRevealResponse,
    CreateContactViewRequest,
)
from app.modules.contact.services.contact_service import ContactService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Contact"])


@router.post(
    "",
    response_model=SuccessResponse[ContactViewRevealResponse],
    status_code=201,
    responses={
        201: {
            "model": SuccessResponse[ContactViewRevealResponse],
            "description": (
                "The Contact View was created; the phone number is revealed."
            ),
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The caller does not hold the customer role, or the "
                "target provider is the caller's own listing "
                "(self-dealing, AC3/AC4)."
            ),
        },
        404: {
            "description": (
                "The provider doesn't exist (or is soft-deleted), or "
                "`search_request_id` was supplied but doesn't exist or "
                "doesn't belong to the calling customer (Decision 4)."
            ),
        },
    },
    summary="Contact A Provider",
    description=(
        "Creates a Contact View and immediately reveals the provider's "
        "phone number -- no quote request, approval wait, or in-app "
        "messaging step exists anywhere in this flow (AC2). Rejected "
        "(403) if the requesting Customer's Account is the same Account "
        "that owns the target Provider (AC3/AC4). Every successful call "
        "creates a new row, even against the same provider (Decision "
        "5, `Plan_S08_CON-001.md`) -- no dedup."
    ),
)
async def create_contact_view(
    payload: CreateContactViewRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    contact_service: ContactService = Depends(get_contact_service),  # noqa: B008
) -> SuccessResponse[ContactViewRevealResponse]:
    """Create a Contact View and reveal the target provider's phone number."""
    contact_view, provider = await contact_service.create_contact_view(
        current_user.id,
        provider_id=payload.provider_id,
        search_request_id=payload.search_request_id,
    )
    await db.commit()
    return SuccessResponse[ContactViewRevealResponse](
        success=True,
        message="Contact revealed.",
        data=ContactViewRevealResponse(
            id=contact_view.id,
            provider_id=provider.id,
            provider_display_name=provider.display_name,
            phone_country_code=provider.phone_country_code,
            phone_number=provider.phone_number,
            whatsapp_number=provider.whatsapp_number,
        ),
    )
