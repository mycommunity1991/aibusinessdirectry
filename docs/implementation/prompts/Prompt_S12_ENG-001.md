# Implementation Prompt — Story ENG-001 (Sprint 12)

**Story:** "Receive marketplace notifications in my preferred channel" | **Sprint/Milestone/Epic:** SP12 / ML12 /
ML12-EP01
**Depends on:** CON-001, VER-002, REV-001 (all shipped) — satisfied. **Priority:** High.

## Story text (verbatim, `Project_Tracker.xlsx` row, relayed via `docs/AI/SESSION_HANDOFF.md`)

"As a user, I want to be notified about new leads, verification status changes, and outcome-tag prompts through
my preferred channel, so that I don't have to keep checking the app manually. This story implements the
Notification domain end to end: data model, WhatsApp/SMS/Email delivery adapters behind a single interface, and
the trigger wiring for every notification-worthy event already emitted by earlier stories. Scope boundary: does
not include the deep-link/Verified-Visit features (ENG-002) -- this story is notification delivery only."

## Acceptance Criteria (verbatim, 8 items)

1. `notifications`, `notification_preferences`, and `notification_delivery` tables exist via migration.
2. A single `NotificationSender` interface has WhatsApp, SMS, and Email adapters; delivery failures surface as
   typed errors, never a silent no-op.
3. Triggers are wired for: new Contact View -> Provider, verification status change -> Provider, manual match
   assignment created -> Admin, outcome-tag prompt -> Customer.
4. A disabled channel or muted category in `notification_preferences` is checked before every send and is a
   hard stop, not a soft suggestion.
5. Non-urgent events update a badge/inbox entry without forcing a push notification unless the user has opted
   in; time-sensitive events may push immediately.
6. Notifications Inbox screen groups entries as New/Earlier and deep-links each entry to its relevant context.
7. Duplicate sends are prevented via an idempotency key on retry.
8. Automated tests cover: preference-disabled blocking a send, and idempotent retry not double-sending.

## Important: a real discrepancy already investigated and resolved during planning

`NotificationService` already exists (`VER-002`/`CON-001`/`REV-001`) and already fires synchronously for three
of this story's four events, writing only an in-app `notification.notifications` row -- no real multi-channel
delivery, preferences, or idempotency exist yet. This story's Plan extends those three existing methods **in
place** (never a parallel second mechanism) and adds one genuinely new trigger (manual-match-assignment ->
Admin). Read the Plan's "Verified Current State" and Decision 1 before touching `NotificationService` --
breaking any of its 12 already-passing tests is the single easiest way to get this story sent back.

## Instructions

Read `app/.agents/agents.md`, then `docs/AI/02_ARCHITECTURE.md`, `04_DATABASE.md`, `05_API_GUIDELINES.md`,
`06_SECURITY.md`, `08_CODING_STANDARDS.md`, and `docs/AI/SESSION_HANDOFF.md` Section 4 before starting. Follow
`docs/implementation/plans/Plan_S12_ENG-001.md` exactly -- it contains the full Verified Current State,
Architecture Decisions (with rationale and rejected alternatives), the itemized Backend and Frontend Proposed
Changes, the Tests lists, and the Delegation & Execution Sequence.

This story needs **both backend and frontend** work, backend first: `backend` implements Backend Proposed
Changes items 1-18 and Tests items 19-25 (build order suggested in the Plan's Delegation section); once the new
`/notifications` endpoints are available, `frontend` implements Frontend Proposed Changes items 1-5 and Tests
6-8, reusing the existing `OutcomeTagPromptSheet` widget as-is (Decision 10) rather than building a new one.

At every flagged Open Question in the Plan, proceed with the Plan's own stated recommended default -- this is
the CTO's standing instruction for every story this sprint. There is **no** standing instruction to skip the
post-review sign-off pause for this story: once `tester` and `architect` both report clean, the orchestrator
presents both verdicts to the CTO for explicit sign-off before writing the Walkthrough or touching the
changelog/tracker.
