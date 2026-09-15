# Implementation Prompt for Story ADM-001 — Resolve Manual-Match and Unmatched-Query Work as an Administrator

**Sprint:** 11 ("Marketplace Operations") | **Milestone:** ML11 | **Epic:** ML11-EP01 | **Priority:** High |
**Depends on:** AI-002 (already shipped)

The CTO authorized starting Story ADM-001, the first story of Sprint 11, immediately following Milestone ML10's
completion (LEAD-001 + LEAD-002, both shipped).

## Story (verbatim)

As an administrator, I want a queue of low-confidence sessions needing manual matching and a report of searches
that produced no good match, so that I can keep the Wizard-of-Oz fallback working and spot supply/category gaps
early. This story gives admins the operational surface for two things already producing data in earlier stories:
AI-002's `manual_match_assignments` and MAT-001's `search_event_log` unmatched entries. The admin platform itself
(Flutter vs. a separate internal tool) remains an explicitly open decision — this story implements the API layer,
which is platform-agnostic, without assuming the answer. Scope boundary: does not include verification review
(VER-002, already delivered) or the broader admin dashboard shell (ADM-002).

## Acceptance Criteria (verbatim)

1. `unmatched_query_reports` table exists via migration, sourced from `search_event_log` rows where
   `was_matched=false`, supporting admin annotation and a status (open/reviewed/actioned).
2. Admin-only endpoint lists pending `manual_match_assignments` with the underlying conversation transcript
   available for context.
3. Admin can select and rank candidate providers for a manual assignment, writing to `provider_matches` exactly as
   the automated matcher would.
4. Completing a manual assignment updates its status and is reflected in the customer's ranked-results screen
   without further admin action.
5. Unmatched query reports can be filtered/sorted and marked reviewed/actioned by an admin.
6. Non-admin access to either endpoint returns 403.
7. Automated tests cover: manual assignment completion producing a customer-visible result, and unmatched-report
   status transitions.

## Standing instructions for this story's execution

The CTO gave a standing instruction for the rest of this story's execution: pick the recommended option at any
decision point without waiting for further confirmation, and the orchestrator will push/close the story through
to completion without pausing for additional sign-off once tester/architect are clean. This does not mean skip
investigation or skip flagging genuine open questions in the Plan — it means the orchestrator resolves flagged
questions with the Plan's own recommended default rather than stopping to ask.

## Required first investigation (before writing the Plan)

`docs/AI/SESSION_HANDOFF.md`'s own "Key technical precedents" section (§4, "Pull-based admin queue pattern") lists
four existing applications of the pattern — `admin_action_log`, `claim_review_requests`, `unmatched_query_reports`,
`manual_match_assignments` — describing them as "backend-API-only, no dashboard UI yet." This reads as if
`unmatched_query_reports` already exists, which would contradict AC1's literal text ("table exists via migration,"
implying new). This contradiction must be resolved with direct evidence (`04_DATABASE.md`'s Administration Domain
section, `backend/app/modules/administration/models.py`, and a grep of the actual migrations directory) before
writing anything else in the Plan — not assumed either way.

Also required reading before planning:
- `backend/app/modules/administration/` in full (models, repositories, services, api.py if any) — the existing
  `administration` module, since this story likely extends it a fourth time.
- `backend/app/modules/search/models.py` and `search_event_log`'s exact shipped schema.
- `backend/app/modules/search/models.py`'s `manual_match_assignments` table (AI-002) and
  `ManualMatchAssignmentService`/`ManualMatchAssignmentRepository` — confirm existing statuses, what `try_resolve`
  already does, and whether "candidate providers"/"conversation transcript" are already reachable or need a new
  join.
- The exact admin authorization/role-checking mechanism in use today (confirm for AC6's 403).
- `docs/implementation/plans/Plan_S07_AI-002.md`/`Walkthrough_S07_AI-002.md` for the `_finalize_matches`
  shared-write mechanism AC3/AC4 must reuse exactly, not reimplement in parallel.
- `docs/AI/02_ARCHITECTURE.md`, `docs/AI/08_CODING_STANDARDS.md`, `docs/AI/06_SECURITY.md`.
- The most recent Plans (`Plan_S10_LEAD-001.md`, `Plan_S10_LEAD-002.md`) for this project's exact Plan document
  format.

## Key design questions the Plan must resolve

1. The `unmatched_query_reports` contradiction above — resolve with evidence, not assumption.
2. AC3's "writing to `provider_matches` exactly as the automated matcher would" — confirm whether this means
   literally calling AI-002's existing shared write path rather than reimplementing it; trace the actual code to
   find the exact reusable entry point.
3. AC4's "reflected in the customer's ranked-results screen without further admin action" — confirm whether this
   is already true once `provider_matches` rows exist, by tracing the real customer read path, not by assumption.
4. Confirm this Plan's scope is backend-only (API layer), with no mobile/frontend work, unless something in the
   actual ACs implies otherwise.
5. AC6's 403 for non-admin — confirm the exact existing role-check mechanism and reuse it verbatim.

Follow this project's exact established Plan structure (ACs restated verbatim, Verified Current State, Decisions
with rationale, Backend Proposed Changes as itemized lists, a Frontend section only if genuinely needed, Tests,
Explicitly Out of Scope, Open Questions if any, Delegation & Execution Sequence, Verification Plan table). Flag
genuine CTO-level open questions rather than silently resolving something that changes product behavior or scope.
Planning only — no implementation in this pass.

## Deliverable

`docs/implementation/plans/Plan_S11_ADM-001.md` — see that file for the full investigation findings, all nine
Architecture Decisions with rationale and alternatives considered, the itemized Backend Proposed Changes, the new
test list, Explicitly Out of Scope items, three flagged Open Questions (each with a stated recommended default per
the standing instruction above), the Delegation & Execution Sequence, and the AC-to-test Verification Plan table.

---

**End of Document**
