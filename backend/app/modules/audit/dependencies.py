"""Dependency-injection providers for the Audit module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.audit.repositories.audit_log_repository import AuditLogRepository
from app.modules.audit.services.audit_service import AuditService


def get_audit_log_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogRepository:
    """Provides an `AuditLogRepository` bound to the request-scoped DB session."""
    return AuditLogRepository(db)


def get_audit_service(
    audit_log_repository: Annotated[
        AuditLogRepository, Depends(get_audit_log_repository)
    ],
) -> AuditService:
    """Provides an `AuditService` bound to the request-scoped DB session."""
    return AuditService(audit_log_repository)
