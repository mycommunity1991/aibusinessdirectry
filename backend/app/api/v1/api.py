from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.modules.contact.api import router as contact_router
from app.modules.conversation.api import router as conversation_router
from app.modules.customer.api import router as customer_router
from app.modules.identity.api import router as auth_router
from app.modules.provider.admin_claim_api import router as admin_claim_router
from app.modules.provider.api import router as provider_router
from app.modules.provider.claim_api import router as claim_router
from app.modules.provider.public_api import router as provider_public_router
from app.modules.search.admin_manual_match_api import (
    router as admin_manual_match_router,
)
from app.modules.search.api import router as search_router
from app.modules.search.search_request_api import router as search_request_router
from app.modules.verification.admin_api import router as admin_verification_router
from app.modules.verification.api import router as verification_router

v1_router = APIRouter()

# Include version 1 routers
v1_router.include_router(health_router, prefix="/health")
v1_router.include_router(auth_router, prefix="/auth")
v1_router.include_router(customer_router, prefix="/customers")
v1_router.include_router(provider_router, prefix="/providers")
v1_router.include_router(verification_router, prefix="/providers/me/verification")
v1_router.include_router(admin_verification_router, prefix="/admin/verification")
v1_router.include_router(search_router, prefix="/search")
v1_router.include_router(claim_router, prefix="/claims")
v1_router.include_router(admin_claim_router, prefix="/admin/claims")
v1_router.include_router(conversation_router, prefix="/conversations")
v1_router.include_router(search_request_router, prefix="/search-requests")
v1_router.include_router(
    admin_manual_match_router, prefix="/admin/search/manual-matches"
)
v1_router.include_router(contact_router, prefix="/contact-views")
# CON-001, Decision 2: registered *after* `provider_router` so `/me`,
# `/me/portfolio`, `/me/availability` continue to match their literal
# paths before this new `/{provider_id}` path-parameter route is ever
# reached (Starlette matches routes in registration order).
v1_router.include_router(provider_public_router, prefix="/providers")
