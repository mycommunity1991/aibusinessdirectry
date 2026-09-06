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


class InvalidIdentityTokenError(BusinessException):
    """
    Raised whenever a Google/Apple ID token cannot be verified -- whether
    the signature, issuer, audience, or expiry check failed, the token
    was malformed, or the provider's JWKS could not be fetched.

    Deliberately generic (AC6, AUTH-002): the message never reveals which
    of those conditions applied, mirroring `InvalidOtpError`'s
    non-revealing design.
    """

    def __init__(
        self,
        message: str = "We couldn't verify your sign-in. Please try again.",
    ):
        super().__init__(message=message, status_code=401)


class InvalidRefreshTokenError(BusinessException):
    """
    Raised whenever a refresh token cannot be used to mint a new
    access/refresh pair -- whether it doesn't exist, is expired, was
    already revoked, or was already rotated away and is being replayed
    (AUTH-003, AC5).

    Deliberately generic, mirroring `InvalidOtpError`/
    `InvalidIdentityTokenError`'s non-revealing design: the message never
    reveals which of those conditions applied.
    """

    def __init__(
        self,
        message: str = "That session could not be refreshed. Please sign in again.",
    ):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class SessionNotFoundError(BusinessException):
    """
    Raised by `DELETE /auth/sessions/{id}` (and any other session lookup)
    when a session either doesn't exist at all, or exists but is not
    owned by the requesting user (AUTH-003, AC8/AC10).

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- consistent with this project's existing
    non-revealing-error philosophy (Decision 9,
    `Plan_S02_AUTH-003.md`).
    """

    def __init__(self, message: str = "Session not found."):
        super().__init__(message=message, status_code=404)


class InsufficientRoleError(BusinessException):
    """
    Raised by `require_role()` (AUTH-004, AC3) when a caller is
    authenticated (a valid, unexpired token was already accepted by
    `get_current_user`) but their `roles` claim does not intersect the
    endpoint's allowed set.

    Deliberately distinct from every 401 exception above: this is only
    ever raised for a *validly authenticated* caller, so 401 and 403 are
    never used interchangeably (AC2/AC3). Deliberately generic -- never
    reveals which role(s) were required, mirroring this project's
    established non-revealing-error philosophy.
    """

    def __init__(
        self,
        message: str = "You don't have permission to perform this action.",
    ):
        super().__init__(message=message, status_code=403)


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
