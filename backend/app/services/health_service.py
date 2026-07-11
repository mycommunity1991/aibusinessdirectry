import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    DB_STATUS_CONNECTED,
    DB_STATUS_DISCONNECTED,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_UNHEALTHY,
)
from app.schemas.health import DatabaseHealthResponse, HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    """Service class responsible for system health check business logic."""

    async def get_app_health(self) -> HealthResponse:
        """Build and return application health check response model.

        Does not perform any database operations.
        """
        # Slugify / format application name dynamically based on settings
        service_name = settings.APP_NAME.lower().replace(" ", "-")

        return HealthResponse(
            status=HEALTH_STATUS_HEALTHY,
            service=service_name,
            version=settings.APP_VERSION,
        )

    async def get_db_health(self, db: AsyncSession) -> DatabaseHealthResponse:
        """
        Verify database connectivity using a lightweight query and return
        response model.

        Reuses the existing connection session and gracefully handles database
        exceptions.
        """
        try:
            # Execute the lightweight connection query
            await db.execute(text("SELECT 1"))
            return DatabaseHealthResponse(
                status=HEALTH_STATUS_HEALTHY,
                database=DB_STATUS_CONNECTED,
            )
        except Exception:
            # Log failure with stack trace using logger.exception.
            # Avoid logging sensitive information like connection URLs or credentials.
            logger.exception("Database connectivity health check failed.")
            return DatabaseHealthResponse(
                status=HEALTH_STATUS_UNHEALTHY,
                database=DB_STATUS_DISCONNECTED,
            )
