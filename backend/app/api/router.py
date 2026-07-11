from fastapi import APIRouter

from app.api.v1.api import v1_router
from app.core.constants import API_V1

# Root API router
api_router = APIRouter()

# Register API versions
api_router.include_router(v1_router, prefix=API_V1)
