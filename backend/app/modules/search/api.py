"""
`GET /search/providers` and `GET /search/categories` (DIR-001, Backend
Proposed Changes item 5, `Plan_S06_DIR-001.md`).

Both routes are gated by `Depends(require_role(ROLE_CUSTOMER))`, no
guest path (Decision 3) -- `14_USER_FLOWS.md` Flow 1 names "search" as
one of exactly three actions requiring authentication with no guest
path, and every registered Account already holds `ROLE_CUSTOMER`
unconditionally from registration onward, so this imposes no friction
beyond "must be signed in."
"""

import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.config import settings
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.search.dependencies import get_search_service
from app.modules.search.schemas import (
    CategoryOptionResponse,
    SearchResultProviderResponse,
)
from app.modules.search.services.search_service import SearchService
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Search"])

_DEFAULT_PAGE_SIZE = 20


@router.get(
    "/providers",
    response_model=CollectionResponse[SearchResultProviderResponse],
    responses={
        200: {"description": "One page of matching, discoverable providers."},
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        422: {"description": "`radius_km` is outside the configured bounds."},
    },
    summary="Browse Nearby Providers",
    description=(
        "Filters `is_discoverable=true` providers by category (optional, "
        "case-insensitive exact match against any of a provider's "
        "`provider_category_labels`, Decision 1) and geospatial radius "
        "around a caller-supplied `latitude`/`longitude` origin (AC1/"
        "AC2) -- category, then geospatial radius, then discoverability, "
        "in that literal order (AC2). Results are ordered nearest-first, "
        "`id ASC` as the deterministic tie-break (AC7), and include "
        "photo, name, category labels, rating with review count (never "
        "rating alone -- honestly `null` until a Review domain exists, "
        "Decision 2), and distance (AC3). An empty result set is a "
        "plain empty `data`/`total_items: 0` collection (AC4) -- "
        "distinguishing a pre-search state from a zero-result search is "
        "a client-side (mobile) concern (Decision 7)."
    ),
)
async def search_providers(
    latitude: float,
    longitude: float,
    category: str | None = None,
    radius_km: float = settings.SEARCH_DEFAULT_RADIUS_KM,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    search_service: SearchService = Depends(get_search_service),  # noqa: B008
) -> CollectionResponse[SearchResultProviderResponse]:
    """Returns one page of discoverable providers matching the given
    category/location/radius filters, nearest-first."""
    page_size = min(page_size, settings.SEARCH_MAX_PAGE_SIZE)
    results, total_items = await search_service.search_providers(
        category=category,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        page=page,
        page_size=page_size,
    )
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[SearchResultProviderResponse](
        success=True,
        message="Search results retrieved.",
        data=results,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/categories",
    response_model=SuccessResponse[list[CategoryOptionResponse]],
    responses={
        200: {"description": "The distinct set of category labels in use."},
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="List Category Chip Options",
    description=(
        "Returns the distinct, case-collapsed set of `provider_category_"
        "labels.label` values currently in use by `is_discoverable=true` "
        "providers (Decision 1) -- backs the mobile category-chip "
        "picker (S-06). Deliberately unpaginated (mirrors ADR-012's "
        "exception): bounded by the number of distinct labels real "
        "providers have actually typed, not by provider count."
    ),
)
async def list_categories(
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    search_service: SearchService = Depends(get_search_service),  # noqa: B008
) -> SuccessResponse[list[CategoryOptionResponse]]:
    """Returns the distinct set of category labels in use by
    discoverable providers."""
    categories = await search_service.list_categories()
    await db.commit()
    return SuccessResponse[list[CategoryOptionResponse]](
        success=True,
        message="Categories retrieved.",
        data=categories,
    )
