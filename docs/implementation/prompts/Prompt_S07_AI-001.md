# Implementation Prompt — Story AI-001

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Story:** AI-001 — Describe My Service Need in a
Guided AI Conversation | **Plan:** `docs/implementation/plans/Plan_S07_AI-001.md` (read in full before starting —
this prompt is a pointer to it, not a replacement for it)

---

## Task

Implement Story AI-001 exactly per `docs/implementation/plans/Plan_S07_AI-001.md`. Read `.agents/agents.md` and
the `docs/AI/` documents that Plan's "Related Documents" section names before writing any code — in particular
`docs/AI/04_DATABASE.md`'s `conversation` schema section (lines 588–628, the exact column spec this story builds)
and `.agents/skills/ai-conversation-engineering/SKILL.md` plus its two rule files (grounding/RAG,
confidence-scoring-and-fallback).

## Story Summary

Build the real `conversation` domain — `conversation_sessions`, `messages`, `confidence_scores` — and a
`ConversationService` that lets an authenticated Customer describe a problem in free text, has the AI resolve a
Category and ask only that category's seeded follow-up questions (`category.category_question_templates`,
shipped by `CTG-001`), tracks a persisted confidence score per turn, and ends the session in `completed` or
`routed_to_admin`. Backend + mobile (new `S-07` AI Conversation screen, plus a new entry point on the Home
placeholder screen). Does **not** create `search.search_requests`, run any provider matching, or create
`administration.manual_match_assignments` — see the Plan's Decision 1 for why that boundary was chosen.

## Acceptance Criteria

See the Plan's "Acceptance Criteria" section — **read its sourcing note first**: this session could not open
`docs/AI/Project_Tracker.xlsx` directly (binary `.xlsx`, no code-execution tool available), so the 11 ACs there
are reconstructed from `03_DOMAIN_MODEL.md`, `04_DATABASE.md`, `14_USER_FLOWS.md` Flow 4, `15_SCREEN_INVENTORY.md`,
`16_UX_GUIDELINES.md`, and the `ai-conversation-engineering` skill — not independently verified verbatim against
the spreadsheet. Confirm the literal wording before/while implementing if spreadsheet access is available.

## Key Decisions to Follow (do not re-derive — the Plan already resolved these)

1. **Scope boundary (Decision 1):** this story owns the `conversation` schema/module only. Do not create
   `search.search_requests`, `search.provider_matches`, `search.search_event_log`, or
   `administration.manual_match_assignments` — the evidence (`search_request_status`'s enum values are matching
   *outcomes*, not "submitted" states) is in the Plan; do not re-litigate this mid-implementation.
2. **LLM integration (Decision 2):** a swappable `ConversationAiClient` Protocol (fourth application of this
   codebase's `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern — ADR-017/018/031), with exactly one
   shipped implementation, `RuleBasedConversationAiClient` — deterministic substring category-matching, verbatim
   category-locked follow-up questions, and a real (not fabricated) confidence score derived from how many
   required questions are answered. No LLM API/SDK/credential is wired in this story — do not add one
   speculatively.
3. **Cross-module edges (Decision 3):** `conversation → customer` (`CustomerService.get_my_profile` for
   `customer_id`/`language`) and `conversation → category` (`CategoryService.list_active_categories`/
   `get_question_templates`, both already built by `CTG-001`) — constructor injection, same shape as ADR-014/016.
4. **Config, not schema (Decision 4):** `CONVERSATION_CONFIDENCE_THRESHOLD` and `CONVERSATION_MAX_TURNS` are new
   `Settings` fields.
5. **Revise-a-previous-answer (Decision 5):** truncate-and-regenerate — `PATCH
   /conversations/{session_id}/answers/{message_id}` updates the target message, hard-deletes every later message
   in the session, and regenerates the next turn. "Start over" is a separate new session; the old one is marked
   `abandoned` (a new, additive `conversation_status` enum value — flag for `04_DATABASE.md` update at story
   close).
6. **Bilingual (Decision 6):** resolve `CustomerPreferences.language` once at session start; pass it into every
   AI-client call; fall back to English when an Arabic field is null.
7. **Endpoint shape (Decision 7, ADR-015):** conversation sessions are `{session_id}`-addressable with
   `ensure_owner_or_not_found` (1:N per customer, not a `/me` singleton).
8. **Mobile entry point:** add a new button to the existing
   `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (same precedent `CLM-001` already
   used for its own entry point) — do not build a full Home (`S-06`) screen; it doesn't exist yet and isn't this
   story's scope.
9. **Grounding must be structural, not a prompt instruction** — write the dedicated `test_grounding.py` (Plan
   item 19) that directly proves no AI-turn message content can exist outside the seeded taxonomy.

## Delegation Order

1. **backend** — the entire backend Plan section (Proposed Changes items 1–19, Architecture Decisions 1–6).
   Build order matters: migration + models → repositories → `ConversationAiClient`/
   `RuleBasedConversationAiClient` (the part most worth extra care) → `ConversationService` → `api.py`/
   `schemas.py`/`dependencies.py`.
2. **frontend** — Mobile Proposed Changes items 20–27, once backend endpoints exist (or in parallel against a
   fake repository). Particular attention to the latency-tier UI logic and the honest, no-fake-results completion
   state (Decision 1) — do not add a results list here; it doesn't exist yet.
3. **tester** — verify all 11 ACs per the Plan's Verification Plan table, with particular attention to AC8/AC11
   (the grounding tests) and AC4 (the revise flow genuinely removes stale AI messages, not merely marks them).
4. **architect** — review per the Plan's Delegation section step 4 (the scope-boundary decision and its evidence,
   the `ConversationAiClient` Protocol against ADR-017/018/031, the additive `abandoned` enum value and
   hard-delete-on-revise mechanism, and the two new cross-module edges for cycle-freedom).

Pause and present to the user once `tester`/`architect` both report clean — do not write the Walkthrough, touch
`docs/CHANGELOG.md`/tracker, or mark the story complete without explicit sign-off.

## Out of Scope

See the Plan's "Explicitly Out of Scope" section — notably any write to `search.search_requests`/
`provider_matches`/`search_event_log`/`administration.manual_match_assignments`, any real provider matching or
`S-08` wiring, Contact View/Outcome Tag/Reviews, a real LLM-provider integration, reconciling
`provider_category_labels` into `category.provider_categories`, any admin-facing consumption UI for low-confidence
sessions, and any LLM cost/rate-limit controls.

## Before You Start — One Open Question Worth a Quick Check

The Plan's "Open Questions" section flags that the `AI-001`/`AI-002` scope boundary (item 3 there) is this
session's own inference, not a confirmed reading of the Tracker. If the CTO has since confirmed or corrected this
boundary, re-read the Plan's Decision 1 and Explicitly Out of Scope section for any resulting update before
starting backend work.
