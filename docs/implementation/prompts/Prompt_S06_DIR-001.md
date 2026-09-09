# Implementation Prompt — Story DIR-001

**Sprint:** 06 (Directory & Listing Claims) | **Story:** DIR-001 — Browse Nearby Providers by Category and
Location | **Plan:** `docs/implementation/plans/Plan_S06_DIR-001.md` (read in full before starting — this prompt
is a pointer to it, not a replacement for it)

---

## Task

Implement Story DIR-001 exactly per `docs/implementation/plans/Plan_S06_DIR-001.md`. Read
`app/.agents/agents.md` and the `docs/AI/` documents that Plan's "Related Documents" section names before writing
any code.

## Story Summary

As a customer, browse providers by category and distance without the AI conversation — a structured,
non-conversational directory backed by `cube`/`earthdistance` geospatial indexing and the existing
discoverability gate (VER-002). Simpler than the future AI-ranked results (MAT-001); exists to ship discovery
early.

## Acceptance Criteria

See the Plan's "Acceptance Criteria" section (7 ACs, verbatim from the Tracker) and its "Verification Plan"
table, which maps each AC to exactly how it gets tested.

## Key Decisions to Follow (do not re-derive — the Plan already resolved these)

1. Category filter: case-insensitive exact match against `provider_category_labels.label`; a new
   `GET /search/categories` endpoint backs the mobile picker with the distinct set of labels actually in use.
2. Reviews don't exist yet: `average_rating=NULL` renders as "No reviews yet," never `"0.0 (0 reviews)"`. Both
   states must be tested (the `NULL` state via real code paths, the has-reviews state via fixture data).
3. Authentication: `require_role(ROLE_CUSTOMER)` on both new endpoints — **flagged for explicit user
   confirmation before backend implementation starts** (see the Plan's Delegation section).
4. Module placement: new `backend/app/modules/search/` module (first slice, no new tables), depending on a new
   `ProviderSearchRepository` inside the existing `provider` module (the query only touches `provider`-schema
   tables) via a new `ProviderService.search_nearby(...)` method — never a direct cross-module repository call.
5. This story does not write to `search.search_requests`/`provider_matches`/`search_event_log` — the origin
   point is a raw `latitude`/`longitude` on the request, never a `saved_addresses` FK.
6. Mobile: a new, minimal Search Filters screen plus the real S-08 Search Results screen — S-06 (Home) itself
   remains unbuilt beyond today's placeholder.
7. Empty states: backend returns a plain empty collection; the two distinct AC4 copy strings are a mobile-only
   concern.
8. Geospatial SQL: `earth_box` containment (GiST-indexed) narrows candidates before the exact `earth_distance`
   recheck; order by `distance_meters ASC, id ASC` for deterministic tie-breaking. This is this codebase's first
   raw parameterized `sqlalchemy.text()` query — bind every parameter, never string-format one.
9. AC6 (query-plan verification) is tested via a real `EXPLAIN (FORMAT JSON)` against ≥1,000 seeded
   `service_areas` rows, asserting an index scan node, not a seq scan.

## Delegation Order

1. **backend** — Plan sections "Backend — Proposed Changes" (items 1–16) and Architecture Decisions 1–5, 8, 9.
2. **frontend** — Plan section "Mobile — Proposed Changes" (items 17–27) and Architecture Decision 6, 7, 2
   (rendering half).
3. **tester** — verify all 7 ACs per the Plan's Verification Plan table.
4. **architect** — review per the Plan's Delegation section, step 4 (module placement, raw SQL precedent,
   category-matching approach, authentication reading, and the Search Event Log trade-off).

Pause and present to the user once `tester`/`architect` both report clean — do not write the Walkthrough, touch
`docs/CHANGELOG.md`, or mark the story complete without explicit sign-off.

## Out of Scope

See the Plan's "Explicitly Out of Scope" section — notably AI-001/MAT-001, the real Category taxonomy, the full
S-06 Home screen, `CLM-001`/Google-seeded listings, and any real Review-domain functionality.
