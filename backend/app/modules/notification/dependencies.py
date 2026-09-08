"""Dependency-injection providers for the Notification module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_service import NotificationService


def get_notification_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRepository:
    """Provides a `NotificationRepository` bound to the request-scoped
    DB session."""
    return NotificationRepository(db)


def get_notification_service(
    notification_repository: Annotated[
        NotificationRepository, Depends(get_notification_repository)
    ],
) -> NotificationService:
    """Provides a `NotificationService` bound to the request-scoped DB
    session."""
    return NotificationService(notification_repository)
