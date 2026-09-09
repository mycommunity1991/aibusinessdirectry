# Implementation Prompt — Story CTG-001

**Sprint:** 07 (Category Domain) | **Story:** CTG-001 — Build the Real Category Domain and Seed the v1 Launch
Taxonomy | **Plan:** `docs/implementation/plans/Plan_S07_CTG-001.md` (read in full before starting — this prompt
is a pointer to it, not a replacement for it)

---

## Task

Implement Story CTG-001 exactly per `docs/implementation/plans/Plan_S07_CTG-001.md`. Read `app/.agents/agents.md`
and the `docs/AI/` documents that Plan's "Related Documents" section names before writing any code — in
particular `docs/AI/17_CATEGORY_TAXONOMY.md` (the CTO-locked taxonomy content this story seeds verbatim) and
`docs/AI/04_DATABASE.md`'s Category Domain section (the exact schema spec).

## Story Summary

Build the real `category.categories` / `category.category_question_templates` / `category.provider_categories`
schema and seed it with the 14-category v1 launch taxonomy (bilingual names, per-category AI follow-up
questions) so `AI-001` has a real taxonomy to build against, instead of PRO-002's free-text
`provider_category_labels` interim stand-in. Backend-only, no mobile scope. Does not reconcile
`provider_category_labels` into the real domain — that is a separate, deliberately deferred future story.

## Acceptance Criteria

See the Plan's "Acceptance Criteria" section — **read its sourcing note first**: this session could not open
`docs/AI/Project_Tracker.xlsx` directly (binary file, no code-execution tool available), so the 7 ACs there are
reconstructed from the task brief's own description, not independently verified verbatim against the
spreadsheet. Confirm the literal wording before/while implementing if spreadsheet access is available.

## Key Decisions to Follow (do not re-derive — the Plan already resolved these)

1. New module: `backend/app/modules/category/` (models/repositories/services/dependencies) — mirrors
   `administration`/`notification`'s "first slice of a real domain, no `api.py`" shape, not `search`'s
   "no `models.py`" shape.
2. Seed mechanism: a canonical `seed_data.py` (plain Python, no ORM import) feeding an idempotent
   `INSERT ... ON CONFLICT (slug) DO NOTHING ... RETURNING` inside the same migration that creates the tables —
   only insert a category's `category_question_templates` rows for categories actually returned (i.e. freshly
   inserted) this run. This codebase's first data-seeding migration — flagged for `architect` and a new ADR.
3. Read-only exposure (AC5): a real `CategoryService` with `list_active_categories()` and
   `get_question_templates(category_id)`, wired via `dependencies.py` for a future `AI-001` cross-module edge.
   **No `api.py`, no HTTP route** — no real caller exists yet and no AC/mobile screen asks for one.
4. Arabic content: seed `17_CATEGORY_TAXONOMY.md`'s first-pass Arabic text now (not `NULL`), flagged in
   `seed_data.py`'s docstring and the migration's docstring as provisional, not yet native-speaker-verified.
5. Idempotency tests must genuinely execute the migration's `upgrade()`/`downgrade()` against a real Postgres
   connection (not mocked) — both an upgrade-twice cycle and an upgrade/downgrade/upgrade cycle, asserting row
   counts computed from `seed_data.py` itself.
6. AC6 (non-interference): zero changes to `backend/app/modules/search/` or `backend/app/modules/provider/`,
   and zero writes to `category.provider_categories` in this story.

## Delegation Order

1. **backend** — the entire Plan (this is a backend-only story): migration, new `category` module,
   `conftest.py` extension, all tests (Backend — Proposed Changes items 1–15, Architecture Decisions 1–6).
2. **tester** — verify all 7 ACs per the Plan's Verification Plan table, with particular attention to AC4
   (idempotency, real DB) and AC6 (non-interference, verified by diff).
3. **architect** — review per the Plan's Delegation section step 3 (module placement, the new
   data-seeding-migration pattern, the real-service/no-route exposure shape, provisional-Arabic seeding, and the
   AC6 non-interference boundary).

Pause and present to the user once `tester`/`architect` both report clean — do not write the Walkthrough, touch
`docs/CHANGELOG.md`/tracker, or mark the story complete without explicit sign-off.

## Out of Scope

See the Plan's "Explicitly Out of Scope" section — notably reconciling `provider_category_labels` into
`category.provider_categories`, any change to `DIR-001`'s `search` module, any HTTP endpoint for reading
categories, the Conversation/AI Intake domain itself, native-speaker Arabic review, icon assets, and
sub-categories.
