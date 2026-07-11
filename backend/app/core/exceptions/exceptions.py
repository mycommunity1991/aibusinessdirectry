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
