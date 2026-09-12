# Prompt for Story CON-001 — Contact a Matched Provider Directly

**Sprint:** 08 | **Epic:** ML8-EP02 | **Milestone:** ML8 | **Phase:** PH2 | **Priority:** Critical | **Depends
On:** MAT-001 (done)

## Instruction given to `tech-lead`

Start Story CON-001 in the AI Marketplace repository, branch `claude/provider-storefront-pro-001-qnicuj`. This
follows the established cycle: tech-lead plans → backend/frontend implement → tester → architect → CTO sign-off
→ closeout → tracker sync. Read `docs/AI/SESSION_HANDOFF.md` first for current project state and standing
process, then the relevant `docs/AI/` files for this story, in numerical order.

## Story (verbatim, `Project_Tracker.xlsx`, `CON-001` row)

Title: Contact a matched provider directly
Sprint ID: SP08 | Epic Code: ML8-EP02 | Milestone ID: ML8 | Phase ID: PH2 | Priority: Critical
Depends On: MAT-001 (done)

Description: "As a customer, I want to see a matched provider's phone number immediately when I tap Contact,
with no quote or approval step in between, so that reaching out feels as simple as getting a number from a
friend. This story implements the platform's growth-first, direct-contact model and its most safety-critical
rule: the self-dealing guard. Because one Account may hold both Customer and Provider roles, a Contact View must
be rejected outright if the requesting Customer's Account is the same Account that owns the target Provider —
otherwise a provider could inflate their own lead/contact/review numbers by contacting themselves. Scope
boundary: does not include the Outcome Tag prompt or reviews (REV-001/002) — this story ends at the phone number
being shown."

Acceptance Criteria (verbatim, 8 items):
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
7. Every Contact View creation is a candidate trigger for provider-lead notifications (wired fully in ENG-001,
   but the event itself must be emitted here).
8. Automated tests cover the happy path (successful contact reveal) and the self-dealing rejection as separate,
   explicit test cases.

## Context supplied for planning

- MAT-001 just shipped (merit-ranked search results); `SearchService.search_providers_ranked(...)` is the
  shared entry point behind both `GET /search/providers` and the AI-conversation automated-match path.
- `contact_views` is a genuinely new table/domain concept, already fully spec'd in `04_DATABASE.md`.
- The self-dealing guard (AC3/AC4) is this story's most safety-critical mechanism — read `03_DOMAIN_MODEL.md`
  for the exact business rule wording and check how the codebase currently models "Account" (via `identity.users`
  and the `customer_profiles.user_id`/`providers.user_id` FKs), mirroring CLM-001's claim-flow one-provider-
  per-account precedent.
- AC5's "Provider Profile screen" needed a scope check: `15_SCREEN_INVENTORY.md`'s S-09 versus what's actually
  built today (nothing — confirmed both `SearchResultsScreen` and `AiConversationScreen` still show a "coming
  soon" stub for it).
- AC7's notification-event scope boundary: check the existing `notification` module (VER-002) for its
  established "narrow, passive record, full delivery is a future story's job" pattern.
- Check `13_OPEN_DECISIONS.md` for anything already flagged relevant to contact/self-dealing (none found beyond
  item 14, unrelated).
- Read `02_ARCHITECTURE.md`, `08_CODING_STANDARDS.md`, `09_DECISIONS.md` (ADR-042/043) for current conventions.

## Deliverable

Produce `docs/implementation/plans/Plan_S08_CON-001.md` following the established plan format (verbatim ACs,
architecture decisions with alternatives considered and rejected, verified-current-state section grounded in
actual code reads, explicit scope-boundary reasoning, delegation sequence). Decide backend-only vs.
backend+frontend scope. Do not start implementation.

---

**End of Document**
