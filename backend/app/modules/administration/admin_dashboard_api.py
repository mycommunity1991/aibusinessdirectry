"""
Admin dashboard endpoints (ADM-002, `Plan_S11_ADM-002.md`) -- mounted at
`/admin/dashboard`, `/admin/feature-flags`, `/admin/system-settings`.

`require_role(ROLE_ADMIN)` alone is every route's entire authorization
boundary (mirrors `administration/api.py`/`search/admin_manual_match_
api.py` exactly, AC5). Backend-API-only -- no dashboard UI exists or is
expected here (Decision 2, Open Question 1): every AC is fully
satisfiable via a backend endpoint alone, and zero admin-facing Flutter
code exists anywhere in this codebase to extend.

Both `feature-flags`/`system-settings` list endpoints paginate a small,
finite, code-defined row set (Decision 3) in Python -- `FeatureFlagService.
list_all`/`SystemSettingService.list_all` return the *entire* set (never
more than a handful of rows), so no repository-level `OFFSET`/`LIMIT` is
needed; the default page size (20) and max (100) mirror
`05_API_GUIDELINES.md`'s general pagination default.
"""

import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_ADMIN
from app.database.session import get_db
from app.modules.administration.dependencies import (
    get_dashboard_service,
    get_feature_flag_service,
    get_system_setting_service,
)
from app.modules.administration.models import FeatureFlag, SystemSetting
from app.modules.administration.schemas import (
    DashboardSummaryResponse,
    FeatureFlagResponse,
    FeatureFlagToggleRequest,
    SystemSettingResponse,
    SystemSettingUpdateRequest,
)
from app.modules.administration.services.dashboard_service import DashboardService
from app.modules.administration.services.feature_flag_service import FeatureFlagService
from app.modules.administration.services.system_setting_service import (
    SystemSettingService,
)
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Admin Dashboard"])

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


def _to_feature_flag_response(flag: FeatureFlag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        id=flag.id,
        key=flag.key,
        is_enabled=flag.is_enabled,
        description=flag.description,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


def _to_system_setting_response(setting: SystemSetting) -> SystemSettingResponse:
    return SystemSettingResponse(
        id=setting.id,
        key=setting.key,
        value=setting.value,
        description=setting.description,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


def _paginate[T](items: list[T], *, page: int, page_size: int) -> tuple[list[T], int]:
    """
    Python-level pagination over an already-fetched, genuinely small,
    finite, code-defined row set (Decision 3) -- never a repository-level
    `OFFSET`/`LIMIT`, since `FeatureFlagService`/`SystemSettingService`'s
    `list_all()` already returns every row.
    """
    total = len(items)
    offset = (page - 1) * page_size
    return items[offset : offset + page_size], total


@router.get(
    "/dashboard/summary",
    response_model=SuccessResponse[DashboardSummaryResponse],
    responses={
        200: {"description": "The current dashboard summary."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="Get Dashboard Summary",
    description=(
        "Summarizes the pending-verification, pending-manual-match, and "
        "open-unmatched-query-report counts (AC2), each paired with its "
        "own queue's real, registered path."
    ),
)
async def get_dashboard_summary(
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    dashboard_service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> SuccessResponse[DashboardSummaryResponse]:
    """Returns the current dashboard summary."""
    summary = await dashboard_service.get_summary()
    await db.commit()
    return SuccessResponse[DashboardSummaryResponse](
        success=True,
        message="Dashboard summary retrieved.",
        data=DashboardSummaryResponse(
            pending_verification_count=summary.pending_verification_count,
            pending_verification_queue_path=summary.pending_verification_queue_path,
            pending_manual_match_count=summary.pending_manual_match_count,
            pending_manual_match_queue_path=summary.pending_manual_match_queue_path,
            open_unmatched_query_report_count=(
                summary.open_unmatched_query_report_count
            ),
            open_unmatched_query_report_queue_path=(
                summary.open_unmatched_query_report_queue_path
            ),
        ),
    )


@router.get(
    "/feature-flags",
    response_model=CollectionResponse[FeatureFlagResponse],
    responses={
        200: {"description": "One page of every `feature_flags` row."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List Feature Flags",
    description="Lists every `feature_flags` row (AC1), ordered by `key`.",
)
async def list_feature_flags(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    feature_flag_service: FeatureFlagService = Depends(  # noqa: B008
        get_feature_flag_service
    ),
) -> CollectionResponse[FeatureFlagResponse]:
    """Returns one page of every `feature_flags` row."""
    page_size = min(page_size, _MAX_PAGE_SIZE)
    all_flags = await feature_flag_service.list_all()
    page_flags, total = _paginate(all_flags, page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[FeatureFlagResponse](
        success=True,
        message="Feature flags retrieved.",
        data=[_to_feature_flag_response(flag) for flag in page_flags],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.patch(
    "/feature-flags/{key}",
    response_model=SuccessResponse[FeatureFlagResponse],
    responses={
        200: {"description": "The feature flag was toggled."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "No feature flag exists for this key."},
    },
    summary="Toggle A Feature Flag",
    description=(
        "Flips `is_enabled` for an existing flag (AC4) -- takes effect "
        "for the next relevant request, no deploy required. Feature-flag "
        "keys are code-defined and migration-seeded only (Decision 3); "
        "an unknown key 404s rather than creating a new one."
    ),
)
async def toggle_feature_flag(
    key: str,
    payload: FeatureFlagToggleRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    feature_flag_service: FeatureFlagService = Depends(  # noqa: B008
        get_feature_flag_service
    ),
) -> SuccessResponse[FeatureFlagResponse]:
    """Toggles an existing feature flag's `is_enabled`."""
    flag = await feature_flag_service.toggle(
        key, is_enabled=payload.is_enabled, admin_user_id=current_user.id
    )
    await db.commit()
    return SuccessResponse[FeatureFlagResponse](
        success=True,
        message="Feature flag updated.",
        data=_to_feature_flag_response(flag),
    )


@router.get(
    "/system-settings",
    response_model=CollectionResponse[SystemSettingResponse],
    responses={
        200: {"description": "One page of every `system_settings` row."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List System Settings",
    description="Lists every `system_settings` row (AC1), ordered by `key`.",
)
async def list_system_settings(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    system_setting_service: SystemSettingService = Depends(  # noqa: B008
        get_system_setting_service
    ),
) -> CollectionResponse[SystemSettingResponse]:
    """Returns one page of every `system_settings` row."""
    page_size = min(page_size, _MAX_PAGE_SIZE)
    all_settings = await system_setting_service.list_all()
    page_settings, total = _paginate(all_settings, page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[SystemSettingResponse](
        success=True,
        message="System settings retrieved.",
        data=[_to_system_setting_response(setting) for setting in page_settings],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.patch(
    "/system-settings/{key}",
    response_model=SuccessResponse[SystemSettingResponse],
    responses={
        200: {"description": "The system setting was updated."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "No system setting exists for this key."},
    },
    summary="Update A System Setting",
    description=(
        "Overwrites an existing setting's `value` (AC1). System-setting "
        "keys are code-defined and migration-seeded only (Decision 3); "
        "an unknown key 404s rather than creating a new one."
    ),
)
async def update_system_setting(
    key: str,
    payload: SystemSettingUpdateRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    system_setting_service: SystemSettingService = Depends(  # noqa: B008
        get_system_setting_service
    ),
) -> SuccessResponse[SystemSettingResponse]:
    """Updates an existing system setting's value."""
    setting = await system_setting_service.update_value(
        key, value=payload.value, admin_user_id=current_user.id
    )
    await db.commit()
    return SuccessResponse[SystemSettingResponse](
        success=True,
        message="System setting updated.",
        data=_to_system_setting_response(setting),
    )
