from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.core.app_state import AppState
from app.core.config import settings
from app.core.database.database import engine
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def validate_config() -> None:
    """
    Perform startup validation of the application configuration.
    Raises ValueError if critical settings are invalid or missing.
    """
    logger.info("Validating application configuration")

    # Secondary validation (since Pydantic already validates on import)
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL must be configured")

    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured")

    if settings.ENVIRONMENT not in ["development", "testing", "production"]:
        raise ValueError(f"Invalid environment: {settings.ENVIRONMENT}")


def verify_routes(app: FastAPI) -> None:
    """
    Verify that routers load correctly, API registration succeeds,
    and no duplicate routes exist.
    """
    logger.info("Verifying registered application routes")

    def get_all_routes(
        router_or_app: Any, current_prefix: str = ""
    ) -> list[tuple[str, set[str]]]:
        routes_list = []
        raw_routes = getattr(router_or_app, "routes", [])
        for route in raw_routes:
            if route.__class__.__name__ == "_IncludedRouter":
                sub_prefix = current_prefix + (route.include_context.prefix or "")
                routes_list.extend(get_all_routes(route.original_router, sub_prefix))
            elif hasattr(route, "path") and hasattr(route, "methods"):
                full_path = (current_prefix + route.path).replace("//", "/")
                if full_path != "/" and full_path.endswith("/"):
                    full_path = full_path.rstrip("/")
                routes_list.append((full_path, route.methods or {"GET"}))
        return routes_list

    all_routes = get_all_routes(app)
    if not all_routes:
        raise ValueError("No routes registered in the application")

    seen_routes = set()
    for path, methods in all_routes:
        for method in methods:
            route_key = (path, method.upper())
            if route_key in seen_routes:
                raise ValueError(f"Duplicate route detected: {method} {path}")
            seen_routes.add(route_key)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Handles application startup and shutdown events.
    """
    # Initialize structured logging
    setup_logging()

    # 1. Startup Process
    logger.info("Application starting")
    startup_successful = False
    try:
        # Validate configuration
        validate_config()

        # Initialize application state container
        app.state.services = AppState(
            db_engine=engine,
            redis_client=None,
            background_workers=None,
        )

        # Verify route registration and uniqueness
        verify_routes(app)

        logger.info("Startup completed")
        startup_successful = True
        yield

    except Exception as e:
        if not startup_successful:
            logger.error(f"Application startup failed: {e}")
            raise e
        else:
            # Re-raise exceptions occurring during application execution
            raise e

    finally:
        if startup_successful:
            # 2. Shutdown Process
            logger.info("Shutdown initiated")

            # Execute cleanup safely, continue even if one cleanup action fails
            # Log cleanup failures without masking other cleanup operations
            try:
                logger.info("Disposing database engine connection pool")
                if app.state.services.db_engine:
                    await app.state.services.db_engine.dispose()
                logger.info("Database engine connection pool disposed successfully")
            except Exception as db_err:
                logger.error(f"Failed to dispose database engine: {db_err}")

            # Future cleanup tasks can be added here

            logger.info("Shutdown completed")
