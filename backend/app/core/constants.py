"""Centralized API prefixes and constants."""

API_PREFIX = "/api"
API_V1 = "/v1"

# Health status constants
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_UNHEALTHY = "unhealthy"
DB_STATUS_CONNECTED = "connected"
DB_STATUS_DISCONNECTED = "disconnected"

# Identity domain role names (seeded by
# app.modules.identity.services.seed_data.seed_roles)
ROLE_CUSTOMER = "customer"
ROLE_PROVIDER = "provider"
ROLE_ADMIN = "admin"

# OTP settings
OTP_CODE_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5

# Rate limiting (05_API_GUIDELINES.md "Rate Limiting" — Authentication)
AUTH_RATE_LIMIT_PER_MINUTE = 10
AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
