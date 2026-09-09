"""
Geospatial + category + discoverability provider search (DIR-001,
Decision 4/8, `Plan_S06_DIR-001.md`).

This is the codebase's first use of raw, parameterized SQL
(`sqlalchemy.text()`): `earth_box`/`earth_distance`/`ll_to_earth`
(`earthdistance` contrib-extension functions) have no SQLAlchemy Core/
ORM expression-language mapping. Every value a caller can influence
(`:category`, `:origin_lat`, `:origin_lng`, `:radius_meters`, `:limit`,
`:offset`) is a bound parameter -- never string-formatted or
concatenated -- satisfying `06_SECURITY.md`/`08_CODING_STANDARDS.md`'s
parameterized-query rule even though this is not expressed through the
ORM's Python-object query builder.

Lives inside the `provider` module, not `search` (Decision 4): the query
only ever touches `provider`-schema tables (`service_areas`,
`providers`, `provider_category_labels`), and
`02_ARCHITECTURE.md` prohibits a module reaching into another module's
repository/tables directly.

`_WHERE_CLAUSE`'s clause order is load-bearing, not cosmetic (AC2): the
category `EXISTS` subquery is evaluated first, then the GiST-indexed
`earth_box(...) @>` containment check (the clause `idx_service_areas_
location` actually accelerates), then the exact (index-incompatible)
`earth_distance(...) <= :radius_meters` recheck over the already-
narrowed candidate set, and only then `is_discoverable`/`is_active` on
`providers` -- a provider failing category or distance never even
reaches the discoverability check, and a provider passing both but not
discoverable is excluded regardless of fit. `ORDER BY distance_meters
ASC, p.id ASC` (AC7): distance-first, `id ASC` as the sole, fully
deterministic tie-break for two providers at an identical distance.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Decision 8's exact clause order -- read verbatim from
# `Plan_S06_DIR-001.md`. Shared, unmodified, between the row-fetching
# query and its matching `COUNT(*)` variant so the two can never drift
# out of sync with each other.
_WHERE_CLAUSE = """
    -- Category filter (Decision 1), applied first, only if :category is provided.
    -- `::text` disambiguates the parameter's type for the driver (`:category`
    -- otherwise appears for the first time in a bare `IS NULL` comparison,
    -- which psycopg/libpq cannot type-infer on its own) -- purely a binding
    -- concern, no change to the query's semantics or clause order (AC2):
    (CAST(:category AS text) IS NULL OR EXISTS (
        SELECT 1 FROM provider.provider_category_labels pcl
        WHERE pcl.provider_id = p.id
          AND pcl.is_active = true
          AND lower(pcl.label) = lower(:category)
    ))
    -- Geospatial radius: earth_box (GiST-indexed) BEFORE earth_distance (AC2):
    AND earth_box(ll_to_earth(:origin_lat, :origin_lng), :radius_meters)
        @> ll_to_earth(sa.center_latitude, sa.center_longitude)
    AND earth_distance(
            ll_to_earth(:origin_lat, :origin_lng),
            ll_to_earth(sa.center_latitude, sa.center_longitude)
        ) <= :radius_meters
    -- Discoverability gate, applied last (AC2):
    AND p.is_discoverable = true
    AND p.is_active = true
"""

_SEARCH_NEARBY_SQL = text(
    f"""
    SELECT
        sa.provider_id,
        earth_distance(
            ll_to_earth(:origin_lat, :origin_lng),
            ll_to_earth(sa.center_latitude, sa.center_longitude)
        ) AS distance_meters
    FROM provider.service_areas sa
    JOIN provider.providers p ON p.id = sa.provider_id
    WHERE
    {_WHERE_CLAUSE}
    ORDER BY distance_meters ASC, p.id ASC
    LIMIT :limit OFFSET :offset
    """
)

_COUNT_NEARBY_SQL = text(
    f"""
    SELECT COUNT(*) AS total_items
    FROM provider.service_areas sa
    JOIN provider.providers p ON p.id = sa.provider_id
    WHERE
    {_WHERE_CLAUSE}
    """
)


class ProviderSearchRepository:
    """
    A dedicated repository for the structured-search query (DIR-001,
    Decision 4) -- deliberately separate from `ProviderRepository`'s
    simple CRUD methods, since this query is genuinely complex (raw
    parameterized SQL, multi-table join, pagination, ordering) and
    deserves isolation (`08_CODING_STANDARDS.md`'s "small, focused"
    class-design principle). Does not subclass `BaseRepository`: it has
    no single owning model, and none of `BaseRepository`'s generic CRUD
    methods apply to a read-only, multi-table, raw-SQL query.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search_nearby(
        self,
        *,
        category: str | None,
        origin_lat: float,
        origin_lng: float,
        radius_meters: float,
        limit: int,
        offset: int,
    ) -> tuple[list[uuid.UUID], dict[uuid.UUID, float], int]:
        """
        Returns `(ordered_provider_ids, provider_id -> distance_meters,
        total_items)` for the given filters -- `ordered_provider_ids`
        preserves the query's own `distance_meters ASC, id ASC` order
        (AC7); `total_items` is a matching, unpaginated `COUNT(*)` over
        the identical `WHERE` clause, for `PaginationMeta.total_items`.
        """
        params = {
            "category": category,
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
            "radius_meters": radius_meters,
        }

        count_result = await self.session.execute(_COUNT_NEARBY_SQL, params)
        total_items = count_result.scalar_one()

        rows_result = await self.session.execute(
            _SEARCH_NEARBY_SQL, {**params, "limit": limit, "offset": offset}
        )
        rows = rows_result.all()

        ordered_ids = [row.provider_id for row in rows]
        distances_by_id = {row.provider_id: float(row.distance_meters) for row in rows}
        return ordered_ids, distances_by_id, total_items
