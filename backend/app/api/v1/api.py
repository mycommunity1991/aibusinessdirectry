from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router

v1_router = APIRouter()

# Include version 1 routers
v1_router.include_router(health_router, prefix="/health")
