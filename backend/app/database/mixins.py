import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class CommonColumnsMixin:
    """
    Reusable base columns shared by every business-domain table.

    Per `docs/AI/04_DATABASE.md` "Common Columns" — every business table
    (i.e. every table except pure join/association tables and the
    append-only `audit.audit_logs`) includes these columns. This mixin is
    the pattern every future domain model must inherit from; it was
    established during the Identity domain migration (AUTH-001), the first
    business-domain schema in the project.

    Pure join tables (e.g. `role_permissions`, `user_roles`) do NOT use this
    mixin — they use a composite primary key and only `created_at`, since
    they represent a relationship rather than an independently-owned
    business record.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    @declared_attr
    def created_at(self) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True), nullable=False, server_default=text("now()")
        )

    @declared_attr
    def created_by(self) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("identity.users.id"),
            nullable=True,
        )

    @declared_attr
    def updated_at(self) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
            onupdate=text("now()"),
        )

    @declared_attr
    def updated_by(self) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("identity.users.id"),
            nullable=True,
        )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
