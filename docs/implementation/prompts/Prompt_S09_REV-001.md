# Prompt for Story REV-001 — Tell the Platform Whether I Hired a Provider

**Sprint:** 09 | **Epic:** ML9-EP01 | **Milestone:** ML9 | **Phase:** PH2 | **Priority:** High | **Depends On:**
CON-001 (done, Sprint 8)

## Instruction given to `tech-lead`

Start Story REV-001 in the AI Marketplace repository, branch `claude/provider-storefront-pro-001-qnicuj`. This
follows the established cycle: tech-lead plans → backend/frontend implement → tester → architect → CTO sign-off
→ closeout → tracker sync. Read `docs/AI/SESSION_HANDOFF.md` first for current project state and standing
process, then the relevant `docs/AI/` files for this story, in numerical order.

## Story (verbatim, `Project_Tracker.xlsx`, `REV-001` row)

Title: Tell the platform whether I hired a provider
Sprint ID: SP09 | Epic Code: ML9-EP01 | Milestone ID: ML9 | Phase ID: PH2 | Priority: High
Depends On: CON-001 (done)

Description: "As a customer who contacted a provider, I want to quickly confirm whether I hired them, so that the
platform has a real signal of what actually happened without tracking payment details it has no visibility into.
The Outcome Tag is the platform's only conversion signal given the offline-payment reality of the direct-contact
model. It is deliberately minimal — a yes/no tied to a specific Contact View — and only the Customer who
generated that Contact View may submit it. Scope boundary: does not include the review itself (REV-002), which
requires a 'Yes' outcome tag as its anchor."

Acceptance Criteria (verbatim, 6 items):
1. `outcome_tags` table exists via migration, with a unique constraint on `contact_view_id` (one outcome tag per
   Contact View).
2. Only the Customer who owns the underlying Contact View can submit an outcome tag for it — attempting to
   submit for someone else's Contact View is rejected.
3. The prompt ("Did you hire them?") is triggered after a Contact View, via a notification, and is dismissible
   ("Maybe later") without penalty.
4. The outcome tag does not attempt to capture payment amount, job completion detail, or scheduling.
5. A "No" or absent outcome tag is still retained as a signal (not discarded) — it is not required to be "Yes"
   for the tag itself to exist, only for a Review to follow.
6. Automated tests cover the ownership restriction and the uniqueness-per-Contact-View constraint.

`REV-002` (next story, depends on `REV-001`, **not** part of this story's scope) will build
`reviews`/`provider_rating_summaries` anchored on a "Yes" outcome tag — nothing from that domain is built here.

## Context supplied for planning

- `CON-001` just shipped (`contact_views` + the self-dealing guard, ADR-044/045/046/047) — its dependency
  requirement is satisfied. `contact_views` already exists exactly per `04_DATABASE.md`'s spec, no deviation.
- `outcome_tags` is already fully spec'd in `04_DATABASE.md`'s Contact Domain section (same `contact` Postgres
  schema `contact_views` lives in): `contact_view_id` (unique FK), `hired` (boolean, not null), `submitted_at`.
  Confirm this directly before building anything.
- AC2's ownership check is the same shape of problem CON-001's `search_request_id` ownership validation
  (Decision 4, ADR-015's "always 404, never 403" convention) already solved — read `ContactService` directly for
  the established pattern, and contrast against CON-001's self-dealing guard's 403 (a different, identity-based
  shape, not directly reusable here).
- Check whether `outcome_tags` should live in a new Python module or the existing `contact` module — the
  `administration` module's own precedent (`AdminActionLog`/`ClaimReviewRequest`/`ManualMatchAssignment`, three
  aggregate roots, one Postgres schema, one Python module, added incrementally across three different stories) is
  directly relevant prior art.
- AC3's notification-trigger mechanism needs a real design decision: read `14_USER_FLOWS.md` Flow 4 step 13 and
  the Notification Triggers table, `03_DOMAIN_MODEL.md`'s Outcome Tag section, and `15_SCREEN_INVENTORY.md`'s
  "Outcome Tag Prompt" sheet row. Confirm whether this requires a small, additive change to CON-001's
  already-shipped `ContactService`/`NotificationService` (a cross-story touch-point worth flagging explicitly).
  Also confirm whether a real Notifications Inbox (S-13) exists yet on mobile, or whether the backend-record-only
  scope trim CON-001's own AC7 already established for provider-lead notifications applies here too.
- Decide whether this story needs new mobile work — AC3's "dismissible ('Maybe later')" wording strongly implies
  a real, testable UI surface, not just a backend record. Check `15_SCREEN_INVENTORY.md` for the exact sheet spec
  and where product intends it to be triggered from.
- Read `docs/AI/09_DECISIONS.md` (ADR-044 through ADR-047, most recent) and `docs/AI/13_OPEN_DECISIONS.md` (item
  14 is explicitly **not** this story's decision — that belongs to `REV-002`) for current conventions.

## Deliverable

Produce `docs/implementation/plans/Plan_S09_REV-001.md` following the established plan format (verbatim ACs,
architecture decisions with alternatives considered and rejected, verified-current-state section grounded in
actual code reads, explicit scope-boundary reasoning, delegation sequence). Decide backend-only vs.
backend+frontend scope. Do not start implementation.

---

**End of Document**
