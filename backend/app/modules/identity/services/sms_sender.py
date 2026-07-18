"""
SMS delivery abstraction for OTP codes.

`SmsSender` is the seam the rest of the codebase depends on; a real
provider (Twilio, AWS SNS, etc.) will implement it in a later story.
`ConsoleSmsSender` is the only implementation wired up in this story
(AUTH-001, AC4) — it never calls a real provider and never logs the raw
OTP code at INFO/WARNING/ERROR level (`06_SECURITY.md` — never log
secrets).
"""

import logging
from abc import ABC, abstractmethod

from app.core.config import Environment, settings

logger = logging.getLogger(__name__)


class SmsSender(ABC):
    """Abstract interface for dispatching an SMS OTP code to a phone number."""

    @abstractmethod
    async def send(self, phone_country_code: str, phone_number: str, code: str) -> None:
        """
        Dispatch an OTP code via SMS.

        Args:
            phone_country_code: E.g. "+971".
            phone_number: The subscriber number, without the country code.
            code: The plain text OTP code to deliver.
        """
        raise NotImplementedError


class ConsoleSmsSender(SmsSender):
    """
    Stub `SmsSender` implementation. Never calls a real SMS provider.

    The OTP code itself is only ever surfaced at DEBUG level, and only
    outside production, as an explicitly-labelled local development aid —
    it is never logged at INFO/WARNING/ERROR (`06_SECURITY.md`). Automated
    tests should assert behavior via a fake/spy `SmsSender`, not by
    reading logs.
    """

    async def send(self, phone_country_code: str, phone_number: str, code: str) -> None:
        logger.info(
            "Stub SMS dispatch invoked for %s%s (no real provider is called).",
            phone_country_code,
            phone_number,
        )
        if settings.ENVIRONMENT != Environment.PRODUCTION:
            logger.debug(
                "[STUB SMS — local development only, never a real provider] "
                "OTP code for %s%s: %s",
                phone_country_code,
                phone_number,
                code,
            )
