# Plan for Story AI-001 — Describe My Service Need in a Guided AI Conversation

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Epic:** ML7-EP03 | **Milestone:** ML7 | **Phase:** PH2 |
**Depends On:** CTG-001 (done), DIR-001 (done, referenced for conventions only — not a functional dependency)

---

## Story

As a registered Customer, I want to describe my service need in my own words and have the app ask me a few
guided follow-up questions, so that the platform understands my problem well enough to find the right provider —
without me having to fill out a rigid form or already know the right category name.

This is the product's differentiated core mechanism (`00_PROJECT_CONTEXT.md` §3, `11_MVP_SCOPE.md` Stage 2):
an LLM-API-driven, RAG-grounded conversational intake that resolves a free-text problem description to a
Category, then asks only category-locked follow-up questions (`category_question_templates`, shipped by
`CTG-001`), tracking a confidence score that will eventually drive automated-vs-manual routing.

---

## A Note on How This Plan Was Produced — Please Read Before Treating the ACs Below as Final

`docs/AI/Project_Tracker.xlsx` is a binary `.xlsx` workbook. Every tool available to this planning session
(`Read`, `Grep`, `Glob`) either refuses binary files outright or — for `Grep` — silently finds nothing, because
the file's actual text is inside compressed XML that plain-text pattern matching cannot see. **This session had
no way to open the spreadsheet and read AI-001's row verbatim**, exactly the same limitation `Plan_S07_CTG-001.md`
recorded for the same file one story ago (see that Plan's own "session could not independently verify the ACs...
against the primary source" note).

The Acceptance Criteria below are therefore **reconstructed**, not transcribed — assembled from every other
authoritative source that describes this story's scope in detail: `03_DOMAIN_MODEL.md`'s "Conversation / AI
Intake Session" entity (line 150), `04_DATABASE.md`'s `conversation` schema spec (`conversation_sessions`,
`messages`, `confidence_scores`, and the `search_request_status` enum, which turned out to carry real design
information — see Decision 1), `14_USER_FLOWS.md` Flow 4 steps 1–5, `15_SCREEN_INVENTORY.md` (`S-06`, `S-07`),
`16_UX_GUIDELINES.md`'s dedicated AI Conversation latency/UX section, `11_MVP_SCOPE.md`'s Stage 2 description, and
`.agents/skills/ai-conversation-engineering/`'s four Core Directives. These sources are unusually detailed and
mutually consistent for this feature — more so than most prior stories' reconstructions — but this must still be
confirmed against the Tracker's literal text by whoever next has spreadsheet access, ideally before or during
`backend` implementation, per the same convention `CTG-001` established.

**The single biggest scope decision in this Plan — how much of Flow 4 belongs to `AI-001` versus its sibling
`AI-002` — is also reconstructed, not confirmed, and is flagged as an open question below (see "Open Questions").**

---

## Acceptance Criteria (reconstructed — see note above)

1. An authenticated Customer can start a new Conversation Session by submitting a free-text description of their
   problem; a `conversation_sessions` row is created (`status = active`) and the description is persisted as the
   first `messages` row (`sender = customer`, `sequence_number = 1`).
2. The AI attempts to resolve a Category from the free text. Once resolved, it asks only follow-up questions
   sourced from that Category's `category_question_templates` — never an invented question outside the seeded
   taxonomy (`.agents/skills/ai-conversation-engineering/SKILL.md` Core Directive 4). If no category can be
   confidently resolved from the free text alone, the customer is asked to choose from the list of active
   categories (`CategoryService.list_active_categories`) rather than the AI silently guessing.
3. Every customer answer and every AI question/response is persisted as an ordered `messages` row
   (`sequence_number` strictly increasing per session), never lost or overwritten.
4. The Customer can revise a previously given answer without restarting the whole conversation
   (`16_UX_GUIDELINES.md` UX Principle 3); a "Start over" option also exists, but is never the only way back.
5. After each turn, a confidence value is computed and persisted to `confidence_scores`; the latest value is
   cached on `conversation_sessions.final_confidence_score`.
6. When confidence reaches the configured threshold, `conversation_sessions.status → completed`.
7. When confidence cannot reach the threshold within a bounded number of turns, `conversation_sessions.status →
   routed_to_admin` — the Customer is never left stuck in an endless question loop, and never sees this framed as
   a failure (`16_UX_GUIDELINES.md`: "the user must never see the words 'manual' or 'fallback'").
8. The AI must never assert availability, prices, ratings, or provider capabilities not grounded in real
   platform data (`00_PROJECT_CONTEXT.md` §3, hard constraint) — verified structurally by construction (see
   Decision 2), not merely by prompt instruction.
9. The conversation responds in the Customer's preferred language (English/Arabic), read from their existing
   `customer_preferences.language`.
10. Mobile: the AI Conversation screen (`S-07`) exists — chat transcript, typing indicator with the tiered
    latency behavior `16_UX_GUIDELINES.md` specifies (0–500ms indicator only, 500ms–3s indicator only, >3s a
    contextual label, >8s a graceful hand-off), quick-reply chips for `single_select`/`multi_select` questions,
    free-text input otherwise — reachable from a new entry point on the current Home placeholder screen.
11. Automated tests cover: category resolution → only-taxonomy follow-up questions; the confidence-threshold
    branch (`completed` vs. `routed_to_admin`); the revise-a-previous-answer flow; and that no code path can ever
    persist a question or fact not sourced from `category_question_templates`/real platform data.

---

## Open Questions — Need CTO Input Before or Early In `backend` Implementation

These are not "nice to resolve eventually" — each one changes what gets built, and none is answered anywhere in
`docs/AI/` today (confirmed by direct search of `13_OPEN_DECISIONS.md`, `09_DECISIONS.md`, `12_TECH_STACK.md`).

1. **Which real LLM provider/API does the real, non-interim `ConversationAiClient` call?** No LLM SDK, API key
   setting, or vendor decision exists anywhere in this codebase (`12_TECH_STACK.md`'s "ChatGPT" entry is listed
   under *Development Tools* — i.e. a tool the human engineering team uses to write code — not the product's own
   runtime AI provider). `11_MVP_SCOPE.md` calls the intake conversation "LLM-API + RAG-grounded" and
   `00_PROJECT_CONTEXT.md` names it the product's single differentiated core mechanism — unlike OCR
   (ADR-018)/file storage (ADR-017)/Google Places (ADR-031), which are supporting infrastructure this codebase
   could afford to ship as an honest stub for a while, **this is the feature itself**. Decision 2 below proposes
   building the swappable Protocol now (needed regardless of the answer) plus one interim, honest, fully
   rule-based implementation — genuinely useful today, but **not** the "understands unstructured free text"
   capability the story's own title promises. Recommend: this Plan proceeds with the Protocol + interim
   implementation so `backend`/`frontend` can start immediately against a real, working API — but the CTO should
   decide the real LLM vendor (and provision credentials) as a fast-follow, not treat the interim client as a
   finished feature.
2. **Cost/rate controls for real LLM calls** — once a real provider is wired in, per-session token/cost limits,
   timeout, and retry policy are unaddressed anywhere in `docs/AI/`. Not blocking for this story (the interim
   client makes no external calls at all), but worth deciding before Open Question 1 is resolved, so the real
   implementation isn't built against an unbounded-cost default.
3. **The `AI-001`/`AI-002` scope boundary** — this Plan scopes `AI-001` to the `conversation` schema/module only
   (session lifecycle, turns, confidence, category resolution) and explicitly **not** to creating
   `search.search_requests`, running any matching, or creating `administration.manual_match_assignments` rows —
   see Decision 1 for the reasoning (the `search_request_status` enum's values — `matched` / `unmatched` /
   `pending_manual_match` — are matching *outcomes*, which only make sense to set once matching genuinely runs,
   which this story does not do). This reads as the more coherent split, but it is this session's own inference,
   not a confirmed reading of the Tracker's actual `AI-002` row. If `AI-002`'s real scope is materially different
   (e.g. it doesn't exist as a separate story and this was meant to include matching), this Plan's Explicitly Out
   of Scope section would need revisiting before `backend` starts.
4. **Item 10 in `13_OPEN_DECISIONS.md`** (degree of manual/Wizard-of-Oz matching at launch) is still Open and
   explicitly named as blocking "the AI-Guided Service Intake sprint's confidence-threshold routing design." This
   Plan proceeds with a config-driven threshold (Decision 4) precisely so the *numeric* answer to that open
   decision is a settings change, not a code change — but the underlying product question (how much of matching
   should be automated vs. admin-assisted at launch) remains genuinely unresolved and is not this Plan's place to
   answer.

---

## Verified Current State (read directly from code and docs)

- **The full `conversation` schema is already specified**, unbuilt: `04_DATABASE.md` lines 588–628 give
  `conversation_sessions` (`customer_id`, `category_id` nullable, `status`, `final_confidence_score`,
  `started_at`, `completed_at`), `messages` (`conversation_session_id`, `sender`, `content`, `sequence_number`,
  `uq_messages_session_sequence`), and `confidence_scores` (`conversation_session_id`, `score`, `model_version`,
  `computed_at`) column-for-column. No migration or module exists yet for any of them (confirmed:
  `backend/app/modules/` has no `conversation` directory; `backend/alembic/versions/` has no such migration).
- **`category.CategoryService` is real, tested, and ready to consume** (`CTG-001`, shipped):
  `list_active_categories() -> list[Category]` and `get_question_templates(category_id) -> list[
  CategoryQuestionTemplate]`, wired via `category/dependencies.py:get_category_service()`. Both return raw ORM
  entities — this story's first real cross-module consumer, exactly as `Plan_S07_CTG-001.md` anticipated.
  `Category` has `name`/`name_ar`/`slug`/`sort_order` (no keyword/synonym list); `CategoryQuestionTemplate` has
  `question_text`/`question_text_ar`/`question_type`/`options` (JSONB, populated for `single_select`/
  `multi_select`)/`is_required`/`sort_order`.
- **`customer.CustomerService.get_my_profile(user_id) -> (CustomerProfile, CustomerPreferences)`** already exists
  and is get-or-create (never 404s on the caller's own data) — `CustomerProfile.id` is the `customer_id` this
  story's `conversation_sessions.customer_id` FK needs, and `CustomerPreferences.language` (`LanguageCode` enum,
  `EN`/`AR`) is exactly the bilingual signal Decision 6 needs. This is the identical cross-module shape ADR-014
  established (`identity → customer`) and PRO-001/VER-001 reused since — a new `conversation → customer` edge
  follows the same constructor-injection, same-session pattern.
- **No LLM/AI-provider SDK, API key setting, or credential exists anywhere** (confirmed: `grep` across
  `backend/app/core/config.py` and `backend/pyproject.toml` for `openai|anthropic|OPENAI|ANTHROPIC|API_KEY` finds
  only the unrelated `GOOGLE_PLACES_API_KEY`). This is the fourth time this codebase has hit exactly this shape of
  problem — an external capability with no confirmed implementation — after `FileStorage` (ADR-017),
  `DocumentOcrService` (ADR-018), and `GooglePlacesClient` (ADR-031), each solved the same way: a swappable
  Protocol plus an honest concrete implementation.
- **`search` module (DIR-001) owns no persisted state at all today** — no `models.py`, no `repositories/`; it is
  a stateless read-layer over `provider.ProviderService`'s existing queries (`search/services/search_service.py`'s
  own docstring: "structured (pre-AI) provider search"). `search.category` (its `search_providers` parameter) is
  a free-text label string matched against `provider_category_labels` (ADR-027's exact-match interim posture) —
  **not** a `category_id`. This confirms `13_OPEN_DECISIONS.md` item 1's own caveat that reconciling
  `provider_category_labels` into the real `category.provider_categories` join table (still empty) remains a
  separate, unresolved gap — one this story cannot and does not paper over (Decision 1).
- **`04_DATABASE.md` line 179 spells out `search_request_status`'s enum values: `matched`, `unmatched`,
  `pending_manual_match`.** These are matching *outcomes*, not "request received" states — read together with
  Flow 4 steps 5–6 (search_requests creation and matching filters happen in the same flow), this is the concrete
  evidence Decision 1 uses to scope `search.search_requests` creation, and any real matching, out of this story.
- **`administration.manual_match_assignments` is fully unbuilt** (spec only, `04_DATABASE.md` lines 866–878);
  its `assigned_admin_id` is `NOT NULL` at creation, which `09_DECISIONS.md` ADR-030 already flagged (in a
  different story's context) as not fitting an "unassigned queue, any admin may pick up" shape, since no
  admin-assignment/round-robin mechanism exists anywhere in this codebase. Under Decision 1's scope boundary,
  this problem belongs to whichever future story actually creates this table, not to `AI-001`.
- **Home (`S-06`) does not exist yet.** `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart`
  is an explicit stub (its own docstring: "The full AI Conversation entry point (S-06/S-07) remains a future
  story") with a "Find a Service" button that opens DIR-001's structured Search Filters screen — not the AI
  conversation. `CLM-001` already established the precedent of adding a second entry-point button to this same
  placeholder file (`claimEntryPointLabel`) rather than building a new Home screen prematurely; this story follows
  the same precedent (Decision 7).
- **`S-08` (Search Results) already exists** (`mobile/lib/features/search/presentation/screens/search_results_screen.dart`,
  DIR-001) but is wired only to DIR-001's structured browse, not to any AI-conversation output — consistent with
  Decision 1's scope boundary, this story does not touch it.
- **Endpoint-shape precedent (ADR-015):** a Conversation Session is a genuine 1:N collection per Customer (many
  past/present sessions), so it takes the `{id}`-addressable shape with `ensure_owner_or_not_found`
  (`app/core/authorization.py`), the same shape as `/auth/sessions/{session_id}` and
  `/customers/me/addresses/{address_id}`.

---

## Architecture Decisions

### Decision 1 — Scope boundary: `AI-001` owns the `conversation` schema/module only; it does not create `search.search_requests`, run any matching, or create `administration.manual_match_assignments`

**The problem:** Flow 4 describes one continuous journey (steps 1–8) from free-text description through to a
ranked provider list, but the Tracker splits Sprint 7's Conversation/AI Intake domain into two stories,
`AI-001`/`AI-002`, and this session cannot read the Tracker's literal split (see the note at the top of this
Plan). A wrong scope call here either duplicates work `AI-002` was meant to do, or ships `AI-001` without a
coherent stopping point.

**Chosen:** `AI-001` ends at `conversation_sessions.status ∈ {completed, routed_to_admin}` — a fully real,
complete, and independently useful domain slice (the guided conversation itself), with **zero** writes to the
`search` or `administration` schemas. The concrete evidence for this boundary: `search_request_status`'s three
enum values (`matched`, `unmatched`, `pending_manual_match`, `04_DATABASE.md` line 179) are all matching
*outcomes* — there is no "submitted, awaiting processing" value in the locked enum. Creating a `search_requests`
row now would force inventing an unspecified interim status (an unrequested schema deviation) or leaving a row in
a state the locked enum doesn't describe. It is more coherent for whichever story actually runs matching
(`AI-002`, most plausibly) to create `search_requests` with its final, correct status already known at creation
time — mirroring exactly how `CLM-001`'s `create_google_seeded_provider` sets `verification_status=approved`
*at creation*, never as a later patch to an interim value (ADR-029).

**Consequence for the customer-facing experience:** the mobile completion state after a `completed` or
`routed_to_admin` session is an honest, plain confirmation ("Thanks — we're finding matches for you," per
`16_UX_GUIDELINES.md`'s own locked microcopy for this exact moment), not a results list — because no results
exist yet at the code level. This is the same "ship a real, complete domain slice ahead of its future consumer"
shape `CTG-001` already established for `CategoryService`.

**Alternatives considered and rejected:**
- **Build the whole Flow 4 (conversation + matching + results) as one story** — rejected: `.agents/agents.md`
  explicitly instructs not to combine stories, and no explicit instruction to do so was given here; the
  Tracker's own row split (`AI-001`, `AI-002`) is evidence two stories were intended even though this session
  can't read their literal boundary.
- **Create `search_requests` now with a new, unspecified `pending`/`submitted` status value** — rejected: adds an
  enum value to a table this story doesn't otherwise need to touch, purely to paper over a scope question, and
  risks colliding with whatever `AI-002` actually needs that enum to mean.
- **Skip persisting anything beyond `conversation_sessions`/`messages`, treat `confidence_scores` as optional** —
  rejected: AC5/AC6/AC7 explicitly require the persisted, auditable confidence trail
  (`.agents/skills/ai-conversation-engineering/confidence-scoring-and-fallback.md`: "never compute a score without
  persisting it").

### Decision 2 — LLM integration: swappable `ConversationAiClient` Protocol (fourth application of the `FileStorage`/`DocumentOcrService`/`GooglePlacesClient` pattern), with an interim, fully deterministic `RuleBasedConversationAiClient`

**The problem:** no LLM provider, SDK, or credential is confirmed anywhere in this codebase or environment (see
Open Question 1), and guessing a vendor/API shape would be exactly the kind of speculative work ADR-018 already
rejected for OCR ("Build or partially reverse-engineer a specific vendor's... integration now").

**Chosen:** `conversation/services/conversation_ai_client.py` defines:
- `ConversationTurnResult` (a small dataclass/Pydantic model): `reply_message: str`, `reply_message_ar: str |
  None`, `resolved_category_id: uuid.UUID | None`, `is_complete: bool`, `confidence: float`, `quick_reply_options:
  list[str] | None` (for rendering chips when the current question is `single_select`/`multi_select`).
- `ConversationAiClient` (`Protocol`): `async def process_turn(self, *, session: ConversationSession, history:
  list[Message], categories: list[Category], active_question: CategoryQuestionTemplate | None, customer_message:
  str, language: LanguageCode) -> ConversationTurnResult`.
- `RuleBasedConversationAiClient` — the only implementation shipped by this story. **Category resolution:**
  case-insensitive substring match of the customer's free text against each active `Category.name`/`name_ar`/
  `slug`; if exactly one category matches, resolve it; if zero or more than one match, return a clarifying
  `ConversationTurnResult` (`resolved_category_id=None`, `quick_reply_options` = the full active category list)
  asking the customer to pick one directly — never a guessed category. **Follow-up questions:** once a category
  is resolved, walk `CategoryQuestionTemplate` rows in `sort_order`, one at a time, verbatim (`question_text`/
  `question_text_ar` per Decision 6) — the AI never phrases or invents a question itself. **Confidence:** `0.0`
  while unresolved, rising in equal steps as required questions are answered, `1.0` once every `is_required=true`
  question for the resolved category has a persisted answer — a genuine, real, auditable score (unlike
  `StubDocumentOcrService`'s always-`0.0`), just not an LLM-derived probability. `confidence_scores.model_version`
  is tagged `"rule_based_v1"`, ready to be replaced by a real model/prompt-version string the moment Open
  Question 1 resolves.
- `ConversationService` depends on the `ConversationAiClient` Protocol only, wired via
  `conversation/dependencies.py:get_conversation_ai_client()` — a future real implementation
  (`OpenAiConversationAiClient`, `AnthropicConversationAiClient`, or whichever provider is chosen) is one new
  class plus one dependency-wiring change, zero changes to `ConversationService` itself.

**This directly satisfies AC8's grounding requirement by construction, not merely by prompt instruction:** the
interim client has no code path that can emit a question, category, or fact that didn't come from
`category.categories`/`category_question_templates` — there is no free-text generation capability in
`RuleBasedConversationAiClient` at all beyond echoing verbatim template text. A future real LLM implementation
must preserve this same structural guarantee (Decision 5 defines exactly how).

**Alternatives considered and rejected:**
- **Wire a real LLM API now, picking a provider unilaterally** — rejected: `.agents/agents.md` requires explicit
  approval before introducing a new external dependency/vendor, and doing so without a credential to actually
  test against would be exactly the unverifiable work ADR-018/ADR-031 already declined for a similar shape of
  problem.
- **Block this entire story on Open Question 1** — rejected: the Protocol boundary, the full `conversation` schema
  build, the confidence/turn-cap mechanics (Decision 4), the revise-a-previous-answer flow (Decision 5), and the
  mobile chat screen (Decision 7) are all real, valuable, and fully buildable and testable today, independent of
  which LLM is eventually chosen — shipping them now, with an honest interim client, is strictly better than
  waiting.
- **A keyword/synonym list stored as new columns on `Category`** (to make substring matching less fragile) —
  rejected as unrequested schema scope creep; `13_OPEN_DECISIONS.md` item 1 already locked the Category schema,
  and no AC asks for a synonym system. The interim client's honest fallback (ask the customer to pick from the
  list) covers the gap without a schema change.

### Decision 3 — Cross-module edges: `conversation → customer` and `conversation → category`, both one-directional, constructor-injection, same-session

Mirrors ADR-014/ADR-016 exactly. `ConversationService` takes `CustomerService` (resolve `customer_id` +
`language` from the caller's `user_id` at session-start, Decision-2/6's inputs) and `CategoryService` (list
active categories, fetch a category's question templates) as constructor dependencies, wired via
`conversation/dependencies.py`. Confirmed zero-cycle: neither `customer` nor `category` gains any import from
`conversation`.

### Decision 4 — Confidence threshold and turn cap are `Settings`, not code

Mirrors VER-001's "business verification type is an app-config decision, not a schema decision" precedent
(`13_OPEN_DECISIONS.md` item 5) and directly serves item 10's still-open "degree of manual matching" question:
whatever the eventual product answer, this story makes it a settings change.

- `CONVERSATION_CONFIDENCE_THRESHOLD: float = 1.0` — since `RuleBasedConversationAiClient` only ever produces
  `0.0` or `1.0` (fully resolved or not), the interim client's own behavior makes any value `<1.0` behave
  identically to `1.0`; the setting exists now so a future real LLM's genuinely fractional confidence has
  something to compare against without a code change.
- `CONVERSATION_MAX_TURNS: int = 12` — a hard cap: if a session has not reached `completed` after this many
  customer turns, it is force-routed (`status = routed_to_admin`) rather than looping indefinitely — satisfies
  AC7's "never leave the customer stuck" requirement even for the interim client's simple category-clarification
  loop (e.g. a customer whose free text never substring-matches any category name and who does not pick one from
  the offered chips after repeated attempts).

### Decision 5 — Revising a previous answer: truncate-and-regenerate, not a parallel edit mechanism

**The problem (AC4):** `16_UX_GUIDELINES.md` UX Principle 3 requires the customer be able to go back and revise a
previous answer without restarting the whole conversation. Editing an early answer can invalidate every AI
question that came after it (e.g. revising which appliance is broken invalidates appliance-specific follow-ups
already asked).

**Chosen:** `PATCH /conversations/{session_id}/answers/{message_id}` — `message_id` must reference an existing
`sender=customer` message in that session. The service (a) updates that message's `content`, (b) hard-deletes
every `messages` row (customer and AI alike) with a strictly greater `sequence_number` in the same session, (c)
re-invokes `ConversationAiClient.process_turn` with the now-shorter history to generate the next turn fresh,
appended at the next available `sequence_number`. From the mobile client's perspective this reads as "the chat
continues from the edited point," never a restart. **"Start over"** is deliberately simpler and separate: a new
`POST /conversations` call starts a fresh session; the previous session is left exactly as it was (marked
`abandoned` — see below) rather than deleted, preserving it as an honest historical record.

**A small, additive enum value:** `conversation_status` gains `abandoned` (alongside `active`/`completed`/
`routed_to_admin`, the three values Flow 4's prose names directly) — set when a customer starts a new session
while a previous one is still `active`. This is a genuinely new value beyond what `04_DATABASE.md`'s text
explicitly enumerates, flagged here (mirroring `CLM-001`'s handling of its own genuinely-new
`claim_review_requests` table) for a `04_DATABASE.md` update at story close if approved.

**Alternatives considered and rejected:**
- **In-place edit only, leave subsequent AI messages stale** — rejected: would show the customer AI questions
  that no longer make sense for their revised answer (e.g. an "AC" follow-up question after they changed their
  category to "Plumbing"), directly undermining trust.
- **Soft-delete truncated messages instead of hard-delete** — rejected: `messages` has no `deleted_at`/soft-delete
  column in `04_DATABASE.md`'s spec (unlike `CommonColumnsMixin`-based tables), and inventing one purely for this
  mechanism is unrequested schema scope; a truncated, superseded AI question has no audit value worth preserving
  the way a verification record does.
- **Silently leave `active` sessions abandoned with no status change when a new one starts** — rejected: makes
  "how many conversations did a customer actually finish vs. give up on" ungoverned and unqueryable, undermining
  the same admin-analytics spirit `search_event_log`/`unmatched_query_reports` exist for elsewhere in this domain.

### Decision 6 — Bilingual handling

`ConversationService` resolves `CustomerPreferences.language` once, at session start (via `CustomerService.
get_my_profile`), and passes it into every `ConversationAiClient.process_turn` call.
`RuleBasedConversationAiClient` selects `question_text_ar`/`Category.name_ar` when `language=AR` and the
Arabic field is non-null, falling back to the English field when it is null — matching `CTG-001`'s own framing
of `name_ar`/`question_text_ar` as "nullable until populated," never a hard failure.

### Decision 7 — Endpoint shape (ADR-015) and module/mobile layout

**Backend**, new `backend/app/modules/conversation/` module (mirrors `category`'s exact file layout):
- `POST /conversations` (AC1) — body `{message: str}`; creates the session + first customer message + first AI
  turn; `require_role(ROLE_CUSTOMER)`.
- `POST /conversations/{session_id}/messages` (AC2/AC3/AC5/AC6/AC7) — body `{content: str}` (free text) or
  `{selected_option: str}` (a quick-reply chip choice, mapped to `content` server-side for persistence
  consistency); `ensure_owner_or_not_found` against the session's `customer_id`.
- `PATCH /conversations/{session_id}/answers/{message_id}` (AC4, Decision 5).
- `GET /conversations/{session_id}` (resume after app restart, review transcript) — `ensure_owner_or_not_found`.

**Mobile**, new `mobile/lib/features/conversation/` feature (mirrors `claim`'s exact layout from `CLM-001`):
`domain/models/`, `data/conversation_repository.dart`, `presentation/screens/ai_conversation_screen.dart` (`S-07`),
`state/conversation_controller.dart` (Riverpod), `core/routing/app_routes.dart` entry. Entry point: a new primary
button on `home_placeholder_screen.dart` ("Describe what you need" or similar, exact copy per
`15_SCREEN_INVENTORY.md`'s `S-06` description) opening `ai_conversation_screen.dart` directly — the same
"add a button to the existing placeholder" precedent `CLM-001` already used for its own entry point, since real
`S-06` still doesn't exist. Chat UI implements `16_UX_GUIDELINES.md`'s exact latency tiers (0–500ms/500ms–3s
indicator only, >3s contextual label e.g. "Thinking about your answer," >8s graceful hand-off copy — though the
interim rule-based client responds well under 500ms in practice, the UI logic must not assume that will always be
true once a real LLM is wired in) and never freezes the input field while "thinking" (queues instead).

---

## Backend — Proposed Changes

### Migration
1. One new Alembic migration (down-revision = `602bf3c4bea7`, `claim_review_requests`, the current head).
   Creates the `conversation` schema; `conversation_status` enum (`active`, `completed`, `routed_to_admin`,
   `abandoned` — Decision 5's addition); `message_sender` enum (`customer`, `ai`); `conversation_sessions`,
   `messages` (with `uq_messages_session_sequence`), `confidence_scores` — column-for-column per `04_DATABASE.md`
   lines 588–628, plus the one additive enum value. No changes to any existing table.

### `conversation` module (new)
2. `models.py` — `ConversationStatus`, `MessageSender` enums; `ConversationSession`, `Message`,
   `ConfidenceScore` ORM models.
3. `repositories/conversation_session_repository.py` — `create`, `get_by_id`, `get_active_for_customer`,
   `update_status`, `set_category`, `update_final_confidence`.
4. `repositories/message_repository.py` — `create`, `list_for_session` (ordered), `get_by_id`,
   `delete_after_sequence(session_id, sequence_number)` (Decision 5), `get_next_sequence_number`.
5. `repositories/confidence_score_repository.py` — `create`, `get_latest_for_session`.
6. `services/conversation_ai_client.py` — `ConversationTurnResult`, `ConversationAiClient` Protocol,
   `RuleBasedConversationAiClient` (Decision 2).
7. `services/conversation_service.py` — `ConversationService`: `start_conversation(user_id, message) ->
   ConversationSession`; `submit_turn(user_id, session_id, content) -> ConversationSession`; `revise_answer(
   user_id, session_id, message_id, content) -> ConversationSession` (Decision 5); `get_session(user_id,
   session_id) -> ConversationSession`. Depends on `ConversationAiClient`, `CustomerService`, `CategoryService`
   (Decision 3), and the three repositories above.
8. `api.py` — the four routes in Decision 7, mounted `/conversations`.
9. `schemas.py` — `StartConversationRequest`, `SubmitTurnRequest`, `ReviseAnswerRequest`,
   `ConversationSessionResponse` (id, status, category_id, messages: list of `{sender, content, sequence_number,
   created_at}`, quick_reply_options if the current turn expects a chip choice).
10. `dependencies.py` — `get_conversation_ai_client`, `get_conversation_session_repository`,
    `get_message_repository`, `get_confidence_score_repository`, `get_conversation_service`.
11. Exceptions: `ConversationSessionNotFoundError` (404), `ConversationSessionNotActiveError` (409 — submitting a
    turn to a `completed`/`routed_to_admin`/`abandoned` session), `AnswerNotRevisableError` (409/422 — targeting a
    non-existent or non-customer message).

### Config (`backend/app/core/config.py`)
12. `CONVERSATION_CONFIDENCE_THRESHOLD: float = 1.0` (Decision 4).
13. `CONVERSATION_MAX_TURNS: int = 12` (Decision 4).

### API wiring
14. `backend/app/api/v1/api.py` — mount the new `conversation_router` (prefix `/conversations`).
15. `backend/tests/conftest.py` — register the three new ORM models for `Base.metadata.create_all()`.

### Tests
16. `backend/tests/modules/conversation/test_conversation_ai_client.py` — `RuleBasedConversationAiClient`:
    resolves an unambiguous category from free text; asks a clarifying category-pick question on zero/multiple
    matches; walks a resolved category's questions in `sort_order`, never inventing one; confidence reaches `1.0`
    only once every required question is answered; Arabic field selection when `language=AR` with a graceful
    English fallback when the Arabic field is null (AC2, AC8, AC9).
17. `backend/tests/modules/conversation/test_conversation_service.py` — `start_conversation` creates session +
    first message (AC1); `submit_turn` persists ordered messages, computes and persists a `confidence_scores` row
    each turn, caches `final_confidence_score` (AC3, AC5); confidence reaching the threshold sets
    `status=completed` (AC6); exceeding `CONVERSATION_MAX_TURNS` without completing sets `status=routed_to_admin`
    (AC7); `revise_answer` truncates every later message and regenerates the next turn (AC4, Decision 5);
    submitting a turn to a non-`active` session raises `ConversationSessionNotActiveError`.
18. `backend/tests/modules/conversation/test_conversation_api.py` — full HTTP round trips: auth/role gating;
    `ensure_owner_or_not_found` returns 404 (never 403) for another customer's session id on every `{session_id}`
    route.
19. `backend/tests/modules/conversation/test_grounding.py` — a direct, structural assertion that no
    `ConversationTurnResult`/persisted `messages.content` for an AI-sender turn can contain text absent from the
    seeded `category_question_templates`/`categories` tables for that session's resolved category (AC8/AC11) —
    the concrete, code-level proof behind Decision 2's "grounded by construction" claim.

---

## Mobile — Proposed Changes

### New feature: `mobile/lib/features/conversation/`
20. `domain/models/conversation_session.dart`, `domain/models/conversation_message.dart`.
21. `data/conversation_repository.dart` — `start(message)`, `submitTurn(sessionId, content)`, `reviseAnswer(
    sessionId, messageId, content)`, `getSession(sessionId)`.
22. `presentation/screens/ai_conversation_screen.dart` (`S-07`, AC10) — chat transcript (customer bubbles
    right-aligned, AI bubbles left-aligned, RTL-mirrored correctly per `16_UX_GUIDELINES.md`'s explicit
    chat-bubble RTL warning), tiered typing indicator, quick-reply chip row when the active turn offers
    `quick_reply_options`, free-text input otherwise (never both disabled at once), tap-to-revise on any past
    customer bubble, an always-visible "Start over" action, and an honest completion state (no fake results list —
    Decision 1) once `status` reaches `completed`/`routed_to_admin`.
23. `state/conversation_controller.dart` (Riverpod) — owns turn submission, the >3s/>8s latency-tier timers,
    queuing additional free-text input typed while a turn is in flight (never blocking the field).
24. `core/routing/app_routes.dart` — new route for `ai_conversation_screen.dart`.

### Entry point
25. `features/home/presentation/screens/home_placeholder_screen.dart` — new primary button ("Describe what you
    need" / final copy TBD with product) opening `ai_conversation_screen.dart`, alongside the existing "Find a
    Service" (structured browse) and "Already listed on Google?" (claim) buttons — mirrors the exact precedent
    `CLM-001` already set for adding a second/third entry point to this same placeholder file.

### Tests
26. `mobile/test/features/conversation/ai_conversation_screen_test.dart` — chip row renders only when the current
    turn expects a selection; free-text input renders otherwise; tapping a past customer bubble opens the revise
    flow and calls the fake repository's `reviseAnswer`; "Start over" starts a fresh session.
27. `mobile/test/features/conversation/fakes/fake_conversation_repository.dart` (mirrors the existing
    fake-repository pattern, e.g. `fake_claim_repository.dart`).

---

## Explicitly Out of Scope (do not implement in this story)

- **Any write to `search.search_requests`, `search.provider_matches`, `search.search_event_log`, or
  `administration.manual_match_assignments`** — Decision 1. A completed or routed-to-admin `conversation_session`
  is this story's entire, honest output; turning it into a matchable, ranked result is a separate story's job
  (most plausibly `AI-002`).
- **Any real geospatial/merit matching against providers**, and any wiring into `S-08` (Search Results) —
  Decision 1; `S-08` remains exactly as DIR-001 left it.
- **Contact View, Outcome Tag, Reviews** — downstream of matching, not reachable without it; unaffected by this
  story either way.
- **A real LLM-provider integration** (OpenAI, Anthropic, or otherwise) — Open Question 1; this story ships the
  Protocol and one interim, honest, deterministic implementation only.
- **Reconciling `provider.provider_category_labels` into the real `category.provider_categories` join table**
  (`13_OPEN_DECISIONS.md` item 1's still-open remainder) — irrelevant to this story's scope (it never queries
  providers at all) but worth naming so it isn't mistaken for something this story should have touched.
- **Any admin-facing consumption UI/endpoint for low-confidence sessions** (Flow 7's admin side) — this story
  doesn't even create the row that flow consumes (Decision 1); `13_OPEN_DECISIONS.md` item 10 explicitly ties
  that dashboard scope to `ADM-001`/`ADM-002` (Sprint 11).
- **Cost controls, rate limiting, or timeout policy for real LLM calls** — Open Question 2; moot while the only
  shipped client makes no external network calls.
- **A synonym/keyword system on `Category`** for more forgiving free-text matching — Decision 2's alternatives.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

**Flagged before `backend` starts, per the Open Questions section above:** Open Question 3 (the `AI-001`/`AI-002`
scope boundary) is the one item genuinely worth a light CTO confirmation before code is written, since it
determines whether this Plan's Explicitly Out of Scope list is correct. Open Questions 1/2/4 do not block
starting `backend` — Decision 2 already specifies a fully buildable, testable interim path for Question 1, and
Question 4 is absorbed by Decision 4's config-driven design regardless of which numeric answer eventually lands.

1. **backend** — Items 1–19. Build order: (a) the migration + `models.py` first; (b) repositories; (c)
   `ConversationAiClient`/`RuleBasedConversationAiClient` (Decision 2) — this is the part most worth extra care,
   since Decision 2's "grounded by construction" claim is only true if every code path is checked; (d)
   `ConversationService` (Decision 1/4/5/6); (e) `api.py`/`schemas.py`/`dependencies.py` last. Read Decision 1 in
   full before starting — the temptation to "just also create a `search_requests` row since it's right there in
   the domain model" is exactly the scope drift this Plan deliberately avoids, for the reasons given.
2. **frontend** — Mobile items 20–27, once the backend endpoints exist (or in parallel against a fake repository).
   Particular attention to Decision 7's latency-tier UI logic and the honest, no-fake-results completion state
   (Decision 1) — this is the most likely place a well-intentioned addition would silently expand this story's
   scope back into `AI-002`'s territory.
3. **tester** — Verify all 11 ACs (mapping below). Particular attention to AC8/AC11 (the grounding tests, item 19)
   and AC4 (the truncate-and-regenerate revise flow actually removes stale AI questions, not just marks them
   somehow superseded).
4. **architect** — Review Decision 1 (the scope boundary and its `search_request_status`-enum evidence) against
   `03_DOMAIN_MODEL.md`/`04_DATABASE.md`'s intent; Decision 2 (the `ConversationAiClient` Protocol) against
   ADR-017/018/031's established pattern for consistency; Decision 5's additive `abandoned` enum value and the
   hard-delete-on-revise mechanism against this codebase's general soft-delete conventions; Decision 3's
   `conversation → customer`/`conversation → category` edges for cycle-freedom.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 1
   (scope boundary), Decision 2 (`ConversationAiClient` Protocol, the pattern's fourth application), and
   Decision 5 (revise/truncate mechanism + the additive `abandoned` status) as new ADRs (next available:
   **ADR-032** onward); update `04_DATABASE.md` (mark the `conversation` schema as shipped, add the `abandoned`
   enum value); update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 7 section.

---

## Verification Plan (mapped to the 11 ACs)

| AC | Verified by |
|---|---|
| 1 | `test_conversation_service.py`/`test_conversation_api.py`: `POST /conversations` creates the session (`status=active`) and the first `messages` row correctly. |
| 2 | `test_conversation_ai_client.py`: unambiguous free text resolves a category; ambiguous/no-match text returns a category-pick prompt, never a guess; only-taxonomy question ordering. |
| 3 | `test_conversation_service.py`: `sequence_number` strictly increasing and never overwritten across multiple turns. |
| 4 | `test_conversation_service.py` (`revise_answer`) + `ai_conversation_screen_test.dart`: truncation and regeneration proven at both the service and UI level. |
| 5 | `test_conversation_service.py`: a `confidence_scores` row is written every turn; `final_confidence_score` matches the latest. |
| 6 | `test_conversation_service.py`: threshold reached → `status=completed`. |
| 7 | `test_conversation_service.py`: `CONVERSATION_MAX_TURNS` exceeded without completion → `status=routed_to_admin`; UX copy reviewed by `architect`/`tester` against `16_UX_GUIDELINES.md`'s "never see the words manual/fallback" rule. |
| 8 | `test_grounding.py` — structural proof, not a prompt-instruction claim. |
| 9 | `test_conversation_ai_client.py`: Arabic field selection + English fallback when null. |
| 10 | `ai_conversation_screen_test.dart` + manual/architect review of the latency-tier timers against `16_UX_GUIDELINES.md`'s literal thresholds. |
| 11 | Items 16–19/26 collectively — cross-referenced here so `tester` confirms none was accidentally treated as "someone else's AC." |

---

## Related Documents

- `docs/AI/00_PROJECT_CONTEXT.md` §3 (grounding hard constraint), `11_MVP_SCOPE.md` (Stage 2 — this feature as the
  differentiated core)
- `docs/AI/03_DOMAIN_MODEL.md` (Conversation / AI Intake Session, lines 150–166)
- `docs/AI/04_DATABASE.md` (`conversation` schema, lines 588–628; `search_request_status` enum, line 179 —
  Decision 1's evidence; `manual_match_assignments`, lines 866–878)
- `docs/AI/09_DECISIONS.md` (ADR-014/ADR-016 — cross-module injection shape, Decision 3; ADR-015 — endpoint-shape
  rule, Decision 7; ADR-017/ADR-018/ADR-031 — Protocol-swappability precedent, Decision 2; ADR-027 — the
  `provider_category_labels` free-text posture this story does not touch; ADR-029 — "set the final status at
  creation, never patch an interim one" precedent, Decision 1)
- `docs/AI/12_TECH_STACK.md` (no LLM vendor named — Open Question 1)
- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy, resolved/implemented by `CTG-001`, consumed here;
  item 5 — config-not-schema precedent, Decision 4; item 10 — Wizard-of-Oz degree, still Open, Decision 4/Open
  Question 4)
- `docs/AI/14_USER_FLOWS.md` Flow 4 (steps 1–5 are this story's scope; steps 6+ are not, Decision 1)
- `docs/AI/15_SCREEN_INVENTORY.md` (`S-06`, `S-07`)
- `docs/AI/16_UX_GUIDELINES.md` (AI Conversation latency section; UX Principle 3 — revise without restarting;
  Wizard-of-Oz invisibility rule)
- `.agents/skills/ai-conversation-engineering/SKILL.md` and its two rule files (grounding/RAG,
  confidence-scoring-and-fallback) — the four Core Directives this Plan builds against directly
- `docs/implementation/plans/Plan_S07_CTG-001.md` / `Walkthrough_S07_CTG-001.md` (the `CategoryService` this story
  consumes, and the "reconstructed ACs, Tracker unreadable" precedent this Plan follows)
- `docs/implementation/plans/Plan_S06_CLM-001.md` (Protocol-swap precedent, Decision 2; the
  "add a button to `home_placeholder_screen.dart`" entry-point precedent, Decision 7)

---

**End of Document**
