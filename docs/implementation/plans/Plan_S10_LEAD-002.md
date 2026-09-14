# Plan for Story LEAD-002 — Understand My Listing Visibility

**Sprint:** 10 (Leads & Visibility) | **Epic:** ML10-EP01 | **Milestone:** ML10 | **Priority:** Medium | **Depends
On:** LEAD-001 (done, this Sprint)

---

## Story (verbatim, `Project_Tracker.xlsx`, `LEAD-002` row — relayed by the orchestrator this session)

"As a provider, I want simple stats on how often I appear in search and how many people viewed my contact info, so
that I can tell whether my listing is actually working, without the platform building brand-new tracking
infrastructure just for this. This story reuses the Search Event Log and Contact Views that already exist for
other purposes, presenting them as a lightweight analytics view — consistent with the product's 'reuse, don't
rebuild' principle. Scope boundary: does not include admin-facing platform-wide analytics (ADM-002) — this is the
single-provider visibility view only."

## Acceptance Criteria (verbatim, 5 items)

1. Visibility Analytics screen shows two headline stats — search appearances and contact views — each with a
   short trend indicator.
2. A 30-day trend chart is shown, sourced from `search_event_log` and `contact_views`, not a new tracking table.
3. Data shown is scoped strictly to the authenticated provider's own listing (ownership enforced).
4. The screen degrades gracefully (a clear "not enough data yet" state) for a newly-onboarded provider with
   little or no history.
5. Automated tests cover the ownership boundary and correct aggregation of the two headline stats over the
   30-day window.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **`search.search_event_log` (AI-002, shipped) columns, confirmed from `backend/app/modules/search/models.py`**:
  `id`, `search_request_id` (nullable FK → `search_requests.id`), `customer_id` (nullable FK), `category_id`
  (nullable FK), `query_text` (nullable, raw customer free text), `result_count` (INTEGER, not null),
  `was_matched` (BOOLEAN, not null), `created_at`. **It has no `provider_id` column and no per-provider row at
  all** — it is a per-*search-request* event ("a search happened, N results, matched or not"), written exactly
  once per `search_requests` row by `SearchRequestService._finalize_matches`. There is structurally no way to
  answer "how many times did *this specific provider* appear in search" from this table alone — it does not carry
  which providers were in the result set.
- **`search.provider_matches` (AI-002, shipped) columns, confirmed from the same `models.py`**: `search_request_id`
  (FK), `provider_id` (FK, not null), `rank`, `match_score` (nullable), plus full `CommonColumnsMixin` (including
  `created_at`). This is "the ranked result set of a Search Request against Provider data" — **one row per
  `(search_request, provider)` pair that actually appeared in a result set** (`uq_provider_matches_request_provider`
  enforces at most one row per pair). Written in the exact same `_finalize_matches` call, on the same operation,
  as the `search_event_log` row for that request (`backend/app/modules/search/services/search_request_service.py`,
  confirmed line-by-line: `bulk_create` then `search_event_log_repository.create`, both inside `_finalize_matches`,
  covering both the automated-match and admin-manual-match paths). **This is the actual, real per-provider "I
  appeared in a search" record this story needs** — `search_event_log` cannot supply it; `provider_matches` can,
  without any new table, migration, or column (see Decision 2). No repository method today aggregates
  `provider_matches` by `provider_id`/date range — `ProviderMatchRepository` only has `bulk_create` and
  `list_for_search_request` (`backend/app/modules/search/repositories/provider_match_repository.py`) — this
  story's Backend items 2–3 add the missing aggregation methods.
- **`contact.contact_views` (CON-001, shipped) columns, confirmed from `Plan_S10_LEAD-001.md`'s own Verified
  Current State (reused, not re-derived)**: `customer_id`, `provider_id` (not null FK), `search_request_id`
  (nullable FK), `viewed_at` (not null, default `now()`), full `CommonColumnsMixin`. `ContactViewRepository`
  today has `list_for_provider`/`count_for_provider` (LEAD-001, unbounded — no date-range filter) — this story
  adds a bounded-range count and a daily-bucketed count (Backend item 1).
- **The `contact` module already has a one-directional, precedented edge toward `search`** (`contact →
  search.SearchRequestRepository`, established by `LEAD-001`, itself under the `ADR-047` raw-Repository exception
  since `SearchRequestService` exposes no equivalent batch-lookup primitive). **`search` has zero edges toward
  `contact`** — confirmed from `search/dependencies.py`: `SearchRequestService`'s cross-module deps are
  `administration`, `customer`, `provider` only, never `contact`. This asymmetry is a real, load-bearing input to
  Decision 1 below (which module gains one more edge vs. which module would need a brand-new, opposite-direction
  edge).
- **`06_SECURITY.md`'s Sensitive Data section is explicit**: "Sensitive data must never appear in: Logs, URLs,
  Exceptions, Analytics." `search_event_log.query_text` (raw customer free text) and any customer-identifying
  field are therefore never read or surfaced by this story at all — the two headline stats are pure counts,
  never per-event detail (Decision 8).
- **No paginated-collection shape is needed here** — unlike `LEAD-001`'s list-of-leads, this screen synthesizes
  exactly one object per caller. The precedent for a single, non-paginated, synthesized-per-caller response is
  `GET /providers/me/availability` (`04_DATABASE.md`: "always synthesizes exactly 7 entries... treating a missing
  row as..."), not `CollectionResponse[T]`.
- **`ProviderService.get_my_provider(user_id) -> Provider | None`** is the same already-shipped ownership
  primitive `LeadService`/`PortfolioService` already use (AC3's ownership gate — resolve the caller's own
  `Provider`, 404 via `ProviderNotFoundError` if none, then scope every query strictly to `provider.id`, never a
  client-supplied id).
- **The `/providers/me/...` mount pattern, and "a module other than `provider` owns a route mounted there," is
  already twice-precedented** (`verification`, then `contact/provider_lead_api.py` for `LEAD-001`) — this story's
  new route follows the identical shape a third time.
- **`mobile/pubspec.yaml` confirmed: no charting package of any kind exists today** (`fl_chart`, `syncfusion_*`,
  `charts_flutter` — none present). Every dependency in this file was added only when Flutter's SDK/existing code
  genuinely had zero built-in way to satisfy a hard requirement (camera/gallery access, arbitrary file browsing,
  `tel:`/`wa.me` launching, map rendering) — confirmed from each dependency's own inline comment. `LEAD-001`'s own
  `relative_time.dart` set the most recent, directly-relevant precedent: a small, well-scoped, non-interactive
  display need was met with a new dependency-free utility rather than reaching for a package
  (`08_CODING_STANDARDS.md`'s "avoid unnecessary packages"; `12_TECH_STACK.md`'s "Technology changes require CTO
  approval").
- **The Storefront entry-point pattern is fully established and directly reusable a second time**:
  `_VerificationStatusChip` and `_LeadsEntryPointCard` (`mobile/lib/features/provider/presentation/screens/
  storefront_screen.dart`) are both simple `InkWell`-wrapped, colored-container tiles reading only an
  `AppRoutes.*` constant, never importing another feature's internals directly. This story adds a third tile,
  `_VisibilityAnalyticsEntryPointCard`, in the same place, same shape.
- Current Alembic migration head is unaffected — **this story adds no new table, no new column, and needs no new
  migration**, exactly like `LEAD-001`. It is a pure aggregation-read layer over three already-shipped tables
  (`contact_views`, `provider_matches`, and indirectly the already-shipped `providers` row for ownership) — never
  `search_event_log` itself as a per-provider source (Decision 2), and never `search_requests.structured_criteria`
  or `search_event_log.query_text` (Decision 8).

---

## Architecture Decisions

### Decision 1 — Visibility Analytics is a fourth read-only slice of the existing `contact` module, not a new `analytics`/`visibility` module, and not folded into `search`

**The problem:** unlike `LEAD-001` (which read only from `contact`'s own tables plus read-only joins), this story
needs data from **two different modules' schemas** (`contact.contact_views` and `search.provider_matches`), with
no single table set it introduces of its own (zero new schema, same as `LEAD-001`). `ADR-054`'s rule — "a
capability that introduces no new schema at all... belongs inside whichever existing module's own data it is
primarily a view over" — assumed one module's data would clearly dominate. Here it doesn't: one headline stat is
`contact`'s own data, the other is `search`'s own data, roughly symmetric.

**Chosen:** extend `backend/app/modules/contact/` in place a second time (its fourth capability, after
`contact_views`/`outcome_tags`/`LeadService`): a new `VisibilityAnalyticsService`
(`services/visibility_analytics_service.py`), two new methods on the existing `ContactViewRepository`, a new
cross-module raw-Repository edge to `search.ProviderMatchRepository` (two new methods on it), a new schema in
`contact/schemas.py`, and a new route file (`contact/provider_visibility_api.py`) mounted separately. Since
ownership of the *primary data* is genuinely split 50/50, this Plan applies a second, concrete tiebreaker
`LEAD-001` itself already used in its own "Alternatives Considered" (Decision 1: "`contact` already depends on
`provider.ProviderService`... reusing an existing direction is simpler than inventing a new, opposite one"):
**dependency-direction symmetry**. `contact` already holds a one-directional, precedented edge toward `search`
(`contact → search.SearchRequestRepository`, `LEAD-001`); `search` holds *zero* edges toward `contact` today.
Extending `contact` again needs only one more edge in the *already-established* direction (a second
`search`-module Repository, `ProviderMatchRepository`, alongside the existing `SearchRequestRepository`); building
this inside `search` instead would require inventing a brand-new, opposite-direction `search →
contact.ContactViewRepository` edge that has no precedent anywhere in this codebase and risks the exact circular
cross-module shape `02_ARCHITECTURE.md` prohibits if a future story ever needed the reverse. This is a routine,
directly-precedented engineering call (mirrors `ADR-054`'s own reasoning, generalized to the "no single owner"
case), not a CTO-level decision — it changes no product behavior or scope.

**Alternatives considered and rejected:**
- **A new standalone `analytics`/`visibility` module.** Rejected for the exact reason `ADR-054` already
  established: this story introduces zero new schema, so there is nothing for a new module to meaningfully own —
  it would just relocate two existing modules' data access behind an extra hop, for zero isolation benefit.
- **Folding into `search` instead**, since `provider_matches` is `search`'s own table and "search appearances" is
  the more search-flavored of the two stats. Rejected — this is the reverse-direction problem above: `search`
  would need a brand-new `search → contact` edge that does not exist today and breaks the codebase's
  currently-consistent one-directional `contact → search` flow.
- **Folding into `provider`**, since the mobile framing is "provider self-service" (the same alternative
  `LEAD-001` considered and rejected). Rejected for the identical reason: `provider` has no existing edge to
  either `contact_views` or `provider_matches`; `contact` already has (or, after this story, will have) both.

### Decision 2 — The per-provider "search appearances" metric is sourced from `search.provider_matches`, not `search.search_event_log` — a table-reference correction, not a new tracking table

**The problem:** AC2's literal text names `search_event_log` as (one of) the two source tables. The Verified
Current State above confirms `search_event_log` carries no `provider_id` at all — it is structurally impossible
to compute a per-provider appearance count from it. Per this codebase's own anti-fabrication discipline (`ADR-038`
and onward: "make the column nullable and report the honest absence, never fabricate a value" — extended here to
"never claim a stat is sourced from a table it cannot actually be computed from"), this Plan does not silently
paper over the mismatch by, e.g., approximating "search appearances" as `search_event_log.result_count` summed
across a provider's category (which would count *every* provider's appearances in that category, not this
provider's own — a real fabrication of specificity).

**Chosen:** the per-provider search-appearances count and trend are computed from `search.provider_matches`
(`provider_id`, `created_at`) instead — a table in the same already-shipped `search` schema (`AI-002`), written in
the same operation as the `search_event_log` row for that request (Verified Current State), so AC2's actual intent
("not a new tracking table," "reuse, don't rebuild") is fully satisfied: **zero new tables are created**, the
data is genuinely the Search domain's own already-existing event history, just the correct table within it.
`search_event_log` remains genuinely unused by this story — there is no honest way to make it contribute a
per-provider count without joining through `provider_matches` anyway (via `search_request_id`), at which point
`provider_matches` alone is already sufficient and simpler. This is a routine, directly-investigated correction of
a table-name assumption in the AC's prose, not a data-availability gap — the underlying, correctly-attributed data
genuinely exists and is queryable today. Flagged for CTO awareness at Open Question 1 (non-blocking).

**Alternatives considered and rejected:**
- **Report "search appearances" as unavailable/not-yet-buildable.** Rejected — the real per-provider data exists
  today in `provider_matches`; declaring a gap here would itself be dishonest given the correct table is one hop
  away and already shipped.
- **Join `search_event_log` to `provider_matches` via `search_request_id` and read timestamps from
  `search_event_log.created_at` instead of `provider_matches.created_at`.** Considered — the two timestamps are
  written in the same `_finalize_matches` call and differ by, at most, sub-second DB round-trip time, immaterial
  for day-level bucketing. Rejected as unneeded complexity: `provider_matches.created_at` alone is sufficient and
  avoids an extra join for no behavioral difference.

### Decision 3 — `GET /providers/me/visibility-analytics` returns one synthesized, non-paginated object, mirroring `GET /providers/me/availability`'s shape, not `CollectionResponse[T]`

**The problem:** every other new "me"-scoped endpoint this Sprint (`GET /providers/me/leads`) returned a paginated
collection. This screen has no list to paginate — it is two headline numbers plus one fixed-length (30-entry)
series.

**Chosen:** `VisibilityAnalyticsResponse` is returned directly, unwrapped, mirroring the already-shipped
`GET /providers/me/availability`'s "always synthesizes exactly N entries" precedent rather than reusing
`CollectionResponse[T]`/`PaginationMeta`, which exist specifically for open-ended, page-able lists this response
is not.

**Alternatives considered and rejected:**
- **Wrapping the single object in `CollectionResponse` with one item.** Rejected — `CollectionResponse` exists for
  genuinely paginated collections; wrapping a single synthesized object in it would be a misuse of an existing
  shape for a case it wasn't designed for, and would force the mobile client to unwrap a list of one for no
  benefit.

### Decision 4 — The 30-day daily series is assembled (zero-filled) in Python at the service layer, not via a SQL `generate_series`

**The problem:** AC2's chart needs one data point per calendar day for the last 30 days, including days with zero
events, for both `contact_views` and `provider_matches`.

**Chosen:** each repository's new `count_daily_for_provider_since` method returns only the days that actually have
at least one row (`GROUP BY date_trunc('day', ...)`, plain SQL, no `generate_series`); `VisibilityAnalyticsService`
builds the full, zero-filled 30-day list in Python by iterating the date range and looking up each day in a
`dict` built from the repository's (sparse) rows, defaulting to `0`. This keeps repository SQL simple (mirrors
this codebase's consistent preference for simple, single-purpose queries plus service-layer assembly — e.g.
`LeadService`'s own batch-resolve-then-assemble shape) and avoids introducing this codebase's first
`generate_series` usage for a 30-row loop that is trivial in Python.

**Alternatives considered and rejected:**
- **A single SQL `generate_series(current_date - 29, current_date, '1 day')` LEFT JOIN per metric.** Rejected as
  unnecessary SQL complexity for a fixed, small (30-row) range with no performance concern either way.

### Decision 5 — The trend indicator is a three-state `up`/`down`/`flat` comparison against the immediately preceding 30-day window, never a fabricated percentage when that prior window is empty

**The problem:** AC1 asks for "a short trend indicator" per headline stat, with no specified calculation.

**Chosen:** for each metric, compare `total_last_30_days` (days 1–30 ago) against `total_previous_30_days` (days
31–60 ago). If the previous window is `0`: `flat` if the current window is also `0` (no change — both are
genuinely zero), otherwise `up` (a real increase from a real zero baseline, stated directionally, never as a
percentage that would require dividing by zero). If the previous window is `> 0`: compute the percentage change
and bucket it — `flat` within ±`VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT` (new config, default `10.0`),
`up`/`down` otherwise. This never fabricates a numeric percentage the mobile client would have to render (the
enum itself is the entire "short trend indicator" — an arrow/label, matching AC1's literal "short" wording), and
never divides by zero.

**Alternatives considered and rejected:**
- **Rendering an exact percentage change (e.g., "+40%") mobile-side.** Rejected — undefined/fabricated when the
  prior period is `0` (division by zero), and a bigger, more precise-looking claim than AC1's "short trend
  indicator" asks for or than this codebase's existing precedents (`LeadOutcomeStatus`'s own plain three-state
  enum, `06_SECURITY.md`'s general caution against over-precise derived claims) would encourage.
- **Comparing against the provider's own all-time average instead of the immediately preceding 30-day window.**
  Rejected — more complex, and "last 30 days vs. the 30 days before that" is the most direct, literal reading of
  "a 30-day trend chart" (AC2) extended to a one-number summary (AC1).

### Decision 6 — `has_sufficient_data` (AC4's gate) is `true` only when at least one of the two current-30-day totals is greater than zero; the server always computes and returns this boolean explicitly, never leaving the mobile client to infer it from zero values

**The problem:** AC4 requires "a clear 'not enough data yet' state... for a newly-onboarded provider with little
or no history," without specifying the exact threshold.

**Chosen:** `has_sufficient_data = (search_appearances.total_last_30_days > 0) or
(contact_views.total_last_30_days > 0)` — a newly-onboarded provider genuinely has zero rows in both tables for
the current window, so this is both the simplest and the most literal reading of "little or no history." The
backend always computes and returns this boolean explicitly (mirrors `LeadOutcomeStatus`'s own "the backend
commits to an explicit state" precedent, `LEAD-001` Decision 5) — the response body still carries the real
(all-zero) numbers and a fully zero-filled chart series alongside the flag, so the field contract never changes
shape between the two states; the mobile client branches purely on the boolean, never re-deriving "is this
enough" from the numbers itself.

**Alternatives considered and rejected:**
- **Gating on provider account age instead of current-window activity** (e.g., "not enough data" only if the
  Provider was created less than 30 days ago). Rejected — a provider who has been listed for 6 months but
  genuinely has zero search appearances and zero contact views is exactly the case AC4's "little... history" also
  describes, not only a brand-new signup; account age is a weaker, less direct signal than the real activity
  counts already being computed anyway.
- **Omitting the numeric fields entirely when insufficient**, forcing the mobile client to treat `null` as the
  signal. Rejected — this reintroduces the "does absence mean zero or unknown" ambiguity this codebase's
  anti-fabrication discipline (`ADR-038` onward) consistently avoids; an explicit boolean plus real zero values is
  strictly clearer.

### Decision 7 — No new mobile charting dependency: a small, dependency-free `CustomPainter`-based dual-series trend chart, not `fl_chart` or an equivalent package

**The problem:** `mobile/pubspec.yaml` has no charting package today (Verified Current State), and AC2 asks for "a
30-day trend chart."

**Chosen:** build a new, small, dependency-free widget (`VisibilityTrendChart`, `CustomPainter`-based) rendering
two simple bar/sparkline series (search appearances, contact views) over the 30 zero-filled daily points — no
axes, no zoom/pan, no tooltips, no legend interaction, since AC1 explicitly frames this as "a short trend
indicator" and AC2 asks only for a chart to be *shown*, not for any interactive charting feature. This mirrors
`LEAD-001`'s own `relative_time.dart` precedent exactly: a well-scoped, non-interactive display need met without a
new package, consistent with `08_CODING_STANDARDS.md`'s "avoid unnecessary packages" and `12_TECH_STACK.md`'s
"Technology changes require CTO approval" (every existing dependency in this codebase was added only when
Flutter's SDK/existing code had genuinely zero built-in way to meet a *hard* requirement — camera access, file
browsing, `tel:`/`wa.me` launching, map rendering — none of which apply to drawing 30 bars). This is judged a
routine call, not a close one, given how directly `relative_time.dart` precedents it; flagged briefly at Open
Question 2 for CTO awareness only (non-blocking) in case a richer, interactive chart is actually wanted for a
future iteration, which would then be a real, flagged new-dependency decision.

**Alternatives considered and rejected:**
- **Adding `fl_chart` (or an equivalent charting package).** Rejected for this story — would be this codebase's
  first-ever charting dependency, requiring CTO approval, for a requirement (`"short trend indicator"`/a shown
  30-day chart, no interactivity specified) a `CustomPainter` fully satisfies without one. Not ruled out forever —
  if the CTO wants a materially richer, interactive chart later, that is a deliberate, separate dependency
  decision, not something this Plan should smuggle in.

### Decision 8 — The Visibility Analytics response carries aggregate counts only — never `search_event_log.query_text`, never any customer-identifying field, never a drill-down to individual events

**The problem:** `06_SECURITY.md`'s Sensitive Data section states sensitive data (including anything
customer-identifying) must never appear in Analytics.

**Chosen:** `VisibilityAnalyticsResponse` carries only: two headline totals, two trend enums, one 30-day daily
series of plain integer pairs (`date`, count), and the `has_sufficient_data` boolean. No customer id, no raw
`search_event_log`/`contact_views` row, no `query_text`, no category breakdown, no per-event list of any kind.
This continues `LEAD-001`'s own zero-customer-PII precedent (Decision 4 there) one level further into aggregate
analytics, which `06_SECURITY.md` makes an explicit, non-discretionary requirement here (not just a privacy-
minimization preference, as it was framed for Leads).

**Alternatives considered and rejected:**
- **Including a "top category searched" or similar breakdown**, sourced from `search_event_log.category_id`/
  `provider_matches` joined to categories. Rejected — out of AC1/AC2's literal scope (two headline stats + one
  chart, not a category breakdown), and not requested by any AC; deferred implicitly, not decided here.

---

## Backend — Proposed Changes

1. **`backend/app/core/config.py`** — add two new `Settings` fields, following the existing config-driven-constant
   pattern (`CONVERSATION_CONFIDENCE_THRESHOLD`, `AI_MATCH_MAX_RESULTS`):
   - `VISIBILITY_ANALYTICS_WINDOW_DAYS: int = 30` — the trend-chart/headline window length, used for both the
     current window and the immediately preceding comparison window (Decision 5).
   - `VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT: float = 10.0` — the ± percentage-change band treated as
     `flat` rather than `up`/`down` (Decision 5).
2. **`backend/app/modules/contact/repositories/contact_view_repository.py`** — add two new methods:
   - `count_for_provider_between(provider_id, start, end) -> int` — bounded-range count on `viewed_at`, the
     counterpart to the existing unbounded `count_for_provider` (LEAD-001).
   - `count_daily_for_provider_since(provider_id, since) -> list[tuple[date, int]]` — `GROUP BY
     date_trunc('day', viewed_at)`, only days with at least one row (Decision 4).
3. **`backend/app/modules/search/repositories/provider_match_repository.py`** — add the mirrored pair:
   - `count_for_provider_between(provider_id, start, end) -> int` — bounded-range count on `created_at`.
   - `count_daily_for_provider_since(provider_id, since) -> list[tuple[date, int]]` — `GROUP BY
     date_trunc('day', created_at)`, only days with at least one row.
4. **New file `backend/app/modules/contact/services/visibility_analytics_service.py`** — `VisibilityAnalyticsService`:
   - Constructor deps: `ContactViewRepository`, `ProviderMatchRepository` (new cross-module edge, Decision 1),
     `ProviderService`.
   - `async def get_my_visibility_analytics(self, user_id: uuid.UUID) -> VisibilityAnalyticsData` (an internal
     dataclass, not yet the Pydantic response — mirrors `LeadService`'s "service returns raw domain data, API
     layer builds the schema" convention):
     1. `provider = await self.provider_service.get_my_provider(user_id)`; `ProviderNotFoundError()` if `None`
        (AC3, identical shape to `LeadService`/`PortfolioService`).
     2. Compute window boundaries: `now = datetime.now(UTC)`; `current_start = now -
        timedelta(days=settings.VISIBILITY_ANALYTICS_WINDOW_DAYS)`; `previous_start = current_start -
        timedelta(days=settings.VISIBILITY_ANALYTICS_WINDOW_DAYS)`.
     3. Four bounded-count calls (two metrics × current/previous window): `contact_view_repository.
        count_for_provider_between(provider.id, current_start, now)`,
        `..._between(provider.id, previous_start, current_start)`, and the mirrored pair on
        `provider_match_repository`.
     4. Two daily-bucket calls: `contact_view_repository.count_daily_for_provider_since(provider.id,
        current_start)`, `provider_match_repository.count_daily_for_provider_since(provider.id, current_start)`.
     5. Zero-fill both series into one aligned, ascending-date 30-entry list (Decision 4) via a small private
        helper, `_build_daily_series`.
     6. Compute each metric's `TrendDirection` via a small private helper, `_trend_for(current_total,
        previous_total)` (Decision 5).
     7. Compute `has_sufficient_data` (Decision 6).
     8. Return the assembled `VisibilityAnalyticsData`.
5. **`backend/app/modules/contact/schemas.py`** — add:
   - `TrendDirection` (`StrEnum`, mirroring `LeadOutcomeStatus`'s shape): `UP = "up"`, `DOWN = "down"`,
     `FLAT = "flat"`.
   - `VisibilityDailyPoint(BaseModel)`: `date: date`, `search_appearances: int`, `contact_views: int`.
   - `VisibilityMetric(BaseModel)`: `total_last_30_days: int`, `trend: TrendDirection`.
   - `VisibilityAnalyticsResponse(BaseModel)`: `has_sufficient_data: bool`, `search_appearances:
     VisibilityMetric`, `contact_views: VisibilityMetric`, `daily_trend: list[VisibilityDailyPoint]`. Deliberately
     carries no customer-identifying or per-event field (Decision 8).
6. **New file `backend/app/modules/contact/provider_visibility_api.py`** (Decision 1/3) — `router = APIRouter(tags=
   ["Visibility Analytics"])`; one route, `GET ""` → `GET /providers/me/visibility-analytics`, bare
   `Depends(get_current_user)` (mirrors `provider_lead_api.py`'s pattern exactly), returns
   `VisibilityAnalyticsResponse` directly (Decision 3, no `CollectionResponse` wrapper), 401 documented, 404
   documented ("the caller has not created a provider listing yet," identical wording to the Leads/Portfolio
   endpoints).
7. **`backend/app/modules/contact/dependencies.py`** — add:
   - Import `get_provider_match_repository`/`ProviderMatchRepository` from `search`'s existing
     `dependencies.py`/`repositories/provider_match_repository.py`.
   - `get_visibility_analytics_service`, wiring `VisibilityAnalyticsService`'s three constructor dependencies.
     Docstring must explicitly name `search.ProviderMatchRepository` as a second instance of the already-recorded
     `ADR-047` raw-Repository exception (alongside the existing `SearchRequestRepository`/`CategoryRepository`
     naming) — per `ADR-054`'s own closeout note that this naming duty is mandatory at implementation time, not
     an optional nicety left for `architect` to catch.
8. **`backend/app/api/v1/api.py`** — add `from app.modules.contact.provider_visibility_api import router as
   provider_visibility_router` and `v1_router.include_router(provider_visibility_router,
   prefix="/providers/me/visibility-analytics")`, placed directly after the existing `provider_lead_router` line.

### Tests

9. `backend/tests/modules/search/test_provider_match_repository.py` (new file, or extend the existing
   `provider_match_repository` test file if one already exists under a different name — check first) —
   `count_for_provider_between`/`count_daily_for_provider_since` correctness: rows inside vs. outside the
   window boundary (inclusive/exclusive edge cases), rows belonging to a *different* provider never counted,
   zero-row case returns `0`/`[]`.
10. `backend/tests/modules/contact/test_contact_view_repository.py` — extend with the mirrored
    `count_for_provider_between`/`count_daily_for_provider_since` cases.
11. `backend/tests/modules/contact/test_visibility_analytics_service.py` (new) — the core of AC3/AC4/AC5's
    coverage:
    - **Ownership (AC3):** no-Provider caller → `ProviderNotFoundError`. A fixture with Contact Views and
      `provider_matches` rows against both Provider A and Provider B asserts Provider A's
      `get_my_visibility_analytics` returns totals reflecting *only* Provider A's rows — the explicit
      cross-provider boundary test.
    - **Headline aggregation correctness (AC5):** a fixture with a known number of Contact Views and
      `provider_matches` rows inside the current 30-day window (and a known number *outside* it, both before day
      30 and inside the previous 30-day window) asserts `total_last_30_days` for both metrics exactly matches the
      in-window count, not the all-time count.
    - **Trend computation (Decision 5), each case separately named:** previous=0/current=0 → `flat`; previous=0/
      current>0 → `up`; previous>0 with a >10% increase → `up`; previous>0 with a >10% decrease → `down`;
      previous>0 within ±10% → `flat`.
    - **`has_sufficient_data` gate (AC4):** both totals `0` → `false`; only one metric non-zero → `true`; both
      non-zero → `true` — three separately-named cases.
    - **Daily series zero-fill (Decision 4):** a fixture with events on only 2 of the 30 days asserts the
      returned series has exactly 30 ascending-date entries, the 2 populated days carry the right counts, the
      other 28 are `0`.
12. `backend/tests/modules/contact/test_provider_visibility_api.py` (new) — full HTTP round trip: 200 happy path
    (asserts the exact `VisibilityAnalyticsResponse` field set, and that no PII/`query_text`/customer-identifying
    field is present anywhere in the raw JSON body); 404 (no Provider); 401 unauthenticated; a cross-provider
    fixture confirming Provider A's authenticated call never reflects Provider B's activity (AC3's HTTP-level
    counterpart); the "not enough data" fixture returns `has_sufficient_data: false` with real zero-filled data
    alongside it, not an omitted/null field set.
13. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

No new mobile dependency (Decision 7) — reuses `dio`/Riverpod/GoRouter and the existing `relative_time.dart`-style
"small dependency-free utility" precedent for the chart itself.

1. **New feature folder `mobile/lib/features/visibility_analytics/`** (a new feature — its own screen/state
   concerns, per `02_ARCHITECTURE.md`'s Feature-First convention, mirroring `features/leads/`'s own shape):
   - `domain/models/visibility_analytics.dart` — mirrors `VisibilityAnalyticsResponse`: `hasSufficientData`,
     `searchAppearances`/`contactViews` (each a small `VisibilityMetric { totalLast30Days, trend }` with a
     `TrendDirection` enum — `up`/`down`/`flat` plus an `unknown` fallback for forward-compatibility, mirroring
     `LeadOutcomeStatus`'s Dart-side parsing convention), `dailyTrend: List<VisibilityDailyPoint>` (`date`,
     `searchAppearances`, `contactViews`).
   - `domain/models/visibility_analytics_exception.dart` — mirrors `lead_exception.dart`'s per-feature
     exception-mapping convention (`notFound`, `network`, `unknown`).
   - `data/visibility_analytics_repository.dart` — `Future<VisibilityAnalytics> getMyVisibilityAnalytics()`,
     calling `GET /providers/me/visibility-analytics`, mapping errors via the same `_mapNotFoundOnlyError` shape
     `LeadRepository`/`ProviderRepository` already use.
   - `state/visibility_analytics_controller.dart` (Riverpod) — a `Status` enum (`idle`/`loading`/`error`/
     `loaded`, mirroring `LeadsController`), holding the loaded `VisibilityAnalytics`; exposes `load()`/
     `refresh()`.
   - `presentation/screens/visibility_analytics_screen.dart` (`VisibilityAnalyticsScreen`) — an `AppBar` titled
     "My Visibility," a `RefreshIndicator`-wrapped scrollable body when loaded: two headline stat cards (search
     appearances, contact views — each showing the 30-day total plus a small trend arrow/label per
     `TrendDirection`, mirroring `_VerificationStatusChip`'s icon+label chip convention), the
     `VisibilityTrendChart` widget (item 2) below them, a loading spinner, a retry-able error state (mirrors
     `_LoadError`), and — when `hasSufficientData` is `false` — a **textually distinct, still
     pull-to-refreshable "not enough data yet" empty state** replacing the stat cards/chart entirely (mirrors
     `_ZeroResultsEmptyState`'s exact `RefreshIndicator` + `LayoutBuilder` + `ConstrainedBox(minHeight: ...)`
     scrollable-when-empty shape, AC4's literal requirement).
2. **`mobile/lib/features/visibility_analytics/presentation/widgets/visibility_trend_chart.dart`** (Decision 7) —
   `VisibilityTrendChart`, a `CustomPainter`-based widget rendering two color-coded, non-interactive bar/sparkline
   series (search appearances, contact views) over the 30 daily points passed in; no axes/legend interactivity,
   a small static legend row (two colored dots + labels) below the drawing area for readability. Pure
   presentational widget — receives `List<VisibilityDailyPoint>`, computes nothing business-logic-related itself.
3. **`mobile/lib/features/provider/presentation/screens/storefront_screen.dart`** — add a third tappable card,
   `_VisibilityAnalyticsEntryPointCard`, below `_LeadsEntryPointCard`, linking to a new `AppRoutes.
   visibilityAnalytics` route — mirrors `_LeadsEntryPointCard`'s exact shape (reads only the route constant,
   never imports `features/visibility_analytics/` internals).
4. **`mobile/lib/core/routing/app_routes.dart`** — add `static const String visibilityAnalytics =
   '/visibility-analytics';`, documented mirroring the existing entries' doc-comment convention.
5. **`mobile/lib/core/routing/app_router.dart`** — add `GoRoute(path: AppRoutes.visibilityAnalytics, builder:
   (context, state) => const VisibilityAnalyticsScreen())` — no `extra` required.
6. **`mobile/lib/l10n/app_en.arb` / `app_ar.arb`** — new keys: `visibilityAnalyticsScreenTitle`,
   `visibilityAnalyticsSearchAppearancesLabel`, `visibilityAnalyticsContactViewsLabel`,
   `visibilityAnalyticsTrendUpLabel`, `visibilityAnalyticsTrendDownLabel`, `visibilityAnalyticsTrendFlatLabel`,
   `visibilityAnalyticsNotEnoughDataMessage`, `storefrontVisibilityAnalyticsEntryLabel`.

### Tests

7. `mobile/test/features/visibility_analytics/` — controller tests (`loaded`/`error`/`not-enough-data`/`refresh`
   states, using fixture responses for each); widget tests for `VisibilityAnalyticsScreen` (both headline stats
   render with the correct trend label for each of the three `TrendDirection` values, the "not enough data yet"
   empty state renders instead of the stat cards/chart when `hasSufficientData` is `false` and remains
   pull-to-refreshable, the loaded state's chart widget renders without error for a full 30-point fixture); a
   focused widget/unit test for `VisibilityTrendChart` confirming it paints without throwing for edge-case inputs
   (all zeros, a single non-zero day, 30 non-zero days).
8. `mobile/test/features/provider/` — extend `storefront_screen_test.dart` to assert the new entry point card is
   present and navigates to `AppRoutes.visibilityAnalytics` on tap.
9. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **Admin-facing platform-wide analytics** (`ADM-002`'s own named scope, the story's own literal scope-boundary
  sentence) — no cross-provider aggregation, no admin dashboard, no supply-gap/category-level reporting.
- **Any date-range customization** — the window is a fixed, config-driven 30 days (current) vs. the preceding 30
  days (trend comparison); no user-facing date picker or custom range.
- **A category/query-level breakdown of search appearances** — AC1/AC2 ask for two headline stats plus one chart,
  not a "top categories" or "top search terms" view; `search_event_log.query_text` is never surfaced (Decision 8,
  `06_SECURITY.md`).
- **CSV/data export of any kind.**
- **Any write path** — this story is read-only over already-shipped data; it writes nothing new.
- **A numeric percentage-change display** — the trend indicator is a plain three-state enum (Decision 5), not a
  precise percentage.
- **Per-provider timezone-aware day bucketing** — daily buckets are plain UTC calendar days (matching every
  `TIMESTAMPTZ` column's storage convention); no provider-timezone field exists anywhere in this codebase to
  bucket against instead, and no other feature does per-user-timezone bucketing today.
- **An interactive/zoomable/tooltip-bearing chart** — `VisibilityTrendChart` is a simple, static, non-interactive
  visual per Decision 7; a richer charting package remains a separate, future, CTO-approval-gated decision if
  ever wanted.
- **Push notifications or alerts based on visibility trends** — display-only, no triggered notification of any
  kind.

---

## Open Questions (flagged for CTO awareness — do not block `backend`/`frontend` from starting)

1. **Decision 2's table-reference correction.** AC2's literal text names `search_event_log` as a source table for
   "search appearances," but that table has no `provider_id` column and cannot answer a per-provider question at
   all — this Plan sources that stat from `search.provider_matches` instead (same already-shipped `search`
   schema, written in the same operation, zero new tables). This is investigated and resolved directly in this
   Plan (not a blocking gap — the real per-provider data exists and is used), included here purely so the CTO
   isn't surprised at review time that the shipped code reads a differently-named table than the AC's prose.
2. **Decision 7's no-new-dependency chart.** `VisibilityTrendChart` is a small, custom-painted, non-interactive
   widget rather than a full charting package (this codebase's first such dependency would otherwise require
   CTO approval per `12_TECH_STACK.md`). This Plan judges AC1/AC2's literal wording ("a short trend indicator,"
   "a chart is shown") as satisfied without one. If a materially richer, interactive chart is actually wanted,
   that is a separate, flagged new-dependency decision for a future iteration, not something this Plan
   unilaterally adds.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story (fresh start — Sprint 10's second and final story, `LEAD-001` already closed
out cleanly with no open Checkpoint left behind).

1. **backend** — Backend Proposed Changes items 1–13. Build order: (a) `config.py`'s two new settings first
   (item 1); (b) the four repository aggregation methods (items 2–3), each independently unit-testable in
   isolation (tests 9–10); (c) `VisibilityAnalyticsService` (item 4), with test 11 written alongside — Decision 5
   (trend thresholding) and Decision 6 (the `has_sufficient_data` gate) are this story's two correctness-critical
   mechanisms, read both in full before starting; (d) schema/route/dependency wiring (items 5–8), with test 12
   (the full HTTP round trip, including the no-PII-in-body assertion) last.
2. **frontend** — Frontend Proposed Changes items 1–9. Should start once `backend`'s `GET
   /providers/me/visibility-analytics` endpoint is available to integrate against (or in parallel against this
   Plan's documented `VisibilityAnalyticsResponse` shape, per this codebase's established parallelization
   practice), with a final integration pass once both are done. Pay particular attention to Decision 7's chart
   widget being genuinely dependency-free — no accidental `pubspec.yaml` addition.
3. **tester** — verify all 5 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget tests).
   Particular attention to: AC1 (both headline stats and all three trend states genuinely render distinct
   copy/styling); AC2 (a real 30-day fixture confirms the chart reflects the correct daily counts, sourced from
   `provider_matches`/`contact_views`, not fabricated or read from `search_event_log`); AC3 (the explicit
   cross-provider fixture, both at the service layer and over real HTTP, confirming Provider A's stats never
   reflect Provider B's activity); AC4 (the "not enough data yet" state renders correctly for an all-zero
   fixture and is genuinely pull-to-refreshable, and does *not* render for a fixture where only one of the two
   metrics is non-zero); AC5 (the headline-aggregation and trend-computation test cases in
   `test_visibility_analytics_service.py`, each separately named, not collapsed into one parameterized case).
4. **architect** — review Decision 1's module-placement tiebreaker (dependency-direction symmetry) against
   `ADR-051`/`ADR-054`/`02_ARCHITECTURE.md` (confirm no circular dependency is introduced — `search` must still
   have zero imports from `contact`); Decision 2's `provider_matches`-not-`search_event_log` sourcing for
   correctness against the real schema; the new `contact → search.ProviderMatchRepository` edge's `ADR-047`
   docstring-naming (confirm the gap is named explicitly this time, given `ADR-054`'s own closeout flagged this
   exact omission as a recurring risk); Decision 8 against `06_SECURITY.md`'s Sensitive Data section (confirm no
   `query_text`/customer-identifying field leaked into the response); Decision 5/6's computation logic for
   correctness and no silently-unhandled edge case (division by zero, negative counts, etc.).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decisions 1–8 as new ADRs (next available: **ADR-056** onward), grouped where several decisions share
     one architectural theme, at `tech-lead`'s discretion at closeout — Decision 1 (module placement tiebreaker)
     and Decision 2 (table-reference correction) are the two most likely candidates for a dedicated ADR each,
     given they generalize/correct existing precedents (`ADR-054`, the anti-fabrication principle) rather than
     merely reusing them unmodified.
   - Update `04_DATABASE.md`'s Search Domain section to note `provider_matches` as a new read-only consumer
     (`VisibilityAnalyticsService`/`GET /providers/me/visibility-analytics`) and, if judged worth an explicit
     callout, note that `search_event_log` itself is *not* a per-provider source (no `provider_id` column) — no
     schema change, documentation-only, mirroring `LEAD-001`'s own closeout update to the Contact Domain section.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 10 section — `LEAD-002` becomes Done, **Sprint
     10/Milestone ML10 becomes 2 of 2 stories complete**.
   - Update `docs/AI/SESSION_HANDOFF.md` accordingly (test counts, ADR numbering, next-sprint framing).

---

## Verification Plan (mapped to the 5 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | `test_visibility_analytics_service.py`'s trend-computation cases (all five: flat/flat, up-from-zero, up, down, flat-within-threshold); `test_provider_visibility_api.py`'s happy-path assertion of the exact response shape; mobile widget tests confirming both headline stat cards and all three trend labels render with distinct copy. |
| 2 | `test_visibility_analytics_service.py`'s daily-series zero-fill test (30 ascending entries, correct counts on populated days); mobile widget/unit tests confirming `VisibilityTrendChart` renders the correct series without error for a full 30-point fixture. |
| 3 | `test_visibility_analytics_service.py`'s and `test_provider_visibility_api.py`'s explicit cross-provider fixtures (Provider A's stats never reflect Provider B's activity, at both the service and HTTP layers) plus the no-Provider-yet 404 case. |
| 4 | `test_visibility_analytics_service.py`'s three separately-named `has_sufficient_data` cases (both zero / one non-zero / both non-zero); mobile widget tests confirming the "not enough data yet" empty state renders only for the all-zero fixture and remains pull-to-refreshable. |
| 5 | `test_visibility_analytics_service.py`'s headline-aggregation-correctness test (in-window vs. out-of-window counts) and the cross-provider ownership tests, both required by AC5's literal wording. |

---

## Related Documents

- `docs/AI/04_DATABASE.md` (Search Domain — `search_event_log`/`provider_matches`' exact shipped columns this
  Plan's Decision 2 depends on; Contact Domain — `contact_views`' exact shipped columns)
- `docs/AI/09_DECISIONS.md` (`ADR-038` — the nullable-column/no-fabrication precedent Decision 2 extends to a
  table-reference correction; `ADR-047` — the raw-Repository cross-module exception and its docstring-naming
  requirement Decision 1/Backend item 7 must honor; `ADR-051`/`ADR-054` — the module/schema placement rules
  Decision 1 applies and extends to the "no single owner" case)
- `docs/AI/06_SECURITY.md` (Sensitive Data section — Decision 8's non-discretionary aggregate-only requirement)
- `docs/AI/12_TECH_STACK.md` (Approved Flutter Packages / "Technology changes require CTO approval" — Decision
  7's no-new-dependency reasoning)
- `docs/implementation/plans/Plan_S10_LEAD-001.md` / `Walkthrough_S10_LEAD-001.md` (the `contact` module's
  existing shape/conventions this Plan continues a fourth time; the `relative_time.dart`
  no-new-dependency precedent Decision 7 directly mirrors; the `_LeadsEntryPointCard` Storefront pattern Frontend
  item 3 reuses)
- `docs/implementation/plans/Plan_S07_AI-002.md` (`search_event_log`/`provider_matches`' original design and the
  `_finalize_matches` shared-write mechanism Decision 2 relies on)
- `docs/implementation/plans/Plan_S08_CON-001.md` (`contact_views`' shape and the `ContactService` precedent this
  Plan's `VisibilityAnalyticsService` mirrors)
- `docs/implementation/plans/Plan_S04_PRO-002.md` (`GET /providers/me/availability`'s "synthesize a fixed-shape
  single object" precedent Decision 3 directly reuses)

---

**End of Document**
