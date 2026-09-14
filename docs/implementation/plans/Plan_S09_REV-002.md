# Plan for Story REV-002 — Leave a Verified Review After a Successful Hire

**Sprint:** 09 (Outcome & Reviews) | **Epic:** ML9-EP01 | **Milestone:** ML9 | **Phase:** PH2 | **Priority:**
High | **Depends On:** REV-001 (done, Sprint 9)

---

## Story (verbatim, relayed by the orchestrator this session)

"As a customer who confirmed a hire, I want to rate and review the provider, so that future customers can trust
the provider's track record — and so that reviews can never be submitted by someone who didn't actually go
through a real Contact View and a positive outcome. This is the anchor-verified review model: a Review can only
exist against a Contact View carrying a 'Yes' outcome tag from REV-001. Because CON-001's self-dealing guard
already blocks a provider from generating a Contact View against their own listing, this story's anchor
requirement transitively blocks self-reviews too, without needing a second explicit check. Scope boundary: does
not include provider-side display of reviews beyond the rating summary recalculation."

## Acceptance Criteria (verbatim, 7 items)

1. `reviews` and `provider_rating_summaries` tables exist via migration; `reviews.contact_view_id` is unique,
   enforcing one review per Contact View.
2. Submitting a review is only possible when the anchoring Contact View has an `outcome_tags.hired=true` row —
   attempting otherwise (no outcome tag, or `hired=false`) is rejected.
3. Rating is constrained to 1–5; a comment field is optional free text.
4. `provider_rating_summaries` (average rating, review count) is recalculated in the same transaction as the
   review write — never left stale.
5. Because the anchoring Contact View was already rejected for self-dealing in CON-001, an automated test
   confirms a provider cannot end up with a review pointing back at their own listing via this path.
6. Write-a-Review screen is only reachable after a "Yes" outcome tag — there is no direct navigation path to it
   otherwise.
7. Automated tests cover the anchor-verification rejection case and the rating-summary recalculation
   correctness.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **`reviews`/`provider_rating_summaries` are already fully spec'd in `04_DATABASE.md`** (Review Domain,
  `review` Postgres schema — its own schema, distinct from `contact`): `reviews` has `contact_view_id` (UUID, not
  null, FK → `contact.contact_views.id`, unique — 1:1), `customer_id` (FK → `customer.customer_profiles.id`),
  `provider_id` (FK → `provider.providers.id`), `rating` (SMALLINT, 1–5), `comment` (TEXT, nullable);
  constraints `uq_reviews_contact_view_id`, `chk_reviews_rating_range CHECK (rating BETWEEN 1 AND 5)`; index
  `idx_reviews_provider_id`. `provider_rating_summaries` has `provider_id` (FK, unique — 1:1), `average_rating`
  (NUMERIC(3,2), not null, default 0), `review_count` (INTEGER, not null, default 0), `recalculated_at`
  (TIMESTAMPTZ, not null); constraint `uq_provider_rating_summaries_provider_id`. Both remain fully unbuilt —
  confirmed by `04_DATABASE.md`'s own "Status" note and by a direct search: no `backend/app/modules/review/`
  directory exists anywhere in this codebase. No deviation from this spec is needed; this story builds it
  exactly as documented.
- **Item 14's resolution — `provider_rating_summaries` is needed, in addition to, not instead of,
  `providers.average_rating`/`review_count`.** `Plan_S08_MAT-001.md` Decision 2 substituted
  `providers.average_rating`/`review_count` for the (then-unbuildable) `provider_rating_summaries` table so
  `MAT-001`'s ranking formula had a real column to read; that formula is embedded directly in
  `ProviderSearchRepository.search_nearby`'s `ORDER BY` clause (`Plan_S08_MAT-001.md` Decision 1) and reads
  `providers.average_rating`/`review_count` inline in that same query — moving it to a join against a separate
  `provider_rating_summaries` table now would touch MAT-001's already-shipped, already-tested ranking SQL for a
  purely internal storage-location change with no behavioral benefit, which this story has no reason to force.
  **Both tables are therefore built and written in the same transaction, from the same computed values, by this
  story**: `providers.average_rating`/`review_count` remains the ranking formula's hot-path read target (zero
  change to `MAT-001`'s SQL); `review.provider_rating_summaries` is built exactly per its pre-existing
  `04_DATABASE.md` spec, becoming the Review domain's own decoupled read-model (its own `recalculated_at` audit
  column, its own row lifecycle, independent of `providers`) for whatever future Review-domain-facing feature
  needs it (explicitly out of this story's own display scope, but the table itself is real, live, and correct
  from day one, not a second unpopulated placeholder). This resolves `13_OPEN_DECISIONS.md` item 14 in the
  affirmative, exactly as `SESSION_HANDOFF.md` already frames it.
- **`contact.outcome_tags` (REV-001) is fully shipped.** `OutcomeTag` (`backend/app/modules/contact/models.py`)
  has `contact_view_id` (unique FK), `hired` (bool, not null), `submitted_at`. `OutcomeTagRepository`
  (`backend/app/modules/contact/repositories/outcome_tag_repository.py`) only has `try_create` today — no
  lookup-by-`contact_view_id` method exists, since REV-001 never needed one (it only ever creates, never reads
  back). This story needs a new read method on it.
- **`contact.ContactView` (CON-001) is fully shipped**, `ContactViewRepository` has only the inherited
  `get_by_id` (no custom methods) — read directly, confirms `customer_id`/`provider_id` are both plain columns
  on the row, exactly what AC2's anchor check and this story's denormalized `reviews.customer_id`/`provider_id`
  columns need.
- **The self-dealing guard (CON-001, `ContactService.create_contact_view`) rejects a self-dealing Contact View
  *before any row is written*** (`if provider.user_id is not None and provider.user_id == current_user_id: raise
  SelfDealingContactError()`, checked before `contact_view_repository.create(...)` is ever called). This is the
  load-bearing fact behind AC5's transitivity claim and behind how it must be tested — see Decision 4 below.
- **`providers.average_rating` has no DB-level `CHECK` constraint today**, confirmed directly in
  `backend/app/modules/provider/models.py` and by `04_DATABASE.md`'s own flagged note under the (unbuilt)
  `provider_rating_summaries` section. That note's exact wording — "`REV-001`, as the first real writer of this
  column, should add one" — is a **naming slip in the existing doc, not a decision already made against this
  story**: `REV-001`'s own Plan explicitly listed "Any change to `providers.average_rating`/`review_count`" as
  out of its scope, and `ProviderService`/`ProviderRepository` confirm no code path anywhere writes
  `average_rating` today (`create_provider`/`create_google_seeded_provider` only ever set `review_count: 0` at
  creation, never `average_rating`). This story is therefore the actual first real writer, and adds the missing
  `chk_providers_average_rating_range` constraint itself — flagged here as a documentation correction to make at
  closeout (`04_DATABASE.md`'s note should say `REV-002`, not `REV-001`).
- **AC2's anchor-verification check is a new precondition shape, distinct from every existing "ownership" or
  "uniqueness" check in this codebase.** It has two parts: (a) does `contact_view_id` exist and belong to the
  calling customer (ordinary `ensure_owner_or_not_found` ownership shape, ADR-015 — ✅ directly reusable,
  including `ContactViewNotFoundError`'s existing 404 shape verbatim, since the message and semantics are
  identical); (b) does that Contact View have an `outcome_tags` row with `hired=True` (a *new* shape — the
  resource exists and is owned, but its current state doesn't permit this write). This second shape already has
  a precedent family in this codebase: `VerificationSubmissionNotAllowedError`,
  `VerificationRecordNotActionableError`, `ManualMatchAssignmentAlreadyResolvedError` — all 409, all "the
  resource exists, ownership isn't in question, but its state blocks this specific write." A new
  `ReviewAnchorNotVerifiedError` (409) is the correct shape for this case, not a 403 (this is not a permanent,
  identity-based rule like `SelfDealingContactError` — a `hired=false` today doesn't mean this exact
  `contact_view_id` could never anchor a review under any circumstance, it means the current recorded outcome
  doesn't support one) and not a 404 (the resource is genuinely found and owned; nothing is being hidden).
- **`ensure_owner_or_not_found`** (`backend/app/core/authorization.py`) takes `(owner_id, requester_id, *,
  not_found_exc)` — directly reusable as-is for the Contact View ownership half of AC2, identical call shape to
  `OutcomeTagService.submit_outcome_tag`'s own use of it.
- **Cross-module service edges available today**: `ProviderService.get_for_public_profile` (existence/active
  check only — not needed here, since the Contact View's own `provider_id` column already names a real
  provider); no existing `ProviderService` method updates `average_rating`/`review_count` — this story adds two
  new ones (Decision 3). No existing `ProviderRepository` method takes a row lock — this story adds one
  (`get_by_id_for_update`, a plain `SELECT ... FOR UPDATE`).
- **No scheduling/notification requirement exists for a Review submission.** `03_DOMAIN_MODEL.md`'s Notification
  domain explicitly enumerates its only three triggers ("new Contact View (lead)... Verification status
  change, Outcome Tag prompt") — a Review event is not among them. No `NotificationService` change is in scope.
- **Mobile: S-10 "Write a Review" is grouped with S-06–S-10 under "Customer — Core Loop — Flow 4"**
  (`15_SCREEN_INVENTORY.md`), the exact same flow group `mobile/lib/features/provider_profile/` already owns
  (S-09 Provider Profile, the Contact Reveal sheet, the Outcome Tag Prompt sheet — REV-001's own placement
  choice for the latter). No existing star-rating widget exists anywhere in `mobile/lib` (confirmed by search) —
  a small new widget is needed, no new package.
- **`OutcomeTagPromptSheet`/`OutcomeTagPromptController` (REV-001) are fully shipped and already expose
  everything this story's mobile trigger needs without modifying either file**: `OutcomeTagPromptState.lastHired`
  already records which button the customer tapped, and `ProviderProfileScreen._onContactTap` already `await`s
  `OutcomeTagPromptSheet.show(...)` and can read the controller's post-close state the same way it already reads
  `ContactRevealController`'s state after `ContactRevealSheet.show(...)` closes (Decision 6,
  `Plan_S09_REV-001.md`'s own precedent, now applied one level deeper).
- **`ContactReveal.providerId`** (`mobile/lib/features/provider_profile/domain/models/contact_reveal.dart`)
  already exists, parsed from the `POST /contact-views` response's `provider_id` field — the Write-a-Review
  screen's `providerId` argument needs no new backend field or new mobile parsing.
- **Router precedent for a separate module's router sharing an existing URL prefix**: `admin_verification_router`
  et al. aside, the cleanest direct match is `verification_router` (a fully separate `verification` module)
  mounted at `prefix="/providers/me/verification"` — the same URL-prefix space `provider_router` itself uses
  (`backend/app/api/v1/api.py`). This is the exact shape needed for this story's endpoint: a new, separate
  `review` module's router, mounted at `prefix="/contact-views"` (the same prefix `contact_router` uses),
  exposing `POST /contact-views/{contact_view_id}/review` — mirroring `outcome-tag`'s identical nested-1:1-child
  URL shape exactly, without needing the new `review` module to physically live inside `contact`.
- Current Alembic migration head: `e11a26e9560e` (`outcome_tags_domain`, REV-001). This story adds two new
  migrations on top of it (Decision 2).

---

## Architecture Decisions

### Decision 1 — `review` is a new, standalone module (not folded into `contact`), because it owns a genuinely separate Postgres schema

**The problem:** REV-001 folded `outcome_tags` into the existing `contact` module because it shared `contact`'s
own Postgres schema. Does the same reasoning apply to `reviews`/`provider_rating_summaries`?

**Chosen:** no — create a new `backend/app/modules/review/` module, with its own `review` Postgres schema, exactly
as `04_DATABASE.md`'s own `# Review Domain (\`review\` schema)` heading already documents. This mirrors this
codebase's actual, consistently-applied rule (`administration`'s multi-aggregate-root precedent, and REV-001's own
citation of it, both explicitly conditioned on "shares the same Postgres schema") — the condition that justified
folding `outcome_tags` into `contact` (same schema) does not hold here (`review` is its own schema, per the DB
spec, not `contact`'s). A new module for a new schema is this codebase's actual default (`provider`, `contact`,
`notification`, `verification`, `search`, `administration` are each their own module/schema pair); `outcome_tags`
was the deliberate exception, not the rule.

**Alternatives considered and rejected:**
- **Fold `reviews`/`provider_rating_summaries` into the existing `contact` module anyway**, since a Review
  anchors to a `ContactView`. Rejected — this would put two different Postgres schemas' tables in one Python
  module, a shape this codebase has never done and that the `administration`/`outcome_tags` precedent explicitly
  does not extend to (both of those examples share one schema across all their aggregate roots).

### Decision 2 — Two migrations: `reviews_domain` (the new schema + both tables), then `provider_average_rating_range_invariant` (the flagged `providers.average_rating` CHECK)

**The problem:** this story both creates the new Review domain and, per the Verified Current State's flagged gap,
should add a DB-level range check to an existing `provider.providers` column it starts writing to for the first
time.

**Chosen:** two separate migrations, on top of `e11a26e9560e`: (1) `reviews_domain` creates the `review` schema
and both `reviews`/`provider_rating_summaries` tables, full `CommonColumnsMixin` columns on each (soft-delete is
this codebase's default; `04_DATABASE.md`'s Soft Delete section exempts only `audit_logs`/`search_event_log`),
plus every FK/constraint/index named in the spec; (2) `provider_average_rating_range_invariant` adds
`chk_providers_average_rating_range CHECK (average_rating IS NULL OR average_rating BETWEEN 0 AND 5)` to
`provider.providers`, mirroring `c415258bcde2_provider_discoverability_invariant`'s own precedent of a small,
single-purpose, separately-named migration for one flagged invariant.

**Alternatives considered and rejected:**
- **One combined migration.** Rejected in favor of matching the existing separately-scoped-migration precedent
  (`provider_discoverability_invariant`) exactly, which keeps each migration's `revision`/docstring readable as
  one coherent change, and keeps the CHECK-constraint addition trivially revertable independent of the new
  domain's tables.

### Decision 3 — Rating-summary recalculation: a full recompute (`SELECT AVG/COUNT FROM reviews`) guarded by a `SELECT ... FOR UPDATE` lock on the `providers` row, never an incremental running-average update

**The problem:** AC4 requires `provider_rating_summaries` to be "recalculated in the same transaction as the
review write — never left stale," and this must be genuinely race-safe: two customers submitting a review for the
same provider concurrently must never produce a lost update (one write silently overwriting the other's
contribution). This is a fundamentally different shape of problem from every existing "atomic conditional write"
precedent in this codebase (`try_claim_for_account`/`try_claim_for_review`/`try_resolve`/`try_create`
(REV-001/ADR-049)) — those are all either a single-row status transition or an INSERT-uniqueness race, expressible
as one self-contained atomic statement. Recomputing an *average over an unbounded, growing set of rows* cannot be
expressed the same way.

**Chosen — full recompute, lock-guarded:**
1. Before writing the new `reviews` row, `ReviewService` calls a new `ProviderService.lock_for_rating_recalculation
   (provider_id) -> Provider`, which issues `SELECT * FROM provider.providers WHERE id = :id FOR UPDATE` (new
   `ProviderRepository.get_by_id_for_update`). Under Postgres, this acquires a row-level lock held for the rest of
   the transaction — any other concurrent transaction attempting the same lock (i.e., another review submission
   for the *same* provider) blocks until this transaction commits or rolls back. Reviews for *different* providers
   are entirely unaffected (the lock is per-row, not global).
2. `ReviewRepository.try_create(...)` inserts the new `reviews` row (an atomic `INSERT ... ON CONFLICT
   (contact_view_id) DO NOTHING ... RETURNING`, the exact ADR-049 pattern, guarding AC1's uniqueness constraint
   against a genuine double-submit race independently of the lock above).
3. `ReviewRepository.compute_rating_aggregate(provider_id)` runs `SELECT AVG(rating), COUNT(*) FROM review.reviews
   WHERE provider_id = :id` — now guaranteed correct and fresh, because step 1's lock means no concurrent
   transaction could have inserted (and left uncommitted) another review for this same provider in the window
   between the lock and this SELECT; any such concurrent attempt is still blocked waiting on the lock.
4. `ProviderRatingSummaryRepository.upsert(provider_id, average_rating, review_count)` — `INSERT ... ON CONFLICT
   (provider_id) DO UPDATE SET average_rating = EXCLUDED.average_rating, review_count = EXCLUDED.review_count,
   recalculated_at = now()`, writing the exact recomputed values from step 3 (safe for the same reason: any
   concurrent writer for this `provider_id` is still blocked on step 1's lock).
5. `ProviderService.apply_rating_recalculation(locked_provider, average_rating=..., review_count=...)` — a plain
   `provider_repository.update(...)` on the *already-locked* `Provider` object from step 1, writing the same
   recomputed values onto `providers.average_rating`/`review_count` (Decision "item 14" above's dual-write).
6. Single `await db.commit()` at the API layer, exactly as every other write path in this codebase — all five
   steps land in one transaction, satisfying AC4's literal wording.

**Alternatives considered and rejected:**
- **An incremental running-average update** (`new_avg = (old_avg * old_count + new_rating) / (old_count + 1)`,
  `new_count = old_count + 1`), expressed as a single atomic `UPDATE ... SET average_rating = (average_rating *
  review_count + :rating) / (review_count + 1), review_count = review_count + 1 WHERE provider_id = :id` (or the
  `INSERT ... ON CONFLICT DO UPDATE` equivalent). This *would* be race-safe on its own (Postgres serializes
  concurrent single-statement UPDATEs against the same row via the same row-locking mechanism, without needing an
  explicit prior `FOR UPDATE`) — but it was rejected on a **correctness-over-time**, not a race-safety, basis:
  `average_rating` is `NUMERIC(3,2)`, storing only two decimal digits. Every incremental step operates on the
  *already-rounded, stored* prior average rather than the exact sum of all raw ratings, so rounding error
  compounds with every subsequent review a provider ever receives — a provider with thousands of reviews over
  years could accumulate a materially wrong displayed average purely from repeated incremental rounding, which is
  unacceptable for a trust-facing number this platform's entire matching/ranking formula (`MAT-001`) also reads.
  A full recompute from the raw `rating` values has zero drift, always exactly matching a fresh `AVG()` over the
  real data, at the cost of one extra `SELECT` per review write — reviews are written far less often than they are
  read/ranked against, so this cost is immaterial.
- **No lock at all, relying on the uniqueness constraint alone.** Rejected — the uniqueness constraint (`ON
  CONFLICT DO NOTHING`) only protects against a *second write for the same `contact_view_id`*; it does nothing to
  serialize two *different* customers' concurrent reviews for the *same provider*, which is exactly the scenario
  that produces a lost update in the recompute step (see Verified Current State's `04_DATABASE.md` citation and
  the worked-through race in this Plan's own review). A lock is genuinely required here, not an optional
  belt-and-suspenders addition.
- **Locking `provider_rating_summaries`'s own row instead of `providers`.** Considered, and functionally
  equivalent once the summary row exists — but rejected as the *primary* lock target because the summary row does
  not exist yet for a provider's very first review, forcing a special-cased "lock-if-exists, else rely on the
  INSERT path's own atomicity" branch. Locking `providers` instead works uniformly for the first review and every
  subsequent one, since the `providers` row is guaranteed to already exist for any provider a Contact View could
  ever have been created against.
- **A database trigger recalculating `provider_rating_summaries` automatically on `reviews` INSERT.** Rejected —
  `08_CODING_STANDARDS.md`/this codebase's established practice puts all business logic in the service layer, not
  in triggers; every other "recalculated on write" behavior in this codebase (`providers.is_discoverable`,
  `verification_status`) is applied by an explicit service call, not a trigger, and there is no reason to
  introduce the first one here.

### Decision 4 — AC5's transitivity claim is proven by demonstrating the self-dealing Contact View never exists to anchor against, not by exercising a dedicated self-dealing check inside `ReviewService`

**The problem:** the story's own text asserts "this story's anchor requirement transitively blocks self-reviews
too, without needing a second explicit check" — this is a real claim about the codebase's actual behavior, not
just narrative framing, and AC5 requires an *automated test* that confirms it. Is it actually true given the real
code, and if so, how is it testable, given `ReviewService` itself never sees a self-dealing case to reject?

**Verified: the claim holds, and holds for a structural reason, not a coincidence.** `ContactService.
create_contact_view`'s self-dealing guard (`if provider.user_id is not None and provider.user_id ==
current_user_id: raise SelfDealingContactError()`) executes and raises **before** `contact_view_repository.create
(...)` is ever called (read directly, `backend/app/modules/contact/services/contact_service.py`). This means a
Contact View row where the contacting customer's Account is the same Account that owns the target Provider
**never exists in the database at all** — not "exists but flagged," not "exists but blocked from being reviewed,"
genuinely absent. `ReviewService.submit_review` always resolves its anchor via `ContactViewRepository.get_by_id`,
and every `ContactView` row that can ever be fetched by that call was, by construction, created by a customer
whose Account differs from the target Provider's owning Account. There is therefore no code path, no fixture, and
no attacker-controlled input that could ever produce a `Review` row whose `customer_id`'s owning Account matches
its own `provider_id`'s owning Account — this is unreachable by construction, not merely unreachable by an
additional runtime check this story would add.

**Chosen test shape:** because the unreachable state cannot be directly constructed and then "rejected" by
`ReviewService` (there is nothing for it to reject — the anchor itself never exists), AC5's automated test proves
the transitivity end-to-end, inside `REV-002`'s own test suite (not merely relying on `CON-001`'s separate test
file continuing to pass): construct the exact dual-role fixture `CON-001`'s own `TestSelfDealingRejection` uses
(one Account holding both a `customer_profiles` row and a `providers` row it owns), attempt `ContactService.
create_contact_view` against that provider (asserts `SelfDealingContactError`, zero `contact_views` rows written —
this reconfirms CON-001's guard is still in force, the load-bearing precondition), then attempt `ReviewService.
submit_review` against a **fabricated, never-created** `contact_view_id` for that same (customer, provider) pair
and assert it raises `ContactViewNotFoundError` (the correct outcome for "this contact view was never created," a
404, not a self-dealing-specific error) with zero `reviews` rows written. This is an honest test of the real
mechanism (there being nothing to anchor against), not a test dressed up to look like it exercises a self-dealing
check that doesn't exist in `ReviewService` at all — the Plan's own reasoning above is the test's documented intent
in comments, so a future reader understands why the assertion is `ContactViewNotFoundError`, not some
`SelfReviewError` that this story deliberately does not create (per the story's own explicit "without needing a
second explicit check" instruction).

**Alternatives considered and rejected:**
- **Add a redundant, explicit self-dealing check inside `ReviewService` anyway**, mirroring `ContactService`'s own
  guard, "just to be safe." Rejected — the story's own verbatim text explicitly instructs against this ("without
  needing a second explicit check"), and adding one would contradict the Plan's own AC5 verification strategy
  (there would be nothing left to prove was "already blocked transitively" if a second, independent block also
  existed) while adding an unrequested, duplicate cross-module lookup (`ReviewService` would need to know how to
  resolve a Provider's owning Account, a concern this story otherwise never needs).

### Decision 5 — Anchor-verification rejection is a new `ReviewAnchorNotVerifiedError` (409), ownership rejection reuses the existing `ContactViewNotFoundError` (404), uniqueness rejection is a new `ReviewAlreadyExistsError` (409)

**The problem:** AC2 requires two independently rejectable conditions (ownership, anchor validity) plus AC1's
uniqueness constraint — three different rejection reasons needing three (not necessarily new) exception shapes.

**Chosen:**
- **Ownership** (`contact_view_id` doesn't exist, or isn't owned by the calling customer): reuse
  `ContactViewNotFoundError` verbatim (404) — this is the exact same check, on the exact same resource, that
  `OutcomeTagService.submit_outcome_tag` already performs; inventing a second, differently-named 404 for an
  identical condition would be pure duplication.
- **Anchor validity** (`outcome_tags` row missing, or `hired=false`): new `ReviewAnchorNotVerifiedError` (409) —
  see Verified Current State's precedent citation (`VerificationSubmissionNotAllowedError`/
  `VerificationRecordNotActionableError`/`ManualMatchAssignmentAlreadyResolvedError`'s "resource exists, state
  blocks the write" 409 family). One exception covers both the "no outcome tag at all" and "`hired=false`" cases
  — AC2's own wording treats them identically ("attempting otherwise (no outcome tag, or `hired=false`) is
  rejected"), so no finer-grained distinction is warranted.
- **Uniqueness** (a second review attempted against an already-reviewed `contact_view_id`): new
  `ReviewAlreadyExistsError` (409) — mirrors `OutcomeTagAlreadyExistsError`/`ClaimAlreadyClaimedError`'s identical
  shape (a genuine timing conflict on an atomic `ON CONFLICT DO NOTHING ... RETURNING` insert, per Decision 3
  step 2).

**Alternatives considered and rejected:**
- **A single generic `ReviewNotAllowedError` covering both the anchor-validity and uniqueness cases.** Rejected —
  collapsing "you already reviewed this" (a genuine one-time-only state, arguably worth a distinct client-facing
  message: "you've already reviewed this") with "this contact view was never a positive outcome" (a completely
  different reason, with a different corrective action — nothing, since it can never become reviewable) would
  make the mobile client's error-mapping logic unable to distinguish two meaningfully different states, which no
  other exception in this codebase's history has ever done deliberately.

### Decision 6 — Rating is validated at three independent layers (Pydantic schema, DB `CHECK`, `SMALLINT` column type), each redundant with the others by design

**The problem:** AC3 requires rating to be constrained to 1–5. Where should this be enforced?

**Chosen:** all three: `SubmitReviewRequest.rating: int = Field(..., ge=1, le=5)` (the first, cheapest rejection,
a 422 before any DB round trip), `chk_reviews_rating_range CHECK (rating BETWEEN 1 AND 5)` (already `04_DATABASE.
md`'s own documented constraint — defense-in-depth against any future direct-DB or bulk-import write bypassing
the API layer), and `SMALLINT` (rules out absurd out-of-range magnitudes at the storage-type level, though this
alone doesn't constrain to 1–5). This mirrors this codebase's own established "schema-level `CHECK` as defense
in depth, not a replacement for application-layer validation" posture (`chk_providers_discoverable_requires_
approved`, VER-002).

**Alternatives considered and rejected:**
- **Pydantic validation only, no DB `CHECK`.** Rejected — `04_DATABASE.md`'s spec already names
  `chk_reviews_rating_range` explicitly; skipping it here would be an unexplained deviation from a pre-existing,
  cited spec for no benefit.

### Decision 7 — Mobile: Write-a-Review lives in the existing `provider_profile` feature, triggered from `ProviderProfileScreen` reading `OutcomeTagPromptController`'s post-close state — no change to the already-shipped `OutcomeTagPromptSheet`/`OutcomeTagPromptController` themselves

**The problem:** AC6 requires the Write-a-Review screen to be reachable *only* after a "Yes" outcome tag, with no
other navigation path to it. Where does the trigger live, and does it require touching REV-001's already-shipped,
already-tested sheet/controller?

**Chosen:** extend `ProviderProfileScreen._onContactTap` (already flagged once, by REV-001 itself, as a
touch-point that grows with each story in this flow) with one more step, mirroring its own existing shape exactly:
after `await OutcomeTagPromptSheet.show(...)` resolves (the sheet has closed, by any means), read
`ref.read(outcomeTagPromptControllerProvider(reveal.id))`. If `state.status == OutcomeTagPromptStatus.submitted &&
state.lastHired == true`, `context.push(AppRoutes.writeReview, extra: WriteReviewArgs(contactViewId: reveal.id,
providerId: reveal.providerId, providerDisplayName: reveal.providerDisplayName, providerPhotoUrl:
providerPhotoUrl))`. Any other outcome (`hired == false`, an unrecoverable error the customer backed out of, or
"Maybe later") does nothing further — the sheet's own existing "Thanks!" auto-close behavior (for a `hired=false`
submission) is completely untouched. `OutcomeTagPromptSheet`/`OutcomeTagPromptController` themselves are **not
modified at all** — `lastHired` already exists on the controller's state specifically to support exactly this kind
of post-submission branching (today it only powers the retry-on-error path, but its shape already fits this new
use unmodified). This satisfies AC6 structurally: `AppRoutes.writeReview` is only ever pushed from this one call
site, which itself is only reached after a real `hired=true` submission — there is no button, deep link, or menu
item anywhere else in the app that navigates there.

**Alternatives considered and rejected:**
- **Handle the branch inside `OutcomeTagPromptSheet`'s own `ref.listen` callback** (e.g., on `submitted` with
  `lastHired == true`, skip the "Thanks!" content and push the new screen directly from inside the sheet).
  Rejected — this would require modifying REV-001's already-shipped, already-tested sheet/controller internals
  (the `ref.listen` callback, the `_ConfirmationContent`/auto-close-timer logic) for a concern (`review`-domain
  navigation) that sheet has no other reason to know about, when the exact same "await the sheet's close, then
  read its final controller state" shape is already proven and untouched-elsewhere at the *screen* level
  (Decision 6, `Plan_S09_REV-001.md`). Keeping the branch at the screen level, one level up, is the smaller, more
  consistent diff, and leaves a `hired=true` customer briefly seeing the existing "Thanks!" confirmation before
  the Write-a-Review screen opens — an acceptable, arguably nicer, sequencing rather than a regression.
- **A new standalone `mobile/lib/features/review/` feature.** Rejected — `15_SCREEN_INVENTORY.md` groups S-10
  under the identical "Customer — Core Loop — Flow 4" heading as S-09/the two existing sheets, all of which
  already live in `features/provider_profile/`; splitting one continuous flow across two feature directories for
  a single new screen has no isolation benefit and would create the exact kind of fragmentation `13_OPEN_
  DECISIONS.md` item 12 already flags as a cross-feature-coupling risk in the opposite direction (avoidable
  fragmentation of one cohesive flow, not reuse of a shared concern).
- **A full-screen route reached via deep link only, with no `context.push` chain.** Rejected — AC6 requires *no*
  direct navigation path to exist at all, which a bare deep link (even an unlisted one) would technically provide;
  the chosen design has no route registered anywhere except this one conditional call site.

---

## Backend — Proposed Changes

1. **New Alembic migration `reviews_domain`** (on top of `e11a26e9560e`): `CREATE SCHEMA review`; creates
   `review.reviews` and `review.provider_rating_summaries`, full `CommonColumnsMixin` columns on each, plus every
   column/FK/constraint/index named in `04_DATABASE.md`'s spec (Verified Current State) — `uq_reviews_contact_
   view_id`, `chk_reviews_rating_range`, `idx_reviews_provider_id` on `reviews`; `uq_provider_rating_summaries_
   provider_id` on `provider_rating_summaries`.
2. **New Alembic migration `provider_average_rating_range_invariant`** (Decision 2): adds
   `chk_providers_average_rating_range CHECK (average_rating IS NULL OR average_rating BETWEEN 0 AND 5)` to
   `provider.providers`.
3. **New file `backend/app/modules/review/__init__.py`**, **`models.py`**: `Review(CommonColumnsMixin, Base)`
   (`__tablename__="reviews"`, `contact_view_id` FK unique, `customer_id` FK, `provider_id` FK, `rating`
   `SMALLINT` not null, `comment` `TEXT` nullable) and `ProviderRatingSummary(CommonColumnsMixin, Base)`
   (`__tablename__="provider_rating_summaries"`, `provider_id` FK unique, `average_rating` `NUMERIC(3,2)` not
   null default `0`, `review_count` `INTEGER` not null default `0`, `recalculated_at` `TIMESTAMPTZ` not null).
4. **New file `backend/app/modules/review/repositories/review_repository.py`** —
   `ReviewRepository(BaseRepository[Review])`:
   - `try_create(values: dict) -> Review | None` — Decision 3 step 2's atomic `INSERT ... ON CONFLICT
     (contact_view_id) DO NOTHING ... RETURNING`.
   - `compute_rating_aggregate(provider_id: UUID) -> tuple[Decimal, int]` — Decision 3 step 3's `SELECT
     AVG(rating), COUNT(*) FROM reviews WHERE provider_id = :id` (returns `(Decimal("0.00"), 0)` if no rows
     exist yet — should not occur mid-write since this always runs immediately after a successful insert, but
     handled honestly rather than assuming `AVG()`'s `NULL` result away).
5. **New file `backend/app/modules/review/repositories/provider_rating_summary_repository.py`** —
   `ProviderRatingSummaryRepository(BaseRepository[ProviderRatingSummary])`: `upsert(provider_id, *,
   average_rating, review_count) -> ProviderRatingSummary` — Decision 3 step 4's `INSERT ... ON CONFLICT
   (provider_id) DO UPDATE SET average_rating = EXCLUDED.average_rating, review_count = EXCLUDED.review_count,
   recalculated_at = now() ... RETURNING`.
6. **New file `backend/app/modules/review/services/review_service.py`** —
   `ReviewService.submit_review(current_user_id, *, contact_view_id, rating, comment) -> Review`:
   1. Resolve the caller's `customer_profiles` row (`CustomerProfileNotFoundError` if missing, defensive,
      mirrors `OutcomeTagService`/`ContactService`).
   2. Resolve the `ContactView` via `ContactViewRepository.get_by_id`; `ensure_owner_or_not_found(contact_view.
      customer_id if contact_view is not None else None, customer_profile.id, not_found_exc=
      ContactViewNotFoundError())` (Decision 5).
   3. Resolve the `OutcomeTag` via the new `OutcomeTagRepository.get_by_contact_view_id(contact_view_id)`; raise
      `ReviewAnchorNotVerifiedError` if `None` or `hired is False` (Decision 5).
   4. `locked_provider = await self.provider_service.lock_for_rating_recalculation(contact_view.provider_id)`
      (Decision 3 step 1).
   5. `review = await self.review_repository.try_create({"contact_view_id": contact_view_id, "customer_id":
      customer_profile.id, "provider_id": contact_view.provider_id, "rating": rating, "comment": comment})`; if
      `None`, raise `ReviewAlreadyExistsError` (Decision 3 step 2/Decision 5).
   6. `average_rating, review_count = await self.review_repository.compute_rating_aggregate(contact_view.
      provider_id)` (Decision 3 step 3).
   7. `await self.provider_rating_summary_repository.upsert(contact_view.provider_id, average_rating=
      average_rating, review_count=review_count)` (Decision 3 step 4).
   8. `await self.provider_service.apply_rating_recalculation(locked_provider, average_rating=average_rating,
      review_count=review_count)` (Decision 3 step 5).
   9. Return `review`.
7. **`backend/app/modules/contact/repositories/outcome_tag_repository.py`** — add
   `get_by_contact_view_id(contact_view_id: UUID) -> OutcomeTag | None`, a plain `SELECT ... WHERE contact_view_id
   = :id` (the read-only counterpart to `try_create`, needed by `ReviewService`, step 3 above).
8. **`backend/app/modules/provider/repositories/provider_repository.py`** — add `get_by_id_for_update(provider_id:
   UUID) -> Provider | None`, `select(Provider).where(Provider.id == provider_id).with_for_update()` (Decision 3
   step 1).
9. **`backend/app/modules/provider/services/provider_service.py`** — add two new methods:
   - `lock_for_rating_recalculation(provider_id) -> Provider` — thin wrapper over `get_by_id_for_update`, raising
     `ProviderNotFoundError` if missing (defensive; should not occur, since `provider_id` is always resolved from
     an already-loaded `ContactView`).
   - `apply_rating_recalculation(provider: Provider, *, average_rating: Decimal, review_count: int) -> Provider`
     — a plain `provider_repository.update(provider, {"average_rating": average_rating, "review_count":
     review_count})`, mirroring `apply_verification_outcome`'s identical shape (same "already-resolved row,
     partial-field update" pattern).
10. **New file `backend/app/modules/review/schemas.py`** — `SubmitReviewRequest` (`rating: int = Field(..., ge=1,
    le=5)`, `comment: str | None = Field(None, max_length=2000)` — a defensive cap mirroring this codebase's
    other free-text fields' bounded lengths, not itself an AC requirement) and `ReviewResponse` (`id`,
    `contact_view_id`, `provider_id`, `rating`, `comment`, `created_at`).
11. **New file `backend/app/modules/review/api.py`** — `router = APIRouter(tags=["Review"])`; `POST
    /{contact_view_id}/review` (mounted at `prefix="/contact-views"` in `v1/api.py`, mirroring `verification_
    router`'s identical separate-module-shared-prefix shape), `require_role(ROLE_CUSTOMER)`, 201 on success,
    documented 404 (ownership)/409 (anchor not verified, or already reviewed) responses.
12. **New file `backend/app/modules/review/dependencies.py`** — `get_review_repository`, `get_provider_rating_
    summary_repository`, `get_review_service` (wires the two new repositories plus the existing `contact.
    ContactViewRepository`/`contact.OutcomeTagRepository` (raw, same justification `ContactService`/
    `OutcomeTagService` already established for these exact repositories — no equivalent read primitive exists on
    a `ContactService`), `customer.CustomerProfileRepository` (raw, same precedent), and `provider.ProviderService`
    (service-only edge, per ADR-047, for the two new lock/apply methods) — each cross-module edge's justification
    named explicitly in this file's own docstring, per ADR-047's own stated expectation.
13. **`backend/app/api/v1/api.py`** — `v1_router.include_router(review_router, prefix="/contact-views")`.
14. **`backend/app/core/exceptions/exceptions.py` + `__init__.py`** — new `ReviewAnchorNotVerifiedError` (409,
    Decision 5) and `ReviewAlreadyExistsError` (409, Decision 5).

### Tests

15. `backend/tests/modules/review/test_review_service.py`:
    - Happy path: a real Contact View with a `hired=true` outcome tag, rating 1–5 both with and without a
      comment, asserting the returned `Review`, a direct row-count check (exactly one `reviews` row), and that
      `provider_rating_summaries` now has a matching row with the correct `average_rating`/`review_count`
      (AC1/AC3/AC4/AC7).
    - AC2/Decision 5 rejection cases, each a separately-named test (not parameterized into one, mirroring
      REV-001's own AC6 discipline): no outcome tag at all (`ReviewAnchorNotVerifiedError`, zero `reviews` rows);
      `hired=false` (`ReviewAnchorNotVerifiedError`, zero rows); a different customer's Contact View
      (`ContactViewNotFoundError`, zero rows); a nonexistent `contact_view_id` (`ContactViewNotFoundError`).
    - AC1 uniqueness: a second `submit_review` against the same, already-reviewed `contact_view_id` raises
      `ReviewAlreadyExistsError`, with a direct row-count assertion confirming exactly one `reviews` row still
      exists.
    - AC3: rating `0` and rating `6` both rejected by the Pydantic schema layer (a separate schema-level test);
      the DB `CHECK` is exercised directly via a raw insert bypassing the service layer, confirming the
      constraint itself (not just the application-layer validation) rejects an out-of-range value.
    - **AC4/Decision 3 recalculation correctness**: multiple reviews for the same provider recompute the correct
      running average/count each time (e.g. ratings 5, 3, 4 → average `4.00`, count `3` after the third); a
      **genuine concurrency test**, mirroring REV-001's own AC1/AC6 concurrency test shape (two independent
      DB sessions/transactions submitting reviews for the *same* provider at overlapping times), asserting the
      final `provider_rating_summaries`/`providers.average_rating`/`review_count` values reflect *both* reviews
      correctly (not a lost update) — this is the test that actually exercises Decision 3's lock, not merely
      "the two calls happened not to overlap in practice."
    - **AC4's "same transaction" claim**: a review write raising after the `reviews` INSERT but before the
      recalculation completes (e.g. by injecting a failure) leaves *both* the `reviews` row and any partial
      `provider_rating_summaries`/`providers` write rolled back together — confirms there is no partial-write
      window, not just that the happy path recalculates correctly.
    - **AC5/Decision 4**: the dual-role self-dealing fixture, confirming `SelfDealingContactError` on the
      `ContactService.create_contact_view` attempt (zero `contact_views` rows) and `ContactViewNotFoundError` on
      a subsequent `ReviewService.submit_review` attempt against a fabricated `contact_view_id` for that same
      pairing (zero `reviews` rows) — both assertions in one test, telling the transitivity story end to end.
16. `backend/tests/modules/review/test_review_api.py` — full HTTP round trip: 201 happy path, 404 (ownership),
    409 (anchor not verified; already reviewed), 401 unauthenticated, 403 wrong role, 422 (rating out of range).
17. `backend/tests/modules/contact/test_outcome_tag_repository.py` (or extend the existing service test file) —
    `get_by_contact_view_id` returns the correct row, and `None` for a nonexistent one.
18. `backend/tests/modules/provider/test_provider_service.py` (or repository-level equivalent) — `get_by_id_for_
    update`/`lock_for_rating_recalculation` return the correct row; `apply_rating_recalculation` writes both
    fields correctly and leaves every other `providers` column untouched.
19. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

No new mobile dependency is required — a star-rating input is five tappable `Icon(Icons.star / Icons.star_border)`
widgets, no new package.

1. **`mobile/lib/features/provider_profile/`** (Decision 7 — continuing the same Flow 4 feature, not a new one):
   - `domain/models/review.dart` — parses `POST .../review`'s response.
   - `domain/models/review_exception.dart` — mirrors `outcome_tag_exception.dart`'s shape (`notFound`,
     `anchorNotVerified`, `alreadyExists`, `network`, `unknown`).
   - `domain/models/write_review_args.dart` (`WriteReviewArgs`) — `contactViewId`, `providerId`,
     `providerDisplayName`, `providerPhotoUrl` — the new screen's navigation arguments, mirroring `provider_
     profile_args.dart`'s existing shape.
   - `data/provider_profile_repository.dart` — add `submitReview({required String contactViewId, required int
     rating, String? comment})`, calling `POST /contact-views/$contactViewId/review`, mapping errors via a new
     `_mapReviewError` (same shape as `_mapOutcomeTagError`). Added to the existing repository class (this
     feature's fourth small endpoint), not a new one.
   - `state/write_review_controller.dart` (Riverpod, `family` keyed by `contact_view_id`) — owns the submit
     action's own rating/comment/loading/error/submitted state, kept separate from every other controller in this
     feature, per this codebase's established "each screen/sheet's own in-flight state doesn't couple to
     another's" principle.
   - `presentation/screens/write_review_screen.dart` (`WriteReviewScreen`, S-10) — provider name/photo, a
     `_StarRatingInput` (five tappable stars, 1–5, no default selection so submission is disabled until a rating
     is chosen), a multi-line optional comment `TextField`, a Submit `PrimaryButton` (disabled while no rating is
     selected or a submission is in flight), and a success state that pops back to `ProviderProfileScreen` with a
     brief confirmation (mirrors the "Thanks!" pattern already used, reused here as this screen's own final
     state, not the sheet's).
2. **`mobile/lib/core/routing/app_routes.dart`** — add `static const String writeReview = '/write-review';`.
3. **`mobile/lib/core/routing/app_router.dart`** — add a `GoRoute(path: AppRoutes.writeReview, builder: (context,
   state) => WriteReviewScreen(args: state.extra as WriteReviewArgs))`.
4. **`mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart`** —
   `_onContactTap` extended per Decision 7: after `await OutcomeTagPromptSheet.show(...)` resolves, read
   `outcomeTagPromptControllerProvider(reveal.id)`'s state; if `submitted && lastHired == true`, `context.push
   (AppRoutes.writeReview, extra: WriteReviewArgs(...))`.
5. **`mobile/lib/l10n/app_en.arb` / `app_ar.arb`** — new keys: `writeReviewTitle`, `writeReviewRatingLabel`,
   `writeReviewCommentLabel` (optional-field hint), `writeReviewSubmitLabel`, `writeReviewThanksMessage`.

### Tests

6. `mobile/test/features/provider_profile/` — controller tests for `WriteReviewController` (submit success with
   and without a comment, error mapping for each `ReviewException` type, submit disabled with no rating selected
   — asserted via the repository mock never being invoked); widget tests for `WriteReviewScreen` (provider
   name/photo rendered, star input selects 1–5 and updates visible state, Submit disabled until a rating is
   chosen, successful submission pops back).
7. `provider_profile_screen_test.dart` — updated to assert: after a `hired=true` Outcome Tag Prompt submission,
   `AppRoutes.writeReview` is pushed with the correct `WriteReviewArgs`; after a `hired=false` submission, or a
   "Maybe later" dismiss, or an unrecoverable-error dismissal, it is **not** pushed (AC6's "no other path"
   assertion, exercised as an explicit negative case, not just the happy path).
8. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **Provider-side display of reviews beyond the rating summary recalculation** — the story's own literal scope
  boundary. No "list of reviews" screen, no provider-facing reviews management surface, no display of `comment`
  text anywhere in this story's own mobile scope.
- **A dedicated, redundant self-dealing check inside `ReviewService`** — Decision 4's explicit reasoning; the
  anchor requirement already makes this unreachable, and the story's own text instructs against a second check.
- **Editing or deleting a submitted Review** — no AC requests this; `reviews.contact_view_id`'s uniqueness
  constraint and this story's `ReviewService` surface (`submit_review` only) make a Review a one-shot write,
  mirroring `OutcomeTag`'s own immutability precedent (REV-001, Decision 4).
- **Any Review-triggered `Notification`** — `03_DOMAIN_MODEL.md`'s Notification domain does not name a Review
  event among its three enumerated triggers; not invented here.
- **Comment content moderation/profanity filtering** — no AC requests it; the only bound applied is a plain
  length cap (Backend Proposed Changes item 10), not content inspection.
- **Reworking `MAT-001`'s ranking formula or `ProviderSearchRepository.search_nearby`'s SQL** — it continues
  reading `providers.average_rating`/`review_count` exactly as today; this story only becomes the first real
  writer of those columns, per Decision "item 14" above.
- **A "My Activity" (S-11) "Reviewed" filter chip, or any other cross-screen surfacing of "have I reviewed this
  provider"** — S-11 is a separate, unscoped screen; not touched here.

---

## Open Questions (flagged for CTO awareness — do not block `backend`/`frontend` from starting)

1. **Decision 3's lock-based recalculation mechanism.** This is a genuinely new correctness pattern for this
   codebase (a `SELECT ... FOR UPDATE` held across a multi-statement critical section, rather than a single
   atomic conditional statement) — flagged for awareness as the first of its kind, even though it is a
   straightforward, standard Postgres technique. Confirm no preference for the incremental-update alternative
   (Decision 3's own rejected alternative) despite its rounding-drift risk over a provider's long-term review
   history.
2. **The `04_DATABASE.md` doc correction** (Verified Current State) — the existing "REV-001, as the first real
   writer of this column" note should read "REV-002." Flagged to fix at this story's own closeout doc-update
   pass, not urgent on its own.
3. **`comment`'s 2000-character cap** (Backend Proposed Changes item 10) — a defensive default, not requested by
   any AC or existing spec. Confirm acceptable, or flag a different limit.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

1. **backend** — Backend Proposed Changes items 1–19. Build order: (a) both migrations first (items 1–2); (b) the
   new `review` module's model/repositories/service/schemas/route (items 3–14), with Decision 3 (recalculation
   race-safety) and Decision 4/5 (anchor verification + exception shapes) built and tested together first, since
   they are this story's two safety-critical mechanisms (mirroring how REV-001 called out its own two such
   pieces); (c) the small additions to `contact`'s `OutcomeTagRepository` and `provider`'s
   `ProviderRepository`/`ProviderService` (items 7–9) as they're needed by (b), not as an afterthought. Read
   Decision 3 and Decision 4 in full before starting.
2. **frontend** — Frontend Proposed Changes items 1–8. Should start once `backend`'s new `POST .../review`
   endpoint is available to integrate against (or in parallel against this Plan's documented response shape, per
   this codebase's established parallelization practice), with a final integration pass once both are done.
3. **tester** — verify all 7 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget tests).
   Particular attention to: AC1 (a genuine concurrent-submission-shaped test proving `reviews.contact_view_id`'s
   `ON CONFLICT` mechanism actually rejects a second insert, plus a direct row-count assertion); AC2 (both
   rejection shapes — missing outcome tag, and `hired=false` — each as its own test, plus the ownership-rejection
   case, confirming zero rows written in every case); AC3 (schema-level 422 for out-of-range rating, plus a
   direct raw-insert test proving the DB `CHECK` itself rejects an out-of-range value bypassing the API layer);
   AC4 (the **concurrency test** is the load-bearing one here — confirm it genuinely exercises two overlapping
   transactions, not merely two sequential calls that happen to pass, and confirm the "same transaction" rollback
   test genuinely leaves no partial write); AC5 (the dual-role fixture, confirming both the `SelfDealingContactError`
   on the Contact View attempt and `ContactViewNotFoundError` on the review attempt, with zero rows at each step);
   AC6 (the mobile screen test's explicit negative case — `hired=false`/dismissal does NOT navigate to
   Write-a-Review); AC7 (confirm both the anchor-rejection and recalculation-correctness tests exist as distinct,
   separately-named test cases, per this codebase's established AC6/AC7-literal-wording discipline).
4. **architect** — review Decision 1's module-placement choice against `02_ARCHITECTURE.md`'s actual
   one-schema-one-module default (confirm the new standalone `review` module is correctly justified, not
   over-fragmented); Decision 3's lock mechanism for genuine correctness under concurrency (confirm no window
   exists where the `FOR UPDATE` lock could be bypassed, held too briefly, or where a deadlock could arise from
   lock-ordering across this new code path and any existing one that also locks a `providers` row); Decision 4's
   AC5 reasoning and test shape (confirm the "unreachable by construction" claim is airtight, not merely
   "unlikely"); Decision 5's exception/status-code choices against `06_SECURITY.md`/ADR-015 (confirm no
   information leak, confirm 409 vs. 404 vs. 403 choices are each correctly reasoned); the new cross-module edges
   in `review/dependencies.py` against ADR-047 (confirm each raw-repository edge is genuinely justified, not a
   silently-assumed shortcut).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decisions 1–7 as new ADRs (next available: **ADR-051** onward), grouped where several decisions share
     one architectural theme, at `tech-lead`'s discretion at closeout.
   - Update `04_DATABASE.md` to note `reviews`/`provider_rating_summaries` are now shipped (cross-reference this
     Plan/Walkthrough), fix the "REV-001" → "REV-002" attribution slip (Open Question 2), and resolve
     `13_OPEN_DECISIONS.md` item 14 to `Resolved` with the affirmative answer this Plan already reasons through.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 9 section and `docs/AI/SESSION_HANDOFF.md` — `REV-002`
     becomes Done, Milestone ML9 becomes fully complete (both its stories done).

---

## Verification Plan (mapped to the 7 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | The real migration (item 1) plus `test_review_service.py`'s uniqueness test (a second `submit_review` against an already-reviewed `contact_view_id` is rejected, with a direct row-count assertion confirming exactly one `reviews` row exists) and its genuine concurrent-submission test. |
| 2 | `test_review_service.py`'s three separately-named rejection cases (no outcome tag, `hired=false`, not-owned/nonexistent contact view) plus `test_review_api.py`'s matching 404/409 HTTP cases, each asserting zero `reviews` rows written. |
| 3 | `test_review_api.py`'s 422 (rating out of range via the schema), plus a direct raw-insert test against the DB `CHECK` constraint bypassing the API layer entirely, plus a test confirming `comment=None` succeeds. |
| 4 | `test_review_service.py`'s recalculation-correctness test (multiple sequential reviews produce the correct running average/count) and its genuine two-overlapping-transaction concurrency test (Decision 3), plus the same-transaction rollback test proving no partial-write window exists. |
| 5 | `test_review_service.py`'s dual-role fixture test (Decision 4): `SelfDealingContactError` on the Contact View attempt, `ContactViewNotFoundError` on the subsequent review attempt against a fabricated `contact_view_id`, zero rows at each step. |
| 6 | `provider_profile_screen_test.dart`'s positive case (a `hired=true` submission pushes `AppRoutes.writeReview` with the correct args) and its explicit negative cases (`hired=false`, "Maybe later," and an unrecoverable-error dismissal all do **not** push it) — plus a static confirmation that `AppRoutes.writeReview` is registered with no other call site anywhere in the app. |
| 7 | AC2's and AC4's test cases above are each present as explicit, separately-named test cases (not merged into one parameterized test), satisfying AC7's literal wording directly. |

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` (Review domain — the exact business rules this Plan implements: anchor-verified,
  transitive self-dealing block, merit-ranking driver)
- `docs/AI/04_DATABASE.md` (Review Domain — `reviews`/`provider_rating_summaries`'s full spec; `providers.
  average_rating`/`review_count`, lines 405–406, this story's first real write path)
- `docs/AI/09_DECISIONS.md` (ADR-015 — the `{id}`-addressable-collection-always-404 convention Decision 5 reuses
  for ownership; ADR-044 — the self-dealing 403 shape Decision 4 relies on transitively, without reusing its
  status code; ADR-047 — the services-only cross-module convention this story's `review` module continues to
  follow; ADR-049 — the `ON CONFLICT DO NOTHING ... RETURNING` uniqueness pattern Decision 3 step 2 reuses
  directly)
- `docs/AI/13_OPEN_DECISIONS.md` (item 14 — this story's own resolution, recorded in the affirmative)
- `docs/AI/14_USER_FLOWS.md` (Flow 4 — the Write-a-Review step this Plan's Decision 7 implements)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-10 — the screen this Plan's mobile work builds, and its Flow-4 grouping
  Decision 7's module-placement choice relies on)
- `docs/implementation/plans/Plan_S09_REV-001.md` / `Walkthrough_S09_REV-001.md` (`outcome_tags`'s shipped shape,
  the `OutcomeTagPromptSheet`/`OutcomeTagPromptController` this story's mobile trigger reads without modifying,
  and the atomic-`ON CONFLICT`-insert precedent Decision 3 extends)
- `docs/implementation/plans/Plan_S08_CON-001.md` / `Walkthrough_S08_CON-001.md` (the self-dealing guard Decision
  4's entire reasoning depends on; `ContactService`/`ProviderService.get_for_public_profile`)
- `docs/implementation/plans/Plan_S08_MAT-001.md` (Decision 2 — the `providers.average_rating`/`review_count`
  rating-source substitution this story's Decision "item 14" resolution builds on top of, without modifying)
- `docs/implementation/plans/Plan_S05_VER-002.md` (`chk_providers_discoverable_requires_approved`, the DB-`CHECK`
  -as-defense-in-depth precedent Decision 6 mirrors; `c415258bcde2_provider_discoverability_invariant`, the
  separately-scoped-migration precedent Decision 2 mirrors)

---

**End of Document**
