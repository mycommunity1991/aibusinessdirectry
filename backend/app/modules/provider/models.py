"""
Provider domain models (`provider` Postgres schema, PRO-001/PRO-002).

See `docs/AI/04_DATABASE.md` (Provider Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S04_PRO-001.md`/
`Plan_S04_PRO-002.md` for the architecture decisions behind this module.

PRO-002 adds `provider_availability`, `portfolios`, `service_areas`
(all exactly per `04_DATABASE.md`'s Provider Domain spec), and a new,
deliberately-not-`provider_categories`-named `provider_category_labels`
table (Decision 1, `Plan_S04_PRO-002.md`) -- a distinctly-named interim
stand-in so no future reader mistakes it for the real Category-domain
join table `04_DATABASE.md` already reserves that name for.
`Provider.category_label` (PRO-001, Decision 4) is removed in favor of
`ProviderCategoryLabel` rows.
"""

import uuid
from datetime import datetime, time
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
    Time,
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


class Weekday(StrEnum):
    """
    `04_DATABASE.md`'s `weekday` enum -- this table's (`provider_
    availability`) first consumer anywhere in the codebase (PRO-002),
    mirroring PRO-001's own enum-colocation precedent. Any future domain
    needing the same enum should reuse it via `create_type=False,
    schema="provider"` rather than duplicating it.
    """

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


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

    `chk_providers_discoverable_requires_approved` (VER-002, Decision 4,
    `Plan_S05_VER-002.md`) is a database-level defense-in-depth layer
    for the invariant "`is_discoverable` can never be true while
    `verification_status` is anything other than `approved`" -- kept in
    sync here with the migration that actually creates it
    (`provider_discoverability_invariant`), so the ORM model and the DB
    schema never drift apart.
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
        CheckConstraint(
            "is_discoverable = false OR verification_status = 'approved'",
            name="chk_providers_discoverable_requires_approved",
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


class ProviderAvailability(CommonColumnsMixin, Base):
    """
    A Provider's weekly operating hours, one row per weekday it has been
    configured for (PRO-002, AC3). `GET /providers/me/availability`
    synthesizes any missing weekday as a "closed, not yet configured"
    entry (Decision 3, `Plan_S04_PRO-002.md`) -- a day being closed is
    always expressed by `open_time`/`close_time` both `NULL`, never by a
    missing row for a weekday that *has* been explicitly saved as closed.
    """

    __tablename__ = "provider_availability"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "weekday",
            name="uq_provider_availability_provider_weekday",
        ),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    weekday: Mapped[Weekday] = mapped_column(
        _pg_enum(Weekday, "weekday"), nullable=False
    )
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_emergency_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class Portfolio(CommonColumnsMixin, Base):
    """
    A Provider's portfolio photo (PRO-002, AC2). `media_url` is always a
    server-generated, relative `/media/...` URL path -- never a raw
    filesystem path and never derived from the client's original
    filename (`06_SECURITY.md` File Upload Security). Soft-deleted on
    removal (Decision 5, `Plan_S04_PRO-002.md`) -- the on-disk file is
    left in place; only the row's `is_active`/`deleted_at` change.
    """

    __tablename__ = "portfolios"
    __table_args__ = (
        Index("idx_portfolios_provider_id", "provider_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    media_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )


class ServiceArea(CommonColumnsMixin, Base):
    """
    A Provider's derived service area (PRO-002) -- internal-only, kept in
    sync by `ProviderService` whenever the subtype profile's location/
    radius fields change (Decision, item 1, `Plan_S04_PRO-002.md`). No
    direct API exposes this table for editing or reading in this story;
    it exists for a future geospatial-matching story to query.

    DIR-001 (`Plan_S06_DIR-001.md`, AC1/Decision 8) is that story: it
    adds a GiST index over `ll_to_earth(center_latitude, center_
    longitude)` here (`idx_service_areas_location`) via migration only
    -- deliberately not modeled as an `Index()` in `__table_args__`
    below, since the index is a functional expression over an
    `earthdistance`-extension function (`ll_to_earth`) that must not be
    created by `Base.metadata.create_all()` (used by the test suite's
    `db_engine` fixture) before the `cube`/`earthdistance` extensions are
    enabled; the real migration handles ordering this correctly.
    `ProviderSearchRepository.search_nearby` is this index's query.
    """

    __tablename__ = "service_areas"
    __table_args__ = (
        Index("idx_service_areas_provider_id", "provider_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    center_latitude: Mapped[float] = mapped_column(Double, nullable=False)
    center_longitude: Mapped[float] = mapped_column(Double, nullable=False)
    radius_meters: Mapped[int] = mapped_column(Integer, nullable=False)


class ProviderCategoryLabel(CommonColumnsMixin, Base):
    """
    A free-text category label owned by a Provider (PRO-002, AC4;
    Decision 1, `Plan_S04_PRO-002.md`). Deliberately named distinctly
    from `provider_categories` -- the real join table `04_DATABASE.md`
    reserves that name for once the Category domain (`category.
    categories`) ships. "Exactly one primary" is enforced at the service
    layer (`ProviderCategoryLabelRepository.replace_all`, delete-then-
    insert, one flush) with `uq_provider_category_labels_primary` as a
    partial-unique-index backstop.
    """

    __tablename__ = "provider_category_labels"
    __table_args__ = (
        Index(
            "uq_provider_category_labels_primary",
            "provider_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
        ),
        Index("idx_provider_category_labels_provider_id", "provider_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.providers.id"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
