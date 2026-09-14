"""
Provider-facing Leads endpoint (LEAD-001, Decision 2,
`Plan_S10_LEAD-001.md`) -- mounted at `/providers/me/leads`, in a route
module owned by `contact` (not `provider`), mirroring the `verification`
module's exact `/providers/me/verification` mount precedent
(`backend/app/api/v1/api.py`).

Bare `Depends(get_current_user)` (not `require_role`) -- ownership/404
is enforced inside `LeadService`, not via a route guard, exactly
mirroring `GET /providers/me`/`GET /providers/me/portfolio`'s own
established pattern: "does this caller even have a Provider yet" is a
data question, not a role question.
"""

import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.database.session import get_db
from app.modules.contact.dependencies import get_lead_service
from app.modules.contact.schemas import LeadResponse
from app.modules.contact.services.lead_service import LeadItem, LeadService
from app.shared.schemas.response import CollectionResponse, PaginationMeta

router = APIRouter(tags=["Leads"])

_DEFAULT_PAGE_SIZE = 20


def _to_lead_response(item: LeadItem) -> LeadResponse:
    return LeadResponse(
        id=item.id,
        category_name=item.category_name,
        viewed_at=item.viewed_at,
        outcome_status=item.outcome_status,
    )


@router.get(
    "",
    response_model=CollectionResponse[LeadResponse],
    responses={
        200: {"description": "One page of the caller's own leads, most-recent-first."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
    },
    summary="List My Leads",
    description=(
        "Returns one page of the caller's own Contact Views (AC1/AC2), "
        "each enriched with a category/request context (`null` when "
        "genuinely unresolvable, Decision 3 -- never a fabricated "
        "fallback) and a three-state outcome status (`hired`/"
        "`not_hired`/`not_yet_reported`, Decision 5). Carries zero "
        "customer-identifying fields (no name, avatar, phone, or raw "
        "customer id, Decision 4/AC3). Ordered most-recent-first "
        "(AC2). Scoped strictly to the caller's own Provider -- never "
        "another provider's leads (AC4)."
    ),
)
async def list_my_leads(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    lead_service: LeadService = Depends(get_lead_service),  # noqa: B008
) -> CollectionResponse[LeadResponse]:
    """Return one page of the caller's own leads, most-recent-first."""
    page_size = min(page_size, settings.LEADS_MAX_PAGE_SIZE)
    items, total_items = await lead_service.list_my_leads(
        current_user.id, page=page, page_size=page_size
    )
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[LeadResponse](
        success=True,
        message="Leads retrieved.",
        data=[_to_lead_response(item) for item in items],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
