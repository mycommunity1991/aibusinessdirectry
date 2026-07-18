from app.shared.schemas.response import ErrorDetail


class BusinessException(Exception):  # noqa: N818
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        errors: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        self.headers = headers
        super().__init__(self.message)


class InvalidTokenError(BusinessException):
    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ExpiredTokenError(BusinessException):
    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticationRequiredError(BusinessException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidOtpError(BusinessException):
    """
    Raised whenever an OTP code cannot be verified — whether it is wrong,
    expired, already used, or simply doesn't exist for that phone number.

    Deliberately generic (AC5/AC10): the message never reveals which of
    those conditions applied, and never reveals whether the phone number
    is registered.
    """

    def __init__(
        self,
        message: str = "That code didn't work — check the digits and try again.",
    ):
        super().__init__(message=message, status_code=400)


class OtpLockedError(BusinessException):
    """Raised when an OTP has reached its maximum verification attempts."""

    def __init__(
        self,
        message: str = (
            "Too many incorrect attempts. Please request a new code and try again."
        ),
    ):
        super().__init__(message=message, status_code=429)


class RateLimitExceededError(BusinessException):
    """
    Raised when a client exceeds a Redis-backed fixed-window rate limit
    (`05_API_GUIDELINES.md`/`06_SECURITY.md` "Rate Limiting").

    Distinct in *meaning* from `OtpLockedError` (which caps wrong-code
    attempts against a single, already-issued OTP): this caps how fast a
    client can hit an endpoint at all. Both currently map to the same 429
    status code and a similarly plain-language message, by design —
    `06_SECURITY.md` requires generic, non-technical error copy either way.
    """

    def __init__(
        self,
        message: str = "Too many requests. Please wait a moment and try again.",
    ):
        super().__init__(message=message, status_code=429)
