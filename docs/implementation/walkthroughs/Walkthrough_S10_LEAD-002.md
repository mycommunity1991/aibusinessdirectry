# Walkthrough S10 LEAD-002

## Story: Understand My Listing Visibility

**Sprint:** 10 | **Story ID:** LEAD-002 | **Priority:** Medium | **Status:** Done

As a provider, I want simple stats on how often I appear in search and how many people viewed my contact info,
so that I can tell whether my listing is actually working, without the platform building brand-new tracking
infrastructure just for this. This story reuses the Search Event Log and Contact Views that already exist for
other purposes, presenting them as a lightweight analytics view — consistent with the product's "reuse, don't
rebuild" principle. **Scope boundary:** does not include admin-facing platform-wide analytics (`ADM-002`) —
this is the single-provider visibility view only.

Full context, the 8 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S10_LEAD-002.md`.

All work is committed and pushed to this branch across commits `30c029c` (backend), `e7933a4` (frontend),
`2543edd` (tester's test additions, exposing a real bug), `e726bb5` (backend's fix for that bug), and `1802c5a`
(backend's fix for a follow-on architect finding the bug fix exposed).

**This is Sprint 10 / Milestone ML10's second and final story.** With `LEAD-002` done, **Sprint 10 and
Milestone ML10 are both fully complete — 2 of 2 stories done: `LEAD-001`, `LEAD-002`.**

---

## What was implemented

### Backend — a fourth, read-only slice of the existing `contact` module (`backend/app/modules/contact/`)

No new table, no new column, no new migration — this story is a pure aggregation-read layer over two
already-shipped tables owned by two different modules (`contact.contact_views`, `search.provider_matches`),
plus the already-shipped `providers` row for ownership.

- **New `VisibilityAnalyticsService`** (`services/visibility_analytics_service.py`,
  `get_my_visibility_analytics`) resolves the caller's own `Provider` via the existing
  `ProviderService.get_my_provider` (404 via `ProviderNotFoundError` if none, the same ownership gate
  `LeadService`/`PortfolioService` already use), computes a shared current/previous 30-day window boundary,
  and assembles two headline metrics plus one zero-filled 30-day daily series.
- **Two new methods on `ContactViewRepository`** (`count_for_provider_between`,
  `count_daily_for_provider_since`) and the mirrored pair on a **new cross-module edge**,
  `search.ProviderMatchRepository` (`count_for_provider_between`, `count_daily_for_provider_since`) — the
  latter is `contact`'s second raw-Repository edge into `search`, alongside the existing
  `SearchRequestRepository` (`LEAD-001`), under the documented `ADR-047` exception.
- **`GET /providers/me/visibility-analytics`** (`contact/provider_visibility_api.py`, its own `["Visibility
  Analytics"]`-tagged router) returns `VisibilityAnalyticsResponse` directly — one synthesized, non-paginated
  object (mirroring `GET /providers/me/availability`'s "always synthesize a fixed shape" precedent), not
  `CollectionResponse[T]`.
- **`VisibilityAnalyticsResponse`** carries exactly: `has_sufficient_data: bool`, `search_appearances`/
  `contact_views` (each `{ total_last_30_days, trend }`), and `daily_trend: list[VisibilityDailyPoint]` — two
  headline totals, two trend enums, one 30-entry daily series, one boolean. No customer id, no raw row, no
  `query_text`, no category breakdown, no per-event list of any kind (`06_SECURITY.md`'s non-discretionary
  Analytics PII rule).
- **`TrendDirection`** (`up`/`down`/`flat`) is computed server-side by comparing the current 30-day total
  against the immediately preceding 30-day total — `flat` when both are zero, `up` from a real zero baseline
  (never a fabricated percentage via division by zero), otherwise a config-driven ±10% (`Settings.
  VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT`) `flat` band around `up`/`down`.
- **`has_sufficient_data`** is `true` only when at least one of the two current-30-day totals is greater than
  zero — always computed and returned explicitly, never left for the mobile client to infer from zero values.

### Mobile — a new feature folder (`mobile/lib/features/visibility_analytics/`)

- **`VisibilityAnalyticsScreen`** — an `AppBar` titled "My Visibility," a `RefreshIndicator`-wrapped scrollable
  body: two headline stat cards (search appearances, contact views, each with a trend arrow/label), the new
  `VisibilityTrendChart` widget, a loading spinner, a retry-able error state, and — when
  `hasSufficientData` is `false` — a textually distinct, still pull-to-refreshable "not enough data yet" empty
  state replacing the stat cards/chart entirely.
- **`VisibilityTrendChart`** (`presentation/widgets/visibility_trend_chart.dart`) — a small, dependency-free
  `CustomPainter`-based widget rendering two color-coded, non-interactive bar/sparkline series over the 30 daily
  points, plus a small static legend. **This codebase's first chart of any kind, built without adding a new
  charting package** — `mobile/pubspec.yaml` gained no new dependency for this story.
- **`VisibilityAnalyticsController`** (Riverpod) — `Status` enum (`idle`/`loading`/`error`/`loaded`), `load()`/
  `refresh()`.
- **`StorefrontScreen`** gained a third tappable entry-point card, `_VisibilityAnalyticsEntryPointCard`, below
  the existing Leads card, linking to a new `AppRoutes.visibilityAnalytics` route — `features/provider/` still
  only imports the route constant, never `features/visibility_analytics/` internals directly.

---

## The 8 Architecture Decisions, as actually shipped

All 8 decisions from `Plan_S10_LEAD-002.md` shipped as planned, with one implementation-time deviation
described in full in the Review Process section below (Decision 4's window-boundary computation was tightened
after a real bug was found — see "The anchoring bug," below):

1. **Visibility Analytics is a fourth read-only slice of the existing `contact` module**, not a new
   `analytics`/`visibility` module, and not folded into `search`. Since ownership of the primary data is
   genuinely split 50/50 between `contact.contact_views` and `search.provider_matches` (unlike `LEAD-001`,
   where one module clearly dominated), this Plan applied a new, concrete tiebreaker beyond `ADR-054`'s own
   rule: **dependency-direction symmetry**. `contact` already held a one-directional edge toward `search`
   (`contact → search.SearchRequestRepository`, established by `LEAD-001`); `search` held zero edges toward
   `contact`. Extending `contact` again needed only one more edge in the already-established direction, rather
   than inventing a brand-new, opposite-direction `search → contact` edge with no precedent anywhere in this
   codebase.
2. **The per-provider "search appearances" metric is sourced from `search.provider_matches`, not
   `search.search_event_log`** — a table-reference correction, not a new tracking table. AC2's literal text
   named `search_event_log`, but that table has no `provider_id` column at all and structurally cannot answer a
   per-provider question. `provider_matches` (written in the same `_finalize_matches` operation, same already-
   shipped `search` schema) is the real, correctly-attributed source — zero new tables either way.
3. **`GET /providers/me/visibility-analytics` returns one synthesized, non-paginated object**, mirroring `GET
   /providers/me/availability`'s shape, not `CollectionResponse[T]` — there is no list to paginate here, only
   two headline numbers plus one fixed-length series.
4. **The 30-day daily series is assembled (zero-filled) in Python at the service layer**, not via a SQL
   `generate_series` — each repository method returns only the days that actually have at least one row;
   `VisibilityAnalyticsService` builds the full, zero-filled 30-day list by iterating the date range.
5. **The trend indicator is a three-state `up`/`down`/`flat` comparison against the immediately preceding
   30-day window**, never a fabricated percentage when that prior window is empty.
6. **`has_sufficient_data` is `true` only when at least one of the two current-30-day totals is greater than
   zero** — the server always computes and returns this boolean explicitly.
7. **No new mobile charting dependency** — a small, dependency-free `CustomPainter`-based dual-series trend
   chart, mirroring `LEAD-001`'s own `relative_time.dart` precedent of meeting a well-scoped, non-interactive
   display need without reaching for a package.
8. **The response carries aggregate counts only** — never `search_event_log.query_text`, never any
   customer-identifying field, never a drill-down to individual events.

Grouped at this closeout into 2 ADRs by architectural theme (module placement; window-boundary/timezone
correctness): **ADR-056** (Decision 1 — the dependency-direction-symmetry tiebreaker, extending `ADR-054` to
the "no single owner" case) and **ADR-057** (Decisions 4/5's window computation, corrected by the anchoring bug
below — plus the UTC-pinning discipline the fix's own follow-on architect finding established). Decision 2
(table-reference correction) is recorded in this Walkthrough and the Plan as a direct application of this
codebase's existing anti-fabrication principle (`ADR-038`) rather than a standalone new precedent — it is a
correction of an AC's prose, not a new architectural shape. Decisions 3, 6, 7, 8 are direct, unmodified
continuations of already-established precedents (`GET /providers/me/availability`'s synthesized-object shape;
`LeadOutcomeStatus`'s "backend commits to an explicit state" convention; `relative_time.dart`'s no-new-
dependency precedent; `CON-001`'s zero-customer-PII posture) and are recorded in the Plan, not given their own
ADR.

---

## Review Process — a full, honest account

### `tester` — one real bug found, with a genuinely reproducing test

The tester independently verified all 5 verbatim ACs against real infrastructure (real DB, real HTTP round
trips, real widget tests) and found **one real, functional bug**, not a theoretical concern:

**The anchoring bug.** The headline 30-day total and the 30-day chart series are supposed to be two consistent
views of the same underlying window of activity — a customer looking at the screen should be able to visually
cross-check the total against the sum of the chart's bars. The initial implementation computed them from two
*independently chosen* window boundaries: the headline total's window started at an exact instant,
`datetime.now(UTC) - timedelta(days=30)`, while the chart's daily buckets started at a calendar-day boundary
(today minus 29 days, at midnight). Both anchors are individually reasonable, but they are not the same
instant — near a day boundary, a real event falling in the gap between the two anchors (a few hours, depending
on what time of day the request happened to run) was counted by one view and not the other. The tester caught
this with a fixture that placed events specifically in that gap and asserted the headline total must equal the
sum of the chart's own daily counts — a genuinely reproducing test, not a theoretical timing argument. Fixed at
commit `e726bb5` by aligning the headline window's start boundary to the same calendar-day boundary the chart
already used, so both views are now computed from one shared window-boundary calculation (see `ADR-057`).
Independently re-verified by `tester` after the fix: 821/821 backend tests, 280/280 mobile tests passing, zero
regressions.

Coverage otherwise included:
- **AC1**: both headline stats and all three trend states (`up`/`down`/`flat`) rendering with distinct
  copy/styling, at both the service and HTTP layers and in mobile widget tests.
- **AC2**: the real 30-day fixture (the same one that exposed the anchoring bug) confirming the chart reflects
  the correct daily counts, sourced from `provider_matches`/`contact_views`, never fabricated or read from
  `search_event_log`.
- **AC3**: explicit cross-provider fixtures, both at the service layer and over real HTTP, confirming Provider
  A's stats never reflect Provider B's activity, plus the no-Provider-yet 404 case.
- **AC4**: the "not enough data yet" state rendering correctly for an all-zero fixture and remaining genuinely
  pull-to-refreshable, and correctly *not* rendering when only one of the two metrics is non-zero.
- **AC5**: the headline-aggregation and trend-computation test cases in `test_visibility_analytics_service.py`,
  each separately named, not collapsed into one parameterized case.

### `architect` — one follow-on, non-blocking finding, fixed and re-confirmed clean

The architect's review, run after the anchoring-bug fix was already in place, found **one additional real,
non-blocking finding**: the new `date_trunc('day', ...)` day-bucketing queries (`ContactViewRepository.
count_daily_for_provider_since`, `ProviderMatchRepository.count_daily_for_provider_since` — this codebase's
first such queries) relied implicitly on the database session's timezone GUC rather than pinning UTC
explicitly. This defaults to UTC today and produced no incorrect result in this story's own testing, but it is
a latent risk: a future session/connection-pool configuration difference could silently shift day-bucket
boundaries and reintroduce the exact class of divergence the anchoring-bug fix had just closed, with no code
change needed to trigger it. Fixed at commit `1802c5a` by pinning UTC explicitly in both queries
(`date_trunc('day', column AT TIME ZONE 'UTC')` or the SQLAlchemy equivalent), establishing the convention for
any future day-bucketing query in this codebase (`ADR-057`). `architect` re-confirmed the fix and returned a
clean verdict on the re-check. Specifically confirmed, independently, not merely trusted:

- **Decision 1 (module placement)**: the dependency-direction-symmetry tiebreaker correctly avoids introducing
  any circular cross-module edge — `search` still has zero imports from `contact`.
- **Decision 2**: `provider_matches` genuinely is the correct, queryable source for the per-provider search-
  appearances metric; `search_event_log` genuinely cannot answer this question.
- **The new `contact → search.ProviderMatchRepository` edge's `ADR-047` docstring-naming** — confirmed named
  explicitly this time (per `ADR-054`'s own closeout note flagging this as a recurring risk to watch for).
- **Decision 8 against `06_SECURITY.md`**: no `query_text`/customer-identifying field leaked into the response.
- **Decisions 5/6's computation logic**: no unhandled division-by-zero, no negative-count edge case, exhaustive
  trend-state coverage.

**Final verdict: clean, no findings that block sign-off, after the two fix rounds.**

### Final verdicts

- **`tester`**: one real bug found (the anchoring divergence), fixed and independently re-verified — all 5 ACs
  pass. 821/821 backend tests, 280/280 mobile tests, zero regressions.
- **`architect`**: one additional, non-blocking finding (the UTC-pin gap the bug fix exposed), fixed and
  **re-confirmed clean**.
- **CTO sign-off**: the CTO gave a standing instruction mid-session to proceed straight through closeout without
  an additional sign-off pause once both verdicts were clean — this closeout follows that instruction.

**This is the second story this Sprint/Milestone (Sprint 10 / Milestone ML10) to need a fix-and-recheck round**
— `LEAD-001` was clean on the first pass; `LEAD-002` needed two, back-to-back rounds (a real tester-found bug,
then a real architect-found follow-on gap the fix itself surfaced). Both are honest, worthwhile findings: the
anchoring bug was a genuine correctness issue a user could have actually seen (an inconsistent total vs. chart),
and the UTC-pin gap is real hardening against a config-driven regression of the exact same bug class, not a
stylistic nitpick.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Visibility Analytics screen shows two headline stats — search appearances and contact views — each with a short trend indicator | Pass — `test_visibility_analytics_service.py`'s five trend-computation cases (flat/flat, up-from-zero, up, down, flat-within-threshold); `test_provider_visibility_api.py`'s happy-path response-shape assertion; mobile widget tests confirming both stat cards and all three trend labels render with distinct copy |
| 2 | A 30-day trend chart is shown, sourced from `search_event_log` and `contact_views`, not a new tracking table | Pass (with the source corrected to `provider_matches`, `ADR-038`-style, per Decision 2/AC2's literal-vs-real-schema gap) — the daily-series zero-fill test (30 ascending entries, correct counts on populated days) and the anchoring-bug fix ensuring the chart and headline total agree; mobile widget/unit tests confirming `VisibilityTrendChart` renders the correct series without error |
| 3 | Data shown is scoped strictly to the authenticated provider's own listing (ownership enforced) | Pass — explicit cross-provider fixtures at both the service and HTTP layers, plus the no-Provider-yet 404 case |
| 4 | The screen degrades gracefully (a clear "not enough data yet" state) for a newly-onboarded provider with little or no history | Pass — three separately-named `has_sufficient_data` cases (both zero / one non-zero / both non-zero); mobile widget tests confirming the empty state renders only for the all-zero fixture and remains pull-to-refreshable |
| 5 | Automated tests cover the ownership boundary and correct aggregation of the two headline stats over the 30-day window | Pass — the headline-aggregation-correctness test (in-window vs. out-of-window counts) and the cross-provider ownership tests, plus the tester's own anchoring-bug regression test now permanently in the suite |

**5 of 5 Pass**, after the fix-and-recheck round described above.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded two new ADRs:
  - **ADR-056** — the dependency-direction-symmetry tiebreaker for module placement (Decision 1), extending
    `ADR-054`'s rule to the "no single owner" case.
  - **ADR-057** — the shared-window-boundary principle for two derived views of the same data (Decisions 4/5,
    as corrected by the anchoring bug), plus the UTC-pinning convention for `date_trunc`/day-bucketing SQL
    queries (the architect's follow-on finding).
- **`docs/AI/04_DATABASE.md`** — Search Domain section updated: `provider_matches` now notes
  `VisibilityAnalyticsService`/`GET /providers/me/visibility-analytics` as a new read-only consumer; the
  `search_event_log` entry now carries an explicit note that it has no `provider_id` column and cannot answer a
  per-provider question, pointing future readers at `provider_matches` instead — no schema change.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 10/Milestone ML10 marked fully complete (2 of 2
  stories done); Section 17 updated; next sprint/milestone flagged as not yet identified.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `LEAD-002`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect `LEAD-002` shipped, Sprint 10/Milestone ML10 fully
  complete, ADR numbering advanced to ADR-057, test counts updated (821 backend / 280 mobile), and the next
  sprint/milestone flagged as needing a fresh tracker lookup before any further planning.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `LEAD-002` row** still needs its Status updated to "Done" and rolled up
  through ML10-EP01/ML10/SP10/the Phase Tracker/the Dashboard, and the Dashboard's Current Milestone/Sprint
  pointers advanced past ML10/SP10 — per standing process, handled via the raw-XML-safe cell-patching procedure
  by the orchestrator, not performed by this closeout.
- **The next sprint/milestone's first story is not yet identified.** A fresh `Project_Tracker.xlsx` lookup is
  needed before any planning begins — this is explicitly separate from, and happens after, this closeout's own
  documentation updates.

---

## Testing Performed

- `backend` implementation: new `contact`/`search` test coverage
  (`test_visibility_analytics_service.py`, `test_provider_visibility_api.py`, extensions to
  `test_contact_view_repository.py` and the `provider_match_repository` test file). Full suite green
  immediately after implementation, `ruff check .` clean.
- `frontend` implementation: new `features/visibility_analytics/` test coverage (controller tests for
  loaded/error/not-enough-data/refresh states; widget tests for `VisibilityAnalyticsScreen` covering all three
  trend labels, the "not enough data yet" empty state, and the loaded chart), plus a Storefront screen test
  extension asserting the new entry-point card navigates to `AppRoutes.visibilityAnalytics`. Full suite green,
  `flutter analyze` clean.
- `tester` agent: independently verified all 5 ACs against real infrastructure; found and regression-tested one
  real bug (the headline/chart anchoring divergence), fixed at commit `e726bb5` and independently re-verified.
- `architect` agent: found one additional, non-blocking finding (the UTC-pin gap), fixed at commit `1802c5a`
  and re-confirmed clean on a second pass.
- **Final counts: 821/821 backend tests (783 baseline before this story + 38 net new across both fix rounds),
  280/280 mobile tests (257 baseline + 23 new), zero regressions in either suite.**
- CTO gave a standing instruction to proceed straight through closeout once both verdicts were clean, without an
  additional sign-off pause for this story.

---

## Key Files

### Backend
- `backend/app/core/config.py` (`VISIBILITY_ANALYTICS_WINDOW_DAYS`, `VISIBILITY_ANALYTICS_TREND_FLAT_THRESHOLD_PCT`, new)
- `backend/app/modules/contact/repositories/contact_view_repository.py` (`count_for_provider_between`,
  `count_daily_for_provider_since`, new — UTC-pinned per `ADR-057`)
- `backend/app/modules/search/repositories/provider_match_repository.py` (`count_for_provider_between`,
  `count_daily_for_provider_since`, new — UTC-pinned per `ADR-057`)
- `backend/app/modules/contact/services/visibility_analytics_service.py` (`get_my_visibility_analytics`, new —
  shared window-boundary computation per `ADR-057`)
- `backend/app/modules/contact/schemas.py` (`TrendDirection`, `VisibilityDailyPoint`, `VisibilityMetric`,
  `VisibilityAnalyticsResponse`, new)
- `backend/app/modules/contact/provider_visibility_api.py` (`GET /providers/me/visibility-analytics`, new)
- `backend/app/modules/contact/dependencies.py` (`get_visibility_analytics_service`, new; `ADR-047`
  docstring-naming for the new `search.ProviderMatchRepository` edge)
- `backend/app/api/v1/api.py` (`provider_visibility_router` registered at `/providers/me/visibility-analytics`)
- `backend/tests/modules/contact/test_visibility_analytics_service.py`, `test_provider_visibility_api.py` (new)
- `backend/tests/modules/search/test_provider_match_repository.py` (new or extended)

### Mobile
- `mobile/lib/features/visibility_analytics/domain/models/visibility_analytics.dart`,
  `visibility_analytics_exception.dart` (new)
- `mobile/lib/features/visibility_analytics/data/visibility_analytics_repository.dart` (new)
- `mobile/lib/features/visibility_analytics/state/visibility_analytics_controller.dart` (new)
- `mobile/lib/features/visibility_analytics/presentation/screens/visibility_analytics_screen.dart` (new)
- `mobile/lib/features/visibility_analytics/presentation/widgets/visibility_trend_chart.dart` (new —
  dependency-free `CustomPainter`, no new `pubspec.yaml` entry)
- `mobile/lib/features/provider/presentation/screens/storefront_screen.dart` (new Visibility Analytics
  entry-point card)
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (`visibilityAnalytics` route)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-056, ADR-057
- `docs/AI/04_DATABASE.md` — Search Domain, new `VisibilityAnalyticsService` read-only consumer note plus the
  `search_event_log` no-`provider_id` callout
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 10/Milestone ML10 marked fully complete
- `docs/AI/SESSION_HANDOFF.md` — refreshed state, ADR numbering, test counts, next-sprint lookup flagged as
  needed
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 10 / Milestone ML10 is now fully complete — 2 of 2 stories done: `LEAD-001`, `LEAD-002`.**
- **The next sprint/milestone's first story has not yet been identified.** A fresh `Project_Tracker.xlsx`
  lookup is required before any planning begins — this is a separate step from this closeout, performed by the
  orchestrator afterward.
- **`ADR-056`'s dependency-direction-symmetry tiebreaker is now a documented precedent** for any future
  zero-new-schema story whose data ownership splits roughly evenly between two modules: check schema ownership
  (`ADR-051`) → single dominant owner (`ADR-054`) → dependency-direction symmetry (`ADR-056`), in that order,
  before considering a new standalone module.
- **`ADR-057`'s shared-window-boundary principle and UTC-pinning convention are now documented precedents** for
  any future story computing two outputs that must stay consistent with each other (a summary and a detail
  series, or any two related aggregates), and for any future `date_trunc`/day-bucketing SQL query.
- **`docs/AI/Project_Tracker.xlsx`'s `LEAD-002` row** still needs its Status flipped to "Done" and rolled up
  through ML10-EP01/ML10/SP10/the Phase Tracker/the Dashboard, with the Dashboard's Current Milestone/Sprint
  pointers advanced — handled separately by the orchestrator via the raw-XML procedure, not performed by this
  closeout.

---

**End of Document**
