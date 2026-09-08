"""
Exceptions package providing centralized error handling.
"""

from app.core.exceptions.exceptions import (
    AuthenticationRequiredError,
    BusinessException,
    ExpiredTokenError,
    InsufficientRoleError,
    InvalidIdentityTokenError,
    InvalidOtpError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    OtpLockedError,
    ProviderAlreadyExistsError,
    ProviderNotFoundError,
    RateLimitExceededError,
    SavedAddressNotFoundError,
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
    "InsufficientRoleError",
    "SavedAddressNotFoundError",
    "ProviderAlreadyExistsError",
    "ProviderNotFoundError",
]
