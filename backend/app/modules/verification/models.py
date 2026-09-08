"""
Verification domain models (`verification` Postgres schema, VER-001).

See `docs/AI/04_DATABASE.md` (Verification Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S05_VER-001.md` for
the architecture decisions behind this module.

`VerificationRecord.status` reuses (never duplicates) the existing
`provider.verification_status` Postgres enum type (Decision 1) --
`VerificationStatus` itself is imported directly from
`app.modules.provider.models`, a pure value-enum import (the same shape
ADR-014 already established for `customer` reusing
`identity.models.LanguageCode`), not a service/repository coupling.
`VerificationType`/`DocumentType` are genuinely new enums, colocated in
this `verification` schema, mirroring `provider/models.py`'s own
`_pg_enum` colocation convention.

This module never defines a column on, or a foreign key *from*, the
`providers` table itself (Decision 2) -- `VerificationRecord.provider_id`
is the only link, a foreign key *to* `provider.providers.id`.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin
from app.modules.provider.models import VerificationStatus

SCHEMA = "verification"
_PROVIDER_SCHEMA = "provider"
_IDENTITY_SCHEMA = "identity"


class VerificationType(StrEnum):
    FREELANCER_ID = "freelancer_id"
    BUSINESS_LICENSE = "business_license"
    BUSINESS_LIGHTWEIGHT = "business_lightweight"


class DocumentType(StrEnum):
    EMIRATES_ID = "emirates_id"
    TRADE_LICENSE = "trade_license"
    OTHER = "other"


def _pg_enum(enum_cls: type[StrEnum], name: str) -> SqlEnum:
    """
    Build a native Postgres ENUM type colocated in the `verification`
    schema -- mirrors `provider/models.py`'s `_pg_enum` pattern, for the
    two genuinely new enums this module owns (`verification_type`,
    `document_type`).
    """
    return SqlEnum(
        enum_cls,
        name=name,
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


def _reused_verification_status_enum() -> SqlEnum:
    """
    References (never duplicates) the existing `provider.verification_
    status` Postgres enum type (Decision 1) -- already created once, by
    `provider/models.py`'s own `Provider.verification_status` column.
    `create_type=False` here (mirroring the migration's own
    `create_type=False, schema="provider"`) so `Base.metadata.create_all()`
    (the test suite's table-creation path, `tests/conftest.py`) never
    attempts a second `CREATE TYPE` for the same Postgres type.
    """
    return SqlEnum(
        VerificationStatus,
        name="verification_status",
        schema=_PROVIDER_SCHEMA,
        create_type=False,
        values_callable=lambda obj: [member.value for member in obj],
    )


class VerificationRecord(CommonColumnsMixin, Base):
    """
    One verification cycle for a Provider (VER-001). A Provider may
    accumulate many of these over time (1:N) -- resubmission after a
    rejection always **creates** a new row, never **updates** an
    existing one (AC7, Decision 4), so history is preserved by
    construction. `status` defaults to `pending` and is never mutated by
    any code this story adds (Decision 2) -- no `PATCH`/`PUT` endpoint of
    any kind exists in this module.
    """

    __tablename__ = "verification_records"
    __table_args__ = (
        Index("idx_verification_records_provider_id", "provider_id"),
        Index("idx_verification_records_status", "status"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
    )
    verification_type: Mapped[VerificationType] = mapped_column(
        _pg_enum(VerificationType, "verification_type"), nullable=False
    )
    status: Mapped[VerificationStatus] = mapped_column(
        _reused_verification_status_enum(),
        nullable=False,
        server_default=VerificationStatus.PENDING.value,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class VerificationDocument(CommonColumnsMixin, Base):
    """
    A document (Emirates ID scan, trade license, etc.) attached to a
    `VerificationRecord` (VER-001). `file_url` is a stored file
    reference, never the file itself (`04_DATABASE.md`) -- and, unlike
    `Portfolio.media_url`, never a public `/media/...` URL (Decision 7):
    it is either a bare storage-relative reference (private
    `LocalFileStorage`) or, at the API response layer, replaced entirely
    by an authenticated `file_download_url` pointing at this module's own
    streaming endpoint. `ocr_extracted_data` stores the user's
    **submitted, confirmed** fields (AC8), not the OCR stub's raw output.
    """

    __tablename__ = "verification_documents"
    __table_args__ = (
        Index("idx_verification_documents_record_id", "verification_record_id"),
        {"schema": SCHEMA},
    )

    verification_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.verification_records.id"),
        nullable=False,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        _pg_enum(DocumentType, "document_type"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
