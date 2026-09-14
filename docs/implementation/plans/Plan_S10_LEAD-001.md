# Plan for Story LEAD-001 — See And Manage My Provider Leads

**Sprint:** 10 (Leads & Visibility) | **Epic:** ML10-EP01 | **Milestone:** ML10 | **Priority:** High | **Depends
On:** CON-001 (done, Sprint 8), REV-001 (done, Sprint 9)

---

## Story (verbatim, `Project_Tracker.xlsx`, `LEAD-001` row — relayed by the orchestrator this session)

"As a provider, I want to see who viewed my contact info and whether they went on to hire me, so that I can gauge
real interest in my listing without needing customer-provider messaging, which doesn't exist in this product. This
story surfaces CON-001's Contact Views and REV-001's outcome tags as a provider-facing Leads list, without exposing
more customer PII than necessary. Scope boundary: does not include visibility analytics/trend charts (LEAD-002) —
this story is the raw lead list only."

## Acceptance Criteria (verbatim, 5 items)

1. Leads screen lists Contact Views for the authenticated provider, each showing a category/request context, a
   relative timestamp, and an outcome status chip (Hired / Not hired / not yet reported) where available.
2. Leads are ordered most-recent-first and support the app's standard pull-to-refresh and empty-state patterns.
3. No more customer PII is shown than necessary for the provider to recognize the lead.
4. A provider can only see their own leads (ownership enforced, tested explicitly).
5. Automated tests cover the ownership boundary and correct outcome-status display across all three states.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **`contact.contact_views` (CON-001, shipped) columns, confirmed from `backend/app/modules/contact/models.py`**:
  `customer_id` (FK → `customer.customer_profiles.id`, not null), `provider_id` (FK → `provider.providers.id`, not
  null), `search_request_id` (FK → `search.search_requests.id`, **nullable**), `viewed_at` (TIMESTAMPTZ, not null,
  default `now()`), plus full `CommonColumnsMixin`. No direct category/request-text column exists on this table at
  all — `search_request_id` is the only possible path to any request context, and it is nullable.
- **`search_request_id`'s nullability is not incidental — it is a real, load-bearing product distinction, confirmed
  from `ContactService.create_contact_view`'s docstring and `CreateContactViewRequest.search_request_id`'s own
  field description**: it is populated only when the customer reached the provider via the AI Conversation search
  path (a real `search.search_requests` row exists); it is `None` for the structured (non-AI) Search Results path
  (`DIR-001`/`MAT-001`'s `SearchService`, confirmed stateless — it writes no `search_requests` row at all, per
  `search/models.py`'s own module docstring: "`DIR-001`'s `SearchService` remains a stateless read-layer... reused
  unchanged"). Confirmed directly in mobile: `SearchResultsScreen._onCardTap` hardcodes `searchRequestId: null` when
  navigating to Provider Profile. **Conclusion: a real fraction of Contact Views (every one from the structured
  browse path) will have no request context available at all — this is an honest data-availability gap, not
  something this story can retroactively backfill.**
- **The join path to a category name, when `search_request_id` is present, confirmed from
  `backend/app/modules/search/models.py`**: `search.search_requests.category_id` is a **nullable** FK →
  `category.categories.id` (one of AI-002's four flagged nullable-column deviations, ADR-038 — a `routed_to_admin`
  session can reach that terminal status with no category ever resolved). So even when `search_request_id` is set,
  `category_id` on that row can still be `NULL`. The full honest join path is: `contact_views.search_request_id` →
  `search_requests.category_id` → `category.categories.name`, with **two** independent points where the chain can
  legitimately dead-end (no `search_request_id` at all; or a `search_request_id` whose `category_id` is `NULL`).
  Both must resolve to an honest "no category available" display, never a fabricated placeholder.
- **`contact.outcome_tags` (REV-001, shipped) columns, confirmed from the same `models.py`**: `contact_view_id`
  (FK → `contact_views.id`, not null, **unique** — 1:1), `hired` (BOOLEAN, **not null**), `submitted_at`
  (TIMESTAMPTZ, not null). `OutcomeTagRepository.get_by_contact_view_id` already exists (added for `REV-002`) as
  the single-row read; **no batch/list method exists yet** for resolving many Contact Views' outcome tags in one
  query. AC1's three literal states map exactly and completely onto this shipped schema, with no ambiguity: `hired
  = true` → "Hired"; `hired = false` → "Not hired"; no row for this `contact_view_id` at all (the 1:1 unique
  constraint makes "no row" and "not yet reported" the same state) → "not yet reported."
- **This codebase's established, zero-customer-PII precedent for anything provider-facing about a Contact View is
  already set by CON-001's own shipped `NotificationService.notify_new_contact_view`**
  (`backend/app/modules/notification/services/notification_service.py`): the existing "new lead" notification a
  provider already receives today carries body text `"A customer just viewed your contact details."` — literally
  zero customer-identifying detail (no name, no photo, no phone, no location). AC3's "no more customer PII than
  necessary to recognize the lead" is not a new, undefined bar this story must invent from scratch — it is a
  continuation of an existing, already-shipped precedent of exposing **zero** customer PII to a provider for a
  Contact View, anywhere in this codebase. `customer.customer_profiles.display_name`/`avatar_url` are never read by
  this story's read path.
- **`ProviderService.get_my_provider(user_id) -> Provider | None`** (`backend/app/modules/provider/services/
  provider_service.py`) is the established, already-shipped "resolve the caller's own Provider" primitive — used
  today by `GET /providers/me` (bare `get_current_user`, 404 via `ProviderNotFoundError` if `None`) and by
  `PortfolioService.list_my_portfolio`'s identical `_get_provider_or_404` pattern (`backend/app/modules/provider/
  services/portfolio_service.py`). This is the exact ownership-resolution shape AC4 needs: resolve the caller's own
  `Provider` row from `current_user.id`, 404 if none exists yet, then scope every query strictly to
  `provider.id` — never to a client-supplied `provider_id`. No new ownership primitive needs to be invented.
- **The `verification` module's mount pattern is the exact precedent for where this story's new route should
  live**, confirmed from `backend/app/api/v1/api.py`: `verification_router` (a fully separate module,
  `backend/app/modules/verification/`) is mounted at `prefix="/providers/me/verification"`, sitting alongside (not
  merged into) `provider_router`'s own `prefix="/providers"` mount. A module other than `provider` owning a route
  under the `/providers/me/...` path is already an established, shipped pattern, not something this story would be
  inventing for the first time.
- **The paginated-collection response shape is already fully established and reused verbatim across three existing
  endpoints**: `CollectionResponse[T]`/`PaginationMeta` (`backend/app/shared/schemas/response.py`), with `GET
  /search/providers` (`backend/app/modules/search/api.py`) as the closest precedent — `page`/`page_size` query
  params, a repository-level `(rows, total_items)` two-part return, `total_pages = math.ceil(total_items /
  page_size)` computed in the router, a per-domain `Settings.<DOMAIN>_MAX_PAGE_SIZE` cap (`SEARCH_MAX_PAGE_SIZE`,
  `CLAIM_SEARCH_MAX_PAGE_SIZE` already exist in `backend/app/core/config.py`). This story adds `LEADS_MAX_PAGE_SIZE`
  as the fourth instance of that same, already-precedented per-domain cap setting.
- **No relative-timestamp formatter exists anywhere in the mobile codebase yet** (confirmed: no `timeago`-style
  package in `mobile/pubspec.yaml`, no existing relative-time utility under `mobile/lib/shared/`). Every existing
  screen that shows a timestamp (verification records, notifications-adjacent copy) either shows no timestamp at
  all or an absolute one. AC1's "relative timestamp" is a genuinely new, small mobile utility this story must add.
- **The mobile provider-side navigation entry point, confirmed from `mobile/lib/features/provider/presentation/
  screens/storefront_screen.dart` and `mobile/lib/features/customer/presentation/screens/
  profile_settings_screen.dart`**: `ProfileSettingsScreen._onListYourBusiness` already resolves whether the caller
  has a Provider (`getMyProvider()`) and routes to `StorefrontScreen` if so. `StorefrontScreen` already has one
  existing precedent for a "tap through to a related provider-only screen" entry point: `_VerificationStatusChip`,
  a tappable card linking to `AppRoutes.verificationStatus`, deliberately reading from `shared/data/` (not
  `features/verification/`) so `features/provider/` never imports another feature directly
  (`02_ARCHITECTURE.md`'s "Features must not depend directly on each other" rule). This story's new "My Leads" entry
  point on `StorefrontScreen` follows the exact same shape: a tappable card/tile linking to a new
  `AppRoutes.leads` route, with no direct import of a new `features/leads/` feature's internals from
  `features/provider/` beyond the route constant.
- **Pull-to-refresh + a paginated list + a distinct empty state is already a fully precedented mobile pattern**:
  `RankedProviderResultsList` (`mobile/lib/shared/widgets/ranked_provider_results_list.dart`) wraps a
  `ListView.builder` in an optional `RefreshIndicator`; `SearchResultsScreen` layers a `Status` enum
  (`idle`/`loading`/`error`/`loaded`) plus a textually distinct empty state on top. This story's Leads screen
  follows the same shape (its own `Status` enum, its own empty-state copy, its own `RefreshIndicator`) rather than
  reusing `RankedProviderResultsList` itself (that widget is typed to `RankedProviderResult`, a provider-search
  result shape entirely unrelated to a Lead).
- Current Alembic migration head is unaffected — **this story adds no new table, no new column, and needs no new
  migration**. It is a pure read-layer over two already-shipped tables (`contact_views`, `outcome_tags`), joined
  against two more already-shipped, read-only tables (`search_requests`, `categories`) it does not own.

---

## Architecture Decisions

### Decision 1 — Leads is a new read-only slice of the existing `contact` module, not a new `leads` module

**The problem:** where should the new query/service/route live — the existing `contact` module (which already owns
`contact_views`/`outcome_tags`), a new standalone `leads` module, or inside `provider`?

**Chosen:** extend `backend/app/modules/contact/` in place: a new `LeadService` (`services/lead_service.py`), two
new read methods on the existing `ContactViewRepository`, one new batch read method on the existing
`OutcomeTagRepository`, a new schema, and a new route file mounted separately (Decision 2). This mirrors
`REV-001`'s own Decision 1 verbatim reasoning (itself mirroring the `administration` module's multi-aggregate-root
precedent): this story writes **zero** new tables — it is a pure query over data `contact` already owns
(`contact_views`, `outcome_tags`), joined read-only against two tables owned by other modules
(`search.search_requests`, `category.categories`) that `contact` already has a precedented, service-mediated edge
to reach information from (`ContactService` already depends on `SearchRequestRepository` for the ownership check at
Contact View creation time). A new standalone `leads` module would need to re-establish the exact same
`ContactViewRepository`/`OutcomeTagRepository` dependency `contact` already has natively, for zero isolation
benefit — the ADR-051 "one schema, one module, except when sharing an existing schema" rule this Plan was asked to
apply points the same direction: `leads` introduces no new schema at all, so there is nothing for a new module to
"own."

**Alternatives considered and rejected:**
- **A new `leads` module.** Rejected for the reason above — no new schema, no new aggregate root; it would only
  duplicate `contact`'s existing repository dependencies as new cross-module edges.
- **Folding this into `provider` module instead** (since the mobile-facing framing is "provider self-service").
  Rejected — `provider` has no existing edge to `contact_views`/`outcome_tags` at all, and `02_ARCHITECTURE.md`'s
  "modules communicate through services only" rule would force a new `provider → contact` service edge for a
  feature that is fundamentally a read over `contact`'s own data, not `provider`'s. `contact` already depends on
  `provider.ProviderService` (Decision 1's own precedent, `ContactService`'s existing constructor) — reusing that
  *existing* direction (`contact → provider`, already established) to resolve "whose Provider is this caller" is
  strictly simpler than inventing a new, opposite-direction edge.

### Decision 2 — The new route is mounted at `GET /providers/me/leads`, in a route module owned by `contact`, mirroring the `verification` module's exact `/providers/me/...` mount precedent

**The problem:** AC4 needs a caller-scoped, `/me`-shaped collection endpoint. Should it live under `provider`'s own
`api.py` (since the URL path reads as `/providers/me/...`), or can a route physically defined inside `contact` be
mounted there?

**Chosen:** a new `backend/app/modules/contact/provider_lead_api.py` (own `APIRouter`, its own `["Leads"]` tag,
mirroring `verification`'s own separately-tagged, separately-mounted router) is registered in
`backend/app/api/v1/api.py` as `v1_router.include_router(provider_lead_router, prefix="/providers/me/leads")` —
placed directly alongside the existing `v1_router.include_router(verification_router,
prefix="/providers/me/verification")` line, the identical, already-shipped precedent for "a module other than
`provider` owns a route mounted under the `/providers/me/...` path." The single route,
`router.get("")`, resolves to `GET /providers/me/leads`. Bare `get_current_user` (not `require_role`), exactly
mirroring `GET /providers/me`/`GET /providers/me/portfolio`'s own established pattern — ownership/404 is enforced
inside `LeadService`, not via a route guard, since "does this caller even have a Provider yet" is a data question,
not a role question (a caller who has never onboarded as a Provider still holds no `ROLE_PROVIDER`-gated
distinction anywhere else in this codebase's shipped code — confirmed no `require_role(ROLE_PROVIDER)` exists
anywhere today).

**Alternatives considered and rejected:**
- **Adding the route directly to `backend/app/modules/provider/api.py`,** calling into a new cross-module
  `contact.LeadService` from there. Rejected — this would invert Decision 1's chosen dependency direction
  (`contact → provider`, already established) into a new, second, opposite direction (`provider → contact`) for a
  single endpoint, when the already-shipped `verification` module's mount precedent proves the router-definition
  location and the URL-path prefix are already decoupled concerns in this codebase — no need to introduce a new
  coupling to make the URL "look right."
- **A different URL shape entirely, e.g. `GET /leads` (top-level, no `/providers/me/` prefix).** Rejected — every
  other "list my own X" collection in this codebase (`/providers/me/portfolio`, `/providers/me/availability`,
  `/providers/me/verification`) is nested under `/providers/me/`; breaking that convention for this one endpoint
  would be an unprecedented, unexplained departure.

### Decision 3 — Category/request context resolves through `search_requests.category_id → categories.name`, with an explicit, honest `null` when either link in the chain is absent — never a fabricated fallback

**The problem:** AC1 requires "a category/request context" on every lead, but the Verified Current State above
confirms two independent, real cases where no category is resolvable at all (no `search_request_id`; or a
`search_request_id` with `category_id = NULL`). What should the field show in those cases, and should anything else
(e.g. the provider's own primary category label, or the raw customer free-text query) be substituted instead?

**Chosen:** `LeadResponse.category_name: str | None` — populated from the real join when available, `null`
otherwise. **Explicitly not backfilled with the provider's own `provider_category_labels` primary label as a
"best guess" substitute**: a provider may hold up to five category labels (`PRO-002`), and silently substituting
"your own primary category" as if it were "the category this specific customer was searching under" would be a
genuine fabrication of specificity this codebase's own established anti-fabrication principle (ADR-038's exact
reasoning: "make the column nullable and report the honest absence, never fabricate a value") directly rules out.
The mobile Leads screen renders a plain, honest fallback string (e.g. "Viewed your profile directly") when
`category_name` is `null`, textually distinct from a real category name, so a provider is never misled into
thinking a specific service category drove that lead when the platform genuinely does not know one.
**Also explicitly not surfacing `search_requests.structured_criteria`'s free-text answers** — AC1's literal
wording asks for "a category/request context," singular, and the story's own scope boundary line ("this story is
the raw lead list only," deferring analytics/trend detail to `LEAD-002`) counsels against dumping raw structured
answer text onto this list screen; a category name is the right level of context for a lead list, not a full
job-detail dump.

**Alternatives considered and rejected:**
- **Falling back to the provider's own primary category label when `category_name` is unresolvable.** Rejected per
  the fabrication reasoning above.
- **Surfacing `structured_criteria`'s raw answers as the "request context."** Rejected — out of this story's
  scope boundary, and a bigger surface than AC1 asks for; also raises its own, separate PII-adjacent question
  (free-text customer answers could incidentally contain identifying detail typed by the customer, e.g. "my address
  is...") that AC3's minimization principle argues against opening at all in this story.

### Decision 4 — Zero customer-identifying fields are ever included in `LeadResponse` — no name, no avatar, no phone, no raw customer id

**The problem:** AC3 requires "no more customer PII than necessary... to recognize the lead," without stating
exactly which fields clear that bar.

**Chosen:** `LeadResponse` carries: `id` (the Contact View's own id — an opaque UUID, not customer-identifying),
`category_name` (Decision 3), `viewed_at` (the raw timestamp; the mobile client renders it as relative time,
Backend/Frontend items below), and `outcome_status` (Decision 5). It never carries `customer_id`,
`customer_profiles.display_name`, `customer_profiles.avatar_url`, or any customer contact detail. This directly
continues this codebase's own already-shipped precedent (Verified Current State) of exposing **zero** customer PII
to a provider anywhere a Contact View is surfaced to them today (`notify_new_contact_view`'s existing, deliberately
anonymous "A customer just viewed your contact details." copy) — this story does not lower that existing bar. A
provider "recognizing" a lead, per the story's own framing ("gauge real interest... without needing
customer-provider messaging, which doesn't exist in this product"), is satisfied by category + recency + outcome
alone; the product deliberately has no messaging thread to "match" a name against in the first place, so a name
would be informationally inert even if shown.

**Alternatives considered and rejected:**
- **Including the customer's first name only** (a common "minimal PII" middle ground in other marketplaces).
  Rejected — this would be a **new, first-ever** exposure of any customer-identifying field to a provider anywhere
  in this codebase, a materially different privacy posture than every other shipped touch-point (the Contact View
  notification, the eventual Review display — which shows the review text/rating but, per `REV-002`'s own shipped
  scope, never the reviewer's name either). Introducing it here, for a lower-stakes "recognize the lead" ask that
  category + timestamp + outcome already satisfies, would be a scope-expanding privacy regression relative to this
  codebase's own established pattern, not a routine call — if the CTO genuinely wants a first name shown, that is
  a deliberate, flagged product decision (Open Question 1 below), not something this Plan silently adds.

### Decision 5 — `outcome_status` is a plain three-value string enum (`hired` / `not_hired` / `not_yet_reported`), computed server-side from `outcome_tags.hired`'s presence/value — never the raw boolean or a raw-row absence left for the client to interpret

**The problem:** AC1's three states ("Hired / Not hired / not yet reported") must map cleanly onto `hired: BOOLEAN
NOT NULL` plus "no row exists yet" (Verified Current State already confirms this mapping is exact and complete —
no fourth state is possible given the 1:1 unique constraint).

**Chosen:** the backend computes and returns one of three literal string values —
`"hired"`, `"not_hired"`, `"not_yet_reported"` — via a single batch lookup
(`OutcomeTagRepository.list_by_contact_view_ids`, a new method, Backend Proposed Changes item 4) rather than
requiring the mobile client to infer "not yet reported" from a missing/null field itself. This mirrors
`NotificationService`'s own established "never simply interpolate the raw enum/boolean value; the backend commits
to an explicit, named state" convention (`06_SECURITY.md`/AC5's "never exposing internal status enum values,"
already applied at `VER-002`), and avoids each of the three states requiring a fragile double-negative client-side
condition (`hired == null ? ... : hired ? ... : ...`).

**Alternatives considered and rejected:**
- **Returning the raw `OutcomeTagResponse | null` shape** (mirroring the existing `POST .../outcome-tag` response
  schema) and letting the mobile client derive the three-state chip itself. Rejected — this pushes a business-rule
  interpretation (what does "no tag" mean, semantically, on this specific screen) onto the client for no benefit,
  and risks a future second mobile surface (e.g. `LEAD-002`'s analytics) re-deriving the same three states
  slightly differently.

---

## Backend — Proposed Changes

1. **`backend/app/core/config.py`** — add `LEADS_MAX_PAGE_SIZE: int = 50` (Settings field), the fourth instance of
   this codebase's established per-domain page-size-cap pattern (`SEARCH_MAX_PAGE_SIZE`,
   `CLAIM_SEARCH_MAX_PAGE_SIZE`).
2. **`backend/app/modules/contact/repositories/contact_view_repository.py`** — add two new methods:
   - `list_for_provider(provider_id: uuid.UUID, *, limit: int, offset: int) -> list[ContactView]` — `SELECT ...
     WHERE provider_id = :provider_id ORDER BY viewed_at DESC, id ASC LIMIT :limit OFFSET :offset` (AC2's
     most-recent-first ordering; `id ASC` as the deterministic tie-break, mirroring `ProviderSearchRepository`'s
     own `p.id ASC` tie-break precedent for two rows with an identical `viewed_at`).
   - `count_for_provider(provider_id: uuid.UUID) -> int` — a matching, unpaginated `SELECT COUNT(*) WHERE
     provider_id = :provider_id`, for `PaginationMeta.total_items` (mirrors `ProviderSearchRepository`'s own
     paired count-query pattern).
3. **`backend/app/modules/search/repositories/search_request_repository.py`** — add
   `list_by_ids(ids: list[uuid.UUID]) -> list[SearchRequest]`, a plain `WHERE id IN (...)` batch fetch, mirroring
   `ProviderRepository.list_by_ids`'s existing, precedented shape — needed to batch-resolve `category_id` for a
   page of leads without an N+1 query.
4. **`backend/app/modules/contact/repositories/outcome_tag_repository.py`** — add `list_by_contact_view_ids(ids:
   list[uuid.UUID]) -> list[OutcomeTag]`, a plain `WHERE contact_view_id IN (...)` batch fetch (Decision 5) —
   the batch counterpart to the existing single-row `get_by_contact_view_id`.
5. **`backend/app/modules/category/repositories/category_repository.py`** — add `list_by_ids(ids:
   list[uuid.UUID]) -> list[Category]`, the same `WHERE id IN (...)` batch-fetch shape as item 3, needed to resolve
   category names for the batch of `category_id`s pulled from item 3's search requests.
6. **New file `backend/app/modules/contact/services/lead_service.py`** — `LeadService`:
   - Constructor deps: `ContactViewRepository`, `OutcomeTagRepository`, `SearchRequestRepository`,
     `CategoryRepository`, `ProviderService` (the last three are new cross-module edges for `contact` — `search`
     and `category` are new; `provider` is already an existing edge via `ContactService`).
   - `async def list_my_leads(self, user_id: uuid.UUID, *, page: int, page_size: int) -> tuple[list[LeadItem],
     int]`:
     1. `provider = await self.provider_service.get_my_provider(user_id)`; if `None`, raise
        `ProviderNotFoundError()` (AC4 — a caller with no Provider listing has no leads to see, by construction;
        mirrors `PortfolioService._get_provider_or_404` verbatim).
     2. `total_items = await self.contact_view_repository.count_for_provider(provider.id)`.
     3. `contact_views = await self.contact_view_repository.list_for_provider(provider.id, limit=page_size,
        offset=(page - 1) * page_size)`.
     4. Batch-resolve outcome tags: `outcome_tags = await
        self.outcome_tag_repository.list_by_contact_view_ids([cv.id for cv in contact_views])`, indexed into a
        `dict[contact_view_id, OutcomeTag]`.
     5. Batch-resolve category context: collect the distinct, non-null `search_request_id`s from `contact_views`,
        `search_requests = await self.search_request_repository.list_by_ids(...)`, index by id; collect the
        distinct, non-null `category_id`s from those, `categories = await
        self.category_repository.list_by_ids(...)`, index by id.
     6. For each `ContactView`, assemble one `LeadItem` (a small internal dataclass/NamedTuple, not yet the
        Pydantic response shape — that translation happens in the API layer, mirroring
        `ProviderService.search_nearby`'s own "service returns raw domain data, API layer builds the response
        schema" convention): `id=cv.id`, `viewed_at=cv.viewed_at`, `category_name` resolved via the two-hop lookup
        (Decision 3, `None` if either hop misses), `outcome_status` computed from the matching `OutcomeTag`'s
        presence/`hired` value (Decision 5).
     7. Return `(items, total_items)`, preserving `list_for_provider`'s own `viewed_at DESC, id ASC` order (no
        re-sort at this layer — mirrors `ProviderService.search_nearby`'s "reconstruct order from the
        already-ordered id list" precedent, except here the repository's own row order is already final since no
        cross-table re-ranking is needed).
7. **`backend/app/modules/contact/schemas.py`** — add:
   - `LeadOutcomeStatus` (a `StrEnum`, mirroring `search/models.py`'s own `SearchRequestStatus` shape):
     `HIRED = "hired"`, `NOT_HIRED = "not_hired"`, `NOT_YET_REPORTED = "not_yet_reported"`.
   - `LeadResponse(BaseModel)`: `id: uuid.UUID`, `category_name: str | None`, `viewed_at: datetime`,
     `outcome_status: LeadOutcomeStatus`. Deliberately carries no `customer_id`/`provider_id`/PII field (Decision
     4).
8. **New file `backend/app/modules/contact/provider_lead_api.py`** (Decision 2) — `router = APIRouter(tags=
   ["Leads"])`; one route, `GET ""` → `GET /providers/me/leads`, `page: int = 1`, `page_size: int =
   _DEFAULT_PAGE_SIZE` query params (`page_size` clamped to `settings.LEADS_MAX_PAGE_SIZE`, mirroring
   `search_providers`'s exact clamping line), bare `Depends(get_current_user)` (Decision 2), returns
   `CollectionResponse[LeadResponse]` with a real `PaginationMeta` (`math.ceil`, mirroring `search_providers`'s
   exact computation), 401 documented, 404 documented ("the caller has not created a provider listing yet,"
   mirroring `GET /providers/me/portfolio`'s identical wording).
9. **`backend/app/modules/contact/dependencies.py`** — add `get_lead_service`, wiring `LeadService`'s five
   constructor dependencies (item 6) — reuses the module's existing `get_contact_view_repository`/
   `get_outcome_tag_repository` providers, plus new `get_search_request_repository` (already exists in `search`'s
   own `dependencies.py`, imported the same way `ContactService`'s existing dependency wiring already imports it),
   a new `get_category_repository` import from `category`'s `dependencies.py`, and the existing
   `get_provider_service` import from `provider`'s `dependencies.py`.
10. **`backend/app/api/v1/api.py`** — add `from app.modules.contact.provider_lead_api import router as
    provider_lead_router` and `v1_router.include_router(provider_lead_router, prefix="/providers/me/leads")`,
    placed directly after the existing `verification_router` line (Decision 2).

### Tests

11. `backend/tests/modules/contact/test_lead_service.py` — the core of AC4/AC5's coverage:
    - **Ownership (AC4):** a caller with no Provider at all → `ProviderNotFoundError`. A Provider with zero Contact
      Views → `([], 0)`, not an error. A page of Contact Views belonging to a *different* provider is never
      returned when listing Provider A's leads (a fixture creates Contact Views against both Provider A and
      Provider B, asserts Provider A's `list_my_leads` call returns exactly and only Provider A's rows, and vice
      versa) — the direct, explicit ownership-boundary test AC4 asks for.
    - **Outcome-status mapping, all three states (AC5):** one Contact View with `outcome_tags.hired=True` →
      `LeadOutcomeStatus.HIRED`; one with `hired=False` → `NOT_HIRED`; one with no `outcome_tags` row at all →
      `NOT_YET_REPORTED` — three separate, explicitly named assertions (not one parameterized case collapsing all
      three, per `REV-001` test 15/AC6's own precedent for "explicit, separately-named test cases").
    - **Category-context resolution (Decision 3):** a Contact View with a `search_request_id` whose
      `search_requests.category_id` resolves to a real category → the real category name; a Contact View with
      `search_request_id = NULL` → `category_name is None`; a Contact View with a `search_request_id` present but
      whose `search_requests.category_id` is itself `NULL` → also `category_name is None` (the second, distinct
      dead-end case named in Decision 3 — must be tested separately, not assumed to behave the same as the first
      by inspection alone).
    - **Ordering (AC2):** three Contact Views created with distinct `viewed_at` values, asserted returned
      most-recent-first.
    - **Pagination:** `total_items`/page-slicing correctness across a fixture with more rows than one page size.
12. `backend/tests/modules/contact/test_lead_api.py` — full HTTP round trip: 200 happy path (a real page of leads,
    including at least one of each of the three outcome states, and a mix of resolvable/unresolvable category
    context, asserting `LeadResponse`'s exact field set and that no PII field is present in the raw JSON body —
    a literal `assert "customer_id" not in item` / no `display_name`/`avatar_url` key anywhere in the payload,
    directly verifying AC3 at the wire level); 404 (caller has no Provider); 401 unauthenticated; a cross-provider
    fixture confirming Provider A's authenticated call never returns Provider B's leads (AC4's HTTP-level
    counterpart to test 11's service-level assertion); pagination query params (`page`/`page_size`) behave per
    `PaginationMeta`.
13. `backend/tests/modules/contact/test_contact_view_repository.py` (new file — no prior test file exists for this
    repository, since it previously had no custom methods) — `list_for_provider`/`count_for_provider` ordering and
    provider-scoping, directly against the DB.
14. `backend/tests/modules/contact/test_outcome_tag_repository.py` — extend with a
    `list_by_contact_view_ids` case (empty input list, partial match, full match).
15. `backend/tests/modules/search/test_search_request_repository.py` (or equivalent existing file) — extend with a
    `list_by_ids` case.
16. `backend/tests/modules/category/` — extend with a `CategoryRepository.list_by_ids` case.
17. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

No new mobile dependency is required for networking/state (reuses `dio`/Riverpod/GoRouter, already in place); one
new, small, dependency-free relative-time utility is added (Verified Current State — none exists yet).

1. **New feature folder `mobile/lib/features/leads/`** (a new feature — this is a new, standalone screen with its
   own list/pagination/empty-state concerns, not a natural extension of `features/provider_profile/` or
   `features/provider/`, per `02_ARCHITECTURE.md`'s Feature-First convention: "Each feature owns: UI, State,
   Business Logic, Repository, Models"):
   - `domain/models/lead.dart` — mirrors `LeadResponse` (`id`, `categoryName` nullable, `viewedAt`,
     `outcomeStatus` — a Dart enum with the same three values plus an `unknown` fallback for forward-compatibility,
     mirroring how other mobile enums in this codebase parse an unrecognized backend string).
   - `domain/models/lead_exception.dart` — mirrors `provider_exception.dart`'s per-feature exception-mapping
     convention (`notFound` — caller has no Provider listing yet; `network`; `unknown`).
   - `data/lead_repository.dart` — `Future<(List<Lead>, PaginationMeta)> listMyLeads({int page = 1, int pageSize =
     20})`, calling `GET /providers/me/leads`, mapping errors via `_mapLeadError` (same shape as
     `ProviderRepository`'s `_mapNotFoundOnlyError`).
   - `state/leads_controller.dart` (Riverpod) — owns a `Status` enum (`idle`/`loading`/`error`/`loaded`, mirroring
     `SearchResultsController`'s own shape) plus the current page's `List<Lead>`; exposes `load()` and `refresh()`
     (the latter backing pull-to-refresh, AC2).
   - `presentation/screens/leads_screen.dart` (`LeadsScreen`) — an `AppBar` titled "My Leads," a
     `RefreshIndicator`-wrapped `ListView.builder` of lead cards when loaded and non-empty (each card: category
     name or the honest fallback string when `null`, Decision 3; a relative-time label; an outcome status chip —
     three visually distinct chip styles for Hired/Not hired/Not yet reported, mirroring
     `_VerificationStatusChip`'s existing chip-styling convention of colored container + icon + label), a loading
     spinner, a retry-able error state (mirrors `_LoadError`/`_ErrorState`'s existing shape across this codebase),
     and a **textually distinct empty state** ("No leads yet — once a customer views your contact details, they'll
     show up here.") that remains pull-to-refresh-able (mirrors `_ZeroResultsEmptyState`'s exact
     `RefreshIndicator` + `LayoutBuilder` + `ConstrainedBox(minHeight: ...)` shape for a scrollable-when-empty
     screen, AC2's literal "standard... empty-state patterns" requirement).
2. **`mobile/lib/shared/utils/relative_time.dart`** (new, small, dependency-free utility) — a single function,
   `String formatRelativeTime(BuildContext context, DateTime value)`, returning coarse buckets ("Just now,"
   "X minutes ago," "X hours ago," "X days ago," falling back to an absolute short date beyond ~30 days) — no new
   package dependency, per `08_CODING_STANDARDS.md`'s "avoid unnecessary packages" and the small, single-purpose
   scope this need actually has.
3. **`mobile/lib/features/provider/presentation/screens/storefront_screen.dart`** — add a new tappable card/tile
   below `_VerificationStatusChip` (or in a small new `_LeadsEntryPointCard`, mirroring that widget's own
   read-from-`AppRoutes`-constant-only shape) linking to `AppRoutes.leads` — `features/provider/` still never
   imports `features/leads/` internals directly, only the route constant (mirrors the existing
   `_VerificationStatusChip` precedent exactly).
4. **`mobile/lib/core/routing/app_routes.dart`** — add `static const String leads = '/leads';`, documented mirroring
   the existing entries' doc-comment convention (reached from `storefront`'s new entry point).
5. **`mobile/lib/core/routing/app_router.dart`** — add `GoRoute(path: AppRoutes.leads, builder: (context, state) =>
   const LeadsScreen())` — no `extra` required (this screen needs no navigation-time arguments, unlike
   `providerProfile`/`writeReview`).
6. **`mobile/lib/l10n/app_en.arb` / `app_ar.arb`** — new keys: `leadsScreenTitle`, `leadsEmptyStateMessage`,
   `leadsOutcomeHiredLabel`, `leadsOutcomeNotHiredLabel`, `leadsOutcomeNotYetReportedLabel`,
   `leadsNoCategoryContextLabel` (Decision 3's honest fallback string), `storefrontLeadsEntryLabel` (the new
   Storefront tile's own label).

### Tests

7. `mobile/test/features/leads/` — controller tests for `LeadsController` (loaded/error/empty states, pagination
   page-append behavior, refresh resets to page 1); widget tests for `LeadsScreen` (empty state renders and is
   pull-to-refresh-able per AC2's literal requirement, all three outcome chip variants render with visually/
   textually distinct copy per AC1/AC5, a `null` `categoryName` renders the honest fallback string rather than
   `null`/empty text, relative-time formatting renders for a few fixed `DateTime` fixtures at known offsets from
   a fixed "now").
8. `mobile/test/features/provider/` — extend `storefront_screen_test.dart` (or equivalent) to assert the new Leads
   entry point card is present and navigates to `AppRoutes.leads` on tap.
9. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **Visibility analytics / trend charts** (`LEAD-002`'s own named scope) — no aggregate counts-over-time, no
  conversion-rate calculation, no chart of any kind. This story is the raw, per-lead list only, per the story's own
  literal scope-boundary sentence.
- **Any customer-provider messaging** — the story's own premise explicitly states this doesn't exist in this
  product; nothing here introduces a reply/contact-back affordance from the Leads screen.
- **Showing any customer name, avatar, or additional identifying detail beyond category/timestamp/outcome**
  (Decision 4) — a deliberate privacy-preserving minimum, not a placeholder for "more detail later" within this
  story's own scope.
- **Surfacing `search_requests.structured_criteria`'s raw free-text answers** (Decision 3) — a bigger surface than
  AC1 asks for, deferred implicitly to whatever `LEAD-002`'s eventual analytics scope decides, not decided here.
- **Filtering/sorting controls on the Leads screen** (e.g. filter by outcome status, filter by category) — AC2 only
  asks for a fixed most-recent-first order; no filter/sort UI is requested or built.
- **Any write path** (marking a lead as reviewed/archived, provider-side notes) — this story is read-only over
  already-shipped Contact View/Outcome Tag data; it writes nothing new.
- **`visit_verifications`** ("Verified Visit") — remains untouched, fully unbuilt, unaffected by this story.
- **A provider-facing "leads count" badge on Storefront or elsewhere outside the Leads screen itself** — no AC asks
  for this; only the Leads screen's own list is in scope.

---

## Open Questions (flagged for CTO awareness — do not block `backend`/`frontend` from starting)

1. **Decision 4's "zero customer PII" reading of AC3.** This Plan reads AC3 ("no more customer PII than
   necessary... to recognize the lead") as satisfied by category + relative timestamp + outcome alone, given this
   codebase's own already-shipped zero-PII precedent for Contact View notifications, and deliberately does **not**
   add the customer's first name (a common industry middle ground this Plan considered and rejected as an
   unrequested, precedent-breaking privacy expansion). If the CTO's actual intent for "recognize the lead" was to
   include at least a first name, that is a real, flagged product-scope difference from this Plan's default choice
   — confirm before `backend`/`frontend` builds `LeadResponse`'s final field set, since adding a name field later
   would be a breaking response-shape change rather than an additive one.
2. **Decision 3's honest-`null` treatment of unresolvable category context**, for the (real, expected-to-be-common)
   fraction of leads reached via the structured Search Results path, which creates no `search_requests` row at
   all. This Plan shows a generic "Viewed your profile directly" fallback string rather than any substitute
   category guess. Confirm this fallback framing is acceptable, versus, e.g., wanting the provider's own category
   label shown instead (a decision this Plan explicitly declined to make unilaterally, per Decision 3's
   fabrication-avoidance reasoning).

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start — first story of Sprint 10/Milestone ML10).

1. **backend** — Backend Proposed Changes items 1–17. Build order: (a) the four small repository batch/list methods
   first (items 2–5), each independently unit-testable in isolation (tests 13–16); (b) `LeadService` (item 6),
   with test 11 written alongside, since Decision 3 (category dead-end handling) and Decision 5 (outcome-status
   mapping) are this story's two correctness-critical mechanisms — read both in full before starting; (c) the
   schema/route/dependency wiring (items 7–10), with test 12 (the full HTTP round trip, including the literal
   no-PII-in-the-wire-body assertion) last.
2. **frontend** — Frontend Proposed Changes items 1–9. Should start once `backend`'s `GET /providers/me/leads`
   endpoint is available to integrate against (or in parallel against this Plan's documented `LeadResponse` shape,
   per this codebase's established parallelization practice, with a final integration pass once both are done).
3. **tester** — verify all 5 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget tests).
   Particular attention to: AC1 (all three outcome states genuinely render with distinct copy/styling, both a
   resolvable and an unresolvable category context render correctly); AC2 (a real multi-row fixture confirms
   most-recent-first order end to end, and the empty state is genuinely pull-to-refresh-able, not merely styled to
   look like it is); AC3 (the literal wire-level assertion that no PII field/value appears anywhere in a real `GET
   /providers/me/leads` response body, for a fixture where the underlying customer *does* have a
   `display_name`/`avatar_url` set — proving the omission is deliberate, not simply "no data existed to leak");
   AC4 (the explicit cross-provider fixture, both at the service layer and over real HTTP, confirming Provider A
   never sees Provider B's leads under any query parameter); AC5 (three separately-named, non-parameterized test
   cases, one per outcome state, both backend and mobile).
4. **architect** — review Decision 1's module-placement choice against `02_ARCHITECTURE.md`/ADR-051 (confirm the
   new `contact → search`/`contact → category` cross-module edges are justified and no circular dependency is
   introduced — `search`/`category` must never import anything from `contact`); Decision 2's route-mounting
   pattern against the `verification` module's existing precedent (confirm no inconsistency); Decision 3/Decision 4
   against `06_SECURITY.md`'s data-privacy principles (confirm the PII-minimization reasoning holds and no field
   was missed); Decision 5's outcome-status computation for correctness against the real `outcome_tags` schema
   (confirm the three-state mapping is exhaustive and cannot silently produce a fourth, unhandled case).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decisions 1–5 as new ADRs (next available: **ADR-054** onward), grouped where several decisions share
     one architectural theme, at `tech-lead`'s discretion at closeout.
   - Update `04_DATABASE.md`'s Contact Domain section to note the new read-only `LeadService`/`GET
     /providers/me/leads` consumer of `contact_views`/`outcome_tags` (no schema change — a documentation-only
     cross-reference update, mirroring how `REV-002`'s closeout documented `OutcomeTagRepository.
     get_by_contact_view_id` as a new consumer of an unchanged table).
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 10 section and `docs/AI/SESSION_HANDOFF.md` — `LEAD-001`
     becomes Done, `LEAD-002` becomes the next startable story in Milestone ML10/Epic ML10-EP01.

---

## Verification Plan (mapped to the 5 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | `test_lead_service.py`'s category-resolution and outcome-status cases; `test_lead_api.py`'s happy-path HTTP assertion of the exact `LeadResponse` field set; mobile widget tests confirming all three outcome chips and both category-context cases (resolved name / honest fallback) render with distinct copy. |
| 2 | `test_lead_service.py`'s ordering test (most-recent-first across a multi-row fixture); mobile widget tests confirming the empty state is genuinely wrapped in a working `RefreshIndicator` (not merely styled), and the loaded-list state is too. |
| 3 | `test_lead_api.py`'s literal wire-level assertion that no PII field/value (customer name, avatar, phone, raw `customer_id`) appears anywhere in a real response body, for a fixture customer who genuinely has that data set. |
| 4 | `test_lead_service.py`'s and `test_lead_api.py`'s explicit cross-provider fixtures (Provider A never sees Provider B's leads, at both the service and HTTP layers) plus the no-Provider-yet 404 case. |
| 5 | Three separately-named, non-parameterized test cases (one per outcome state) in both `test_lead_service.py` and the mobile `LeadsScreen` widget tests. |

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` (Contact View / Outcome Tag domain rules this Plan reads from, not extends)
- `docs/AI/04_DATABASE.md` (Contact Domain — `contact_views`/`outcome_tags`' exact shipped columns; Search Domain —
  `search_requests.category_id`'s nullable-FK deviation, ADR-038, this Plan's Decision 3 depends on)
- `docs/AI/09_DECISIONS.md` (ADR-038 — the nullable-column/no-fabrication precedent Decision 3 directly applies;
  ADR-044/ADR-048/ADR-049 — the `contact` module's existing shape/conventions this story continues; ADR-051 — the
  "one schema, one module" rule Decision 1 applies)
- `docs/AI/06_SECURITY.md` (Data Privacy / Sensitive Data sections — Decision 4's PII-minimization reasoning)
- `docs/implementation/plans/Plan_S08_CON-001.md` / `Walkthrough_S08_CON-001.md` (`contact_views`' shape and the
  `ContactService`/`NotificationService.notify_new_contact_view` zero-PII precedent Decision 4 extends)
- `docs/implementation/plans/Plan_S09_REV-001.md` / `Walkthrough_S09_REV-001.md` (`outcome_tags`' shape, and the
  exact Plan-document format this Plan mirrors)
- `docs/implementation/plans/Plan_S06_DIR-001.md` / `Plan_S08_MAT-001.md` (the `CollectionResponse`/
  `PaginationMeta` pattern and `GET /search/providers`'s exact pagination-clamping precedent Decision 2/Backend
  item 8 reuse)
- `docs/implementation/plans/Plan_S05_VER-001.md` (the `verification` module's `/providers/me/verification` mount
  precedent Decision 2 directly reuses)
- `docs/implementation/plans/Plan_S04_PRO-002.md` (`PortfolioService.list_my_portfolio`'s `_get_provider_or_404`
  ownership pattern this Plan's `LeadService.list_my_leads` mirrors)

---

**End of Document**
