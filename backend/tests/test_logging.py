import json
import logging
from unittest.mock import patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.logging import JSONFormatter, setup_logging
from app.main import app

# Ensure logging is set up for tests (mimics lifespan)
setup_logging()

client = TestClient(app)


# Dummy router for testing logging
@app.get("/api/v1/dummy_logging")
async def dummy_logging_endpoint():
    logger = logging.getLogger(__name__)
    logger.info("Test log inside endpoint")
    return {"message": "ok"}


@app.get("/api/v1/dummy_exception")
async def dummy_exception_endpoint():
    raise ValueError("Test unhandled exception")


def test_json_formatter_structure(caplog):
    """Test the JSON formatter produces correct fields."""
    logger = logging.getLogger("test_logger")
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    with patch("sys.stdout", new_callable=list):
        with caplog.at_level(logging.INFO):
            logger.info("Test structure", extra={"custom_field": 42})

    # We inspect caplog records formatted manually
    record = caplog.records[-1]
    formatter = JSONFormatter()
    formatted = formatter.format(record)

    data = json.loads(formatted)
    assert "timestamp" in data
    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Test structure"
    assert data["custom_field"] == 42

    logger.removeHandler(handler)


def test_json_formatter_sensitive_data(caplog):
    """Test sensitive data masking in JSON formatter."""

    record = logging.LogRecord(
        name="test_sensitive",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test sensitive",
        args=(),
        exc_info=None,
    )
    # Add extra attributes
    record.__dict__["password"] = "supersecret"
    record.__dict__["jwt_token"] = "eyJhb..."
    record.__dict__["nested"] = {"authorization": "Bearer foo"}

    formatter = JSONFormatter()
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["password"] == "***MASKED***"
    assert data["jwt_token"] == "***MASKED***"
    assert data["nested"]["authorization"] == "***MASKED***"


@pytest.mark.anyio
async def test_exception_logging():
    """Test that unhandled exceptions are caught and return 500 JSON response."""
    from app.core.exceptions.constants import DEFAULT_SERVER_ERROR_MESSAGE
    from app.core.exceptions.handlers import unexpected_exception_handler

    # Create a dummy request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/dummy_exception",
        "headers": [],
    }
    request = Request(scope)
    exc = ValueError("Test unhandled exception")

    response = await unexpected_exception_handler(request, exc)

    assert response.status_code == 500
    body = json.loads(response.body.decode())
    assert body["success"] is False
    assert body["message"] == DEFAULT_SERVER_ERROR_MESSAGE
    assert body["errors"] == []
