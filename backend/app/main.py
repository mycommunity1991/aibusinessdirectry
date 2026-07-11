from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions.handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.openapi import contact_info, license_info, tags_metadata
from app.middleware.logging_middleware import LoggingMiddleware

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the MyCommunity platform",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact=contact_info,
    license_info=license_info,
)

# Register Middleware
app.add_middleware(LoggingMiddleware)

# Register Exception Handlers
register_exception_handlers(app)

# Include root API router
app.include_router(api_router, prefix=settings.API_PREFIX)
