import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import setup_logging
from app.middleware.logging_middleware import LoggingMiddleware

# Setup a dummy app for middleware testing
app = FastAPI()
app.add_middleware(LoggingMiddleware)

# Setup logging for capturing output
setup_logging()


@app.get("/api/v1/endpoint1")
async def endpoint1():
    return {"message": "endpoint 1"}


@app.get("/api/v1/endpoint2")
async def endpoint2():
    return {"message": "endpoint 2"}


@app.get("/api/v1/error_endpoint")
async def error_endpoint():
    raise ValueError("Test error in endpoint")


client = TestClient(app)


def test_correlation_id_generation():
    """Test that a correlation ID is generated if not provided."""
    response = client.get("/api/v1/endpoint1")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"]


def test_correlation_id_propagation():
    """Test that a provided correlation ID is propagated."""
    test_id = "test-corr-id-123"
    response = client.get("/api/v1/endpoint1", headers={"X-Correlation-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == test_id


def test_middleware_execution_across_multiple_endpoints():
    """Test middleware runs correctly across different endpoints."""
    res1 = client.get("/api/v1/endpoint1")
    res2 = client.get("/api/v1/endpoint2")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.headers["X-Correlation-ID"] != res2.headers["X-Correlation-ID"]


def test_execution_time_and_client_ip_logging(caplog):
    """Test that execution time and client IP are logged correctly."""
    with caplog.at_level(logging.INFO):
        response = client.get(
            "/api/v1/endpoint1", headers={"X-Correlation-ID": "test-id"}
        )

    assert response.status_code == 200

    # Ensure Request completed was logged
    completed_log = next(
        (r for r in caplog.records if r.getMessage() == "Request completed"), None
    )
    assert completed_log is not None

    # Inspect the extra attributes added to the log record by the middleware
    assert hasattr(completed_log, "execution_time")
    assert isinstance(completed_log.execution_time, (int, float))
    assert hasattr(completed_log, "client_ip")
    assert completed_log.client_ip == "testclient"
    assert hasattr(completed_log, "status_code")
    assert completed_log.status_code == 200
