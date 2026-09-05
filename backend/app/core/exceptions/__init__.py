"""
Exceptions package providing centralized error handling.
"""

from app.core.exceptions.exceptions import (
    AuthenticationRequiredError,
    BusinessException,
    ExpiredTokenError,
    InvalidIdentityTokenError,
    InvalidOtpError,
    InvalidTokenError,
    OtpLockedError,
    RateLimitExceededError,
)

__all__ = [
    "BusinessException",
    "InvalidTokenError",
    "ExpiredTokenError",
    "AuthenticationRequiredError",
    "InvalidOtpError",
    "InvalidIdentityTokenError",
    "OtpLockedError",
    "RateLimitExceededError",
]
