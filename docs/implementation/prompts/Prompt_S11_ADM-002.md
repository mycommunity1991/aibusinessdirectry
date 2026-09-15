# Implementation Prompt — Story ADM-002 (Sprint 11)

**Story:** "Operate the marketplace from an admin dashboard" | **Sprint/Milestone/Epic:** SP11 / ML11 / ML11-EP01
**Depends on:** VER-002 (shipped) + ADM-001 (shipped) — both satisfied. **Priority:** Medium.

## Story text (verbatim, `Project_Tracker.xlsx` row, relayed via `docs/AI/SESSION_HANDOFF.md`)

"As an administrator, I want a single dashboard summarizing verification queues, manual-match workload, and
platform configuration, so that I can operate the marketplace day-to-day without stitching together separate
tools. This story consolidates ADM-001 and VER-002's queues alongside feature-flag and system-configuration
management into one operational surface -- the capstone of the Marketplace Operations sprint. Scope boundary:
does not add new admin capabilities beyond what ADM-001/VER-002 already implemented."

## Acceptance Criteria (verbatim, 6 items)

1. `feature_flags` and `system_settings` tables exist via migration (if not already present) and are editable
   only by admins.
2. Dashboard summarizes: pending verification count, pending manual-match count, and open unmatched-query-report
   count, each linking to its respective queue.
3. `admin_action_log` records every configuration change, feature-flag toggle, and queue action taken from this
   dashboard.
4. Feature flags can be toggled without a deploy and take effect for the next relevant request.
5. Non-admin access returns 403 across every dashboard endpoint.
6. Automated tests cover feature-flag toggling taking effect and `admin_action_log` recording every action type
   exercised by this story.

## Instructions

Read `app/.agents/agents.md`, then `docs/AI/02_ARCHITECTURE.md`, `04_DATABASE.md`, `06_SECURITY.md`,
`08_CODING_STANDARDS.md`, and `13_OPEN_DECISIONS.md` (item 10) before starting. Follow
`docs/implementation/plans/Plan_S11_ADM-002.md` exactly — it contains the full Verified Current State,
Architecture Decisions (with rationale and rejected alternatives), the itemized Backend Proposed Changes, the
Tests list, and the Delegation & Execution Sequence. This story is backend-only (Decision 2/Open Question 1 in
the Plan) — no Flutter/mobile work is in scope.

CTO standing instruction for this story: pick the Plan's own recommended option at every open decision point
without waiting for further confirmation, and proceed straight through closeout once `tester`/`architect` both
report clean, without an additional sign-off pause.
