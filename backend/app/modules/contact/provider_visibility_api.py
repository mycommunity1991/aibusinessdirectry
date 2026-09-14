"""
Provider-facing Visibility Analytics endpoint (LEAD-002, Decision 1/3,
`Plan_S10_LEAD-002.md`) -- mounted at `/providers/me/visibility-
analytics`, in a route module owned by `contact` (not `provider`),
mirroring `provider_lead_api.py`'s exact `/providers/me/leads` mount
pattern a third time (after `verification`, then `contact/
provider_lead_api.py`).

Bare `Depends(get_current_user)` (not `require_role`) -- ownership/404
is enforced inside `VisibilityAnalyticsService`, not via a route guard,
exactly mirroring `GET /providers/me`/`GET /providers/me/portfolio`/
`GET /providers/me/leads`'s own established pattern: "does this caller
even have a Provider yet" is a data question, not a role question.

Returns `VisibilityAnalyticsResponse` directly, unwrapped (Decision 3)
-- mirrors `GET /providers/me/availability`'s "one synthesized,
non-paginated object" shape, not `CollectionResponse[T]`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.modules.contact.dependencies import get_visibility_analytics_service
from app.modules.contact.schemas import (
    VisibilityAnalyticsResponse,
    VisibilityDailyPoint,
    VisibilityMetric,
)
from app.modules.contact.services.visibility_analytics_service import (
    VisibilityAnalyticsData,
    VisibilityAnalyticsService,
)

router = APIRouter(tags=["Visibility Analytics"])


def _to_visibility_analytics_response(
    data: VisibilityAnalyticsData,
) -> VisibilityAnalyticsResponse:
    return VisibilityAnalyticsResponse(
        has_sufficient_data=data.has_sufficient_data,
        search_appearances=VisibilityMetric(
            total_last_30_days=data.search_appearances.total_last_30_days,
            trend=data.search_appearances.trend,
        ),
        contact_views=VisibilityMetric(
            total_last_30_days=data.contact_views.total_last_30_days,
            trend=data.contact_views.trend,
        ),
        daily_trend=[
            VisibilityDailyPoint(
                date=point.day,
                search_appearances=point.search_appearances,
                contact_views=point.contact_views,
            )
            for point in data.daily_trend
        ],
    )


@router.get(
    "",
    response_model=VisibilityAnalyticsResponse,
    responses={
        200: {
            "description": (
                "The caller's own Visibility Analytics -- two headline "
                "stats with trend indicators, plus a 30-day daily "
                "series."
            )
        },
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
    },
    summary="Get My Visibility Analytics",
    description=(
        "Returns the caller's own search-appearances and contact-views "
        "headline stats (AC1), each with a three-state trend indicator "
        "(up/down/flat, Decision 5) versus the immediately preceding "
        "30-day window, plus a zero-filled 30-day daily series (AC2, "
        "Decision 4). `has_sufficient_data` is `false` for a "
        "newly-onboarded provider with little or no history (AC4, "
        "Decision 6) -- the real (possibly all-zero) numbers are still "
        "returned alongside the flag. Scoped strictly to the caller's "
        "own Provider -- never another provider's activity (AC3). "
        "Carries no customer-identifying or per-event field (Decision "
        "8)."
    ),
)
async def get_my_visibility_analytics(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    visibility_analytics_service: VisibilityAnalyticsService = Depends(  # noqa: B008
        get_visibility_analytics_service
    ),
) -> VisibilityAnalyticsResponse:
    """Return the caller's own Visibility Analytics."""
    data = await visibility_analytics_service.get_my_visibility_analytics(
        current_user.id
    )
    await db.commit()
    return _to_visibility_analytics_response(data)
