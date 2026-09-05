"""identity_email_uniqueness_per_provider

Revision ID: be1f79b6fa2a
Revises: 19249fb61ae8
Create Date: 2026-08-29 10:00:00.000000

Replaces `uq_users_email` (a global partial unique index on `email`
alone, `WHERE email IS NOT NULL`) with `uq_users_email_provider`, a
partial unique index scoped to `(auth_provider, email)`.

Required by AUTH-002 AC5: a different `auth_provider` presenting the
same email as an existing account must be able to create a second,
independent `User` row, which the old provider-agnostic constraint
blocked (a second row with the same email would fail the unique
constraint regardless of provider). See
`docs/implementation/plans/Plan_S02_AUTH-002.md` Decision 2.

`downgrade()` recreates the old global constraint; it will fail if the
target database already contains cross-provider duplicate emails at
that point (expected/acceptable for a dev rollback -- this migration is
not designed to be downgraded in an environment with live AUTH-002 data
present).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be1f79b6fa2a"
down_revision: str | Sequence[str] | None = "19249fb61ae8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "identity"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("uq_users_email", table_name="users", schema=SCHEMA)
    op.create_index(
        "uq_users_email_provider",
        "users",
        ["auth_provider", "email"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("email IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_users_email_provider", table_name="users", schema=SCHEMA)
    op.create_index(
        "uq_users_email",
        "users",
        ["email"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
