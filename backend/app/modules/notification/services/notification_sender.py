"""
`NotificationSender` -- the swappable-Protocol external-delivery
abstraction (`ENG-001`, AC2, Decision 7, `Plan_S12_ENG-001.md`), the
fifth application of this codebase's swappable-Protocol external-
integration pattern (`FileStorage`, `DocumentOcrService`,
`GooglePlacesClient`, `ConversationAiClient`, and now this one) --
narrower in scope than `identity.SmsSender`, which is OTP-code-specific
and stays untouched/unreused here (Decision 7's own "Alternatives
considered and rejected").

Delivery failures surface as typed, plain-Python exceptions -- never a
`BusinessException`/HTTP-mapped error, since a delivery failure must
never surface as an HTTP error response on the *triggering* request
(e.g. a WhatsApp outage must never fail a Contact View creation call).
`NotificationDeliveryService` (this module's own `notification_delivery_
service.py`) is the only caller expected to catch these.

Only stub implementations exist in this story (Decision 7) -- no real
WhatsApp/SMS/Email vendor integration is wired up; a real provider is
explicitly out of scope (see the Plan's "Explicitly Out of Scope"
section, `13_OPEN_DECISIONS.md` Open Question 5). Each stub always
succeeds -- no real vendor exists to fail against, so a stub that
pretends to fail would itself be a fabrication. Automated tests for the
"delivery failure surfaces as a typed error" half of AC2/AC8 use a
fake/spy `NotificationSender` that deliberately raises, exactly
mirroring how `AUTH-001`'s own OTP tests already verify `SmsSender`
failure handling via a fake, never by forcing the real stub to fail.
"""

import logging
import uuid
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationDeliveryError(Exception):
    """Base class for every typed `NotificationSender.send` failure."""


class WhatsAppDeliveryError(NotificationDeliveryError):
    """Raised when a WhatsApp delivery attempt fails."""


class SmsDeliveryError(NotificationDeliveryError):
    """Raised when an SMS delivery attempt fails."""


class EmailDeliveryError(NotificationDeliveryError):
    """Raised when an Email delivery attempt fails."""


class NotificationSender(ABC):
    """Abstract interface for dispatching one notification to one
    recipient over one external channel."""

    @abstractmethod
    async def send(
        self, *, recipient_user_id: uuid.UUID, title: str, body: str
    ) -> str | None:
        """
        Dispatch a notification to `recipient_user_id`.

        Returns an optional external provider message id on success.
        Raises a `NotificationDeliveryError` subclass on failure --
        never returns a falsy sentinel to signal failure.
        """
        raise NotImplementedError


class StubWhatsAppSender(NotificationSender):
    """Stub `NotificationSender` implementation. Never calls a real
    WhatsApp Business API provider -- always succeeds."""

    async def send(
        self, *, recipient_user_id: uuid.UUID, title: str, body: str
    ) -> str | None:
        logger.info(
            "Stub WhatsApp dispatch invoked for user %s (no real provider "
            "is called).",
            recipient_user_id,
        )
        return None


class StubSmsSender(NotificationSender):
    """Stub `NotificationSender` implementation. Never calls a real SMS
    provider -- always succeeds. Distinct from `identity.SmsSender`,
    which is narrowly scoped to OTP-code delivery (Decision 7's own
    "Alternatives considered and rejected")."""

    async def send(
        self, *, recipient_user_id: uuid.UUID, title: str, body: str
    ) -> str | None:
        logger.info(
            "Stub SMS dispatch invoked for user %s (no real provider is "
            "called).",
            recipient_user_id,
        )
        return None


class StubEmailSender(NotificationSender):
    """Stub `NotificationSender` implementation. Never calls a real
    email provider -- always succeeds."""

    async def send(
        self, *, recipient_user_id: uuid.UUID, title: str, body: str
    ) -> str | None:
        logger.info(
            "Stub Email dispatch invoked for user %s (no real provider is "
            "called).",
            recipient_user_id,
        )
        return None
