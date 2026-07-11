import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import verify_routes
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Verify that the health check endpoint returns 200 and 'healthy' status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["service"] == "mycommunity-api"
    assert data["data"]["version"] == "1.0.0"


def test_verify_routes_no_routes() -> None:
    """Verify that verify_routes raises ValueError if no routes exist."""
    dummy_app = FastAPI()
    dummy_app.router.routes.clear()

    with pytest.raises(ValueError, match="No routes registered in the application"):
        verify_routes(dummy_app)


def test_verify_routes_duplicate_routes() -> None:
    """Verify that verify_routes raises ValueError if duplicates exist."""
    dummy_app = FastAPI()

    router1 = APIRouter()

    @router1.get("/duplicate")
    def route1() -> str:
        return "one"

    router2 = APIRouter()

    @router2.get("/duplicate")
    def route2() -> str:
        return "two"

    dummy_app.include_router(router1)
    dummy_app.include_router(router2)

    with pytest.raises(ValueError, match="Duplicate route detected: GET /duplicate"):
        verify_routes(dummy_app)
