# Checkpoint — Story REV-002 (Leave a Verified Review After a Successful Hire)

**Written by:** `frontend` agent (this update); backend section below written by the `backend` agent
**Status:** Backend implementation complete, all tests green. Frontend (mobile) implementation complete, all tests green. Tester/architect review not yet run.

---

## Current task

Backend build of REV-002 per `docs/implementation/plans/Plan_S09_REV-002.md` (all 7 architecture decisions CTO-confirmed, including the two flagged Open Questions). Build order followed the Plan's Delegation section: (a) both migrations, (b) the new `review` module (model/repositories/service/schemas/api/dependencies) with Decision 3 (recalculation race-safety) and Decision 4/5 (anchor verification + exception shapes) built and tested first, (c) small additions to `contact`'s `OutcomeTagRepository` and `provider`'s `ProviderRepository`/`ProviderService`.

## Files touched

**New migrations:**
- `backend/alembic/versions/2026_09_14_1000-b2b3c4d5e6f7_reviews_domain.py` — creates `review` schema, `review.reviews`, `review.provider_rating_summaries`.
- `backend/alembic/versions/2026_09_14_1100-c3c4d5e6f7a8_provider_average_rating_range_invariant.py` — adds `chk_providers_average_rating_range` to `provider.providers`.

**New `review` module:**
- `backend/app/modules/review/__init__.py`
- `backend/app/modules/review/models.py` — `Review`, `ProviderRatingSummary`.
- `backend/app/modules/review/repositories/__init__.py`
- `backend/app/modules/review/repositories/review_repository.py` — `try_create` (ADR-049 pattern), `compute_rating_aggregate`.
- `backend/app/modules/review/repositories/provider_rating_summary_repository.py` — `upsert`.
- `backend/app/modules/review/services/__init__.py`
- `backend/app/modules/review/services/review_service.py` — `submit_review` (anchor verification + race-safe recalculation).
- `backend/app/modules/review/schemas.py` — `SubmitReviewRequest`, `ReviewResponse`.
- `backend/app/modules/review/api.py` — `POST /contact-views/{contact_view_id}/review`.
- `backend/app/modules/review/dependencies.py`.

**Small additions to existing modules:**
- `backend/app/modules/contact/repositories/outcome_tag_repository.py` — added `get_by_contact_view_id`.
- `backend/app/modules/provider/repositories/provider_repository.py` — added `get_by_id_for_update`.
- `backend/app/modules/provider/services/provider_service.py` — added `lock_for_rating_recalculation`, `apply_rating_recalculation`.
- `backend/app/modules/provider/models.py` — added `chk_providers_average_rating_range` to `Provider.__table_args__` (kept in sync with migration).

**Wiring:**
- `backend/app/api/v1/api.py` — registered `review_router` at `prefix="/contact-views"`.
- `backend/app/core/exceptions/exceptions.py` + `__init__.py` — added `ReviewAnchorNotVerifiedError` (409), `ReviewAlreadyExistsError` (409).
- `backend/alembic/env.py` — added `import app.modules.review.models` (was missing; found and fixed during migration verification).

**Test infra:**
- `backend/tests/conftest.py` — registered `review` schema + `Review`/`ProviderRatingSummary` models in `db_engine`/`db_session` fixtures (creation, teardown, truncation order — before `ContactView`/`Provider`).
- `backend/tests/modules/category/test_category_migration.py` — added `review` to `_excluded_schemas` (its isolated-engine fixture excludes schemas with cross-schema FKs into other excluded schemas; `review.reviews` FKs into the already-excluded `contact` schema).

**New tests:**
- `backend/tests/modules/review/__init__.py`, `_helpers.py`
- `backend/tests/modules/review/test_review_service.py` — happy path, AC2 anchor-verification rejections (no outcome tag / hired=false / wrong owner / nonexistent), AC1 uniqueness, AC3 DB CHECK, AC4 sequential + **genuine concurrency** (`asyncio.gather`, two independent sessions, same provider) + same-transaction-rollback, AC5 self-dealing transitivity.
- `backend/tests/modules/review/test_review_api.py` — full HTTP round trip (201/404/409/401/403/422).
- `backend/tests/modules/contact/test_outcome_tag_repository.py` — `get_by_contact_view_id`.
- `backend/tests/modules/provider/test_provider_repository.py` — `get_by_id_for_update`.
- `backend/tests/modules/provider/test_provider_service.py` — added `TestLockForRatingRecalculation`, `TestApplyRatingRecalculation`.

## Verification performed

- Full backend suite: **752 passed** (baseline was 721; +31 new tests, zero regressions).
- `ruff check .`: all checks passed.
- `mypy`: **not runnable in this environment** — not installed in `backend/.venv`, and not listed in `pyproject.toml`'s `[dependency-groups] dev` (only `pytest`/`pytest-asyncio`/`ruff` are). This is a pre-existing environment gap, not introduced by this story. Flagging for `tech-lead`/`architect` awareness.
- Alembic migrations verified end-to-end against a real scratch Postgres DB (`ai_marketplace_migration_check`, created and dropped for this check only): `upgrade head` → `downgrade -1` (twice) → `upgrade head` all succeed cleanly, full chain from `101b27d7096b` through the two new revisions.

## What's next

1. **frontend** — Frontend Proposed Changes items 1-8 in the Plan (mobile `WriteReviewScreen`, `WriteReviewController`, `ProviderProfileScreen._onContactTap` extension, routing, l10n). Can integrate against `POST /contact-views/{contact_view_id}/review`'s real response shape (`ReviewResponse`: `id`, `contact_view_id`, `provider_id`, `rating`, `comment`, `created_at`), 404/409/422 error shapes as documented in `backend/app/modules/review/api.py`.
2. **tester** — verify all 7 ACs per the Plan's Verification Plan table. Backend-side evidence already exists in the test files above; tester should independently confirm (real DB, real HTTP) rather than trust this checkpoint's own claims.
3. **architect** — review Decision 1 (module placement), Decision 3 (lock correctness/deadlock risk), Decision 4 (AC5 "unreachable by construction" claim), Decision 5 (exception/status-code choices), `review/dependencies.py`'s cross-module edges against ADR-047.

## No deviations from the Plan (backend)

Everything in "Backend — Proposed Changes" items 1-19 was built as specified. The `alembic/env.py` model-import addition and the `test_category_migration.py` schema-exclusion-set addition were not explicitly listed in the Plan but are necessary consequences of adding a new domain module/schema, following the exact same pattern the Plan's own cited precedents (`outcome_tags_domain`, `contact_domain`) already established.

---

## Frontend (mobile) work — done by `frontend` agent

Built Frontend Proposed Changes items 1-8 in full, within the existing `mobile/lib/features/provider_profile/` feature (Decision 7 — no new feature directory).

### Files created

- `mobile/lib/features/provider_profile/domain/models/review.dart` — `Review` model, mirrors `ReviewResponse`.
- `mobile/lib/features/provider_profile/domain/models/review_exception.dart` — `ReviewException`/`ReviewErrorType` (`network`, `notFound`, `anchorNotVerified`, `alreadyExists`, `unknown`), mirrors `outcome_tag_exception.dart`'s shape.
- `mobile/lib/features/provider_profile/domain/models/write_review_args.dart` — `WriteReviewArgs` record typedef (`contactViewId`, `providerId`, `providerDisplayName`, `providerPhotoUrl`).
- `mobile/lib/features/provider_profile/state/write_review_controller.dart` — `WriteReviewController`/`WriteReviewState` (Riverpod, `.autoDispose.family` keyed by `contactViewId`), mirrors `OutcomeTagPromptController`'s shape.
- `mobile/lib/features/provider_profile/presentation/screens/write_review_screen.dart` — `WriteReviewScreen` (S-10): provider name/photo, `_StarRatingInput` (5 tappable stars, no default), optional multi-line comment field (2000-char cap), Submit button disabled until a rating is chosen, inline error display for every failure type, "Thanks!" confirmation + auto-pop on success.
- `mobile/lib/features/provider_profile/presentation/utils/review_error_copy.dart` — `reviewErrorMessage`, mirrors `outcome_tag_error_copy.dart`.
- Tests: `mobile/test/features/provider_profile/write_review_controller_test.dart`, `write_review_screen_test.dart`, `provider_profile_repository_test.dart` (new — HTTP-error-mapping regression coverage for `submitReview`, mirrors `conversation_repository_test.dart`'s pattern).

### Files modified

- `mobile/lib/features/provider_profile/data/provider_profile_repository.dart` — added `submitReview(contactViewId, rating, comment)` + `_mapReviewError`.
- `mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart` — `_onContactTap` extended per Decision 7: after the Outcome Tag Prompt sheet closes, reads `outcomeTagPromptControllerProvider(reveal.id)`; if `submitted && lastHired == true`, pushes `AppRoutes.writeReview` with `WriteReviewArgs`. `OutcomeTagPromptSheet`/`OutcomeTagPromptController` themselves untouched.
- `mobile/lib/core/routing/app_routes.dart` — added `AppRoutes.writeReview`.
- `mobile/lib/core/routing/app_router.dart` — registered the `GoRoute`, `extra`-required (`WriteReviewArgs`), redirects to `AppRoutes.homePlaceholder` if reached without it (mirrors `claimOtp`'s "no natural args-free parent" fallback choice).
- `mobile/lib/l10n/app_en.arb` / `app_ar.arb` — added the 5 keys the Plan named (`writeReviewTitle`, `writeReviewRatingLabel`, `writeReviewCommentLabel`, `writeReviewSubmitLabel`, `writeReviewThanksMessage`).
- Test fixtures: `mobile/test/features/provider_profile/fakes/fake_provider_profile_repository.dart` (added `submitReview` stubbing), `test_helpers.dart` (added a `write-review` stub route), `provider_profile_screen_test.dart` (added the AC6 positive + 3 negative chaining cases).

### One real deviation from the Plan (backend-response-shape gap, not a mobile oversight)

The Plan's mobile exception design (`review_exception.dart`... "mirrors outcome_tag_exception.dart's shape (notFound, anchorNotVerified, alreadyExists, network, unknown)") implies both 409 causes (`ReviewAnchorNotVerifiedError`, `ReviewAlreadyExistsError`) are independently distinguishable from the HTTP response. They are not: `backend/app/shared/schemas/response.py`'s `ErrorResponse` carries only `{success, message, errors}` — no structured error code/identifier — so both arrive as a bare 409 with no reliable signal to tell them apart (and this codebase's own convention, followed by every other repository, never parses the raw `message` string). `ProviderProfileRepository._mapReviewError` therefore maps every review 409 to `ReviewErrorType.anchorNotVerified`; `alreadyExists` is kept in the domain model for documentation/forward-compatibility but is never actually produced by today's real backend response. This is functionally inconsequential: `WriteReviewScreen` shows the identical plain-language inline error for every `ReviewErrorType` regardless, and AC6's own guard already means these are rare, effectively-unreachable edge cases in the normal flow. Flagged for `architect`/`tech-lead` awareness — if a finer-grained distinction is ever wanted, the backend would need to add a structured error identifier to `ErrorResponse` (out of this story's/this agent's scope to change).

### Verification performed

- `flutter test` (mobile/): before 211 passed, after **233 passed** (+22 new, zero regressions).
- `flutter analyze`: before and after, **no issues found**.
- `dart format` applied to every file created/touched this story; stable (0 changes on re-check).

### What's next

- **tester** — verify AC6/AC7's mobile-relevant coverage per the Plan's Verification Plan table (the positive push + 3 negative non-push cases in `provider_profile_screen_test.dart`; the star-input/disabled-Submit/success-pop widget tests in `write_review_screen_test.dart`).
- **architect** — review the 409-collapsing deviation above; confirm the "screen shows inline error rather than silently closing" UX choice is acceptable (`docs/AI/16_UX_GUIDELINES.md`).
