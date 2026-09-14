# Walkthrough S09 REV-002

## Story: Leave a Verified Review After a Successful Hire

**Sprint:** 09 | **Story ID:** REV-002 | **Priority:** High | **Status:** Done

As a customer who confirmed a hire, I want to rate and review the provider, so that future customers can trust
the provider's track record — and so that reviews can never be submitted by someone who didn't actually go
through a real Contact View and a positive outcome. This is the anchor-verified review model: a Review can only
exist against a Contact View carrying a "Yes" outcome tag from `REV-001`. Because `CON-001`'s self-dealing guard
already blocks a provider from generating a Contact View against their own listing, this story's anchor
requirement transitively blocks self-reviews too, without needing a second explicit check. **Scope boundary:**
does not include provider-side display of reviews beyond the rating summary recalculation.

Full context, the 7 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S09_REV-002.md`.

All work is committed and pushed to this branch across commits `d61d8e4` (backend), `0a11e87` (frontend), and
`44f1c56` (docs: review outcomes).

**This is Sprint 9 / Milestone ML9's second and final story.** With `REV-002` done, **Milestone ML9 ("Outcome &
Reviews") is now fully complete — 2 of 2 stories done: `REV-001`, `REV-002`.**

---

## What was implemented

### Backend — a new, standalone `review` module (`backend/app/modules/review/`)

Unlike `REV-001`'s `outcome_tags` (folded into the existing `contact` module because it shared `contact`'s own
Postgres schema), `reviews`/`provider_rating_summaries` live in their own `review` schema per `04_DATABASE.md`'s
pre-existing spec — so this story builds a genuinely new module, not an extension (Decision 1 / **ADR-051**).

- **Two new migrations** on top of `e11a26e9560e` (`outcome_tags_domain`): `reviews_domain` (creates the `review`
  schema and both `review.reviews`/`review.provider_rating_summaries` tables, exactly per `04_DATABASE.md`'s
  pre-existing spec — `uq_reviews_contact_view_id`, `chk_reviews_rating_range CHECK (rating BETWEEN 1 AND 5)`,
  `idx_reviews_provider_id`, `uq_provider_rating_summaries_provider_id`) and
  `provider_average_rating_range_invariant` (adds `chk_providers_average_rating_range CHECK (average_rating IS
  NULL OR average_rating BETWEEN 0 AND 5)` to `provider.providers`, mirroring the
  `provider_discoverability_invariant` separately-scoped-migration precedent).
- **`Review`/`ProviderRatingSummary` models**, `ReviewRepository` (`try_create` — the ADR-049 atomic
  `INSERT ... ON CONFLICT (contact_view_id) DO NOTHING ... RETURNING` pattern; `compute_rating_aggregate`),
  `ProviderRatingSummaryRepository` (`upsert`).
- **`ReviewService.submit_review`** — resolves the caller's `customer_profiles` row, resolves and
  ownership-checks the `ContactView` (`ensure_owner_or_not_found` → `ContactViewNotFoundError`, 404), resolves
  the anchoring `OutcomeTag` via a new `OutcomeTagRepository.get_by_contact_view_id` and rejects with
  `ReviewAnchorNotVerifiedError` (409) if missing or `hired=false`, locks the target provider's row
  (`ProviderService.lock_for_rating_recalculation`, `SELECT ... FOR UPDATE`), inserts the review
  (`ReviewAlreadyExistsError`, 409, on a genuine conflict), recomputes the rating aggregate from raw `reviews`
  rows, and writes the same computed values to both `provider_rating_summaries` and
  `providers.average_rating`/`review_count` — all in one transaction (Decision 3 / **ADR-052**).
- **`POST /contact-views/{contact_view_id}/review`** — mounted at the shared `/contact-views` prefix, mirroring
  `verification_router`'s separate-module-shared-prefix shape; `require_role(ROLE_CUSTOMER)`.
- New exceptions `ReviewAnchorNotVerifiedError` (409) and `ReviewAlreadyExistsError` (409); ownership rejection
  reuses `ContactViewNotFoundError` (404) verbatim (Decision 5 / **ADR-053**).
- Small additions to existing modules: `OutcomeTagRepository.get_by_contact_view_id` (`contact`);
  `ProviderRepository.get_by_id_for_update`, `ProviderService.lock_for_rating_recalculation`/
  `apply_rating_recalculation` (`provider`).

### Mobile (`mobile/lib/features/provider_profile/` — extended, not a new feature)

- **`WriteReviewScreen`** (S-10): provider name/photo, a five-star `_StarRatingInput` (no default selection),
  an optional multi-line comment field (2000-char cap), a Submit button disabled until a rating is chosen, and a
  "Thanks!" confirmation that pops back to `ProviderProfileScreen` on success.
- **`WriteReviewController`** (Riverpod, `.autoDispose.family` keyed by `contactViewId`), `Review`/
  `ReviewException`/`WriteReviewArgs` domain models, `ProviderProfileRepository.submitReview`.
- **`ProviderProfileScreen._onContactTap`** extended (Decision 7): after the Outcome Tag Prompt sheet closes,
  reads `outcomeTagPromptControllerProvider`'s post-close state; only if `submitted && lastHired == true` does it
  push `AppRoutes.writeReview` — `OutcomeTagPromptSheet`/`OutcomeTagPromptController` themselves are untouched.
  `AppRoutes.writeReview` has exactly one call site anywhere in the app, satisfying AC6 structurally.
- New l10n keys (`writeReviewTitle`, `writeReviewRatingLabel`, `writeReviewCommentLabel`,
  `writeReviewSubmitLabel`, `writeReviewThanksMessage`) in `app_en.arb`/`app_ar.arb`.

**One flagged, non-blocking deviation:** the backend's `ErrorResponse` carries no structured error code, so the
mobile client cannot distinguish `ReviewAnchorNotVerifiedError` from `ReviewAlreadyExistsError` from the raw HTTP
response — both 409s map to `ReviewErrorType.anchorNotVerified` on mobile today. Functionally inconsequential
(the screen shows the identical plain-language inline error either way, and AC6's own guard makes these rare,
effectively-unreachable edge cases); `architect` reviewed and accepted this as-is. Revisiting it would require
adding a structured error identifier to `ErrorResponse`, out of this story's scope.

---

## The 7 Architecture Decisions, as actually shipped

All 7 decisions from `Plan_S09_REV-002.md` shipped exactly as planned, with no implementation-time deviations:

1. **`review` is a new, standalone module, not folded into `contact`**, because it owns a genuinely separate
   Postgres schema — the codebase's actual one-schema-one-module default, with `REV-001`'s `outcome_tags`
   remaining the deliberate, narrowly-scoped exception, not a general rule.
2. **Two separate migrations** (`reviews_domain`, then `provider_average_rating_range_invariant`), mirroring the
   `provider_discoverability_invariant` precedent.
3. **Rating-summary recalculation is a full recompute, lock-guarded** by `SELECT ... FOR UPDATE` on the target
   `providers` row — never an incremental running average, to avoid `NUMERIC(3,2)` rounding drift compounding
   over a provider's long-term review history.
4. **AC5's transitivity claim is proven by demonstrating the self-dealing Contact View never exists to anchor
   against**, not by adding a redundant self-dealing check inside `ReviewService` — the story's own text
   explicitly instructs against a second check, and the anchor requirement already makes the state unreachable
   by construction.
5. **Anchor-verification rejection is `ReviewAnchorNotVerifiedError` (409); ownership reuses
   `ContactViewNotFoundError` (404); uniqueness is `ReviewAlreadyExistsError` (409)** — three independently
   testable, separately-asserted rejection paths, not collapsed into one generic exception.
6. **Rating validated at three redundant layers** — Pydantic (`ge=1, le=5`), DB `CHECK`
   (`chk_reviews_rating_range`), and `SMALLINT` column type — defense-in-depth, mirroring `VER-002`'s established
   posture.
7. **Write-a-Review lives in the existing `provider_profile` feature**, triggered from
   `ProviderProfileScreen._onContactTap` reading `OutcomeTagPromptController`'s post-close state — no change to
   `REV-001`'s already-shipped sheet/controller.

Grouped at this closeout into 3 ADRs by architectural theme (module placement; recalculation correctness;
exception shapes), mirroring how `REV-001`'s own closeout grouped its 7 decisions into 3 ADRs: **ADR-051**
(Decision 1 — module placement), **ADR-052** (Decision 3 — full-recompute + lock-guarded recalculation),
**ADR-053** (Decision 5 — exception shapes). Decision 4's AC5 test methodology and Decision 2's migration split
are recorded in this Walkthrough and the Plan, not as separate ADRs — they are testing/sequencing choices
downstream of Decision 1/3, not standalone architectural precedents with their own future reuse shape.

---

## Review Process — a full, honest account

### `tester` — independent verification against real infrastructure, no bugs found

The tester independently verified all 7 verbatim ACs with real evidence (real DB, real HTTP round trips, real
widget tests) and found **no functional bugs of any kind**. Coverage included:

- **AC1/AC4's genuine concurrency proof**: a real two-independent-database-session test
  (`asyncio.gather`, same provider, overlapping transactions) confirming both reviews are counted correctly in
  the final `provider_rating_summaries`/`providers.average_rating`/`review_count` values — not a lost update —
  and that the `reviews.contact_view_id` uniqueness constraint genuinely rejects a second insert via the real
  `ON CONFLICT DO NOTHING` path.
- **AC4's "same transaction" claim**: a rollback test confirming a review write that fails mid-recalculation
  leaves no partial write across `reviews`/`provider_rating_summaries`/`providers`.
- **AC5's structural-unreachability methodology**: rather than trying to construct a self-dealing Review and
  assert it's rejected (there is nothing to reject — the anchor itself never exists), the test constructs
  `CON-001`'s own dual-role fixture, confirms `SelfDealingContactError` on the `ContactService.create_contact_view`
  attempt (zero `contact_views` rows), then confirms `ContactViewNotFoundError` on a subsequent
  `ReviewService.submit_review` attempt against a fabricated `contact_view_id` for that same pairing (zero
  `reviews` rows) — an honest test of the real mechanism, not one dressed up to exercise a self-dealing check
  that deliberately does not exist in `ReviewService`.
- **AC2's three separately-named rejection cases** (no outcome tag, `hired=false`, not-owned/nonexistent contact
  view), each independently asserted at both the service and HTTP layers with zero-rows-written confirmation.
- **AC6's mobile coverage**: the positive push (`hired=true` → `AppRoutes.writeReview` with correct args) and
  three explicit negative cases (`hired=false`, "Maybe later," an unrecoverable-error dismissal — none push the
  route).

Final counts: **752/752 backend tests, 233/233 mobile tests**, `ruff check .`/`flutter analyze` both clean.

### `architect` — clean, zero findings; no fix-and-recheck round needed

The architect's review returned a **clean verdict with no findings that block sign-off** — this story joins
`MAT-001` and `REV-001` as one of only a few stories in this project's history to ship with zero real bugs and
zero blocking findings across both review passes. Specifically confirmed, independently, not merely trusted:

- **Decision 1 (module placement)**: correct against the actual one-schema-one-module default; no cross-module
  logic coupling in `review/models.py` (FKs into `contact`/`customer`/`provider` are ordinary cross-schema FKs).
- **Cross-module edges vs ADR-047**: `ReviewService` reaches `provider` only via `ProviderService`, never
  `ProviderRepository` directly (confirmed by grep); the raw `contact`/`customer` Repository edges are the
  documented ADR-047 exception, named explicitly in `review/dependencies.py`'s own docstring.
- **Decision 3 (lock correctness)**: `get_by_id_for_update`/`FOR UPDATE` on `providers` is the only row-lock
  anywhere in the backend (repo-wide grep) — no lock-order-inversion deadlock is possible; the lock is held
  through recompute/upsert/apply with no external I/O awaited while held.
- **AC5 reasoning**: independently re-verified, not trusted — confirmed `ContactViewRepository.create` has
  exactly one call site in the entire codebase, so the self-dealing state is structurally unreachable, not merely
  untested.
- **Decision 5 (exceptions)**: status code choices correct against the established "resource exists, state
  blocks write" 409 family and ADR-015's non-revealing-404 convention; no information leak.
- **The mobile 409-collapsing deviation** (both new exceptions surfacing as one `ReviewErrorType` on mobile):
  reviewed and accepted as functionally inconsequential, not a blocking finding.

**Final verdict: CLEAN — no findings that block sign-off.** No fix-and-recheck round was required for this story.

### Final verdicts

- **`tester`**: all 7 ACs independently verified; **no bugs found**.
- **`architect`**: **CLEAN**, zero findings.
- **CTO sign-off** received after both final verdicts were presented, per standing process.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `reviews`/`provider_rating_summaries` tables exist via migration; `reviews.contact_view_id` unique, one review per Contact View | Pass — real migration, no deviation from `04_DATABASE.md`'s spec; uniqueness independently proven under genuine two-session concurrency, plus a direct row-count assertion |
| 2 | Submitting a review only possible with `outcome_tags.hired=true`; rejected otherwise (no tag, or `hired=false`) | Pass — `ReviewAnchorNotVerifiedError` (409) for both cases, each a separately-named test, zero `reviews` rows written; ownership separately rejected via `ContactViewNotFoundError` (404) |
| 3 | Rating constrained to 1–5; comment optional free text | Pass — three redundant layers (Pydantic 422, DB `CHECK` proven via a direct raw-insert test bypassing the API, `SMALLINT` column type); `comment=None` confirmed to succeed |
| 4 | `provider_rating_summaries` recalculated in the same transaction as the review write — never left stale | Pass — sequential recalculation-correctness test, a genuine two-overlapping-transaction concurrency test (no lost update), and a same-transaction rollback test proving no partial-write window |
| 5 | A provider cannot end up with a review pointing back at their own listing via this path (automated test) | Pass — the dual-role fixture test: `SelfDealingContactError` on the Contact View attempt (zero rows), `ContactViewNotFoundError` on the subsequent review attempt against a fabricated `contact_view_id` (zero rows) |
| 6 | Write-a-Review screen only reachable after a "Yes" outcome tag — no other navigation path | Pass — positive case (`hired=true` pushes the route with correct args) and three explicit negative cases (`hired=false`, "Maybe later," unrecoverable-error dismissal — none push it); `AppRoutes.writeReview` has exactly one call site in the app |
| 7 | Automated tests cover the anchor-verification rejection case and the rating-summary recalculation correctness | Pass — both present as explicit, separately-named test cases (AC2's rejection tests, AC4's recalculation/concurrency/rollback tests), not merged into one parameterized test |

**7 of 7 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded three new ADRs, grouped by architectural theme:
  - **ADR-051** — `review` module placement (Decision 1): new standalone module/schema vs. `REV-001`'s
    shared-schema `outcome_tags` exception.
  - **ADR-052** — rating-summary recalculation (Decision 3): full recompute, `SELECT ... FOR UPDATE`-guarded,
    never incremental (`NUMERIC(3,2)` rounding-drift rejection).
  - **ADR-053** — review rejection exception shapes (Decision 5): `ReviewAnchorNotVerifiedError`/
    `ReviewAlreadyExistsError` (409), reused `ContactViewNotFoundError` (404).
- **`docs/AI/04_DATABASE.md`** — `review.reviews`/`review.provider_rating_summaries` marked shipped, cross-
  referencing ADR-051/052/053; corrected the pre-existing attribution error ("`REV-001`, as the first real writer
  of this column, should add [the `CHECK` constraint]") — `REV-001` never wrote to `providers.average_rating`;
  `REV-002` is the actual first real writer and the one that added `chk_providers_average_rating_range`.
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 14 resolved: both `providers.average_rating`/`review_count`
  (`MAT-001`'s ranking-formula hot-path read target, unchanged) and `review.provider_rating_summaries` (the
  Review domain's own decoupled read-model) are needed, written from the same computed values in the same
  transaction.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 9 section updated to 2 of 2 stories done; Milestone ML9
  marked fully complete.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `REV-002`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect `REV-002` shipped, Milestone ML9 fully complete, ADR
  numbering advanced to ADR-053, test counts updated (752 backend / 233 mobile), Sprint 10 flagged as next
  (first story TBD by tracker lookup).

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `REV-002` row** still needs its Status updated to "Done" and rolled up
  through ML9-EP01/ML9/SP09/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure by the orchestrator, not performed by this closeout.
- **The mobile 409-collapsing gap** (both new review-rejection exceptions surface as one `ReviewErrorType` on
  mobile, since `ErrorResponse` carries no structured error code) remains as `architect` accepted it — functionally
  inconsequential today, revisitable only if `ErrorResponse` itself gains a structured error identifier in a
  future story.
- **Sprint 10** is the next sprint; its first story is not identified in this closeout — the orchestrator must
  look it up in `docs/AI/Project_Tracker.xlsx` before the next planning session, per this project's standing
  practice of never planning ahead without an explicit CTO "Start X" instruction.

---

## Testing Performed

- `backend` implementation: new `review` module test coverage (`test_review_service.py`, `test_review_api.py`),
  plus extensions to `test_outcome_tag_repository.py` (`get_by_contact_view_id`) and `test_provider_repository.py`/
  `test_provider_service.py` (`get_by_id_for_update`, `lock_for_rating_recalculation`,
  `apply_rating_recalculation`). Migrations verified end-to-end against a real scratch Postgres DB
  (`upgrade head` → `downgrade -1` (twice) → `upgrade head`, all clean). Full suite green immediately after
  implementation: 752/752 (baseline 721, +31 new, zero regressions).
- `frontend` implementation: new `provider_profile` feature test coverage (`write_review_controller_test.dart`,
  `write_review_screen_test.dart`, `provider_profile_repository_test.dart`), updated
  `provider_profile_screen_test.dart` for the AC6 positive/negative chaining cases. Full mobile suite green
  immediately after implementation: 233/233 (baseline 211, +22 new, zero regressions).
- `tester` agent: independently verified all 7 ACs against real infrastructure (real DB, real HTTP round trips,
  real widget tests); no functional bugs found. Final: 752/752 backend, 233/233 mobile.
- `architect` agent: single review pass — **CLEAN, zero findings**, no fix-and-recheck round required.
- User (CTO) sign-off received after both final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/` (two new migrations — `reviews_domain`, `provider_average_rating_range_invariant`,
  on top of `e11a26e9560e`)
- `backend/app/modules/review/models.py` (`Review`, `ProviderRatingSummary`)
- `backend/app/modules/review/repositories/review_repository.py` (`try_create`, `compute_rating_aggregate`)
- `backend/app/modules/review/repositories/provider_rating_summary_repository.py` (`upsert`)
- `backend/app/modules/review/services/review_service.py` (`submit_review`)
- `backend/app/modules/review/schemas.py` (`SubmitReviewRequest`, `ReviewResponse`)
- `backend/app/modules/review/api.py` (`POST /contact-views/{contact_view_id}/review`)
- `backend/app/modules/review/dependencies.py`
- `backend/app/modules/contact/repositories/outcome_tag_repository.py` (`get_by_contact_view_id`, new)
- `backend/app/modules/provider/repositories/provider_repository.py` (`get_by_id_for_update`, new)
- `backend/app/modules/provider/services/provider_service.py` (`lock_for_rating_recalculation`,
  `apply_rating_recalculation`, new)
- `backend/app/modules/provider/models.py` (`chk_providers_average_rating_range` added to `__table_args__`)
- `backend/app/core/exceptions/exceptions.py` (`ReviewAnchorNotVerifiedError`, `ReviewAlreadyExistsError`)
- `backend/app/api/v1/api.py` (`review_router` registered at `/contact-views`)
- `backend/tests/modules/review/test_review_service.py`, `test_review_api.py` (new)
- `backend/tests/modules/contact/test_outcome_tag_repository.py` (new)
- `backend/tests/modules/provider/test_provider_repository.py` (new); `test_provider_service.py` (extended)

### Mobile
- `mobile/lib/features/provider_profile/domain/models/review.dart`, `review_exception.dart`,
  `write_review_args.dart` (new)
- `mobile/lib/features/provider_profile/state/write_review_controller.dart` (new)
- `mobile/lib/features/provider_profile/presentation/screens/write_review_screen.dart` (new)
- `mobile/lib/features/provider_profile/presentation/utils/review_error_copy.dart` (new)
- `mobile/lib/features/provider_profile/data/provider_profile_repository.dart` (`submitReview`, added)
- `mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart` (`_onContactTap`
  extended)
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (`writeReview` route)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-051, ADR-052, ADR-053
- `docs/AI/04_DATABASE.md` — Review Domain marked shipped, attribution correction
- `docs/AI/13_OPEN_DECISIONS.md` — item 14 resolved
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 9 / Milestone ML9 marked fully complete
- `docs/AI/SESSION_HANDOFF.md` — refreshed state, ADR numbering, Sprint 10 flagged as next
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Milestone ML9 ("Outcome & Reviews") is now fully complete** — both `REV-001` and `REV-002` are Done.
- **Sprint 10** is the next sprint. Its first story is **not identified by this closeout** — per standing
  practice, the orchestrator must look it up in `docs/AI/Project_Tracker.xlsx` and record it in
  `docs/AI/PROJECT_IMPLEMENTATION_STATE.md`/`docs/AI/SESSION_HANDOFF.md` before any engineering agent plans or
  starts it, gated on an explicit CTO "Start X" instruction.
- **The lock-then-full-recompute pattern (ADR-052) is now a documented precedent** for any future race-safe
  aggregate recompute over an unbounded, growing row set — reuse it rather than an incremental update, per its
  documented `NUMERIC` rounding-drift reasoning.
- **`docs/AI/Project_Tracker.xlsx`'s `REV-002` row** still needs its Status flipped to "Done" and rolled up
  through ML9-EP01/ML9/SP09/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.

---

**End of Document**
