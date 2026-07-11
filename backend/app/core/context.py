import contextvars

# Context variables for logging and tracking
correlation_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
user_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


def get_correlation_id() -> str | None:
    return correlation_id_ctx_var.get()


def get_user_id() -> str | None:
    return user_id_ctx_var.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    return correlation_id_ctx_var.set(correlation_id)


def set_user_id(user_id: str | None) -> contextvars.Token:
    return user_id_ctx_var.set(user_id)
