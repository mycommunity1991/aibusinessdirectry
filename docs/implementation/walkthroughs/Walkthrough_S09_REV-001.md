# Walkthrough S09 REV-001

## Story: Tell the Platform Whether I Hired a Provider

**Sprint:** 09 | **Story ID:** REV-001 | **Priority:** High | **Status:** Done

As a customer who contacted a provider, I want to quickly confirm whether I hired them, so that the platform has
a real signal of what actually happened without tracking payment details it has no visibility into. The Outcome
Tag is the platform's only conversion signal given the offline-payment reality of the direct-contact model. It is
deliberately minimal — a yes/no tied to a specific Contact View — and only the Customer who generated that
Contact View may submit it. **Scope boundary:** does not include the review itself (`REV-002`), which requires a
"Yes" outcome tag as its anchor.

Full context, the 7 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S09_REV-001.md`.

All work is committed to branch `claude/provider-storefront-pro-001-qnicuj` (head `d33e8c2` at this closeout).

**This is Sprint 9 / Milestone ML9's first story** — Milestone ML9 ("Outcome & Reviews") is now 1 of 2 stories
done. `REV-002` ("leave a verified review after a successful hire") is the next story in this epic (ML9-EP01),
depends on `REV-001`, and will finally build `reviews`/`provider_rating_summaries`, resolving
`13_OPEN_DECISIONS.md` item 14.

---

## What was implemented

No new module was created — every table this story needed extends the already-shipped `contact` domain.

### Backend (`backend/app/modules/contact/` — extended, not a new module)

- **New migration** (`outcome_tags_domain`, on top of `024bcc0fbaf8`) — creates `contact.outcome_tags` exactly per
  `04_DATABASE.md`'s pre-existing spec: `contact_view_id` (FK → `contact.contact_views.id`, not null, unique),
  `hired` (boolean, not null), `submitted_at` (timestamptz, not null, default `now()`), plus the full
  `CommonColumnsMixin` (soft-delete by default), and `uq_outcome_tags_contact_view_id`. No deviation from the
  spec occurred.
- **`OutcomeTag`** added to the existing `contact/models.py` alongside `ContactView` — the `administration`
  module's own multi-aggregate-root precedent (`AdminActionLog`/`ClaimReviewRequest`/`ManualMatchAssignment`, all
  one Python module, one Postgres schema) applied to `contact` for the first time.
- **`OutcomeTagRepository.try_create`** — a single atomic statement,
  `postgresql.insert(OutcomeTag).values(**values).on_conflict_do_nothing(index_elements=["contact_view_id"])
  .returning(OutcomeTag.id)`. Returns `None` on the conflict path (no read-then-write gap anywhere).
- **`OutcomeTagService.submit_outcome_tag`** — resolves the caller's `customer_profiles` row, resolves the target
  `ContactView`, runs `ensure_owner_or_not_found(...)` (AC2), calls `try_create` (AC1/AC6) — raising
  `OutcomeTagAlreadyExistsError` (409) on conflict, `ContactViewNotFoundError` (404) on ownership failure or a
  nonexistent Contact View.
- **`POST /contact-views/{contact_view_id}/outcome-tag`** added to the existing `contact/api.py` router (same
  prefix, same `["Contact"]` tag, `require_role(ROLE_CUSTOMER)`) — 201 on success, documented 404/409 responses.
- **`NotificationService.notify_outcome_tag_prompt`** — a new method mirroring `notify_new_contact_view`'s
  existing shape (`type="outcome_tag_prompt"`, already the exact value `04_DATABASE.md`'s own column
  documentation named).
- **Flagged touch-point on `CON-001`'s already-shipped `ContactService.create_contact_view`** — one new,
  unconditional call to `notify_outcome_tag_prompt` after the `contact_views` row is created, alongside (not
  replacing) the existing conditional provider-lead notification. No other line of the method changed.
- New exceptions: `ContactViewNotFoundError` (404), `OutcomeTagAlreadyExistsError` (409).

### Mobile (`mobile/lib/features/provider_profile/` — the same feature `CON-001` built, extended)

- **`OutcomeTagPromptSheet`** — a new bottom sheet: provider name/photo, "Did you hire them?" title, Yes/No
  buttons (each submits and closes), and a "Maybe later" text button that closes with **zero** network calls.
  Loading state while a submission is in flight; a 404/409 (effectively unreachable in the normal flow) simply
  closes the sheet rather than surfacing a scary error.
- **`ProviderProfileScreen._onContactTap`** — now `async`, `await`s `ContactRevealSheet.show(...)` (previously
  fire-and-forget), then — guarded by `context.mounted`, only if the reveal genuinely reached `loaded` state —
  opens `OutcomeTagPromptSheet` with the just-created `contact_view_id`, provider display name, and photo.
- New domain model/exception/repository-method/controller for the outcome-tag submission, added to the existing
  `provider_profile` feature (not a new feature) — mirrors `contact_exception.dart`'s existing error-mapping
  convention.
- New localization keys (`app_en.arb`/`app_ar.arb`) for the sheet's copy.

---

## The 7 Architecture Decisions, as actually shipped

All 7 decisions from `Plan_S09_REV-001.md` shipped exactly as planned, with no implementation-time deviations:

1. **`outcome_tags` extends the existing `contact` module, not a new standalone module** — shipped as planned.
2. **AC2's ownership rejection is a 404 (`ContactViewNotFoundError`), via `ensure_owner_or_not_found`, never a
   403** — shipped as planned; deliberately distinct from `CON-001`'s self-dealing 403.
3. **Uniqueness enforced via atomic `INSERT ... ON CONFLICT DO NOTHING ... RETURNING`** — shipped as planned; the
   first INSERT-shaped member of the atomic-conditional-write family.
4. **An outcome tag is immutable once submitted; no update/resubmission path** — shipped as planned.
5. **`NotificationService.notify_outcome_tag_prompt`, fired synchronously and unconditionally from
   `ContactService.create_contact_view`** — shipped as planned, flagged explicitly as an additive touch-point on
   `CON-001`'s shipped code.
6. **The Outcome Tag Prompt sheet is triggered directly after the Contact Reveal sheet closes, same session** —
   shipped as planned, not via a Notifications-Inbox tap-through.
7. **"Maybe later" performs zero network calls and creates no row** — shipped as planned.

Grouped at this closeout into 3 ADRs per the architect's own explicit grouping recommendation (group by
load-bearing precedent, not one ADR per Plan decision — mirroring how ADR-044/045 already did this for
`CON-001`): **ADR-048** (Decisions 1 + 4 — module placement + immutability), **ADR-049** (Decisions 2 + 3 —
ownership shape + atomicity), **ADR-050** (Decisions 5 + 6 + 7 — notification touch-point + mobile delivery).

---

## Review Process — a full, honest account

### `tester` — independent verification against real infrastructure, no bugs found

The tester independently verified all 6 verbatim ACs with real evidence (real DB, real HTTP round trips, real
widget tests) and found **no functional bugs of any kind**. Its only addition was closing a genuine
verification-rigor gap, not a defect:

- **A genuine two-independent-session concurrency proof for the uniqueness guard.** The Plan's own test coverage
  called for a "concurrent-submission-shaped" test; the tester went further and constructed a real test with two
  fully independent database sessions racing a `try_create` call against the same `contact_view_id` at the same
  moment — not a sequential "call it twice" assertion. The result: exactly one row was ever written, and the
  losing session's call genuinely raised `OutcomeTagAlreadyExistsError` from the real `ON CONFLICT DO NOTHING`
  path, not from any application-level pre-check. This **proves** the atomic mechanism already worked correctly —
  it does not fix anything, since nothing was broken.

Final counts: 721/721 backend tests pass, 211/211 mobile tests pass, `flutter analyze`/`ruff check .` both clean.

### `architect` — one minor, non-blocking finding; APPROVED

The architect's review returned **APPROVED**, with a single documentation-only finding, not a code defect:

- **`02_ARCHITECTURE.md`'s System Overview diagram** had a combined "Review & Outcome Tag" module bubble label,
  which could be misread by a future reader as implying Outcome Tag belongs conceptually with the future Review
  module rather than Contact — the opposite of where it actually lives (`04_DATABASE.md`'s Contact Domain
  section, `backend/app/modules/contact/`). Everything else — the ownership-check shape against `06_SECURITY.md`/
  ADR-015, the `ON CONFLICT DO NOTHING` mechanism's genuine atomicity, the `ContactService` touch-point's
  purely-additive nature, and the module-placement choice against `02_ARCHITECTURE.md` — was reviewed and
  confirmed correct with no further findings.
- **Fix (this closeout):** `02_ARCHITECTURE.md`'s diagram bubbles relabeled to "Contact View / Outcome Tag" and
  "Review" as separate lines, with a short clarifying note added directly below the diagram cross-referencing
  `04_DATABASE.md` and this story's ADR-048, so a future reader doesn't have to re-derive correct module
  ownership from `04_DATABASE.md` alone.

**Final verdict: APPROVED, zero findings requiring a fix.** (The diagram-label note is a documentation
clarification the architect itself characterized as minor and non-blocking, not a "finding requiring fixes" in
the sense that would have blocked sign-off — fixed anyway at this closeout for completeness.)

### Final verdicts

- **`tester`**: all 6 ACs independently verified; **no bugs found** — one genuine concurrency test added, proving
  (not fixing) that the atomic uniqueness mechanism already worked correctly.
- **`architect`**: **APPROVED**, zero findings requiring fixes; one minor documentation note (the diagram label)
  addressed at this closeout.
- **CTO sign-off** received after both final verdicts were presented, per standing process.

**This is notable: `REV-001` and `MAT-001` are the only two stories in this project's history to ship with zero
real bugs found during review.**

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `outcome_tags` table exists via migration, with a unique constraint on `contact_view_id` (one outcome tag per Contact View) | Pass — real migration, verified against `04_DATABASE.md`'s exact spec, no deviation; uniqueness independently proven under genuine two-independent-session concurrency |
| 2 | Only the Customer who owns the underlying Contact View can submit an outcome tag for it — attempting to submit for someone else's Contact View is rejected | Pass — `ensure_owner_or_not_found` raises `ContactViewNotFoundError` (404) for a different customer's Contact View or a nonexistent one, with zero rows written, verified at both the service and HTTP layers |
| 3 | The prompt ("Did you hire them?") is triggered after a Contact View, via a notification, and is dismissible ("Maybe later") without penalty | Pass — a `type="outcome_tag_prompt"` Notification row is genuinely created at Contact View creation time; the mobile sheet genuinely renders after a real Contact Reveal; "Maybe later" is confirmed (mock-repository-never-called assertion) to make zero network calls |
| 4 | The outcome tag does not attempt to capture payment amount, job completion detail, or scheduling | Pass — direct inspection of the migration/model columns, request/response schemas, and mobile models confirms no such field exists anywhere in this story's new surface |
| 5 | A "No" or absent outcome tag is still retained as a signal (not discarded) — it is not required to be "Yes" for the tag itself to exist, only for a Review to follow | Pass — a `hired=false` row is queried back and confirmed present, not deleted or coerced; a Contact View with no outcome tag at all is confirmed a valid, unexceptional state |
| 6 | Automated tests cover the ownership restriction and the uniqueness-per-Contact-View constraint | Pass — both present as explicit, separately-named test cases at the service and API layers, plus the tester's added genuine two-session concurrency test for uniqueness |

**6 of 6 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded three new ADRs, grouped by load-bearing precedent per the architect's
  own recommendation:
  - **ADR-048** — module placement + immutability (Decisions 1 + 4): `outcome_tags` extends the existing
    `contact` module (the `administration` multi-aggregate-root precedent); an outcome tag is immutable/one-shot.
  - **ADR-049** — ownership shape + atomicity (Decisions 2 + 3): AC2's 404 (`ContactViewNotFoundError`, via
    `ensure_owner_or_not_found`), deliberately distinct from `CON-001`'s self-dealing 403; AC1/AC6's atomic
    `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` uniqueness guard, independently proven under genuine
    two-session concurrency.
  - **ADR-050** — notification touch-point + mobile delivery trim (Decisions 5 + 6 + 7): the flagged, additive
    touch-point on `CON-001`'s shipped `ContactService`; the mobile sheet chained after Contact Reveal, not a
    Notifications-Inbox tap-through; "Maybe later"'s zero-network-call mechanics.
- **`docs/AI/04_DATABASE.md`** — `contact.outcome_tags` marked shipped, cross-referencing ADR-048/ADR-049; no
  deviation from the existing spec.
- **`docs/AI/02_ARCHITECTURE.md`** — the System Overview diagram's combined "Review & Outcome Tag" bubble
  relabeled to separate "Contact View / Outcome Tag" and "Review" lines, with a short clarifying note added
  cross-referencing `04_DATABASE.md` and ADR-048 — the architect's one minor finding, addressed at this closeout.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 9 section added (1 of 2 stories done: `REV-001`;
  `REV-002` next), Milestone ML9 marked started.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `REV-001`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect `REV-001` shipped, `REV-002` promoted to the next
  startable story (pending the CTO's explicit instruction), ADR numbering advanced to ADR-050, test counts
  updated (721 backend / 211 mobile).

### A note on Open Question 1's disposition

The Plan's Open Question 1 (immediate vs. eventually-delayed notification timing) was CTO-confirmed as "fire
immediately" during planning. This remains a one-line future change — moving the `notify_outcome_tag_prompt` call
to a scheduled job — once real scheduling infrastructure exists anywhere in this codebase; no action is needed
now, consistent with how the Plan itself framed it (flagged for CTO awareness, not a blocker).

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `REV-001` row** still needs its Status updated to "Done" and rolled up
  through ML9-EP01/ML9/SP09/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure by the orchestrator, not performed by this closeout.
- **`13_OPEN_DECISIONS.md` item 14** (`provider_rating_summaries`) remains genuinely open — this is explicitly
  `REV-002`'s decision to make, unaffected by this story.
- **`REV-002`** ("leave a verified review after a successful hire") is the next story in this epic (ML9-EP01),
  depends on `REV-001`, and remains unplanned/unstarted, gated on an explicit CTO "Start REV-002" instruction.

---

## Testing Performed

- `backend` implementation: new `contact` module test coverage (`test_outcome_tag_service.py`,
  `test_outcome_tag_api.py`), extended `test_contact_service.py` (the new notification touch-point regression)
  and `test_notification_service.py` (`notify_outcome_tag_prompt`). Full suite green immediately after
  implementation.
- `frontend` implementation: new `provider_profile` feature test coverage (`OutcomeTagPromptController`,
  `OutcomeTagPromptSheet`), updated `provider_profile_screen_test.dart` for the sequential Contact Reveal →
  Outcome Tag Prompt chain. Full mobile suite green immediately after implementation.
- `tester` agent: independently verified all 6 ACs against real infrastructure; added a genuine
  two-independent-session concurrency test proving (not fixing) the atomic uniqueness mechanism; no functional
  bugs found. Final: 721/721 backend, 211/211 mobile.
- `architect` agent: single review pass — **APPROVED**, one minor documentation-only finding (the
  `02_ARCHITECTURE.md` diagram label), addressed at this closeout.
- User (CTO) sign-off received after both final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/` (new migration — `outcome_tags_domain`, on top of `024bcc0fbaf8`)
- `backend/app/modules/contact/models.py` (`OutcomeTag`, alongside `ContactView`)
- `backend/app/modules/contact/repositories/outcome_tag_repository.py` (new — `try_create`)
- `backend/app/modules/contact/services/outcome_tag_service.py` (new — `submit_outcome_tag`)
- `backend/app/modules/contact/schemas.py` (`SubmitOutcomeTagRequest`, `OutcomeTagResponse`)
- `backend/app/modules/contact/api.py` (`POST /contact-views/{contact_view_id}/outcome-tag`)
- `backend/app/modules/contact/dependencies.py` (`get_outcome_tag_repository`, `get_outcome_tag_service`)
- `backend/app/modules/contact/services/contact_service.py` (flagged additive touch-point)
- `backend/app/core/exceptions/exceptions.py` (`ContactViewNotFoundError`, `OutcomeTagAlreadyExistsError`)
- `backend/app/modules/notification/services/notification_service.py` (`notify_outcome_tag_prompt`)
- `backend/tests/modules/contact/test_outcome_tag_service.py`, `test_outcome_tag_api.py` (new)
- `backend/tests/modules/contact/test_contact_service.py` (extended — notification regression)
- `backend/tests/modules/notification/test_notification_service.py` (extended)

### Mobile
- `mobile/lib/features/provider_profile/domain/models/outcome_tag.dart`,
  `outcome_tag_exception.dart` (new)
- `mobile/lib/features/provider_profile/data/provider_profile_repository.dart` (`submitOutcomeTag`)
- `mobile/lib/features/provider_profile/state/outcome_tag_prompt_controller.dart` (new)
- `mobile/lib/features/provider_profile/presentation/widgets/outcome_tag_prompt_sheet.dart` (new)
- `mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart` (async
  `_onContactTap`, sheet chaining)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-048, ADR-049, ADR-050
- `docs/AI/04_DATABASE.md` — `contact.outcome_tags` marked shipped
- `docs/AI/02_ARCHITECTURE.md` — System Overview diagram label fix
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 9 / Milestone ML9 section
- `docs/AI/SESSION_HANDOFF.md` — refreshed state, ADR numbering, REV-002 promoted to startable
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **`REV-002`** ("leave a verified review after a successful hire") is the next story in this epic (ML9-EP01),
  depends on `REV-001`, and is the sole next candidate — not planned or started by this closeout, gated on an
  explicit CTO "Start REV-002" instruction. It will finally build `reviews`/`provider_rating_summaries`, resolving
  `13_OPEN_DECISIONS.md` item 14.
- **`13_OPEN_DECISIONS.md` item 14** (whether `provider_rating_summaries` is still needed once real reviews exist)
  is now `REV-002`'s decision to make — unaffected by this story.
- **The atomic-conditional-write family now has a documented INSERT-shaped member** (ADR-049) alongside its three
  existing UPDATE-shaped ones — `REV-002`'s own `reviews.contact_view_id` uniqueness constraint is a direct
  candidate to reuse this exact mechanism.
- **`docs/AI/Project_Tracker.xlsx`'s `REV-001` row** still needs its Status flipped to "Done" and rolled up
  through ML9-EP01/ML9/SP09/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.
- **No `Checkpoint_S09_REV-001.md` file existed at this closeout** — this story was reported to the tech-lead as
  already fully implemented, tested, and reviewed (backend, mobile, tester, architect all complete, CTO signed
  off) in the same session that produced this Walkthrough, so no interim Checkpoint was ever written or needed to
  be deleted.

---

**End of Document**
