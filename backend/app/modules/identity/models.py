"""
Identity domain models (`identity` Postgres schema).

Covers the AUTH-001 scope: `users`, `roles`, `permissions`,
`role_permissions`, `user_roles`, `devices`, and `otp_verifications`.
See `docs/AI/04_DATABASE.md` (Identity Domain) for the column-level source
of truth and `docs/implementation/plans/Plan_S02_AUTH-001.md` for the
architecture decisions behind this module (first domain migration —
establishes the mixin/enum/schema conventions every later domain reuses).

`sessions`/`refresh_tokens` are intentionally NOT defined here — they
belong to AUTH-003.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "identity"


def _pg_enum(enum_cls: type[StrEnum], name: str) -> SqlEnum:
    """Build a native Postgres ENUM type colocated in the identity schema."""
    return SqlEnum(
        enum_cls,
        name=name,
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class AuthProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
    MOBILE_OTP = "mobile_otp"
    EMAIL_PASSWORD = "email_password"


class DevicePlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"


class LanguageCode(StrEnum):
    EN = "en"
    AR = "ar"


class OtpPurpose(StrEnum):
    REGISTRATION = "registration"
    LOGIN = "login"
    ARRIVAL_VERIFICATION = "arrival_verification"
    CLAIM_LISTING = "claim_listing"


class User(CommonColumnsMixin, Base):
    """An Account — the single identity record shared across Customer and
    Provider roles (dual-role rule, see `03_DOMAIN_MODEL.md`)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR phone_number IS NOT NULL "
            "OR external_auth_subject IS NOT NULL",
            name="chk_users_has_identifier",
        ),
        Index(
            "uq_users_email",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
        Index(
            "uq_users_phone",
            "phone_country_code",
            "phone_number",
            unique=True,
            postgresql_where=text("phone_number IS NOT NULL"),
        ),
        Index(
            "uq_users_external_auth",
            "auth_provider",
            "external_auth_subject",
            unique=True,
            postgresql_where=text("external_auth_subject IS NOT NULL"),
        ),
        Index("idx_users_email", "email"),
        Index("idx_users_phone_number", "phone_number"),
        Index("idx_users_status", "status"),
        {"schema": SCHEMA},
    )

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        _pg_enum(AuthProvider, "auth_provider"), nullable=False
    )
    external_auth_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[UserStatus] = mapped_column(
        _pg_enum(UserStatus, "user_status"),
        nullable=False,
        server_default=UserStatus.ACTIVE.value,
    )
    preferred_language: Mapped[LanguageCode] = mapped_column(
        _pg_enum(LanguageCode, "language_code"),
        nullable=False,
        server_default=LanguageCode.EN.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Role(CommonColumnsMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_roles_name"),
        {"schema": SCHEMA},
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Permission(CommonColumnsMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_permissions_code"),
        {"schema": SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RolePermission(Base):
    """Pure join table: role_permissions. Composite PK + created_at only."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        {"schema": SCHEMA},
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.roles.id"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.permissions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class UserRole(Base):
    """Pure join table: user_roles. Composite PK + created_at only."""

    __tablename__ = "user_roles"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.users.id"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.roles.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Device(CommonColumnsMixin, Base):
    """A user's device. Table created by this story; not yet populated —
    session/device tracking is AUTH-003."""

    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_devices_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.users.id"), nullable=False
    )
    platform: Mapped[DevicePlatform] = mapped_column(
        _pg_enum(DevicePlatform, "device_platform"), nullable=False
    )
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_trusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OtpVerification(CommonColumnsMixin, Base):
    """Reused across every OTP use case in the product (registration/login,
    arrival-verification, claim-listing) — not one-off tables per feature."""

    __tablename__ = "otp_verifications"
    __table_args__ = (
        Index("idx_otp_verifications_phone", "phone_country_code", "phone_number"),
        Index("idx_otp_verifications_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.users.id"), nullable=True
    )
    phone_country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(
        _pg_enum(OtpPurpose, "otp_purpose"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
