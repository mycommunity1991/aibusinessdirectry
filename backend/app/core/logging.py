import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.context import get_correlation_id, get_user_id


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    """

    def __init__(self, **kwargs: Any):
        super().__init__()
        self.sensitive_keys = {"password", "secret", "token", "jwt", "authorization"}

    def format(self, record: logging.LogRecord) -> str:
        # Standard required fields
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
            "user_id": get_user_id(),
        }

        # Handle exception information
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra attributes attached to the record
        # (excluding built-in LogRecord attributes)
        extra_attrs = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in logging.LogRecord(None, None, "", 0, "", (), None, None).__dict__
            and k not in ("message", "asctime")
        }

        # Apply sensitive data masking to extra attributes
        masked_extra = self._mask_sensitive_data(extra_attrs)
        log_entry.update(masked_extra)

        return json.dumps(log_entry)

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively mask sensitive data in dictionaries."""
        masked = {}
        for k, v in data.items():
            if any(sensitive_key in k.lower() for sensitive_key in self.sensitive_keys):
                masked[k] = "***MASKED***"
            elif isinstance(v, dict):
                masked[k] = self._mask_sensitive_data(v)
            else:
                masked[k] = v
        return masked


def setup_logging() -> None:
    """
    Configure the root logger for structured JSON logging.
    Prevents duplicate handlers and sets the log level.
    """
    root_logger = logging.getLogger()

    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Configure stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Prevent uvicorn access logs from duplicating if we are handling request logging
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False

    # Route default uvicorn logs through our root logger
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.propagate = True

    # Route fastapi logs
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.handlers.clear()
    fastapi_logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    """Helper to retrieve a logger instance."""
    return logging.getLogger(name)
