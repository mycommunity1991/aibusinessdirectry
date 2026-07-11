from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import HEALTH_STATUS_UNHEALTHY
from app.core.database.session import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.services.health_service import HealthService
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "",
    response_model=SuccessResponse[HealthResponse],
    responses={
        200: {
            "model": SuccessResponse[HealthResponse],
            "description": "Application health status details.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Application health retrieved successfully.",
                        "data": {
                            "status": "healthy",
                            "service": "mycommunity-api",
                            "version": "1.0.0",
                        },
                    }
                }
            },
        }
    },
    summary="Get Application Health Status",
    description=(
        "Verify that the API application is running and able to serve requests."
    ),
)
async def get_health(
    service: HealthService = Depends(),  # noqa: B008
) -> SuccessResponse[HealthResponse]:
    """Check API application health status."""
    health_result = await service.get_app_health()
    return SuccessResponse[HealthResponse](
        success=True,
        message="Application health retrieved successfully.",
        data=health_result,
    )


@router.get(
    "/db",
    response_model=SuccessResponse[DatabaseHealthResponse],
    responses={
        200: {
            "model": SuccessResponse[DatabaseHealthResponse],
            "description": "Database is connected and healthy.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Database health retrieved successfully.",
                        "data": {
                            "status": "healthy",
                            "database": "connected",
                        },
                    }
                }
            },
        },
        503: {
            "model": SuccessResponse[DatabaseHealthResponse],
            "description": "Database is disconnected or unavailable.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Database health retrieved successfully.",
                        "data": {
                            "status": "unhealthy",
                            "database": "disconnected",
                        },
                    }
                }
            },
        },
    },
    summary="Get Database Health Status",
    description="Verify PostgreSQL connectivity and connection pool health.",
)
async def get_db_health(
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    service: HealthService = Depends(),  # noqa: B008
) -> SuccessResponse[DatabaseHealthResponse]:
    """Check database connection and availability."""
    health_result = await service.get_db_health(db)
    if health_result.status == HEALTH_STATUS_UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return SuccessResponse[DatabaseHealthResponse](
        success=True,
        message="Database health retrieved successfully.",
        data=health_result,
    )
