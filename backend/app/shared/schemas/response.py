from typing import Literal

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model for all API responses."""

    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(
        ..., description="A message describing the result of the request"
    )


class SuccessResponse[T](BaseResponse):
    """Standard success response wrapping a generic data payload."""

    success: Literal[True] = Field(
        True, description="Always true for successful requests"
    )
    data: T = Field(..., description="The payload of the response")


class PaginationMeta(BaseModel):
    """Pagination metadata for collection responses."""

    page: int = Field(..., description="The current page number")
    page_size: int = Field(..., description="The number of items per page")
    total_items: int = Field(
        ..., description="The total number of items across all pages"
    )
    total_pages: int = Field(..., description="The total number of pages")


class CollectionResponse[T](BaseResponse):
    """Standard success response for collections supporting pagination."""

    success: Literal[True] = Field(
        True, description="Always true for successful collection requests"
    )
    data: list[T] = Field(..., description="The collection of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class ErrorDetail(BaseModel):
    """Detailed information about a specific error (e.g. validation error)."""

    field: str | None = Field(
        None, description="The field that caused the error, if applicable"
    )
    message: str = Field(..., description="The error message details")


class ErrorResponse(BaseResponse):
    """Standard error response model."""

    success: Literal[False] = Field(
        False, description="Always false for error responses"
    )
    errors: list[ErrorDetail] = Field(
        default_factory=list, description="A list of error details"
    )
