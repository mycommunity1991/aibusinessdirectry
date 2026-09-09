# Plan for Story DIR-001 — Browse Nearby Providers by Category and Location

**Sprint:** 06 (Directory & Listing Claims) | **Epic:** ML6-EP01 | **Priority:** Critical | **Depends On:**
CUS-002, PRO-002, VER-002 (all done, confirmed unblocked directly from `docs/AI/Project_Tracker.xlsx`'s own
`Depends On` field per `docs/AI/13_OPEN_DECISIONS.md` item 3's 08 September 2026 resolution and
`docs/AI/PROJECT_IMPLEMENTATION_STATE.md` Section 17).

---

## Story

As a customer, I want to filter providers by category and distance without needing the AI conversation, so that
basic discovery works end to end — proving the platform's core value with zero dependency on
verification-review turnaround or AI infrastructure being finished.

This story delivers the first customer-facing search surface: a structured (non-conversational) directory
backed by the geospatial proximity infrastructure (`cube`/`earthdistance`) and the discoverability gate VER-002
already shipped. It is intentionally simpler than the eventual AI-powered results (MAT-001) and exists
specifically to ship discovery early.

**Scope boundary:** does not include the AI conversation (AI-001) or ranked AI-matched results (MAT-001) —
filtering here is a straightforward category + radius query. Does not touch `CLM-001`, Google-seeded listings,
or the `is_claimed`/`google_place_id` columns at all — this story searches only self-registered,
`is_discoverable=true` providers (confirmed independent of `13_OPEN_DECISIONS.md` item 3, per the Tracker).

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`, as supplied)

1. `earthdistance` and `cube` PostgreSQL extensions are enabled via migration; GiST indexes exist on
   `saved_addresses` and `service_areas` location columns.
2. Search filters apply in order: category, then geospatial radius (using `earth_box` before `earth_distance`),
   then discoverability — a provider with `is_discoverable=false` never appears in results regardless of
   category/distance fit.
3. Results show provider photo, name, category, rating with review count (never rating alone), and distance.
4. Empty results show a specific empty-state message distinct from a "no search performed yet" state.
5. Search Results screen is implemented in its structured (pre-AI) form, ready to be upgraded to AI-ranked
   results in MAT-001 without a screen redesign.
6. Query performance is verified to use the GiST index (via query plan check) rather than a sequential scan at
   representative data volumes.
7. Automated tests cover filter precedence (category → geo → discoverability) and deterministic tie-breaking
   when multiple providers are equally ranked.

---

## Verified Current State (read directly from code and docs, not assumed)

- **No `search`/`directory` module exists anywhere** — confirmed by glob (`backend/app/modules/*/`: `audit`,
  `customer`, `identity`, `provider`, `verification` only; no `search` schema, no `search_requests` table, no
  `provider_matches`, no `search_event_log` anywhere in the codebase, despite all three being fully specified in
  `04_DATABASE.md`'s Search Domain section). This is a genuinely new module for this story to create.
- **`service_areas` is real, populated data today, not an empty table** — confirmed by reading
  `backend/app/modules/provider/services/provider_service.py` directly: `create_provider` calls
  `service_area_repository.upsert_for_provider(...)` for both subtypes at creation time, and
  `update_basic_info`'s `_apply_business_details_update`/`_apply_freelancer_details_update` re-sync it on every
  location/radius edit (PRO-002's own Plan Decision, item 1, confirmed actually implemented, not merely
  documented as an intention). Any self-registered provider created through the existing onboarding flow has a
  matching `service_areas` row with real `center_latitude`/`center_longitude`/`radius_meters` — this story's
  geospatial query has real data to search against.
- **`provider.service_areas` currently has only `idx_service_areas_provider_id`** — no geospatial index exists
  yet (`backend/app/modules/provider/models.py`, confirmed). `04_DATABASE.md` Section 13 already specifies the
  exact index this story must add: `CREATE INDEX idx_service_areas_location ON provider.service_areas USING
  gist (ll_to_earth(center_latitude, center_longitude));`, gated behind `CREATE EXTENSION IF NOT EXISTS
  cube;`/`CREATE EXTENSION IF NOT EXISTS earthdistance;`. PRO-002's own Plan explicitly deferred this exact index
  "to the future Search & Matching story that actually queries it" — this is that story.
- **`saved_addresses` has no geospatial index either** (`customer/models.py`, confirmed: only
  `idx_saved_addresses_customer_id` and the default-uniqueness partial index). AC1 names `saved_addresses`
  explicitly alongside `service_areas` — a defensible, forward-looking parity index (Decision 5 below), even
  though this story's actual query (Decision 4) never queries through `saved_addresses` at all — the origin
  point is a raw lat/lng, never a `saved_addresses` FK (see Decision 5).
- **`providers.average_rating` is `NULL` for every provider that exists today, `review_count` is `0`** —
  confirmed directly: `Provider.average_rating` is `Numeric(3,2), nullable=True` with **no server default and no
  application-code write path anywhere** (a full grep of `average_rating` across the codebase shows it appears
  only in the model declaration and `04_DATABASE.md`'s spec — no repository, service, or migration ever sets
  it). `create_provider` explicitly sets `"review_count": 0` but never sets `average_rating` at all, so it stays
  at the column's implicit `NULL`. The Review domain (`review.reviews`, `provider_rating_summaries`) has never
  been built — there is no code path in this entire codebase that could ever populate `average_rating` today.
  AC3's "rating with review count (never rating alone)" must be designed around this honestly (Decision 2).
- **`provider_category_labels.label` is free text with no taxonomy** (`04_DATABASE.md`, PRO-002 Decision 1;
  `13_OPEN_DECISIONS.md` item 1, still Open, critical path). A provider can hold up to 5 labels, exactly one
  marked `is_primary`, edited only as a full-set replace via `PATCH /providers/me`. There is no `categories`
  table, no fixed value set, and no picker source anywhere in the backend or mobile code today. AC2's "filter by
  category" must be designed against this free-text reality (Decision 1).
- **`14_USER_FLOWS.md` Flow 1 explicitly lists "search" as one of exactly three actions requiring
  authentication with no guest path**: "any action requiring auth (search, contact, review) redirects here
  first. There is no guest path." `11_MVP_SCOPE.md` Section 6's Scope Guardrails separately prohibit "a
  guest/unauthenticated path to Search Requests or Contact Views" for AI-assisted implementation specifically.
  Read together, browsing (a search-shaped action) is authenticated — see Decision 3.
- **Every registered Account already holds `ROLE_CUSTOMER`** — assigned unconditionally at first successful
  registration (`AuthService`'s inline grant, Flow 1 step 4; confirmed unchanged by every story since AUTH-001).
  A dual-role Account (Customer + Provider) still holds `ROLE_CUSTOMER`, so gating on this role imposes no extra
  friction beyond "must be logged in" for any legitimate caller.
- **`app/shared/schemas/response.py`'s `CollectionResponse[T]`/`PaginationMeta` exist and have one prior real
  consumer** (VER-002's `GET /admin/verification/records` — the first genuinely shared, platform-wide,
  unbounded-growth collection in this codebase). This story is the **second** real use, and the first
  **customer-facing** one.
- **No raw/`text()`-based SQL exists anywhere in this codebase yet** — every prior query has been expressible
  through SQLAlchemy's ORM/Core expression language. `earth_box`/`earth_distance`/`ll_to_earth` are `earthdistance`
  contrib-extension SQL functions with no SQLAlchemy expression-language mapping; this story is the first to need
  parameterized raw SQL (via `sqlalchemy.text()` with bound parameters — still fully parameterized per
  `06_SECURITY.md`/`08_CODING_STANDARDS.md`'s SQL-injection-prevention rule, never string-interpolated).
- **`15_SCREEN_INVENTORY.md` S-06 (Home) already anticipates a non-AI entry point**: "Prominent 'What do you need
  help with?' input + mic icon, **optional quick-start category chips beneath**, bell icon." S-08 (Search
  Results) is already specified with exactly the fields AC3 asks for: "Provider cards (photo, name, category,
  rating + count, distance, Verified badge), empty state explaining Wizard-of-Oz fallback if unmatched." S-06
  itself, however, **does not exist in the mobile codebase yet** — confirmed by glob: `mobile/lib/features/`
  has no `home`/`search` feature beyond a placeholder screen (`features/home/presentation/screens/
  home_placeholder_screen.dart`) whose "Find a Service" button currently only checks for a saved address and
  then shows a "coming soon" snackbar (CUS-002's own temporary stand-in, explicitly flagged in that file's
  doc-comment as "replaced [target], not the gate itself" by "whichever future story builds the real Search
  feature"). This is that story, for the *structured* (non-AI) slice only — see Decision 6/Mobile section.
- **`16_UX_GUIDELINES.md`'s empty-state formula already distinguishes exactly the two states AC4 asks for**:
  "'No matches yet — describe what you need and we'll find someone nearby' (Home, first-time) is different from
  'No results for this search — try widening your search area' (Search Results, post-search)." This is a
  client-side (mobile) state distinction — the backend's contract is simply an empty `data`/`total_items: 0`
  collection; "no search performed yet" is a screen state that exists before any API call is even made
  (Decision 7).
- `docs/AI/13_OPEN_DECISIONS.md` item 1 (Category Taxonomy) directly covers the free-text category gap this
  story must work within — no new numbered item is needed; this Plan's Decision 1 is an application of the same
  interim posture PRO-001/PRO-002 already established, not a new kind of workaround.

---

## Architecture Decisions

### Decision 1 — Category filter mechanism: case-insensitive exact match against `provider_category_labels.label`, plus a new lightweight "distinct labels in use" endpoint to back the mobile picker

**The problem, stated precisely:** AC2 asks to filter "by category," but there is no real `categories` table
with a fixed, enumerable value set — `13_OPEN_DECISIONS.md` item 1 is still Open and explicitly blocks the real
`category.categories`/`provider_categories` domain until the AI question-flow taxonomy work happens. A category
*picker* UI needs some source of selectable values today, and none exists.

**Chosen:**
- **Matching semantics:** `?category=<value>` matches any of a provider's `provider_category_labels` rows (not
  only the primary one — a provider capable of "Plumbing" and "AC Repair" should surface for either query) via a
  case-insensitive **exact** match (`lower(label) = lower(:category)`), never a substring/fuzzy match. Exact
  match is chosen over `ILIKE '%...%'` because a free-text field with no taxonomy is exactly the situation where
  substring matching produces silently wrong results (e.g. "AC" matching "Vacation Cleaning") with no taxonomy
  to sanity-check against — an honest, narrow tool beats a falsely-broad one here, consistent with this
  codebase's "never assert ungrounded data" principle (`00_PROJECT_CONTEXT.md` Section 3, applied here to search
  matching rather than AI output).
- **Picker source:** a new, small, read-only endpoint, `GET /search/categories`, returns the **distinct set of
  `label` values currently in use** across `provider_category_labels` rows belonging to `is_discoverable=true`
  providers (case-normalized to a single canonical casing per distinct value — e.g. `lower()`-grouped, returning
  the first-seen original casing — so "Plumbing" and "plumbing" collapse to one chip, not two). This is
  genuinely small (bounded by the number of distinct labels real providers have actually typed, not by provider
  count) and owner-agnostic (platform-wide, but tiny) — it is **not** paginated, citing the same reasoning as
  ADR-012's exception, generalized: a bounded-by-real-world-input collection, not one that grows with data
  volume the way a provider listing does. This mirrors S-06's "quick-start category chips" description directly.
- **`category` is optional** on the search endpoint — omitting it browses across all categories (still filtered
  by geo + discoverability). No AC requires category to be mandatory, and "browse nearby providers by category
  **and** location" reads naturally as "by either or both," not as two hard-required parameters.

**Alternatives considered and rejected:**
- **Build a minimal real `categories` table now, even just a handful of hardcoded rows** — rejected outright:
  explicitly out of this story's reach per `13_OPEN_DECISIONS.md` item 1's "blocks the entire AI question-flow
  design" framing; inventing a taxonomy as a side effect of a search story would pre-empt that larger, still-open
  decision without the product input it needs.
- **Substring/`ILIKE` matching** — rejected per the false-positive reasoning above; a substring match over
  ungoverned free text is more likely to mislead than help without a real taxonomy to bound it.
- **No picker-source endpoint at all — let mobile hardcode a static chip list** — rejected: a hardcoded client
  list would silently drift from whatever labels providers have actually typed (which have zero validation
  against any fixed set), producing chips that filter to empty results for categories no provider actually uses,
  or missing categories real providers do use. A live, data-driven distinct-label endpoint costs one small query
  and stays honest.

### Decision 2 — Reviews don't exist yet: `average_rating=NULL` renders as "No reviews yet," never as a fabricated `0.0 (0 reviews)`

**The problem, stated precisely:** AC3 requires "rating with review count (never rating alone)" — but the
Review domain has never been built, and `providers.average_rating` is `NULL` for literally every provider that
exists today (Verified Current State). Displaying `0.0 (0 reviews)` would be dishonestly precise — it implies a
provider was rated and scored zero, which never happened; it was simply never reviewed.

**Chosen:** the search response includes both raw fields, `average_rating: Decimal | null` and
`review_count: int`, exactly as stored — no synthesized default value. Rendering rule (documented here for
`frontend`, enforced in the mobile widget, not the backend, since this is presentation logic over an honestly
nullable field): if `average_rating is None`, render **"No reviews yet"** (a specific, honest microcopy string,
matching `16_UX_GUIDELINES.md`'s "speak the user's language" and "never assert ungrounded data" principles);
otherwise render `"{average_rating} ({review_count} review{s})"` (e.g. `"4.8 (3 reviews)"`), per
`16_UX_GUIDELINES.md`'s explicit rating+count-together rule. This is the same honesty posture ADR-018
(`StubDocumentOcrService`) and ADR-017 (`LocalFileStorage`) already established for other not-yet-real
capabilities: an honest "this doesn't exist yet" state, never a state that *looks* real but isn't.

**Testing implication, addressed explicitly per the task's own framing:** the "has reviews" rendering path
(`"4.8 (3 reviews)"`) can only be exercised today via **directly-inserted fixture data** (manually setting
`average_rating`/`review_count` on a test provider row, since no story yet lets a real Review get created) —
this is not a gap in this story's test coverage, it is the honest state of the domain. Both the backend service
test suite and the mobile widget test suite must cover **both** cases explicitly: (a) a provider with
`average_rating=NULL`/`review_count=0` (the only state achievable through any real, currently-shipped code path)
renders/returns "No reviews yet"; (b) a provider with fixture-injected `average_rating=4.8`/`review_count=3`
renders/returns `"4.8 (3 reviews)"` — proving the *shape* is correct and forward-compatible with a future Review
domain story, without overstating what's actually wired up today.

**Alternatives considered and rejected:**
- **`0.0 (0 reviews)`** — rejected outright as dishonestly precise, per the reasoning above.
- **Omit the rating/count fields entirely from the response until reviews exist** — rejected: AC3 is a literal,
  present-tense requirement ("results show... rating with review count"); the honest "no reviews yet" state
  *is* the correct way to show it today, not a reason to hide the field. Also would require a second, breaking
  schema change once the Review domain ships, whereas the `null`-aware shape absorbs that future without a
  contract change.
- **A separate boolean `has_reviews` flag alongside the raw fields** — rejected as redundant: `average_rating is
  None` already carries exactly this information; a second field encoding the same fact is unnecessary
  surface area (`08_CODING_STANDARDS.md`'s "avoid unnecessary abstractions").

### Decision 3 — Authentication: `require_role(ROLE_CUSTOMER)`, no guest path

`14_USER_FLOWS.md` Flow 1 explicitly names "search" as one of exactly three actions requiring authentication
with no guest path, and `11_MVP_SCOPE.md` Section 6 separately prohibits "a guest/unauthenticated path to Search
Requests or Contact Views" for AI-assisted implementation. Even though this story's structured directory query
is deliberately *not* the `search.search_requests` entity (Decision 4 explains why), it is unambiguously a
search-shaped action in the product sense Flow 1 is describing, and the platform's blanket "mandatory
registration, no guest path" principle (`03_DOMAIN_MODEL.md`, `11_MVP_SCOPE.md` Section 1) gives no textual
basis for carving out an exception here.

**Chosen:** `GET /search/providers` and `GET /search/categories` are both gated by
`Depends(require_role(ROLE_CUSTOMER))` — every registered Account already holds this role unconditionally from
registration onward (Verified Current State), so this imposes no friction beyond "must be signed in," and it
correctly documents this as a Customer-facing action per `03_DOMAIN_MODEL.md`'s own domain framing, rather than
bare bearer-token-only authentication (which would also technically work, but would under-specify *which* kind
of caller this endpoint is for, unlike `provider/api.py`'s bare-auth self-service routes where a bare-auth
choice was made deliberately to sidestep ADR-016's token-refresh-lag issue — that concern does not apply here,
since a Customer's `ROLE_CUSTOMER` is granted at registration, before any token could ever be issued without
it).

**Alternatives considered and rejected:**
- **No authentication (public/guest browsing)** — rejected outright per Flow 1's explicit text and the MVP
  Scope Guardrail above; flagged here as a genuinely blocking product-policy question, not a silent
  interpretation, in case the user intends browsing specifically (as distinct from Contact View) to be
  guest-accessible. **This is called out for explicit user confirmation** — see the Delegation section — because
  it is the one place this Plan's reading of "no guest path" could plausibly be read the other way (e.g. many
  real directory products let anyone browse and only gate contact/lead actions), even though the documented
  evidence available points toward "search requires auth."
- **Bare `get_current_user`, no role check** — rejected in favor of the explicit role check for the reason
  given above; also does not meaningfully simplify anything, since every relevant caller already holds
  `ROLE_CUSTOMER`.

### Decision 4 — Module placement: a new, first-slice `search` module, depending on a new read-only `provider → (its own schema)` repository method exposed via `ProviderService`

`02_ARCHITECTURE.md` names "Search Request & Matching" as its own core business module, responsible for
"Location + service-area + category matching against Provider data" — a domain distinct from Provider even
though every table it queries here (`providers`, `provider_category_labels`, `service_areas`) lives in the
`provider` schema. This mirrors exactly the reasoning VER-001 used to justify a new `verification` module
despite touching `provider`-owned data: a real, architecturally-named domain gets its own module, even when its
first slice is thin and reads (rather than writes) another module's data.

**Chosen:** a new `backend/app/modules/search/` module — this domain's first slice, following the same
"first-slice-of-a-real-domain" shape `verification` (VER-001), `administration` (VER-002), and `notification`
(VER-002) each already established:
- **No new tables, no `models.py`.** This story does not write `search_requests`/`provider_matches`/
  `search_event_log` at all (Decision 5 explains why) — there is nothing for this module to persist.
- **The actual geospatial/category/discoverability SQL lives inside the `provider` module**, as a new,
  dedicated `ProviderSearchRepository` (`backend/app/modules/provider/repositories/provider_search_repository.py`),
  since the query only ever touches `provider`-schema tables — no cross-module repository access is needed or
  permitted (`02_ARCHITECTURE.md`: "Module → Another Module's Repository" is explicitly "Not Allowed"). This is
  kept as its own repository class, separate from the existing `ProviderRepository`, because the query is
  genuinely complex (raw parameterized SQL, multi-table join, pagination, ordering) and deserves isolation from
  `ProviderRepository`'s simple CRUD methods, per `08_CODING_STANDARDS.md`'s "small, focused" class-design
  principle.
- **`ProviderService` gains one new, read-only method**, `search_nearby(...)` (signature in Backend Proposed
  Changes below), thinly wrapping `ProviderSearchRepository` — exposed to other modules the same way
  `ProviderService.list_by_ids` already is (VER-002 Decision 9's precedent).
- **`search`'s own new `SearchService`** depends on `ProviderService` via constructor injection (the identical,
  now four-times-established shape: ADR-014, ADR-016, VER-001 Decision 9, VER-002 Decision 7) — a new,
  one-directional `search → provider` edge, read-only, cycle-free (`provider` gains zero imports from `search`).
  `SearchService` owns response-shaping (category label lookup for display, distance formatting) and the
  `GET /search/categories` distinct-label query (a second new, small `ProviderCategoryLabelRepository` method,
  `list_distinct_labels_for_discoverable_providers()`, added to the *existing* repository since it is a simple
  read with no new complexity to isolate).

**Alternatives considered and rejected:**
- **Extend the `provider` module directly with a `GET /providers/search` endpoint, no new module** — rejected:
  this is exactly the "Search Request & Matching" responsibility `02_ARCHITECTURE.md` names as its own domain,
  and MAT-001 (this story's own explicitly-named future upgrade path, AC5) will need to add ranking/merit logic
  that has nothing to do with a provider's own self-service storefront management — colocating it inside
  `provider` now would misrepresent domain ownership the same way VER-001 itself rejected colocating
  verification code inside `provider`, and would make MAT-001's eventual extension awkward (bloating a module
  whose current responsibility is strictly "manage my own listing").
- **Build the real `search.search_requests`/`provider_matches`/`search_event_log` tables now, reusing the
  `search` schema `04_DATABASE.md` already specifies** — rejected: `search_requests.category_id` is a hard,
  `NOT NULL` FK to `category.categories.id`, a table that does not exist (Decision 1's premise); a
  `conversation_session_id`-optional design still assumes the Conversation/AI-Intake domain's shape. Building
  these tables now, with a fabricated or nullable-hacked category reference, would misrepresent a table
  `04_DATABASE.md` designs for the *conversational* flow as something this purely structural, category-label-based
  query produces — a real category-mismatch, not a naming nuance like `provider_category_labels` vs.
  `provider_categories`. This story's query is read-only and ephemeral by design (Decision 5); no persistent
  Search Request/Search Event Log row is created.
- **A `ProviderSearchRepository` method placed inside `search`, directly issuing SQL against `provider`-schema
  tables via a raw session** — rejected per `02_ARCHITECTURE.md`'s explicit prohibition; the query must be owned
  by the module that owns the tables it touches.

### Decision 5 — This story does not write `search_requests`/`search_event_log`; the origin point is a raw request `latitude`/`longitude`, never a `saved_addresses` FK

**Location origin, resolved:** `14_USER_FLOWS.md`'s only description of an origin point for a search
(`search_requests.customer_latitude`/`customer_longitude`) is a **plain lat/lng pair carried directly on the
request row**, not a foreign key to `saved_addresses` — `04_DATABASE.md`'s `search_requests` table confirms this
column-for-column (`customer_latitude DOUBLE PRECISION NOT NULL`, no `saved_address_id` column anywhere in the
schema). This settles the question directly from existing, authoritative design: the origin point for a search
is always a **raw coordinate pair supplied with the request**, never a `saved_addresses` row reference — whether
that coordinate came from the customer's default saved address (mobile pre-fills it, see Mobile section) or
live device GPS ("search near me") is a client-side UX choice, invisible to the API contract.

**Chosen:** `GET /search/providers` takes `latitude: float`, `longitude: float` as required query parameters
(no `saved_address_id` alternative) — both directly supplied by the caller, sourced by the mobile client from
either the customer's default saved address (pre-filled, editable) or on-device GPS via the existing
`geolocator` dependency (already a mobile dependency since CUS-002's `LocationPickerScreen`), matching Flow 1's
"Use current location" precedent already built into `S-05`. `radius_km` is an optional query parameter
(default value documented in Backend Proposed Changes) bounding the search.

**This story does not write to `search.search_requests`, `search.provider_matches`, or `search.search_event_log`
at all** — those tables model the *conversational* flow's structured output (tied to a `conversation_session_id`
and a real `category_id`), which this story deliberately bypasses entirely per its own "without needing the AI
conversation" framing. A structured directory browse is a pure, ephemeral, read-only query — there is nothing to
log for admin unmatched-query analytics here (that concern belongs to the real Search Request flow, a future
story), and inventing a write path into tables designed for a different flow's shape would misrepresent this
story's actual (simpler) semantics. **Flagged explicitly**: `03_DOMAIN_MODEL.md`'s "Search Event Log... every
Search Request, matched or not" framing means this decision leaves DIR-001's queries invisible to future
supply-gap analytics — an accepted, explicit trade-off of this story's "prove discovery early, zero AI
dependency" scope, not an oversight.

**Alternatives considered and rejected:**
- **Accept `saved_address_id` as an alternative to raw `latitude`/`longitude`** — rejected: adds a second
  request shape for zero benefit (the mobile client already has the coordinate in hand either way, whether from
  a saved address or GPS), and would require this endpoint to reach into `customer`-schema data
  (`saved_addresses`) it has no other reason to touch, a new cross-module edge this story doesn't need.
- **Write a `search_event_log` row anyway, with `category_id=NULL`** — rejected: `search_event_log.category_id`
  is nullable, so this is technically possible, but doing so would misrepresent this story's queries (free-text
  label matches, no real category) as instances of the real category-driven analytics `04_DATABASE.md` designs
  that table for, and no AC asks for it.

### Decision 6 — Mobile entry point: a new, minimal "Search Filters" screen, since real S-06 (Home) doesn't exist yet

`15_SCREEN_INVENTORY.md`'s S-06 already anticipates "optional quick-start category chips" as a non-AI entry
point, but **S-06 itself has not been built** — the current mobile Home is only `HomePlaceholderScreen`, whose
"Find a Service" button is an explicitly-flagged temporary stand-in (CUS-002) with a "coming soon" snackbar as
its only behavior once an address exists. Building the *full* S-06 (AI input box + mic icon + chips) is out of
this story's scope — the AI Conversation input has no backend to call yet (AI-001/AI-002 are Sprint 7, blocked
on Category Taxonomy per `13_OPEN_DECISIONS.md` item 1).

**Chosen:** this story builds:
1. A new, minimal **Search Filters** screen (`features/search/presentation/screens/search_filters_screen.dart`)
   — a category chip/dropdown (populated from `GET /search/categories`) and a location field (pre-filled from
   the customer's default saved address if one exists, editable via the existing, reusable
   `LocationPickerScreen` from `shared/widgets/location_picker/`, including its already-built "use current
   location" option) plus a radius selector, with a single "Search" primary action.
2. The real **S-08 Search Results screen** (`features/search/presentation/screens/search_results_screen.dart`)
   — provider cards (photo, name, category, rating+count per Decision 2, distance), the two distinct empty
   states (Decision 7/AC4), and a loading state — calling `GET /search/providers` with the filters chosen on
   screen 1.
3. `HomePlaceholderScreen`'s existing "Find a Service" button is rewired to open the new Search Filters screen
   instead of showing the "coming soon" snackbar — replacing exactly the placeholder behavior that file's own
   doc-comment already flagged as temporary, per CUS-002's own stated expectation ("whichever future story
   builds the real Search feature replaces this button's target"). The address-required gate CUS-002 built stays
   in place unchanged (a customer with zero saved addresses is still prompted to add one first — the Search
   Filters screen's location field needs a starting point).

This is **not** a claim that S-06 is now fully built — the AI conversation input, mic icon, and the rest of the
real Home screen remain unbuilt, deferred to the future AI Conversation story exactly as `15_SCREEN_INVENTORY.md`
already scopes it. This story's mobile surface is scoped strictly to "structured search, no AI," per the
story's own title and framing, and is built so S-08 itself needs no redesign once MAT-001 upgrades what backs
it (AC5) — only the ranking/response content changes, not the screen.

**Alternatives considered and rejected:**
- **Build a placeholder-only mobile change (leave `HomePlaceholderScreen`'s "coming soon" snackbar as-is,
  backend-only story)** — rejected: AC5 explicitly requires "Search Results screen is implemented," a literal,
  present-tense mobile deliverable, unlike VER-002's genuinely backend-only scope (which had no AC requiring any
  screen). This story cannot honestly claim AC5 without shipping S-08.
- **Build the full S-06 Home screen now (AI input box included, even if it does nothing yet)** — rejected: no AC
  asks for it, and building a non-functional AI input box that goes nowhere would be a worse user experience
  than the current explicit placeholder, plus unrequested scope beyond "browse... without needing the AI
  conversation."

### Decision 7 — Empty-state contract: backend returns a plain empty collection; the two distinct AC4 states are a client-side (mobile) concern

The backend has no way to distinguish "the user hasn't searched yet" from "the user searched and got zero
results" — the first state is definitionally a state where **no API call has been made at all**. `GET
/search/providers` returning `{"data": [], "pagination": {"total_items": 0, ...}}` is the *only* backend-visible
outcome; the "no search performed yet" state is a Search Filters/Search Results screen state that exists purely
client-side, before any request is sent. `frontend` implements both copy strings per
`16_UX_GUIDELINES.md`'s own worked example verbatim: pre-search empty state on the results screen (if reached
without filters applied) reads "No matches yet — describe what you need and we'll find someone nearby"-equivalent
phrasing adapted for the non-AI flow (e.g. "Choose a category or search nearby to see providers"), and the
post-search zero-result state reads "No results for this search — try widening your search area." No backend
schema field is needed to distinguish them.

### Decision 8 — Geospatial SQL: `earth_box` containment (GiST-indexed) narrows candidates, `earth_distance` exact-filters and orders, `id ASC` breaks ties

AC2's literal wording ("using `earth_box` before `earth_distance`") and AC7's "deterministic tie-breaking" both
require a specific, testable query shape, not merely "some distance calculation":

```sql
SELECT
    sa.provider_id,
    earth_distance(
        ll_to_earth(:origin_lat, :origin_lng),
        ll_to_earth(sa.center_latitude, sa.center_longitude)
    ) AS distance_meters
FROM provider.service_areas sa
JOIN provider.providers p ON p.id = sa.provider_id
WHERE
    -- Category filter (Decision 1), applied first, only if :category is provided:
    (:category IS NULL OR EXISTS (
        SELECT 1 FROM provider.provider_category_labels pcl
        WHERE pcl.provider_id = p.id
          AND pcl.is_active = true
          AND lower(pcl.label) = lower(:category)
    ))
    -- Geospatial radius, earth_box (GiST-indexed containment) BEFORE earth_distance (AC2):
    AND earth_box(ll_to_earth(:origin_lat, :origin_lng), :radius_meters)
        @> ll_to_earth(sa.center_latitude, sa.center_longitude)
    AND earth_distance(
            ll_to_earth(:origin_lat, :origin_lng),
            ll_to_earth(sa.center_latitude, sa.center_longitude)
        ) <= :radius_meters
    -- Discoverability gate, applied last (AC2):
    AND p.is_discoverable = true
    AND p.is_active = true
ORDER BY distance_meters ASC, p.id ASC
LIMIT :limit OFFSET :offset;
```

- **Filter order matches AC2 literally**: category (an `EXISTS` subquery against `provider_category_labels`) is
  evaluated first in the `WHERE` clause's textual/logical order; the `earth_box(...) @>` containment check comes
  next and is the clause the GiST index (`idx_service_areas_location`) actually accelerates — it cheaply
  eliminates every row outside a bounding cube around the origin point using the index, before the exact
  (index-incompatible) `earth_distance(...) <= :radius_meters` recheck runs only against that already-narrowed
  candidate set. This is the standard, documented `earthdistance` idiom for exactly this reason: `earth_box`
  is a cube (not a sphere) bounding volume cheap to index-scan; `earth_distance` is the expensive, exact
  great-circle calculation that must still run to trim the box's corners, but only over a small candidate set
  instead of the whole table. `is_discoverable=true` is checked last, directly on `providers`, exactly matching
  AC2's specified order (category → geo → discoverability) — a provider failing category or being outside the
  radius never even reaches the discoverability check, and a provider passing both but not discoverable is
  excluded regardless of fit, satisfying AC2's explicit "never appears... regardless of category/distance fit."
- **Deterministic tie-breaking (AC7):** primary order is `distance_meters ASC` (nearest first — this story's
  entire premise is proximity-first structured browsing, pre-merit-ranking). When two providers are equally
  ranked (identical `distance_meters` — a realistic tie, e.g. two providers with the same configured `service_areas`
  center point in a test fixture, or in production two providers whose computed distance rounds identically), the
  tie-break is `p.id ASC` — `id` is always present, unique, and immutable (ADR-008), so this always produces one
  single, fully deterministic total order with no extra column needed. `created_at ASC` was considered and
  rejected as the tie-break (see below) in favor of `id`, per the task's own suggested precedent.
- **Raw parameterized SQL, not the ORM expression language:** `earth_box`/`earth_distance`/`ll_to_earth` have no
  SQLAlchemy Core/ORM function mapping. This query is issued via `sqlalchemy.text()` with fully bound parameters
  (`:origin_lat`, `:origin_lng`, `:radius_meters`, `:category`, `:limit`, `:offset`) — never string-formatted or
  concatenated user input, satisfying `06_SECURITY.md`/`08_CODING_STANDARDS.md`'s parameterized-query requirement
  even though it is not expressed through the ORM's Python-object query builder. This is flagged as this
  codebase's **first use of raw parameterized SQL**, a genuine precedent-setting choice for `architect`'s
  attention.

**Alternatives considered and rejected:**
- **`created_at ASC` as the tie-break** — rejected in favor of `id ASC`: `providers.created_at` is a real,
  meaningful column, but using it as an arbitrary tie-break for an otherwise-proximity-sorted list could read as
  implying "older listings rank higher," an unintended, uncommunicated bias; `id ASC` is transparently arbitrary
  (a random UUID) and cannot be misread as expressing any ranking intent, matching the task's own suggested
  precedent.
- **PostGIS `ST_DWithin`/`ST_Distance` instead of `cube`/`earthdistance`** — rejected: `04_DATABASE.md` Section
  13 and `09_DECISIONS.md`'s existing architecture already commit to `cube`/`earthdistance` specifically because
  PostGIS is not an approved dependency (`12_TECH_STACK.md` lists only PostgreSQL FTS for Phase 1); introducing
  PostGIS now would be an unapproved, unrequested infrastructure change.
- **Compute distance in Python after fetching all candidates** — rejected: defeats the entire purpose of AC1/AC6
  (a GiST index existing and actually being used); would degrade to an O(n) full-table scan and Python-side
  Haversine computation at any real provider volume.

### Decision 9 — AC6's query-plan verification: seed representative volume, run `EXPLAIN (FORMAT JSON)` against the repository's actual query, assert an index scan node targeting `idx_service_areas_location`

A GiST index existing is necessary but not sufficient for AC6 — Postgres's planner will still choose a
sequential scan over a tiny table, since a seq scan is genuinely cheaper below some row-count threshold. AC6
requires this to be *verified*, not merely asserted by the index's existence.

**Chosen:** a dedicated test (`backend/tests/modules/provider/test_provider_search_repository.py`) seeds a
representative volume of `service_areas` rows (at least 1,000, scattered across a wide geographic spread — e.g.
randomly distributed within a large bounding box, not clustered at one point, so the GiST index has a genuine
selectivity advantage to offer) directly via bulk insert (bypassing the full `ProviderService.create_provider`
flow for speed — a raw fixture, not a claim that 1,000 real onboardings were exercised), then executes
`EXPLAIN (FORMAT JSON) <the repository's exact query>` through the same `AsyncSession`, parses the returned plan
JSON, and asserts that the plan contains an `Index Scan`/`Bitmap Index Scan` node whose `Index Name` is
`idx_service_areas_location` — and explicitly asserts the **top-level** scan of `service_areas` is not a
`Seq Scan`. This is a real, environment-verified assertion (run against the actual configured test database,
not inferred), not a static code-review claim.

**Alternative considered and rejected:** `SET enable_seqscan = off` before running the query, then just confirm
the query still executes correctly — rejected: this proves the index *can* be used correctly, but not that the
planner *chooses* to use it under realistic conditions, which is what AC6 actually asks for ("verified to use
the GiST index... rather than a sequential scan at representative data volumes" — a statement about the
planner's real behavior, not merely the index's functional correctness).

---

## Backend — Proposed Changes

### Migrations
1. `enable_geospatial_extensions_and_indexes` — new Alembic migration (down-revision = VER-002's latest head).
   - `CREATE EXTENSION IF NOT EXISTS cube;` / `CREATE EXTENSION IF NOT EXISTS earthdistance;` (idempotent,
     safe to re-run).
   - `CREATE INDEX idx_service_areas_location ON provider.service_areas USING gist
     (ll_to_earth(center_latitude, center_longitude));` — exactly per `04_DATABASE.md` Section 13.
   - `CREATE INDEX idx_saved_addresses_location ON customer.saved_addresses USING gist
     (ll_to_earth(latitude, longitude));` — AC1's explicit, literal requirement (Decision 5 notes this story's
     own query never uses it, but AC1 names it directly; built now so any future story needing a
     `saved_addresses`-centered geospatial query — e.g. "providers near my other saved address" — has it ready
     without a second migration).
   - Verify upgrade/downgrade against a disposable scratch database (ADR-013's precedent) — `DROP INDEX`s but
     does **not** `DROP EXTENSION` on downgrade (extensions are shared, low-risk-to-leave, high-risk-to-drop if
     anything else were to depend on them; downgrading only removes what this migration's own upgrade added
     that's safe to remove).

### New module: `backend/app/modules/search/`
2. `dependencies.py` — `get_search_service()` (constructs `SearchService`, injecting `get_provider_service` from
   `provider/dependencies.py` per Decision 4).
3. `schemas.py` — `SearchResultProviderResponse { id, display_name, slug, provider_type, category_labels:
   list[str], primary_photo_url: str | None, average_rating: Decimal | None, review_count: int,
   distance_meters: float }`; `CategoryOptionResponse { label: str }`.
4. `services/search_service.py` — `SearchService`:
   - `search_providers(*, category: str | None, latitude: float, longitude: float, radius_km: float, page: int,
     page_size: int) -> tuple[list[SearchResultProviderResponse], int]` — validates `radius_km` bounds (a
     configurable max, see Config below, rejecting an unreasonably large radius with 422), converts to meters,
     calls `ProviderService.search_nearby(...)`, enriches each result with its primary portfolio photo (first by
     `sort_order`, if any — reuses the existing `PortfolioRepository.list_active_for_provider`, first item only)
     and its category labels (reuses `ProviderService.get_category_labels`, already exists from PRO-002).
   - `list_categories() -> list[CategoryOptionResponse]` (Decision 1).
5. `api.py` — `GET /search/providers` (AC2, AC3, AC4; `require_role(ROLE_CUSTOMER)`, Decision 3), returning
   `CollectionResponse[SearchResultProviderResponse]`; `GET /search/categories` (Decision 1;
   `require_role(ROLE_CUSTOMER)`), returning `SuccessResponse[list[CategoryOptionResponse]]` (unpaginated, per
   Decision 1's ADR-012-style reasoning).

### `provider` module extensions
6. `repositories/provider_search_repository.py` (new) — `ProviderSearchRepository`:
   - `search_nearby(*, category: str | None, origin_lat: float, origin_lng: float, radius_meters: float,
     limit: int, offset: int) -> tuple[list[uuid.UUID], dict[uuid.UUID, float], int]` — executes Decision 8's
     raw parameterized `text()` query (plus a matching `COUNT(*)` variant, same `WHERE` clause, for
     `PaginationMeta.total_items`), returning ordered provider ids, a `provider_id → distance_meters` map, and
     the total count.
7. `repositories/provider_category_label_repository.py` — new `list_distinct_labels_for_discoverable_providers()
   -> list[str]` (Decision 1's picker-source query: `SELECT DISTINCT ON (lower(label)) label FROM
   provider_category_labels pcl JOIN providers p ON p.id = pcl.provider_id WHERE p.is_discoverable = true AND
   pcl.is_active = true ORDER BY lower(label), label`).
8. `services/provider_service.py` — new `search_nearby(...)` (thin pass-through to
   `ProviderSearchRepository.search_nearby`, plus a batch `list_by_ids` call — reusing the existing VER-002
   method — to hydrate full `Provider` rows for the ids returned, preserving the repository's distance-ordered
   sequence) and `list_distinct_category_labels()` (thin pass-through, Decision 1).
9. `repositories/provider_repository.py` — no changes; `list_by_ids` already exists (VER-002).

### Config (`backend/app/core/config.py`)
10. New settings: `SEARCH_DEFAULT_RADIUS_KM: float = 10.0`, `SEARCH_MAX_RADIUS_KM: float = 100.0`,
    `SEARCH_MAX_PAGE_SIZE: int = 50` (a tighter cap than `05_API_GUIDELINES.md`'s general 100 default, since a
    provider-photo-carrying result card is heavier than a typical list row — flagged, no AC specifies a number).

### API wiring
11. `backend/app/api/v1/api.py` — `v1_router.include_router(search_router, prefix="/search")`.
12. `backend/tests/conftest.py` — no new import needed (this module adds no ORM models).

### Exceptions
13. `InvalidSearchRadiusError` (422 — `radius_km` outside the configured bounds).

### Tests
14. `backend/tests/modules/provider/test_provider_search_repository.py` — Decision 9's `EXPLAIN`-based AC6 test;
    filter-precedence tests (AC2): a provider matching category+radius but `is_discoverable=false` is excluded;
    a provider matching category but outside radius is excluded; a provider inside radius but wrong category is
    excluded; a provider matching all three appears. Tie-break test (AC7): two providers with identical
    `service_areas` coordinates (same computed distance) are returned in `id ASC` order, verified across two
    runs with the ids inserted in reverse order (proving the order is driven by `id`, not insertion order).
15. `backend/tests/modules/search/test_search_service.py` — category-list distinct/case-collapse behavior
    (Decision 1); rating rendering-input shape for both the `average_rating=NULL` and fixture-injected
    `average_rating=4.8` cases (Decision 2 — asserts the *raw* response fields, since rendering itself is a
    mobile concern); radius bounds validation (`InvalidSearchRadiusError` on an out-of-range `radius_km`).
16. `backend/tests/modules/search/test_search_endpoints.py` — full HTTP round trip: unauthenticated → 401;
    a `ROLE_CUSTOMER` token → 200 with correct pagination envelope (`CollectionResponse`); empty result set
    returns `data: []`/`total_items: 0` (AC4's backend half); `GET /search/categories` returns only labels
    belonging to `is_discoverable=true` providers (a label belonging only to a non-discoverable provider is
    absent).

---

## Mobile — Proposed Changes

### New feature: `mobile/lib/features/search/`
17. `domain/models/search_result_provider.dart`, `domain/models/category_option.dart` — mirror the backend
    response shapes (including `averageRating: double?`/`reviewCount: int`, never a synthesized default).
18. `data/search_repository.dart` — `searchProviders({category, latitude, longitude, radiusKm, page, pageSize})`,
    `listCategories()`.
19. `presentation/screens/search_filters_screen.dart` (new, Decision 6) — category chip/dropdown (from
    `listCategories()`), location field (pre-filled from the customer's default saved address via the existing
    `SavedAddressRepository`, editable through the existing `LocationPickerScreen`), radius selector, "Search"
    primary action navigating to the results screen with the chosen filters.
20. `presentation/screens/search_results_screen.dart` (new, S-08, AC3/AC4/AC5) — provider card list (photo,
    name, category labels, rating+count per Decision 2's rendering rule, distance formatted as km/m), the two
    distinct empty states (Decision 7), loading state, pull-to-refresh, tap-through stub (navigates toward the
    future Provider Profile screen, S-09 — not built by this story; a simple "coming soon" placeholder on tap is
    acceptable here, mirroring CUS-002's own precedent for a not-yet-built downstream screen).
21. `presentation/widgets/provider_search_card.dart` (new, reusable) — the individual result card, built so
    MAT-001 can reuse it unchanged (AC5) when the underlying data becomes AI-ranked rather than
    proximity-ranked; no ranking-specific UI (e.g. a "match score") is shown, since none exists yet.
22. `state/search_filters_controller.dart`, `state/search_results_controller.dart` (Riverpod controllers, no
    business logic in widgets, per `08_CODING_STANDARDS.md`).

### Existing screen change
23. `features/home/presentation/screens/home_placeholder_screen.dart` — `_onFindService` is rewired to navigate
    to the new Search Filters screen once a saved address exists (replacing the "coming soon" snackbar), per
    Decision 6. The existing address-required gate (CUS-002, AC5) is unchanged.
24. `core/routing/app_routes.dart` — new routes for the two new screens.

### Tests
25. `mobile/test/features/search/search_results_screen_test.dart` — renders both empty states distinctly
    (Decision 7); renders both the "No reviews yet" and `"4.8 (3 reviews)"` card states (Decision 2, using
    fixture data through a fake repository, mirroring the existing `fake_provider_repository.dart` pattern).
26. `mobile/test/features/search/search_filters_screen_test.dart` — category chips populate from the fake
    repository's `listCategories()`; location field pre-fills from a fake default saved address; "Search"
    navigates with the expected query parameters.
27. `mobile/test/features/search/fakes/fake_search_repository.dart` (new, mirrors the existing fake-repository
    pattern used throughout `features/provider`/`features/verification`).

---

## Explicitly Out of Scope (do not implement in this story)

- The AI Conversation (AI-001) and ranked AI-matched results (MAT-001) — this story's results are proximity-
  ordered only, with the deterministic `id ASC` tie-break (Decision 8); no merit/ranking algorithm of any kind.
- The real Category taxonomy domain (`category.categories`, `category_question_templates`, the real
  `provider_categories` join table) — Decision 1's free-text exact-match approach is a deliberate, flagged
  interim mechanism, not a preview of the real feature.
- The full S-06 Home screen (AI input box, mic icon) — Decision 6's Search Filters screen is a minimal,
  structured-only entry point, not S-06 itself.
- `CLM-001`, Google-seeded/unclaimed listings, `is_claimed`/`google_place_id` filtering of any kind — this
  story's query is unconditionally scoped to `is_discoverable=true` regardless of `listing_source`, and no AC
  asks for unclaimed-listing labeling here (that is `CLM-001`'s own, still-deferred scope per
  `13_OPEN_DECISIONS.md` item 3/4).
- Writing to `search.search_requests`, `search.provider_matches`, or `search.search_event_log` — Decision 5.
- The Provider Profile screen (S-09) — this story's result cards are tap-stubbed only; a full profile view is a
  future story's scope.
- Any real Review-domain functionality (`review.reviews`, `provider_rating_summaries`, review submission) —
  Decision 2 only renders the existing, honestly-`NULL` `providers.average_rating`/`review_count` columns.
- PostGIS or any geospatial extension beyond `cube`/`earthdistance` — Decision 8.
- Full-text search over provider name/description (`04_DATABASE.md`'s separately-scoped Phase 1 FTS strategy) —
  not requested by any AC here; category + radius only.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet — fresh start, first story of Sprint 6, immediately following Sprint 5's
clean closeout on this same branch.

**Before backend implementation starts: Decision 3 (authentication requirement) should be explicitly confirmed
by the user** — this Plan's reading of `14_USER_FLOWS.md` Flow 1 and `11_MVP_SCOPE.md` Section 6 concludes
browsing requires `ROLE_CUSTOMER` authentication, no guest path, but this is the first genuinely public-feeling,
large-collection endpoint in the codebase, and a reasonable alternate reading (public browsing, gate only
Contact View) exists in real-world directory products generally. Every other decision in this Plan proceeds
regardless of which way Decision 3 resolves (swapping `require_role(ROLE_CUSTOMER)` for bare/no auth is a
one-line change to the endpoint's dependency, not a redesign).

1. **backend** — Migration (extensions + both GiST indexes), the new `search` module, the new
   `ProviderSearchRepository`/`ProviderCategoryLabelRepository` additions, `ProviderService.search_nearby`/
   `list_distinct_category_labels`, config, exceptions, schemas, API routes, dependencies, app wiring, all tests
   (items 1–16). ACs to satisfy: 1, 2, 3 (backend half — raw fields, not rendering), 4 (backend half — empty
   collection contract), 6, 7 (backend half — repository-level filter-precedence/tie-break tests). **Read
   Decision 8 in full before starting** — the `earth_box`-before-`earth_distance` clause ordering and the raw
   `text()` parameterization are the parts of this story most likely to be gotten subtly wrong (e.g. accidentally
   string-formatting a parameter instead of binding it, or checking `earth_distance` without the `earth_box`
   pre-filter at all, which would still be *correct* but would fail AC6's index-usage verification).
2. **frontend** — The new `features/search/` module (Search Filters + Search Results screens, the reusable
   provider card, repository/models/controllers), the `HomePlaceholderScreen` rewire, routing, tests (items
   17–27), once backend endpoints exist (or in parallel against a fake repository per the existing
   `fake_provider_repository.dart` pattern). ACs to satisfy: 3 (mobile half — rendering rating+count per
   Decision 2), 4 (mobile half — the two distinct empty-state copy strings), 5.
3. **tester** — Verify all 7 ACs individually. Particular attention to: AC2 (read the actual repository query to
   confirm the literal clause order — category, then `earth_box`, then `earth_distance`, then
   `is_discoverable` — not just that the right rows come back, since AC2's wording is about *order*, not only
   correctness); AC3/Decision 2 (confirm both the `NULL`-rating and fixture-injected-rating rendering paths are
   actually exercised, on both backend and mobile, and that "0.0 (0 reviews)" never appears anywhere); AC6
   (independently re-run the `EXPLAIN` test and confirm the plan genuinely shows an index scan at the seeded
   volume, not merely that the test asserts it); AC7 (the tie-break test with reversed insertion order, proving
   the order is driven by `id`, not insertion/scan order).
4. **architect** — Review Decision 4 (new `search` module vs. extending `provider`) against
   `02_ARCHITECTURE.md`'s domain-boundary and "Module → Another Module's Repository" rules; Decision 8 (the raw
   `text()` SQL, this codebase's first use) against `06_SECURITY.md`'s SQL-injection-prevention principle and
   `08_CODING_STANDARDS.md`'s "Database access must use SQLAlchemy ORM / parameterized queries" wording,
   confirming `text()` with bound parameters satisfies the letter and spirit of that rule; Decision 1 (free-text
   category matching) against `13_OPEN_DECISIONS.md` item 1's existing interim-workaround precedent; Decision 3
   (authentication requirement) against `11_MVP_SCOPE.md`/`14_USER_FLOWS.md`, flagging explicitly if it reads
   the guest-path question differently; Decision 5 (no `search_requests` write) against `03_DOMAIN_MODEL.md`'s
   Search Event Log framing, confirming the trade-off is acceptable and clearly documented, not silently
   dropped.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 4
   (new `search` module placement), Decision 8 (raw parameterized SQL precedent for `earthdistance`/`cube`
   functions), and Decision 3 (authentication requirement for browsing, if confirmed as scoped) as new ADRs
   (next available: **ADR-025** onward — tech-lead finalizes exact numbering/grouping at story close); update
   `04_DATABASE.md` (Section 13 — confirm the GiST indexes as shipped exactly per spec; note the new
   `idx_saved_addresses_location` index); update `03_DOMAIN_MODEL.md`/`13_OPEN_DECISIONS.md` if needed
   (confirming item 1's continued Open status and this story's specific interim application of it).

---

## Verification Plan (mapped to the 7 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade against a scratch database; `\dx` confirms `cube`/`earthdistance` are enabled; `\d provider.service_areas` and `\d customer.saved_addresses` both show their new GiST index (`idx_service_areas_location`, `idx_saved_addresses_location`) via `ll_to_earth(...)`. |
| 2 | Repository-level integration test reads the actual query text/clause order (category `EXISTS` → `earth_box` containment → `earth_distance` recheck → `is_discoverable`); functional tests confirm a provider failing any one of the three conditions never appears, regardless of how well it satisfies the other two. |
| 3 | Integration test asserts the response payload includes `photo` (nullable), `name`, `category_labels`, `average_rating`+`review_count` together (never `average_rating` alone), and `distance_meters`, for both the no-reviews (`NULL`) and fixture-injected-rating cases (Decision 2); mobile widget test confirms the rendered string is "No reviews yet" or `"X.X (N reviews)"`, never a synthesized `"0.0 (0 reviews)"`. |
| 4 | Backend integration test confirms an empty `data`/`total_items: 0` response for a query matching zero providers; mobile widget test confirms the Search Results screen shows the distinct "no results for this search" copy in that state, and separately confirms the pre-search Search Filters screen never shows that same copy before a search is submitted. |
| 5 | Widget test confirms the Search Results screen (S-08) renders the structured fields listed in AC3 with no AI-ranking-specific UI element present, and that `provider_search_card.dart` has no hardcoded assumption tying it to a proximity-only data source (reviewed by `architect` for forward-compatibility with a future ranked-response shape). |
| 6 | Dedicated `EXPLAIN (FORMAT JSON)`-based test (Decision 9), seeded with ≥1,000 representative `service_areas` rows, asserts an `Index Scan`/`Bitmap Index Scan` node referencing `idx_service_areas_location` and explicitly asserts no top-level `Seq Scan` node targets `service_areas`. |
| 7 | Repository-level test covers filter precedence (category → geo → discoverability) with four provider fixtures, each failing exactly one condition, confirming only the fully-matching one is returned; a separate tie-break test with two identically-located providers, inserted in both ascending and descending `id` order across two test runs, confirms the returned order is always `id ASC` regardless of insertion order. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md` (Search Request & Matching module responsibilities; module communication rules)
- `docs/AI/03_DOMAIN_MODEL.md` (Search Request, Provider, Category, Service Area domains)
- `docs/AI/04_DATABASE.md` (Search Domain, Provider Domain, Section 13 — Geospatial Query Strategy)
- `docs/AI/05_API_GUIDELINES.md` (Pagination, Collection Response)
- `docs/AI/06_SECURITY.md` (SQL Injection Prevention, Authentication)
- `docs/AI/07_UI_GUIDELINES.md` / `docs/AI/16_UX_GUIDELINES.md` (Empty States, rating+count display rule)
- `docs/AI/09_DECISIONS.md` (ADR-012 — pagination exception precedent this story's category-list endpoint
  extends; ADR-014/016 — cross-module service-injection shape; ADR-015 — endpoint shape rule; ADR-023 —
  role-only authorization shape precedent)
- `docs/AI/11_MVP_SCOPE.md` (Section 6 — Scope Guardrails, the "no guest path" language Decision 3 relies on)
- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy, still Open; item 3 — the 08 September 2026
  resolution confirming `DIR-001` is unblocked independent of the Google Places legal review)
- `docs/AI/14_USER_FLOWS.md` (Flow 1 — the "search" authentication precedent; Flow 4 — the conversational flow's
  filter-order precedent this story's structured query mirrors)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-06, S-08)
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` (Section 17 — Next Planned Story)
- `docs/implementation/plans/Plan_S04_PRO-002.md` (`service_areas` sync mechanism this story depends on;
  `provider_category_labels` origin)
- `docs/implementation/plans/Plan_S05_VER-002.md` (`CollectionResponse`/`PaginationMeta` first-use precedent;
  cross-module service-injection precedent this story's `search → provider` edge mirrors)
