# Plan for Story CTG-001 — Build the Real Category Domain and Seed the v1 Launch Taxonomy

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Epic:** ML7-EP03 "Category Domain" | **Milestone:** ML7
| **Phase:** PH2 | **Priority:** Critical | **Depends On:** none (confirmed from the Tracker's `Depends On`
field, and consistent with the story's own framing — it depends on nothing already-built and unblocks `AI-001`).

---

## Story

As the engineering team resolving `13_OPEN_DECISIONS.md` item 1 at the code level, build the real
`category.categories` / `category.category_question_templates` / `category.provider_categories` schema and seed
it with the CTO-approved v1 launch taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md`) — 14 categories and their
AI follow-up question templates — so that `AI-001` (Sprint 7) has a real, queryable taxonomy to build the
Conversation/AI Intake domain against, instead of the free-text `provider_category_labels` interim stand-in
PRO-001/PRO-002/DIR-001 have been using.

**This story does not design or alter the taxonomy's content.** `17_CATEGORY_TAXONOMY.md` is CTO-locked; this
Plan is about *how* to build and seed what that document already specifies, not whether its content is right.

**Scope boundary:** does not reconcile `provider.provider_category_labels` (PRO-002's free-text interim table)
into the real `category.provider_categories` join table — `13_OPEN_DECISIONS.md` item 1 and
`17_CATEGORY_TAXONOMY.md`'s own "Migration Notes for Implementation" section both name that reconciliation as a
separate, deliberately deferred follow-up story. Does not touch `DIR-001`'s `search` module or its existing
free-text category matching in any way. Backend-only — no AC in this story asks for a mobile screen, and
`AI-001` (the eventual real mobile consumer) does not exist yet.

---

## Acceptance Criteria

**A note on sourcing, read first:** `docs/AI/Project_Tracker.xlsx` is a binary `.xlsx` file. This session's tool
set (`Read`/`Write`/`Edit`/`Grep`/`Glob` only — no shell/code-execution tool) cannot open or decompress it; `Read`
explicitly refuses binary files, and `Grep` returns no matches against its compressed internal XML (confirmed by
testing both directly). **This session could not independently verify the ACs below against the primary source**,
contrary to this project's established practice and this task's own explicit instruction to do so. The 7 items
below are reconstructed from the task brief's own description of the row's content ("7 ACs covering:
schema-per-spec, seeding both tables, idempotency, a read-only exposure method for AI-001 to consume later,
non-interference with `provider_category_labels`/DIR-001's search, and test coverage"), organized into a
plausible, internally-consistent 7-item list. **This must be confirmed against the literal Tracker text — by
whoever next has spreadsheet access — before or during `backend` implementation; treat the wording below as
reconstructed, not verbatim, until then.**

1. `category.categories`, `category.category_question_templates`, and `category.provider_categories` exist via
   migration, exactly matching `04_DATABASE.md`'s Category Domain section (column types, nullability,
   constraints — `uq_categories_slug` — and indexes).
2. All 14 categories from `17_CATEGORY_TAXONOMY.md` are seeded into `category.categories` with correct bilingual
   (EN/AR) names, slugs, and `sort_order`.
3. Each category's `category_question_templates` rows are seeded exactly per `17_CATEGORY_TAXONOMY.md`
   (`question_text`/`question_text_ar`, `question_type`, `options`, `is_required`, `sort_order`).
4. The seeding mechanism is idempotent: running it more than once (upgrade run twice, or
   upgrade → downgrade → upgrade) never produces duplicate categories or duplicate question rows.
5. A read-only service method (or endpoint, if warranted) exists so a future consumer (`AI-001`) can retrieve
   categories and their question templates, without requiring `AI-001` itself to exist yet.
6. This story does not modify, migrate, or reconcile `provider.provider_category_labels`, and does not alter
   `DIR-001`'s existing `search` module or its `GET /search/providers`/`GET /search/categories` behavior in any
   way.
7. Automated tests cover schema creation, seed completeness (14 categories, correct per-category question
   counts, correct bilingual content), idempotency (no duplicates on a second run), and the read-only exposure
   method's correctness.

---

## Verified Current State (read directly from code and docs, not assumed)

- **No `category` module, schema, or table exists anywhere in the codebase today** — confirmed by glob
  (`backend/app/modules/**/models.py`: `audit`, `identity`, `verification`, `notification`, `administration`,
  `customer`, `provider` only) and by the Alembic versions directory (8 migrations, most recent
  `2026_09_09_0900-a3f6e9c21d47_enable_geospatial_extensions_and_indexes.py` — no `category`-named migration).
  This is a genuinely new domain to build, matching `13_OPEN_DECISIONS.md` item 1's framing ("the real `category`
  schema domain... has not been built yet").
- **`02_ARCHITECTURE.md` names "Category" as its own Core Business Module**, a peer of Identity, Customer,
  Provider, and Conversation/AI Intake — not a sub-concept of either — with explicit responsibilities "Category
  taxonomy" and "Category Question Templates that drive the AI's follow-up questions." `03_DOMAIN_MODEL.md`
  separately lists Category as its own top-level domain with two entities (Category, Category Question Template)
  and the business rule "A Provider belongs to one or more Categories." `04_DATABASE.md` places all three tables
  in a dedicated `category` Postgres schema — a peer schema to `provider`/`verification`/`administration`, not a
  child of any of them.
- **`04_DATABASE.md`'s Category Domain section is fully specified, column-by-column** (read directly, not
  paraphrased):
  - `categories`: `parent_category_id` (UUID, nullable, self-FK), `name` (VARCHAR(100), not null), `name_ar`
    (VARCHAR(100), nullable — "nullable only until translation is populated; required before launch"), `slug`
    (VARCHAR(120), not null), `icon_url` (VARCHAR(500), nullable), `sort_order` (SMALLINT, not null, default 0).
    Constraint: `uq_categories_slug`.
  - `category_question_templates`: `category_id` (UUID, not null, FK → `categories.id`), `question_text`
    (VARCHAR(500), not null), `question_text_ar` (VARCHAR(500), nullable), `question_type` (VARCHAR(30), not
    null — "VARCHAR, not enum: expected to grow" — values `text`/`single_select`/`multi_select`/`number`/
    `boolean`), `options` (JSONB, nullable), `is_required` (BOOLEAN, not null, default `true`), `sort_order`
    (SMALLINT, not null, default 0). Index: `idx_category_question_templates_category_id`. **No unique
    constraint of any kind is specified for this table** — relevant to Decision 2's idempotency mechanism below.
  - `provider_categories` (join table): `provider_id`/`category_id` composite PK, `is_primary` (BOOLEAN, default
    `false`, service-layer-enforced uniqueness), `created_at` (TIMESTAMPTZ, not null). Index:
    `idx_provider_categories_category_id`.
- **`backend/app/database/mixins.py`'s `CommonColumnsMixin` docstring explicitly exempts "pure join/association
  tables"** from the full common-columns set ("they use a composite primary key and only `created_at`") — this
  directly settles that `categories`/`category_question_templates` (ordinary business tables) get the full
  mixin, while `provider_categories` (a join table, explicitly named in `04_DATABASE.md`'s own column list with
  only `created_at` beyond its composite PK) does not. `administration.admin_action_log`'s migration is the
  exact, directly-reusable template for how a full-`CommonColumnsMixin` table's migration is written in this
  codebase (`_common_columns()` helper, `sa.ForeignKeyConstraint` for `created_by`/`updated_by` → `identity.users.id`).
- **No migration in this codebase has ever inserted data rows** — confirmed by grepping all 8 existing migrations
  for `bulk_insert`/`INSERT INTO`/`seed`: every hit is schema/table/index/extension DDL only (e.g.
  `enable_geospatial_extensions_and_indexes`'s `CREATE EXTENSION IF NOT EXISTS`). Role/permission values
  (`ROLE_CUSTOMER`, etc.) are plain Python string constants in `app/core/constants.py`, never seeded database
  rows, so there is no existing "seed a reference table" precedent to reuse — this story is a genuinely new
  pattern for this codebase (Decision 2).
- **`17_CATEGORY_TAXONOMY.md`'s own "Migration Notes for Implementation" section explicitly instructs**: "This
  data should be seeded via a data migration (or a dedicated, idempotent seed step run as part of the same
  migration that creates these tables) — not left for manual `INSERT`s, so it ships identically across every
  environment." This directly settles AC1's "via migration" mechanism at the document-of-record level; this
  Plan's job is only the concrete idempotency mechanism (Decision 2).
- **The ordinary backend test suite never runs Alembic migrations at all.** `backend/tests/conftest.py`'s
  `db_engine` fixture builds every domain's schema by calling `Base.metadata.create_all()` directly against a
  real local Postgres test database (creating each domain's Postgres schema by hand first, e.g. `CREATE SCHEMA
  IF NOT EXISTS provider`), then imports each domain's `models.py` so its tables register on `Base.metadata`.
  `backend/tests/test_migrations.py` is the only place Alembic itself runs, and it does so against a **mocked**
  connection (`AsyncMock`), never a real database. This means: (a) `CategoryService`-level tests need their own,
  real seed-data insertion into the ordinary test DB — the migration's seed rows are never present there — and
  (b) genuinely verifying AC4's idempotency (real Postgres, real `ON CONFLICT` behavior) needs a dedicated test
  that executes the new migration's actual Python functions against a real connection, following the "real-DB
  migration verification, separate from the test suite's own `Base.metadata` approach" precedent `Plan_S05_VER-001.md`
  already named (ADR-013) but that this codebase has not yet actually built as a *live-executed* (non-mocked)
  test anywhere (Decision 5).
- **Cross-module service reads already return raw ORM entities, not Pydantic-wrapped schemas** — confirmed
  directly: `AdminVerificationService.provider_service.list_by_ids(...)` (`backend/app/modules/verification/services/admin_verification_service.py`)
  returns `list[Provider]` (the ORM model) straight from `ProviderService`, with no HTTP layer or response schema
  involved at that boundary. This is the established, reusable shape for Decision 3's `CategoryService` methods.
- **`administration` and `notification` are this codebase's existing "first slice of a real domain" precedent
  with no `api.py`** — both ship `models.py` + `repositories/` + `services/` + `dependencies.py` and nothing
  else; neither has ever had its own HTTP route. The difference from `category`: both had a real, same-story
  caller (`VER-002`'s admin-review flow) the day they shipped. `category`'s prospective caller (`AI-001`) does
  not exist yet — the closest genuine precedent for "a plain service method built ahead of its future
  cross-module consumer" is `ProviderService.list_by_ids`, itself added by `VER-002` specifically for
  `AdminVerificationService` to call — the only difference here is timing (Decision 3).
- **`13_OPEN_DECISIONS.md` item 1 is explicit that this story's scope stops at building the domain and seeding
  it** — reconciling `provider_category_labels` into `provider_categories` is "explicitly not part of this
  taxonomy decision or its implementing story."

---

## Architecture Decisions

### Decision 1 — New module: `backend/app/modules/category/`

**Chosen:** a new, top-level `backend/app/modules/category/` module — `models.py`, `repositories/`, `services/`,
`dependencies.py` — following exactly the "first slice of a real domain" shape `verification` (VER-001),
`administration` (VER-002), and `notification` (VER-002) each already established, and, per Decision 3,
deliberately mirroring `administration`/`notification`'s specific no-`api.py` shape rather than `search`'s
no-`models.py` shape.

**Justification:** `02_ARCHITECTURE.md` names "Category" as its own Core Business Module with its own explicit
responsibilities, distinct from Provider and from Conversation/AI Intake; `03_DOMAIN_MODEL.md` gives it its own
top-level domain section with two named entities; `04_DATABASE.md` gives it its own dedicated Postgres schema,
a peer to every other domain schema, not a sub-schema of `provider`. This is exactly the same reasoning
`Plan_S05_VER-001.md` Decision 5 used to justify a new `verification` module even though every table
verification cares about at read-time (`providers.verification_status`) lives elsewhere: a real,
architecturally-named domain gets its own module even when its first slice is thin and has no writer-facing
endpoint of its own.

**Alternatives considered and rejected:**
- **Add these tables/models to `backend/app/modules/provider/`** — rejected: `04_DATABASE.md` places them in a
  distinct `category` schema, not `provider`; `02_ARCHITECTURE.md` explicitly separates the two domains. Blurring
  this boundary would repeat exactly the mistake VER-001's own Decision 5 already rejected for Verification.
- **Add to the existing `search` module (DIR-001 already deals with category-like free-text matching)** —
  rejected: `search` has zero tables and zero `models.py` by deliberate design (`Plan_S06_DIR-001.md` Decision 4
  — "no new tables, no `models.py`. This story does not write... at all"). Category is genuinely persisted,
  owned reference data with its own lifecycle and its own schema — conflating it with `search`'s
  query-time-only module would misrepresent both domains and contradict `02_ARCHITECTURE.md`'s explicit module
  list.

### Decision 2 — Seed mechanism: a canonical Python seed-data module, plus an idempotent `INSERT ... ON CONFLICT (slug) DO NOTHING ... RETURNING` inside the same migration that creates the tables

**The problem, stated precisely:** AC1/AC2/AC3 require the seed data to exist via migration (per
`17_CATEGORY_TAXONOMY.md`'s own instruction, see Verified Current State); AC4 requires that mechanism to be
genuinely idempotent — proven by directly re-running it, not merely by trusting Alembic's own "don't reapply an
already-applied revision" bookkeeping (which the AC's own "upgrade run twice" wording explicitly asks to be
tested past, not relied on as the only guard). No existing migration in this codebase has ever inserted data
before, so this is a new pattern this Plan must design carefully, not copy from precedent.

**Chosen:**
- A new, plain-Python module, `backend/app/modules/category/seed_data.py` — `CATEGORY_SEED: list[dict]` (one
  dict per category: `slug`, `name`, `name_ar`, `sort_order`) and `QUESTION_SEED_BY_SLUG: dict[str, list[dict]]`
  (one list per category slug, each dict: `question_text`, `question_text_ar`, `question_type`, `options`,
  `is_required`, `sort_order`) — transcribed verbatim from `17_CATEGORY_TAXONOMY.md`. **No SQLAlchemy or ORM
  import** — plain data only, so it is safely importable both by the Alembic migration (which, matching every
  existing migration's own convention, never imports `app.modules.*.models`, only raw `sa.Column`/`op.create_table`
  Core constructs) and by test fixtures (Decision 5), avoiding transcribing the taxonomy's 14 categories and
  ~48 questions twice in two files (`08_CODING_STANDARDS.md`: never duplicate code/data).
- The new `category_domain` migration's `upgrade()`, after creating the schema and all three tables:
  1. Declares lightweight `sa.table("categories", sa.column("id"), sa.column("slug"), ...)`/
     `sa.table("category_question_templates", ...)` Core table objects (not the ORM model — matching this
     codebase's existing migration convention).
  2. Executes `postgresql.insert(categories_tbl).values(seed_data.CATEGORY_SEED).on_conflict_do_nothing(
     index_elements=["slug"]).returning(categories_tbl.c.id, categories_tbl.c.slug)` via `op.get_bind()`,
     capturing the `(id, slug)` pairs actually inserted **this run**. On a fresh database this returns all 14
     rows; on a re-run against an already-seeded database, `uq_categories_slug`'s conflict target means every
     row conflicts and the returned set is empty — genuinely, not by assertion.
  3. For each `(id, slug)` pair actually returned, builds and executes the matching
     `category_question_templates` insert batch for `seed_data.QUESTION_SEED_BY_SLUG[slug]`, using the
     freshly-returned `id` as `category_id`. **No `ON CONFLICT` clause is needed on this table** (`04_DATABASE.md`
     specifies no unique constraint on it) — a question batch is only ever inserted when its parent category was
     itself freshly inserted this run, so the parent's `ON CONFLICT DO NOTHING` transitively gates the whole
     batch; a re-run with zero freshly-inserted categories inserts zero question rows.
- `downgrade()` drops all three tables and the `category` schema — the standard pattern every other domain
  migration already uses. A downgrade → upgrade cycle reseeds cleanly from empty; an upgrade → upgrade cycle
  (AC4's literal "run twice" case) inserts 14 rows the first call and 0 the second, verified by row-count
  assertions (Decision 5), not merely argued.
- **Flagged for `architect`'s attention and a new ADR at story close:** this is this codebase's first
  data-seeding migration — every one of the 8 existing migrations is schema/DDL only. Recorded here explicitly,
  mirroring how `Plan_S06_DIR-001.md` flagged its own first-use-of-raw-`text()`-SQL precedent (ADR-026).

**Alternatives considered and rejected:**
- **A standalone seed script (`scripts/seed_categories.py`) run manually/via a deploy step, outside Alembic** —
  rejected: `17_CATEGORY_TAXONOMY.md`'s own Migration Notes explicitly reject this ("not left for manual
  `INSERT`s, so it ships identically across every environment"); a standalone script could be forgotten in any
  one environment, unlike a migration Alembic runs automatically as part of `alembic upgrade head`.
- **Application-level "seed on startup" logic** — rejected: `app/.agents/agents.md`'s Architecture Stability
  Rule explicitly protects "Database migration strategy" from unrequested change; introducing a second, parallel
  seeding mechanism outside Alembic would be exactly that kind of unrequested infrastructure addition.
- **Add a new unique constraint to `category_question_templates` (e.g. `(category_id, sort_order)`) so it can
  use its own symmetric `ON CONFLICT DO NOTHING`** — rejected: `04_DATABASE.md`'s spec for this table lists
  exactly one index and no unique constraint; adding one not in the authoritative spec is an unrequested schema
  deviation. The chosen "only insert a category's questions when its parent category was itself freshly
  inserted" gating achieves full idempotency without touching the spec at all.

### Decision 3 — Read-only exposure (AC5): a genuine, real `CategoryService` with two plain methods; no `api.py`/HTTP route in this story

**Chosen:** `backend/app/modules/category/services/category_service.py`,
`CategoryService(category_repository, category_question_template_repository)`:
- `list_active_categories() -> list[Category]` — all 14 categories, ordered by `sort_order` (the
  category-resolution read a future `AI-001` needs).
- `get_question_templates(category_id: uuid.UUID) -> list[CategoryQuestionTemplate]` — a category's questions,
  ordered by `sort_order` (the follow-up-question read a future `AI-001` needs); returns an empty list for an
  unknown `category_id` rather than raising — an honest "no questions" answer, not a fabricated error, matching
  the fact there is no HTTP layer here to translate an exception into a response for.

Wired via `dependencies.py`'s `get_category_service()`, the same DI-provider shape every other module already
uses — so a future `AI-001` module can add a one-directional `ai_intake → category` cross-module edge via
constructor injection, the same pattern ADR-014/ADR-016/`VER-001` Decision 9 already established three times,
with zero changes to `CategoryService` itself required when that story starts. Both methods return raw ORM
entities, matching this codebase's own established precedent for cross-module service-to-service reads
(`ProviderService.list_by_ids` returning raw `Provider` rows to `AdminVerificationService`, `VER-002`) — a
Pydantic response schema is what an HTTP layer needs, and there is no HTTP layer in this story.

**No `api.py` is added to the `category` module.** This is not a stub, and not analogous to ADR-018's
`StubDocumentOcrService` — the *implementation* here is fully real, backed by the full, CTO-approved seeded
taxonomy; the only thing not yet real is the *caller* (`AI-001` doesn't exist). Building an HTTP endpoint now
would force an arbitrary, product-unmotivated choice (what auth policy? what response shape? paginated, given
only 14 rows?) with no real caller or AC to validate it against, and no AC in this story requests one (mobile
scope is explicitly excluded from this story). The precedent for "a plain, unrouted, real service method built
ahead of its future cross-module consumer" is already established in this exact codebase
(`ProviderService.list_by_ids`) — the only difference here is that `CTG-001`'s consumer arrives in a later
story rather than the same one, which changes nothing about the shape of the exposure itself.

**Alternatives considered and rejected:**
- **Build a public `GET /categories`(`/{id}/questions`) endpoint now, mirroring DIR-001's `GET
  /search/categories`** — rejected: DIR-001's endpoint backed a real, immediately-shipping mobile picker (S-06's
  quick-start chips) in the *same* story. `CTG-001` has no such caller; building a route "just in case" is
  unrequested scope (`app/.agents/agents.md`: "Implement only the requested task"; `11_MVP_SCOPE.md`: "Do not
  introduce additional features unless explicitly requested").
- **Build the endpoint but gate it behind `require_role(ROLE_ADMIN)` as an internal tool** — rejected for the
  same "no real caller, no AC" reason; also invents an auth policy with nothing to justify the specific choice.
- **Leave `CategoryService` entirely unbuilt, deferring all read access to `AI-001`** — rejected: AC5 (as
  reconstructed) explicitly requires this exposure to exist now, and building it now means `AI-001`'s own future
  Plan can cite an already-real, already-tested method instead of re-deriving read access to a domain it
  doesn't own.

### Decision 4 — Bilingual Arabic content: seed the first-pass Arabic text now, explicitly flagged as provisional everywhere it appears

**Chosen:** `name_ar`/`question_text_ar` are populated with `17_CATEGORY_TAXONOMY.md`'s first-pass Arabic text
for all 14 categories and their question templates — not left `NULL`. `04_DATABASE.md`'s column note
("nullable only until translation is populated; required before launch") describes *populated* vs.
*not-yet-populated*, not *verified* vs. *unverified* — nothing in that note requires the populated text to
already have passed native-speaker review, only that it exist before launch. Seeding `NULL` instead would leave
any future bilingual UI showing blank Arabic for every category for the entire interval between this story and
whichever future story runs a native-speaker review — a strictly worse interim state, for no compliance or
correctness benefit, given the CTO has already supplied a first-pass translation in the very document this
story implements.

**The actual risk this decision must manage** — someone later mistaking first-pass text for a verified
translation — is handled the same way this codebase already handles every other "real but not fully finished"
capability (ADR-018's OCR stub is the closest precedent in spirit, though the situation here is inverted per
Decision 3): an explicit, hard-to-miss comment at the point of definition. `seed_data.py`'s module docstring,
the migration's own docstring, and this Plan all state plainly: *"Arabic text seeded here is a first-pass
translation per `17_CATEGORY_TAXONOMY.md`, not yet native-speaker-verified; do not treat as launch-final."*
`17_CATEGORY_TAXONOMY.md` already carries this exact caveat at the source-document level, so no new
`13_OPEN_DECISIONS.md` item is needed for it — item 1's existing text already covers the taxonomy's provisional
Arabic status.

**Alternative considered and rejected:** seed `NULL` for every `*_ar` column now, treating Arabic population as
fully separate follow-up work. Rejected: strictly worse for the actual product (blank Arabic in the interim,
for no benefit — `04_DATABASE.md` never conditions non-`NULL` on verification, only on population), and would
require a second migration later purely to backfill text this story already has in hand from the CTO-approved
source document.

### Decision 5 — Testing approach for idempotency and seed completeness

**Chosen, concretely:**
- `backend/tests/modules/category/test_category_migration.py` (new) — against a real scratch Postgres
  connection (this codebase's `db_engine`-fixture pattern, extended per the mechanical addition in the note
  below), exercises the new migration's actual `upgrade()`/`downgrade()` Python functions directly (via
  `alembic.runtime.migration.MigrationContext.configure(connection)` + `alembic.operations.Operations(context)`,
  the standard way to run a single migration's functions against a real `Connection` outside the full `alembic
  upgrade head` CLI flow — genuinely executed, unlike `test_migrations.py`'s existing fully-mocked coverage):
  - Runs `upgrade()` once; asserts exactly 14 rows in `category.categories`, and — for every slug in
    `seed_data.QUESTION_SEED_BY_SLUG` — exactly `len(seed_data.QUESTION_SEED_BY_SLUG[slug])` rows in
    `category.category_question_templates` for that category (counts read from `seed_data.py` itself, never
    re-typed as separate literals, so the test stays correct if the seed data is ever edited in place, per
    `17_CATEGORY_TAXONOMY.md`'s own "a data change, not a migration" design intent).
  - Runs `upgrade()` a **second time** against the same, already-seeded schema (AC4's literal "upgrade run
    twice" case) and re-asserts the identical row counts — proving the `ON CONFLICT DO NOTHING`/gated-question-
    insert logic is genuinely idempotent, not merely asserted to be.
  - Separately, on a fresh schema: `upgrade()` → `downgrade()` → `upgrade()` (AC4's other named case, and this
    codebase's existing ADR-013 scratch-DB migration-verification precedent) and re-asserts the same row counts
    after the second `upgrade()`.
- `backend/tests/modules/category/test_category_service.py` — seeds a test database (via `db_engine`/`db_session`,
  Decision 6 below) directly from `seed_data.py` (never via the migration — the ordinary test fixtures never run
  Alembic, per Verified Current State), then asserts: `list_active_categories()` returns exactly 14 categories in
  `sort_order` order with the correct slugs/names; `get_question_templates(category_id)` returns the correct,
  ordered question list (text, type, options, `is_required`) for at least three representative categories
  spanning every `question_type` actually used by the real seed data (`single_select`, `multi_select`, `text`,
  `boolean` — `number` is not used by any of the 14 categories' questions per `17_CATEGORY_TAXONOMY.md`, noted
  here as a fact about the real data, not a test gap, since no AC requires exercising a type the seed data never
  produces) and both `is_required=True`/`False` cases; a non-existent `category_id` returns an empty list, not
  an error.

### Decision 6 (mechanical, no genuine alternative) — `conftest.py` extension

`backend/tests/conftest.py`'s `db_engine`/`db_session` fixtures gain the `category` schema/model registration,
exactly like every prior domain: `CREATE SCHEMA IF NOT EXISTS category` (create + drop, mirroring every existing
schema line), `import app.modules.category.models` (registers `Category`/`CategoryQuestionTemplate`/
`ProviderCategory` on `Base.metadata`), and the three new model classes added to the teardown truncation list.
No alternative considered — this is the same mechanical addition every prior domain module has already made.

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration, `category_domain` (down-revision = current head, `a3f6e9c21d47` — confirm via
   `alembic heads` at implementation time). Creates the `category` Postgres schema and:
   - `category.categories` — full `CommonColumnsMixin`-equivalent columns (mirroring
     `administration_domain`'s `_common_columns()` helper) + `parent_category_id` (self-FK, nullable),
     `name` (VARCHAR(100), not null), `name_ar` (VARCHAR(100), nullable), `slug` (VARCHAR(120), not null,
     `uq_categories_slug`), `icon_url` (VARCHAR(500), nullable), `sort_order` (SMALLINT, not null, default 0).
   - `category.category_question_templates` — full `CommonColumnsMixin`-equivalent columns + `category_id`
     (FK → `categories.id`, not null), `question_text` (VARCHAR(500), not null), `question_text_ar`
     (VARCHAR(500), nullable), `question_type` (VARCHAR(30), not null), `options` (JSONB, nullable),
     `is_required` (BOOLEAN, not null, default `true`), `sort_order` (SMALLINT, not null, default 0). Index:
     `idx_category_question_templates_category_id`.
   - `category.provider_categories` — join table only: composite PK (`provider_id`, `category_id`), FK
     `provider_id` → `provider.providers.id`, FK `category_id` → `category.categories.id`, `is_primary`
     (BOOLEAN, default `false`), `created_at` (TIMESTAMPTZ, not null). Index:
     `idx_provider_categories_category_id`. **No rows are ever inserted into this table by this story** — it is
     created empty; reconciling `provider_category_labels` into it is out of scope (Explicitly Out of Scope).
   - Decision 2's seed-insert logic for `categories`/`category_question_templates`, sourced from the new
     `seed_data.py` (item 5 below).
   - `downgrade()` drops all three tables and the `category` schema.
2. Verify upgrade → upgrade and upgrade → downgrade → upgrade against a disposable scratch database
   (Decision 5/ADR-013's precedent), asserting row counts both times.

### New module: `backend/app/modules/category/`
3. `models.py` — `Category(CommonColumnsMixin, Base)`, `CategoryQuestionTemplate(CommonColumnsMixin, Base)`,
   `ProviderCategory(Base)` (join table, no mixin, composite PK — mirrors `provider_category_labels`'
   already-established "join/association shape" precedent, adapted for a composite PK per `04_DATABASE.md`'s
   explicit spec here).
4. `repositories/category_repository.py` — `CategoryRepository(BaseRepository[Category])`:
   `list_active(order_by sort_order)`.
5. `repositories/category_question_template_repository.py` —
   `CategoryQuestionTemplateRepository(BaseRepository[CategoryQuestionTemplate])`: `list_for_category(category_id)`
   (ordered by `sort_order`).
6. `seed_data.py` — `CATEGORY_SEED`, `QUESTION_SEED_BY_SLUG` (Decision 2), transcribed verbatim from
   `17_CATEGORY_TAXONOMY.md`, with the Arabic-first-pass caveat (Decision 4) in its module docstring. No
   SQLAlchemy/ORM import.
7. `services/category_service.py` — `CategoryService` (Decision 3): `list_active_categories()`,
   `get_question_templates(category_id)`.
8. `dependencies.py` — `get_category_repository`, `get_category_question_template_repository`,
   `get_category_service` — standard DI-provider chain, no HTTP route consumes it in this story (Decision 3).
9. **No `api.py`, no `schemas.py`** in this module for this story (Decision 3).
10. `repositories/provider_category_repository.py` — **not built in this story.** The `provider_categories`
    table exists in the database only; no repository/service/write path touches it until the future
    reconciliation story (Explicitly Out of Scope).

### App wiring
11. `backend/app/database/base.py`/model-registration path — no change needed beyond the new module's own
    `models.py` existing; no `api.py` means no `backend/app/api/v1/api.py` router registration for this story.
12. `backend/tests/conftest.py` — `category` schema/model registration (Decision 6).

### Tests
13. `backend/tests/modules/category/test_category_migration.py` — Decision 5's live-executed
    upgrade/upgrade-twice and upgrade/downgrade/upgrade idempotency tests, plus a column-level assertion that
    `category.categories`/`category.category_question_templates`/`category.provider_categories` match
    `04_DATABASE.md`'s spec (types, nullability, `uq_categories_slug`, indexes) — AC1.
14. `backend/tests/modules/category/test_category_service.py` — Decision 5's seed-completeness and
    read-method-correctness tests — AC2, AC3, AC5, AC7.
15. `backend/tests/modules/category/__init__.py` (new test package, mirrors every other module's test layout).

---

## Explicitly Out of Scope (do not implement in this story)

- Reconciling `provider.provider_category_labels`'s free-text values into real `category.provider_categories`
  rows — explicitly deferred per `13_OPEN_DECISIONS.md` item 1 and `17_CATEGORY_TAXONOMY.md`'s own "Migration
  Notes for Implementation" section. `provider_categories` is created empty by this story's migration and stays
  empty until that future story.
- Any change to `DIR-001`'s `search` module, its free-text category-matching logic (`ProviderCategoryLabelRepository`,
  `GET /search/categories`), or its response shapes — AC6. This story adds a parallel, unrelated real-taxonomy
  domain; it does not migrate `search` to use it.
- Any HTTP endpoint/route for reading categories or question templates — Decision 3; deferred to whichever
  future story (most plausibly `AI-001` itself) actually needs one.
- The Conversation/AI Intake domain itself (`AI-001`/`AI-002`, Sprint 7's other stories) — this story only
  unblocks them by making a real taxonomy exist and be readable.
- Native-speaker verification or correction of the seeded Arabic text — Decision 4; `17_CATEGORY_TAXONOMY.md`'s
  own caveat already tracks this as future work, not blocking.
- Icon assets / populating `icon_url` — deliberately `NULL` for every row per `17_CATEGORY_TAXONOMY.md`.
- Sub-categories or any non-flat taxonomy shape — `parent_category_id` is `NULL` for all 14 rows, per v1 scope.
- Any mobile change of any kind — no AC in this story requires a screen.
- Any code path that writes to `category.provider_categories` — schema only, no repository/service, this story.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start; `docs/implementation/plans/Checkpoint_S02_AUTH-002.md` is
the only Checkpoint file in the repository, unrelated to this story).

**Nothing in this Plan is blocked pending user product/policy confirmation before backend work starts.** Unlike
`Plan_S06_DIR-001.md`'s Decision 3 (a genuine product-policy ambiguity — whether browsing requires
authentication — with real customer-facing consequences), every open question this story surfaced (module
placement, seed mechanism, exposure shape, Arabic-seeding timing) is an implementation-shape decision within
`tech-lead` engineering authority, explicitly scoped that way by this task's own framing ("the taxonomy content
itself is not up for reconsideration, only implementation-shape decisions are open"). **The one genuine
limitation to flag explicitly: this session could not open `docs/AI/Project_Tracker.xlsx` to verify the 7 ACs
above verbatim** (see the Acceptance Criteria section's note) — recommend confirming the literal AC wording
against the spreadsheet before treating this Plan's AC list as final, ideally before `tester` signs off against
it.

1. **backend** — Migration (schema + 3 tables + Decision 2's idempotent seed), the new `category` module
   (models/repositories/services/dependencies/`seed_data.py`), `conftest.py` extension, all tests (items 1–15).
   ACs to satisfy: 1, 2, 3, 4, 5, 6, 7 (all of them — this is a backend-only story). **Read Decision 2 in full
   before starting** — the `ON CONFLICT DO NOTHING ... RETURNING`-gated question-insert logic is the part of
   this story most likely to be gotten subtly wrong (e.g. inserting a category's questions unconditionally
   instead of only for freshly-returned category ids, which would silently duplicate question rows on a
   second run while categories themselves stayed correctly deduplicated).
2. **tester** — Verify all 7 ACs individually. Particular attention to: AC1 (read the actual migration's
   `op.create_table` calls against `04_DATABASE.md`'s column list directly, not just that *some* columns exist);
   AC2/AC3 (spot-check bilingual content and question sets for at least 3–4 categories against
   `17_CATEGORY_TAXONOMY.md` directly, not only aggregate counts); AC4 (independently re-run the
   upgrade-twice and upgrade/downgrade/upgrade tests and confirm zero duplicate rows genuinely, not merely that
   the test asserts it); AC5 (confirm `CategoryService`'s two methods are real, callable, and correct — not a
   stub); AC6 (grep-level confirmation that no file this story touches lives under
   `backend/app/modules/search/` or `backend/app/modules/provider/` in a way that changes existing behavior,
   and that `provider_category_labels`'s table/rows are byte-for-byte unaffected); AC7 (confirm the test suite
   genuinely executes against a real Postgres connection for the idempotency tests, not a mock, per Decision 5).
3. **architect** — Review Decision 1 (new `category` module) against `02_ARCHITECTURE.md`'s explicit module
   list; Decision 2 (the codebase's first data-seeding migration, and its `ON CONFLICT`/`RETURNING`-based
   idempotency mechanism) for genuine correctness and for whether it warrants its own ADR; Decision 3 (real
   service method with no route, timed ahead of its consumer) against the `ProviderService.list_by_ids`
   precedent and against `08_CODING_STANDARDS.md`'s "no unnecessary abstractions" principle in the other
   direction (confirm this isn't *under*-building what AC5 actually needs); Decision 4 (seeding provisional
   Arabic text) against `04_DATABASE.md`'s column-nullability note and `06_SECURITY.md`/data-honesty principles
   generally; confirm AC6's non-interference boundary is genuinely unbroken by diffing `search`/`provider`
   module files against their pre-story state.
4. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/the tracker, per standing process. If approved: record Decision 2
   (idempotent data-seeding-migration pattern, this codebase's first) as a new ADR (next available: **ADR-028**
   — tech-lead confirms exact numbering at story close); update `04_DATABASE.md`'s Category Domain section to
   note the tables are now shipped (not just specified); update `13_OPEN_DECISIONS.md` item 1's status/Blocks
   text to reflect that `CTG-001` has shipped and the item can now close in full; update
   `PROJECT_IMPLEMENTATION_STATE.md` Section 17.

---

## Verification Plan (mapped to the 7 reconstructed ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade against a scratch database; `\d category.categories` / `\d category.category_question_templates` / `\d category.provider_categories` each match `04_DATABASE.md`'s column list, types, nullability, `uq_categories_slug`, and both named indexes exactly. |
| 2 | `test_category_service.py` asserts `list_active_categories()` returns exactly 14 rows, correct `slug`/`name`/`name_ar`/`sort_order` for every category, cross-checked directly against `17_CATEGORY_TAXONOMY.md`'s table (not only against `seed_data.py`, to catch a transcription error in `seed_data.py` itself). |
| 3 | `test_category_service.py` asserts `get_question_templates(category_id)` returns the correct ordered question set (text, type, options, `is_required`) for every category, cross-checked against `17_CATEGORY_TAXONOMY.md`'s per-category tables directly for at least the categories spanning every real `question_type` in use. |
| 4 | `test_category_migration.py`'s upgrade-twice test and upgrade→downgrade→upgrade test (Decision 5) both assert identical row counts (14 categories, correct per-category question counts) after every `upgrade()` call, with no duplicate rows at any point. |
| 5 | `test_category_service.py` calls both `CategoryService` methods directly and asserts correct, real (non-empty, non-stubbed) results; `architect` confirms the methods are genuinely wired for a future cross-module consumer (DI provider exists, no missing plumbing). |
| 6 | `architect`/`tester` diff `backend/app/modules/search/` and `backend/app/modules/provider/` against this story's changes and confirm zero modifications; a direct query against `provider.provider_category_labels` before and after this story's migration confirms its schema and any existing rows are untouched. |
| 7 | All of items 13–14 above exist, pass, and are independently re-run by `tester` against a real (not mocked) database connection for the idempotency-specific assertions. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md` (Category Core Business Module; module communication rules)
- `docs/AI/03_DOMAIN_MODEL.md` (Category domain — entities, business rules)
- `docs/AI/04_DATABASE.md` (Category Domain section — `categories`, `category_question_templates`,
  `provider_categories`; Section 14 — Schema Flexibility Against Open Decisions, item 1)
- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy, resolved at the content level; this story is what
  fully closes it)
- `docs/AI/17_CATEGORY_TAXONOMY.md` (the authoritative, CTO-locked v1 taxonomy content this story seeds verbatim)
- `docs/AI/08_CODING_STANDARDS.md` (no duplicate code/data — the basis for Decision 2's shared `seed_data.py`)
- `docs/AI/09_DECISIONS.md` (ADR-013 — scratch-DB migration verification precedent; ADR-014/016 — cross-module
  service-injection shape; ADR-018 — the honest-interim-capability precedent Decision 3 distinguishes itself
  from; ADR-026 — this codebase's first raw-SQL precedent, the closest prior example of flagging a genuinely new
  SQL pattern for `architect`'s attention, as Decision 2 does here)
- `docs/implementation/plans/Plan_S06_DIR-001.md` (module-placement reasoning precedent; `ProviderCategoryLabelRepository`/
  `provider_category_labels` interim mechanism this story does not touch)
- `docs/implementation/plans/Plan_S05_VER-001.md` (`administration`/`notification`-style "first slice of a real
  domain" precedent; `ProviderService.list_by_ids` cross-module read-only exposure precedent)
- `docs/implementation/plans/Plan_S05_VER-002.md` (`administration`/`notification` module shape origin)
