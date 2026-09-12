# Session Handoff — Read This First, Skip the Tracker

**Purpose:** A new session should be able to resume story-by-story development directly from
this file — without opening `Project_Tracker.xlsx` or re-reading `PROJECT_IMPLEMENTATION_STATE.md`
in full — to save tokens. This file is refreshed at the end of every story closeout. If it looks
stale (doesn't match the latest git log / `09_DECISIONS.md` ADR numbers), trust the repo over this
file and update this file once caught up.

**Last updated:** 12 September 2026, immediately after Story CON-001 closeout, tracker synced.
**Repo:** `mycommunity1991/aibusinessdirectry` | **Branch:** `claude/provider-storefront-pro-001-qnicuj`
**Last commit at time of writing:** `1eacb4a` (tracker sync marking CON-001 Done)

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
- **Dashboard numbers (confirmed as of commit `1eacb4a`):** Overall Progress **54.2%** | Completed Milestones
  **8/24** | Completed Epics **15/23** | Completed Stories **35/47** | Current Phase **PH2** | Current Milestone
  **ML9** | Current Sprint **SP09** | Upcoming Sprint **SP10**.
- **Sprint 9 / Milestone ML9 ("Outcome & Reviews") has not been started.** Its first story is **`REV-001`**,
  detailed in full below (Section 2) — everything needed to start is already here, no tracker read required.
- Full narrative history of every story shipped so far (Sprints 1–8) lives in
  `docs/AI/PROJECT_IMPLEMENTATION_STATE.md`'s Executive Summary — only open that file if you need deep
  historical context on a specific earlier decision; it's over 1100 lines.

## 2. Next story — Sprint 9 / Milestone ML9 ("Outcome & Reviews")

**Do NOT start without the CTO's explicit "Start REV-001" (or equivalent) instruction.**
Standing practice throughout this project: no engineering agent plans or starts a story unprompted.

**`CON-001` ("contact a matched provider directly") has shipped** — its dependency requirement for `REV-001`
is satisfied. `REV-001` is the first of two stories in this milestone; `REV-002` (below, for context) depends
on `REV-001` and is not yet startable on its own.

### REV-001 — "Tell the platform whether I hired a provider"
- Sprint: SP09 | Epic: ML9-EP01 | Milestone: ML9 | Phase: PH2 | Priority: **High** | Depends On: **CON-001**
- **Description:** As a customer who contacted a provider, I want to quickly confirm whether I hired them, so
  that the platform has a real signal of what actually happened without tracking payment details it has no
  visibility into. The Outcome Tag is the platform's only conversion signal given the offline-payment reality
  of the direct-contact model. It is deliberately minimal — a yes/no tied to a specific Contact View — and only
  the Customer who generated that Contact View may submit it. **Scope boundary:** does not include the review
  itself (`REV-002`), which requires a "Yes" outcome tag as its anchor.
- **Acceptance Criteria (verbatim):**
  1. `outcome_tags` table exists via migration, with a unique constraint on `contact_view_id` (one outcome tag
     per Contact View).
  2. Only the Customer who owns the underlying Contact View can submit an outcome tag for it — attempting to
     submit for someone else's Contact View is rejected.
  3. The prompt ("Did you hire them?") is triggered after a Contact View, via a notification, and is
     dismissible ("Maybe later") without penalty.
  4. The outcome tag does not attempt to capture payment amount, job completion detail, or scheduling.
  5. A "No" or absent outcome tag is still retained as a signal (not discarded) — it is not required to be
     "Yes" for the tag itself to exist, only for a Review to follow.
  6. Automated tests cover the ownership restriction and the uniqueness-per-Contact-View constraint.

### REV-002 — "Leave a verified review after a successful hire" (for context only — depends on REV-001, not yet startable)
- Sprint: SP09 | Epic: ML9-EP01 | Milestone: ML9 | Phase: PH2 | Priority: **High** | Depends On: **REV-001**
- **Description:** As a customer who confirmed a hire, I want to rate and review the provider, so that future
  customers can trust the provider's track record — and so that reviews can never be submitted by someone who
  didn't actually go through a real Contact View and a positive outcome. This is the anchor-verified review
  model: a Review can only exist against a Contact View carrying a "Yes" outcome tag from `REV-001`. Because
  `CON-001`'s self-dealing guard already blocks a provider from generating a Contact View against their own
  listing, this story's anchor requirement transitively blocks self-reviews too, without needing a second
  explicit check. **Scope boundary:** does not include provider-side display of reviews beyond the rating
  summary recalculation. **This is also the story that finally builds `provider_rating_summaries`** — resolving
  `13_OPEN_DECISIONS.md` item 14's open question in the affirmative (the table is needed after all).
- **Acceptance Criteria (verbatim):**
  1. `reviews` and `provider_rating_summaries` tables exist via migration; `reviews.contact_view_id` is unique,
     enforcing one review per Contact View.
  2. Submitting a review is only possible when the anchoring Contact View has an `outcome_tags.hired=true` row
     — attempting otherwise (no outcome tag, or `hired=false`) is rejected.
  3. Rating is constrained to 1–5; a comment field is optional free text.
  4. `provider_rating_summaries` (average rating, review count) is recalculated in the same transaction as the
     review write — never left stale.
  5. Because the anchoring Contact View was already rejected for self-dealing in `CON-001`, an automated test
     confirms a provider cannot end up with a review pointing back at their own listing via this path.
  6. Write-a-Review screen is only reachable after a "Yes" outcome tag — there is no direct navigation path to
     it otherwise.
  7. Automated tests cover the anchor-verification rejection case and the rating-summary recalculation
     correctness.

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
- **Pull-based admin queue pattern** (four applications: `admin_action_log`, `claim_review_requests`,
  `unmatched_query_reports`, `manual_match_assignments`): backend-API-only, no dashboard UI yet (that's
  `ADM-001`/`ADM-002`, a later story), admin polls a `GET .../queue` endpoint. Never invent a push-notification
  "notify the admin team" mechanism — no such recipient concept exists in this codebase.
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
- **Item 14 — `provider_rating_summaries` Remains Unbuilt: Is It Still Needed Once Real Reviews Exist?** Open
  (new, added at `MAT-001`'s close). `MAT-001` ranks against `providers.average_rating`/`review_count` instead,
  since the table is unbuilt and structurally cannot hold data before `CON-001`/an Outcome Tag mechanism ship. A
  future `REV-001` must decide whether the distinct table is still needed once real reviews exist, or whether
  the `providers` columns alone are sufficient — not resolved here, not this story's decision to make.

## 7. ADR numbering

Current last ADR in `docs/AI/09_DECISIONS.md`: **ADR-047** (ADR-044/045/046/047, all recorded at `CON-001`'s
closeout). Next new ADR starts at **ADR-048**.

## 8. Environment notes

- Backend: FastAPI/SQLAlchemy async, Postgres, Redis. Full test suite as of `CON-001`'s closeout, independently
  re-run/re-confirmed at each review stage: **702/702 backend tests passing** (unchanged across both the
  pre-fix and post-fix (`bed63e8`) `architect` review passes — the fix was a pure refactor, no test assertions
  changed). `ruff check .` clean. `mypy` is configured in `pyproject.toml` but is **not installed** in this
  sandbox's venv — cannot be run here; this is a known, pre-existing environment gap, not a regression to chase.
- Mobile: Flutter/Riverpod. **195 mobile tests passing** as of `CON-001`'s closeout (192 after backend+frontend
  implementation + 3 more from `tester`'s coverage additions, including the Arabic-locale AC6 case).
  `flutter analyze` clean. Flutter SDK is not preinstalled in a fresh container — a prior session cloned
  `flutter/stable` to `/root/.flutter_sdk` to run `flutter analyze`/`flutter test`/`gen-l10n`; this is outside
  the repo and won't persist across containers, so a fresh session may need to redo this setup step once,
  before running any mobile agent.
- `Project_Tracker.xlsx` is readable by direct `openpyxl`/shell access in this orchestrating session, but the
  specialist agents (tech-lead, tester, architect, backend, frontend) do **not** have Bash/openpyxl tools —
  always relay verbatim tracker text to them directly in the task prompt rather than asking them to read the
  spreadsheet themselves (this was a repeated, avoidable source of wasted planning rounds in Sprints 6–7).

---

**End of handoff. Sprint 8 / Milestone ML8 is fully complete, tracker synced. When resuming: read this file,
confirm the CTO wants to proceed with `REV-001` (Sprint 9's first story, detailed in Section 2), then follow
Section 3's cycle starting with `tech-lead`.**
