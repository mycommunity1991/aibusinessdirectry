# Session Handoff — Read This First, Skip the Tracker

**Purpose:** A new session should be able to resume story-by-story development directly from
this file — without opening `Project_Tracker.xlsx` or re-reading `PROJECT_IMPLEMENTATION_STATE.md`
in full — to save tokens. This file is refreshed at the end of every story closeout. If it looks
stale (doesn't match the latest git log / `09_DECISIONS.md` ADR numbers), trust the repo over this
file and update this file once caught up.

**Last updated:** 10 September 2026, immediately after Story AI-002 closeout.
**Repo:** `mycommunity1991/aibusinessdirectry` | **Branch:** `claude/provider-storefront-pro-001-qnicuj`
**Last commit at time of writing:** `6c7482c` (tracker sync marking AI-002 Done)

---

## 1. Where things stand

- **Sprints 1–7 are fully complete.** Milestones ML1 through **ML7 are all Done.**
- **Dashboard numbers (as of commit `6c7482c`):** Overall Progress **49%** | Completed Milestones **7/24** |
  Completed Epics **13/23** | Completed Stories **33/47** | Current Phase **PH2** | Current Milestone **ML8** |
  Current Sprint **SP08** | Upcoming Sprint **SP09**.
- **Sprint 8 / Milestone ML8 has NOT been started.** Its two stories are detailed in full below (Section 2) —
  everything needed to start is already here, no tracker read required.
- Full narrative history of every story shipped so far (Sprints 1–7) lives in
  `docs/AI/PROJECT_IMPLEMENTATION_STATE.md`'s Executive Summary — only open that file if you need deep
  historical context on a specific earlier decision; it's ~1000 lines.

## 2. Next stories — Sprint 8 / Milestone ML8 (verbatim from the tracker, already extracted)

**Do NOT start either story without the CTO's explicit "Start MAT-001" (or equivalent) instruction.**
Standing practice throughout this project: no engineering agent plans or starts a story unprompted.

### MAT-001 — "See ranked providers for my request"
- Sprint: SP08 | Epic: ML8-EP01 | Milestone: ML8 | Phase: PH2 | Priority: **Critical** | Depends On: **AI-002 (done)**
- **Description:** As a customer, I want the providers matched to my described need ranked by relevance and
  quality, so that the best-fit options show up first. This story upgrades DIR-001's structured search into
  the AI-powered ranking pipeline, consuming AI-002's structured Search Request output and combining it with
  the same category → geospatial → discoverability filter chain, then ranking by proximity plus rating and
  review volume — never distance alone. **Scope boundary:** does not include the actual contact/reveal step
  (CON-001) — this story ends at a ranked results list.
- **Acceptance Criteria (verbatim):**
  1. `search_requests` and `provider_matches` tables exist via migration; `provider_matches` stores rank and
     match_score per provider per request.
  2. Filter order is identical to DIR-001's (category, then geospatial radius, then discoverability) — this
     story does not introduce a second, divergent filter implementation.
  3. Ranking combines proximity with `provider_rating_summaries` (average rating and review count) and is
     never based on distance alone.
  4. Ranking ties break deterministically (e.g., by `provider_id`) so identical searches return stable,
     reproducible ordering.
  5. Search Results screen consumes AI-001's conversation output directly — Home's search entry point starts
     a Conversation Session, which flows into this screen without a manual re-search step.
  6. Every search, matched or not, is written to `search_event_log` with an accurate `was_matched` flag.
  7. A provider with `is_discoverable=false` never appears in ranked results, mirroring DIR-001's rule.
  8. Automated tests cover ranking correctness against known rating/distance combinations and deterministic
     tie-breaking.
- **Important note for whoever plans this:** `search.search_requests`/`provider_matches`/`search_event_log`
  and the `_finalize_matches` mechanism **already exist** — AI-002 built them (see ADR-037/038/039/040/041).
  AI-002's Decision 5 explicitly deferred a real merit-ranking algorithm (rating × review-count × proximity)
  because the Review domain (`REV-001`, unshipped) has no real rating data yet — `match_score` is currently
  always `NULL`. **This story (MAT-001) is very likely the one meant to finally implement that ranking
  formula** — check whether `REV-001`/`provider_rating_summaries` has shipped by the time this starts; if not,
  this is a real, must-resolve planning question (same shape as AI-001's own scope questions), not something
  to silently guess at.

### CON-001 — "Contact a matched provider directly"
- Sprint: SP08 | Epic: ML8-EP02 | Milestone: ML8 | Phase: PH2 | Priority: **Critical** | Depends On: **MAT-001**
- **Description:** As a customer, I want to see a matched provider's phone number immediately when I tap
  Contact, with no quote or approval step in between, so that reaching out feels as simple as getting a number
  from a friend. This story implements the platform's growth-first, direct-contact model and its most
  safety-critical rule: **the self-dealing guard.** Because one Account may hold both Customer and Provider
  roles, a Contact View must be rejected outright if the requesting Customer's Account is the same Account
  that owns the target Provider — otherwise a provider could inflate their own lead/contact/review numbers by
  contacting themselves. **Scope boundary:** does not include the Outcome Tag prompt or reviews (REV-001/002)
  — this story ends at the phone number being shown.
- **Acceptance Criteria (verbatim):**
  1. `contact_views` table exists via migration, referencing the customer, the provider, and optionally the
     originating search request.
  2. Tapping Contact on a matched provider immediately shows the phone number and Call/WhatsApp buttons in a
     bottom sheet — no quote request, approval wait, or in-app messaging step exists anywhere in this flow.
  3. A Contact View is rejected if the requesting Customer Account is the same Account that owns the target
     Provider — this is enforced at the point of Contact View creation, not just documented as a rule.
  4. The rejection in the self-dealing case is tested explicitly with an automated test asserting the Contact
     View row is never created.
  5. Provider Profile screen shows rating together with review count (never rating alone), a Verified badge
     (or Unclaimed label) as applicable, and hours/service-area information.
  6. The Contact Reveal sheet includes a brief note that contact happens outside the app.
  7. Every Contact View creation is a candidate trigger for provider-lead notifications (wired fully in
     ENG-001, but the event itself must be emitted here).
  8. Automated tests cover the happy path (successful contact reveal) and the self-dealing rejection as
     separate, explicit test cases.

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
as intended, not a sign something is wrong.

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

## 7. ADR numbering

Current last ADR in `docs/AI/09_DECISIONS.md`: **ADR-041**. Next new ADR starts at **ADR-042**.

## 8. Environment notes

- Backend: FastAPI/SQLAlchemy async, Postgres, Redis. Full test suite as of this writing: **658 backend tests
  passing**, **169 mobile tests passing**. `ruff check .` clean. `mypy` is configured in `pyproject.toml` but
  is **not installed** in this sandbox's venv — cannot be run here; this is a known, pre-existing environment
  gap, not a regression to chase.
- Mobile: Flutter/Riverpod. Flutter SDK is not preinstalled in a fresh container — a prior session cloned
  `flutter/stable` to `/root/.flutter_sdk` to run `flutter analyze`/`flutter test`/`gen-l10n`; this is outside
  the repo and won't persist across containers, so a fresh session may need to redo this setup step once,
  before running any mobile agent.
- `Project_Tracker.xlsx` is readable by direct `openpyxl`/shell access in this orchestrating session, but the
  specialist agents (tech-lead, tester, architect, backend, frontend) do **not** have Bash/openpyxl tools —
  always relay verbatim tracker text to them directly in the task prompt rather than asking them to read the
  spreadsheet themselves (this was a repeated, avoidable source of wasted planning rounds in Sprints 6–7).

---

**End of handoff. When resuming: read this file, confirm the CTO wants to proceed with MAT-001 (or a
different story), then follow Section 3's cycle starting with `tech-lead`.**
