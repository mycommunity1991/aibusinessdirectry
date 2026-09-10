# Walkthrough S07 AI-001

## Story: Describe My Service Need in a Guided AI Conversation

**Sprint:** 07 | **Story ID:** AI-001 | **Priority:** Critical | **Status:** Done

As a registered Customer, I want to describe my service need in my own words and have the app ask me a few
guided follow-up questions, so that the platform understands my problem well enough to find the right provider —
without me having to fill out a rigid form or already know the right category name. This is the product's core
differentiator: an LLM-API-driven, RAG-grounded conversational intake, with the hard constraint that the AI must
never assert availability, prices, ratings, or capabilities not grounded in real platform data, and every
follow-up question comes only from the approved `category_question_templates`, never an invented question.
**Scope boundary:** routing low-confidence sessions to manual matching (the Wizard-of-Oz fallback) is `AI-002` —
this story covers the conversation itself and its structured output only, ending at
`conversation_sessions.status ∈ {completed, routed_to_admin}` with zero writes to `search`/`administration`.

**Explicit, CTO-accepted MVP gap, stated up front:** no real LLM vendor is selected or wired in. This story ships
a fully rule-based, deterministic interim `ConversationAiClient` implementation behind a swappable Protocol. Two
of the story's 11 verbatim acceptance criteria (AC3, AC5) are honestly **not met** by this implementation and are
recorded as a deferred MVP gap, not silently skipped — see Decision 2b below and `13_OPEN_DECISIONS.md` item 13.

Full context, the 7 Architecture Decisions (1, 1b, 2, 2b, 3, 4, 5, 6, 7 — numbered per the Plan), and file-by-file
scope: `docs/implementation/plans/Plan_S07_AI-001.md`. That Plan is the complete, final record of this story,
including the corrected Decision 5 (soft-delete, not the originally-planned hard-delete).

All work is committed and pushed to branch `claude/provider-storefront-pro-001-qnicuj`:
- `7816403` — backend implementation
- `46602ec` — mobile implementation
- `bc37164` — tester's regression test proving the mobile 422 error-mapping bug
- `ac1e8c1` — fix: mobile revise-specific 422 distinguished from body-validation 422
- `9a52cd8` — fix: revise editor uses the shared `PrimaryButton` (architect nit)
- `cbf7cdd` — fix: `revise_answer` soft-deletes messages instead of hard-deleting them (architect finding)
- `1db6330` — docs: correct a stale hard-delete docstring left behind by the previous fix (current HEAD)

---

## What was implemented

### Backend (`backend/app/modules/conversation/`, new)

- **New, reversible Alembic migration** (`conversation_domain`, revision `ef7b7d439f40`, down-revision
  `602bf3c4bea7`) — creates the `conversation` Postgres schema and its three tables column-for-column per
  `04_DATABASE.md`'s pre-existing spec: `conversation_sessions`, `messages`, `confidence_scores`. Two additive
  items beyond that spec, both flagged in the Plan for a `04_DATABASE.md` update at close:
  - `conversation_status` gains a fourth value, `abandoned` (Decision 5) — set when a customer starts a new
    session while a previous one is still `active`.
  - `conversation_sessions.structured_criteria` (JSONB, nullable, Decision 1b) — the AC9 payload, populated only
    when a session reaches `status=completed`.
  - `uq_messages_session_sequence` is a **partial** unique index on `(conversation_session_id, sequence_number)`
    scoped `WHERE is_active = true` — not a plain table-level `UniqueConstraint` — mirroring
    `uq_saved_addresses_customer_default`'s existing precedent, required by Decision 5's soft-delete mechanism
    (see below).
  - This story's first genuine cross-schema FKs into two already-shipped domains:
    `conversation_sessions.customer_id → customer.customer_profiles.id` and
    `conversation_sessions.category_id → category.categories.id` (Decision 3).
- **`ConversationAiClient` Protocol + `RuleBasedConversationAiClient`** (`services/conversation_ai_client.py`,
  Decision 2) — the fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient`
  swappable-Protocol pattern (ADR-017/018/031) for an external capability with no confirmed vendor. Category
  resolution is a case-insensitive substring match against each active category's `name`/`name_ar`/`slug`; zero
  or multiple matches never guess — they return a clarifying quick-reply category picker instead (AC4). Follow-up
  questions walk a resolved category's `is_required=true` `CategoryQuestionTemplate` rows in `sort_order`,
  verbatim, one at a time — the client has no free-text generation capability at all beyond echoing template/
  category data, so AC10's grounding requirement holds by construction, not by prompt instruction. Confidence is
  `0.0` while unresolved, rising in equal steps as required questions are answered, `1.0` once every required
  question has a persisted answer; `confidence_scores.model_version` is tagged `"rule_based_v1"`.
- **A documented, deliberate signature deviation from the Plan's literal sketch:** `process_turn` takes
  `question_templates_by_category: dict[uuid.UUID, list[CategoryQuestionTemplate]]` (every active category's
  templates, keyed by `category_id`) instead of the Plan's originally-sketched single `active_question:
  CategoryQuestionTemplate | None`. A single `active_question` value cannot support both "how many required
  questions are left" (needed for the equal-step confidence calculation) and the same-turn category-resolution
  case, where no `active_question` exists yet because the category is being resolved for the first time inside
  that very call. `ConversationService` assembles the full dict once per turn (14 categories, ~47 templates in
  the seeded taxonomy — cheap to refetch every turn). No other part of Decision 2's design changed. Recorded as
  part of **ADR-032** below.
- **`StructuredCriteria` / `StructuredCriteriaAnswer`** (`services/structured_criteria.py`, Decision 1b) —
  Pydantic models satisfying AC9: `category_id`, `category_slug`, and an ordered list of
  `{question_id, question_text, answer_text}`. Built and validated by `ConversationService._complete_session`
  from the resolved category and the session's most recent `len(required_templates)` customer messages (always
  the actual required-question answers, in order, once the confidence-threshold gate has already fired), then
  persisted to `conversation_sessions.structured_criteria` in the same transaction that sets `status=completed`.
  A `ValidationError` at this point raises `InvalidStructuredCriteriaError` (500) rather than surfacing a raw
  Pydantic error — defensive, since the service constructs the payload itself and this should never occur in
  correct code. A `routed_to_admin` session leaves `structured_criteria` `NULL`. Lives entirely inside the
  `conversation` schema — this story never creates or writes to `search.search_requests` (Decision 1's scope
  boundary).
- **`ConversationService`** (`services/conversation_service.py`) — `start_conversation` (creates the session,
  marks any still-`active` prior session `abandoned` first, persists the first customer message, generates the
  first AI turn); `submit_turn` (persists the next answer, generates the next turn, rejects a non-`active` session
  with `ConversationSessionNotActiveError`); `revise_answer` (Decision 5, AC8 — see below); `get_session`
  (`ensure_owner_or_not_found`, replays `process_turn` read-only to recover `quick_reply_options` for a plain
  `GET` without creating a new message or confidence row). Applies Decision 4's completion policy every turn:
  confidence-threshold completion first (`CONVERSATION_CONFIDENCE_THRESHOLD`, default `1.0`), then a hard turn
  cap (`CONVERSATION_MAX_TURNS`, default `12`) routing to `routed_to_admin` if never reached — both `Settings`,
  not code, so the eventual Wizard-of-Oz-degree answer (`13_OPEN_DECISIONS.md` item 10) is a config change.
- **Revising a previous answer (AC8, Decision 5)** — `PATCH /conversations/{session_id}/answers/{message_id}`:
  updates the target message's content, truncates every later message in the same session (customer and AI
  alike), and regenerates the next turn fresh from the now-shorter history. Revising the session's very first
  message re-opens category resolution from scratch (clears `category_id`). A session that had already
  `completed`/`routed_to_admin` reverts to `active` and has any stale `structured_criteria` cleared before the
  truncated history is reprocessed — it may or may not re-complete. An `abandoned` session can never be revised
  (`AnswerNotRevisableError`) — it was superseded by a newer session.
- **`api.py`/`schemas.py`** — `POST /conversations`, `POST /conversations/{session_id}/messages`, `PATCH
  /conversations/{session_id}/answers/{message_id}`, `GET /conversations/{session_id}`, all
  `require_role(ROLE_CUSTOMER)` + `ensure_owner_or_not_found` (404, never 403). `ConversationSessionResponse`
  deliberately has no raw confidence/score field anywhere in its schema — AC6's "never shows a raw confidence
  score" is satisfied at the API-contract level, not merely by mobile choosing not to render a field it could
  otherwise see.
- **Config** — `CONVERSATION_CONFIDENCE_THRESHOLD: float = 1.0`, `CONVERSATION_MAX_TURNS: int = 12`.
- **Tests** — `test_conversation_ai_client.py`, `test_conversation_service.py`, `test_structured_criteria.py`,
  `test_conversation_api.py`, `test_grounding.py` (a direct, structural assertion that no AI-sender message
  content is ever absent from the seeded `categories`/`category_question_templates` rows — the concrete proof
  behind Decision 2's "grounded by construction" claim, not a prompt-instruction claim).

### Mobile (`mobile/lib/features/conversation/`, new)

- `domain/models/` (`conversation_session.dart`, `conversation_message.dart`, `conversation_exception.dart`),
  `data/conversation_repository.dart`, `state/conversation_controller.dart` (Riverpod), `presentation/screens/
  ai_conversation_screen.dart` (S-07), `presentation/widgets/` (`chat_bubble.dart`, `typing_indicator_bubble.dart`).
- **Latency-tiered feedback (AC6/AC7)** — `ConversationController` schedules a 3-second "contextual label" timer
  and an 8-second "handoff" timer on every turn submission; the screen renders a typing indicator (0–3s), a
  contextual label (3–8s), then "we'll notify you" hand-off messaging past 8s or on a timeout — never an
  indefinite spinner. The input is never frozen while a turn is in flight — additional input typed mid-turn is
  queued and dispatched automatically in order (`_enqueueOrRun`/`_drainQueue`).
- **Revise-in-place (AC8)** — tapping a past customer bubble opens an inline revise editor, gated by
  `session.isActive && message.sender == customer` — i.e. **a completed/routed-to-admin/abandoned session's
  bubbles are deliberately not tappable.** This is a legitimate mobile-side design choice, not a bug or a gap:
  see the Design Debt section below for why it was reviewed and left as-is.
- **"Start over"** (Decision 5) — resets the controller to its initial compose state; the previous session is
  left exactly as it is on the backend (marked `abandoned` the next time `POST /conversations` is called) — the
  mobile client never deletes or otherwise touches it.
- **Never renders a numeric confidence value anywhere in the widget tree** (AC6) — the mobile session model has
  no such field to render in the first place, matching the backend's API-contract-level guarantee.
- **RTL/Arabic** — chat bubbles mirror correctly under RTL; Arabic reply/prompt text renders via the backend's
  `reply_message_ar`/`question_text_ar` selection (AC11).
- Entry point: a new primary button ("Describe what you need") on `home_placeholder_screen.dart`, opening
  `ai_conversation_screen.dart` directly — the same "add a button to the existing placeholder" precedent
  `CLM-001` already used, since real `S-06` still doesn't exist.
- Tests: `ai_conversation_screen_test.dart`, `conversation_repository_test.dart`,
  `fakes/fake_conversation_repository.dart`, `test_helpers.dart`.

---

## The Architecture Decisions, as actually shipped

All decisions from `Plan_S07_AI-001.md` shipped, with one corrected decision (5) and one documented signature
deviation (2) — both fully accounted for below and in the new ADRs.

1. **Scope boundary (CONFIRMED by the verbatim `AI-002` row)** — `AI-001` ends at `conversation_sessions.status ∈
   {completed, routed_to_admin}`; zero writes to `search`/`administration`. Shipped exactly as planned.
2. **`ConversationAiClient` Protocol + `RuleBasedConversationAiClient`** — shipped as planned, with the documented
   `process_turn` signature generalization (`question_templates_by_category` dict instead of a single
   `active_question`) described above and in ADR-032.
3. **`StructuredCriteria` (AC9)** — shipped exactly as planned: a validated JSONB payload on
   `conversation_sessions`, never touching `search.search_requests`.
4. **AC3/AC5 honest deferral (Decision 2b)** — shipped exactly as planned: both recorded as **not met**, not
   silently skipped, with a new `13_OPEN_DECISIONS.md` item 13 tracking the real-LLM-vendor decision this gap is
   downstream of.
5. **Cross-module edges (`conversation → customer`, `conversation → category`)** — shipped exactly as planned,
   constructor-injected, same-session, zero cycles, mirroring ADR-014/016.
6. **Confidence threshold / turn cap as `Settings`** — shipped exactly as planned.
7. **Revising a previous answer (Decision 5)** — shipped with a genuine, tester/architect-caught correction: the
   Plan originally specified a hard `DELETE` of truncated messages, reasoned (incorrectly) as necessary because
   `messages` supposedly had no soft-delete column. That premise was factually wrong — `Message` is
   `CommonColumnsMixin`-based and already has `deleted_at`/`is_active`. Corrected during architect review to a
   soft-delete (`MessageRepository.delete_after_sequence` now sets `deleted_at`/`is_active=False`), mirroring
   `SavedAddressRepository.soft_delete`'s exact convention, and requiring the partial-unique-index promotion
   described above. See Review Process below for the full account.
8. **Bilingual handling (Decision 6)** and **endpoint shape / module layout (Decision 7)** — both shipped exactly
   as planned.

---

## Review Process — a full, honest account

### 1. `tester` — independent verification against real HTTP round trips, plus one genuine finding

The tester independently verified the 11 verbatim ACs (explicitly confirming AC3/AC5 are correctly documented as
deferred, not silently absent or falsely marked satisfied), with particular attention to AC10's grounding tests,
AC9's `structured_criteria` validation, AC6's confidence-never-surfaced guarantee at both the API and widget
level, and AC8's truncate-and-regenerate revise flow.

**Found a genuine bug:** `ConversationRepository._mapError` in the mobile client mapped every HTTP 422 response to
`ConversationErrorType.answerNotRevisable`, regardless of which endpoint produced it. `PATCH .../answers/
{message_id}` genuinely does raise a 422 for `AnswerNotRevisableError`, but `POST /conversations` and `POST
.../messages` can also return a plain FastAPI 422 for ordinary request-body validation failures (e.g. the
2000-character limit on `message`/`content`) — an unrelated failure mode that was being shown to the customer as
"this answer can no longer be revised," a confusing and wrong message for a validation error on a brand-new
message. Proven with a regression test (`bc37164`) before the fix.

### 2. `tech-lead` (this session's prior pass) — fixed the mobile 422 bug and a minor architect nit

- **Fixed** (`ac1e8c1`): `_mapError` now takes an `isReviseCall: bool` parameter, set `true` only by
  `reviseAnswer`'s call site — the sole endpoint that can raise `AnswerNotRevisableError`. Every other call site's
  422 now maps to the new `ConversationErrorType.validationFailed` instead. The two share an HTTP status code but
  mean unrelated things; `ConversationErrorType`'s own doc comments now record this distinction explicitly so a
  future call site doesn't reintroduce the conflation.
- **Fixed** (`9a52cd8`, architect finding, non-blocking): the revise editor's "Save" button used a raw
  `FilledButton` instead of the shared `PrimaryButton` widget. Fixed to reuse `PrimaryButton`, wrapped in
  `Expanded` since `PrimaryButton`'s underlying theme sets a full-width minimum size that would otherwise force an
  infinite-width constraint inside a `Row`.

### 3. `architect` — first review found the two items above; second review found a genuine standards violation

**First pass:** confirmed the Protocol boundary (AC2), the grounding-by-construction claim (AC10), and Decision
1's scope boundary against `03_DOMAIN_MODEL.md`/`04_DATABASE.md`; flagged the `PrimaryButton` nit (fixed above)
and deferred a full sign-off pending the mobile 422 fix landing.

**Second pass, the story's most consequential finding:** Decision 5's originally-shipped `revise_answer` used a
hard `DELETE` on every truncated message, reasoned in the Plan as necessary because "`messages` has no
`deleted_at`/soft-delete column... unlike `CommonColumnsMixin`-based tables." The architect confirmed this premise
is factually wrong by reading `backend/app/modules/conversation/models.py` directly: `Message(CommonColumnsMixin,
Base)` *is* `CommonColumnsMixin`-based and *does* have `deleted_at`/`is_active` (`backend/app/database/mixins.py`).
A hard `DELETE` of customer conversation transcript data, triggered by a customer-initiated revise (not an
administrative action), violated `04_DATABASE.md`'s "Common Columns" rule that permanent deletion is an
administrative operation — `audit.audit_logs`/`search.search_event_log` are the only stated exemptions, and
`messages` is neither.

**Fixed** (`cbf7cdd`): `MessageRepository.delete_after_sequence` now sets `deleted_at`/`is_active=False` instead of
issuing a `DELETE`, mirroring `SavedAddressRepository.soft_delete`'s exact convention. `list_for_session` and
`get_next_sequence_number` now filter `is_active.is_(True)` so a soft-deleted message is invisible to the
transcript and never double-counted when assigning the next `sequence_number` — the customer-visible behavior
(truncated messages disappear, sequence numbers continue correctly) is unchanged, only the persistence mechanism
is. This required promoting `uq_messages_session_sequence` from a plain table-level `UniqueConstraint` to a
**partial** unique index (`WHERE is_active = true`, mirroring `uq_saved_addresses_customer_default`), so a
regenerated turn can reuse a soft-deleted row's old `sequence_number` without a constraint conflict. A follow-up
commit (`1db6330`, current HEAD) corrected a stale docstring in `revise_answer` that still described the old
hard-delete behavior after the fix landed. Re-reviewed and confirmed clean by `architect` on this specific fix.

### Two design-debt items architect reviewed and deliberately left unfixed

- **`RuleBasedConversationAiClient._count_answered_required_questions`'s replay fragility** — this method
  deterministically re-runs the same category-matching logic used at resolution time against the session's
  customer-message history, to find how many required questions have been answered so far (the `messages` schema
  has no column recording "which message resolved the category"). This is correct and side-effect-free today,
  but it is a form of implicit, recomputed state rather than an explicitly persisted one — a genuine, if minor,
  fragility acknowledged in the method's own docstring. **Not fixed**: adding a persisted "resolution marker"
  column would be unrequested schema scope creep for an interim client that is itself scheduled for replacement
  the moment a real LLM vendor is chosen (Decision 2b); the replay is deterministic and correctly tested
  (`test_conversation_ai_client.py`) today.
- **Mobile's choice not to expose revising a completed session's answers** — `ai_conversation_screen.dart` gates
  `canRevise` on `session.isActive`, so a `completed`/`routed_to_admin`/`abandoned` session's past bubbles are not
  tappable. `ConversationService.revise_answer` itself *does* support reviving a completed session (see Decision
  5's revert-to-`active` behavior above) — the backend capability is broader than what the mobile UI currently
  exposes. **Reviewed and accepted, not a gap**: AC8's literal requirement is "revise a previous answer without
  restarting the conversation," which is fully satisfied while a session is still in progress; exposing
  post-completion revision on mobile would also need new UX for "your finished conversation just reopened," which
  no screen inventory or UX guideline currently specifies. Left as a legitimate, narrower mobile scope choice, not
  something the backend's broader capability obligates mobile to expose.

### Final verdicts

- **`tester`**: all 11 ACs independently verified, one genuine bug found and fixed (see above), AC3/AC5 confirmed
  correctly documented as deferred rather than tested for something that cannot exist in this implementation.
- **`architect`**: two rounds — first pass flagged the `PrimaryButton` nit (fixed); second, focused pass found and
  required the hard-delete → soft-delete correction (fixed and re-verified clean).
- **CTO sign-off** received after both verdicts were presented, per standing process.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `conversation_sessions`, `messages`, and `confidence_scores` exist via migration; messages ordered by `sequence_number` | Pass |
| 2 | The LLM provider sits behind a service interface, never called directly from routes or the mobile screen | Pass |
| 3 | System prompts are stored as version-controlled files, not inline strings | **Deferred (MVP gap)** — see Decision 2b, `13_OPEN_DECISIONS.md` item 13 |
| 4 | Follow-up questions are sourced only from `category_question_templates` for the resolved category | Pass |
| 5 | A retrieved provider record with a null field is reported as unknown, never estimated or guessed | **Deferred (MVP gap)** — see Decision 2b, `13_OPEN_DECISIONS.md` item 13 |
| 6 | Typing indicator within 500ms, contextual label past 3s, never a raw confidence score shown | Pass |
| 7 | A response past 8s (or a timeout) transitions to "we'll notify you" messaging, never an indefinite spinner | Pass |
| 8 | The customer can go back and revise a previous answer without restarting the entire conversation | Pass |
| 9 | Every completed session produces a `search_requests`-ready, Pydantic-validated `structured_criteria` payload | Pass |
| 10 | Automated tests assert no fabricated provider attribute is ever surfaced in a conversation response | Pass |
| 11 | RTL layout and Arabic prompt/response quality verified for the chat screen | Pass |

**9 of 11 Pass; AC3 and AC5 Deferred as a documented, CTO-accepted MVP gap** — not silently absent, not falsely
marked satisfied. Both become directly testable and required the moment a real LLM+RAG implementation is built.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded five new ADRs:
  - **ADR-032** — the `AI-001`/`AI-002` scope boundary, now Tracker-confirmed (Decision 1).
  - **ADR-033** — `structured_criteria` JSONB + Pydantic validation for AC9 (Decision 1b).
  - **ADR-034** — the `ConversationAiClient` Protocol, the fourth application of the swappable-Protocol pattern,
    including the documented `process_turn` signature generalization (Decision 2).
  - **ADR-035** — AC3/AC5 honestly deferred as an MVP gap (Decision 2b).
  - **ADR-036** — the revise-answer truncate-and-regenerate mechanism, corrected to soft-delete via a partial
    unique index, plus the additive `abandoned` enum value (Decision 5).
- **`docs/AI/13_OPEN_DECISIONS.md`** — new item 13: real LLM vendor selection and RAG grounding implementation,
  tracking Open Question 1 (which vendor), AC3, and AC5 as one still-open, CTO-accepted MVP gap.
- **`docs/AI/04_DATABASE.md`** — Conversation / AI Intake Domain marked shipped; `abandoned` confirmed as a live
  enum value; `structured_criteria` column added to the `conversation_sessions` table; `messages`' unique
  constraint documented as a partial index mirroring `uq_saved_addresses_customer_default`.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 7 now shows `AI-001` done; Executive Summary, Section 8
  (Sprint Progress), Section 9 (Backend Capabilities), Section 14 (Repository State), Section 15 (Current
  Limitations), Section 16 (Overall Progress), and Section 17 (Next Planned Story) all updated.
- **`docs/CHANGELOG.md`** — new `[Unreleased]` entry for AI-001 (backend + mobile), including both bug fixes.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `AI-001` row** still needs its Status updated to "Done" and rolled up through
  ML7-EP03/ML7/SP07/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure.
- **Real LLM vendor selection** (`13_OPEN_DECISIONS.md` item 13) remains genuinely open — this story executes the
  CTO's decision to ship the rule-based interim client for MVP; it does not resolve which real vendor eventually
  replaces it.
- **`AI-002`** (routing low-confidence sessions to manual matching) remains unplanned — this closeout does not
  plan it.
- **The two design-debt items** (the rule-based client's replay fragility, mobile's narrower revise-exposure
  choice) remain exactly as reviewed and accepted above — not tracked as new open-decision items, since neither
  blocks anything and both are fully explained in this document and in the code's own docstrings.

---

## Testing Performed

- `backend` implementation: new test suite across `test_conversation_ai_client.py`, `test_conversation_service.py`,
  `test_structured_criteria.py`, `test_conversation_api.py`, and `test_grounding.py`.
- `frontend` implementation: new test suite across `ai_conversation_screen_test.dart` and
  `conversation_repository_test.dart`, backed by `fakes/fake_conversation_repository.dart`.
- `tester` agent: all 11 ACs independently verified; one genuine bug found (the mobile 422 error-mapping
  conflation) and fixed, proven via a regression test that went from failing (`bc37164`) to passing (`ac1e8c1`).
- `architect` agent: two review passes — the first flagged a minor `PrimaryButton` nit (fixed); the second, a
  genuine standards violation (hard-delete vs. this codebase's soft-delete convention, fixed and re-verified
  clean).
- User (CTO) sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_10_1000-ef7b7d439f40_conversation_domain.py` (new migration)
- `backend/app/modules/conversation/models.py` (new — `ConversationStatus`, `MessageSender`,
  `ConversationSession`, `Message`, `ConfidenceScore`)
- `backend/app/modules/conversation/services/conversation_ai_client.py` (new — `ConversationAiClient` Protocol,
  `RuleBasedConversationAiClient`)
- `backend/app/modules/conversation/services/structured_criteria.py` (new — `StructuredCriteria`,
  `StructuredCriteriaAnswer`)
- `backend/app/modules/conversation/services/conversation_service.py` (new — `ConversationService`)
- `backend/app/modules/conversation/repositories/` (new — `conversation_session_repository.py`,
  `message_repository.py` — soft-delete fix, `confidence_score_repository.py`)
- `backend/app/modules/conversation/api.py`, `schemas.py`, `dependencies.py` (new)
- `backend/tests/modules/conversation/` (new — 5 test files)

### Mobile
- `mobile/lib/features/conversation/` (new — `domain/`, `data/conversation_repository.dart` — 422-mapping fix,
  `state/conversation_controller.dart`, `presentation/screens/ai_conversation_screen.dart` — `PrimaryButton` fix,
  `presentation/widgets/`)
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (new AI-conversation entry point)
- `mobile/test/features/conversation/` (new — 4 test files)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-032 through ADR-036
- `docs/AI/13_OPEN_DECISIONS.md` — item 13
- `docs/AI/04_DATABASE.md` — Conversation / AI Intake Domain confirmed-shipped
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 7 status, AI-001 done
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **`AI-002`** (routing low-confidence sessions to manual matching, the Wizard-of-Oz fallback) is the next
  genuinely unblocked candidate in Sprint 7 — this closeout does not plan or start it.
- **Real LLM vendor selection** remains the single biggest open product decision this story surfaces
  (`13_OPEN_DECISIONS.md` item 13) — until it resolves, AC3/AC5 stay unmet and the conversation's
  question-answering remains fully rule-based/scripted rather than genuinely conversational.
- **`docs/AI/Project_Tracker.xlsx`'s `AI-001` row** still needs its Status flipped to "Done" and rolled up through
  its Epic/Milestone/Sprint/Phase Tracker/Dashboard — handled separately via the raw-XML-safe procedure.
