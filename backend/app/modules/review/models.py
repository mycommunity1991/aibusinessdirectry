"""
Review domain model (`review` Postgres schema, REV-002).

See `docs/AI/04_DATABASE.md` (Review Domain) for the column-level source
of truth and `docs/implementation/plans/Plan_S09_REV-002.md` (Decision 1)
for the architecture decision behind this module -- a new, standalone
`review` module, not folded into `contact`, because it owns a genuinely
separate Postgres schema (unlike REV-001's `outcome_tags`, which shared
`contact`'s own schema).

`Review` is anchor-verified: it can only be written against a
`contact.contact_views` row carrying a "Yes" (`hired=True`)
`contact.outcome_tags` row -- enforced entirely at the service layer
(`ReviewService.submit_review`), since it requires reading
`outcome_tags.hired` at write time, not expressible as a single-table DB
`CHECK`. Because the anchoring Contact View is already rejected for
self-dealing at creation time (CON-001), a Review can never end up
pointing back at its own author's Provider (Decision 4). Immutable,
one-shot, mirroring `OutcomeTag`'s own precedent -- no update/deletion
path is ever exposed.

`ProviderRatingSummary` is the Review domain's own decoupled read-model
of the same aggregate `providers.average_rating`/`review_count` also
caches (Decision "item 14", `Plan_S09_REV-002.md`) -- both are written,
from the same computed values, in the same transaction, by
`ReviewService.submit_review`.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "review"
_CONTACT_SCHEMA = "contact"
_CUSTOMER_SCHEMA = "customer"
_PROVIDER_SCHEMA = "provider"


class Review(CommonColumnsMixin, Base):
    """
    One Review (REV-002, AC1) -- a 1:1, anchor-verified rating/comment
    tied to a specific `ContactView`. Only ever created via
    `ReviewService.submit_review`; no update/deletion path exists
    (mirrors `OutcomeTag`'s immutability precedent).
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("contact_view_id", name="uq_reviews_contact_view_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_reviews_rating_range"),
        Index("idx_reviews_provider_id", "provider_id"),
        {"schema": SCHEMA},
    )

    contact_view_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CONTACT_SCHEMA}.contact_views.id"),
        nullable=False,
        unique=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_CUSTOMER_SCHEMA}.customer_profiles.id"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProviderRatingSummary(CommonColumnsMixin, Base):
    """
    A Provider's denormalized rating aggregate (REV-002, AC4) -- recomputed
    in full (never incrementally, Decision 3) every time a Review is
    written for its `provider_id`, guarded by a row lock on the
    `providers` row (`ProviderService.lock_for_rating_recalculation`) so
    concurrent submissions for the same provider never produce a lost
    update.
    """

    __tablename__ = "provider_rating_summaries"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", name="uq_provider_rating_summaries_provider_id"
        ),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
        unique=True,
    )
    average_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("0")
    )
    review_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
