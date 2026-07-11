from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database.session import get_db
from app.main import app

client = TestClient(app)


def test_app_health_endpoint() -> None:
    """
    Verify that GET /api/v1/health returns HTTP 200
    and matches the expected schema.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    service_name = settings.APP_NAME.lower().replace(" ", "-")

    assert data == {
        "success": True,
        "message": "Application health retrieved successfully.",
        "data": {
            "status": "healthy",
            "service": service_name,
            "version": settings.APP_VERSION,
        },
    }


def test_db_health_endpoint_healthy() -> None:
    """
    Verify that GET /api/v1/health/db returns HTTP 200
    when the database is available.
    """
    # Mock database session to execute SELECT 1 successfully
    mock_session = AsyncMock()
    mock_session.execute.return_value = AsyncMock()

    # Override get_db dependency to yield mock_session
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Database health retrieved successfully.",
            "data": {"status": "healthy", "database": "connected"},
        }
    finally:
        # Clear dependency overrides after test execution
        app.dependency_overrides.clear()


def test_db_health_endpoint_unhealthy() -> None:
    """
    Verify that GET /api/v1/health/db returns HTTP 503
    when database connectivity fails.
    """
    # Mock database session to raise an exception on execute
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection timeout")

    # Override get_db dependency to yield mock_session
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        response = client.get("/api/v1/health/db")
        assert response.status_code == 503
        assert response.json() == {
            "success": True,
            "message": "Database health retrieved successfully.",
            "data": {
                "status": "unhealthy",
                "database": "disconnected",
            },
        }
    finally:
        # Clear dependency overrides after test execution
        app.dependency_overrides.clear()
