"""Dependency-injection providers for the Administration module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)


def get_admin_action_log_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActionLogRepository:
    """Provides an `AdminActionLogRepository` bound to the request-scoped
    DB session."""
    return AdminActionLogRepository(db)


def get_admin_action_log_service(
    admin_action_log_repository: Annotated[
        AdminActionLogRepository, Depends(get_admin_action_log_repository)
    ],
) -> AdminActionLogService:
    """Provides an `AdminActionLogService` bound to the request-scoped
    DB session."""
    return AdminActionLogService(admin_action_log_repository)
