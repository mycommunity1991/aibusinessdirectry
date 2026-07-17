# Rule: PostgreSQL earthdistance/cube Patterns

## Setup
* **Extensions Required:** `CREATE EXTENSION IF NOT EXISTS cube;` and `CREATE EXTENSION IF NOT EXISTS earthdistance;` must run in the same migration that first indexes a location column — never assume they're already enabled.
* **GiST Index Per Location Column:** Every table storing a queryable lat/long pair (`service_areas`, `saved_addresses`) gets its own `USING gist (ll_to_earth(latitude, longitude))` index.

## Querying
* **`earth_box` Before `earth_distance`:** Filter candidates with `earth_box(ll_to_earth(:lat, :lng), :radius_meters)` to use the index, then refine with `earth_distance()` only on the shortlisted rows — calling `earth_distance()` directly in a `WHERE` clause on the full table defeats the index.
* **Meters, Always:** Store and compare radii in meters throughout the codebase; never mix miles/km/meters across layers.
