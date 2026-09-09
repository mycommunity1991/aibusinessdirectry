"""enable_geospatial_extensions_and_indexes

Revision ID: a3f6e9c21d47
Revises: c415258bcde2
Create Date: 2026-09-09 09:00:00.000000

DIR-001 (`Plan_S06_DIR-001.md`, Decision 8/Decision 9, AC1): enables the
`cube`/`earthdistance` Postgres contrib extensions and adds the two GiST
indexes `04_DATABASE.md` Section 13 already specifies -- the search
domain's first migration, and the first migration in this codebase that
supports a raw, `earth_box`/`earth_distance`-based geospatial query.

`idx_service_areas_location` (`provider.service_areas`) is this story's
own query's index -- `ProviderSearchRepository.search_nearby` is the
first, and so far only, consumer. `idx_saved_addresses_location`
(`customer.saved_addresses`) is AC1's explicit, literal requirement even
though this story's own query never reads through `saved_addresses` at
all (Decision 5) -- a forward-looking parity index for a future
`saved_addresses`-centered geospatial query, built now so that future
story needs no second migration.

Both indexes index `ll_to_earth(latitude, longitude)` -- a functional
GiST index -- so `CREATE EXTENSION IF NOT EXISTS cube;`/`earthdistance;`
must run first in this same migration, before either `CREATE INDEX`
statement, since `ll_to_earth` is an `earthdistance`-extension function.

`downgrade()` deliberately drops only the two indexes it created, never
the extensions themselves (Decision, Migrations section,
`Plan_S06_DIR-001.md`) -- extensions are shared, database-wide objects;
dropping them on a downgrade risks breaking any other index/query that
might come to depend on them later, for no real benefit (leaving an
unused, idempotently-`IF NOT EXISTS`-created extension enabled carries
no meaningful risk).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f6e9c21d47"
down_revision: str | Sequence[str] | None = "c415258bcde2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROVIDER_SCHEMA = "provider"
CUSTOMER_SCHEMA = "customer"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS cube")
    op.execute("CREATE EXTENSION IF NOT EXISTS earthdistance")

    op.execute(
        f"CREATE INDEX idx_service_areas_location ON {PROVIDER_SCHEMA}.service_areas "
        "USING gist (ll_to_earth(center_latitude, center_longitude))"
    )
    op.execute(
        f"CREATE INDEX idx_saved_addresses_location ON {CUSTOMER_SCHEMA}.saved_addresses "
        "USING gist (ll_to_earth(latitude, longitude))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"DROP INDEX IF EXISTS {CUSTOMER_SCHEMA}.idx_saved_addresses_location"
    )
    op.execute(
        f"DROP INDEX IF EXISTS {PROVIDER_SCHEMA}.idx_service_areas_location"
    )
