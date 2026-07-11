from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_openapi_json() -> None:
    """Verify OpenAPI JSON endpoint is accessible and correctly generated."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi_data = response.json()

    assert "openapi" in openapi_data
    assert openapi_data["info"]["title"] == settings.APP_NAME
    assert openapi_data["info"]["version"] == settings.APP_VERSION
    assert openapi_data["info"]["contact"]["name"] == "MyCommunity API Team"

    # Check that the health endpoint is included and versioned route is preserved
    paths = openapi_data.get("paths", {})
    health_route = f"{settings.API_PREFIX}/v1/health"
    assert health_route in paths
    assert "get" in paths[health_route]
    assert paths[health_route]["get"]["tags"] == ["Health"]


def test_swagger_ui() -> None:
    """Verify Swagger UI endpoint is accessible."""
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text.lower()


def test_redoc() -> None:
    """Verify ReDoc endpoint is accessible."""
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "redoc" in response.text.lower()
