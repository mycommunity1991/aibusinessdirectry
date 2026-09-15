"""
Notifications Inbox endpoints (`ENG-001`, AC5/AC6, Decision 10,
`Plan_S12_ENG-001.md`) -- mounted at `/notifications`. `notification`'s
first-ever `api.py`.

Gated only by `get_current_user` (no `require_role`) -- every account,
of any role, may have notifications; mirrors how `/customers/me`-shaped
endpoints impose no extra role check beyond authentication. A
`require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` gate was
considered and rejected (Decision 10's own "Alternatives considered and
rejected") -- every registered Account already holds at least one of
these roles, so naming all three explicitly adds no real restriction
over plain authentication and would silently break the day a new role
is ever added.
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.config import settings
from app.database.session import get_db
from app.modules.notification.dependencies import get_notification_service
from app.modules.notification.models import Notification
from app.modules.notification.schemas import NotificationResponse, UnreadCountResponse
from app.modules.notification.services.notification_service import NotificationService
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)

router = APIRouter(tags=["Notifications"])

_DEFAULT_PAGE_SIZE = 20


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        body=notification.body,
        related_entity_type=notification.related_entity_type,
        related_entity_id=notification.related_entity_id,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get(
    "",
    response_model=CollectionResponse[NotificationResponse],
    responses={
        200: {"description": "One page of the caller's own notifications."},
        401: {"description": "Authentication required."},
    },
    summary="List My Notifications",
    description=(
        "Lists the caller's own `notifications` rows (AC6), newest "
        "first. The mobile client groups entries into New/Earlier by "
        "`read_at is None` (Decision 10) -- this endpoint returns raw "
        "fields only, never a server-computed grouping."
    ),
)
async def list_notifications(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    notification_service: NotificationService = Depends(  # noqa: B008
        get_notification_service
    ),
) -> CollectionResponse[NotificationResponse]:
    """Returns one page of the caller's own notifications."""
    page_size = min(page_size, settings.NOTIFICATION_MAX_PAGE_SIZE)
    notifications, total = await notification_service.list_for_user(
        current_user.id, page=page, page_size=page_size
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[NotificationResponse](
        success=True,
        message="Notifications retrieved.",
        data=[_to_response(notification) for notification in notifications],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/unread-count",
    response_model=SuccessResponse[UnreadCountResponse],
    responses={
        200: {"description": "The caller's current unread notification count."},
        401: {"description": "Authentication required."},
    },
    summary="Get My Unread Notification Count",
    description="Returns the caller's current unread notification count (AC5).",
)
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    notification_service: NotificationService = Depends(  # noqa: B008
        get_notification_service
    ),
) -> SuccessResponse[UnreadCountResponse]:
    """Returns the caller's current unread notification count."""
    count = await notification_service.count_unread(current_user.id)
    await db.commit()
    return SuccessResponse[UnreadCountResponse](
        success=True,
        message="Unread notification count retrieved.",
        data=UnreadCountResponse(count=count),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=SuccessResponse[NotificationResponse],
    responses={
        200: {"description": "The notification was marked read."},
        401: {"description": "Authentication required."},
        404: {
            "description": (
                "`notification_id` doesn't exist, or doesn't belong to "
                "the calling user (Decision 10 -- collapsed into one "
                "non-revealing 404, `ADR-015`, never a 403)."
            ),
        },
    },
    summary="Mark A Notification Read",
    description=(
        "Marks a `notifications` row read (AC6) -- idempotent: marking "
        "an already-read row read again is a harmless no-op, returning "
        "the same row unchanged."
    ),
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    notification_service: NotificationService = Depends(  # noqa: B008
        get_notification_service
    ),
) -> SuccessResponse[NotificationResponse]:
    """Marks the caller's own notification read."""
    notification = await notification_service.mark_read(
        notification_id, current_user.id
    )
    await db.commit()
    return SuccessResponse[NotificationResponse](
        success=True,
        message="Notification marked read.",
        data=_to_response(notification),
    )
