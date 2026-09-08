"""
Provider domain models (`provider` Postgres schema, PRO-001).

See `docs/AI/04_DATABASE.md` (Provider Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S04_PRO-001.md` for
the architecture decisions behind this module.

Only `providers`, `business_profiles`, and `freelancer_profiles` are
created by this story -- `provider_availability`, `portfolios`, and
`service_areas` are PRO-002 scope and deliberately not modeled here.

`providers.category_label` is a genuine, flagged addition beyond
`04_DATABASE.md`'s literal `providers` spec (Decision 4,
`Plan_S04_PRO-001.md`): the Category domain (`category.categories`,
`provider_categories`) does not exist yet, so this free-text column is a
temporary stand-in for AC4's "category" field. Flagged for a
`04_DATABASE.md` follow-up update once the real Category domain ships.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "provider"
_IDENTITY_SCHEMA = "identity"


class ProviderType(StrEnum):
    BUSINESS = "business"
    FREELANCER = "freelancer"


class ListingSource(StrEnum):
    SELF_REGISTERED = "self_registered"
    GOOGLE_SEEDED_UNCLAIMED = "google_seeded_unclaimed"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


def _pg_enum(enum_cls: type[StrEnum], name: str) -> SqlEnum:
    """
    Build a native Postgres ENUM type colocated in the `provider` schema
    -- this is these three enums' first consumer anywhere in the
    codebase (mirrors `identity/models.py`'s `_pg_enum` pattern). Flagged
    in the migration for the future Verification-domain story
    (`verification_records.status`) to reuse `verification_status` via
    `create_type=False, schema="provider"` rather than duplicating it.
    """
    return SqlEnum(
        enum_cls,
        name=name,
        schema=SCHEMA,
        values_callable=lambda obj: [member.value for member in obj],
    )


class Provider(CommonColumnsMixin, Base):
    """
    The Provider aggregate root -- shared columns for both the Business
    and Freelancer subtypes (PRO-001). `user_id` is nullable at the
    column level to support Google-seeded unclaimed listings (a later
    story, Claim-Your-Listing) -- this story's only creation path
    (`ProviderService.create_provider`) always sets it to the caller's
    own id.

    `provider_type` is immutable after creation by construction: no
    `PATCH`/`PUT` endpoint for `providers` exists anywhere in this story
    (Decision 3, `Plan_S04_PRO-001.md`).
    """

    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_providers_slug"),
        Index(
            "uq_providers_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_providers_google_place_id",
            "google_place_id",
            unique=True,
            postgresql_where=text("google_place_id IS NOT NULL"),
        ),
        CheckConstraint(
            "is_claimed = false OR user_id IS NOT NULL",
            name="chk_providers_claimed_has_owner",
        ),
        Index("idx_providers_provider_type", "provider_type"),
        Index("idx_providers_is_discoverable", "is_discoverable"),
        Index("idx_providers_verification_status", "verification_status"),
        Index("idx_providers_country_code", "country_code"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_IDENTITY_SCHEMA}.users.id"),
        nullable=True,
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        _pg_enum(ProviderType, "provider_type"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    listing_source: Mapped[ListingSource] = mapped_column(
        _pg_enum(ListingSource, "listing_source"), nullable=False
    )
    is_claimed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        _pg_enum(VerificationStatus, "verification_status"),
        nullable=False,
        server_default=VerificationStatus.PENDING.value,
    )
    is_discoverable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    # Decision 4, `Plan_S04_PRO-001.md`: a flagged, temporary free-text
    # column standing in for the not-yet-built Category domain. Not in
    # `04_DATABASE.md`'s literal `providers` spec.
    category_label: Mapped[str] = mapped_column(String(100), nullable=False)


class BusinessProfile(CommonColumnsMixin, Base):
    """A Business Provider's subtype-specific details -- 1:1 with `providers`."""

    __tablename__ = "business_profiles"
    __table_args__ = (
        UniqueConstraint("provider_id", name="uq_business_profiles_provider_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    trade_license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_line: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    operating_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    delivery_radius_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FreelancerProfile(CommonColumnsMixin, Base):
    """A Freelancer Provider's subtype-specific details -- 1:1 with `providers`."""

    __tablename__ = "freelancer_profiles"
    __table_args__ = (
        UniqueConstraint("provider_id", name="uq_freelancer_profiles_provider_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    base_latitude: Mapped[float] = mapped_column(Double, nullable=False)
    base_longitude: Mapped[float] = mapped_column(Double, nullable=False)
    service_radius_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
