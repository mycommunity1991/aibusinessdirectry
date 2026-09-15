"""
Dependency-injection providers for the Notification module.

`ENG-001` (`Plan_S12_ENG-001.md`, Decisions 4/7/9) extends this module
with `notification_preferences`/`notification_delivery` wiring, plus
two documented `ADR-047` exceptions: `get_notification_preference_
service` constructs `customer.CustomerProfileRepository`/`customer.
CustomerPreferencesRepository` directly (leaf-repository construction,
no `customer.dependencies` import -- no side-effect-free `CustomerService`
read primitive exists for this purpose), and `get_notification_service`
constructs `identity.RoleRepository` directly (same reasoning, Decision
9's admin-broadcast lookup).
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.customer.models import NotificationChannel
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.notification.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.modules.notification.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from app.modules.notification.repositories.notification_repository import (
    NotificationRepository,
)
from app.modules.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.modules.notification.services.notification_preference_service import (
    NotificationPreferenceService,
)
from app.modules.notification.services.notification_sender import (
    NotificationSender,
    StubEmailSender,
    StubSmsSender,
    StubWhatsAppSender,
)
from app.modules.notification.services.notification_service import NotificationService


def get_notification_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRepository:
    """Provides a `NotificationRepository` bound to the request-scoped
    DB session."""
    return NotificationRepository(db)


def get_notification_preference_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferenceRepository:
    """Provides a `NotificationPreferenceRepository` bound to the
    request-scoped DB session (`ENG-001`, Decision 3)."""
    return NotificationPreferenceRepository(db)


def get_notification_preference_service(
    notification_preference_repository: Annotated[
        NotificationPreferenceRepository,
        Depends(get_notification_preference_repository),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferenceService:
    """
    Provides a `NotificationPreferenceService` bound to the
    request-scoped DB session. Constructs `customer.
    CustomerProfileRepository`/`customer.CustomerPreferencesRepository`
    **directly** here rather than importing `customer.dependencies` --
    a documented `ADR-047` exception (`ENG-001`, Decision 4/7): no
    side-effect-free `CustomerService` read primitive exists for a
    read-only "does this user have a customer profile, and if so what's
    their existing channel preference" lookup (`CustomerService.
    get_my_profile` auto-provisions a profile as a side effect, which
    would be wrong to trigger for a Provider/Admin account here).
    """
    return NotificationPreferenceService(
        notification_preference_repository,
        CustomerProfileRepository(db),
        CustomerPreferencesRepository(db),
    )


def get_notification_delivery_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationDeliveryRepository:
    """Provides a `NotificationDeliveryRepository` bound to the
    request-scoped DB session (`ENG-001`, Decision 3/8)."""
    return NotificationDeliveryRepository(db)


def get_notification_sender_registry() -> dict[NotificationChannel, NotificationSender]:
    """
    Provides the `dict[NotificationChannel, NotificationSender]`
    registry (`ENG-001`, Decision 7) -- mirrors `identity.dependencies.
    get_oauth_service`'s existing `{AuthProvider.GOOGLE: ..., AuthProvider.
    APPLE: ...}` dict-of-implementations shape exactly. Only stub
    implementations are wired up in this story -- no real WhatsApp/SMS/
    Email vendor integration exists yet.
    """
    return {
        NotificationChannel.WHATSAPP: StubWhatsAppSender(),
        NotificationChannel.SMS: StubSmsSender(),
        NotificationChannel.EMAIL: StubEmailSender(),
    }


def get_notification_delivery_service(
    notification_delivery_repository: Annotated[
        NotificationDeliveryRepository, Depends(get_notification_delivery_repository)
    ],
    sender_registry: Annotated[
        dict[NotificationChannel, NotificationSender],
        Depends(get_notification_sender_registry),
    ],
) -> NotificationDeliveryService:
    """Provides a `NotificationDeliveryService` bound to the
    request-scoped DB session (`ENG-001`, Decision 7/8)."""
    return NotificationDeliveryService(
        notification_delivery_repository, sender_registry
    )


def get_notification_service(
    notification_repository: Annotated[
        NotificationRepository, Depends(get_notification_repository)
    ],
    notification_preference_service: Annotated[
        NotificationPreferenceService, Depends(get_notification_preference_service)
    ],
    notification_delivery_service: Annotated[
        NotificationDeliveryService, Depends(get_notification_delivery_service)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    """
    Provides a `NotificationService` bound to the request-scoped DB
    session. Constructs `identity.RoleRepository` **directly** here
    rather than importing `identity.dependencies` -- a documented
    `ADR-047` exception (`ENG-001`, Decision 9): the only thing needed
    is `get_user_ids_for_role`, a single, business-logic-free read, with
    no equivalent lightweight identity Service to reach for.
    """
    return NotificationService(
        notification_repository,
        notification_preference_service,
        notification_delivery_service,
        RoleRepository(db),
    )
