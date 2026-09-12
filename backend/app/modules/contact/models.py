"""
Contact domain model (`contact` Postgres schema, CON-001).

See `docs/AI/04_DATABASE.md` (Contact Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S08_CON-001.md`
(Decision 1/5) for the architecture decisions behind this module.

`ContactView` is the platform's replacement for a staged Quote/approval
flow: a Contact View row is created the instant a customer taps Contact
on a matched provider, and its own creation is what reveals the
provider's phone number (never a separate, later approval step). Full
`CommonColumnsMixin` (versioned, soft-deletable), mirroring every other
ordinary business table in this codebase -- `04_DATABASE.md`'s Soft
Delete section names only `audit_logs`/`search_event_log` as exempt.

Deliberately **no** uniqueness constraint on `(customer_id,
provider_id)` (Decision 5) -- every successful Contact View creation is
its own row, since a customer genuinely re-contacting the same provider
weeks later for a different job is a real, separately meaningful
analytics event, not a duplicate to collapse.

This module has no `outcome_tags`/`visit_verifications` model yet --
both are explicitly out of this story's scope, even though
`04_DATABASE.md` already documents them as `contact_views`'s future
children.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "contact"
_CUSTOMER_SCHEMA = "customer"
_PROVIDER_SCHEMA = "provider"
_SEARCH_SCHEMA = "search"


class ContactView(CommonColumnsMixin, Base):
    """
    One Contact View (CON-001, AC1) -- created the instant a customer's
    Contact tap is accepted (`ContactService.create_contact_view`), the
    sole event this story's self-dealing guard (Decision 1) protects.
    """

    __tablename__ = "contact_views"
    __table_args__ = (
        Index("idx_contact_views_customer_id", "customer_id"),
        Index("idx_contact_views_provider_id", "provider_id"),
        Index("idx_contact_views_viewed_at", "viewed_at"),
        {"schema": SCHEMA},
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
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SEARCH_SCHEMA}.search_requests.id"),
        nullable=True,
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
