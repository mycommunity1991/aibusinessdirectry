from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.modules.customer.api import router as customer_router
from app.modules.identity.api import router as auth_router

v1_router = APIRouter()

# Include version 1 routers
v1_router.include_router(health_router, prefix="/health")
v1_router.include_router(auth_router, prefix="/auth")
v1_router.include_router(customer_router, prefix="/customers")
