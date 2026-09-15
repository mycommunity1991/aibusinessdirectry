# Walkthrough S12 ENG-001

## Story: Receive Marketplace Notifications in My Preferred Channel

**Sprint:** 12 ("Engagement & Trust") | **Story ID:** ENG-001 | **Milestone:** ML12 | **Epic:** ML12-EP01 |
**Priority:** High | **Status:** Done

As a user, I want to be notified about new leads, verification status changes, and outcome-tag prompts through my
preferred channel, so that I don't have to keep checking the app manually. Scope boundary: does not include the
deep-link/Verified-Visit features (`ENG-002`) — this story is notification delivery only.

Full context, the 10 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S12_ENG-001.md`.

Backend implemented and committed at `2442b9f`. Mobile implemented and committed at `6f4e229`. `architect`'s
review fix committed at `8737874`.

**This is Sprint 12 / Milestone ML12's first story. `ENG-002` ("share a provider profile and verify an arrival")
has not yet started — Sprint 12 and Milestone ML12/Epic ML12-EP01 are not yet complete.**

---

## The discrepancy this story resolved

`ENG-001`'s own tracker description framed this story as building the Notification domain "end to end... for the
first time." Planning read `backend/app/modules/notification/` in full before writing the Plan and found this was
not literally accurate: `NotificationService` already existed, with three working methods
(`notify_verification_status_change`, `notify_new_contact_view`, `notify_outcome_tag_prompt`), each already
called synchronously, in production, from a different module entirely — `AdminVerificationService` (`VER-002`),
`ContactService` (`CON-001`/`REV-001`). Each already wrote a real, honest `notification.notifications` row with
hardcoded, plain-language copy. What genuinely did not exist: the `notification_preferences`/`notification_
delivery` tables, any real multi-channel delivery adapter, any preference enforcement, any idempotency mechanism,
and the fourth trigger (manual-match-assignment → Admin). This is the same class of tracker-text-vs-reality gap
this project has now found and corrected three times (`unmatched_query_reports` before `ADM-001`; `feature_flags`/
`system_settings` before `ADM-002`; `NotificationService`'s real state before `ENG-001`) — the Plan's own
Investigation 1 records the full evidence trail.

The story's real, net-new scope was therefore: the two missing tables plus two spec additions their own literal
ACs required; real delivery/preference/idempotency layered **onto** the three already-existing call sites via an
in-place extension of `NotificationService`'s existing methods, never a second, parallel mechanism; the one
genuinely new fourth trigger; and the Notifications Inbox screen, which had zero precedent anywhere in this
codebase.

---

## What was implemented

### `notification_preferences`/`notification_delivery` — the two genuinely missing tables, plus two literal-AC-driven additions

A new migration creates both tables exactly to `04_DATABASE.md`'s pre-existing spec, plus two genuine additions
neither the Plan nor `04_DATABASE.md` originally specified, each required to honestly satisfy a literal AC:

- **`notification_preferences.channel_enabled BOOLEAN NOT NULL DEFAULT true`** — the pre-existing spec's
  `channel` column (the already-shipped, 3-value `customer.notification_channel` enum) has no "off" value, so
  there was no way to express AC4's literal "a disabled channel... is checked before every send" using `channel`
  alone. A separate boolean cleanly represents "is any external channel enabled at all," independent of *which*
  channel is the standing preference (re-enabling remembers the prior choice).
- **`notification_delivery.idempotency_key VARCHAR(255) NOT NULL UNIQUE`** — AC7 is not satisfiable at all
  without a persisted key to conflict on.
- **`notifications.read_at TIMESTAMPTZ NULL`** (an `ALTER TABLE` on the already-shipped table — this codebase's
  first column-addition-to-an-existing-table migration) — required to honestly satisfy AC5's "badge" (an unread
  count needs a read/unread boundary) and AC6's "New/Earlier grouping" (the same boundary).

`notification_preferences.channel`/`notification_delivery.channel` both reuse the already-existing
`customer.notification_channel` Postgres enum type (`create_type=False`) rather than duplicating it — see
Decisions below.

### `NotificationService`'s three existing methods, extended in place — never a second, parallel mechanism

`notify_verification_status_change`, `notify_new_contact_view`, and `notify_outcome_tag_prompt` were extended in
place: each now first checks `NotificationPreferenceService.is_category_allowed`; if the category is muted, the
entire call becomes a no-op — no `notifications` row, no `notification_delivery` row, nothing recorded at all
(a full hard stop, per AC4's literal wording). If allowed, the existing `notifications` row is created exactly as
before (unchanged copy, unchanged shape); only then, for the two urgent trigger types (new Contact View,
verification status change), does it check `is_channel_enabled` and, if true, dispatch external delivery via
`NotificationDeliveryService`. Existing signatures, existing copy templates, and existing callers
(`AdminVerificationService`, `ContactService`) are unchanged — no `_v2` method, no duplicated row-creation logic.
The existing 12-test `test_notification_service.py` suite's assertions for these three methods were re-run
unchanged and re-confirmed passing byte-for-byte, the concrete proof this in-place extension broke nothing
already relied upon by `verification`/`contact`.

A genuinely new fourth method, `notify_manual_match_assignment_created`, was added for AC3's one genuinely new
trigger (see below).

### `NotificationSender` Protocol — the fifth application of the swappable-Protocol pattern

`NotificationSender` (an `abc.ABC` with one abstract `send` method) has three stub implementations
(`StubWhatsAppSender`/`StubSmsSender`/`StubEmailSender`, all always succeeding, log-only, mirroring
`ConsoleSmsSender`'s convention) and three typed exceptions inheriting a common `NotificationDeliveryError` base
— a plain Python exception hierarchy, never HTTP-mapped, since a delivery failure must never fail the triggering
request. `NotificationDeliveryService.send` computes a deterministic idempotency key
(`f"{notification_id}:{channel}"`) itself, `try_create`s the delivery row via an atomic
`ON CONFLICT DO NOTHING ... RETURNING` (the fourth application of `ADR-049`'s INSERT-shaped atomic-conflict
family), short-circuits on conflict without calling the sender a second time, and catches
`NotificationDeliveryError` to record `status="failed"` with a non-null `failure_reason` — never re-raised.

### The fourth trigger — manual-match-assignment → Admin, via a new RBAC reverse lookup

AC3 literally requires a trigger with no admin identity attached at creation time
(`ManualMatchAssignmentService.create` is pull-based; `assigned_admin_id` is `NULL` until `resolve`), creating a
real tension with `SESSION_HANDOFF.md`'s standing "never invent a push-to-admin mechanism" rule. Resolved via a
new `RoleRepository.get_user_ids_for_role(role_name)` — the reverse of the existing `get_role_names_for_user` —
backing `notify_manual_match_assignment_created`, which broadcasts one in-app-only `notifications` row per
current `ROLE_ADMIN` account: no preference check, no `NotificationDeliveryService` call, no external channel
dispatch, ever. This satisfies AC3's literal wording using an already-real RBAC primitive, without ever
attempting the push the standing rule actually prohibits.

### Preference reuse and seeding: `customer.notification_channel` is not duplicated

`notification_preferences.channel` reuses `customer.notification_channel` — an enum type that had existed,
stored-but-read-by-zero-delivery-code, since `CUS-001` (Sprint 3). `NotificationPreferenceService.
get_or_create_for_user` seeds a customer's first-touch row from their existing `customer_preferences.
notification_channel` value (a raw, read-only lookup, never provisioning a new customer profile as a side
effect); a provider/admin account, or any account with no customer profile, defaults to `whatsapp`. This is a
**one-time seed only** — the two columns are not kept in sync afterward, a deliberate divergence flagged as a new
`13_OPEN_DECISIONS.md` item, not silently assumed to stay aligned.

### Urgency: fixed by trigger type, not a further user-configurable dimension

AC5's "unless the user has opted in" clause implies a fourth preference dimension no AC actually names and no
schema field backs anywhere in this story's own spec. Rather than inventing an unrequested field to satisfy the
clause literally, or silently dropping it, urgency (push-immediately vs. inbox-only) is classified as a fixed,
code-level constant per trigger type — new Contact View and verification status change are urgent; outcome-tag
prompt and manual-match-assignment are not, and never reach `NotificationDeliveryService` regardless of
preference state. The gap is recorded explicitly, not silently.

### Notifications Inbox — backend and mobile, both with zero prior precedent

Three new endpoints (`GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`),
gated only by `get_current_user` (every account of any role may have notifications). On mobile, a new
`features/notifications/` module delivers the Inbox screen (New/Earlier sectioned list, per-`relatedEntityType`
deep-links, reusing the existing `OutcomeTagPromptSheet` widget rather than building a new screen for that case)
and a shared unread-count badge tile on the Home placeholder screen — implemented as a `shared/`-owned provider,
not a `features/notifications/`-owned one, to respect `02_ARCHITECTURE.md`'s "features must not depend on each
other" rule (a deliberate, flagged deviation from the Plan's literal wording, mirroring the
`_VerificationStatusChip` precedent already established for this exact rule).

---

## The 10 Architecture Decisions, as actually shipped

All 10 decisions from `Plan_S12_ENG-001.md` shipped as planned. Recorded at this closeout as **5 new ADRs**:

1. **Decision 1 — `ADR-064`**: in-place extension of `NotificationService`'s three pre-existing methods, each with
   live cross-module callers — a new, distinct nuance beyond `ADR-042` (which was a Repository query, not Service
   methods with external callers in other modules).
2. **Decision 2** (module placement — both new tables fold into the existing `notification` module) — a direct,
   unmodified application of `ADR-051`'s already-recorded module/schema placement rule; recorded here, not given
   its own ADR.
3. **Decision 3** (the two schema additions, `channel_enabled`/`idempotency_key`, plus `notifications.read_at`) —
   recorded in `04_DATABASE.md`'s own updated Notification Domain section, not given a standalone ADR (the
   additions are direct, literal-AC-driven consequences of Decisions 5/8, which are separately recorded).
4. **Decision 4 — `ADR-065`**: cross-schema enum-type reuse plus a one-time, divergence-tolerant seed from an
   independent, still-live preference column — a genuinely new nuance beyond `CUS-001`'s original `language_code`
   reuse (which had no seeding dimension at all), and the first ADR to record the enum-reuse convention itself
   (never previously given its own ADR).
5. **Decision 5** (preference enforcement as a full hard stop per category) — a direct, mechanical application of
   AC4's own literal wording; recorded in the Plan, not given its own ADR.
6. **Decision 6 — `ADR-066`**: fixed, code-level urgency classification over an AC-implied but schema-unsupported
   user-configurable dimension — distinct from the anti-fabrication family (which governs never inventing a
   *data value*) and from `ADR-050`/`ADR-061`'s "don't invent unrequested capability" family (which addresses a
   team choosing not to build something a broader narrative gestured at, not an individual AC's own prose
   implying a dimension with zero schema backing anywhere in the story).
7. **Decision 7** (`NotificationSender` Protocol, three stub adapters) — the fifth, direct, mechanical application
   of the already-established swappable-Protocol pattern; recorded in the Plan, not given its own ADR.
8. **Decision 8 — `ADR-067`**: a deterministic, server-computed idempotency key for an internal, non-client-facing
   retry, never a caller-supplied header — the *mechanism* (`ON CONFLICT DO NOTHING ... RETURNING`) is a
   mechanical fourth application of `ADR-049`, but the *key-sourcing* decision (server-computed natural key vs.
   the general REST header convention, specifically for an internal retry) is new and citable on its own.
9. **Decision 9 — `ADR-068`**: reconciling AC3's literal requirement against the standing "never invent a
   push-to-admin mechanism" rule by finding the narrower, already-real RBAC reverse-lookup mechanism that
   satisfies both — a genuinely novel resolution pattern for the recurring "an AC's literal wording appears to
   conflict with a standing, named prohibition" shape.
10. **Decision 10** (Notifications Inbox backend/mobile shape) — direct application of already-established
    patterns (`ADR-046`'s raw-fields/client-computed convention, `ADR-015`'s 404-not-403 ownership shape); recorded
    in the Plan, not given its own ADR.

**The `mark_read` repository-vs-service ownership-check fix (below) is also not given its own ADR** —
`08_CODING_STANDARDS.md` already states, verbatim, "Repositories never contain business rules." This is a
straightforward enforcement of an already-explicit standing rule, not a new principle, so it is recorded here in
this Walkthrough only.

---

## Review Process

### `tester` — all 8 verbatim ACs pass, zero real bugs

`tester` independently verified every verbatim AC against real infrastructure (real DB, real HTTP round trips):
migration applies cleanly with all three tables' columns/constraints confirmed exactly (AC1); a fake, deliberately
failing `NotificationSender` produces a caught, recorded, non-propagated typed error (AC2); all four triggers
fire correctly end-to-end, including a regression-check that `REV-001`'s outcome-tag-prompt behavior still works
after the in-place extension (AC3); a muted category blocks the entire send while a disabled channel blocks only
external delivery, verified as two independently-checked hard stops (AC4); the two urgent triggers dispatch
delivery while the two non-urgent triggers never do, regardless of preference state (AC5); `GET`/`PATCH
/notifications` round trips correctly distinguish New/Earlier and the mobile Inbox groups/deep-links correctly
(AC6); calling the same trigger twice never creates a second delivery row or calls the sender twice (AC7); both
dedicated tests (preference-disabled blocking, idempotent retry) exist and genuinely exercise their named
scenarios (AC8). **Result: all 8 verbatim ACs pass, zero gaps, zero real bugs found.**

### `architect` — one real, blocking finding on the first pass; fixed and re-confirmed clean

`architect`'s first review found `NotificationRepository.mark_read` did the ownership comparison **inline inside
the repository** — building the `WHERE id = :id AND user_id = :user_id` clause itself, rather than the plain,
ownership-scoped-only-at-the-SQL-level shape this codebase's own repositories use elsewhere, with the actual
"does this row belong to this caller, and if not, is that a 404" business decision left to be inferred from the
query's own shape rather than made explicitly in the service layer. This is a direct violation of
`08_CODING_STANDARDS.md`'s explicit "Repositories never contain business rules" rule, mirroring `06_SECURITY.md`'s
equivalent principle. Compounding it, `NotificationNotFoundError`'s own docstring falsely claimed
`ensure_owner_or_not_found` was already in use for this check, when it wasn't.

**Fixed at commit `8737874`:** `NotificationRepository.mark_read` now issues a plain, ownership-scoped
`UPDATE ... WHERE id = :id AND user_id = :user_id AND read_at IS NULL RETURNING`, and
`NotificationService.mark_read` calls `ensure_owner_or_not_found` explicitly on the `None` case — mirroring
`SavedAddressService`'s already-established shape exactly, the same pattern this codebase has used correctly
since `AUTH-004`. The docstring was corrected. External behavior was proven unchanged, not merely asserted: 404
is still returned for another user's notification id (never 403), the endpoint is still idempotent on a repeat
call, `read_at` still persists correctly — and the existing test file for this endpoint was byte-identical
before and after the fix, with every test still passing. `architect`'s re-check returned **APPROVED**.

This is the same general shape of finding this project has seen before (`LEAD-001`'s `ADR-047` docstring-naming
gap) — the wiring was functionally correct, but a specific, already-documented discipline (there: naming a raw
cross-module dependency; here: keeping business rules out of the repository layer) was not followed on the first
pass. Both are examples of the same broader lesson: a green test suite does not, by itself, prove a standing
architectural rule was actually followed.

### Final verdicts

- **`tester`**: all 8 verbatim ACs pass, zero gaps, zero real bugs.
- **`architect`**: one real, blocking finding on the first pass (`mark_read`'s business-rule-in-repository
  violation), fixed at commit `8737874` and independently re-confirmed — **APPROVED**.
- **CTO standing instruction**: proceed straight through closeout without an additional sign-off pause once both
  verdicts were clean, the same standing instruction already applied to every Sprint 11 story.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `notifications`/`notification_preferences`/`notification_delivery` tables exist via migration | Pass — migration applies cleanly; all columns/constraints (including the two genuine spec additions) confirmed directly |
| 2 | `NotificationSender` interface with WhatsApp/SMS/Email adapters; delivery failures surface as typed errors, never a silent no-op | Pass — a fake, deliberately-failing sender produces a caught, recorded, non-propagated typed error |
| 3 | Triggers wired for new Contact View → Provider, verification status change → Provider, manual match assignment → Admin, outcome-tag prompt → Customer | Pass — all four fire correctly end-to-end, including a `REV-001` regression re-confirmation |
| 4 | A disabled channel or muted category is a hard stop, not a soft suggestion | Pass — two independently-verified hard stops (category mutes the entire send; channel disables only external delivery) |
| 5 | Non-urgent events update a badge/inbox entry without forcing a push unless opted in; time-sensitive events may push immediately | Pass — urgent-vs-non-urgent dispatch behavior verified as a genuine behavioral assertion |
| 6 | Notifications Inbox groups New/Earlier and deep-links each entry | Pass — backend round trips plus mobile widget tests for every `relatedEntityType` case |
| 7 | Duplicate sends prevented via an idempotency key on retry | Pass — calling the same trigger twice never creates a second delivery row or calls the sender twice |
| 8 | Automated tests cover preference-disabled blocking and idempotent retry | Pass — both dedicated tests exist and genuinely exercise their named scenarios |

**8 of 8 Pass.**

---

## Documentation updated at this closeout

- **`docs/AI/09_DECISIONS.md`** — recorded five new ADRs: **ADR-064** (in-place extension of Service methods with
  live cross-module callers), **ADR-065** (cross-schema enum reuse plus one-time divergence-tolerant seeding),
  **ADR-066** (fixed classification over an AC-implied, schema-unsupported dimension), **ADR-067** (deterministic
  server-computed idempotency key for an internal retry), **ADR-068** (reconciling a literal AC against a
  standing prohibition via a narrower, already-real mechanism). Decisions 2, 3, 5, 7, 10, and the `mark_read` fix
  are recorded in this Walkthrough/the Plan only — mechanical reapplications of already-recorded principles, per
  `09_DECISIONS.md`'s own append-only discipline.
- **`docs/AI/04_DATABASE.md`** — `notification_preferences`/`notification_delivery` marked shipped, including the
  two genuine spec additions (`channel_enabled`, `idempotency_key`); the new `notifications.read_at` column
  documented.
- **`docs/AI/13_OPEN_DECISIONS.md`** — three new items added: item 15 (whether to deprecate
  `customer_preferences.notification_channel` now that a broader, seeded-but-divergent `notification_preferences.
  channel` exists), item 16 (real notification-vendor selection — distinct from items 11/13), item 17 (a future
  customer-facing notification-preferences settings screen).
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — top summary line, Section 16 (Overall Progress), and Section 17
  (Next Planned Story) all updated: `ENG-001` marked complete, Sprint 12/Milestone ML12 explicitly marked **not**
  complete (`ENG-002` not yet started).
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `ENG-001`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `ENG-001` row** still needs its Status updated to "Done" and rolled up
  through ML12-EP01/ML12/SP12/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML cell-patching procedure, not performed by this closeout.
- **`docs/AI/SESSION_HANDOFF.md`** is refreshed separately by the orchestrator, not by this closeout.
- **The `Checkpoint_S12_ENG-001.md` continuity file** — deleted as part of this closeout, its purpose served
  (both `tester` and `architect` have reported, the fix-and-recheck round is complete, and this Walkthrough now
  records the full account).

---

## Testing Performed

- `backend` implementation (commit `2442b9f`): new `notification` module coverage across
  `test_notification_preference_service.py`, `test_notification_delivery_service.py`, an extended
  `test_notification_service.py` (12 pre-existing tests re-confirmed unchanged plus new preference/urgency/
  fourth-trigger coverage), a new `test_role_repository.py` addition, an extended
  `test_manual_match_assignment_service.py`, and a new `test_notification_api.py`. Full suite green, `ruff check
  .` clean, a real `python -c "import app.main"` sanity check confirming no circular import.
- `architect`'s fix (commit `8737874`): `NotificationRepository.mark_read`/`NotificationService.mark_read`
  corrected; the existing test file for this endpoint was byte-identical before and after, all tests still
  passing.
- `mobile` implementation (commit `6f4e229`): new `features/notifications/` test coverage (controller,
  screen, fakes) plus extended `home_placeholder_screen_test.dart` coverage for the new entry tile/badge.
- `tester` agent: independently verified all 8 verbatim ACs against real infrastructure; zero real bugs found.
- `architect` agent: one real, blocking finding on the first pass (documented above), fixed and independently
  re-confirmed — **APPROVED**.
- **Final counts: 929/929 backend tests (898 baseline + 31 new, zero regressions); 303/303 mobile tests (280
  baseline + 23 new, zero regressions).**
- CTO gave a standing instruction to proceed straight through closeout once both verdicts were clean, without an
  additional sign-off pause for this story.

---

## Key Files

### Backend
- `backend/alembic/versions/<...>_notification_preferences_and_delivery.py` (new migration)
- `backend/app/modules/notification/models.py` (`Notification.read_at`; `NotificationPreference`,
  `NotificationDelivery`, new)
- `backend/app/modules/notification/repositories/notification_preference_repository.py` (new)
- `backend/app/modules/notification/repositories/notification_delivery_repository.py` (new)
- `backend/app/modules/notification/repositories/notification_repository.py` (`list_for_user`, `count_unread`,
  `mark_read` — the last corrected at commit `8737874`)
- `backend/app/modules/notification/services/notification_sender.py` (new — `NotificationSender`,
  `NotificationDeliveryError` family, three stub adapters)
- `backend/app/modules/notification/services/notification_preference_service.py` (new)
- `backend/app/modules/notification/services/notification_delivery_service.py` (new)
- `backend/app/modules/notification/services/notification_service.py` (three existing methods extended in place;
  `notify_manual_match_assignment_created`, new; `mark_read` corrected at commit `8737874`)
- `backend/app/modules/identity/repositories/role_repository.py` (`get_user_ids_for_role`, new)
- `backend/app/modules/administration/services/manual_match_assignment_service.py` (`notification_service`
  dependency; new call in `create`)
- `backend/app/modules/notification/dependencies.py`, `backend/app/modules/administration/dependencies.py`
  (extended)
- `backend/app/modules/notification/schemas.py`, `backend/app/modules/notification/api.py` (new)
- `backend/app/api/v1/api.py` (`notification_router` registered)
- `backend/app/core/exceptions/exceptions.py` (`NotificationNotFoundError`, new; docstring corrected at commit
  `8737874`)
- `backend/tests/modules/notification/` (new/extended coverage — see Testing Performed)
- `backend/tests/modules/identity/test_role_repository.py`,
  `backend/tests/modules/administration/test_manual_match_assignment_service.py` (extended)

### Mobile
- `mobile/lib/features/notifications/` (new — domain models, repository, controller, Inbox screen)
- `mobile/lib/shared/data/unread_notification_count_repository.dart` (new — shared unread-count provider)
- `mobile/lib/features/customer/presentation/screens/home_placeholder_screen.dart` (new entry-point tile/badge)
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (new route)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys)
- `mobile/test/features/notifications/`, `mobile/test/shared/fakes/`,
  `mobile/test/features/home/home_placeholder_screen_test.dart` (new/extended)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-064, ADR-065, ADR-066, ADR-067, ADR-068
- `docs/AI/04_DATABASE.md` — Notification Domain, `notification_preferences`/`notification_delivery` marked
  shipped, `notifications.read_at` documented
- `docs/AI/13_OPEN_DECISIONS.md` — items 15, 16, 17 added
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — top summary, Section 16, Section 17 updated (Sprint 12/ML12 marked
  not yet complete)
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 12 and Milestone ML12/Epic ML12-EP01 are not yet complete — 1 of 2 stories done: `ENG-001` shipped;
  `ENG-002` ("share a provider profile and verify an arrival") has not yet started.** No engineering agent should
  begin planning or implementing `ENG-002` without an explicit CTO "Start ENG-002" instruction.
- **`ADR-064`'s in-place-Service-extension principle is now a documented precedent**: a future story extending a
  shared Service method that already has live callers in other modules should cite both this ADR and `ADR-042`,
  and must re-run the pre-existing tests for the untouched behavior unchanged as concrete proof, not merely
  assert nothing broke.
- **`ADR-065`'s cross-schema-enum-reuse-plus-seed pattern is now a documented precedent**: reuse the existing
  type, seed once at row-creation time, and explicitly document — never silently assume — that the two fields
  are now allowed to diverge.
- **`ADR-066`'s principle is now documented**: when an AC's own literal prose implies a capability with no schema
  backing anywhere in the story's own spec, ship the fixed, schema-backed interpretation and name the gap
  explicitly — never invent unrequested schema, and never silently drop the clause.
- **`ADR-068`'s reconciliation pattern is now documented**: when a literal AC requirement appears to conflict with
  a standing, named prohibition, look for a narrower, already-real primitive that satisfies the AC without doing
  the specific thing the prohibition targets, rather than treating the AC as unsatisfiable or violating the rule.
- **Three new, genuinely open follow-ups are now tracked** (`13_OPEN_DECISIONS.md` items 15–17): reconciling the
  two now-independent notification-channel preference fields; real WhatsApp/SMS/Email vendor selection; a future
  customer-facing notification-preferences settings screen.
- **`docs/AI/Project_Tracker.xlsx`'s `ENG-001` row** still needs its Status flipped to "Done" and rolled up
  through ML12-EP01/ML12/SP12/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.

---

**End of Document**
