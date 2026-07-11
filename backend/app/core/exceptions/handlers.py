from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.core.exceptions.constants import (
    DEFAULT_SERVER_ERROR_MESSAGE,
    VALIDATION_FAILED_MESSAGE,
)
from app.core.exceptions.exceptions import BusinessException
from app.core.logging import get_logger
from app.shared.schemas.response import ErrorDetail, ErrorResponse

logger = get_logger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handles Pydantic validation errors (FastAPI RequestValidationError).
    Normalizes loc fields and returns 422 standard response.
    """
    logger.info(f"Validation error: {exc.errors()}")

    errors = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field_name = str(loc[-1]) if loc else "unknown"
        # Avoid including transport prefixes if loc is just ("body",)
        if len(loc) == 1 and str(loc[0]) in ("body", "query", "path", "header"):
            field_name = None

        errors.append(
            ErrorDetail(
                field=field_name,
                message=error.get("msg", "Invalid value"),
            )
        )

    response = ErrorResponse(
        success=False,
        message=VALIDATION_FAILED_MESSAGE,
        errors=errors,
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles FastAPI HTTP exceptions.
    """
    response = ErrorResponse(
        success=False,
        message=str(exc.detail),
        errors=[],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True),
        headers=exc.headers,
    )


async def business_exception_handler(
    request: Request, exc: BusinessException
) -> JSONResponse:
    """
    Handles custom Business logic exceptions.
    """
    logger.warning(f"Business logic error: {exc.message}")

    response = ErrorResponse(
        success=False,
        message=exc.message,
        errors=exc.errors,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True),
        headers=exc.headers,
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handles all unexpected exceptions. Returns 500 without leaking details.
    """
    logger.error(
        "Unhandled server exception",
        exc_info=exc,
        extra={
            "http_method": request.method,
            "request_path": request.url.path,
        },
    )

    response = ErrorResponse(
        success=False,
        message=DEFAULT_SERVER_ERROR_MESSAGE,
        errors=[],
    )
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all exception handlers application-wide.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
