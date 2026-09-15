"""notification_preferences_and_delivery

Revision ID: 1d2b4636e621
Revises: f4a8c1d9e6b3
Create Date: 2026-09-15 12:00:00.000000

`ENG-001` (Sprint 12, Decision 3, `Plan_S12_ENG-001.md`) -- closes the
two genuine table gaps `VER-002`'s own migration (`04c69a216287_
notification_domain.py`) flagged as "remain unbuilt", plus one
`ALTER TABLE` on the already-shipped `notifications` table:

- `ALTER TABLE notification.notifications ADD COLUMN read_at
  TIMESTAMPTZ NULL` -- this codebase's first column-addition-to-an-
  existing-table migration. `NULL` = unread ("New"), a real timestamp =
  read ("Earlier"), set once by `PATCH /notifications/{id}/read`.
- `CREATE TABLE notification.notification_preferences` -- per-user
  channel/category preferences. `channel` reuses the already-existing
  `customer.notification_channel` Postgres enum type (`create_type=
  False`), mirroring `35cd57521089_customer_domain.py`'s own identical
  `language_code` cross-schema reuse of `identity.language_code` --
  never a second, duplicate enum type. `channel_enabled` is a genuine
  addition beyond `04_DATABASE.md`'s original pre-written spec (Decision
  3): the reused enum has no "off" value, so a separate boolean is
  needed to express AC4's "a disabled channel... is a hard stop".
- `CREATE TABLE notification.notification_delivery` -- one row per
  delivery attempt. `channel` reuses the same `customer.
  notification_channel` enum. `idempotency_key` is the other genuine
  addition beyond the original spec (Decision 3/8) -- AC7's "duplicate
  sends are prevented via an idempotency key on retry" is not
  satisfiable without a persisted, uniquely-constrained key to conflict
  on.

See `docs/AI/04_DATABASE.md` (Notification Domain) and
`docs/implementation/plans/Plan_S12_ENG-001.md` (Decisions 3/4/8).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d2b4636e621"
down_revision: str | Sequence[str] | None = "f4a8c1d9e6b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "notification"
IDENTITY_SCHEMA = "identity"
CUSTOMER_SCHEMA = "customer"


def _notification_channel_enum() -> postgresql.ENUM:
    """
    Reuses the exact `customer.notification_channel` Postgres enum type
    already created by `35cd57521089_customer_domain.py`
    (`create_type=False` -- Decision 4, `Plan_S12_ENG-001.md`) -- never
    a second, duplicate type.
    """
    return postgresql.ENUM(
        "whatsapp",
        "sms",
        "email",
        name="notification_channel",
        schema=CUSTOMER_SCHEMA,
        create_type=False,
    )


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` -- mirrors every prior domain
    migration's own identically-named helper."""
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "notifications",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    # --- notification_preferences -------------------------------------
    op.create_table(
        "notification_preferences",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "channel",
            _notification_channel_enum(),
            nullable=False,
            server_default="whatsapp",
        ),
        sa.Column(
            "channel_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "leads_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "verification_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "outcome_prompts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.UniqueConstraint(
            "user_id", name="uq_notification_preferences_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notification_preferences_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notification_preferences_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notification_preferences_updated_by",
        ),
        schema=SCHEMA,
    )

    # --- notification_delivery ------------------------------------------
    op.create_table(
        "notification_delivery",
        *_common_columns(),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", _notification_channel_enum(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_notification_delivery_idempotency_key"
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            [f"{SCHEMA}.notifications.id"],
            name="fk_notification_delivery_notification_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notification_delivery_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{IDENTITY_SCHEMA}.users.id"],
            name="fk_notification_delivery_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_notification_delivery_notification_id",
        "notification_delivery",
        ["notification_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("notification_delivery", schema=SCHEMA)
    op.drop_table("notification_preferences", schema=SCHEMA)
    op.drop_column("notifications", "read_at", schema=SCHEMA)
