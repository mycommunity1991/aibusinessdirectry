from pydantic import BaseModel

from app.shared.schemas.response import (
    CollectionResponse,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    SuccessResponse,
)


class DummyData(BaseModel):
    id: int
    name: str


def test_success_response_serialization():
    data = DummyData(id=1, name="Test Item")
    response = SuccessResponse[DummyData](success=True, message="Success", data=data)

    dump = response.model_dump()
    assert dump["success"] is True
    assert dump["message"] == "Success"
    assert dump["data"]["id"] == 1
    assert dump["data"]["name"] == "Test Item"


def test_collection_response_serialization():
    data = [DummyData(id=1, name="Item 1"), DummyData(id=2, name="Item 2")]
    pagination = PaginationMeta(page=1, page_size=10, total_items=2, total_pages=1)

    response = CollectionResponse[DummyData](
        success=True, message="Collection retrieved", data=data, pagination=pagination
    )

    dump = response.model_dump()
    assert dump["success"] is True
    assert dump["message"] == "Collection retrieved"
    assert len(dump["data"]) == 2
    assert dump["data"][0]["id"] == 1
    assert dump["pagination"]["page"] == 1
    assert dump["pagination"]["total_items"] == 2


def test_error_response_serialization():
    errors = [
        ErrorDetail(field="email", message="Invalid email format"),
        ErrorDetail(field=None, message="System error"),
    ]
    response = ErrorResponse(success=False, message="Validation failed", errors=errors)

    dump = response.model_dump()
    assert dump["success"] is False
    assert dump["message"] == "Validation failed"
    assert len(dump["errors"]) == 2
    assert dump["errors"][0]["field"] == "email"
    assert dump["errors"][0]["message"] == "Invalid email format"
    assert dump["errors"][1]["field"] is None
