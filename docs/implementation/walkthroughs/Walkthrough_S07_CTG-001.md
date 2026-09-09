# Walkthrough S07 CTG-001

## Story: Build the Real Category Domain and Seed the v1 Launch Taxonomy

**Sprint:** 07 | **Story ID:** CTG-001 | **Priority:** Critical | **Status:** Done

As the engineering team resolving `13_OPEN_DECISIONS.md` item 1 at the code level, this story builds the real
`category.categories` / `category.category_question_templates` / `category.provider_categories` schema and seeds
it with the CTO-approved v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md`) — 14 categories and their 47 AI
follow-up question templates — so `AI-001` (Sprint 7's Conversation/AI Intake domain) has a real, queryable
taxonomy to build against, instead of the free-text `provider.provider_category_labels` interim stand-in
PRO-001/PRO-002/DIR-001 have been using. **This story does not design or alter the taxonomy's content** —
`17_CATEGORY_TAXONOMY.md` is CTO-locked; it is about *how* to build and seed what that document specifies.
**Scope boundary:** does not reconcile `provider_category_labels` into `category.provider_categories`, and does
not touch DIR-001's `search` module in any way — both are explicitly deferred, separate follow-up work. Backend
only — no AC asked for a mobile screen, and `AI-001` (the eventual real consumer) doesn't exist yet.

Full context, the 6 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S07_CTG-001.md`.

All work is committed and pushed to branch `claude/provider-storefront-pro-001-qnicuj`: backend implementation
(`0c6dabd`) and a tester-found test-assertion fix (`adeeb0b`).

---

## What was implemented

### Backend (`backend/app/modules/category/`, new)

- **New, reversible Alembic migration** (`category_domain`, revision `a804c46bf703`, down-revision
  `a3f6e9c21d47`) — creates the `category` Postgres schema and its three tables exactly per `04_DATABASE.md`'s
  Category Domain section: `categories` (full `CommonColumnsMixin`-equivalent columns + `parent_category_id`
  self-FK, `name`, `name_ar`, `slug` with `uq_categories_slug`, `icon_url`, `sort_order`), `category_question_templates`
  (full common columns + `category_id` FK, `question_text`, `question_text_ar`, `question_type`, `options` JSONB,
  `is_required`, `sort_order`, indexed on `category_id`), and `provider_categories` (a pure join table — composite
  PK on `(provider_id, category_id)`, `is_primary`, `created_at` only, no common-columns mixin — created **empty**;
  reconciling `provider_category_labels` into it is explicitly out of scope for this story).
- **This codebase's first data-seeding migration.** `upgrade()` seeds all 14 categories and 47 question templates
  via `INSERT ... ON CONFLICT (slug) DO NOTHING ... RETURNING`, gating each category's question-template insert
  batch on that category having been genuinely, freshly returned this run (`category_question_templates` has no
  unique constraint of its own per spec, so its idempotency is entirely inherited from `categories.slug`'s
  conflict target). `upgrade()` is additionally guarded by a DDL-existence check (`"categories" in
  inspector.get_table_names(schema="category")`) so the function is safely re-callable even outside Alembic's
  normal one-time-per-revision bookkeeping — the specific mechanism recorded as **ADR-028** (see below).
  Seed content lives in `backend/app/modules/category/seed_data.py` (`CATEGORY_SEED`, `QUESTION_SEED_BY_SLUG`) —
  plain Python data, no SQLAlchemy/ORM import, transcribed verbatim from `17_CATEGORY_TAXONOMY.md` — so the
  taxonomy is never transcribed twice, and both the migration and the test suite's non-Alembic fixtures read the
  same source.
- **New module**, mirroring `administration`/`notification`'s "first slice of a real domain, no `api.py`" shape:
  `models.py` (`Category`, `CategoryQuestionTemplate`, `ProviderCategory`), `repositories/category_repository.py`
  (`list_active`, ordered by `sort_order`), `repositories/category_question_template_repository.py`
  (`list_for_category`, ordered by `sort_order`), `services/category_service.py` (`CategoryService`:
  `list_active_categories()`, `get_question_templates(category_id)` — returns an empty list for an unknown ID
  rather than raising), and `dependencies.py` (`get_category_service`, the standard DI-provider chain). **No
  `api.py`/HTTP route** — the implementation is fully real, backed by the complete seeded taxonomy; only the
  future caller (`AI-001`) doesn't exist yet, mirroring the already-established `ProviderService.list_by_ids`
  precedent (a real service method built ahead of its cross-module consumer, `VER-002`).
- **Bilingual Arabic content seeded now, not left `NULL`** — `name_ar` and `question_text_ar` carry
  `17_CATEGORY_TAXONOMY.md` v1.1.0's first-pass Arabic text for all 14 categories and all 47 questions, explicitly
  flagged everywhere (module docstring, migration docstring, this document) as first-pass and not yet
  native-speaker-verified. See Review Process below for how v1.1.0 came to exist.
- **`backend/tests/conftest.py`** — extended with the `category` schema/model registration (`CREATE SCHEMA IF NOT
  EXISTS category`, model import, teardown truncation list), the same mechanical addition every prior domain has
  made.
- **Tests (17 new, all passing)**:
  - `test_category_migration.py` — runs the migration's actual `upgrade()`/`downgrade()` functions against a real
    Postgres connection (not mocked): asserts column types/nullability/constraints/indexes for all three tables
    match `04_DATABASE.md` exactly (including the deliberate absence of any unique constraint on
    `category_question_templates`); runs `upgrade()` twice and asserts identical row counts (14 categories, the
    correct per-category question counts) with zero duplicates the second time; runs
    `upgrade() → downgrade() → upgrade()` on a fresh schema and re-asserts the same counts — both bypassing
    Alembic's own version bookkeeping, per AC4's literal wording.
  - `test_category_service.py` — seeds a test database directly from `seed_data.py` (the ordinary test fixtures
    never run Alembic), then asserts `list_active_categories()` returns exactly 14 categories in `sort_order`
    order with correct bilingual names/slugs; `get_question_templates(category_id)` returns the correct ordered
    question set (text, type, options, `is_required`) for representative categories spanning every real
    `question_type` in use (`single_select`, `multi_select`, `text`, `boolean` — `number` is not used by any of
    the 14 categories' real questions); every category's exact seeded question count; non-`NULL` bilingual text
    for every question; and an unknown `category_id` returns an empty list, not an error.

---

## The 6 Architecture Decisions, as actually shipped

All 6 decisions from `Plan_S07_CTG-001.md` shipped as planned, with no semantic deviations:

1. **New module: `backend/app/modules/category/`** — shipped exactly as planned, mirroring `administration`/
   `notification`'s no-`api.py` shape, not `search`'s no-`models.py` shape. `02_ARCHITECTURE.md` names Category
   as its own Core Business Module; conflating it with `provider` or `search` was rejected for the same reasons
   `Plan_S05_VER-001.md` originally rejected folding Verification into Provider.
2. **Seed mechanism: a canonical `seed_data.py` module plus an idempotent `INSERT ... ON CONFLICT (slug) DO
   NOTHING ... RETURNING` inside the same migration that creates the tables** — shipped exactly as planned; this
   codebase's first data-seeding migration, recorded as the new **ADR-028** (see Documentation Updated below).
3. **Read-only exposure (AC5): a genuine, real `CategoryService` with two plain methods; no `api.py`/HTTP route
   in this story** — shipped exactly as planned. Both methods return raw ORM entities, matching the established
   `ProviderService.list_by_ids` cross-module-read precedent.
4. **Bilingual Arabic content: seed the first-pass Arabic text now, explicitly flagged as provisional
   everywhere it appears** — shipped as planned, with one honest, unplanned wrinkle: the source document
   (`17_CATEGORY_TAXONOMY.md` v1.0.0) turned out not to actually contain the Arabic question text its own prose
   claimed existed. See Review Process below for the full account.
5. **Testing approach for idempotency and seed completeness** — shipped exactly as planned: a live-executed
   (non-mocked) migration test and a service-level seed-completeness/correctness test, per Decision 5's design.
6. **`conftest.py` extension** — shipped exactly as planned, the same mechanical addition every prior domain has
   made.

---

## Review Process — a full, honest account

### 1. `backend` — an honest data gap found and refused to paper over

While transcribing `17_CATEGORY_TAXONOMY.md` v1.0.0 into `seed_data.py`, the `backend` agent found that the
document's per-category question tables never actually contained any Arabic question text (`question_text_ar`)
in any row, despite the document's own prose claiming the same first-pass-translation caveat already covered it.
Rather than fabricate plausible-looking Arabic translations to fill the gap, the agent seeded `question_text_ar`
as `NULL` in its first version of the migration and flagged the discrepancy back up the chain — consistent with
this codebase's "never assert ungrounded data" principle. The CTO then corrected the source document directly:
`17_CATEGORY_TAXONOMY.md` is now v1.1.0, with real first-pass Arabic text added for all 47 questions across all
14 categories, carrying the identical "first-pass, not yet native-speaker-verified" caveat already stated for the
category names. The same `backend` agent then updated `seed_data.py` to seed the now-real Arabic question text
instead of `NULL`. This is recorded in both the taxonomy document's own change note and the migration's docstring
so the history isn't lost.

### 2. `tester` — independent verification of all 7 ACs against a real database, plus one genuine finding

The tester did not simply re-run the existing suite. It independently, against a real Postgres database:

- Ran the actual migration (not a mock) and queried the seeded rows directly to confirm all 14 categories and 47
  question templates exist with correct bilingual content.
- Ran `upgrade()` twice, and separately `upgrade() → downgrade() → upgrade()`, both bypassing Alembic's own
  revision-bookkeeping (calling the migration's Python functions directly against a live connection, not via the
  `alembic` CLI), to prove idempotency empirically rather than trust the test suite's own assertions about itself.
- Called `CategoryService`'s two methods directly and confirmed correct, real (non-stubbed) results.
- Confirmed zero interference with `search`/`provider`/`provider_category_labels` via a git diff of those modules
  against pre-story state and a direct query against `provider_category_labels` before/after the migration.

**Finding:** a tautological test assertion in `test_category_migration.py` — `assert "questions_unique_constraints"
not in info`, checking for a dict key that was never added in the first place, so the assertion always passed
regardless of the database's real state and provided zero actual coverage of "no unique constraint exists on
`category_question_templates`" (a fact Decision 2's idempotency design specifically depends on). **Fixed**
(commit `adeeb0b`): the test now actually calls `inspector.get_unique_constraints("category_question_templates",
schema="category")` and asserts the real result is an empty list — genuine coverage of the real database state,
not a vacuously-true check.

All 7 acceptance criteria were verified Pass with this direct evidence.

### 3. `architect` — APPROVED WITH RECOMMENDATIONS (non-blocking)

No code, security, or architecture defects were found. Two process recommendations, both non-blocking and both
acted on as part of this closeout:

1. Write an ADR documenting this codebase's first data-seeding-migration pattern (Decision 2) — done, recorded
   below as **ADR-028**.
2. Confirm the 7 reconstructed ACs' wording against the literal Tracker text (the Plan's own Acceptance Criteria
   section flagged that this session could not open the binary `.xlsx` tracker to verify verbatim) — done: the
   CTO confirmed the AC wording directly via the tracker's own raw-XML-safe editing procedure, and it matches the
   Plan's reconstructed list.

### Final test counts

- **Backend: 493 passed** (476 pre-existing + 17 new). `ruff check` clean.

---

## Acceptance Criteria — Verification

All 7 acceptance criteria (from `Plan_S07_CTG-001.md`, confirmed against the literal Tracker text by the CTO
during architect review) were independently verified by the `tester` agent with direct evidence against a real
Postgres database — see Review Process above.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `category.categories`, `category.category_question_templates`, and `category.provider_categories` exist via migration, exactly matching `04_DATABASE.md`'s Category Domain section (column types, nullability, constraints — `uq_categories_slug` — and indexes) | Pass |
| 2 | All 14 categories from `17_CATEGORY_TAXONOMY.md` are seeded with correct bilingual (EN/AR) names, slugs, and `sort_order` | Pass |
| 3 | Each category's `category_question_templates` rows are seeded exactly per `17_CATEGORY_TAXONOMY.md` (text/text_ar, type, options, `is_required`, `sort_order`) | Pass |
| 4 | The seeding mechanism is idempotent — upgrade run twice, or upgrade → downgrade → upgrade, never produces duplicate categories or question rows | Pass |
| 5 | A read-only `CategoryService` exists so a future consumer (`AI-001`) can retrieve categories and their question templates | Pass |
| 6 | This story does not modify/migrate/reconcile `provider_category_labels`, and does not alter DIR-001's `search` module or its endpoint behavior in any way | Pass |
| 7 | Automated tests cover schema creation, seed completeness, idempotency, and the read-only exposure method's correctness | Pass |

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-028** (this codebase's first data-seeding-migration pattern:
  `ON CONFLICT (slug) DO NOTHING ... RETURNING`-gated inserts sourced from a plain-data module with no ORM
  import, question/child-row inserts transitively gated on which parent rows were actually freshly returned, and
  an `upgrade()` DDL-existence-check guard making the function safely re-callable outside Alembic's normal
  one-time-per-revision bookkeeping). Append-only; no existing entry modified.
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 1's Status updated from "Resolved — v1 launch taxonomy locked;
  implementation not yet built" to reflect that the real domain has now shipped: the taxonomy is both decided
  *and* built, and `AI-001`/`AI-002` (and everything cascading from them through Sprint 12 per the Tracker's own
  dependency chain) are genuinely unblocked at the code level.
- **`docs/AI/04_DATABASE.md`** — Category Domain section updated to confirm all three tables shipped exactly per
  spec, no deviation, mirroring how DIR-001's closeout updated Section 13 for the geospatial indexes.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — CTG-001 marked done; Sprint 7 now genuinely started (though
  `AI-001` itself is not yet planned or started — only unblocked); Executive Summary, Current Backend
  Capabilities, Repository State, Current Limitations, Overall Progress, and Next Planned Story sections updated.
- **`docs/CHANGELOG.md`** — new entry under `[Unreleased]`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s Stories sheet still needs its CTG-001 row's Status updated from "Planned" to
  "Done"** — per standing process, the CTO handles this separately via a raw-XML-safe cell-patching procedure
  (a normal `openpyxl` load/save round-trip was previously found to silently drop this workbook's
  conditional-formatting extensions). Not performed by this closeout.
- **Native-speaker verification of the seeded Arabic text** (category names and all 47 question texts) remains
  genuinely open, tracked at the source-document level (`17_CATEGORY_TAXONOMY.md`'s own caveat) — not a new
  `13_OPEN_DECISIONS.md` item, since item 1's existing text already covers the taxonomy's provisional Arabic
  status.
- **Reconciling `provider.provider_category_labels` into `category.provider_categories`** remains a separate,
  deliberately deferred follow-up story — `provider_categories` was created empty by this story's migration and
  stays empty until that future story.

---

## Testing Performed

- `backend` implementation, with a new 17-test automated suite (`test_category_migration.py`,
  `test_category_service.py`) — see What Was Implemented above.
- `tester` agent: all 7 ACs independently verified with direct evidence against a real Postgres database (the
  actual migration run, upgrade-twice and upgrade/downgrade/upgrade idempotency proofs bypassing Alembic's own
  bookkeeping, direct service-method calls, and a diff-based non-interference check) — see Review Process above.
  One genuine finding (a tautological test assertion) fixed in commit `adeeb0b`.
- `architect` agent: returned **APPROVED WITH RECOMMENDATIONS (non-blocking)** — both recommendations (write
  ADR-028, confirm AC wording against the Tracker) acted on at this closeout.
- User (CTO) sign-off received after both the tester's and architect's final verdicts were presented, and after
  the CTO's own direct confirmation of the AC wording against the Tracker.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_09_1000-a804c46bf703_category_domain.py` (new — migration + idempotent seed)
- `backend/app/modules/category/models.py` (new — `Category`, `CategoryQuestionTemplate`, `ProviderCategory`)
- `backend/app/modules/category/seed_data.py` (new — `CATEGORY_SEED`, `QUESTION_SEED_BY_SLUG`, no ORM import)
- `backend/app/modules/category/repositories/category_repository.py`,
  `category_question_template_repository.py` (new)
- `backend/app/modules/category/services/category_service.py` (new — `CategoryService`)
- `backend/app/modules/category/dependencies.py` (new)
- `backend/tests/modules/category/test_category_migration.py`,
  `backend/tests/modules/category/test_category_service.py` (new — 17 tests)
- `backend/tests/conftest.py` — `category` schema/model registration extension

### Documentation
- `docs/AI/17_CATEGORY_TAXONOMY.md` (v1.0.0 → v1.1.0 — real Arabic question text added for all 47 questions)
- `docs/AI/09_DECISIONS.md` — ADR-028
- `docs/AI/13_OPEN_DECISIONS.md` — item 1 status update
- `docs/AI/04_DATABASE.md` — Category Domain section confirmed-shipped
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — CTG-001 marked done, Sprint 7 status
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 7 (Conversation / AI Intake) can now genuinely begin.** `AI-001` and `AI-002` are unblocked at the
  code level — a real, queryable `category.categories`/`category_question_templates` domain exists for them to
  build against. This closeout does not plan or start `AI-001`; that remains a separate future planning pass.
- **`docs/AI/Project_Tracker.xlsx`'s CTG-001 row** still needs its Status flipped to "Done" — handled separately
  by the CTO's own raw-XML procedure, not performed by this closeout.
- **Native-speaker review of the seeded Arabic text** (14 category names, 47 question texts) remains open,
  non-blocking, tracked at the `17_CATEGORY_TAXONOMY.md` source-document level.
- **Reconciling `provider_category_labels` into `provider_categories`** remains a separate, not-yet-scheduled
  future story — `provider_categories` is empty today by design.
