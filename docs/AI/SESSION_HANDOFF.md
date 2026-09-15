# Session Handoff — Read This First, Skip the Tracker

**Purpose:** A new session should be able to resume story-by-story development directly from
this file — without opening `Project_Tracker.xlsx` or re-reading `PROJECT_IMPLEMENTATION_STATE.md`
in full — to save tokens. This file is refreshed at the end of every story closeout. If it looks
stale (doesn't match the latest git log / `09_DECISIONS.md` ADR numbers), trust the repo over this
file and update this file once caught up.

**Last updated:** 15 September 2026, after Story ADM-001 closeout (documentation closeout complete; tracker sync
still pending — a separate process performed by the orchestrator, not part of this closeout).
**Repo:** `mycommunity1991/aibusinessdirectry` | **Branch:** `claude/provider-storefront-pro-001-qnicuj`
**Last commit at time of writing:** `c4411c9` (`ADM-001`'s full implementation, committed and pushed as a single
commit). Prior: `6248676` (chore: tracker sync for LEAD-002; docs closeout `146ff4f`; LEAD-002's implementation
commits — `30c029c` backend, `e7933a4` frontend, `2543edd` tester's regression test, `e726bb5` anchoring-bug fix,
`1802c5a` UTC-pin fix).

---

## 1. Where things stand

- **Sprints 1–7 are fully complete.** Milestones ML1 through **ML7 are all Done.**
- **Sprint 8 / Milestone ML8 is now fully complete — both stories Done: `MAT-001` and `CON-001`.**
  `MAT-001` shipped and was signed off 11 September 2026 — see
  `docs/implementation/walkthroughs/Walkthrough_S08_MAT-001.md` (`architect`: APPROVED, zero findings).
  `CON-001` ("contact a matched provider directly") has since shipped and was signed off 12 September 2026, on
  top of `MAT-001` — see `docs/implementation/walkthroughs/Walkthrough_S08_CON-001.md`. It built the new
  `contact` domain module (`contact.contact_views`), the self-dealing guard (ADR-044), a new customer-facing
  `GET /providers/{id}` public profile endpoint (ADR-045), a client-computed trust-badge precedence pattern
  (ADR-046), and the real mobile Provider Profile screen (S-09) plus Contact Reveal sheet (`url_launcher`,
  CTO-approved). `architect`'s one real finding — `ContactService` wired to a raw `ProviderRepository` instead
  of `ProviderService` — was fixed (commit `bed63e8`) and re-confirmed clean (ADR-047, the concrete precedent
  for the cross-module services-only convention). Final verdicts: `tester` all 8 ACs pass (one genuine
  test-coverage gap closed — AC6's Arabic-locale rendering, confirmed already-working, not a bug); `architect`
  PASS, fully APPROVED. Independently re-confirmed: 702/702 backend tests, 195/195 mobile tests passing.
- **Dashboard numbers (as of commit `6248676`, tracker sync for LEAD-002 confirmed applied and verified):**
  Overall Progress **64.6%** | Completed Milestones **10/24** | Completed Epics **17/23** | Completed Stories
  **39/47** | Current Phase **PH2** (progress **0.84**) | Milestone **ML9** — ✅ **Completed** (2/2 stories) |
  Milestone **ML10** — ✅ **Completed** (2/2 stories) | Epic **ML10-EP01** — ✅ **Completed** | Sprint **SP10** —
  ✅ **Completed** (2/2 stories). These numbers are current and verified (each of the 16 changed cells checked
  individually via `openpyxl` before and after, plus a structural cell-by-cell diff against the pre-sync file
  confirming no other cell changed — including a correction to the Dashboard's separate "Chart Data — Story
  Status" mini-table, which had independently drifted stale across several prior stories since it's a hardcoded
  snapshot, not a live formula) — no further tracker action is needed for `LEAD-001`/`LEAD-002`.
- **Sprint 9 / Milestone ML9 ("Outcome & Reviews") is now fully complete — 2 of 2 stories done: `REV-001`,
  `REV-002`.** `REV-001` shipped and was signed off 13 September 2026 — see
  `docs/implementation/walkthroughs/Walkthrough_S09_REV-001.md` (`architect`: APPROVED, one minor non-blocking
  documentation finding, fixed at closeout; `tester`: all 6 ACs pass, no bugs found). It extended the existing
  `contact` module in place with `outcome_tags` (ADR-048), an ownership check reusing `ensure_owner_or_not_found`
  for a 404 plus an atomic `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` uniqueness guard — independently
  proven correct under a genuine two-independent-session concurrency test (ADR-049) — and a flagged, additive
  notification touch-point on `CON-001`'s shipped `ContactService`, plus the mobile Outcome Tag Prompt sheet
  chained after Contact Reveal (ADR-050).
  `REV-002` ("leave a verified review after a successful hire") has since shipped and was signed off
  14 September 2026, on top of `REV-001` — see `docs/implementation/walkthroughs/Walkthrough_S09_REV-002.md`
  (`architect`: clean verdict, zero findings, no fix-and-recheck round needed; `tester`: all 7 ACs pass, no
  functional bugs found). It builds a new, standalone `review` domain module (its own Postgres schema, distinct
  from `contact` — ADR-051, since `REV-001`'s `outcome_tags`-into-`contact` folding was a narrower, same-schema
  exception, not a general rule), a race-safe rating-summary recalculation (`SELECT ... FOR UPDATE`-locked full
  recompute, never an incremental running average, to avoid `NUMERIC(3,2)` rounding drift — ADR-052), and a new
  409/404 rejection family (`ReviewAnchorNotVerifiedError`/`ReviewAlreadyExistsError`/reused
  `ContactViewNotFoundError` — ADR-053). `13_OPEN_DECISIONS.md` item 14 is now **Resolved**: both
  `providers.average_rating`/`review_count` and `review.provider_rating_summaries` are needed, written from the
  same computed values in the same transaction. On mobile, a new Write-a-Review screen (S-10) is reachable only
  after a "Yes" Outcome Tag Prompt submission. Final counts: 752/752 backend tests, 233/233 mobile tests.
  **`REV-001` and `MAT-001` remain the only two stories in this project's history to ship with zero real bugs
  found during review; `REV-002` is the first story to also return a fully clean `architect` verdict on the
  first pass alongside a bug-free `tester` pass.**
- **Sprint 10 ("Provider Leads & Analytics," Milestone ML10, Epic ML10-EP01) has since started and is now
  fully complete — 2 of 2 stories done: `LEAD-001`, `LEAD-002`.** Its first story, `LEAD-001` ("see and manage
  my provider leads"), shipped and was signed off on top of `REV-001`/`CON-001`** — see
  `docs/implementation/walkthroughs/Walkthrough_S10_LEAD-001.md` (`architect`: one documentation-only finding,
  an `ADR-047` docstring-naming gap, fixed at commit `8e987c3` and re-confirmed clean; `tester`: all 5 ACs pass,
  no bugs and no gaps found). It extends the existing `contact` module in place with a new, read-only
  `LeadService`/`GET /providers/me/leads` — zero new schema, zero new migration —
  generalizing `ADR-051`'s module/schema placement rule from the opposite direction: a capability with no new
  schema of its own belongs inside whichever existing module already owns the primary data being surfaced, even
  when it needs new cross-module raw-Repository edges into schemas it had no prior relationship with
  (`contact → search.SearchRequestRepository`, `contact → category.CategoryRepository` — ADR-054). Category
  context resolves via a two-hop join with **two independent, honest-null dead-ends** (no `search_request_id` at
  all, or a `search_request_id` whose own `category_id` is `NULL`), both collapsing to one honest fallback
  rather than a fabricated substitute — extending the anti-fabrication principle to a chained-nullable-FK case
  with more than one distinct absence reason (ADR-055). `LeadResponse` carries zero customer-identifying fields;
  `outcome_status` is a server-computed three-value enum. On mobile, a new `features/leads/` module delivers the
  Leads screen (pull-to-refresh, a distinct empty state, three outcome chip variants) and a new, dependency-free
  relative-time utility. Final counts: 783/783 backend tests, 257/257 mobile tests.
- **`LEAD-002` ("understand my listing visibility") has since shipped and been signed off on top of `LEAD-001`,
  completing Sprint 10 and Milestone ML10 in full** — see
  `docs/implementation/walkthroughs/Walkthrough_S10_LEAD-002.md`. It extends the existing `contact` module in
  place a fourth time with a new, read-only `VisibilityAnalyticsService`/`GET
  /providers/me/visibility-analytics` — zero new schema, zero new migration — surfacing `contact_views` and
  `search.provider_matches` as two headline stats (search appearances, contact views) plus a 30-day daily trend
  chart. Unlike `LEAD-001`, this story's data ownership split 50/50 between `contact` and `search`, resolved via
  a new **dependency-direction-symmetry** tiebreaker extending `ADR-054` to the "no single owner" case: extend
  the module that already holds a one-directional edge toward the other, rather than inventing a new,
  opposite-direction edge (`ADR-056`). AC2's literal text named `search_event_log` as a source table, but that
  table has no `provider_id` column and cannot answer a per-provider question — corrected to source
  "search appearances" from `search.provider_matches` instead (a table-reference correction, `ADR-038`-style,
  zero new tables). A three-state `up`/`down`/`flat` trend enum and an explicit server-computed
  `has_sufficient_data` boolean gate the "not enough data yet" state. On mobile, a new
  `features/visibility_analytics/` module delivers the screen and this codebase's **first chart of any kind** —
  a small, dependency-free `CustomPainter`-based widget, no new charting package added. **`tester` found one
  real bug**: the headline 30-day total and the chart series were computed from two independently-derived time
  windows (an exact-instant anchor vs. a calendar-day anchor), which could disagree near a day boundary — caught
  with a genuinely reproducing test, fixed by aligning both to one shared calendar-day window boundary.
  **`architect`'s subsequent review found one further, non-blocking gap the fix exposed**: the new
  `date_trunc('day', ...)` day-bucketing queries (this codebase's first) relied implicitly on the DB session's
  timezone GUC rather than pinning UTC explicitly — fixed by pinning UTC in both queries. Both principles (a
  shared window-boundary computation between two views of the same data; explicit UTC-pinning for day-bucketing
  SQL) are recorded together as `ADR-057`. Both fix rounds independently re-verified, zero regressions. Final
  counts: 821/821 backend tests (783 baseline + 38 net new across both fix rounds), 280/280 mobile tests (257
  baseline + 23 new). **This is the second story this Sprint/Milestone to need a fix-and-recheck round**
  (`LEAD-001` was clean on the first pass). CTO gave a standing instruction to proceed straight through closeout
  once both verdicts were clean, without an additional sign-off pause for this story. **Tracker sync for both
  `LEAD-001` and `LEAD-002` is done and verified** (Dashboard numbers in the bullet above are current).
- **Sprint 11 ("Marketplace Operations," Milestone ML11, Epic ML11-EP01) has since started.** Its first story,
  `ADM-001` ("Resolve manual-match and unmatched-query work as an administrator"), has shipped and been signed
  off on top of `AI-002` — see `docs/implementation/walkthroughs/Walkthrough_S11_ADM-001.md`. It ships the
  genuinely new `administration.unmatched_query_reports` table (a real migration — this codebase's own
  documentation-integrity check during planning confirmed the table did not exist before this story, correcting
  a stale precedent-list entry, see Section 4 below), populated automatically by one additive, write-time hook
  inside `SearchRequestService._finalize_matches` (`ADR-058`, extending `ADR-042`'s in-place-upgrade principle to
  a new-dependent-record-creation case), plus `administration`'s first-ever `api.py` (`ADR-059` — an admin
  capability's HTTP surface lives wherever the write its resolution performs actually lands; this one is
  self-contained, unlike `administration`'s three prior aggregates). Getting there required avoiding a circular
  import **twice** in one story — once as planned (`search -> conversation.MessageRepository`, for AC2's
  transcript embedding) and once as a genuine mid-implementation deviation from the Plan's own literal wiring
  instruction (`administration -> search.SearchEventLogService`, constructed directly from `search`'s leaf
  repository rather than via `search/dependencies.py`, since the Plan's own two separately-correct wiring items
  would otherwise have combined into a second cycle neither one alone created) — both recorded as one shared,
  generalizable principle (`ADR-060`). AC3/AC4/AC6-for-manual-matches/AC7-bullet-1 were confirmed already fully
  shipped by `AI-002` with zero new write logic needed, narrowing this story's real net-new engineering to
  AC1/AC2/AC5. **`tester` found all 7 verbatim ACs pass, zero gaps, zero regressions in the already-shipped
  `AI-002` code; `architect` returned zero blocking findings, no fix-and-recheck round needed.** CTO gave a
  standing instruction for this story to proceed straight through closeout without an additional sign-off pause
  once both verdicts were clean. Final counts: 864/864 backend tests (821 baseline + 43 new, zero regressions).
  Backend-only — no mobile/Flutter work, per the story's own explicit scope. **This is Sprint 11's first story —
  1 of 2 done.**
- Full narrative history of every story shipped so far (Sprints 1–11) lives in
  `docs/AI/PROJECT_IMPLEMENTATION_STATE.md`'s Executive Summary — only open that file if you need deep
  historical context on a specific earlier decision; it's over 1200 lines.

## 2. Next story — Sprint 11, second story: `ADM-002`

**Sprint 11 ("Marketplace Operations," Milestone ML11, Epic ML11-EP01) is now 1 of 2 stories done: `ADM-001`
shipped.** Its second and final story, `ADM-002` ("Operate the marketplace from an admin dashboard"), depends on
`VER-002` (already shipped, Sprint 5) + `ADM-001` (now also shipped) — both dependencies are satisfied, so
`ADM-002` is the next startable story in this sprint. Its full details have not been re-fetched from
`docs/AI/Project_Tracker.xlsx` this session — a fresh lookup is needed before planning begins, per this
project's standing practice of reading the tracker fresh at the start of each new story's planning rather than
relying on a stale summary here.

**Do NOT start `ADM-002` (or plan it) without the CTO's explicit "Start X" instruction** — noting it as the next
startable story is not authorization to begin it.

## 3. Standing process (do not skip steps)

Every story follows this full cycle, no exceptions, no shortcuts:

1. **tech-lead** agent plans the story → `docs/implementation/plans/Plan_SXX_<Story-ID>.md`.
2. **backend** agent implements (and **frontend** agent, if mobile work is in scope) — always run the *full*
   test suite before reporting done (not just new tests), plus `ruff`/`flutter analyze`.
3. **tester** agent independently verifies every verbatim AC with real evidence (real DB, real HTTP round
   trips) — never trust "should work," hunt for cross-module interaction bugs the implementer couldn't see in
   isolation. If it finds a bug, it writes a failing regression test and leaves it in the suite; the
   orchestrator commits that failing test, then dispatches backend/frontend to fix it.
4. **architect** agent reviews against `02_ARCHITECTURE.md`/`08_CODING_STANDARDS.md`/`06_SECURITY.md` as the
   final gate. Verdict is APPROVED / APPROVED WITH RECOMMENDATIONS / CHANGES REQUIRED. Any real finding gets
   fixed and then re-checked by architect before sign-off — every story in this project so far has needed at
   least one such fix-and-recheck round; don't be surprised if the next one does too.
5. **CTO sign-off** — always ask via `AskUserQuestion` before writing the Walkthrough or touching
   `CHANGELOG.md`/the tracker. Never assume approval.
6. **Closeout** — tech-lead writes `docs/implementation/walkthroughs/Walkthrough_SXX_<Story-ID>.md`, records
   new ADRs (append-only) in `09_DECISIONS.md`, updates `04_DATABASE.md`/`13_OPEN_DECISIONS.md` as needed,
   updates `PROJECT_IMPLEMENTATION_STATE.md` and `CHANGELOG.md`.
7. **Tracker sync** — the orchestrator (not a subagent) does this directly via the raw-XML method (Section 5
   below), since the tech-lead/tester/architect agents in this project do **not** have Bash/openpyxl access.
8. **Update this file** (`SESSION_HANDOFF.md`) with the new state before ending the session.

**Never start a story without an explicit "Start X" instruction from the CTO.** Planning ahead or
implementing speculatively is against this project's established practice.

**Never let a real finding from tester/architect go unfixed before sign-off.** Every story so far (CLM-001,
AI-001, AI-002) has had at least one genuine bug found and fixed during review — this is the process working
as intended, not a sign something is wrong. **`MAT-001` is the first exception**: `architect` returned
APPROVED with zero findings on the first pass — the tester found no functional bugs either, only a genuine
end-to-end coverage gap to close (a claim of "already satisfied" for AC5 that had never actually been tested)
and one trivial doc-only bug (a stale OpenAPI comment). Don't read this as evidence the review process can be
skipped or lightened going forward — it can genuinely happen when a story's scope is this narrow and
well-precedented, not a reason to expect it every time.

## 4. Key technical precedents already established (reuse, don't reinvent)

- **Module structure:** `backend/app/modules/<domain>/{models,repositories,services,api.py,schemas.py,
  dependencies.py}.py`. Cross-module communication is **constructor-injected services only** — never reach
  into another module's repository directly. Check for import cycles before adding a new cross-module edge.
- **Atomic conditional updates for race conditions:** when two concurrent actors might both pass a
  status-check-then-write, use a single `UPDATE ... WHERE id = :id AND status = 'pending'` + check
  `rowcount == 1` — never a read-then-write check. Three existing examples to mirror:
  `ProviderRepository.try_claim_for_account`, `VerificationRecordRepository.try_claim_for_review`,
  `ManualMatchAssignmentRepository.try_resolve`.
- **Swappable external-integration Protocol pattern** (four applications so far: `FileStorage`,
  `DocumentOcrService`, `GooglePlacesClient`, `ConversationAiClient`): define a `Protocol`, ship one honest
  concrete implementation now (interim/stub/rule-based as appropriate), never guess at a real vendor's API
  shape without credentials to test against.
  **Currently unresolved real-vendor gap:** no real LLM provider is selected anywhere (tracked as
  `13_OPEN_DECISIONS.md` item 13) — `ConversationAiClient`'s only implementation is fully rule-based.
- **Pull-based admin queue pattern** (four applications, all genuinely shipped as of `ADM-001`'s completion:
  `admin_action_log`, `claim_review_requests`, `manual_match_assignments`, `unmatched_query_reports`):
  backend-API-only, no dashboard UI yet (that's `ADM-002`, a later story), admin polls a `GET .../queue`
  endpoint. Never invent a push-notification "notify the admin team" mechanism — no such recipient concept
  exists in this codebase. **Documentation-integrity note:** prior to `ADM-001` shipping, this same entry listed
  `unmatched_query_reports` as if it were already a fourth shipped application, alongside the other three — this
  was a genuine documentation slip, not fact: `administration/models.py` defined only three model classes at the
  time, no migration referenced `unmatched_query_reports` anywhere, and `04_DATABASE.md` itself already labeled
  it "remain unbuilt" in the same breath. `ADM-001`'s own planning caught this directly against the real code
  before any implementation began, and the table has genuinely shipped since. Recorded here so a future reader
  isn't confused about why an "already shipped" claim needed correcting mid-project — the entry above is now
  accurate as of `ADM-001`'s completion, not before.
- **Soft-delete is the default** for any `CommonColumnsMixin`-based table (`deleted_at`/`is_active`) —
  `04_DATABASE.md`'s Soft Delete section only exempts `audit_logs`/`search_event_log` (append-only-by-design).
  AI-001 shipped a real bug (hard-deleting `messages` on a factually wrong premise) by not checking this —
  don't repeat it.
- **Anti-fabrication principle** (`00_PROJECT_CONTEXT.md` §3): never synthesize a value the system can't
  honestly provide (a rating, a location, a category, an assigned admin). Make the column nullable and report
  the honest absence instead. Applied repeatedly: AI-001 (AC5 deferral), AI-002 (four nullable-column
  deviations), CLM-001 (Google-seeded listings never claim a fake verification review).
- **Set the final status at creation, never patch an interim one** (ADR-029): when a locked enum has no
  "pending/submitted" value, don't invent one — create the row only once its real final state is known.
- **`{id}`-addressable collection vs `/me` singleton** (ADR-015): a genuine 1:N collection (sessions,
  addresses, search requests) gets `{id}` + `ensure_owner_or_not_found` (always 404, never 403, for another
  user's resource); a strict one-per-account resource (a profile) is a `/me` singleton with no id parameter.
- **Config, not schema, for a business-tunable numeric threshold** (confidence threshold, turn cap, match
  result cap) — a `Settings` field, not a hardcoded constant or a new DB column.
- **In-place upgrade of a shared query, not a second parallel implementation, when two callers need to share a
  changed behavior** (ADR-042, `MAT-001`): when a Plan/prior story has already pre-announced that a shared
  query will later gain new behavior (e.g. DIR-001's own AC5 naming `MAT-001` as its future ranking upgrade),
  modify the existing method in place — never fork it into `foo`/`foo_v2` — and prove the untouched parts
  (filter clauses, WHERE conditions) really didn't change via a direct diff, not just "tests still pass."
- **Merit-ranking formula pattern** (ADR-042/043, `MAT-001`): a bounded `[0, 1]` weighted composite score,
  every term normalized before combining (never mixing raw units like meters with a 1–5 rating scale), computed
  inside the same `ORDER BY` a paginated query already uses (never re-ranked in Python after `LIMIT`/`OFFSET`
  — that either defeats pagination or silently misranks across pages). Config-driven weights (`RANKING_*`
  `Settings`), a documented neutral default for a `NULL` signal (never treating "no data" as best or worst).
  **`REV-001` will need this precedent**: the formula already reads `providers.average_rating`/`review_count`
  and needs zero further code change once real rating data exists — `REV-001`'s job is only to become the first
  real writer of those columns (and to decide `13_OPEN_DECISIONS.md` item 14 — whether `provider_rating_summaries`
  is still needed as a separate table).
- **Cross-module wiring: Services only, never a raw Repository from another module** (ADR-047, `CON-001`) —
  `02_ARCHITECTURE.md`'s rule now has a concrete violation-and-fix example to cite: `ContactService` was
  initially wired to a raw `ProviderRepository` instead of `ProviderService`, duplicating logic already in
  `ProviderService.get_for_public_profile`; fixed at commit `bed63e8`. When a new module's service needs data
  from another module, prefer that module's Service class; a raw cross-module Repository dependency is only
  acceptable when the target module's Service genuinely exposes no equivalent read primitive — and that gap
  should be named explicitly in the new module's own `dependencies.py` docstring, not silently assumed
  acceptable.
- **A permanent, identity-based authorization rejection is 403, not 409** (ADR-044, `CON-001`) — the
  self-dealing contact guard (`provider.user_id == current_user_id`, checked before any write) uses a new
  `SelfDealingContactError` (403), distinct from this codebase's existing 409-for-timing-conflict precedent
  (`ClaimAlreadyClaimedError`) since there is no race/retry window that would ever change the outcome for the
  same caller/provider pair.
- **A public, arbitrary-`{id}` customer-facing detail endpoint sibling to an existing `/me`-scoped router**
  (ADR-045, `CON-001`) — register the new router *after* the existing owner-scoped one so Starlette's
  registration-order route matching resolves `/me...` literal paths before the new `/{id}` path-parameter route
  is ever reached; don't gate a customer's ability to view/contact a resource they already have a direct
  reference to on a search-visibility flag like `is_discoverable` unless explicitly required.
- **Trust-badge precedence: raw fields, client-computed, never a server-computed enum** (ADR-046, `CON-001`) —
  when more than one raw trust-related boolean/enum must be shown together (e.g. `is_claimed` +
  `verification_status`), return both raw and let the client compute a strict precedence order client-side;
  never invent a single pre-computed `trust_badge` enum server-side. Reusable for a future Review domain's
  "Verified Visit" badge.
- **A module holding more than one aggregate root is a deliberate, precedented pattern, not accretion** (ADR-048,
  `REV-001`) — `outcome_tags` was added to the existing `contact` module (alongside `contact_views`) rather than
  a new standalone module, mirroring `administration`'s own `AdminActionLog`/`ClaimReviewRequest`/
  `ManualMatchAssignment` precedent. Prefer extending an existing module that already shares the same Postgres
  schema/cross-module edges over creating a new one purely for isolation with no real benefit.
- **An ordinary `{id}`-addressable-resource ownership check is always a 404, never a 403 — reserve 403 for a
  permanent, identity-based rule with no race/retry window** (ADR-049, `REV-001`) — `outcome_tags`' ownership
  check reuses `ensure_owner_or_not_found` (ADR-015) exactly as `CON-001`'s `search_request_id` check did, kept
  deliberately distinct from `CON-001`'s own self-dealing 403 (ADR-044).
- **Atomic conditional writes, INSERT-shaped** (ADR-049, `REV-001`) — a fourth application of the "never a
  read-then-write check" family, and the first INSERT-shaped one: `postgresql.insert(...).values(...)
  .on_conflict_do_nothing(index_elements=[...]).returning(...)`, returning `None` on the conflict path (no
  exception-driven `IntegrityError`/`session.rollback()` recovery needed). Reuse this for any future INSERT-time
  uniqueness race (e.g. `REV-002`'s own `reviews.contact_view_id` uniqueness constraint is a direct candidate).
- **A flagged, additive touch-point on an already-shipped module's service is the correct way to wire a new
  story's side effect into existing code** (ADR-050, `REV-001`) — `ContactService.create_contact_view` gained one
  new unconditional notification call for `REV-001`, with every other line of the method left untouched; call out
  such touch-points explicitly in the Plan and Walkthrough rather than burying them as an incidental diff.
- **Fire a notification immediately/synchronously when no scheduling infrastructure exists, rather than inventing
  one** (ADR-050, `REV-001`) — mirrors the existing discipline against inventing unrequested mechanisms (e.g. the
  admin-queue pull-based pattern's "never invent a push-notification recipient concept"). Flag the gap to the CTO
  as an open item, don't block the story on building scheduling infrastructure nobody asked for yet.
- **Module-vs-schema placement rule, generalized** (ADR-051, `REV-002`) — a new table set gets its own new module
  when it owns a genuinely separate Postgres schema (the codebase's actual default: `provider`, `contact`,
  `notification`, `verification`, `search`, `administration` are each their own module/schema pair); it only
  folds into an existing module when it *shares* that module's existing schema (`outcome_tags`→`contact`,
  ADR-048, was this narrower exception, not a general "related-by-FK" license). Check Postgres schema identity
  first, not just how tightly a new table references another module's data by foreign key.
- **Race-safe aggregate recompute over an unbounded, growing row set: lock the parent row, then fully recompute
  — never increment** (ADR-052, `REV-002`) — when an aggregate (e.g. an average) must be recalculated
  transactionally on every write and read by a trust-facing/ranking-facing consumer, take a
  `SELECT ... FOR UPDATE` lock on a stable parent row (here, `providers`) before a fresh `AVG()`/`COUNT()`-style
  recompute from the raw rows, rather than an incremental running-average update — the latter is race-safe on its
  own but compounds `NUMERIC` column rounding drift over the aggregate's lifetime, which a full recompute never
  does. First application of a lock held across a multi-statement critical section in this codebase (every prior
  atomic-write precedent is a single self-contained statement).
- **A new 409/404 rejection family should reuse an existing exception for an identical check, and only add a new
  exception per genuinely distinct rejection reason** (ADR-053, `REV-002`) — `reviews`' ownership check reused
  `ContactViewNotFoundError` verbatim (the same check `REV-001`'s `outcome_tags` already performs on the same
  resource) rather than inventing a duplicate 404; separate new 409s were added only for the two genuinely
  distinct reasons (anchor validity, uniqueness) that need independently distinguishable rejection reasons.
- **Module/schema placement rule, generalized from the opposite direction: zero new schema → fold into the
  module that already owns the primary data being surfaced** (ADR-054, `LEAD-001`) — `ADR-051` already
  established that a genuinely new schema gets a new module regardless of FK-reference density; `LEAD-001`
  confirms the converse: a capability introducing no new schema at all has nothing for a standalone module to
  own, so it belongs inside whichever existing module already owns the data being surfaced, even when it
  requires new cross-module raw-Repository edges into schemas that module had no prior relationship with.
  **This story's own `architect` review also caught a concrete instance of `ADR-047`'s docstring-naming
  requirement not yet being honored** — the wiring was correct, but the new raw-Repository edges weren't yet
  named as the `ADR-047` exception in `dependencies.py`'s own docstring; fixed at implementation time. Treat
  `ADR-047`'s naming duty as a mandatory step when adding a new raw-Repository edge, not something to leave for
  review to catch.
- **A chained, multi-hop optional-FK context resolution needs an honest `null` at every dead-end, even when
  there is more than one independently reachable dead-end** (ADR-055, `LEAD-001`) — extends the anti-fabrication
  principle (`ADR-038`) beyond its prior single-dead-end applications: `LEAD-001`'s category-context lookup
  (`contact_views.search_request_id → search_requests.category_id → categories.name`) has two distinct, real
  absence reasons, both collapsing to one honest fallback (never a fabricated substitute like the provider's own
  category label), with each dead-end tested as its own separately-named case rather than assumed identical by
  inspection.
- **When a story's primary data ownership splits ~50/50 between two modules (no single dominant owner), use
  dependency-direction symmetry as the tiebreaker** (ADR-056, `LEAD-002`) — extend whichever module already
  holds a one-directional, precedented edge toward the other module's schema, rather than inventing a
  brand-new, opposite-direction edge with no precedent. Apply in order: schema ownership (`ADR-051`) → single
  dominant owner (`ADR-054`) → dependency-direction symmetry (`ADR-056`) → only then consider a new standalone
  module.
- **Two derived views of the same underlying data (a summary stat and a detail series) must share one window-
  boundary computation, never two independently "reasonable" ones** (ADR-057, `LEAD-002`) — the real lesson from
  a genuine bug `tester` found: `LEAD-002`'s headline 30-day total and its 30-day chart series each computed
  their own window start (an exact-instant anchor vs. a calendar-day anchor), which could disagree near a day
  boundary. Fixed by deriving both from one shared boundary. Generalize this beyond dates: whenever two outputs
  must stay consistent with each other, compute the shared boundary/filter once, not twice.
- **Any `date_trunc`/day-bucketing SQL query must pin UTC explicitly**, never rely on the DB session's implicit
  timezone GUC (ADR-057, `LEAD-002`) — established at this codebase's first such query, after `architect`'s
  review found the fix above's new queries hadn't pinned UTC, a latent risk of reintroducing the same divergence
  via a future session/config difference.
- **Auto-create a dependent record inside an existing shared write path, keyed off a specific outcome of that
  write** (ADR-058, `ADM-001`) — `unmatched_query_reports` rows are created by one additive call inside
  `SearchRequestService._finalize_matches` whenever the row it just wrote has `was_matched = false`, never by a
  lazy list-time query or a batch/cron job. Extends `ADR-042`'s "in-place upgrade of a shared write path" to a
  new shape: creating a new, dependent record in a different module's schema, not just changing what the shared
  write itself records.
- **An admin capability's HTTP surface lives in whichever module performs the write its resolution requires; a
  self-contained resolution (no cross-module write) belongs in the aggregate's own home module even if that
  module has never had an `api.py` before** (ADR-059, `ADM-001`) — a sibling rule to `ADR-051`/`ADR-054`'s
  schema-ownership placement rule, for a different question (route placement, not table placement).
  `administration` got its first-ever `api.py` for `unmatched_query_reports` specifically because reviewing it
  needs no write into another module's schema, unlike all three of `administration`'s prior aggregates.
- **When a planned cross-module wiring path would itself create a circular import — whether foreseen at planning
  time or only surfacing from the interaction of two of the same Plan's own separately-reasoned wiring items —
  construct the dependency directly from the target module's leaf repository instead, and document why in the
  wiring function's own docstring** (ADR-060, `ADM-001`) — a second, distinct justification under `ADR-047`'s
  raw-dependency exception, applied twice in one story (`search -> conversation.MessageRepository`, as planned;
  `administration -> search.SearchEventLogService`, as a genuine mid-implementation deviation from the Plan's
  own literal text). Re-check for a fresh circular import whenever a new edge touches a `dependencies.py` file
  already modified earlier in the same story — a Plan can reason correctly about each wiring edge in isolation
  and still combine two of its own items into a cycle neither one alone would have produced.

## 5. Tracker editing method (raw XML — never openpyxl `.save()`)

`Project_Tracker.xlsx`'s formatting/conditional-formatting/charts get corrupted by openpyxl's write path.
The only safe method, used for every closeout so far:

1. `cp docs/AI/Project_Tracker.xlsx` to a scratch copy; `unzip` it into `extracted/` and a pristine `orig_extract/`.
2. Use `openpyxl` (read-only, `data_only=False`) to find the exact cell coordinates and current formula/values
   you need to change (Story status, and every dependent rollup: Epic → Milestone → Sprint → Phase Tracker →
   Dashboard — **all of these are live formulas** referencing the Stories sheet, except several Dashboard cells
   which are **plain hardcoded values** that must be manually recomputed: `Completed Milestones`/`Completed
   Epics`/`Completed Stories`, and `Current Milestone`/`Current Sprint`/`Upcoming Sprint`).
3. Patch the raw XML in `extracted/xl/worksheets/sheetN.xml` with exact, anchored string replacements (the full
   `<c r="...">...</c>` element, asserting count==1 before replacing) — never touch `sharedStrings.xml` unless
   a genuinely new string is needed (reuse existing shared-string indices for "✅ Done"/"⏳ Planned"/etc., which
   are already in the table).
4. Rezip (`zip -X -r`), then verify via `openpyxl` (`data_only=True`) that every value/rollup is correct.
5. **Rigorously confirm no unintended changes**: for every edit, revert it in a scratch copy and assert the
   result is byte-identical to the pristine original file. Only then replace the real
   `docs/AI/Project_Tracker.xlsx` and commit.
6. Watch for **stale cached rollup values** unrelated to your own edit (this has happened twice — Phase
   Tracker's PH2 progress and the Dashboard's Current Milestone/Sprint pointers were both found stale by one or
   two stories, because a prior closeout's manual patch missed a downstream cell). Recompute from the real
   Stories data directly rather than trusting old cached values when in doubt.

## 6. Open decisions that remain genuinely unresolved (do not silently resolve or forget these)

Only the still-`Open` items from `13_OPEN_DECISIONS.md` are listed — see that file directly if you need an
item's full history/reasoning.

- **Item 3 — Google Places Data Legal Review.** CTO made an explicit risk-acceptance decision (09 Sept 2026)
  to proceed with bulk-import anyway; the underlying legal/UAE-PDPL question is **not** resolved and this item
  must stay `Open` in perpetuity until real legal review happens. Do not let a future session mark this
  Resolved just because CLM-001 shipped.
- **Item 5 — Business Verification Bar.** Open.
- **Item 8 — Final Product / Company Name.** Open ("Qivo" is an uncleared candidate name — do not use it in
  anything user-facing or legally binding).
- **Item 10 — Degree of Manual ("Wizard-of-Oz") Matching at Launch.** The *mechanism* now exists and works
  (AI-002 shipped it) — the *product question* of how much matching should stay manual long-term at launch is
  still open.
- **Item 11 — Real OCR Pipeline Interface Confirmation.** Open (`StubDocumentOcrService` is still the only
  implementation).
- **Item 12 — Mobile `features/search`/`features/home` Directly Import `features/customer`.** Open, logged
  debt. Note: AI-002 explicitly did NOT add a third instance of this problem (it did a full shared-widget
  extraction instead) — keep that discipline.
- **Item 13 — Real LLM Vendor Selection and RAG Grounding Implementation.** Open. `ConversationAiClient` is
  fully rule-based; AC3/AC5 of AI-001 are honestly unmet pending a real vendor decision + credentials.
Item 14 (`provider_rating_summaries`) is **no longer listed here** — it was **Resolved** by `REV-002` (14
September 2026): both `providers.average_rating`/`review_count` (`MAT-001`'s ranking-formula hot-path read
target, unchanged) and `review.provider_rating_summaries` (the Review domain's own decoupled read-model) are
needed, written from the same computed values in the same transaction. See `13_OPEN_DECISIONS.md` item 14 for
the full resolution.

## 7. ADR numbering

Current last ADR in `docs/AI/09_DECISIONS.md`: **ADR-060** (ADR-058/059/060, all recorded at `ADM-001`'s
closeout — the write-time dependent-record-creation hook extending `ADR-042` to a new-record-creation case;
the admin-capability HTTP-surface placement rule, a sibling to `ADR-051`/`ADR-054` for the route-placement
question rather than the table-placement one; the circular-import-avoidance principle, applied twice in one
story, a second distinct justification under `ADR-047`'s raw-dependency exception). Prior: ADR-056/057,
recorded at `LEAD-002`'s closeout. Next new ADR starts at **ADR-061**.

## 8. Environment notes

- Backend: FastAPI/SQLAlchemy async, Postgres, Redis. Full test suite as of `ADM-001`'s closeout, independently
  verified clean by `tester` (all 7 ACs pass, zero gaps, zero regressions) and `architect` (zero blocking
  findings, no fix-and-recheck round needed): **864/864 backend tests passing** (821 baseline before `ADM-001`,
  +43 new, zero regressions). `ruff check .` clean. `mypy` is configured in `pyproject.toml` but is **not
  installed** in this sandbox's venv — cannot be run here; this is a known, pre-existing environment gap, not a
  regression to chase.
- Mobile: Flutter/Riverpod. **280 mobile tests passing**, unchanged since `LEAD-002`'s closeout (257 baseline +
  23 new) — `ADM-001` is backend-only, no mobile work in scope. `flutter analyze` clean as of `LEAD-002`. Flutter
  SDK is not preinstalled in a fresh container — a prior session cloned `flutter/stable` to `/root/.flutter_sdk`
  to run `flutter analyze`/`flutter test`/`gen-l10n`; this is outside the repo and won't persist across
  containers, so a fresh session may need to redo this setup step once, before running any mobile agent.
- `Project_Tracker.xlsx` is readable by direct `openpyxl`/shell access in this orchestrating session, but the
  specialist agents (tech-lead, tester, architect, backend, frontend) do **not** have Bash/openpyxl tools —
  always relay verbatim tracker text to them directly in the task prompt rather than asking them to read the
  spreadsheet themselves (this was a repeated, avoidable source of wasted planning rounds in Sprints 6–7).
---

**End of handoff. Sprint 11 / Milestone ML11 is now 1 of 2 stories done: `ADM-001` ("Resolve manual-match and
unmatched-query work as an administrator") has shipped and been signed off — see Section 1 and
`docs/implementation/walkthroughs/Walkthrough_S11_ADM-001.md`. Its tracker sync is still pending (a separate
process performed by the orchestrator, not part of this closeout). Sprint 11's second and final story, `ADM-002`
("Operate the marketplace from an admin dashboard"), is the next startable story — both of its dependencies
(`VER-002`, `ADM-001`) are now satisfied, but its full details have not been re-fetched from
`Project_Tracker.xlsx` this session.** When resuming: read this file, perform the tracker sync for `ADM-001` if
not already done, confirm the CTO wants to proceed with `ADM-002`, then follow Section 3's cycle starting with
`tech-lead`.**
