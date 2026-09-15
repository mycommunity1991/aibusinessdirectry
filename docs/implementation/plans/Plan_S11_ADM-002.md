# Plan for Story ADM-002 — Operate the Marketplace from an Admin Dashboard

**Sprint:** 11 ("Marketplace Operations") | **Epic:** ML11-EP01 | **Milestone:** ML11 | **Priority:** Medium |
**Depends On:** VER-002 (done, Sprint 5) + ADM-001 (done, Sprint 11) — both satisfied

---

## Story (verbatim, `Project_Tracker.xlsx`, `ADM-002` row — relayed via `docs/AI/SESSION_HANDOFF.md` this session)

"As an administrator, I want a single dashboard summarizing verification queues, manual-match workload, and
platform configuration, so that I can operate the marketplace day-to-day without stitching together separate
tools. This story consolidates ADM-001 and VER-002's queues alongside feature-flag and system-configuration
management into one operational surface — the capstone of the Marketplace Operations sprint. Scope boundary:
does not add new admin capabilities beyond what ADM-001/VER-002 already implemented."

## Acceptance Criteria (verbatim, 6 items)

1. `feature_flags` and `system_settings` tables exist via migration (if not already present) and are editable
   only by admins.
2. Dashboard summarizes: pending verification count, pending manual-match count, and open unmatched-query-report
   count, each linking to its respective queue.
3. `admin_action_log` records every configuration change, feature-flag toggle, and queue action taken from this
   dashboard.
4. Feature flags can be toggled without a deploy and take effect for the next relevant request.
5. Non-admin access returns 403 across every dashboard endpoint.
6. Automated tests cover feature-flag toggling taking effect and `admin_action_log` recording every action type
   exercised by this story.

---

## Verified Current State (read directly from code and docs before writing this Plan)

### Investigation 1 — `feature_flags`/`system_settings` genuinely do not exist; AC1 is a real migration

Checked directly, not assumed, exactly the way `ADM-001`'s own planning caught the `unmatched_query_reports`
documentation slip:

- `backend/app/modules/administration/models.py` (read in full, post-`ADM-001`) defines exactly four model
  classes — `AdminActionLog`, `ClaimReviewRequest`, `ManualMatchAssignment`, `UnmatchedQueryReport`. **No
  `FeatureFlag` or `SystemSetting` class exists.**
- `backend/alembic/versions/` (globbed in full, 23 files) contains **zero migrations referencing
  `feature_flag`/`system_setting`** anywhere (`grep -r "feature_flag|system_setting" backend/alembic/versions/`
  returns no matches).
- `docs/AI/04_DATABASE.md` line 951 (`admin_action_log`'s own section, updated at `ADM-001`'s closeout): *"...
  `unmatched_query_reports` (below) has since shipped as its fourth slice (Story ADM-001, Sprint 11)... `feature_
  flags` and `system_settings` (below) remain unbuilt."* The full column-level spec already exists at lines
  1027–1046 — `feature_flags` (`key` VARCHAR(100) unique, `is_enabled` BOOLEAN default `false`, `description`
  TEXT nullable) and `system_settings` (`key` VARCHAR(100) unique, `value` JSONB not null, `description` TEXT
  nullable) — **designed and documented, explicitly labeled "remain unbuilt," not merely absent from
  discussion.**

**Conclusion: AC1 is a genuine new migration**, building both tables exactly to `04_DATABASE.md`'s pre-existing
spec, plus the full `CommonColumnsMixin` (per the file's own "every business table gets Common Columns unless
explicitly exempted" rule — only `audit_logs`/`search_event_log` are named exempt, neither of these two tables
is).

### Investigation 2 — platform scope: this Plan stays backend-only; the UI-suggestive framing does not name a concrete UI

The story's own text ("a single dashboard... consolidat[ing]... into one operational surface") never names
Flutter, mobile, or a separate internal tool — unlike its *absence* of `ADM-001`'s explicit "the admin platform
itself... remains an explicitly open decision" deferral sentence. This is a real difference in phrasing, not
nothing — investigated rather than assumed away:

- `mobile/lib/` was searched in full (`grep -ri admin`) — the only matches are incidental substring hits
  (`routed_to_admin`, "reviewed_by admin," a claim-repository doc comment) with **zero actual admin-facing
  screens, routes, or feature modules anywhere in the Flutter codebase.** Every admin capability shipped so far
  (`VER-002`, `CLM-001`'s admin side, `AI-002`'s admin side, `ADM-001`) is backend-API-only, with each own
  `admin_*_api.py`'s docstring stating this explicitly ("Backend-API-only — no dashboard UI exists or is
  expected here").
- All 6 ACs are fully, literally satisfiable by backend endpoints alone: AC1 (migration + admin-only CRUD
  endpoints), AC2 (one aggregation endpoint returning three counts + each queue's own existing path), AC3/AC4
  (service-layer/data changes with no UI dependency), AC5 (a role-check on backend routes), AC6 (backend
  automated tests). **No AC's literal wording requires a screen, a widget, or any rendered UI to be provably
  true** — every one of them is testable end-to-end via a real HTTP call.
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` (line 1134, at `ADM-001`'s own closeout) already frames the "admin
  dashboard UI" as a still-open, unbuilt item — this story's own text does not say it resolves that; it only
  says it *consolidates the backend queues and adds configuration management*, which is a data/API-shape
  statement, not a UI-shape one.

**Conclusion: this Plan is backend-only**, on the strength of every AC being satisfiable without one, and zero
precedent or codebase evidence of any admin UI existing to extend. This is still a genuine, flagged product-shape
judgment call, not something to silently resolve — see Open Question 1.

### `administration` module — confirmed shape (five files, four aggregate roots, one existing `api.py`)

`backend/app/modules/administration/{models,dependencies,api,schemas}.py` and both `repositories/`/`services/`
directories (all read in full, post-`ADM-001`) confirm: four aggregate roots (`AdminActionLog`,
`ClaimReviewRequest`, `ManualMatchAssignment`, `UnmatchedQueryReport`), one existing `api.py` (unmatched-query-
report routes only, mounted at `/admin/unmatched-query-reports`), and one existing outgoing cross-module edge
(`administration -> search.SearchEventLogService`, constructed directly inside `administration/dependencies.py`
to avoid a circular import with `search/dependencies.py`, which already imports `administration.dependencies` —
`ADR-060`).

### `AdminActionLogService` — confirmed shape: one explicit method today, and two of the three dashboard-linked queue actions do **not** currently write to it at all

`backend/app/modules/administration/services/admin_action_log_service.py` (read in full) exposes exactly one
method, `record_verification_review`, called by `verification/services/admin_verification_service.py`'s
`approve`/`reject` — **AC3's "queue action" requirement is already satisfied for the verification queue.**

Checked directly, not assumed, for the other two dashboard-linked queues (`grep -r "admin_action_log\|
AdminActionLog" backend/app/modules/`):

- **`ManualMatchAssignmentService.resolve`** (`administration/services/manual_match_assignment_service.py`, read
  in full) has **no `AdminActionLogService` dependency at all** and never writes an `admin_action_log` row when
  an admin resolves a manual-match assignment.
- **`UnmatchedQueryReportService.mark_reviewed`/`mark_actioned`** (`administration/services/
  unmatched_query_report_service.py`, read in full, `ADM-001`) likewise has **no `AdminActionLogService`
  dependency** and never logs a status transition.

**This is a real, evidence-based gap AC3 explicitly requires this story to close** — not new scope beyond
`ADM-001`/`VER-002` (the queue actions themselves already exist and are unchanged), but a genuine audit-logging
completeness fix the AC's own literal wording names directly ("every... queue action taken from this
dashboard"). See Decision 6.

### Count sources for AC2 — no existing repository method returns a bare count; every existing `list_*` method returns `(items, total)` together

`ManualMatchAssignmentRepository.list_pending`, `UnmatchedQueryReportRepository.list_filtered`, and
`VerificationRecordRepository.list_for_review` (all read in full) each compute a `COUNT(*)` internally but only
ever return it bundled with a full page of hydrated rows — no dedicated, standalone count-only method exists on
any of the three. Fetching a full page of rows (including PII-bearing fields such as `claimant_user_id`/
`customer_id`-adjacent context) just to read `total` for a dashboard headline number would be wasteful and
inconsistent with `02_ARCHITECTURE.md`'s Performance Principles and `06_SECURITY.md`'s data-minimization
posture. See Decision 4.

### `admin_action_log`'s cross-module edges for a dashboard-summary aggregation — a genuine new `administration -> verification` edge, with a real circular-import obstacle to avoid

`backend/app/modules/verification/dependencies.py` (read in full) already imports
`app.modules.administration.dependencies.get_admin_action_log_service` at module level — an established
`verification -> administration` edge (VER-002). If a new dashboard capability living in `administration` were
to import `verification.dependencies` back (even indirectly, via a Service constructed there), this would create
a genuine Python circular import (`administration.dependencies -> verification.dependencies ->
administration.dependencies`), the identical class of problem `ADR-060` already solved twice in `ADM-001` for
`search -> conversation` and `administration -> search`. See Decision 5.

### No existing feature-flag-gated behavior anywhere in this codebase; AC4 needs a genuine, real consumer to be honestly testable

`grep -ri "feature_flag\|FeatureFlag\|is_enabled"` across `backend/` (excluding this story's own soon-to-exist
code) returns zero matches beyond `04_DATABASE.md`'s own spec text. Every existing business-tunable value in this
codebase is either a `Settings`/env-config constant (`CONVERSATION_CONFIDENCE_THRESHOLD`,
`AI_MATCH_MAX_RESULTS`, `RANKING_WEIGHT_*`, etc. — all requiring a deploy/restart to change) or a hardcoded
constant. **None is toggleable at runtime without a deploy** — which is the entire, literal point AC4 asks
`feature_flags` to newly provide. A flag that is stored in the new table but read by nothing would make AC4's
own wording ("take effect for the next relevant request") and AC6's own wording ("automated tests cover
feature-flag toggling taking effect") both literally false to claim — this genuinely requires wiring at least
one real, meaningful runtime consumer, not inventing a new business capability gratuitously. See Decision 3.

`docs/AI/13_OPEN_DECISIONS.md` item 10 ("Degree of Manual (Wizard-of-Oz) Matching at Launch") is recorded as
still genuinely open: *"The mechanism now exists and works (AI-002 shipped it) — the product question of how
much matching should stay manual long-term at launch is still open."* `SearchRequestService.handle_session_
completed` (read in full, post-`ADM-001`) is the single dispatcher that decides, per session, whether to run the
automated matcher (`_handle_completed`) or create a `manual_match_assignments` row (`_handle_routed_to_admin`) —
today, purely based on the `status` string ("completed" vs. "routed_to_admin") the `conversation` module already
computed from `CONVERSATION_CONFIDENCE_THRESHOLD`. This dispatcher is the natural, minimal-blast-radius, already-
existing branch point to gate with a real flag.

### Admin role-check mechanism — confirmed, reused verbatim

`app/api/dependencies.py`'s `RequireRole`/`require_role(ROLE_ADMIN)` remains this codebase's entire
authorization boundary for every admin-only route (`AUTH-004`), reused unchanged for every new route in this
Plan (AC5).

---

## Architecture Decisions

### Decision 1 — `feature_flags`/`system_settings` do not exist yet; AC1 is a genuine new migration, built exactly to `04_DATABASE.md`'s pre-existing spec

Resolved above with direct file/line evidence. **Chosen:** one new migration creates both tables as
`administration`'s fifth and sixth aggregate roots (`FeatureFlag`, `SystemSetting`), each with the full
`CommonColumnsMixin` plus `04_DATABASE.md`'s literal columns (`key` VARCHAR(100) unique not null; `FeatureFlag.
is_enabled` BOOLEAN not null default `false`; `SystemSetting.value` JSONB not null; both get a nullable
`description` TEXT) — mirroring `34cd99dbf8db_unmatched_query_reports.py`'s exact template (same
`_common_columns()` helper, same FK-per-`created_by`/`updated_by` pattern). The same migration seeds exactly one
row per table (a data-seeding migration, directly precedented by `CTG-001`'s category-taxonomy seed and this
migration's own down_revision-adjacent sibling), so AC1's "editable" claim is genuinely exercisable end-to-end
by a test from day one, rather than leaving both tables permanently empty until some future, unspecified story
adds rows:
- `feature_flags`: `key="manual_matching_force_all"`, `is_enabled=false`, `description="When enabled, every
  conversation session that would otherwise auto-match is instead routed through manual admin review — a live,
  no-deploy operational lever for 13_OPEN_DECISIONS.md item 10."`
- `system_settings`: `key="support_contact_email"`, `value={"email": "support@aimarketplace.example"}`,
  `description="Contact email surfaced to internal admin tooling; editable without a deploy."`

**Alternatives considered and rejected:**
- **Leave both tables empty at creation, no seed.** Rejected — AC1's "editable" claim and AC6's "toggling takes
  effect"/action-log tests would have nothing real to edit/toggle without first inventing a row-creation API
  (rejected below, Decision 3) or a separate seed step nobody asked for.
- **A DB view or config-only (non-persisted) toggle.** Rejected — AC1's literal text asks for real tables, and
  "editable... by admins" requires a writable, durable row, mirroring `unmatched_query_reports`'s own "physical
  table, not a view" precedent.

### Decision 2 — Platform scope stays backend-only; flagged as a genuine Open Question, not silently assumed

Resolved above (Investigation 2) with direct evidence: zero admin-facing Flutter code exists anywhere, and every
one of the 6 ACs is fully satisfiable by a backend endpoint. **Chosen:** no Frontend section, no new Flutter
code — recommended default, flagged at Open Question 1 rather than silently carried over from `ADM-001` without
re-checking (the story's own phrasing genuinely differs from `ADM-001`'s explicit deferral sentence, which is why
this needed real investigation rather than an assumption).

**Alternatives considered and rejected:**
- **Build a minimal Flutter admin screen this story**, reading the new endpoints. Rejected for this iteration —
  no admin authentication/navigation shell exists anywhere in the mobile app to host it (the mobile app has no
  concept of an Admin-role user signing in at all), so this would require inventing an entire new mobile
  surface (login-as-admin, a new routing shell, a new `features/admin/` module) with no precedent and no ACs
  literally requiring it — a materially larger, unrequested scope expansion for a "Medium" priority story
  explicitly scoped as "does not add new admin capabilities beyond what ADM-001/VER-002 already implemented."

### Decision 3 — Feature-flag/system-setting **keys** are a known, finite, code-defined set; no admin-facing "create a new key" endpoint

**The problem:** should an admin be able to invent arbitrary new flag/setting keys via the API, or only edit
values for keys the codebase already knows about?

**Chosen:** mirror this codebase's own established "VARCHAR + application-level constant for a value set
expected to grow, never open-ended free-text creation" convention (`04_DATABASE.md`'s own stated preference,
already applied to `admin_action_log.action_type` and `notification.type`) — `feature_flags`/`system_settings`
rows are created only by a migration (Decision 1's seed), never by an API `POST`. The admin-facing surface is
`GET` (list all rows) + `PATCH /{key}` (edit an *existing* row only), raising a new 404
(`FeatureFlagNotFoundError`/`SystemSettingNotFoundError`) for an unknown key. A future story needing a new flag
adds a new migration + a new named constant the consuming code references — exactly how a new `notification.type`
value would be added today. This also directly serves AC4: a flag needs a real code consumer keyed by a known
constant regardless, so an open-ended "any string key" creation API would only ever produce dead, unread keys.

**Alternatives considered and rejected:**
- **A full `POST` "create a new flag/setting" endpoint accepting any key.** Rejected — produces unbounded,
  free-text keys with no way for any code to ever meaningfully consume them (a flag nothing reads cannot "take
  effect," AC4's own literal requirement), and has no precedent anywhere in this codebase for an open-ended,
  admin-invented extensible-value-set surface.

### Decision 4 — Three new, dedicated count-only repository methods, not a reuse of each `list_*` method's bundled `(items, total)`

Resolved above with direct evidence: no existing repository exposes a standalone count. **Chosen:**
`ManualMatchAssignmentRepository.count_pending() -> int`, `UnmatchedQueryReportRepository.count_by_status(status:
str) -> int` (called with `"open"`), `VerificationRecordRepository.count_for_review() -> int` — each a single
`SELECT count(*) WHERE ...` mirroring the exact `WHERE` clause its sibling `list_*` method already uses, with no
`OFFSET`/`LIMIT`/row hydration at all. Mirrors this codebase's established "small, single-purpose repository
methods" convention (every `try_*`/`list_*` method already does exactly one thing).

**Alternatives considered and rejected:**
- **Call each existing `list_*(page=1, page_size=1)` and read only `total`.** Rejected — still executes the
  full hydration/ordering query plan for at least one row and depends on an implementation detail (`total` being
  computed identically regardless of `page_size`) that a future refactor could silently break; a dedicated count
  query is simpler, cheaper, and self-documenting.

### Decision 5 — `administration -> verification` count-only edge, via a raw-Repository direct construction — a third application of `ADR-060`'s circular-import-avoidance principle

**The problem:** AC2's dashboard summary needs a pending-verification count, but that data lives in
`verification.VerificationRecordRepository`, and `verification.dependencies` already imports
`administration.dependencies` at module level (Verified Current State) — a same-direction import back
(`administration.dependencies -> verification.dependencies`) would be a genuine circular import, the identical
class of problem `ADR-060` already solved twice in `ADM-001`.

**Chosen:** `administration/dependencies.py` constructs `VerificationRecordRepository(db)` **directly** —
importing only `app.modules.verification.repositories.verification_record_repository` (a leaf module with no
edge back into `administration`), never `verification.dependencies`/`verification.services` — exactly mirroring
how `administration/dependencies.py` already constructs `SearchEventLogRepository(db)`/`SearchEventLogService(...)`
directly for the exact same reason (`ADM-001`, Decision 6/`ADR-060`). This is a raw-Repository edge (not a
Service), since the only thing needed is `count_for_review()` — a single, business-logic-free read with no
equivalent lightweight Service to reach for, and introducing a new, single-method `VerificationCountService`
purely to satisfy `ADR-047`'s "Services only" preference would be an unnecessary abstraction for one COUNT query
(`08_CODING_STANDARDS.md`'s "avoid unnecessary abstractions" rule). `administration/dependencies.py`'s own
docstring names this edge and its circular-import rationale explicitly, per `ADR-047`/`ADR-054`'s mandatory
naming-duty precedent.

**Alternatives considered and rejected:**
- **Host the dashboard-summary endpoint inside `verification` instead**, reusing its already-established
  `verification -> administration` edge direction (the `ADR-056` dependency-direction-symmetry tiebreaker).
  Considered seriously — but rejected because `administration` already owns **two of the three** counted
  sources (`manual_match_assignments`, `unmatched_query_reports`) plus the brand-new `feature_flags`/
  `system_settings` this same story introduces; hosting the dashboard in `verification` would need it to reach
  into `administration`'s own tables for two-thirds of the summary and would separate the dashboard's summary
  endpoint from the feature-flag/settings endpoints this same story adds to `administration` — a worse cohesion
  outcome than one new, narrow, well-justified opposite-direction edge for a single count.
- **A cross-schema SQL `JOIN`** (querying `verification.verification_records` directly from an
  `administration`-owned query). Rejected — same class of rejection as `ADM-001`'s Decision 6: a materially
  different and riskier pattern than this codebase's established Repository-per-schema convention, for no real
  benefit over a single, simple, separate count query.

### Decision 6 — `AdminActionLogService` gains four new explicit methods; `ManualMatchAssignmentService`/`UnmatchedQueryReportService` gain a new, intra-module `AdminActionLogService` dependency each

Resolved above: two of the three dashboard-linked queue actions do not currently log to `admin_action_log` at
all — a real gap AC3's literal text requires closing. **Chosen:** extend `AdminActionLogService`'s existing
"explicit methods, never one generic `record()`" convention (its own docstring's stated rule) with four new
methods:
- `record_manual_match_resolution(*, admin_user_id, assignment_id, provider_ids)` — `action_type=
  "manual_match_resolved"`, `target_entity_type="manual_match_assignment"`, `target_entity_id=assignment_id`,
  `metadata={"provider_ids": [str(p) for p in provider_ids]}`.
- `record_unmatched_query_report_transition(*, admin_user_id, report_id, to_status, category_gap_notes)` —
  `action_type=f"unmatched_query_report_{to_status}"` (i.e. `"unmatched_query_report_reviewed"`/
  `"...actioned"`), `target_entity_type="unmatched_query_report"`, `target_entity_id=report_id`,
  `metadata={"category_gap_notes": category_gap_notes}`.
- `record_feature_flag_toggle(*, admin_user_id, flag_id, key, is_enabled)` — `action_type=
  "feature_flag_toggled"`, `target_entity_type="feature_flag"`, `target_entity_id=flag_id`,
  `metadata={"key": key, "is_enabled": is_enabled}`.
- `record_system_setting_update(*, admin_user_id, setting_id, key, value)` — `action_type=
  "system_setting_updated"`, `target_entity_type="system_setting"`, `target_entity_id=setting_id`,
  `metadata={"key": key, "value": value}`.

Both `ManualMatchAssignmentService` and `UnmatchedQueryReportService` already live inside `administration` itself
alongside `AdminActionLogService` — this is a trivial **intra-module** constructor-injection addition (zero new
cross-module edges, zero circular-import risk), wired in `administration/dependencies.py`'s existing
`get_manual_match_assignment_service`/`get_unmatched_query_report_service` providers (both already import
`AdminActionLogService` in the same file). `ManualMatchAssignmentService.resolve` gains one new parameter,
`provider_ids: list[uuid.UUID]` (its only caller, `SearchRequestService.resolve_manual_match`, already has this
value available and threads it through) so the log entry can record which providers were selected — an
in-place, additive signature change, not a parallel method (`ADR-042`-style). `verification`'s existing
`record_verification_review` call path is untouched (already correct, confirmed above).

**Alternatives considered and rejected:**
- **Log from the route handler instead of the service layer.** Rejected — every existing precedent
  (`AdminVerificationService.approve`/`reject`) logs from inside the Service that performs the action, not the
  route; keeping business logic (including "this counts as a loggable action") out of controllers is
  `02_ARCHITECTURE.md`'s own explicit rule ("business logic must never exist inside API routes").
- **One generic `record(action_type: str, ...)` method** instead of four named ones. Rejected — directly
  contradicts `AdminActionLogService`'s own existing, explicit docstring convention, established at `VER-002`
  and never revisited since.

### Decision 7 — `manual_matching_force_all`'s real AC4 consumer: gates `SearchRequestService.handle_session_completed`'s automated-vs-manual dispatch

Resolved above (Verified Current State): this is the single, already-existing branch point deciding automated
vs. manual resolution, and ties directly to `13_OPEN_DECISIONS.md` item 10's still-open product question.
**Chosen:** at the top of `handle_session_completed`, when `status == "completed"`, first check
`feature_flag_service.is_enabled("manual_matching_force_all")` — if `true`, call `_handle_routed_to_admin` (the
existing manual-queue path) instead of `_handle_completed` (the existing automated path); an already-
`routed_to_admin` session is unaffected either way (it was always going to the manual queue regardless of this
flag). `SearchRequestService` gains one new constructor dependency, `administration.services.feature_flag_
service.FeatureFlagService` — a new `search -> administration` edge, but the **same, already-established
direction** as the two existing ones (`ManualMatchAssignmentService`/`UnmatchedQueryReportService`), so this
requires no new circular-import analysis (`search/dependencies.py` already imports `administration.
dependencies` safely). `FeatureFlagService.is_enabled(key)` returns `False` for an unknown key (anti-fabrication
— absence is honestly reported as "disabled," never assumed "enabled"). No change to `conversation`'s own
confidence-threshold logic or `conversation_sessions.status` semantics — a session can genuinely, honestly have
`conversation_sessions.status="completed"` (the AI really did resolve a category) while its `search_requests`
row is manually resolved, because this flag is a **marketplace matching-policy** decision, a separate concern
from **conversation completion**, exactly mirroring how `search`'s own existing `status` dispatch already treats
these as independent concerns today.

**Alternatives considered and rejected:**
- **A no-op flag, stored but read by nothing.** Rejected outright — fails AC4's own literal wording ("take
  effect for the next relevant request") and makes AC6's own literal wording ("automated tests cover
  feature-flag toggling taking effect") impossible to satisfy honestly; a test asserting "the flag exists in the
  database" would not be testing "taking effect."
- **A blunt, customer-facing "maintenance mode" kill switch** (e.g. rejecting `POST /conversations` entirely
  when a flag is on). Considered seriously as a more conventional first feature-flag example — rejected in favor
  of the narrower, better-precedented choice: this alternative blocks *all* new customer intake (a much larger
  blast radius for this story's first-ever flag) and has no connection to any already-flagged open product
  question, whereas `manual_matching_force_all` directly operationalizes `13_OPEN_DECISIONS.md` item 10 with
  minimal, well-contained risk (it only changes which of two already-existing, already-tested branches
  `handle_session_completed` takes).
- **Gate `SearchService.search_providers`/`ProviderSearchRepository.search_nearby`** (DIR-001's own customer-
  facing browse endpoint) instead. Rejected — that path has no Wizard-of-Oz/manual-queue concept at all; gating
  it would mean inventing an entirely new "browse is disabled" behavior with no existing precedent or open
  product question motivating it, unlike the chosen dispatch point.

### Decision 8 — Feature-flag/system-setting writes use a plain `update`, not a `try_*`-prefixed atomic conditional `UPDATE`

**The problem:** should toggling a flag or editing a setting use this codebase's established atomic-conditional-
`UPDATE`-with-`rowcount`-check pattern (`try_resolve`/`try_transition_status`/`try_claim_for_review`)?

**Chosen:** no — that pattern exists specifically to make a **forward-only workflow-state transition** race-safe
("exactly one caller may ever win *this* transition," e.g. resolving a pending queue item exactly once). Setting
a flag's `is_enabled`/a setting's `value` has no such "exactly once" semantics: it is a plain, idempotent,
last-write-wins configuration write, not a state-machine transition — if two admins concurrently set the same
flag, the expected, correct outcome is simply whichever write commits last, not a 409 rejection. `BaseRepository.
update` (already inherited by every repository) is reused directly, keyed by looking the row up by `key` first
(a 404 `FeatureFlagNotFoundError`/`SystemSettingNotFoundError` if the key is unknown, per Decision 3).

**Alternatives considered and rejected:**
- **Force every write through the `try_*` atomic pattern regardless, for consistency.** Rejected — mechanically
  applying a pattern designed for a distinct problem (queue-item race safety) to a problem that doesn't have
  that race (config value writes) would be pattern-matching without understanding *why* the pattern exists; this
  codebase's own established discipline (`ADR-053`: "reuse for an identical reason, only add new for a
  genuinely distinct one") cuts the other way here — these are genuinely distinct problems.

---

## Backend — Proposed Changes

1. **New migration** `backend/alembic/versions/<timestamp>-<hash>_feature_flags_and_system_settings.py`
   (down_revision = `34cd99dbf8db`, the current head) — creates `administration.feature_flags` (`key`
   VARCHAR(100) not null unique, `is_enabled` BOOLEAN not null server default `false`, `description` TEXT
   nullable, plus full `CommonColumnsMixin`) and `administration.system_settings` (`key` VARCHAR(100) not null
   unique, `value` JSONB not null, `description` TEXT nullable, plus full `CommonColumnsMixin`) — mirrors
   `34cd99dbf8db_unmatched_query_reports.py`'s exact template (`_common_columns()` helper,
   `created_by`/`updated_by` FKs). Seeds exactly one row per table (Decision 1's literal seed values) via
   `op.bulk_insert`/`op.execute`, mirroring `a804c46bf703_category_domain.py`'s data-seeding precedent.
   Constraints: `uq_feature_flags_key`, `uq_system_settings_key`. No new indexes beyond the unique constraints
   (both tables are small, finite, code-defined sets — no query pattern needs a secondary index).
2. **`backend/app/modules/administration/models.py`** — add `FeatureFlag(CommonColumnsMixin, Base)` and
   `SystemSetting(CommonColumnsMixin, Base)`, matching item 1's columns exactly.
3. **New file `backend/app/modules/administration/repositories/feature_flag_repository.py`** —
   `FeatureFlagRepository(BaseRepository[FeatureFlag])`: `get_by_key(key: str) -> FeatureFlag | None`;
   `list_all() -> list[FeatureFlag]` (ordered by `key`).
4. **New file `backend/app/modules/administration/repositories/system_setting_repository.py`** —
   `SystemSettingRepository(BaseRepository[SystemSetting])`: `get_by_key(key: str) -> SystemSetting | None`;
   `list_all() -> list[SystemSetting]` (ordered by `key`).
5. **New file `backend/app/modules/administration/services/feature_flag_service.py`** —
   `FeatureFlagService(repository, admin_action_log_service)`:
   - `async def is_enabled(self, key: str) -> bool` — returns `False` if the key doesn't exist (Decision 7,
     anti-fabrication default). **This is the method `SearchRequestService` calls (item 12).**
   - `list_all() -> list[FeatureFlag]`.
   - `toggle(key: str, *, is_enabled: bool, admin_user_id: uuid.UUID) -> FeatureFlag` — 404
     `FeatureFlagNotFoundError` if unknown; `self.repository.update(flag, {"is_enabled": is_enabled})`, then
     `admin_action_log_service.record_feature_flag_toggle(...)` (Decision 6/8 — plain update, then log).
6. **New file `backend/app/modules/administration/services/system_setting_service.py`** —
   `SystemSettingService(repository, admin_action_log_service)`:
   - `list_all() -> list[SystemSetting]`.
   - `update_value(key: str, *, value: Any, admin_user_id: uuid.UUID) -> SystemSetting` — 404
     `SystemSettingNotFoundError` if unknown; plain `update`, then `admin_action_log_service.
     record_system_setting_update(...)`.
7. **`backend/app/modules/administration/repositories/manual_match_assignment_repository.py`** — add
   `count_pending() -> int` (Decision 4, mirrors `list_pending`'s exact `WHERE status = 'pending'` clause, no
   `OFFSET`/`LIMIT`).
8. **`backend/app/modules/administration/repositories/unmatched_query_report_repository.py`** — add
   `count_by_status(status: str) -> int` (Decision 4, mirrors `list_filtered`'s `WHERE status = :status` clause).
9. **`backend/app/modules/verification/repositories/verification_record_repository.py`** — add
   `count_for_review() -> int` (Decision 4, mirrors `list_for_review`'s exact `_REVIEWABLE_STATUSES` clause).
10. **New file `backend/app/modules/administration/services/dashboard_service.py`** —
    `DashboardService(manual_match_assignment_repository, unmatched_query_report_repository,
    verification_record_repository)`: `async def get_summary(self) -> DashboardSummary` (a small internal
    dataclass/NamedTuple), returning the three counts (Decision 4's new methods) plus each queue's own,
    already-registered path string (`/admin/verification/records`, `/admin/search/manual-matches`,
    `/admin/unmatched-query-reports` — Decision-documented literal constants, never derived/guessed) for AC2's
    "each linking to its respective queue."
11. **`backend/app/modules/administration/services/admin_action_log_service.py`** — add the four new explicit
    methods from Decision 6 (`record_manual_match_resolution`, `record_unmatched_query_report_transition`,
    `record_feature_flag_toggle`, `record_system_setting_update`); update the class's own docstring (its
    "exposes one explicit method" claim no longer applies).
12. **`backend/app/modules/administration/services/manual_match_assignment_service.py`** — constructor gains
    `admin_action_log_service: AdminActionLogService`; `resolve` gains a new `provider_ids: list[uuid.UUID]`
    parameter and, after a successful `try_resolve`, calls `admin_action_log_service.
    record_manual_match_resolution(admin_user_id=..., assignment_id=..., provider_ids=provider_ids)` (Decision 6).
13. **`backend/app/modules/search/services/search_request_service.py`** — `resolve_manual_match` passes its own
    `provider_ids` argument through to `manual_match_assignment_service.resolve(...)`'s new parameter (item 12);
    constructor gains `feature_flag_service: FeatureFlagService` (Decision 7); `handle_session_completed` gains
    the new flag check (Decision 7) before dispatching to `_handle_completed`/`_handle_routed_to_admin`. Update
    the module's own top-of-file docstring to name this fourth `search -> administration` edge.
14. **`backend/app/modules/administration/services/unmatched_query_report_service.py`** — constructor gains
    `admin_action_log_service: AdminActionLogService`; `mark_reviewed`/`mark_actioned` (via the shared
    `_transition` helper) call `admin_action_log_service.record_unmatched_query_report_transition(admin_user_id=...,
    report_id=..., to_status=to_status, category_gap_notes=category_gap_notes)` after a successful transition
    (Decision 6).
15. **`backend/app/modules/administration/dependencies.py`**:
    - Add `get_feature_flag_repository`/`get_feature_flag_service`, `get_system_setting_repository`/
      `get_system_setting_service`, `get_dashboard_service` (the latter also constructs
      `VerificationRecordRepository(db)` **directly**, per Decision 5 — docstring names the circular-import
      rationale explicitly, mirroring `_get_search_event_log_service_for_administration`'s own existing
      docstring shape).
    - Extend `get_manual_match_assignment_service`/`get_unmatched_query_report_service` to also inject
      `admin_action_log_service` (Decision 6, item 6's dependency addition).
16. **`backend/app/modules/search/dependencies.py`** — add `get_feature_flag_service` import from
    `administration.dependencies` (mirrors the two existing `search -> administration` imports exactly); extend
    `get_search_request_service`'s signature with the new `feature_flag_service` dependency.
17. **New file `backend/app/modules/administration/schemas.py` additions** (existing file, extended in place) —
    `FeatureFlagResponse` (`id`, `key`, `is_enabled`, `description`, `created_at`, `updated_at`);
    `FeatureFlagToggleRequest` (`is_enabled: bool`); `SystemSettingResponse` (`id`, `key`, `value: Any`,
    `description`, `created_at`, `updated_at`); `SystemSettingUpdateRequest` (`value: Any`);
    `DashboardSummaryResponse` (`pending_verification_count: int`, `pending_verification_queue_path: str`,
    `pending_manual_match_count: int`, `pending_manual_match_queue_path: str`,
    `open_unmatched_query_report_count: int`, `open_unmatched_query_report_queue_path: str`).
18. **New file `backend/app/modules/administration/admin_dashboard_api.py`** — `router = APIRouter(tags=["Admin
    Dashboard"])`, every route `Depends(require_role(ROLE_ADMIN))` (AC5):
    - `GET /dashboard/summary` → `DashboardSummaryResponse` via `SuccessResponse`.
    - `GET /feature-flags` → `CollectionResponse[FeatureFlagResponse]`, paginated (`05_API_GUIDELINES.md`'s "all
      collection endpoints must support pagination" rule, default page 20/max 100 — the general default, no new
      per-domain `Settings` constant needed given the genuinely small, code-bounded row count, Decision 3).
    - `PATCH /feature-flags/{key}` → `FeatureFlagToggleRequest` body → `SuccessResponse[FeatureFlagResponse]`;
      404 for an unknown key.
    - `GET /system-settings` → `CollectionResponse[SystemSettingResponse]`, same pagination shape.
    - `PATCH /system-settings/{key}` → `SystemSettingUpdateRequest` body → `SuccessResponse[SystemSettingResponse]`;
      404 for an unknown key.
19. **`backend/app/api/v1/api.py`** — import `administration.admin_dashboard_api.router` and register
    `v1_router.include_router(admin_dashboard_router, prefix="/admin")`, placed directly after the existing
    `admin_unmatched_query_report_router` registration (no path collision — this router's own paths are
    `/dashboard/summary`, `/feature-flags[/{key}]`, `/system-settings[/{key}]`, none of which any existing
    `/admin/...` mount already claims).
20. **`backend/app/core/exceptions/exceptions.py`** (+ `__init__.py` export list) — add `FeatureFlagNotFoundError`
    (404) and `SystemSettingNotFoundError` (404), mirroring `UnmatchedQueryReportNotFoundError`'s exact shape.
21. **Existing test call sites** constructing `ManualMatchAssignmentService`, `UnmatchedQueryReportService`, or
    `SearchRequestService` directly (explicit keyword arguments) must be updated to pass the new constructor
    dependencies (`admin_action_log_service`, `feature_flag_service`) — flagged here so `backend` doesn't
    discover this as a surprise break while running the full suite (mirrors `Plan_S11_ADM-001.md` item 18's
    identical flag).

### Tests

22. `backend/tests/modules/administration/test_feature_flag_service.py` (new) — `is_enabled` returns the seeded
    default (`False`) for `manual_matching_force_all`; returns `False` for a nonexistent key (never raises);
    `toggle` flips `is_enabled`, persists it, and writes exactly one `admin_action_log` row with
    `action_type="feature_flag_toggled"`; `toggle` on an unknown key raises `FeatureFlagNotFoundError` (404).
23. `backend/tests/modules/administration/test_system_setting_service.py` (new) — `update_value` persists the
    new JSONB value and writes exactly one `admin_action_log` row with `action_type="system_setting_updated"`;
    unknown key raises `SystemSettingNotFoundError` (404).
24. `backend/tests/modules/administration/test_dashboard_service.py` (new) — `get_summary` returns correct
    counts for a fixture with a known number of pending-verification/pending-manual-match/open-unmatched-query
    rows (and correctly excludes non-matching statuses from each count); each `*_queue_path` field matches the
    real, registered route path exactly.
25. `backend/tests/modules/administration/test_admin_dashboard_api.py` (new) — full HTTP round trips: 200 `GET
    /admin/dashboard/summary`; 200 `GET`/`PATCH /admin/feature-flags[/{key}]`; 200 `GET`/`PATCH
    /admin/system-settings[/{key}]`; 404 `PATCH` on an unknown key for both; **403 for a non-admin caller on
    every one of these five routes** (AC5).
26. `backend/tests/modules/search/test_search_request_service.py` — extend `handle_session_completed`'s existing
    test coverage: with `manual_matching_force_all` toggled `true`, a session that would otherwise auto-match
    (a customer with a default address and a matching provider nearby) instead creates a
    `manual_match_assignments` row and resolves the `search_requests` row to `pending_manual_match`, never
    calling the automated-match path; with the flag `false` (the default), the existing automated-match
    behavior is unchanged (an explicit regression case, not just "not re-tested") — this is AC4's/AC6's "feature-
    flag toggling takes effect" proof, exercised as a real end-to-end behavioral test, not a unit-level flag read.
27. `backend/tests/modules/administration/test_manual_match_assignment_service.py` — extend `resolve`'s existing
    coverage: a successful resolution writes exactly one `admin_action_log` row with
    `action_type="manual_match_resolved"` and `metadata["provider_ids"]` matching the supplied list.
28. `backend/tests/modules/administration/test_unmatched_query_report_service.py` — extend `mark_reviewed`/
    `mark_actioned`'s existing coverage: each writes exactly one `admin_action_log` row with
    `action_type="unmatched_query_report_reviewed"`/`"...actioned"` respectively.
29. `backend/tests/modules/verification/test_admin_verification_service.py` (or equivalent existing file) — a
    regression re-run confirming `approve`/`reject` still write `admin_action_log` rows unchanged (AC3's
    already-shipped third of the coverage, re-confirmed rather than assumed).
30. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

**None.** Confirmed in Verified Current State/Decision 2: zero admin-facing Flutter code exists anywhere in
`mobile/lib/`, and all 6 ACs are fully satisfiable via backend endpoints alone. No mobile work is in scope for
this story — see Open Question 1 for the flagged, non-silent reasoning behind this call.

---

## Explicitly Out of Scope (do not implement in this story)

- **Any admin-facing UI** (Flutter screens, web dashboard, or a separate internal tool) — Decision 2/Open
  Question 1.
- **An open-ended "create a new feature flag/system setting key" API** — Decision 3; keys are code-defined and
  migration-seeded only.
- **Any additional feature-flag consumer beyond `manual_matching_force_all`** — one real, meaningful,
  well-scoped consumer is sufficient to prove AC4/AC6 honestly; inventing more toggle points not asked for by
  any AC would be scope creep beyond "does not add new admin capabilities beyond ADM-001/VER-002."
- **`claim_review_requests`' admin action log coverage** — not one of AC2's three linked queues; unchanged by
  this story.
- **Any push-notification/alerting mechanism** for configuration changes — no such recipient concept exists
  anywhere in this codebase (`ADR-030`).
- **CSV/data export, bulk edit, or a flag/setting audit-history endpoint** beyond what `admin_action_log` already
  records generically.
- **Real-time/WebSocket dashboard updates** — every existing admin surface is pull-based (`GET`, polled);
  unchanged here.

---

## Open Questions (flagged for CTO awareness — do not block `backend` from starting; per standing instruction,
resolved with this Plan's own stated recommendation if not addressed before implementation)

1. **Backend-only vs. a real admin UI (Decision 2).** The story's own phrasing is more UI-suggestive than
   `ADM-001`'s explicit deferral, but no admin-facing Flutter code or navigation shell exists anywhere to extend,
   and every AC is fully satisfiable via API alone. **Recommended default: ship backend-API-only**, consistent
   with every prior admin capability in this codebase; a future, separate story can build a real admin UI/tool
   once the CTO decides which platform (Flutter admin mode vs. a standalone internal tool) it should be — that
   platform choice was never resolved by `ADM-001` either and remains genuinely open.
2. **`manual_matching_force_all`'s existence operationalizes `13_OPEN_DECISIONS.md` item 10 but does not resolve
   it (Decision 7).** Building this flag gives the business a real, live lever to route more or less traffic
   through manual review without a deploy, but the underlying product question ("how much matching should stay
   manual long-term at launch") remains a business decision, not something this story's code can answer.
   **Recommended default: ship the flag defaulted `false`** (today's existing automated-first behavior is
   unchanged out of the box), and leave the product question open for the CTO to revisit with real usage data
   once this lever exists.
3. **`support_contact_email`'s seed value is illustrative, not a real, CTO-confirmed contact address
   (Decision 1).** Nothing currently reads this value at runtime (no AC requires a `system_settings` consumer,
   unlike feature flags) — it exists solely to make AC1's "editable" claim genuinely testable. **Recommended
   default: ship as a placeholder value**, since no AC or existing code path depends on its real-world accuracy;
   flagged so the CTO isn't surprised by a placeholder-looking value if this table is inspected directly in
   production.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story (fresh start — Sprint 11's second and final story, immediately following
`ADM-001`'s clean close with no open Checkpoint left behind).

1. **backend** — Backend Proposed Changes items 1–21, Tests items 22–30. Suggested build order: (a) migration +
   models (items 1–2) first; (b) `FeatureFlagRepository`/`Service` and `SystemSettingRepository`/`Service`
   (items 3–6) with tests 22–23 written alongside, including the new 404 exceptions (item 20); (c) the three new
   count methods (items 7–9) and `DashboardService` (item 10) with test 24; (d) `AdminActionLogService`'s four
   new methods (item 11) and the two existing services' new `admin_action_log_service` wiring (items 12, 14)
   with tests 27–28, re-confirming test 29's already-shipped verification coverage; (e) the new `admin_dashboard_
   api.py` (items 17–19) with test 25 (including all five 403 checks); (f) the `manual_matching_force_all`
   consumer wiring last (items 13, 16, Decision 7 — the most architecturally sensitive piece, given the new
   `search -> administration.FeatureFlagService` edge and the dispatch-logic change) with test 26; (g) item 21's
   existing-test-call-site sweep and the full regression run (test 30) at the very end. Read Decisions 3, 5, 6,
   and 7 in full before starting — they are this story's real engineering substance.
2. **tester** — verify all 6 verbatim ACs with real evidence (real DB, real HTTP round trips):
   - **AC1**: the migration applies cleanly; both tables' columns/constraints match `04_DATABASE.md`'s spec
     exactly; the seeded rows exist; a non-admin `PATCH` is rejected (folds into AC5); an admin `PATCH`
     genuinely persists.
   - **AC2**: `GET /admin/dashboard/summary`'s three counts are independently verified against real fixture data
     (not just "endpoint returns 200"), and each `*_queue_path` field resolves to a real, working `GET` request
     against that exact path.
   - **AC3**: every one of the five action types this story exercises
     (`feature_flag_toggled`/`system_setting_updated`/`manual_match_resolved`/`unmatched_query_report_reviewed`/
     `unmatched_query_report_actioned`) produces exactly one `admin_action_log` row with correct
     `target_entity_type`/`target_entity_id`/`metadata`; `verification_approved`/`verification_rejected` still
     work unmodified (regression, not assumed).
   - **AC4**: test 26's full behavioral round trip — toggling `manual_matching_force_all` on genuinely changes
     which path a *subsequent* session-completion call takes, with no deploy/restart between the toggle and the
     next request.
   - **AC5**: 403 for a non-admin caller on **every** new route (dashboard summary, both `GET`s, both `PATCH`es)
     — five separate checks, not one representative sample.
   - **AC6**: test 26 (feature-flag-toggling-takes-effect) and tests 27/28 (admin_action_log recording every new
     action type) both exist and pass.
3. **architect** — review: Decision 5's `administration -> verification` raw-Repository edge for a genuine,
   confirmed circular-import avoidance (not just "tests pass") and correct `ADR-047`/`ADR-054`/`ADR-060`
   docstring-naming; Decision 7's `search -> administration.FeatureFlagService` edge and the `handle_session_
   completed` dispatch-logic change against `ADR-042`'s "in-place upgrade, prove the untouched parts really
   didn't change" standard; Decision 6's new `admin_action_log` call sites for correct `target_entity_type`/
   `metadata` shape consistency with the existing `record_verification_review` precedent; Decision 8's plain-
   update-vs-atomic-conditional reasoning for genuine soundness (confirm no real race-condition risk was missed);
   confirm `05_API_GUIDELINES.md`'s pagination rule is honored on both new list endpoints; confirm no new
   circular import anywhere via a full `python -c "import app.main"`-style sanity check if available.
4. Once `tester` and `architect` both report clean, **the orchestrator proceeds straight through closeout
   without an additional sign-off pause**, per the CTO's standing instruction for this story — present the final
   summary to the user after closeout rather than pausing beforehand. A failed or "sent back" verdict from
   either still loops back to `backend` automatically first, as always.
5. At closeout: record Decisions 1, 3, 4, 5, 6, 7, 8 as new ADRs (next available: **ADR-061** onward, per
   contribution — Decision 2 is a scope/platform judgment call, not itself architecture-worthy; Decisions 5 and 7
   are the most likely candidates for their own dedicated ADR given they extend `ADR-060`/introduce this
   codebase's first real feature-flag consumer); update `04_DATABASE.md`'s Administration Domain section to mark
   `feature_flags`/`system_settings` as shipped (removing them from the "remain unbuilt" list); update
   `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 11 section (this closes Sprint 11 and Milestone ML11 in full);
   update `docs/AI/SESSION_HANDOFF.md` with the new state (test counts, ADR numbering, next-sprint framing).

---

## Verification Plan (mapped to the 6 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Migration applies cleanly and matches `04_DATABASE.md`'s spec (columns, unique constraints); seeded rows exist; `test_admin_dashboard_api.py`'s 200/403 `PATCH` cases (test 25). |
| 2 | `test_dashboard_service.py`'s count-correctness assertions against real fixture data (test 24); `test_admin_dashboard_api.py`'s `GET /admin/dashboard/summary` round trip and queue-path verification (test 25). |
| 3 | `test_feature_flag_service.py`/`test_system_setting_service.py`'s admin-action-log assertions (tests 22–23); `test_manual_match_assignment_service.py`/`test_unmatched_query_report_service.py`'s extended coverage (tests 27–28); `test_admin_verification_service.py`'s regression re-confirmation (test 29). |
| 4 | `test_search_request_service.py`'s full behavioral toggle-then-observe round trip (test 26). |
| 5 | `test_admin_dashboard_api.py`'s five separate 403 cases (test 25). |
| 6 | Test 26 (feature-flag toggling takes effect) and tests 27–28 (admin_action_log records every new action type) both exist and pass. |

---

## Related Documents

- `docs/AI/04_DATABASE.md` (Administration Domain — `feature_flags`/`system_settings`' already-specified column
  shape this Plan builds exactly, and the "remain unbuilt" note this story resolves)
- `docs/AI/13_OPEN_DECISIONS.md` (item 10 — the still-open "degree of manual matching" product question
  `manual_matching_force_all` operationalizes without resolving, Decision 7/Open Question 2)
- `docs/AI/09_DECISIONS.md` (`ADR-030` — no push-notification mechanism; `ADR-042` — in-place upgrade of a
  shared write path, the precedent for Decision 7's `handle_session_completed` dispatch change; `ADR-047` —
  Services-only cross-module rule and its raw-Repository exception; `ADR-053` — reuse-for-an-identical-reason,
  underlying Decision 8's plain-update choice; `ADR-056` — dependency-direction-symmetry tiebreaker, considered
  and distinguished in Decision 5; `ADR-058`/`ADR-059`/`ADR-060` — `ADM-001`'s write-time-hook, HTTP-surface-
  placement, and circular-import-avoidance principles, all directly reused or extended here)
- `docs/implementation/plans/Plan_S11_ADM-001.md` (the `unmatched_query_reports`/`administration/api.py`/
  `SearchEventLogService` precedents this Plan directly builds on and mirrors throughout)
- `docs/implementation/plans/Plan_S05_VER-002.md` (`AdminActionLogService`'s original "explicit methods" design
  this Plan extends, Decision 6)
- `docs/implementation/plans/Plan_S07_AI-002.md` (`SearchRequestService.handle_session_completed`'s original
  automated-vs-manual dispatch design, the exact branch point Decision 7 gates)
- `docs/AI/06_SECURITY.md` (Sensitive Data section — reused unchanged from `ADM-001`'s Decision 9 for any
  admin-operational-tool exposure judgment; data-minimization reasoning underlying Decision 4)
- `docs/AI/05_API_GUIDELINES.md` (Pagination section — "all collection endpoints must support pagination,"
  applied to the two new list endpoints per Backend item 18)

---

**End of Document**
