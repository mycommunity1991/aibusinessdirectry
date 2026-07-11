import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import set_correlation_id, set_user_id
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate or read correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in state and context
        request.state.correlation_id = correlation_id
        req_token = set_correlation_id(correlation_id)

        # Extract client IP
        client_ip = request.client.host if request.client else None

        # Try to extract user_id if authentication middleware has set it
        # (Assuming it might be stored in request.state.user later in the project)
        user_id = None
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            user_id = str(request.state.user.id)
        user_token = set_user_id(user_id)

        # Log request started
        logger.info(
            "Request started",
            extra={
                "http_method": request.method,
                "request_path": request.url.path,
                "client_ip": client_ip,
            },
        )

        start_time = time.perf_counter()

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Exception bypassed or will be caught by ExceptionMiddleware outside
            logger.error(
                "Unhandled middleware exception",
                exc_info=e,
                extra={
                    "http_method": request.method,
                    "request_path": request.url.path,
                    "client_ip": client_ip,
                },
            )
            raise e
        finally:
            # Calculate execution time in ms
            execution_time = round((time.perf_counter() - start_time) * 1000, 2)

            # Log request completed
            logger.info(
                "Request completed",
                extra={
                    "http_method": request.method,
                    "request_path": request.url.path,
                    "status_code": status_code,
                    "execution_time": execution_time,
                    "client_ip": client_ip,
                },
            )

            # Clean up context
            import app.core.context as ctx

            ctx.correlation_id_ctx_var.reset(req_token)
            ctx.user_id_ctx_var.reset(user_token)

        # Add X-Correlation-ID to response headers
        if "response" in locals():
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        # If response was never created (exception raised and not caught by outer
        # middleware), just let it bubble up, but this should not normally happen
        # in HTTP middleware.
