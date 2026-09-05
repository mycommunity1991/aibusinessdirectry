"""
Exceptions package providing centralized error handling.
"""

from app.core.exceptions.exceptions import (
    AuthenticationRequiredError,
    BusinessException,
    ExpiredTokenError,
    InvalidIdentityTokenError,
    InvalidOtpError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    OtpLockedError,
    RateLimitExceededError,
    SessionNotFoundError,
)

__all__ = [
    "BusinessException",
    "InvalidTokenError",
    "ExpiredTokenError",
    "AuthenticationRequiredError",
    "InvalidOtpError",
    "InvalidIdentityTokenError",
    "InvalidRefreshTokenError",
    "SessionNotFoundError",
    "OtpLockedError",
    "RateLimitExceededError",
]
