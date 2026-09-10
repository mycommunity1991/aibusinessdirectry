# Plan for Story AI-001 — Describe My Service Need in a Guided AI Conversation

**Sprint:** 07 (Category Domain / AI Intake foundation) | **Epic:** ML7-EP03 | **Milestone:** ML7 | **Phase:** PH2 |
**Depends On:** CTG-001 (done), DIR-001 (done, referenced for conventions only — not a functional dependency)

---

## Story

As a registered Customer, I want to describe my service need in my own words and have the app ask me a few
guided follow-up questions, so that the platform understands my problem well enough to find the right provider —
without me having to fill out a rigid form or already know the right category name.

Verbatim from `docs/AI/Project_Tracker.xlsx` (Stories sheet, `AI-001` row): "As a customer, I want to describe my
problem in plain language and answer relevant follow-up questions, so that the app understands what I need
without me having to guess the right category upfront. This is the product's core differentiator: an
LLM-API-driven, RAG-grounded conversational intake. The AI must never assert availability, prices, ratings, or
capabilities not grounded in real platform data — every claim traces back to a retrieved record, and every
follow-up question comes only from the approved `category_question_templates`, never an invented question.
Perceived latency is handled explicitly with staged feedback (typing indicator to contextual label to graceful
timeout) so the AI never reads as an unresponsive app. Scope boundary: routing low-confidence sessions to manual
matching (the Wizard-of-Oz fallback) is `AI-002` — this story covers the conversation itself and its structured
output."

---

## Revision Note (10 September 2026) — Verbatim Tracker Data Now Available

This Plan was originally written without direct access to `docs/AI/Project_Tracker.xlsx` (a binary `.xlsx`
workbook this session's tools could not open); its Acceptance Criteria and the `AI-001`/`AI-002` scope boundary
were **reconstructed** from `03_DOMAIN_MODEL.md`, `04_DATABASE.md`, `14_USER_FLOWS.md`, `15_SCREEN_INVENTORY.md`,
`16_UX_GUIDELINES.md`, and the `ai-conversation-engineering` skill files.

The orchestrator has since obtained direct `openpyxl` access to the Tracker and read the `AI-001` and `AI-002`
rows verbatim. This revision:

1. **Replaces** the reconstructed 11-item AC list with the Tracker's actual, verbatim 11-item AC list (materially
   different in shape — the verbatim list is criteria-level, not the reconstructed list's behavior-level detail;
   most reconstructed behaviors survive as the *implementation* that satisfies a verbatim AC, cross-referenced
   below).
2. **Confirms** Open Question 3 (the `AI-001`/`AI-002` scope boundary) — the verbatim `AI-002` row states its own
   scope boundary as "does not include the admin-side queue UI itself (`ADM-001`) — this story implements the
   routing/data model side and the customer-facing continuity guarantee," which is fully consistent with this
   Plan's Decision 1 (`AI-001` ends at `conversation_sessions.status ∈ {completed, routed_to_admin}`, zero writes
   to `search`/`administration`). **Decision 1 stands, now confirmed rather than inferred.**
3. **Records two CTO decisions** resolving Open Question 1 and the former AC9 gap — see Decision 2b and Decision
   1b below.

The rest of this Plan's architecture (Decisions 3–7, the module/schema layout, the mobile screen) is materially
unchanged; only the AC list, the scope-boundary confidence level, and the two new decisions below are new.

---

## Acceptance Criteria (verbatim, `Project_Tracker.xlsx`, `AI-001` row)

1. `conversation_sessions`, `messages`, and `confidence_scores` tables exist via migration; messages are ordered
   by `sequence_number`.
2. The LLM provider sits behind a service interface (not called directly from routes or the AI conversation
   screen) so the provider can be swapped without touching Domain/API code.
3. System prompts are stored as version-controlled files, not inline strings. — **Deferred (MVP gap)**, see
   Decision 2b.
4. Follow-up questions are sourced only from `category_question_templates` for the resolved category — the AI
   never asks an invented question outside the approved taxonomy.
5. A retrieved provider record with a null field (e.g., no price range) is reported to the customer as unknown,
   never estimated or guessed. — **Deferred (MVP gap)**, see Decision 2b.
6. The AI Conversation screen shows a typing indicator within 500ms, switches to a contextual label past 3
   seconds, and never shows a raw confidence score to the user.
7. A response taking longer than 8 seconds (or timing out) transitions to "we'll notify you" messaging rather
   than an indefinite spinner.
8. The customer can go back and revise a previous answer without restarting the entire conversation.
9. Every completed session produces a `search_requests`-ready `structured_criteria` payload, validated via a
   Pydantic model before persistence.
10. Automated tests assert no fabricated provider attribute is ever surfaced in a conversation response.
11. RTL layout and Arabic prompt/response quality verified for the chat screen.

---

## Open Questions — Status After CTO Decisions A and B (10 September 2026)

1. **Which real LLM provider/API does the real, non-interim `ConversationAiClient` call?** — **Resolved for MVP
   scope, not resolved as a product question.** The CTO has explicitly accepted shipping the rule-based interim
   client (Decision 2 below) for MVP, with AC3 and AC5 honestly marked as not met by this implementation
   (Decision 2b). Real LLM vendor selection remains open and is recorded as a new item in
   `13_OPEN_DECISIONS.md` (item 13 — see Decision 2b) as a fast-follow, not part of this story.
2. **Cost/rate controls for real LLM calls** — still moot; the interim client makes no external calls. Deferred
   alongside Open Question 1 to whenever a real vendor is chosen.
3. ~~The `AI-001`/`AI-002` scope boundary~~ — **CONFIRMED.** The verbatim `AI-002` row's own scope-boundary
   sentence matches this Plan's Decision 1 exactly. No further action needed.
4. **Item 10 in `13_OPEN_DECISIONS.md`** (degree of manual/Wizard-of-Oz matching at launch) remains genuinely
   Open. This Plan proceeds with a config-driven threshold (Decision 4) so the eventual numeric answer is a
   settings change, not a code change — unchanged from the original Plan.

---

## Verified Current State (read directly from code and docs)

- **The full `conversation` schema is already specified**, unbuilt: `04_DATABASE.md` lines 588–628 give
  `conversation_sessions` (`customer_id`, `category_id` nullable, `status`, `final_confidence_score`,
  `started_at`, `completed_at`), `messages` (`conversation_session_id`, `sender`, `content`, `sequence_number`,
  `uq_messages_session_sequence`), and `confidence_scores` (`conversation_session_id`, `score`, `model_version`,
  `computed_at`) column-for-column. No migration or module exists yet for any of them (confirmed:
  `backend/app/modules/` has no `conversation` directory; `backend/alembic/versions/` has no such migration).
  **This story's migration additionally adds `conversation_sessions.structured_criteria` (JSONB, nullable) —
  Decision 1b, satisfying AC9 — a genuinely new column beyond `04_DATABASE.md`'s current text, flagged here for a
  `04_DATABASE.md` update at story close, mirroring how Decision 5's `abandoned` enum value is already flagged.**
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
  Protocol plus an honest concrete implementation. The CTO has now explicitly accepted (Decision 2b) that, unlike
  those three, this particular interim implementation does not merely lack a vendor behind the Protocol — it also
  cannot satisfy AC3/AC5 structurally, since it has no prompts and no provider-record retrieval at all.
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
  **AC9's `structured_criteria` payload (Decision 1b) is the bridge**: it is written to `conversation_sessions`
  itself (inside this story's own schema), not to `search.search_requests`, so `AI-002` or a later story can build
  the actual `search_requests` row from it without this story needing to touch the locked enum at all.
- **`administration.manual_match_assignments` is fully unbuilt** (spec only, `04_DATABASE.md` lines 866–878);
  its `assigned_admin_id` is `NOT NULL` at creation, which `09_DECISIONS.md` ADR-030 already flagged (in a
  different story's context) as not fitting an "unassigned queue, any admin may pick up" shape, since no
  admin-assignment/round-robin mechanism exists anywhere in this codebase. Under Decision 1's scope boundary,
  this problem belongs to whichever future story actually creates this table, not to `AI-001` — confirmed
  correct by the verbatim `AI-002` row.
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

**Status: CONFIRMED** by the verbatim `AI-002` row ("this story implements the routing/data model side... does
not include the admin-side queue UI itself"), which presupposes `AI-002` — not `AI-001` — is the story that
creates the manual-match routing/assignment records. No change to the reasoning below, only to its confidence
level.

**The problem:** Flow 4 describes one continuous journey (steps 1–8) from free-text description through to a
ranked provider list, but the Tracker splits Sprint 7's Conversation/AI Intake domain into two stories,
`AI-001`/`AI-002`. A wrong scope call here either duplicates work `AI-002` was meant to do, or ships `AI-001`
without a coherent stopping point.

**Chosen:** `AI-001` ends at `conversation_sessions.status ∈ {completed, routed_to_admin}` — a fully real,
complete, and independently useful domain slice (the guided conversation itself), with **zero** writes to the
`search` or `administration` schemas. The concrete evidence for this boundary: `search_request_status`'s three
enum values (`matched`, `unmatched`, `pending_manual_match`, `04_DATABASE.md` line 179) are all matching
*outcomes* — there is no "submitted, awaiting processing" value in the locked enum. Creating a `search_requests`
row now would force inventing an unspecified interim status (an unrequested schema deviation) or leaving a row in
a state the locked enum doesn't describe. It is more coherent for whichever story actually runs matching
(`AI-002`, confirmed) to create `search_requests` with its final, correct status already known at creation
time — mirroring exactly how `CLM-001`'s `create_google_seeded_provider` sets `verification_status=approved`
*at creation*, never as a later patch to an interim value (ADR-029).

**Consequence for the customer-facing experience:** the mobile completion state after a `completed` or
`routed_to_admin` session is an honest, plain confirmation ("Thanks — we're finding matches for you," per
`16_UX_GUIDELINES.md`'s own locked microcopy for this exact moment), not a results list — because no results
exist yet at the code level. This is the same "ship a real, complete domain slice ahead of its future consumer"
shape `CTG-001` already established for `CategoryService`.

**Alternatives considered and rejected:**
- **Build the whole Flow 4 (conversation + matching + results) as one story** — rejected: `.agents/agents.md`
  explicitly instructs not to combine stories, and no explicit instruction to do so was given here; the verbatim
  `AI-002` row confirms two stories were intended.
- **Create `search_requests` now with a new, unspecified `pending`/`submitted` status value** — rejected: adds an
  enum value to a table this story doesn't otherwise need to touch, purely to paper over a scope question, and
  risks colliding with whatever `AI-002` actually needs that enum to mean.
- **Skip persisting anything beyond `conversation_sessions`/`messages`, treat `confidence_scores` as optional** —
  rejected: AC9's structured completion output and the confidence-driven routing this story's design already
  builds toward both require the persisted, auditable confidence trail
  (`.agents/skills/ai-conversation-engineering/confidence-scoring-and-fallback.md`: "never compute a score without
  persisting it").

### Decision 1b — `conversation_sessions.structured_criteria` (JSONB): satisfies AC9 without crossing the `search`-schema boundary

**The problem (AC9):** "Every completed session produces a `search_requests`-ready `structured_criteria`
payload, validated via a Pydantic model before persistence." The original Plan had no mechanism for this at all
(the reconstructed AC list never named it). Producing a `search_requests` row directly would violate Decision 1's
scope boundary (no writes to the `search` schema from this story) — but AC9 is explicit and verbatim, and must be
satisfied within `AI-001`.

**Chosen (CTO Decision B, 10 September 2026):** add `conversation_sessions.structured_criteria` — `JSONB`,
nullable, populated only when a session reaches `status = completed`. Shape, validated by a new Pydantic model
`StructuredCriteria` before the column is ever written:

```python
class StructuredCriteriaAnswer(BaseModel):
    question_id: uuid.UUID
    question_text: str
    answer_text: str

class StructuredCriteria(BaseModel):
    category_id: uuid.UUID
    category_slug: str
    answers: list[StructuredCriteriaAnswer]
```

This is a **generic, category-agnostic** shape (works identically for every category's question set, no
per-category schema needed) built from exactly two things this story already owns: the resolved `Category` and
every answered `is_required=true` `CategoryQuestionTemplate` for it, paired with the customer's persisted
`messages.content` answer for that question. It is genuinely Pydantic-validated (a malformed/incomplete shape
raises `ValidationError`, caught and surfaced as a 500 with a clear log message — this should never happen in
correct code, since the service constructs the payload itself, but the validation gate is real, not decorative)
**before** the row is persisted, not after.

**Where it's populated:** `ConversationService.submit_turn` / `ConversationService._complete_session` (the same
internal step that flips `status → completed` per Decision 4's threshold check) builds the `StructuredCriteria`
instance from the resolved category + the session's answered required questions, validates it
(`StructuredCriteria.model_validate(...)`), and passes `structured_criteria.model_dump(mode="json")` to
`conversation_session_repository.complete_session(session_id, structured_criteria=...)` in the same transaction
that sets `status = completed`. A session that instead transitions to `routed_to_admin` (confidence never reached
threshold) leaves `structured_criteria` `NULL` — there is no complete, validated answer set to build it from,
which is itself consistent with `AI-002`'s job being to resolve that case through the manual-match path, not to
read a `structured_criteria` column that was never populated for it.

**This directly satisfies AC9 without violating Decision 1's scope boundary:** the payload lives entirely inside
the `conversation` schema (a new column on a table this story already owns and creates), is genuinely
`search_requests`-*ready* (its shape maps cleanly onto plausible future `search_requests` filter columns) without
this story creating or writing to `search_requests` itself. `AI-002` (or a later story) is the one that reads
`conversation_sessions.structured_criteria` to build the actual `search_requests` row — exactly the "future
consumer reads a complete, honest domain output" shape Decision 1 already establishes for the rest of this
story's completion state.

**Alternatives considered and rejected:**
- **Compute `structured_criteria` on-the-fly at read time (a service method, not a persisted column)** —
  rejected: AC9 says "produces... a payload... validated... before persistence," which is explicit about
  persistence being part of the requirement, not merely computability. A persisted column is also directly
  queryable/auditable by `AI-002` without re-deriving it from the full `messages` history every time.
- **A separate `structured_criteria` table instead of a column** — rejected as unrequested schema scope creep;
  it's a 1:1 relationship with `conversation_sessions` (one payload per completed session, never revised
  independently of the session itself), so a nullable JSONB column is the simpler, equally correct shape — the
  same reasoning `04_DATABASE.md` already applies to `conversation_sessions.final_confidence_score` being a
  column, not a side table.
- **Populate `structured_criteria` from raw `messages` rows at query time in a later story instead of persisting
  it here** — rejected: this pushes AC9's own explicit requirement onto a future story that never agreed to carry
  it, and risks `AI-002` re-implementing parsing logic that `ConversationService` already has in hand at the
  moment a session completes.

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
  str, language: LanguageCode) -> ConversationTurnResult`. Neither API routes nor the mobile AI Conversation
  screen ever import or reference a concrete client — routes depend on `ConversationService`, which depends on
  this Protocol only, and the mobile screen talks exclusively to this story's own HTTP API. **This satisfies AC2
  directly and completely** — the Protocol boundary itself, not the choice of which concrete implementation sits
  behind it, is what AC2 requires.
- `RuleBasedConversationAiClient` — the only implementation shipped by this story. **Category resolution:**
  case-insensitive substring match of the customer's free text against each active `Category.name`/`name_ar`/
  `slug`; if exactly one category matches, resolve it; if zero or more than one match, return a clarifying
  `ConversationTurnResult` (`resolved_category_id=None`, `quick_reply_options` = the full active category list)
  asking the customer to pick one directly — never a guessed category. **Follow-up questions:** once a category
  is resolved, walk `CategoryQuestionTemplate` rows in `sort_order`, one at a time, verbatim (`question_text`/
  `question_text_ar` per Decision 6) — the AI never phrases or invents a question itself. **This directly
  satisfies AC4.** **Confidence:** `0.0` while unresolved, rising in equal steps as required questions are
  answered, `1.0` once every `is_required=true` question for the resolved category has a persisted answer — a
  genuine, real, auditable score (unlike `StubDocumentOcrService`'s always-`0.0`), just not an LLM-derived
  probability. `confidence_scores.model_version` is tagged `"rule_based_v1"`, ready to be replaced by a real
  model/prompt-version string the moment Open Question 1 resolves.
- `ConversationService` depends on the `ConversationAiClient` Protocol only, wired via
  `conversation/dependencies.py:get_conversation_ai_client()` — a future real implementation
  (`OpenAiConversationAiClient`, `AnthropicConversationAiClient`, or whichever provider is chosen) is one new
  class plus one dependency-wiring change, zero changes to `ConversationService` itself.

**This directly satisfies AC10's grounding requirement by construction, not merely by prompt instruction:** the
interim client has no code path that can emit a question, category, or fact that didn't come from
`category.categories`/`category_question_templates` — there is no free-text generation capability in
`RuleBasedConversationAiClient` at all beyond echoing verbatim template text. A future real LLM implementation
must preserve this same structural guarantee (Decision 5 defines exactly how).

**Alternatives considered and rejected:**
- **Wire a real LLM API now, picking a provider unilaterally** — rejected: `.agents/agents.md` requires explicit
  approval before introducing a new external dependency/vendor, and doing so without a credential to actually
  test against would be exactly the unverifiable work ADR-018/ADR-031 already declined for a similar shape of
  problem.
- **Block this entire story on Open Question 1** — rejected, and now explicitly overridden by CTO Decision A
  (see Decision 2b): the Protocol boundary, the full `conversation` schema build, the confidence/turn-cap
  mechanics (Decision 4), the revise-a-previous-answer flow (Decision 5), the mobile chat screen (Decision 7),
  and AC1/AC2/AC4/AC6/AC7/AC8/AC9/AC10/AC11 are all real, valuable, and fully buildable and testable today,
  independent of which LLM is eventually chosen.
- **A keyword/synonym list stored as new columns on `Category`** (to make substring matching less fragile) —
  rejected as unrequested schema scope creep; `13_OPEN_DECISIONS.md` item 1 already locked the Category schema,
  and no AC asks for a synonym system. The interim client's honest fallback (ask the customer to pick from the
  list) covers the gap without a schema change.

### Decision 2b — AC3 and AC5 are honest MVP gaps under the rule-based interim client, CTO-accepted, deferred to `13_OPEN_DECISIONS.md` item 13

**CTO Decision A (10 September 2026):** ship the rule-based interim client for MVP exactly as Decision 2
proposes, explicitly accepting — the same risk-acceptance pattern `13_OPEN_DECISIONS.md` item 3 already used for
`CLM-001`'s Google Places decision — that two of the verbatim ACs are **not** meaningfully satisfiable by this
implementation:

- **AC3 ("system prompts are stored as version-controlled files, not inline strings") does not apply** to a
  client with no LLM prompts at all. `RuleBasedConversationAiClient` has no prompt — it does deterministic
  substring matching and verbatim template lookups, with zero natural-language generation. There is nothing to
  version-control as a "system prompt" file; writing one would be theater, not a real control. **Not satisfied.
  Deferred.**
- **AC5 ("a retrieved provider record with a null field... is reported to the customer as unknown, never
  estimated or guessed") requires live retrieval/grounding against real provider records mid-conversation.** The
  rule-based interim client never retrieves or discusses a specific provider at all — per Decision 1's scope
  boundary, this story doesn't query `provider.providers` from inside the conversation; it only resolves a
  category and walks scripted follow-up questions. There is no provider-record retrieval code path for this AC to
  apply to yet. **Not satisfied. Deferred.**

**Both are recorded honestly as NOT met by this story's interim implementation** (see the Verification Plan
table below — marked "Deferred (MVP gap)," not "Satisfied"), with a clear path forward: both become directly
testable and required the moment a real LLM+RAG implementation (Open Question 1's eventual resolution) is built,
since that implementation will (a) actually have prompts to version-control and (b) actually retrieve and discuss
specific provider records mid-conversation.

**New open-decision item:** `13_OPEN_DECISIONS.md` item 13 (next available number — items 1–12 already exist,
including numbering-gap placeholders at 2/6/7) — *"Real LLM Vendor Selection and RAG Grounding Implementation"* —
tracking (a) Open Question 1 (which vendor), (b) AC3 (system-prompt version control, only meaningful once real
prompts exist), and (c) AC5 (null-field-as-unknown grounding, only meaningful once real provider retrieval
exists). Per this project's standing convention (decisions are written up in the Plan first, formalized in the
shared docs at story sign-off), **this Plan documents item 13's content here but does not itself edit
`13_OPEN_DECISIONS.md` yet** — that edit happens at closeout, alongside `AI-001`'s other doc updates (see
Delegation & Execution Sequence). This is not judged urgent enough to block `backend` starting: Decision 2's
Protocol boundary and interim client are already fully specified and buildable without it.

**Alternatives considered and rejected:**
- **Write a placeholder "system prompt" file with no real content, just to check the AC3 box** — rejected: this
  is exactly the kind of decorative compliance `.agents/agents.md` and this project's prior ADR-017/018/031
  precedent explicitly avoid; an empty or fake prompt file version-controlled for a client that never reads it is
  worse than an honest "not applicable yet" note.
- **Fabricate a synthetic "provider record" with a null field just to exercise AC5's code path** — rejected: this
  story's Decision 1 scope boundary already excludes any provider-record retrieval from this domain; inventing a
  fake retrieval solely to test an AC that isn't really being exercised by production logic would be a test that
  asserts nothing true about the shipped system.

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
  customer turns, it is force-routed (`status = routed_to_admin`) rather than looping indefinitely.

### Decision 5 — Revising a previous answer: truncate-and-regenerate, not a parallel edit mechanism

**The problem (AC8):** `16_UX_GUIDELINES.md` UX Principle 3 requires the customer be able to go back and revise a
previous answer without restarting the whole conversation. Editing an early answer can invalidate every AI
question that came after it (e.g. revising which appliance is broken invalidates appliance-specific follow-ups
already asked).

**Chosen:** `PATCH /conversations/{session_id}/answers/{message_id}` — `message_id` must reference an existing,
still-active `sender=customer` message in that session. The service (a) updates that message's `content`, (b)
**soft-deletes** every `messages` row (customer and AI alike) with a strictly greater `sequence_number` in the
same session — `deleted_at`/`is_active=False`, never a hard `DELETE` (see the corrected note below), (c)
re-invokes `ConversationAiClient.process_turn` with the now-shorter, active-only history to generate the next turn
fresh, appended at the next available `sequence_number` (computed over active rows only). If the truncated
history no longer has a complete answer set for `structured_criteria` (Decision 1b), any previously computed
`structured_criteria` on that session is cleared (`NULL`) until the session re-completes — it must never be left
stale/inconsistent with the actual answer history. From the mobile client's perspective this reads as "the chat
continues from the edited point," never a restart. **"Start over"** is deliberately simpler and separate: a new
`POST /conversations` call starts a fresh session; the previous session is left exactly as it was (marked
`abandoned` — see below) rather than deleted, preserving it as an honest historical record.

**Correction (post-implementation, `architect` review):** this Plan originally specified a hard `DELETE` for step
(b), reasoned (incorrectly) below under "Alternatives considered and rejected" as necessary because "`messages`
has no `deleted_at`/soft-delete column... unlike `CommonColumnsMixin`-based tables." That premise is factually
wrong: `Message(CommonColumnsMixin, Base)` (`backend/app/modules/conversation/models.py`) *is*
`CommonColumnsMixin`-based and *does* have `deleted_at`/`is_active` (`backend/app/database/mixins.py`). A hard
`DELETE` of customer conversation transcript data, triggered by a customer-initiated revise (not an
administrative action), violated `04_DATABASE.md`'s "Common Columns" rule ("permanent deletion is an
administrative operation") — `audit.audit_logs`/`search.search_event_log` are the only stated exemptions, and
`messages` is neither. `MessageRepository.delete_after_sequence` now sets `deleted_at`/`is_active` instead,
mirroring `SavedAddressRepository.soft_delete`'s exact convention; `list_for_session` and
`get_next_sequence_number` filter `is_active.is_(True)` so a soft-deleted message is invisible to the transcript
and never double-counted when assigning the next `sequence_number` — the customer-visible behavior (truncated
messages disappear, sequence numbers continue correctly) is unchanged, only the persistence mechanism is. This
also required promoting `uq_messages_session_sequence` from a plain `UniqueConstraint` to a **partial** unique
index (`WHERE is_active = true`, mirroring `uq_saved_addresses_customer_default`'s precedent) so a regenerated
turn can reuse a soft-deleted row's old `sequence_number` without a constraint conflict.

**A small, additive enum value:** `conversation_status` gains `abandoned` (alongside `active`/`completed`/
`routed_to_admin`, the three values Flow 4's prose names directly) — set when a customer starts a new session
while a previous one is still `active`. This is a genuinely new value beyond what `04_DATABASE.md`'s text
explicitly enumerates, flagged here (mirroring `CLM-001`'s handling of its own genuinely-new
`claim_review_requests` table) for a `04_DATABASE.md` update at story close if approved.

**Alternatives considered and rejected:**
- **In-place edit only, leave subsequent AI messages stale** — rejected: would show the customer AI questions
  that no longer make sense for their revised answer (e.g. an "AC" follow-up question after they changed their
  category to "Plumbing"), directly undermining trust.
- ~~**Soft-delete truncated messages instead of hard-delete** — rejected: `messages` has no `deleted_at`/
  soft-delete column in `04_DATABASE.md`'s spec (unlike `CommonColumnsMixin`-based tables), and inventing one
  purely for this mechanism is unrequested schema scope; a truncated, superseded AI question has no audit value
  worth preserving the way a verification record does.~~ **Superseded (see "Correction" above): this reasoning
  was factually wrong.** `messages` *is* `CommonColumnsMixin`-based and already has `deleted_at`/`is_active` —
  no new column was ever needed. Soft-delete is in fact this codebase's standing convention for exactly this
  shape of problem (`04_DATABASE.md`'s "Common Columns" rule), and hard-delete was the actual violation, now
  corrected: `delete_after_sequence` soft-deletes.
- **Silently leave `active` sessions abandoned with no status change when a new one starts** — rejected: makes
  "how many conversations did a customer actually finish vs. give up on" ungoverned and unqueryable, undermining
  the same admin-analytics spirit `search_event_log`/`unmatched_query_reports` exist for elsewhere in this domain.

### Decision 6 — Bilingual handling

`ConversationService` resolves `CustomerPreferences.language` once, at session start (via `CustomerService.
get_my_profile`), and passes it into every `ConversationAiClient.process_turn` call.
`RuleBasedConversationAiClient` selects `question_text_ar`/`Category.name_ar` when `language=AR` and the
Arabic field is non-null, falling back to the English field when it is null — matching `CTG-001`'s own framing
of `name_ar`/`question_text_ar` as "nullable until populated," never a hard failure. This is the backend half of
AC11; the mobile RTL layout is Decision 7's job.

### Decision 7 — Endpoint shape (ADR-015) and module/mobile layout

**Backend**, new `backend/app/modules/conversation/` module (mirrors `category`'s exact file layout):
- `POST /conversations` (AC1) — body `{message: str}`; creates the session + first customer message + first AI
  turn; `require_role(ROLE_CUSTOMER)`.
- `POST /conversations/{session_id}/messages` (AC4/AC6/AC7) — body `{content: str}` (free text) or
  `{selected_option: str}` (a quick-reply chip choice, mapped to `content` server-side for persistence
  consistency); `ensure_owner_or_not_found` against the session's `customer_id`.
- `PATCH /conversations/{session_id}/answers/{message_id}` (AC8, Decision 5).
- `GET /conversations/{session_id}` (resume after app restart, review transcript) — `ensure_owner_or_not_found`.

**`ConversationSessionResponse` never includes a raw numeric confidence/score field** — only `status` (which the
mobile UI maps to user-facing states), satisfying AC6's "never shows a raw confidence score to the user" at the
API-contract level, not merely by the mobile UI choosing not to render a field it could otherwise see.

**Mobile**, new `mobile/lib/features/conversation/` feature (mirrors `claim`'s exact layout from `CLM-001`):
`domain/models/`, `data/conversation_repository.dart`, `presentation/screens/ai_conversation_screen.dart` (`S-07`),
`state/conversation_controller.dart` (Riverpod), `core/routing/app_routes.dart` entry. Entry point: a new primary
button on `home_placeholder_screen.dart` ("Describe what you need" or similar, exact copy per
`15_SCREEN_INVENTORY.md`'s `S-06` description) opening `ai_conversation_screen.dart` directly — the same
"add a button to the existing placeholder" precedent `CLM-001` already used for its own entry point, since real
`S-06` still doesn't exist. Chat UI implements `16_UX_GUIDELINES.md`'s exact latency tiers (0–500ms/500ms–3s
indicator only, >3s a contextual label e.g. "Thinking about your answer," >8s or a timed-out call transitions to
"We'll notify you when we have an answer" messaging rather than an indefinite spinner — AC7, verbatim) — though
the interim rule-based client responds well under 500ms in practice, the UI logic must not assume that will
always be true once a real LLM is wired in — and never freezes the input field while "thinking" (queues instead).
RTL mirroring of chat bubbles and Arabic prompt/response rendering (AC11) is verified on this screen specifically.

---

## Backend — Proposed Changes

### Migration
1. One new Alembic migration (down-revision = `602bf3c4bea7`, `claim_review_requests`, the current head).
   Creates the `conversation` schema; `conversation_status` enum (`active`, `completed`, `routed_to_admin`,
   `abandoned` — Decision 5's addition); `message_sender` enum (`customer`, `ai`); `conversation_sessions`
   (including `structured_criteria JSONB NULL` — Decision 1b), `messages` (with
   `uq_messages_session_sequence`), `confidence_scores` — column-for-column per `04_DATABASE.md` lines 588–628,
   plus the two additive items (the `abandoned` enum value, the `structured_criteria` column). No changes to any
   existing table.

### `conversation` module (new)
2. `models.py` — `ConversationStatus`, `MessageSender` enums; `ConversationSession` (including
   `structured_criteria: dict | None`, mapped as JSONB), `Message`, `ConfidenceScore` ORM models.
3. `repositories/conversation_session_repository.py` — `create`, `get_by_id`, `get_active_for_customer`,
   `update_status`, `set_category`, `update_final_confidence`, `complete_session(session_id, structured_criteria:
   dict)` (Decision 1b — sets `status=completed`, `completed_at`, and `structured_criteria` atomically),
   `clear_structured_criteria(session_id)` (Decision 5 — used when a revise invalidates a prior completion).
4. `repositories/message_repository.py` — `create`, `list_for_session` (ordered), `get_by_id`,
   `delete_after_sequence(session_id, sequence_number)` (Decision 5), `get_next_sequence_number`.
5. `repositories/confidence_score_repository.py` — `create`, `get_latest_for_session`.
6. `services/conversation_ai_client.py` — `ConversationTurnResult`, `ConversationAiClient` Protocol,
   `RuleBasedConversationAiClient` (Decision 2).
7. `services/structured_criteria.py` — `StructuredCriteriaAnswer`, `StructuredCriteria` Pydantic models
   (Decision 1b).
8. `services/conversation_service.py` — `ConversationService`: `start_conversation(user_id, message) ->
   ConversationSession`; `submit_turn(user_id, session_id, content) -> ConversationSession` (on reaching
   threshold, builds and validates `StructuredCriteria`, then calls `complete_session(...)`; on exceeding
   `CONVERSATION_MAX_TURNS`, routes to `routed_to_admin` with `structured_criteria` left `NULL`);
   `revise_answer(user_id, session_id, message_id, content) -> ConversationSession` (Decision 5, clears any prior
   `structured_criteria` on truncation); `get_session(user_id, session_id) -> ConversationSession`. Depends on
   `ConversationAiClient`, `CustomerService`, `CategoryService` (Decision 3), and the three repositories above.
9. `api.py` — the four routes in Decision 7, mounted `/conversations`.
10. `schemas.py` — `StartConversationRequest`, `SubmitTurnRequest`, `ReviseAnswerRequest`,
    `ConversationSessionResponse` (id, status, category_id, messages: list of `{sender, content, sequence_number,
    created_at}`, quick_reply_options if the current turn expects a chip choice — **no raw confidence field**,
    per Decision 7/AC6).
11. `dependencies.py` — `get_conversation_ai_client`, `get_conversation_session_repository`,
    `get_message_repository`, `get_confidence_score_repository`, `get_conversation_service`.
12. Exceptions: `ConversationSessionNotFoundError` (404), `ConversationSessionNotActiveError` (409 — submitting a
    turn to a `completed`/`routed_to_admin`/`abandoned` session), `AnswerNotRevisableError` (409/422 — targeting a
    non-existent or non-customer message), `InvalidStructuredCriteriaError` (500 — a `StructuredCriteria`
    validation failure at completion time; should never occur in correct code, but caught and logged distinctly
    rather than surfacing a raw `ValidationError`).

### Config (`backend/app/core/config.py`)
13. `CONVERSATION_CONFIDENCE_THRESHOLD: float = 1.0` (Decision 4).
14. `CONVERSATION_MAX_TURNS: int = 12` (Decision 4).

### API wiring
15. `backend/app/api/v1/api.py` — mount the new `conversation_router` (prefix `/conversations`).
16. `backend/tests/conftest.py` — register the three new ORM models for `Base.metadata.create_all()`.

### Tests
17. `backend/tests/modules/conversation/test_conversation_ai_client.py` — `RuleBasedConversationAiClient`:
    resolves an unambiguous category from free text; asks a clarifying category-pick question on zero/multiple
    matches; walks a resolved category's questions in `sort_order`, never inventing one (AC4); confidence reaches
    `1.0` only once every required question is answered; Arabic field selection when `language=AR` with a
    graceful English fallback when the Arabic field is null (AC11 backend half).
18. `backend/tests/modules/conversation/test_conversation_service.py` — `start_conversation` creates session +
    first message (AC1); `submit_turn` persists ordered messages, computes and persists a `confidence_scores` row
    each turn, caches `final_confidence_score`; confidence reaching the threshold sets `status=completed`;
    exceeding `CONVERSATION_MAX_TURNS` without completing sets `status=routed_to_admin`; `revise_answer` truncates
    every later message and regenerates the next turn (AC8, Decision 5), and clears a stale `structured_criteria`
    if the session had previously completed; submitting a turn to a non-`active` session raises
    `ConversationSessionNotActiveError`.
19. `backend/tests/modules/conversation/test_structured_criteria.py` (new) — `StructuredCriteria` Pydantic model
    rejects a malformed shape (missing `category_id`, an answer missing `question_text`, wrong types); a
    completed session's persisted `conversation_sessions.structured_criteria` matches exactly the resolved
    category + every required question's answer, in the documented shape (AC9); a `routed_to_admin` session has
    `structured_criteria IS NULL`.
20. `backend/tests/modules/conversation/test_conversation_api.py` — full HTTP round trips: auth/role gating;
    `ensure_owner_or_not_found` returns 404 (never 403) for another customer's session id on every `{session_id}`
    route; `ConversationSessionResponse` payload contains no raw confidence/score field at any point in a session's
    lifecycle (AC6).
21. `backend/tests/modules/conversation/test_grounding.py` — a direct, structural assertion that no
    `ConversationTurnResult`/persisted `messages.content` for an AI-sender turn can contain text absent from the
    seeded `category_question_templates`/`categories` tables for that session's resolved category (AC10) —
    the concrete, code-level proof behind Decision 2's "grounded by construction" claim.

---

## Mobile — Proposed Changes

### New feature: `mobile/lib/features/conversation/`
22. `domain/models/conversation_session.dart`, `domain/models/conversation_message.dart`.
23. `data/conversation_repository.dart` — `start(message)`, `submitTurn(sessionId, content)`, `reviseAnswer(
    sessionId, messageId, content)`, `getSession(sessionId)`.
24. `presentation/screens/ai_conversation_screen.dart` (`S-07`, AC6/AC7/AC11) — chat transcript (customer bubbles
    right-aligned, AI bubbles left-aligned, RTL-mirrored correctly per `16_UX_GUIDELINES.md`'s explicit
    chat-bubble RTL warning), tiered typing indicator (AC6), quick-reply chip row when the active turn offers
    `quick_reply_options`, free-text input otherwise (never both disabled at once), tap-to-revise on any past
    customer bubble (AC8), an always-visible "Start over" action, a "We'll notify you" hand-off state on an
    8-second timeout or slow response (AC7), and an honest completion state (no fake results list — Decision 1)
    once `status` reaches `completed`/`routed_to_admin`. Never renders any confidence value (AC6).
25. `state/conversation_controller.dart` (Riverpod) — owns turn submission, the >3s/>8s latency-tier timers,
    queuing additional free-text input typed while a turn is in flight (never blocking the field).
26. `core/routing/app_routes.dart` — new route for `ai_conversation_screen.dart`.

### Entry point
27. `features/home/presentation/screens/home_placeholder_screen.dart` — new primary button ("Describe what you
    need" / final copy TBD with product) opening `ai_conversation_screen.dart`, alongside the existing "Find a
    Service" (structured browse) and "Already listed on Google?" (claim) buttons — mirrors the exact precedent
    `CLM-001` already set for adding a second/third entry point to this same placeholder file.

### Tests
28. `mobile/test/features/conversation/ai_conversation_screen_test.dart` — chip row renders only when the current
    turn expects a selection; free-text input renders otherwise; tapping a past customer bubble opens the revise
    flow and calls the fake repository's `reviseAnswer`; "Start over" starts a fresh session; typing indicator
    tiers fire at the documented thresholds; a simulated >8s response shows the "We'll notify you" state, not a
    spinner (AC7); no widget in the tree ever displays a numeric confidence value (AC6); RTL golden/layout check
    for Arabic (AC11).
29. `mobile/test/features/conversation/fakes/fake_conversation_repository.dart` (mirrors the existing
    fake-repository pattern, e.g. `fake_claim_repository.dart`).

---

## Explicitly Out of Scope (do not implement in this story)

- **Any write to `search.search_requests`, `search.provider_matches`, `search.search_event_log`, or
  `administration.manual_match_assignments`** — Decision 1, now confirmed by the verbatim `AI-002` row. A
  completed or routed-to-admin `conversation_session` (including its `structured_criteria` payload, Decision 1b)
  is this story's entire, honest output; turning it into a matchable, ranked result is `AI-002`'s job.
- **Any real geospatial/merit matching against providers**, and any wiring into `S-08` (Search Results) —
  Decision 1; `S-08` remains exactly as DIR-001 left it.
- **Contact View, Outcome Tag, Reviews** — downstream of matching, not reachable without it; unaffected by this
  story either way.
- **A real LLM-provider integration** (OpenAI, Anthropic, or otherwise) — Open Question 1, CTO Decision A; this
  story ships the Protocol and one interim, honest, deterministic implementation only. AC3 and AC5 are the
  explicit, documented consequence — see Decision 2b, not to be confused with "out of scope" (they are ACs of
  this story, honestly not met yet, tracked as a deferred MVP gap rather than silently skipped).
- **Reconciling `provider.provider_category_labels` into the real `category.provider_categories` join table**
  (`13_OPEN_DECISIONS.md` item 1's still-open remainder) — irrelevant to this story's scope (it never queries
  providers at all) but worth naming so it isn't mistaken for something this story should have touched.
- **Any admin-facing consumption UI/endpoint for low-confidence sessions** (Flow 7's admin side) — this story
  doesn't even create the row that flow consumes (Decision 1); `13_OPEN_DECISIONS.md` item 10 explicitly ties
  that dashboard scope to `ADM-001`/`ADM-002` (Sprint 11).
- **Cost controls, rate limiting, or timeout policy for real LLM calls** — Open Question 2; moot while the only
  shipped client makes no external network calls.
- **A synonym/keyword system on `Category`** for more forgiving free-text matching — Decision 2's alternatives.

## Deferred Acceptance Criteria (MVP gap, CTO-accepted — Decision 2b)

Distinct from "Explicitly Out of Scope" above: these are verbatim ACs of *this* story, not later stories' work,
which this story's interim implementation honestly cannot satisfy yet.

- **AC3** (system prompts as version-controlled files) — not applicable to a client with no prompts.
- **AC5** (null provider field reported as unknown) — requires live provider-record retrieval this story's scope
  boundary (Decision 1) doesn't include, and the interim client doesn't do regardless.

Both tracked as `13_OPEN_DECISIONS.md` item 13 (to be added at story closeout, per this Plan's convention).

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

Open Question 3 (the `AI-001`/`AI-002` scope boundary) is now **confirmed**, not merely flagged — no CTO
confirmation is needed before `backend` starts. Open Questions 1/2/4 do not block starting `backend` either:
Decision 2/2b already specify a fully buildable, testable interim path (with two explicitly deferred ACs), and
Question 4 is absorbed by Decision 4's config-driven design regardless of which numeric answer eventually lands.

1. **backend** — Items 1–21. Build order: (a) the migration + `models.py` first (including `structured_criteria`
   — Decision 1b); (b) repositories; (c) `ConversationAiClient`/`RuleBasedConversationAiClient` (Decision 2) —
   this is the part most worth extra care, since Decision 2's "grounded by construction" claim is only true if
   every code path is checked; (d) `structured_criteria.py`'s Pydantic model (Decision 1b); (e)
   `ConversationService` (Decisions 1/1b/4/5/6) — pay particular attention to where `StructuredCriteria` gets
   built and validated (only on the `completed` transition, cleared on a revise that invalidates it); (f)
   `api.py`/`schemas.py`/`dependencies.py` last, double-checking `ConversationSessionResponse` never leaks a raw
   confidence value (AC6). Read Decision 1 in full before starting — the temptation to "just also create a
   `search_requests` row since it's right there in the domain model" is exactly the scope drift this Plan
   deliberately avoids, for the reasons given.
2. **frontend** — Mobile items 22–29, once the backend endpoints exist (or in parallel against a fake
   repository). Particular attention to Decision 7's latency-tier UI logic (AC6/AC7's exact thresholds and
   copy), the honest, no-fake-results completion state (Decision 1), and RTL/Arabic verification (AC11) — this is
   the most likely place a well-intentioned addition would silently expand this story's scope back into
   `AI-002`'s territory, or silently skip the RTL check.
3. **tester** — Verify all 11 verbatim ACs (mapping below), explicitly confirming AC3 and AC5 are correctly
   documented as deferred (not silently absent, not falsely marked satisfied) rather than testing for something
   that cannot exist in this implementation. Particular attention to AC10 (the grounding tests, item 21), AC9
   (the `structured_criteria` Pydantic validation and correct population, item 19), AC6 (no raw confidence ever
   surfaced, at both the API-contract and mobile-widget level), and AC8 (the truncate-and-regenerate revise flow
   actually removes stale AI questions and any stale `structured_criteria`, not just marks them somehow
   superseded).
4. **architect** — Review Decision 1 (the scope boundary and its `search_request_status`-enum evidence, now
   Tracker-confirmed) against `03_DOMAIN_MODEL.md`/`04_DATABASE.md`'s intent; Decision 1b's `structured_criteria`
   column and Pydantic-validate-before-persist mechanism for correctness and for genuinely not touching
   `search.search_requests`; Decision 2 (the `ConversationAiClient` Protocol) against ADR-017/018/031's
   established pattern for consistency; Decision 2b's honest AC3/AC5 deferral for whether the reasoning holds up
   (not merely whether it's convenient); Decision 5's additive `abandoned` enum value and the hard-delete-on-revise
   mechanism against this codebase's general soft-delete conventions; Decision 3's `conversation → customer`/
   `conversation → category` edges for cycle-freedom.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decision 1 (scope boundary, now confirmed), Decision 1b (`structured_criteria` payload/AC9
     mechanism), Decision 2 (`ConversationAiClient` Protocol, the pattern's fourth application), Decision 2b
     (AC3/AC5 honest deferral), and Decision 5 (revise/truncate mechanism + the additive `abandoned` status) as
     new ADRs (next available: **ADR-032** onward).
   - Add `13_OPEN_DECISIONS.md` item 13 (Decision 2b's content, as drafted above) — this is the point at which
     that doc edit actually happens, per this Plan's stated convention.
   - Update `04_DATABASE.md` (mark the `conversation` schema as shipped, add the `abandoned` enum value and the
     `structured_criteria` column).
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 7 section.

---

## Verification Plan (mapped to the 11 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Migration exists and applies cleanly; `test_conversation_service.py`/`test_conversation_api.py`: `POST /conversations` creates the session (`status=active`) and the first `messages` row with `sequence_number=1`; subsequent turns strictly increase `sequence_number`, never overwritten. |
| 2 | `test_conversation_ai_client.py` + code review: `ConversationService`/routes/mobile screen depend only on the `ConversationAiClient` Protocol, never a concrete client — `architect` confirms no import of `RuleBasedConversationAiClient` (or any future concrete client) outside `conversation/dependencies.py`. |
| 3 | **Deferred (MVP gap)** — see Decision 2b and `13_OPEN_DECISIONS.md` item 13 (to be added at closeout). Not applicable to a client with no prompts; not satisfied by this story, honestly recorded as such. |
| 4 | `test_conversation_ai_client.py`: unambiguous free text resolves a category; ambiguous/no-match text returns a category-pick prompt, never a guess; only-taxonomy question ordering, never an invented question. |
| 5 | **Deferred (MVP gap)** — see Decision 2b and `13_OPEN_DECISIONS.md` item 13 (to be added at closeout). Requires live provider-record retrieval this story's scope and interim client do not implement. |
| 6 | `ai_conversation_screen_test.dart`: typing indicator within 500ms, contextual label past 3s; `test_conversation_api.py` + widget tests: no raw confidence value anywhere in the API response or widget tree. |
| 7 | `ai_conversation_screen_test.dart`: a simulated >8s/timed-out response transitions to "We'll notify you" messaging, never an indefinite spinner. |
| 8 | `test_conversation_service.py` (`revise_answer`) + `ai_conversation_screen_test.dart`: truncation and regeneration proven at both the service and UI level, including stale `structured_criteria` being cleared. |
| 9 | `test_structured_criteria.py`: `StructuredCriteria` Pydantic model rejects malformed input; a completed session's `conversation_sessions.structured_criteria` is correctly populated and matches the resolved category + answered required questions; a `routed_to_admin` session leaves it `NULL`. |
| 10 | `test_grounding.py` — structural proof that no AI-sender message content is absent from the seeded taxonomy, not a prompt-instruction claim. |
| 11 | `test_conversation_ai_client.py` (Arabic field selection + English fallback when null) + `ai_conversation_screen_test.dart` (RTL layout/golden check) + manual/architect review of Arabic prompt/response quality on the chat screen. |

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
  item 3 — the `CLM-001` Google Places risk-acceptance pattern Decision 2b mirrors; item 5 — config-not-schema
  precedent, Decision 4; item 10 — Wizard-of-Oz degree, still Open, Decision 4/Open Question 4; item 13 —
  new item this story's closeout adds, per Decision 2b)
- `docs/AI/14_USER_FLOWS.md` Flow 4 (steps 1–5 are this story's scope; steps 6+ are `AI-002`'s, Decision 1,
  confirmed)
- `docs/AI/15_SCREEN_INVENTORY.md` (`S-06`, `S-07`)
- `docs/AI/16_UX_GUIDELINES.md` (AI Conversation latency section; UX Principle 3 — revise without restarting;
  Wizard-of-Oz invisibility rule)
- `.agents/skills/ai-conversation-engineering/SKILL.md` and its two rule files (grounding/RAG,
  confidence-scoring-and-fallback) — the four Core Directives this Plan builds against directly
- `docs/implementation/plans/Plan_S07_CTG-001.md` / `Walkthrough_S07_CTG-001.md` (the `CategoryService` this story
  consumes)
- `docs/implementation/plans/Plan_S06_CLM-001.md` (Protocol-swap precedent, Decision 2; the risk-acceptance
  pattern Decision 2b mirrors; the "add a button to `home_placeholder_screen.dart`" entry-point precedent,
  Decision 7)

---

**End of Document**
