# Walkthrough S10 LEAD-001

## Story: See And Manage My Provider Leads

**Sprint:** 10 | **Story ID:** LEAD-001 | **Priority:** High | **Status:** Done

As a provider, I want to see who viewed my contact info and whether they went on to hire me, so that I can gauge
real interest in my listing without needing customer-provider messaging, which doesn't exist in this product.
This story surfaces `CON-001`'s Contact Views and `REV-001`'s outcome tags as a provider-facing Leads list,
without exposing more customer PII than necessary. **Scope boundary:** does not include visibility analytics/
trend charts (`LEAD-002`) — this story is the raw lead list only.

Full context, the 5 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S10_LEAD-001.md`.

All work is committed and pushed to this branch across commits `e05747b` (backend), `03f1f5b` (frontend), and
`8e987c3` (a docstring fix resolving the architect's one finding — an `ADR-047` gap-naming requirement).

**This is Sprint 10 / Milestone ML10's first story.** With `LEAD-001` done, **Sprint 10 is 1 of 2 stories
complete — `LEAD-002` ("understand my listing visibility") remains.**

---

## What was implemented

### Backend — a new, read-only slice of the existing `contact` module (`backend/app/modules/contact/`)

No new table, no new column, no new migration — this story is a pure query layer over two already-shipped
tables (`contact_views`, `outcome_tags`), joined read-only against two more already-shipped tables owned by
other modules (`search.search_requests`, `category.categories`).

- **New `LeadService`** (`services/lead_service.py`, `list_my_leads`) resolves the caller's own `Provider` via
  the existing `ProviderService.get_my_provider` (404 via `ProviderNotFoundError` if none, mirroring
  `PortfolioService._get_provider_or_404`), then batch-resolves a page of Contact Views, their outcome tags, and
  their two-hop category context, entirely N+1-free.
- **Two new `ContactViewRepository` methods** (`list_for_provider`, `count_for_provider`) — provider-scoped,
  `viewed_at DESC, id ASC` ordering.
- **One new batch method each** on `OutcomeTagRepository` (`list_by_contact_view_ids`),
  `SearchRequestRepository` (`list_by_ids`), and `CategoryRepository` (`list_by_ids`) — plain `WHERE id IN (...)`
  batch fetches, avoiding a per-lead query for outcome tags or category context.
- **`GET /providers/me/leads`** (`contact/provider_lead_api.py`, its own `["Leads"]`-tagged router) is mounted
  at `/providers/me/leads`, registered in `api.py` directly alongside the existing `verification_router`'s own
  `/providers/me/verification` mount — the identical, already-shipped pattern for "a module other than
  `provider` owns a route under `/providers/me/...`." Bare `Depends(get_current_user)`, `CollectionResponse[
  LeadResponse]` with real `page`/`page_size` pagination (a fourth `Settings.LEADS_MAX_PAGE_SIZE` cap, following
  `SEARCH_MAX_PAGE_SIZE`/`CLAIM_SEARCH_MAX_PAGE_SIZE`'s precedent).
- **`LeadResponse`** carries exactly `id`, `category_name: str | None`, `viewed_at`, `outcome_status` — no
  `customer_id`, no `display_name`/`avatar_url`, no customer contact detail of any kind.
- **`LeadOutcomeStatus`** (`hired` / `not_hired` / `not_yet_reported`) is computed server-side from
  `outcome_tags.hired`'s presence/value — the mobile client never has to infer the third state from a
  missing/null field itself.

### Mobile — a new feature folder (`mobile/lib/features/leads/`)

- **`LeadsScreen`** — an `AppBar` titled "My Leads," a `RefreshIndicator`-wrapped `ListView.builder` of lead
  cards (category name or an honest fallback string when `null`; a relative-time label; a three-variant outcome
  chip mirroring `_VerificationStatusChip`'s existing chip-styling convention), a loading spinner, a retry-able
  error state, and a textually distinct, still-pull-to-refresh-able empty state.
- **`LeadsController`** (Riverpod) — `Status` enum (`idle`/`loading`/`error`/`loaded`), `load()`/`refresh()`.
- **`mobile/lib/shared/utils/relative_time.dart`** — a new, small, dependency-free relative-timestamp utility
  (`formatRelativeTime`), the first of its kind in this codebase; no new package dependency added.
- **`StorefrontScreen`** gained a new tappable "My Leads" entry-point card below `_VerificationStatusChip`,
  linking to a new `AppRoutes.leads` route — `features/provider/` still only imports the route constant, never
  `features/leads/` internals directly.

---

## The 5 Architecture Decisions, as actually shipped

All 5 decisions from `Plan_S10_LEAD-001.md` shipped exactly as planned, with no implementation-time deviations
to the decisions themselves (only the one architect finding described below, a docstring gap, not a design
change):

1. **Leads is a new read-only slice of the existing `contact` module, not a new `leads` module** — this story
   writes zero new tables, so there is no new schema for a standalone module to own; extending `contact` in
   place reuses its existing `contact_views`/`outcome_tags` ownership and its existing `contact → provider`
   edge, rather than inventing a new module purely to relocate the same data access behind an extra hop.
2. **The new route is mounted at `GET /providers/me/leads`, in a route module owned by `contact`**, mirroring
   `verification`'s exact `/providers/me/...` mount precedent — router-definition location and URL-path prefix
   are already decoupled concerns in this codebase.
3. **Category/request context resolves through `search_requests.category_id → categories.name`, with an
   explicit, honest `null` when either link in the chain is absent** — never a fabricated fallback (the
   provider's own primary category label, or raw `structured_criteria` free-text).
4. **Zero customer-identifying fields are ever included in `LeadResponse`** — no name, no avatar, no phone, no
   raw `customer_id` — continuing this codebase's already-shipped zero-customer-PII precedent for anything
   provider-facing about a Contact View.
5. **`outcome_status` is a plain three-value string enum, computed server-side** from `outcome_tags.hired`'s
   presence/value — never the raw boolean or a raw-row absence left for the client to interpret.

Grouped at this closeout into 2 ADRs by architectural theme (module placement; the two-hop honest-null
category-resolution pattern): **ADR-054** (Decision 1 — module placement, generalizing `ADR-051`'s rule from the
opposite direction, plus the `ADR-047` docstring-naming gap this story's own architect finding surfaced and
fixed) and **ADR-055** (Decision 3 — the two-independent-dead-end honest-null pattern, extending the
anti-fabrication principle to a chained-nullable-FK case with more than one distinct absence reason). Decision
2 (route mounting) is a direct, unmodified reuse of an already-ADR'd precedent (`verification`'s own mount
shape) and needed no new ADR; Decisions 4/5 are recorded in this Walkthrough and the Plan as direct, unmodified
continuations of already-established precedents (the zero-customer-PII posture from `CON-001`'s
`notify_new_contact_view`; the "backend commits to an explicit named state" convention already used at
`VER-002`), not standalone new architectural precedents in their own right.

---

## Review Process — a full, honest account

### `tester` — independent verification against real infrastructure, no bugs found

The tester independently verified all 5 verbatim ACs with real evidence (real DB, real HTTP round trips, real
widget tests) and found **no functional bugs and no gaps**. Coverage included:

- **AC1**: all three outcome states rendering with distinct copy/styling, both a resolvable and an unresolvable
  category context rendering correctly, at both the service and HTTP layers and in mobile widget tests.
- **AC2**: a real multi-row fixture confirming most-recent-first order end to end; the empty state genuinely
  wrapped in a working `RefreshIndicator` (a real pull gesture triggers a real refetch), not merely styled to
  look pull-to-refreshable.
- **AC3**: the literal wire-level assertion that no PII field/value appears anywhere in a real `GET
  /providers/me/leads` response body, for a fixture customer who genuinely has a `display_name`/`avatar_url`
  set — proving the omission is deliberate, not merely "no data existed to leak."
- **AC4**: the explicit cross-provider fixture, both at the service layer and over real HTTP, confirming
  Provider A never sees Provider B's leads under any query parameter, plus the no-Provider-yet 404 case.
- **AC5**: three separately-named, non-parameterized test cases (one per outcome state), both backend and
  mobile — including the second, distinct category dead-end case (a real `search_request_id` whose own
  `category_id` is `NULL`), tested independently rather than assumed to behave like the first dead-end
  (no `search_request_id` at all) by inspection alone.

Final counts: **783/783 backend tests (752 baseline + 31 new), 257/257 mobile tests (233 baseline + 24 new)**,
zero regressions in either suite.

### `architect` — one documentation-only finding, fixed and re-confirmed clean

The architect's review found **one real, non-blocking finding**: `contact/dependencies.py`'s docstring did not
yet explicitly name the two new cross-module raw-Repository edges this story introduces
(`search.SearchRequestRepository`, `category.CategoryRepository`) as instances of the `ADR-047` documented
exception — the wiring itself was correct (neither `search.SearchRequestService` nor `category.CategoryService`
expose an equivalent batch-lookup primitive today, so a raw Repository is the legitimate exception `ADR-047`
already allows), but `ADR-047`'s own text requires that gap to be *named explicitly* in the docstring, not
merely be true in fact. Fixed at commit `8e987c3` by adding the explicit naming; `architect` re-confirmed the
fix and returned a clean verdict on the re-check. Specifically confirmed, independently, not merely trusted:

- **Decision 1 (module placement)**: correct against `ADR-051`'s schema-ownership test read from the opposite
  direction — no new schema exists for a standalone `leads` module to own.
- **Cross-module edges**: `contact → search`/`contact → category` confirmed cycle-free (neither module imports
  anything from `contact`); `contact → provider` reuses the existing `ProviderService` edge, never a raw
  `ProviderRepository`, consistent with `ADR-047`'s default.
- **Decision 3/4 against `06_SECURITY.md`**: the PII-minimization reasoning holds; no customer-identifying field
  was missed in `LeadResponse`'s field set.
- **Decision 5's outcome-status computation**: the three-state mapping is exhaustive given `outcome_tags`'
  1:1 unique constraint — no fourth, unhandled case is reachable.

**Final verdict: clean, no findings that block sign-off, after the one docstring fix.**

### Final verdicts

- **`tester`**: all 5 ACs independently verified; **no bugs found, no gaps**.
- **`architect`**: one documentation-only finding (`ADR-047` docstring-naming gap), fixed and **re-confirmed
  clean**.
- **CTO sign-off** received after both final verdicts were presented, per standing process.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Leads screen lists Contact Views for the authenticated provider, each showing a category/request context, a relative timestamp, and an outcome status chip (Hired / Not hired / not yet reported) where available | Pass — `test_lead_service.py`/`test_lead_api.py`'s category-resolution and outcome-status cases; mobile widget tests confirming all three outcome chips and both category-context cases (resolved name / honest fallback) render with distinct copy |
| 2 | Leads are ordered most-recent-first and support the app's standard pull-to-refresh and empty-state patterns | Pass — a real multi-row fixture confirms most-recent-first order; mobile widget tests confirm the empty state is genuinely, not merely visually, pull-to-refreshable |
| 3 | No more customer PII is shown than necessary for the provider to recognize the lead | Pass — a literal wire-level assertion that no PII field/value appears anywhere in a real response body, for a fixture customer with real `display_name`/`avatar_url` data set |
| 4 | A provider can only see their own leads (ownership enforced, tested explicitly) | Pass — explicit cross-provider fixtures at both the service and HTTP layers, plus the no-Provider-yet 404 case |
| 5 | Automated tests cover the ownership boundary and correct outcome-status display across all three states | Pass — three separately-named, non-parameterized test cases (one per outcome state) in both `test_lead_service.py` and the mobile `LeadsScreen` widget tests |

**5 of 5 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded two new ADRs:
  - **ADR-054** — Leads module placement (Decision 1): extends `contact` in place, generalizing `ADR-051`'s
    schema-ownership rule from the opposite direction (zero new schema → fold into the module that already owns
    the primary data being surfaced), and records the `ADR-047` docstring-naming gap this story's own architect
    finding surfaced and fixed.
  - **ADR-055** — the two-independent-dead-end honest-null category-resolution pattern (Decision 3), extending
    the anti-fabrication principle (`ADR-038`) to a chained-nullable-FK case with more than one distinct absence
    reason.
- **`docs/AI/04_DATABASE.md`** — Contact Domain section updated with a documentation-only note: `contact_views`/
  `outcome_tags` now also back `LeadService`/`GET /providers/me/leads` as a new read-only consumer (no schema
  change), mirroring how `REV-002`'s closeout documented `OutcomeTagRepository.get_by_contact_view_id` as a new
  consumer of an unchanged table.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 10 section updated: 1 of 2 stories done (`LEAD-001`);
  `LEAD-002` remains, dependent on `LEAD-001`.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `LEAD-001`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect `LEAD-001` shipped, Sprint 10/Milestone ML10 now 1 of 2
  stories complete, ADR numbering advanced to ADR-055, test counts updated (783 backend / 257 mobile), and
  `LEAD-002` flagged as the next startable story (dependency known, full description/ACs not yet looked up).

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `LEAD-001` row** still needs its Status updated to "Done" and rolled up
  through ML10-EP01/ML10/SP10/the Phase Tracker/the Dashboard — per standing process, handled via the
  raw-XML-safe cell-patching procedure by the orchestrator, not performed by this closeout.
- **`LEAD-002`** ("understand my listing visibility") is Sprint 10's next story, depending on `LEAD-001` — its
  full verbatim description/acceptance criteria have not yet been fetched from `docs/AI/Project_Tracker.xlsx`;
  a fresh tracker lookup is needed before planning it, gated on an explicit CTO "Start X" instruction.

---

## Testing Performed

- `backend` implementation: new `contact` module test coverage (`test_lead_service.py`, `test_lead_api.py`), a
  new `test_contact_view_repository.py` (no prior test file existed for this repository), and extensions to
  `test_outcome_tag_repository.py`, the `search_request_repository` test file, and the `category` repository
  test file for each new batch `list_by_ids`/`list_by_contact_view_ids` method. Full suite green immediately
  after implementation: 783/783 (baseline 752, +31 new, zero regressions), `ruff check .` clean.
- `frontend` implementation: new `features/leads/` test coverage (controller tests for loaded/error/empty/
  pagination/refresh states; widget tests for `LeadsScreen` covering the empty state, all three outcome chip
  variants, the honest category fallback string, and relative-time formatting at fixed offsets), plus an
  extension to the Storefront screen test asserting the new Leads entry-point card navigates to `AppRoutes.leads`.
  Full suite green immediately after implementation: 257/257 (baseline 233, +24 new, zero regressions),
  `flutter analyze` clean.
- `tester` agent: independently verified all 5 ACs against real infrastructure (real DB, real HTTP round trips,
  real widget tests); no functional bugs or gaps found. Final: 783/783 backend, 257/257 mobile.
- `architect` agent: one documentation-only finding (the `ADR-047` docstring-naming gap), fixed at commit
  `8e987c3` and re-confirmed clean on a second pass.
- User (CTO) sign-off received after both final verdicts were presented.

---

## Key Files

### Backend
- `backend/app/core/config.py` (`LEADS_MAX_PAGE_SIZE`, new)
- `backend/app/modules/contact/repositories/contact_view_repository.py` (`list_for_provider`,
  `count_for_provider`, new)
- `backend/app/modules/contact/repositories/outcome_tag_repository.py` (`list_by_contact_view_ids`, new)
- `backend/app/modules/search/repositories/search_request_repository.py` (`list_by_ids`, new)
- `backend/app/modules/category/repositories/category_repository.py` (`list_by_ids`, new)
- `backend/app/modules/contact/services/lead_service.py` (`list_my_leads`, new)
- `backend/app/modules/contact/schemas.py` (`LeadOutcomeStatus`, `LeadResponse`, new)
- `backend/app/modules/contact/provider_lead_api.py` (`GET /providers/me/leads`, new)
- `backend/app/modules/contact/dependencies.py` (`get_lead_service`, new; docstring fix at `8e987c3` naming the
  `ADR-047` raw-Repository exception explicitly)
- `backend/app/api/v1/api.py` (`provider_lead_router` registered at `/providers/me/leads`)
- `backend/tests/modules/contact/test_lead_service.py`, `test_lead_api.py`, `test_contact_view_repository.py`
  (new)

### Mobile
- `mobile/lib/features/leads/domain/models/lead.dart`, `lead_exception.dart` (new)
- `mobile/lib/features/leads/data/lead_repository.dart` (new)
- `mobile/lib/features/leads/state/leads_controller.dart` (new)
- `mobile/lib/features/leads/presentation/screens/leads_screen.dart` (new)
- `mobile/lib/shared/utils/relative_time.dart` (new)
- `mobile/lib/features/provider/presentation/screens/storefront_screen.dart` (new Leads entry-point card)
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (`leads` route)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-054, ADR-055
- `docs/AI/04_DATABASE.md` — Contact Domain, new `LeadService` read-only consumer note
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 10 section updated (1 of 2 stories done)
- `docs/AI/SESSION_HANDOFF.md` — refreshed state, ADR numbering, test counts, `LEAD-002` flagged as next
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 10 / Milestone ML10 is now 1 of 2 stories complete** — `LEAD-001` is Done, `LEAD-002` remains.
- **`LEAD-002`** ("understand my listing visibility," depends on `LEAD-001`) is Sprint 10's next story. Its
  dependency is already known from this closeout's own tracker context, but its full verbatim
  description/acceptance criteria have **not yet been fetched** — the orchestrator must look it up fresh in
  `docs/AI/Project_Tracker.xlsx` before planning it, gated on an explicit CTO "Start X" instruction.
- **The two-independent-dead-end honest-null pattern (ADR-055) is now a documented precedent** for any future
  chained-nullable-FK context-resolution need — collapse every dead-end to one honest, textually distinct
  fallback, while still testing each dead-end as an independently named case.
- **`docs/AI/Project_Tracker.xlsx`'s `LEAD-001` row** still needs its Status flipped to "Done" and rolled up
  through ML10-EP01/ML10/SP10/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.

---

**End of Document**
