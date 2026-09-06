"""
Customer domain models (`customer` Postgres schema, CUS-001).

See `docs/AI/04_DATABASE.md` (Customer Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S03_CUS-001.md` for
the architecture decisions behind this module.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin
from app.modules.identity.models import LanguageCode

SCHEMA = "customer"
_IDENTITY_SCHEMA = "identity"


class NotificationChannel(StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


def _notification_channel_enum() -> SqlEnum:
    """Build the native Postgres ENUM type for `notification_channel`,
    colocated in the `customer` schema -- its first consumer anywhere in
    the codebase (Decision 2, `Plan_S03_CUS-001.md`)."""
    return SqlEnum(
        NotificationChannel,
        name="notification_channel",
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


def _identity_language_code_enum() -> SqlEnum:
    """
    Reuses the exact `identity.language_code` Postgres ENUM type already
    created by the identity-domain migration (Decision 2,
    `Plan_S03_CUS-001.md`) -- never a second, duplicate type. The
    canonical Python enum (`LanguageCode`) is imported from
    `identity.models`, not redefined here.
    """
    return SqlEnum(
        LanguageCode,
        name="language_code",
        schema=_IDENTITY_SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


class CustomerProfile(CommonColumnsMixin, Base):
    """
    A Customer's profile -- 1:1 with `identity.users` (Decision 5,
    `Plan_S03_CUS-001.md`: `GET`/`PATCH /customers/me` resolve this row
    exclusively from the caller's own `user_id`, never a client-supplied
    identifier).
    """

    __tablename__ = "customer_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_customer_profiles_user_id"),
        Index("idx_customer_profiles_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CustomerPreferences(CommonColumnsMixin, Base):
    """A Customer's preferences -- 1:1 with `customer_profiles`."""

    __tablename__ = "customer_preferences"
    __table_args__ = (
        UniqueConstraint("customer_id", name="uq_customer_preferences_customer_id"),
        Index("idx_customer_preferences_customer_id", "customer_id"),
        {"schema": SCHEMA},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.customer_profiles.id"),
        nullable=False,
    )
    notification_channel: Mapped[NotificationChannel] = mapped_column(
        _notification_channel_enum(),
        nullable=False,
        server_default=NotificationChannel.WHATSAPP.value,
    )
    language: Mapped[LanguageCode] = mapped_column(
        _identity_language_code_enum(),
        nullable=False,
        server_default=LanguageCode.EN.value,
    )
