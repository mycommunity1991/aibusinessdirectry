"""
Category domain model (`category` Postgres schema, CTG-001).

See `docs/AI/04_DATABASE.md` (Category Domain) for the column-level
source of truth and `docs/implementation/plans/Plan_S07_CTG-001.md`
(Decisions 1, 3) for the architecture decisions behind this module.

`02_ARCHITECTURE.md` names "Category" as its own Core Business Module,
a peer of Identity/Customer/Provider/Conversation -- this module is
this domain's first slice: `Category` and `CategoryQuestionTemplate`
are ordinary, fully-`CommonColumnsMixin` business tables;
`ProviderCategory` is a pure join/association table (composite PK,
`created_at` only), mirroring `identity`'s `RolePermission`/`UserRole`
join-table shape. `ProviderCategory` is created empty by this story's
migration -- reconciling `provider.provider_category_labels` into it is
explicitly out of scope (see `seed_data.py`'s module docstring and
`Plan_S07_CTG-001.md`).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import CommonColumnsMixin

SCHEMA = "category"
_PROVIDER_SCHEMA = "provider"


class Category(CommonColumnsMixin, Base):
    """
    A category in the v1 launch taxonomy (`17_CATEGORY_TAXONOMY.md`),
    seeded by the `category_domain` migration. Flat for v1 --
    `parent_category_id` is `NULL` for every seeded row, reserved for a
    future sub-category shape without a schema change.
    """

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_categories_slug"),
        {"schema": SCHEMA},
    )

    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.categories.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )


class CategoryQuestionTemplate(CommonColumnsMixin, Base):
    """
    One AI follow-up question template belonging to a `Category`
    (`17_CATEGORY_TAXONOMY.md`'s per-category question sets). `options`
    is JSONB -- a choice list for `single_select`/`multi_select`
    questions, `NULL` for `text`/`boolean`/`number` questions.
    """

    __tablename__ = "category_question_templates"
    __table_args__ = (
        Index("idx_category_question_templates_category_id", "category_id"),
        {"schema": SCHEMA},
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.categories.id"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)
    question_text_ar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    options: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )


class ProviderCategory(Base):
    """
    Pure join table: a Provider belongs to one or more Categories
    (`03_DOMAIN_MODEL.md`). Composite PK + `created_at` only, mirroring
    `identity.role_permissions`/`identity.user_roles`'s established
    join-table shape (`CommonColumnsMixin`'s own docstring exempts pure
    join/association tables from the full common-columns set).

    Created empty by this story's migration -- no repository/service
    writes to this table in CTG-001; reconciling
    `provider.provider_category_labels` into real rows here is a
    deliberately deferred follow-up story (`13_OPEN_DECISIONS.md`
    item 1).
    """

    __tablename__ = "provider_categories"
    __table_args__ = (
        PrimaryKeyConstraint(
            "provider_id", "category_id", name="pk_provider_categories"
        ),
        Index("idx_provider_categories_category_id", "category_id"),
        {"schema": SCHEMA},
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_PROVIDER_SCHEMA}.providers.id"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.categories.id"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
