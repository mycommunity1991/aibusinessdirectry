from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions.constants import (
    DEFAULT_SERVER_ERROR_MESSAGE,
    VALIDATION_FAILED_MESSAGE,
)
from app.core.exceptions.exceptions import BusinessException
from app.core.exceptions.handlers import register_exception_handlers
from app.shared.schemas.response import ErrorDetail

app = FastAPI()
register_exception_handlers(app)


class Item(BaseModel):
    name: str
    price: float


@app.post("/test-validation")
async def endpoint_validation(item: Item):
    return item


@app.get("/test-http")
async def endpoint_http():
    raise HTTPException(
        status_code=401,
        detail="Unauthorized access",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/test-business")
async def endpoint_business():
    raise BusinessException(
        message="Business rule violated",
        status_code=403,
        errors=[ErrorDetail(field="custom_field", message="Custom error")],
        headers={"X-Business-Error": "true"},
    )


@app.get("/test-unexpected")
async def endpoint_unexpected():
    raise ValueError("Something completely unexpected")


client = TestClient(app, raise_server_exceptions=False)


def test_validation_exception_handler():
    response = client.post("/test-validation", json={"name": "test"})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["success"] is False
    assert data["message"] == VALIDATION_FAILED_MESSAGE
    assert "errors" in data
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "price"
    assert data["errors"][0]["message"] == "Field required"


def test_http_exception_handler():
    response = client.get("/test-http")
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/json"
    assert response.headers["www-authenticate"] == "Bearer"
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Unauthorized access"
    assert "errors" in data
    assert data["errors"] == []


def test_business_exception_handler():
    response = client.get("/test-business")
    assert response.status_code == 403
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-business-error"] == "true"
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Business rule violated"
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "custom_field"
    assert data["errors"][0]["message"] == "Custom error"


def test_unexpected_exception_handler():
    response = client.get("/test-unexpected")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["success"] is False
    assert data["message"] == DEFAULT_SERVER_ERROR_MESSAGE
    assert "errors" in data
    assert data["errors"] == []
