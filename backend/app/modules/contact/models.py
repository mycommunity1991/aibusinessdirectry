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

`OutcomeTag` (REV-001) is `contact_views`'s first anchored child --
the platform's only conversion signal, a minimal yes/no ("did you hire
them?") tied 1:1 to a specific Contact View. It lives in this same
module rather than a new standalone one (Decision 1,
`Plan_S09_REV-001.md`), mirroring the `administration` module's own
precedent of housing several aggregate roots, added incrementally by
different stories, in one Postgres schema/one Python module.
`visit_verifications` remains the one child still unbuilt.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, text
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


class OutcomeTag(CommonColumnsMixin, Base):
    """
    One Outcome Tag (REV-001, AC1) -- a minimal, immutable yes/no
    ("did you hire them?") tied 1:1 to a specific `ContactView`
    (`uq_outcome_tags_contact_view_id`). Only the Customer who owns the
    parent Contact View may submit this row (`OutcomeTagService`, AC2);
    no update/resubmission path is ever exposed (Decision 4,
    `Plan_S09_REV-001.md`) -- once written, this row never changes.
    """

    __tablename__ = "outcome_tags"
    __table_args__ = ({"schema": SCHEMA},)

    contact_view_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.contact_views.id"),
        nullable=False,
        unique=True,
    )
    hired: Mapped[bool] = mapped_column(Boolean, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
