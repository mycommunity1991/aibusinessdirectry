"""
`GET /search-requests/{search_request_id}` (AI-002, Decision 6,
`Plan_S07_AI-002.md`) -- the customer's ranked-results screen. A
separate router/prefix from `/search` (a genuine sibling collection, not
a sub-resource of the structured-browse endpoints, ADR-015's
`{id}`-addressable-collection shape), mirroring `provider/claim_api.py`
vs. `provider/admin_claim_api.py` living as separate files/routers
inside one module.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.search.dependencies import get_search_request_service
from app.modules.search.schemas import SearchRequestResultResponse
from app.modules.search.services.search_request_service import SearchRequestService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Search Requests"])


@router.get(
    "/{search_request_id}",
    response_model=SuccessResponse[SearchRequestResultResponse],
    responses={
        200: {
            "model": SuccessResponse[SearchRequestResultResponse],
            "description": "The search request's current status and matched providers.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The search request does not exist, or does not belong to "
                "the caller -- the response never reveals which."
            ),
        },
    },
    summary="Get A Search Request's Results",
    description=(
        "Returns the same ranked-results shape (AC4) regardless of "
        "whether the request was resolved by the automated matcher or "
        "by an admin (Decision 4/6) -- `matched_providers` is empty "
        "while `status=pending_manual_match` or `unmatched`."
    ),
)
async def get_search_request(
    search_request_id: uuid.UUID,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    search_request_service: SearchRequestService = Depends(  # noqa: B008
        get_search_request_service
    ),
) -> SuccessResponse[SearchRequestResultResponse]:
    """Retrieve a search request's status and matched providers, owned
    exclusively by the caller."""
    search_request = await search_request_service.get_result_for_customer(
        current_user.id, search_request_id
    )
    matched_providers = await search_request_service.get_matched_providers(
        search_request
    )
    await db.commit()
    return SuccessResponse[SearchRequestResultResponse](
        success=True,
        message="Search request retrieved.",
        data=SearchRequestResultResponse(
            status=search_request.status,
            matched_providers=matched_providers,
        ),
    )
