# Walkthrough S11 ADM-002

## Story: Operate the Marketplace From an Admin Dashboard

**Sprint:** 11 | **Story ID:** ADM-002 | **Milestone:** ML11 | **Epic:** ML11-EP01 | **Priority:** Medium |
**Status:** Done

As an administrator, I want a single dashboard summarizing verification queues, manual-match workload, and
platform configuration, so that I can operate the marketplace day-to-day without stitching together separate
tools. This story consolidates `ADM-001` and `VER-002`'s queues alongside feature-flag and system-configuration
management into one operational surface — the capstone of the Marketplace Operations sprint. Scope boundary:
does not add new admin capabilities beyond what `ADM-001`/`VER-002` already implemented.

Full context, the 8 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S11_ADM-002.md`.

All work is committed and pushed as a single commit, `3a025d8`.

**This is Sprint 11 / Milestone ML11's second and final story. With `ADM-002` done, Sprint 11 and Milestone ML11
are now both fully complete — 2 of 2 stories done: `ADM-001`, `ADM-002`.**

---

## What was implemented

### `feature_flags`/`system_settings` — `administration`'s fifth and sixth aggregate roots

Planning confirmed directly against the code (mirroring `ADM-001`'s own planning discipline, not assumed): neither
table existed before this story — `administration/models.py` defined exactly four model classes, no migration
anywhere referenced `feature_flag`/`system_setting`, and `04_DATABASE.md` itself already labeled both "remain
unbuilt" in the same breath as documenting their full column spec. **AC1 is a genuine new migration**, built
exactly to that pre-existing spec:

- **New migration** creates `administration.feature_flags` (`key` VARCHAR(100) unique not null, `is_enabled`
  BOOLEAN not null default `false`, `description` TEXT nullable) and `administration.system_settings` (`key`
  VARCHAR(100) unique not null, `value` JSONB not null, `description` TEXT nullable), both with the full
  `CommonColumnsMixin`, mirroring `unmatched_query_reports`' own migration template. The migration also seeds
  exactly one row per table so AC1's "editable" claim and AC6's "toggling takes effect" tests have something real
  to exercise from day one: `feature_flags.manual_matching_force_all` (`is_enabled=false`) and
  `system_settings.support_contact_email` (a placeholder value — nothing currently reads it at runtime, since no
  AC required a `system_settings` consumer).
- **`FeatureFlagRepository`/`FeatureFlagService`** and **`SystemSettingRepository`/`SystemSettingService`** — each
  exposes `list_all`/`get_by_key` plus one write method (`toggle`/`update_value`). Keys are a known, finite,
  code-defined set: created only by a migration, never by an admin-facing `POST` — mirroring this codebase's
  existing "VARCHAR + application-level constant" convention (`admin_action_log.action_type`,
  `notification.type`). The admin surface is `GET`/`PATCH /admin/feature-flags[/{key}]` and
  `GET`/`PATCH /admin/system-settings[/{key}]`, both `require_role(ROLE_ADMIN)`, raising a new 404
  (`FeatureFlagNotFoundError`/`SystemSettingNotFoundError`) for an unknown key.
- **Writes use a plain `BaseRepository.update`, not the `try_*` atomic-conditional pattern** (Decision 8/ADR-062)
  — toggling a flag or editing a setting is a last-write-wins configuration write, not a workflow-state
  transition with "exactly one caller wins" semantics; if two admins concurrently edit the same row, whichever
  write commits last is the correct, expected outcome, not a 409.

### A real, honest runtime consumer for `manual_matching_force_all` (AC4)

`grep`ing the whole codebase found zero existing feature-flag-gated behavior anywhere — every business-tunable
value before this story was a `Settings`/env-config constant requiring a deploy to change. A flag stored but read
by nothing would make AC4's ("take effect for the next relevant request") and AC6's ("toggling taking effect")
own literal wording false to claim. **Decision 7/ADR-061 rejected a no-op flag outright** and instead wired a
real, meaningful consumer: `SearchRequestService.handle_session_completed` now checks
`feature_flag_service.is_enabled("manual_matching_force_all")` — when `true`, a session that would otherwise
auto-match is instead routed through the manual admin queue (`_handle_routed_to_admin`), exactly as a genuine
low-confidence AI result already is. `FeatureFlagService.is_enabled` returns `False` for an unknown key
(anti-fabrication default — absence is honestly reported as "disabled," never assumed "enabled"). This directly
operationalizes — without resolving — `13_OPEN_DECISIONS.md` item 10's still-open "degree of manual matching"
product question, giving the CTO a real, live, no-deploy lever to act on with real usage data.

### The dashboard-summary aggregation endpoint (AC2)

- **Three new, dedicated count-only repository methods** (`ManualMatchAssignmentRepository.count_pending`,
  `UnmatchedQueryReportRepository.count_by_status`, `VerificationRecordRepository.count_for_review`) — no
  existing repository exposed a standalone count; every `list_*` method only ever returned a full hydrated page
  bundled with `total`. A dedicated `COUNT(*)` avoids fetching PII-bearing rows just to read a headline number.
- **`DashboardService.get_summary()`** — a new `administration` service composing all three counts plus each
  queue's own already-registered path string, exposed at `GET /admin/dashboard/summary`
  (`require_role(ROLE_ADMIN)`).
- **A third application of `ADR-060`'s circular-import-avoidance principle**: the verification count needed a
  new `administration -> verification` edge, but `verification.dependencies` already imports
  `administration.dependencies` at module level (an established `VER-002` edge) — a same-direction import back
  would have been a genuine circular import. `administration/dependencies.py` constructs
  `VerificationRecordRepository(db)` **directly**, importing only the leaf repository module, never
  `verification.dependencies`/`verification.services` — the same fix shape `ADM-001` already applied twice
  (`ADR-060`). This is a raw-`Repository` edge, not a `Service`, since the only thing needed is one
  business-logic-free `COUNT(*)`; introducing a single-method `VerificationCountService` purely to satisfy the
  Services-only default would have been an unnecessary abstraction for one query (`ADR-047`'s exception,
  documented explicitly in `administration/dependencies.py`'s own docstring per `ADR-054`'s naming duty). Unlike
  `ADM-001`'s two applications of this same principle — one of which needed a mid-implementation deviation from
  the Plan's own literal wiring instruction — this third instance was correctly foreseen and planned for in
  advance, and shipped exactly as planned with no deviation.

### The real `admin_action_log` completeness gap — found and closed for two queue actions (AC3)

Direct investigation during planning (reading `ManualMatchAssignmentService.resolve` and
`UnmatchedQueryReportService.mark_reviewed`/`mark_actioned` in full, plus a repo-wide grep) found that **two of
the three dashboard-linked queue actions did not write to `admin_action_log` at all** — despite both being
genuine, already-shipped admin actions (`AI-002`, `ADM-001`). Only the verification queue's `approve`/`reject`
already logged correctly (`VER-002`). This was a real, evidence-based gap AC3's own literal wording
("every... queue action taken from this dashboard") required closing — not new scope, but an audit-logging
completeness fix in already-shipped code:

- **`AdminActionLogService` gains four new explicit methods** (`record_manual_match_resolution`,
  `record_unmatched_query_report_transition`, `record_feature_flag_toggle`, `record_system_setting_update`),
  extending its own existing "explicit named methods, never a generic `record()`" convention (`VER-002`).
- **`ManualMatchAssignmentService`/`UnmatchedQueryReportService` each gain a trivial, intra-module
  `AdminActionLogService` dependency** — both already live inside `administration` alongside
  `AdminActionLogService`, so this is zero new cross-module edges, zero circular-import risk. Each service calls
  its new logging method immediately after a successful transition. `ManualMatchAssignmentService.resolve` gains
  one additive `provider_ids` parameter so the log entry can record which providers were selected.
- `verification`'s existing, already-correct `record_verification_review` call path is left untouched.

### Backend-only scope (Decision 2)

Confirmed directly, not assumed to carry over from `ADM-001`: zero admin-facing Flutter code exists anywhere in
`mobile/lib/` (only incidental substring matches), and every one of the 6 ACs is fully, literally satisfiable by
a backend endpoint alone. No admin authentication/navigation shell exists in the mobile app to host a dashboard
screen even if one were built. Flagged as Open Question 1, not silently resolved — the story's own phrasing
("consolidat[ing]... into one operational surface") is more UI-suggestive than `ADM-001`'s explicit deferral
sentence was, so this genuinely needed investigation rather than a carried-over assumption.

---

## The 8 Architecture Decisions, as actually shipped

All 8 decisions from `Plan_S11_ADM-002.md` shipped exactly as planned, with **zero implementation-time
deviations** — the second story in this project's history (after `MAT-001`) to ship with no Plan deviation at
all.

1. `feature_flags`/`system_settings` did not exist yet; AC1 is a genuine new migration, built exactly to
   `04_DATABASE.md`'s pre-existing spec, with one seeded row per table.
2. Platform scope stays backend-only; flagged as a genuine Open Question, not silently carried over from `ADM-001`.
3. Feature-flag/system-setting keys are a known, finite, code-defined set; no admin-facing "create a new key"
   endpoint.
4. Three new, dedicated count-only repository methods, not a reuse of each `list_*` method's bundled
   `(items, total)`.
5. `administration -> verification` count-only edge, via a raw-`Repository` direct construction — a third,
   correctly-foreseen application of `ADR-060`'s circular-import-avoidance principle.
6. `AdminActionLogService` gains four new explicit methods; `ManualMatchAssignmentService`/
   `UnmatchedQueryReportService` gain a new, intra-module `AdminActionLogService` dependency each — a real
   audit-log completeness fix, not new scope.
7. `manual_matching_force_all`'s real AC4 consumer: gates `SearchRequestService.handle_session_completed`'s
   automated-vs-manual dispatch — a no-op flag was explicitly rejected.
8. Feature-flag/system-setting writes use a plain `update`, not a `try_*`-prefixed atomic conditional `UPDATE` —
   a genuinely different problem (last-write-wins configuration) than the one the `try_*` pattern solves
   (exactly-once workflow-state transitions).

Recorded at this closeout as **3 new ADRs**: **ADR-061** (Decision 7 — the feature-flag honest-runtime-consumer
requirement, a new principle distinct from anti-fabrication), **ADR-062** (Decision 8 — the plain-update-vs-
atomic-conditional distinction, a negative-case precedent for when *not* to use `try_*`), **ADR-063** (Decision
6 — the audit-log completeness-check principle for any story wrapping existing admin actions in a new
capability). **Decision 5 (the third `ADR-060` application) is deliberately *not* given its own ADR entry** —
per `09_DECISIONS.md`'s own append-only rule, an already-recorded ADR's body cannot be edited to add an
addendum, and a third *mechanical* application of the same already-recorded circular-import-avoidance principle
(with no genuinely new nuance — this instance was foreseen and planned for, unlike `ADM-001`'s own
mid-implementation deviation) is recorded here in this Walkthrough instead, mirroring exactly how `ADM-001`'s own
Decision 1 (a documentation correction, not a new architectural shape) was disposed of at that story's own
closeout. Decisions 1–4 are direct, unmodified continuations of already-established precedents (the migration/
seed-row template; the backend-only scope judgment call; the finite-code-defined-key-set convention; the
dedicated-count-method convention) and are recorded in the Plan, not given their own ADR.

---

## Review Process

### `tester` — all 6 verbatim ACs pass, zero gaps, zero regressions

`tester` independently verified every verbatim AC against real infrastructure (real DB, real HTTP round trips):

- **AC1**: the migration applies cleanly (confirmed via a real migration apply, not just a code read); both
  tables' columns/constraints match `04_DATABASE.md`'s spec exactly; the seeded rows exist; a non-admin `PATCH`
  is rejected (folds into AC5); an admin `PATCH` genuinely persists.
- **AC2**: `GET /admin/dashboard/summary`'s three counts independently verified against real fixture data (not
  just "endpoint returns 200"); each `*_queue_path` field resolves to a real, working `GET` request against that
  exact path.
- **AC3**: all five action types this story exercises (`feature_flag_toggled`/`system_setting_updated`/
  `manual_match_resolved`/`unmatched_query_report_reviewed`/`unmatched_query_report_actioned`) each produce
  exactly one `admin_action_log` row with correct `target_entity_type`/`target_entity_id`/`metadata`;
  `verification_approved`/`verification_rejected` re-confirmed still working unmodified (regression, not
  assumed).
- **AC4**: a full behavioral round trip — toggling `manual_matching_force_all` on genuinely changes which path a
  *subsequent* session-completion call takes, with no deploy/restart between the toggle and the next request;
  the `false` default case re-confirmed as an explicit regression check, not just "not re-tested."
- **AC5**: 403 for a non-admin caller on **every** new route — five separate checks (dashboard summary, both
  `GET`s, both `PATCH`es), not one representative sample.
- **AC6**: the feature-flag-toggling-takes-effect test and the `admin_action_log`-records-every-new-action-type
  tests both exist and pass.

**Result: all 6 verbatim ACs pass, zero gaps, zero regressions in the already-shipped `VER-002`/`ADM-001`/
`AI-002` code.**

### `architect` — zero blocking findings, no fix-and-recheck round needed

`architect`'s review covered: Decision 5's `administration -> verification` raw-`Repository` edge for a genuine,
confirmed circular-import avoidance (not just "tests pass") and correct `ADR-047`/`ADR-054`/`ADR-060`
docstring-naming; Decision 7's `search -> administration.FeatureFlagService` edge and the
`handle_session_completed` dispatch-logic change against `ADR-042`'s "in-place upgrade, prove the untouched parts
really didn't change" standard; Decision 6's new `admin_action_log` call sites for correct
`target_entity_type`/`metadata` shape consistency with the existing `record_verification_review` precedent;
Decision 8's plain-update-vs-atomic-conditional reasoning for genuine soundness (no real race-condition risk was
missed); `05_API_GUIDELINES.md`'s pagination rule on both new list endpoints; and a full `import app.main`-style
sanity check confirming no circular import anywhere in the final diff.

**Result: zero blocking findings. No fix-and-recheck round needed.** `architect` noted this is the **third**
application of the circular-import-avoidance principle in this project's history, and — unlike `ADM-001`, which
shipped one `ADR-047` docstring-naming slip on its own new raw-dependency edge — this one was executed correctly
on the first pass, with the required docstring naming present from the start. `architect`'s one non-blocking
housekeeping note (`04_DATABASE.md`/`09_DECISIONS.md` still needing their closeout updates) is exactly this
closeout's own work, addressed below.

### Final verdicts

- **`tester`**: all 6 verbatim ACs pass, zero gaps, zero regressions in the already-shipped `VER-002`/`ADM-001`/
  `AI-002` code.
- **`architect`**: zero blocking findings, no fix-and-recheck round needed.
- **CTO standing instruction**: the CTO gave a standing instruction for this story to proceed straight through
  closeout without an additional sign-off pause once both verdicts were clean — this closeout follows that
  instruction.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `feature_flags`/`system_settings` tables exist via migration and are editable only by admins | Pass — migration applies cleanly, columns/constraints match `04_DATABASE.md`'s spec exactly; seeded rows exist; non-admin `PATCH` rejected, admin `PATCH` genuinely persists |
| 2 | Dashboard summarizes pending verification/manual-match/open-unmatched-query counts, each linking to its queue | Pass — counts independently verified against real fixture data; each queue path resolves to a real, working `GET` |
| 3 | `admin_action_log` records every configuration change, feature-flag toggle, and queue action taken from this dashboard | Pass — all five new action types produce exactly one correctly-shaped row each; verification logging re-confirmed unmodified |
| 4 | Feature flags can be toggled without a deploy and take effect for the next relevant request | Pass — full behavioral toggle-then-observe round trip, both `true` and `false` cases |
| 5 | Non-admin access returns 403 across every dashboard endpoint | Pass — five separate 403 checks across every new route |
| 6 | Automated tests cover feature-flag toggling taking effect and `admin_action_log` recording every action type exercised | Pass — both test categories exist and pass |

**6 of 6 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded three new ADRs:
  - **ADR-061** — the feature-flag honest-runtime-consumer requirement: a flag must have a real, meaningful
    consumer before it can honestly be considered to "take effect," distinct from the anti-fabrication
    principle (about not inventing missing data, not about not inventing the appearance of working behavior).
  - **ADR-062** — the plain-idempotent-overwrite vs. atomic-conditional-transition distinction, a negative-case
    precedent for when *not* to reach for the `try_*` pattern.
  - **ADR-063** — the audit-log completeness-check principle: when a new admin capability wraps around existing
    admin actions, verify each one already logs to `admin_action_log` — never assume it does.
  - Decision 5 (the third `ADR-060` circular-import-avoidance application) was deliberately **not** given its
    own ADR — see the "8 Architecture Decisions" section above for the reasoning.
- **`docs/AI/04_DATABASE.md`** — `feature_flags`/`system_settings` marked shipped (removed from the "remain
  unbuilt" list), each section updated with its shipped shape, seeded row, and (for `feature_flags`) the
  documentation-only fact that `manual_matching_force_all` has a real runtime effect, not a decorative one.
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 10 updated to record that a real, live, no-deploy operational lever
  (`manual_matching_force_all`) now exists — **this operationalizes item 10, it does not resolve it**; the item
  stays `Open`.
- **`docs/AI/SESSION_HANDOFF.md`** — §1 (new `ADM-002` outcome bullet; Sprint 11/Milestone ML11 now fully
  complete), §2 (next sprint/milestone's first story not yet identified — a fresh tracker lookup is needed),
  §4 (new precedent bullets for ADR-061/062/063), §7 (ADR numbering — next new ADR starts at ADR-064), §8 (test
  counts: 898 backend, mobile unchanged at 280).
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — top summary line, Executive Summary, Section 16 (Overall
  Progress), and Section 17 (Next Planned Story) all updated: `ADM-002` marked complete, Sprint 11 and Milestone
  ML11 both marked fully complete (2 of 2 stories), next sprint/milestone's first story noted as not yet
  identified.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `ADM-002`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `ADM-002` row** still needs its Status updated to "Done" and rolled up
  through ML11-EP01/ML11/SP11/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML-safe cell-patching procedure, not performed by this closeout.
- **`system_settings.support_contact_email`'s seed value is a placeholder**, not a real, CTO-confirmed contact
  address — nothing currently reads it at runtime, so this carries no functional risk, but a future reader
  inspecting production data directly should not assume it is a real, live support address.
- **No Checkpoint file existed for this story** (tester/architect both returned clean on the first pass with no
  fix-and-recheck round needed) — none to delete at closeout.

---

## Testing Performed

- `backend` implementation: new `administration` test coverage (`test_feature_flag_service.py`,
  `test_system_setting_service.py`, `test_dashboard_service.py`, `test_admin_dashboard_api.py`), plus extensions
  to `test_search_request_service.py` (feature-flag-toggle-takes-effect), `test_manual_match_assignment_service.py`
  and `test_unmatched_query_report_service.py` (new `admin_action_log` assertions), and a regression re-run of
  `test_admin_verification_service.py`. Full suite green immediately after implementation, `ruff check .` clean.
- `tester` agent: independently verified all 6 verbatim ACs against real infrastructure (real DB, real HTTP round
  trips); zero gaps, zero regressions found in the already-shipped `VER-002`/`ADM-001`/`AI-002` code.
- `architect` agent: zero blocking findings; no fix-and-recheck round needed.
- **Final counts: 898/898 backend tests (864 baseline before this story + 34 new, zero regressions).** No mobile
  work — this story is backend-only, per its own explicit scope boundary; mobile remains unchanged at 280/280.
- CTO gave a standing instruction to proceed straight through closeout once both verdicts were clean, without an
  additional sign-off pause for this story.

---

## Key Files

### Backend
- `backend/alembic/versions/<...>_feature_flags_and_system_settings.py` (new migration)
- `backend/app/modules/administration/models.py` (`FeatureFlag`, `SystemSetting`, new)
- `backend/app/modules/administration/repositories/feature_flag_repository.py` (new)
- `backend/app/modules/administration/repositories/system_setting_repository.py` (new)
- `backend/app/modules/administration/services/feature_flag_service.py` (new — `is_enabled`, `list_all`, `toggle`)
- `backend/app/modules/administration/services/system_setting_service.py` (new — `list_all`, `update_value`)
- `backend/app/modules/administration/repositories/manual_match_assignment_repository.py` (`count_pending`, new)
- `backend/app/modules/administration/repositories/unmatched_query_report_repository.py` (`count_by_status`, new)
- `backend/app/modules/verification/repositories/verification_record_repository.py` (`count_for_review`, new)
- `backend/app/modules/administration/services/dashboard_service.py` (new — `get_summary`)
- `backend/app/modules/administration/services/admin_action_log_service.py` (four new explicit methods)
- `backend/app/modules/administration/services/manual_match_assignment_service.py` (`admin_action_log_service`
  dependency; `resolve` gains `provider_ids`)
- `backend/app/modules/administration/services/unmatched_query_report_service.py` (`admin_action_log_service`
  dependency)
- `backend/app/modules/search/services/search_request_service.py` (`feature_flag_service` dependency;
  `handle_session_completed`'s new flag check)
- `backend/app/modules/administration/dependencies.py` (new providers; `VerificationRecordRepository(db)`
  direct construction — the third `ADR-060` application)
- `backend/app/modules/search/dependencies.py` (`get_feature_flag_service` import; `get_search_request_service`
  extended)
- `backend/app/modules/administration/schemas.py` (`FeatureFlagResponse`/`FeatureFlagToggleRequest`/
  `SystemSettingResponse`/`SystemSettingUpdateRequest`/`DashboardSummaryResponse`, new)
- `backend/app/modules/administration/admin_dashboard_api.py` (new — dashboard summary + feature-flag +
  system-settings routes)
- `backend/app/api/v1/api.py` (`admin_dashboard_router` registered at `/admin`)
- `backend/app/core/exceptions/exceptions.py` (`FeatureFlagNotFoundError`, `SystemSettingNotFoundError`, new)
- `backend/tests/modules/administration/test_feature_flag_service.py`, `test_system_setting_service.py`,
  `test_dashboard_service.py`, `test_admin_dashboard_api.py` (new)
- `backend/tests/modules/search/test_search_request_service.py`,
  `backend/tests/modules/administration/test_manual_match_assignment_service.py`,
  `test_unmatched_query_report_service.py`, `test_admin_verification_service.py` (extended/re-confirmed)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-061, ADR-062, ADR-063
- `docs/AI/04_DATABASE.md` — Administration Domain, `feature_flags`/`system_settings` marked shipped
- `docs/AI/13_OPEN_DECISIONS.md` — item 10 updated (operationalized, not resolved)
- `docs/AI/SESSION_HANDOFF.md` — §1/§2/§4/§7/§8 refreshed
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 11/Milestone ML11 marked fully complete
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 11 and Milestone ML11 are now fully complete — 2 of 2 stories done: `ADM-001`, `ADM-002`.**
- The next sprint/milestone's first story has **not yet been identified** — a fresh lookup against
  `docs/AI/Project_Tracker.xlsx` is needed before any planning begins, mirroring how every previous milestone
  transition in this project has been handled.
- **`ADR-061`'s feature-flag honest-consumer requirement is now a documented precedent**: any future feature flag
  must have a real, meaningful runtime consumer wired in the same story that ships it — never satisfy a
  table-existence AC with a flag nothing reads.
- **`ADR-062`'s plain-update-vs-`try_*` distinction is now a documented precedent**: a plain, last-write-wins
  configuration value write should default to `BaseRepository.update`, reserving the `try_*` atomic-conditional
  pattern for genuine "exactly one caller wins" workflow-state transitions.
- **`ADR-063`'s audit-log completeness-check principle is now a documented precedent**: any future story
  consolidating or dashboarding existing admin workflows should explicitly verify — not assume — that each
  wrapped action already logs to `admin_action_log`.
- **`docs/AI/Project_Tracker.xlsx`'s `ADM-002` row** still needs its Status flipped to "Done" and rolled up
  through ML11-EP01/ML11/SP11/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.

---

**End of Document**
