"""provider_discoverability_invariant

Revision ID: c415258bcde2
Revises: 04c69a216287
Create Date: 2026-09-08 15:00:00.000000

Adds `chk_providers_discoverable_requires_approved` to the existing
`provider.providers` table (VER-002, Decision 4,
`Plan_S05_VER-002.md`) -- a database-level defense-in-depth layer for
AC4's invariant: "a Freelancer's `is_discoverable` can never be true
while the latest `verification_records` status is anything other than
`approved`". Unconditional (applies to both Freelancer and Business
Providers, per Decision 5) -- a strictly stronger, always-true rule for
both subtypes, not a `provider_type`-conditional expression.

No column changes of any kind -- narrow, additive constraint-only
migration.

See `docs/AI/04_DATABASE.md` (Provider Domain, Constraints) and
`docs/implementation/plans/Plan_S05_VER-002.md`.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c415258bcde2"
down_revision: str | Sequence[str] | None = "04c69a216287"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "provider"
CONSTRAINT_NAME = "chk_providers_discoverable_requires_approved"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "providers",
        "is_discoverable = false OR verification_status = 'approved'",
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(CONSTRAINT_NAME, "providers", schema=SCHEMA, type_="check")
