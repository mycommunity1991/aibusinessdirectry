"""provider_average_rating_range_invariant

Revision ID: c3c4d5e6f7a8
Revises: b2b3c4d5e6f7
Create Date: 2026-09-14 11:00:00.000000

Adds `chk_providers_average_rating_range` to the existing `provider.
providers` table (REV-002, Decision 2, `Plan_S09_REV-002.md`) -- a
database-level defense-in-depth layer for the invariant "`average_rating`
is either unset or within the real 0-5 rating range", mirroring
`c415258bcde2_provider_discoverability_invariant`'s own precedent of a
small, single-purpose, separately-named migration for one flagged
invariant. `NULL` remains a valid value (a provider with zero reviews
has no average yet) -- only a non-null, out-of-range value is rejected.

`REV-002` is this column's actual first real writer (`ProviderService.
apply_rating_recalculation`) -- `04_DATABASE.md`'s existing note
attributing this gap to `REV-001` is a documentation slip, corrected at
this story's own closeout (`REV-001`'s own Plan explicitly scoped "any
change to `providers.average_rating`/`review_count`" out of its work).

No column changes of any kind -- narrow, additive constraint-only
migration.

See `docs/AI/04_DATABASE.md` (Provider Domain, Constraints) and
`docs/implementation/plans/Plan_S09_REV-002.md` (Decision 2).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "b2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "provider"
CONSTRAINT_NAME = "chk_providers_average_rating_range"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "providers",
        "average_rating IS NULL OR average_rating BETWEEN 0 AND 5",
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(CONSTRAINT_NAME, "providers", schema=SCHEMA, type_="check")
