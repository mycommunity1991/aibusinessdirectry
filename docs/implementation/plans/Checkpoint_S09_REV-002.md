# Checkpoint — Story REV-002 (Leave a Verified Review After a Successful Hire)

**Written by:** `backend` agent
**Status:** Backend implementation complete, all tests green. Frontend (mobile) work not started. Tester/architect review not yet run.

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

## No deviations from the Plan

Everything in "Backend — Proposed Changes" items 1-19 was built as specified. The `alembic/env.py` model-import addition and the `test_category_migration.py` schema-exclusion-set addition were not explicitly listed in the Plan but are necessary consequences of adding a new domain module/schema, following the exact same pattern the Plan's own cited precedents (`outcome_tags_domain`, `contact_domain`) already established.
