# Implementation Prompt — Story MAT-001

**Sprint:** 08 (Matching / Contact) | **Story:** MAT-001 — See Ranked Providers for My Request | **Plan:**
`docs/implementation/plans/Plan_S08_MAT-001.md` (read in full before starting — this prompt is a pointer to it,
not a replacement for it)

---

## Task

Implement Story MAT-001 exactly per `docs/implementation/plans/Plan_S08_MAT-001.md`. Read `.agents/agents.md` and
the `docs/AI/` documents that Plan's "Related Documents" section names before writing any code — in particular
`docs/AI/04_DATABASE.md`'s `providers.average_rating`/`review_count` columns and Review Domain section, and
`docs/AI/09_DECISIONS.md` ADR-025/026/027 (DIR-001's original query design) and ADR-037–041 (AI-002's `search`
schema and its Decision-5 "no ranking algorithm yet" reasoning — this story is the one that resolves it).

## Story Summary

Upgrade the existing, shared provider-matching query (`ProviderSearchRepository.search_nearby`, built by DIR-001
and reused unchanged by AI-002) from nearest-first-only ordering to a real, deterministic merit-ranking formula
combining proximity, average rating, and review count — never distance alone. This is a backend-only,
no-new-migration story: every table this story needs (`search_requests`, `provider_matches`, `search_event_log`,
`providers.average_rating`/`review_count`) already exists, shipped by AI-002/PRO-001. AC5 (conversation output
flowing into a results screen with no manual re-search step) is already fully satisfied by AI-002's shipped
mobile code — confirm this via regression testing, do not re-implement it.

## Acceptance Criteria

See the Plan's "Acceptance Criteria" section — verbatim from `Project_Tracker.xlsx`, relayed by the orchestrator
this session. AC1, AC2, AC5, AC6, AC7 are already satisfied by AI-002's shipped code (see the Plan's "Verified
Current State"); this story's genuinely new work is AC3, AC4, and AC8.

## Key Decisions to Follow (do not re-derive — the Plan already resolved these)

1. **In-place query upgrade, not a second ranking implementation (Decision 1):** modify
   `ProviderSearchRepository._SEARCH_NEARBY_SQL`'s `SELECT`/`ORDER BY` in place — `_WHERE_CLAUSE` must stay
   byte-for-byte unchanged (AC2). This affects **both** DIR-001's own `GET /search/providers` and the
   AI-conversation path (`SearchRequestService`) — that is intentional, directly evidenced by DIR-001's own Plan
   pre-announcing this exact upgrade as MAT-001's job. Do not build a separate `search_nearby_ranked` method.
2. **The exact composite formula and its five new `Settings` values** are specified in Decision 1 — a bounded
   `[0,1]` weighted combination of proximity, `COALESCE(average_rating, neutral_default)/5`, and a capped,
   normalized `review_count`. Do not invent a different formula shape without checking back — the bounded
   `[0,1]` design is load-bearing for fitting `provider_matches.match_score NUMERIC(5,4)` and for AC8's
   testability.
3. **Rating source is `providers.average_rating`/`review_count`, never `provider_rating_summaries` (Decision 2).**
   Do not create a `review` schema, a `reviews` table, or a `provider_rating_summaries` table in this story —
   that domain is structurally impossible to build meaningfully before CON-001/an Outcome Tag mechanism exist,
   and is `REV-001`'s job. If you find yourself about to create a `review` module, stop and flag it.
4. **`match_score` becomes real for the automated path, stays `NULL` for the manual path (Decision 3).**
   `ProviderMatchRepository.bulk_create` takes `list[tuple[uuid.UUID, float | None]]` — an admin's manual
   ordering never gets a fabricated score.
5. **No new migration.** If you find yourself reaching for `alembic revision`, stop — every table/column this
   story needs already exists; this is a service/repository/config change only.

## Delegation Order

1. **backend** — the entire Backend Proposed Changes list (items 1–12) and Architecture Decisions 1–3. Build
   order: `Settings` fields → `ProviderSearchRepository`'s query change with its own direct tests written
   alongside it (highest-risk change, do this first and in isolation) → `ProviderService`/`SearchService` thin
   pass-through (re-run DIR-001's existing tests immediately after this step — some fixture-expected orders may
   need updating, per Decision 1's Consequences; flag any such change plainly) → `SearchRequestService`/
   `ProviderMatchRepository` last. Full existing suite + `ruff` before reporting done, not just new tests.
2. **frontend** — not needed for this story (confirmed in Verified Current State — AC5 is already fully wired by
   AI-002, no new field is introduced for mobile to render). Only the one-line stale code comment in
   `mobile/lib/features/search/data/search_repository.dart` needs correcting — `backend` can make this trivial
   doc-only edit directly, no frontend delegation required.
3. **tester** — verify all 8 ACs per the Plan's Verification Plan table. Particular attention to AC3/AC8
   (construct real fixture providers with deliberately varied rating/distance combinations and confirm the
   actual returned order, not just that a score column is populated) and AC4 (a genuine exact-tie fixture).
   Re-verify AC1/AC2/AC5/AC6/AC7 as regressions against already-shipped behavior.
4. **architect** — review per the Plan's Delegation section step 4: the SQL score expression's bounds and
   parameterization, that `_WHERE_CLAUSE` truly did not change, Decision 2's anti-fabrication posture, and
   confirm no new cross-module edge was introduced.

Pause and present to the user once `tester`/`architect` both report clean — do not write the Walkthrough, touch
`docs/CHANGELOG.md`/tracker, or mark the story complete without explicit sign-off.

## Out of Scope

See the Plan's "Explicitly Out of Scope" section — notably any part of the real Review domain, CON-001's
contact/reveal step, exposing `match_score` to mobile, a customer-facing sort control, and the
`provider_category_labels` reconciliation gap.

## Before You Start — Open Questions Worth a Quick CTO Check

The Plan's "Open Questions" section flags three items: (1) the rating-source substitution (Decision 2), (2)
changing DIR-001's own already-shipped endpoint's result order as part of this story (Decision 1), and (3) the
specific default ranking weights/neutral-rating value. None of these block starting backend work — all three are
documented, reasoned interim designs with direct supporting evidence — but confirm no CTO correction has landed
before finalizing the Walkthrough.
