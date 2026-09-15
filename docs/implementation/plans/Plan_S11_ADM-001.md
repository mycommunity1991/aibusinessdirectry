# Plan for Story ADM-001 — Resolve Manual-Match and Unmatched-Query Work as an Administrator

**Sprint:** 11 ("Marketplace Operations") | **Epic:** ML11-EP01 | **Milestone:** ML11 | **Priority:** High | **Depends
On:** AI-002 (done, Sprint 7)

---

## Story (verbatim, `Project_Tracker.xlsx`, `ADM-001` row — relayed via `docs/AI/SESSION_HANDOFF.md` this session)

"As an administrator, I want a queue of low-confidence sessions needing manual matching and a report of searches
that produced no good match, so that I can keep the Wizard-of-Oz fallback working and spot supply/category gaps
early. This story gives admins the operational surface for two things already producing data in earlier stories:
AI-002's `manual_match_assignments` and MAT-001's `search_event_log` unmatched entries. The admin platform itself
(Flutter vs. a separate internal tool) remains an explicitly open decision — this story implements the API layer,
which is platform-agnostic, without assuming the answer. Scope boundary: does not include verification review
(`VER-002`, already delivered) or the broader admin dashboard shell (`ADM-002`)."

## Acceptance Criteria (verbatim, 7 items)

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

---

## Verified Current State (read directly from code and docs before writing this Plan)

### The `unmatched_query_reports` contradiction — resolved with direct evidence, not assumed

`docs/AI/SESSION_HANDOFF.md`'s own "Key technical precedents" section (§4, "Pull-based admin queue pattern") lists
`unmatched_query_reports` alongside three already-shipped tables (`admin_action_log`, `claim_review_requests`,
`manual_match_assignments`) as if it were a fourth already-built application of the pattern. **This is checked
directly against the real code and is confirmed to be a documentation slip, not fact:**

- `backend/app/modules/administration/models.py` (read in full) defines exactly three model classes —
  `AdminActionLog`, `ClaimReviewRequest`, `ManualMatchAssignment`. **No `UnmatchedQueryReport` class exists.**
- `backend/alembic/versions/` (globbed in full, 22 files) contains **no migration referencing
  `unmatched_query_reports`** anywhere (`grep -r unmatched_query_reports backend/alembic/` returns zero matches).
- `docs/AI/04_DATABASE.md` itself is the actual source of truth and settles this unambiguously. Line 948-949, in
  `admin_action_log`'s own section: *"`claim_review_requests` (below) has since shipped... `manual_match_assignments`
  (below) has since shipped as its third slice (Story AI-002, Sprint 7); **`unmatched_query_reports`, `feature_flags`,
  and `system_settings` (below) remain unbuilt.**"* The full column-level spec already exists at line 1005-1017
  (`search_event_log_id` FK unique 1:1, `category_gap_notes` TEXT nullable, `status` VARCHAR(20) default `'open'`,
  `reviewed_by`/`reviewed_at` nullable, constraint `uq_unmatched_query_reports_search_event_log_id`) — **designed,
  documented, and explicitly labeled "remain unbuilt" in the same file**, not merely absent from discussion.
- `docs/AI/03_DOMAIN_MODEL.md` (line 284) lists "Unmatched Query Report" as an Administration-domain entity — a
  planned aggregate root, consistent with "designed but not yet built," not evidence it was ever shipped.

**Conclusion: AC1 is a genuinely new migration, exactly as its literal text says.** `SESSION_HANDOFF.md`'s §4
precedent-list entry is corrected at this story's closeout (Decision 1) — it should have described three shipped
applications plus one *specified-but-unbuilt* fourth, not four shipped applications.

### `manual_match_assignments` / the resolution path — already fully built and already fully tested by AI-002

Reading `backend/app/modules/search/admin_manual_match_api.py`,
`backend/app/modules/search/services/search_request_service.py`, `backend/app/modules/search/schemas.py`,
`backend/app/modules/administration/services/manual_match_assignment_service.py`,
`backend/app/modules/administration/repositories/manual_match_assignment_repository.py`, and
`backend/tests/modules/search/test_search_request_api.py` in full confirms **AI-002 already shipped almost all of
AC2/AC3/AC4/AC6/AC7's substance**:

- `GET /admin/search/manual-matches` (mounted via `admin_manual_match_router`, `require_role(ROLE_ADMIN)`) already
  lists `status=pending` assignments, oldest first, paginated. Its own docstring/`ManualMatchAssignmentSummaryResponse`
  docstring explicitly says: *"Deliberately does not include the session's `messages` transcript (Explicitly Out
  of Scope, `Plan_S07_AI-002.md`) — `ADM-001`'s job to design."* **This is the one genuinely missing piece of
  AC2** — the list endpoint, role gate, and pagination already exist; only the transcript is missing.
- `POST /admin/search/manual-matches/{assignment_id}/resolve` already: validates every `provider_ids` entry against
  a real `providers` row (422 `InvalidManualMatchProviderIdsError` otherwise); closes the assignment via
  `ManualMatchAssignmentService.resolve` (atomic `try_resolve`, 409 `ManualMatchAssignmentAlreadyResolvedError` on a
  repeat call, race-safe); then calls **the exact same `SearchRequestService._finalize_matches` helper the
  automated matcher uses** — the sole place in the codebase that ever writes `provider_matches`,
  `search_requests.status`, or `search_event_log`. `rank` is the admin's own supplied list order (never
  re-derived) — confirmed at `ProviderMatchRepository.bulk_create`'s `enumerate(ranked_matches, start=1)`. **This
  is AC3 in full, already shipped, unchanged by this Plan.**
- The customer read path (`GET /search-requests/{id}` → `SearchRequestService.get_matched_providers` →
  `ProviderMatchRepository.list_for_search_request`) is identical regardless of whether `provider_matches` was
  written by the automated or the manual path — **this is AC4, already true by construction, not something this
  story needs to build.**
- `require_role(ROLE_ADMIN)` (`backend/app/api/dependencies.py`'s `RequireRole`) is already the sole authorization
  boundary on both existing manual-match routes, raising `InsufficientRoleError` (403) for a non-admin caller —
  **AC6, for these two routes, already shipped.**
- `test_search_request_api.py::TestAdminResolveManualMatch::test_resolving_with_provider_ids_returns_matched_result`
  (line ~275-304) already performs the full round trip AC7's first bullet asks for: admin resolves an assignment,
  then the same test asserts `GET /search-requests/{id}` as the owning customer returns the identical
  `matched_providers` body. `test_list_returns_403_for_a_non_admin`/`test_resolve_returns_403_for_a_non_admin`
  already cover AC6 for these two routes. **AC7's first bullet is already satisfied by an existing, passing test**
  — this Plan's job for AC7 is only to add the analogous coverage for the *new* `unmatched_query_reports`
  transitions (its second bullet), plus a regression re-run confirming nothing above breaks.

This materially narrows this story's real backend scope: **AC3, AC4, and AC6-for-manual-matches need no new
write logic at all** (Decision 5) — this Plan's manual-match-side work is limited to AC2's transcript gap.

### `search.search_event_log` — confirmed shape, confirmed `was_matched=false` is directly queryable

`backend/app/modules/search/models.py`'s `SearchEventLog` (no `CommonColumnsMixin`, mirrors `audit_logs`'s
append-only exemption, `04_DATABASE.md`'s only two named exemptions): `id`, `search_request_id` (nullable FK),
`customer_id` (nullable FK), `category_id` (nullable FK), `query_text` (nullable — **confirmed always written as
`None` today**, see Decision 1's flagged limitation below), `result_count` (INTEGER, not null), `was_matched`
(BOOLEAN, not null), `created_at`. Written exactly once per `search_requests` row, by
`SearchRequestService._finalize_matches` — the same shared helper AC3/AC4 already rely on. `was_matched=False`
is a plain, directly-filterable boolean column — no derived/computed logic needed to identify an unmatched row.

### Conversation transcript — `MessageRepository.list_for_session`/`conversation.schemas.MessageResponse` already exist and are directly reusable

`backend/app/modules/conversation/repositories/message_repository.py::list_for_session` already returns a
session's full active-message transcript ordered by `sequence_number`; `conversation/schemas.py` already defines
`MessageResponse`/`message_to_response`. `ConversationService.get_session`/`_get_owned_session`, however, are
**ownership-gated to a specific customer** (`ensure_owner_or_not_found`) — there is no existing "any session,
admin context" read primitive on `ConversationService` itself. A precedent for a cross-module schema reuse
already exists (`backend/app/modules/provider/claim_api.py` imports `identity.schemas.RequestOtpResponse`
directly) — this Plan reuses that precedent rather than duplicating `MessageResponse` inside `search`.

**A real circular-import constraint, confirmed by reading both `dependencies.py` files:**
`conversation/dependencies.py` already imports `search.dependencies.get_search_request_service` (AI-001/AI-002's
existing `conversation -> search` edge, needed to wire `ConversationService`'s own `search_request_service`
dependency). If `search` were to depend on `conversation.services.conversation_service.ConversationService` (via
`conversation/dependencies.py`) to fetch a transcript, `search.dependencies` and `conversation.dependencies` would
import each other at module level — a genuine Python circular import, not merely an architectural style
preference. `conversation/repositories/message_repository.py`, by contrast, imports only
`app.modules.conversation.models`/`app.repositories.base_repository` — a leaf module with no edge back into
`search` at all. This is the concrete, evidence-based reason Decision 4 below reaches for a raw-Repository
dependency rather than the target module's Service.

### Administration module — confirmed shape, confirmed it has never had an `api.py`

`backend/app/modules/administration/` (models, dependencies, `repositories/`, `services/` all read in full) has
**zero cross-module imports today** (`dependencies.py` only wires its own three existing services) and **no
`api.py` file at all** — every existing admin-facing HTTP surface for its three aggregates is hosted by the
*other* module that orchestrates the underlying business action: `admin_action_log` has no dedicated routes of
its own (written internally by `AdminActionLogService.record_verification_review`, called from
`verification/admin_api.py`); `claim_review_requests`' routes live in `provider/admin_claim_api.py`;
`manual_match_assignments`' routes live in `search/admin_manual_match_api.py`. In every one of those three cases,
the hosting module needed to *write into its own schema* as part of resolving the admin action (approve a
verification → flip `providers.is_discoverable`; approve/reject a claim → finalize or leave unclaimed; resolve a
manual match → write `provider_matches`). This is the direct evidence Decision 6 below relies on: `administration`
has never needed its own `api.py` because every prior aggregate's resolution needed a cross-module *write*; the
new `unmatched_query_reports` review workflow needs no such write into another module at all.

### Admin role-check mechanism — confirmed, reused verbatim

`backend/app/api/dependencies.py`'s `RequireRole`/`require_role(*allowed_roles)` (AUTH-004): a composable FastAPI
dependency layered on top of `get_current_user`, raising `InsufficientRoleError` (403, never conflated with 401)
when the caller's JWT `roles` claim doesn't intersect the allowed set. `ROLE_ADMIN = "admin"`
(`app/core/constants.py`). Every existing admin-only route in this codebase (`verification/admin_api.py`,
`provider/admin_claim_api.py`, `search/admin_manual_match_api.py`) uses `Depends(require_role(ROLE_ADMIN))` as its
**entire** authorization boundary, with no ownership check layered on top (an Admin has no "own" resource to scope
to). This Plan's new routes reuse this exact mechanism, verbatim — AC6 needs no new authorization code, only new
routes correctly wired to the existing dependency.

### Platform scope — confirmed backend-only

The story's own text states the admin platform (Flutter vs. a separate tool) is an explicitly open decision, and
this story "implements the API layer, which is platform-agnostic." Every one of `admin_action_log`/
`claim_review_requests`/`manual_match_assignments`' existing admin surfaces is backend-API-only with no Flutter
screen (`SESSION_HANDOFF.md` §4's own "no dashboard UI yet" framing, `admin_manual_match_api.py`'s own docstring:
"Backend-API-only — no dashboard UI exists or is expected here"). **This Plan is backend-only — no mobile/Frontend
section, no new Flutter code.**

---

## Architecture Decisions

### Decision 1 — `unmatched_query_reports` does not exist yet; AC1 is a genuine new migration; `SESSION_HANDOFF.md` is corrected at closeout

Resolved above with direct file/line evidence, not assumption. **Chosen:** build the table exactly to
`04_DATABASE.md`'s already-specified column shape (it was designed, just never migrated) — `search_event_log_id`
(UUID, not null, FK → `search.search_event_log.id`, unique — a strict 1:1), `category_gap_notes` (TEXT, nullable),
`status` (VARCHAR(20), not null, default `'open'`), `reviewed_by` (UUID, nullable, FK → `identity.users.id`),
`reviewed_at` (TIMESTAMPTZ, nullable), plus the full `CommonColumnsMixin` — mirroring `claim_review_requests`' own
precedent of using the full mixin (versioned, soft-deletable) rather than `search_event_log`'s narrower exemption,
since `04_DATABASE.md`'s Soft Delete section names only `audit_logs`/`search_event_log` as exempt.

**Flagged, non-blocking limitation inherited from AI-002 (not fixed by this story):** `search_event_log.query_text`
is written as a hardcoded `None` in every call to `_finalize_matches` today (confirmed at
`search_request_service.py`'s `_finalize_matches`: `"query_text": None`) — no code path anywhere populates it with
the customer's actual free text. This means every `unmatched_query_reports` row's enriched `query_text` field will
read `null` until a separate story wires the real value through. `category_id`/`customer_id`/`result_count` are
unaffected and populate correctly. Flagged at Open Question 1 for CTO awareness; out of this story's scope to fix
(the story's own AC1 asks only for the table and admin workflow, not for fixing an upstream write gap in a
different story's code).

**Alternatives considered and rejected:**
- **Treat AC1 as already satisfied** (misreading `SESSION_HANDOFF.md`'s precedent list at face value). Rejected —
  directly contradicted by `models.py`, the migrations directory, and `04_DATABASE.md`'s own explicit "remain
  unbuilt" text.
- **A DB view instead of a physical table.** Rejected — `04_DATABASE.md`'s own spec is explicit: "kept as a
  physical table (not a DB view) because admin review status must be writable and durable." A view cannot hold
  `category_gap_notes`/`status`/`reviewed_by`/`reviewed_at`.

### Decision 2 — `unmatched_query_reports` is `administration`'s fourth aggregate root, auto-created inside `_finalize_matches` at write time, never lazily computed

**The problem:** given the table is new, when/how do rows get created? AC1 says "sourced from `search_event_log`
rows where `was_matched=false`."

**Chosen:** `unmatched_query_reports` becomes `administration`'s fourth slice (own `models.py` class, own
`repositories/unmatched_query_report_repository.py`, own `services/unmatched_query_report_service.py`) — the
exact same "one module, several aggregate roots sharing one schema" pattern already established three times
(`ADR-048`) and already named as this table's eventual home by `04_DATABASE.md`'s own schema assignment
(`administration.unmatched_query_reports`). `SearchRequestService._finalize_matches` (the sole writer of
`search_event_log`) is extended **in place** with one new, additive call: immediately after creating the
`search_event_log` row, if `not ranked_matches` (i.e. the just-written row has `was_matched=False`), call a new
`UnmatchedQueryReportService.create(search_event_log_id=...)`. This mirrors `ADR-042`'s "in-place upgrade of a
shared query, never a second parallel implementation" precedent exactly — `_finalize_matches` already is the one
and only place `search_event_log` rows are ever written, so it is also the only correct place to guarantee a 1:1
report row exists for every unmatched one, with zero risk of a report being missed or double-created (both the
automated and manual paths funnel through this one helper, satisfying AC3/AC4's own "identical shape" guarantee
one more time). This is a second `search -> administration` service dependency on `SearchRequestService`
(alongside the existing `ManualMatchAssignmentService` one) — zero new cross-module architecture risk, since the
edge direction is already established and used.

**Alternatives considered and rejected:**
- **Lazily materialize report rows from a query at list-time** (e.g., `GET .../unmatched-query-reports` queries
  `search_event_log WHERE was_matched=false AND NOT EXISTS (a report row)` and creates rows on the fly). Rejected
  — `04_DATABASE.md`'s own spec calls this "a physical table... because admin review status must be writable and
  durable," which only makes sense if rows exist independently of when an admin happens to browse the list; a
  lazy-create-on-read pattern would also put row-creation inside a `GET` handler, which should be side-effect-free.
- **A separate batch/cron job that periodically scans `search_event_log` for new unmatched rows.** Rejected — no
  scheduling infrastructure exists anywhere in this codebase (`ADR-050`'s own "fire immediately/synchronously
  rather than inventing scheduling infrastructure nobody asked for" precedent applies directly); the write-time
  hook is simpler, synchronous, and cannot fall behind or double-process.

### Decision 3 — AC2's transcript is embedded directly in the existing list-item response (in-place upgrade), reusing `conversation.schemas.MessageResponse` verbatim

**The problem:** the existing `GET /admin/search/manual-matches` list endpoint and
`ManualMatchAssignmentSummaryResponse` deliberately exclude the transcript today, explicitly deferring the design
to this story. Two shapes were considered: embed the transcript in each list-page row, or add a new, separate
`GET /admin/search/manual-matches/{id}` detail endpoint returning it.

**Chosen:** embed it directly in the existing list response, in place — **directly precedented by
`verification/admin_api.py`'s own `list_verification_records`**, which already embeds each record's full Provider
context *and* every one of its documents inline in the same paginated list response, not behind a separate detail
call. The pending manual-match queue is a low-volume, Wizard-of-Oz-scale queue by design (this is precisely why it
exists — the automated matcher already resolves the bulk of traffic), so per-row transcript payload size is not a
realistic performance concern, and a second detail endpoint would only add an extra round trip for zero benefit at
this scale. `ManualMatchAssignmentSummaryResponse` keeps its existing name (its docstring's exclusion note is
updated, not its identity) and gains one new field: `transcript: list[MessageResponse]`, reusing
`conversation.schemas.MessageResponse`/`message_to_response` verbatim rather than duplicating a parallel DTO in
`search` — directly precedented by `provider/claim_api.py`'s own existing `from
app.modules.identity.schemas import RequestOtpResponse` cross-module schema reuse, and consistent with this
project's "never create duplicate models" rule.

**Alternatives considered and rejected:**
- **A new `GET /admin/search/manual-matches/{id}` detail endpoint**, list rows staying transcript-free. Rejected —
  less directly precedented than `verification/admin_api.py`'s embed-per-row shape, and adds a second round trip
  an admin reviewing a small queue doesn't need.
- **A brand-new, `search`-owned transcript DTO** instead of reusing `conversation.schemas.MessageResponse`.
  Rejected — `message_to_response`/`MessageResponse` are already a stable, public, behavior-free DTO; duplicating
  them serves no isolation purpose the `identity.schemas.RequestOtpResponse` precedent doesn't already accept as
  fine.

### Decision 4 — The new `search -> conversation` edge is `MessageRepository` (raw Repository), not `ConversationService` — a second, distinct justification under the existing `ADR-047` exception

**The problem:** `search` needs *some* way to read a session's transcript for Decision 3, but `search` has zero
imports from `conversation` today (a deliberate AI-002 decision, confirmed in `search_request_service.py`'s own
module docstring) — for good reason: `conversation.dependencies` already imports
`search.dependencies.get_search_request_service`, so a same-direction `search -> conversation.services
.ConversationService` edge (via `conversation.dependencies`) would create a genuine circular import at the Python
module level, not just a style violation.

**Chosen:** `SearchRequestService` gains one new constructor dependency,
`conversation.repositories.message_repository.MessageRepository` — a raw-Repository cross-module edge, wired
directly via `MessageRepository(db)` inside `search/dependencies.py` (never importing
`conversation.dependencies` or `conversation.services` at all, avoiding the cycle entirely, since
`conversation.repositories.message_repository` is a leaf module with no edge back into `search`). This is
`ADR-047`'s raw-Repository exception clause applied for a **second, distinct reason** beyond its original "no
equivalent Service primitive exists" justification (`CON-001`/`LEAD-001`/`LEAD-002`'s prior applications): here, an
equivalent-ish primitive *does* exist on `ConversationService` (`get_session`), but is architecturally unreachable
for this caller both because it is ownership-gated to a specific customer (an admin caller has no customer
profile to scope to) and because reaching it would reintroduce a real circular import. `MessageRepository` gains
one new batch method, `list_for_sessions(session_ids: list[UUID]) -> dict[UUID, list[Message]]` (`WHERE
conversation_session_id IN (...) AND is_active`, grouped and ordered by `sequence_number` per session) —
`SearchRequestService.list_pending_manual_matches` (an in-place upgrade, `ADR-042`-style, since its own AI-002
docstring already pre-announced this exact future extension) calls it once per page (page size is capped, so this
remains a single batched query, never N+1) and returns the transcripts dict alongside the existing
`(assignments, total)` tuple. `search_request_service.py`'s own module docstring is updated at implementation time
to state precisely: the write/orchestration path (`handle_session_completed`) still has zero imports from
`conversation` and still receives only plain primitives (AI-002's original guarantee, unchanged); this story adds
`search`'s *only* import from `conversation`, scoped strictly to this one read-only admin-transcript path, and
deliberately targets `conversation.repositories`/`conversation.models` only, never `conversation.services`.

**Alternatives considered and rejected:**
- **Route handler calls `ConversationService` directly, bypassing `SearchRequestService`.** Rejected — breaks
  `list_pending_manual_matches`'s own documented convention ("lets `search/api.py`'s admin route depend only on
  this module's own service"), and still hits the same circular-import problem if wired via
  `conversation.dependencies`.
- **Move `manual_match_assignments`' admin routes into `conversation` instead**, since `conversation` already owns
  `Message`. Rejected — would relocate an already-shipped, already-tested, working endpoint purely to solve an
  import-direction problem, a much larger and riskier change than adding one new leaf-level Repository import.

### Decision 5 — AC3, AC4, and AC6-for-manual-matches need no new backend write logic; this story's job there is verification/regression-confirmation only

Directly established in Verified Current State above with file/line/test-name evidence: `resolve_manual_match`
already writes `provider_matches` through `_finalize_matches` with the admin's own supplied order as `rank`
(AC3); the customer read path is already identical regardless of resolution method (AC4); `require_role(ROLE_ADMIN)`
already gates both existing manual-match routes with a passing 403 test each (AC6, partially — the *new*
`unmatched_query_reports` routes still need their own 403 tests, Decision 8 area); and
`test_resolving_with_provider_ids_returns_matched_result` already covers AC7's first bullet end-to-end. **Chosen:**
this Plan's Backend items for the manual-match side are limited to Decision 3/4's transcript addition; the full
existing backend suite (783+ tests) is re-run as a regression gate, and `tester` independently re-verifies AC3/
AC4/AC6-for-manual-matches/AC7-bullet-1 against the real, already-shipped code rather than writing brand-new tests
that would just duplicate `test_search_request_api.py`'s existing coverage. This is a routine, well-evidenced
scoping call, not a corner cut — the story's real net-new engineering is concentrated in AC1/AC2/AC5.

### Decision 6 — `administration` module gets its first-ever `api.py`, hosting the new `unmatched_query_reports` endpoints; a new, minimal `search.SearchEventLogService` supplies read-only display context

**The problem:** unlike `administration`'s three existing aggregates (each resolved by writing into some *other*
module's schema, which is why their routes live in that other module), marking an `unmatched_query_reports` row
`reviewed`/`actioned` is a **self-contained state transition entirely within `administration`'s own table** — no
write into `search` or anywhere else is needed to complete the action. The only cross-module need is a read: enough
`search_event_log` context (`category_id`, `customer_id`, `query_text`, `result_count`) for an admin to make an
informed review/action decision, exactly analogous to how `verification/admin_api.py` reads `provider.Provider`
for display context without ever writing to it.

**Chosen:** give `administration` its own `api.py` for the first time (`router = APIRouter(tags=["Admin
Unmatched Query Reports"])`, mounted at `/admin/unmatched-query-reports`) — the natural, evidence-based conclusion
of Verified Current State's finding that every prior "no `api.py`" instance was caused by a cross-module *write*
need this capability simply doesn't have. For the read-only enrichment, add a new, minimal
`search.services.search_event_log_service.SearchEventLogService` (`get_by_ids(ids) -> dict[UUID, SearchEventLog]`,
backed by one new `SearchEventLogRepository.list_by_ids` method) and wire it as a constructor dependency of the
new `administration.UnmatchedQueryReportService` — `administration`'s first-ever outgoing cross-module edge
(`administration -> search`), via a Service (satisfying `ADR-047`'s "Services only" preference in full, no raw
Repository needed here since `search` has no equivalent circular-import obstacle in this direction).
`administration/dependencies.py`'s new wiring docstring names this edge explicitly, per `ADR-054`'s closeout note
that this naming duty is mandatory at implementation time, not left for `architect` to catch.

**Alternatives considered and rejected:**
- **Host the new routes in `search/admin_manual_match_api.py` instead**, purely to preserve the superficial "no
  `api.py` in `administration`" pattern. Rejected — there is no genuine cross-module write-orchestration need
  here (unlike the three existing precedents), so forcing it into `search` would misrepresent which module truly
  owns the capability, and would need the exact same new `search -> search_event_log` read plus an *additional*
  `search -> administration.UnmatchedQueryReportService` write edge for status transitions — strictly more
  cross-module surface than placing it correctly in `administration` to begin with.
- **A cross-schema SQL `JOIN` inside `UnmatchedQueryReportRepository`** (importing `search.models.SearchEventLog`
  directly into `administration`'s own query, mirroring `search_request_service.py`'s existing direct import of
  `administration.models.ManualMatchAssignment`). Considered — technically leaf-safe (no cycle), but rejected as
  a materially different and riskier pattern than the codebase's established "Services only" cross-module rule,
  which the alternative chosen (a real `SearchEventLogService`) satisfies cleanly with negligible extra code.

### Decision 7 — AC5's filter/sort scope is `status` + `created_at` only; category-level filtering is deliberately deferred, not silently dropped

**The problem:** AC5 says "filtered/sorted" without naming specific fields. `category_gap_notes`/`status` live on
`unmatched_query_reports` itself; `category_id`/`query_text`/`customer_id` live on the joined `search_event_log`
row, fetched via `SearchEventLogService.get_by_ids` *after* the page's own rows are already selected (Decision 6).

**Chosen:** filter by `status` (`open`/`reviewed`/`actioned`/`all`, default `open` — matching every existing
admin queue's convention of defaulting to the actionable subset) and sort by the report's own `created_at`
(`created_at_asc`/`created_at_desc`, default ascending, oldest-first, matching every existing queue's ordering) —
both are plain columns on `unmatched_query_reports` itself, filterable/sortable directly in SQL with correct
pagination. A true category-level filter would need the join to happen *before* pagination (to avoid the
`ADR-042`/`ADR-042`-adjacent "never filter/paginate in Python after `LIMIT`/`OFFSET`" anti-pattern), which this
Plan judges as unnecessary complexity for a capability no AC literally requests. This is a deliberately scoped,
flagged deferral (Open Question 2), not a silently dropped requirement — the underlying `category_id` is still
visible on every list row via the existing enrichment, so an admin can still see it, just not filter a whole page
by it yet.

**Alternatives considered and rejected:**
- **A category filter implemented as a post-pagination Python filter.** Rejected outright — would either return
  fewer than `page_size` items per page for no visible reason, or defeat pagination's correctness guarantee
  entirely, the exact anti-pattern this codebase's ranking-formula precedent (`ADR-042`) already rejects.
- **Add the cross-schema join now, just to support category filtering.** Rejected for this iteration — real, but
  avoidable complexity (a new join pattern with no existing precedent) for a filter dimension no AC names
  explicitly; flagged instead of silently built or silently dropped.

### Decision 8 — Status-transition mechanics: atomic conditional `UPDATE`, forward-only lifecycle, one shared 409 exception

**The problem:** AC5 needs "marked reviewed/actioned by an admin" with two admins potentially racing on the same
report, and a defined transition order (`open` → `reviewed` → `actioned`, per AC1's own literal enum ordering).

**Chosen:** `UnmatchedQueryReportRepository.try_transition_status(report_id, *, from_statuses, to_status, ...)` — a
single conditional `UPDATE ... WHERE id = :id AND status IN (:from_statuses)`, mirroring
`ManualMatchAssignmentRepository.try_resolve`/`VerificationRecordRepository.try_claim_for_review`/
`ProviderRepository.try_claim_for_account`'s identical "never a read-then-write check" family. Two entry points:
`mark_reviewed` (`open` → `reviewed` only) and `mark_actioned` (`open` **or** `reviewed` → `actioned`, since a
single admin may reasonably action a report directly without a separate review step first). Any disallowed
transition (repeat call, or an attempted backward move) raises one shared new `UnmatchedQueryReportInvalidTransitionError`
(409) — per `ADR-053`'s "reuse for an identical check, add new only for a genuinely distinct reason," both failure
paths collapse to the exact same underlying reason ("this transition isn't valid from the report's current
status"), so one exception suffices rather than two.

**Alternatives considered and rejected:**
- **A single generic `PATCH .../status` endpoint accepting any target status.** Rejected — every existing admin
  queue in this codebase uses explicit verb-shaped endpoints (`/resolve`, `/approve`, `/reject`), never a generic
  status-PATCH; two explicit endpoints (`/review`, `/action`) stay consistent with that convention and make the
  allowed-transition rules explicit in the routing itself rather than in a runtime status-value check.
- **Idempotent no-op on a repeat transition** (return 200 instead of 409 if already in the target status).
  Rejected — every existing "already resolved" precedent in this codebase treats a repeat admin action as a
  rejected 409, not a silent no-op; consistency with that established idiom was preferred over a debatable
  idempotency convenience nobody asked for.

### Decision 9 — The response exposes `customer_id`/`query_text`/`category_id` directly — this is an admin operational tool, not "Analytics" under `06_SECURITY.md`'s restriction

**The problem:** `06_SECURITY.md`'s Sensitive Data section states sensitive/customer-identifying data must never
appear in "Analytics" (the exact restriction `LEAD-002`'s `VisibilityAnalyticsService` deliberately avoided
tripping, Decision 8 there). Does an admin-facing unmatched-query queue count as "Analytics" under that rule?

**Chosen:** no — this is judged the same category of admin operational tool `claim_review_requests` already is,
which exposes `claimant_user_id` (a real, unmasked customer-identifying field) directly to an admin reviewing a
specific case, not an aggregate, provider-facing "Analytics" surface. `06_SECURITY.md`'s restriction targets
provider-facing/aggregate reporting surfaces (`LEAD-002`'s own worked example), not an admin's operational,
per-case review queue, where identifying the specific customer/search is often the entire point of "spotting a
supply/category gap" (the story's own stated purpose). `UnmatchedQueryReportResponse` therefore carries
`customer_id` and `query_text` (currently always `null`, Decision 1's flagged limitation) directly, alongside
`category_id`, `result_count`, and the report's own workflow fields.

**Alternatives considered and rejected:**
- **Omit `customer_id`/`query_text` from the response entirely**, treating this as in-scope for
  `06_SECURITY.md`'s Analytics restriction. Rejected — would make the admin queue meaningfully less useful for its
  stated purpose, and has no precedent in this codebase's existing admin-queue responses, all three of which
  already expose a real, unmasked identifying field for their respective review context.

---

## Backend — Proposed Changes

1. **New migration** `backend/alembic/versions/<timestamp>-<hash>_unmatched_query_reports.py` (down_revision =
   `c3c4d5e6f7a8`, the current head) — creates `administration.unmatched_query_reports` with the full
   `CommonColumnsMixin` plus `search_event_log_id` (UUID, not null, FK → `search.search_event_log.id`, unique
   constraint `uq_unmatched_query_reports_search_event_log_id`), `category_gap_notes` (TEXT, nullable), `status`
   (VARCHAR(20), not null, server default `'open'`), `reviewed_by` (UUID, nullable, FK → `identity.users.id`),
   `reviewed_at` (TIMESTAMPTZ, nullable); index `idx_unmatched_query_reports_status` — mirrors
   `602bf3c4bea7_claim_review_requests.py`'s exact template.
2. **`backend/app/modules/administration/models.py`** — add `UnmatchedQueryReport(CommonColumnsMixin, Base)`
   matching item 1's columns exactly, reusing the module's existing `_SEARCH_SCHEMA`/`_IDENTITY_SCHEMA` constants.
3. **New file `backend/app/modules/administration/repositories/unmatched_query_report_repository.py`** —
   `UnmatchedQueryReportRepository(BaseRepository[UnmatchedQueryReport])`:
   - `list_filtered(*, status: str | None, sort_desc: bool, offset: int, limit: int) -> tuple[list[UnmatchedQueryReport], int]`
     — `WHERE status = :status` only when `status is not None`, `ORDER BY created_at` asc/desc per `sort_desc`.
   - `try_transition_status(report_id, *, from_statuses: tuple[str, ...], to_status: str, admin_user_id: UUID,
     reviewed_at: datetime, category_gap_notes: str | None) -> bool` — atomic conditional `UPDATE ... WHERE id =
     :id AND status IN :from_statuses` (Decision 8), returns whether the caller's own call won the transition.
4. **New file `backend/app/modules/administration/services/unmatched_query_report_service.py`** —
   `UnmatchedQueryReportService(repository, search_event_log_service)`:
   - `create(*, search_event_log_id: UUID) -> UnmatchedQueryReport` — `status="open"` (Decision 2's write-time hook).
   - `list_filtered(*, status, sort_desc, page, page_size) -> tuple[list[UnmatchedQueryReport], dict[UUID,
     SearchEventLog], total]` — paginates, then batch-enriches via `search_event_log_service.get_by_ids`
     (Decision 6).
   - `get_by_id(report_id) -> UnmatchedQueryReport | None`.
   - `mark_reviewed(report_id, *, admin_user_id, category_gap_notes) -> tuple[UnmatchedQueryReport,
     SearchEventLog | None]` — 404 `UnmatchedQueryReportNotFoundError` if missing, 409
     `UnmatchedQueryReportInvalidTransitionError` if `try_transition_status(from_statuses=("open",),
     to_status="reviewed", ...)` fails (Decision 8).
   - `mark_actioned(report_id, *, admin_user_id, category_gap_notes) -> tuple[UnmatchedQueryReport, SearchEventLog
     | None]` — same shape, `from_statuses=("open", "reviewed")`, `to_status="actioned"`.
5. **`backend/app/modules/search/repositories/search_event_log_repository.py`** — add
   `list_by_ids(ids: list[UUID]) -> list[SearchEventLog]` (`WHERE id IN (...)`, empty list short-circuits to `[]`).
6. **New file `backend/app/modules/search/services/search_event_log_service.py`** — `SearchEventLogService
   (repository)`: `async def get_by_ids(self, ids: list[UUID]) -> dict[UUID, SearchEventLog]` (Decision 6, keyed
   batch lookup).
7. **`backend/app/modules/search/dependencies.py`** — add `get_search_event_log_service` (mirrors every other
   `get_*_service` provider in this file); add `get_message_repository` (Decision 4 — constructs
   `conversation.repositories.message_repository.MessageRepository(db)` directly, **never** importing
   `conversation.dependencies`, avoiding the circular-import Decision 4 documents); extend
   `get_search_request_service`'s signature with the new `message_repository` dependency.
8. **`backend/app/modules/search/services/search_request_service.py`**:
   - Constructor gains `message_repository: MessageRepository` (Decision 4).
   - `_finalize_matches` gains one additive call (Decision 2): capture the `search_event_log_repository.create(...)`
     return value, and when `not ranked_matches`, call a new `unmatched_query_report_service.create(...)`.
     Requires the constructor to also gain `unmatched_query_report_service:
     administration.services.unmatched_query_report_service.UnmatchedQueryReportService` (a second
     `search -> administration` service edge, Decision 2).
   - `list_pending_manual_matches` (in-place upgrade, Decision 3/4): after fetching `(assignments, total)` from
     `ManualMatchAssignmentService.list_pending`, batch-fetch `self.message_repository.list_for_sessions([a.
     conversation_session_id for a in assignments])` and return `(assignments, transcripts_by_session, total)`.
   - Update the module's own top-of-file docstring (Decision 4): the write/orchestration path
     (`handle_session_completed`) still has zero imports from `conversation` and still receives only plain
     primitives; this story adds `search`'s only import from `conversation`, scoped to the read-only admin-
     transcript path, targeting `conversation.repositories`/`conversation.models` only.
9. **`backend/app/modules/conversation/repositories/message_repository.py`** — add `list_for_sessions(
   session_ids: list[UUID]) -> dict[UUID, list[Message]]` (`WHERE conversation_session_id IN (...) AND
   is_active`, grouped by session id, each group ordered by `sequence_number` ascending — mirrors
   `list_for_session`'s single-session filtering/ordering, batched).
10. **`backend/app/modules/search/schemas.py`** — `ManualMatchAssignmentSummaryResponse` gains `transcript:
    list[MessageResponse] = Field(default_factory=list)` (Decision 3), importing `MessageResponse` from
    `app.modules.conversation.schemas`; update the class's own docstring (its exclusion note no longer applies).
11. **`backend/app/modules/search/admin_manual_match_api.py`** — `_to_summary` gains a `transcript: list[Message]`
    parameter, mapped via `conversation.schemas.message_to_response`; `list_pending_manual_matches`'s handler
    unpacks the new 3-tuple and passes each assignment's transcript through.
12. **New file `backend/app/modules/administration/schemas.py`** (administration's first schemas file) —
    `UnmatchedQueryReportResponse` (`id`, `status`, `category_gap_notes`, `reviewed_by`, `reviewed_at`,
    `created_at`, `search_event_log_id`, `category_id`, `customer_id`, `query_text`, `result_count` — Decision 9);
    `UnmatchedQueryReportActionRequest` (`category_gap_notes: str | None`, used by both `/review` and `/action`).
13. **New file `backend/app/modules/administration/api.py`** (administration's first `api.py`, Decision 6) —
    `router = APIRouter(tags=["Admin Unmatched Query Reports"])`:
    - `GET ""` → `GET /admin/unmatched-query-reports` — query params `status: Literal["open", "reviewed",
      "actioned", "all"] = "open"`, `sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc"`,
      `page`, `page_size` (capped at `settings.UNMATCHED_QUERY_REPORT_MAX_PAGE_SIZE`); `require_role(ROLE_ADMIN)`;
      returns `CollectionResponse[UnmatchedQueryReportResponse]`.
    - `POST "/{report_id}/review"` → `mark_reviewed`; `require_role(ROLE_ADMIN)`; 200/404/409 documented; returns
      `SuccessResponse[UnmatchedQueryReportResponse]`.
    - `POST "/{report_id}/action"` → `mark_actioned`; same shape as above.
14. **`backend/app/modules/administration/dependencies.py`** — add `get_unmatched_query_report_repository`,
    `get_unmatched_query_report_service` (wiring in `search.dependencies.get_search_event_log_service` — the
    module's first-ever cross-module import; docstring names this explicitly per `ADR-047`/`ADR-054`'s naming
    duty).
15. **`backend/app/core/config.py`** — add `UNMATCHED_QUERY_REPORT_MAX_PAGE_SIZE: int = 50` (mirrors
    `SEARCH_MAX_PAGE_SIZE`'s existing config-driven-constant convention).
16. **`backend/app/core/exceptions/exceptions.py`** — add `UnmatchedQueryReportNotFoundError` (404, mirrors
    `ManualMatchAssignmentNotFoundError`/`ClaimReviewRequestNotFoundError`) and
    `UnmatchedQueryReportInvalidTransitionError` (409, mirrors `ManualMatchAssignmentAlreadyResolvedError`,
    Decision 8).
17. **`backend/app/api/v1/api.py`** — import `administration.api.router` and register
    `v1_router.include_router(admin_unmatched_query_report_router, prefix="/admin/unmatched-query-reports")`,
    placed directly after the existing `admin_manual_match_router` registration.
18. **Existing test call sites instantiating `SearchRequestService` directly** (any unit test constructing it with
    explicit keyword arguments) must be updated to pass the two new constructor dependencies
    (`message_repository`, `unmatched_query_report_service`) — flagged here so `backend` doesn't discover this as
    a surprise break while running the full suite.

### Tests

19. `backend/tests/modules/administration/test_unmatched_query_report_service.py` (new) — `create` (status
    defaults to `open`); `list_filtered` (status filter, both sort directions, pagination correctness, enrichment
    dict keyed correctly, a report whose `search_event_log_id` somehow has no matching row — defensive `None`
    handling, never a fabricated value); `mark_reviewed`/`mark_actioned`'s full transition matrix, each case
    separately named: `open→reviewed` succeeds; `open→actioned` succeeds; `reviewed→actioned` succeeds;
    `reviewed→reviewed` (repeat) → 409; `actioned→reviewed`/`actioned→actioned` (backward/repeat) → 409;
    nonexistent id → 404 for both entry points.
20. `backend/tests/modules/administration/test_unmatched_query_report_repository.py` (new) — `try_transition_status`'s
    atomic-race behavior (mirrors `try_resolve`'s own test shape: two concurrent calls, exactly one wins);
    `list_filtered`'s SQL-level correctness independent of the service layer.
21. `backend/tests/modules/administration/test_unmatched_query_report_api.py` (new) — full HTTP round trips: 200
    list (default `status=open` filter, explicit `status=all`, both sort orders); 200 `/review`/`/action`; 404 for
    a nonexistent id; 409 for an invalid transition; **403 for a non-admin caller on all three routes** (AC6, the
    new routes' own dedicated coverage, distinct from the already-existing manual-match 403 tests).
22. `backend/tests/modules/search/test_search_request_service.py` — extend `_finalize_matches`'s existing test
    coverage: an unmatched resolution (empty `ranked_matches`, either automated-path-with-no-address or
    manual-path-with-empty-`provider_ids`) creates exactly one `unmatched_query_reports` row pointing at the
    correct `search_event_log_id`; a **matched** resolution creates zero such rows (the negative case, explicitly
    asserted, not just "not tested for").
23. `backend/tests/modules/search/test_search_request_api.py` — extend `TestListPendingManualMatches` with a new
    assertion that each returned item's `transcript` field contains the session's real messages, oldest first,
    matching what `MessageRepository.list_for_session` would return directly for that session id; add a
    multi-assignment fixture confirming assignment A's transcript never contains assignment B's messages (the
    batching correctness check, since `list_for_sessions` groups in one query).
24. `backend/tests/modules/conversation/` (extend `test_conversation_service.py` or add a focused
    `test_message_repository.py`, whichever this codebase's own convention favors on inspection) —
    `MessageRepository.list_for_sessions`: correct grouping across two+ sessions, correct per-session ordering,
    soft-deleted messages excluded, an empty input list returns an empty dict.
25. Full existing backend suite re-run (not just new tests — Decision 5's regression-confirmation duty explicitly
    includes re-verifying AC3/AC4/AC6-for-manual-matches/AC7-bullet-1 still pass unmodified), plus `ruff check .`.

---

## Frontend — Proposed Changes

**None.** Confirmed in Verified Current State: the story's own text defers the admin platform choice (Flutter vs.
a separate internal tool) as an explicitly open decision, and frames this story as "the API layer, which is
platform-agnostic." Every prior admin-queue story in this codebase (`VER-002`, `CLM-001`'s admin side, `AI-002`'s
admin side) shipped backend-API-only with zero Flutter screens, and `ADM-001`'s own tracker description confirms
this pattern continues here. No mobile work is in scope for this story.

---

## Explicitly Out of Scope (do not implement in this story)

- **The admin platform itself** (Flutter admin screens, or a separate internal tool) — the story's own explicit
  scope boundary; this Plan is backend-API-only.
- **`VER-002`'s verification review** and **`ADM-002`'s broader admin dashboard shell** — both explicitly named as
  out of scope in the story's own text.
- **Fixing `search_event_log.query_text`'s always-`None` write path** (Decision 1's flagged limitation) — a
  pre-existing AI-002 gap, not something AC1 asks this story to repair.
- **Category-level filtering of `unmatched_query_reports`** (Decision 7) — deliberately deferred, flagged at Open
  Question 2, not silently dropped.
- **Any push-notification/alerting mechanism** for either queue — no such recipient concept exists anywhere in
  this codebase (`ADR-030`'s "never invent a push-notification 'notify the admin team' mechanism" precedent
  applies directly); both queues remain pull-based (`GET .../queue`, admin polls).
- **`feature_flags`/`system_settings`** — also named "remain unbuilt" alongside `unmatched_query_reports` in
  `04_DATABASE.md`, but not part of any of this story's 7 ACs; not built here.
- **CSV/data export of any kind** for either queue.
- **Bulk/multi-select review or action** on `unmatched_query_reports` — AC5 asks for filter/sort plus a per-report
  status change, not a bulk-operation UI/API.

---

## Open Questions (flagged for CTO awareness — do not block `backend` from starting; per standing instruction, resolved with this Plan's own stated recommendation if not addressed before implementation)

1. **`search_event_log.query_text` is always `None` today** (Decision 1) — a pre-existing AI-002 write-path gap,
   not something this Plan fixes. Every `unmatched_query_reports` row will therefore show `query_text: null` until
   a future story wires the customer's real free text through `_finalize_matches`. Recommended default: ship
   `ADM-001` as planned (the table/workflow itself is fully functional and useful via `category_id` alone), and
   track the `query_text` gap as a follow-up item at closeout.
2. **AC5's filter/sort scope is `status` + `created_at` only** (Decision 7) — `category_id`-level filtering is
   visible per-row but not filterable as a whole-page query dimension yet, since doing so correctly would require
   a new cross-schema join-before-paginate pattern with no current precedent. Recommended default: ship as scoped
   in this Plan; revisit only if real admin usage shows this filter is actually needed.
3. **`SESSION_HANDOFF.md`'s precedent-list correction** (Decision 1) — a documentation-only fix at closeout, not a
   product decision, flagged here only so the CTO isn't surprised the shipped code diverges from that file's prior
   phrasing.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story (fresh start — Sprint 11's first story, immediately following Sprint 10's
clean close with no open Checkpoint left behind).

1. **backend** — Backend Proposed Changes items 1-18, Tests items 19-25. Suggested build order: (a) migration +
   model (items 1-2) first, since everything else depends on the table existing; (b) `administration`'s new
   repository/service (items 3-4) with tests 19-20 written alongside; (c) `search`'s new
   `SearchEventLogService`/`list_by_ids` (items 5-6) and the new `administration.api`/`schemas` (items 12-14),
   with test 21 (the full HTTP round trip, including the 403 checks) once wiring is complete; (d) the `_finalize_matches`
   write-time hook (item 8's first half) with test 22; (e) the transcript path last (items 7-11, Decision 3/4 —
   the most architecturally sensitive piece, given the circular-import reasoning; read Decision 4 in full before
   starting) with tests 23-24; (f) item 18's existing-test-call-site sweep and the full regression run (test 25)
   at the very end. Read Decisions 2, 4, 6, and 8 in full before starting — they are this story's real engineering
   substance; Decision 5 defines what does *not* need new backend code.
2. **tester** — verify all 7 verbatim ACs with real evidence (real DB, real HTTP round trips):
   - **AC1**: the migration applies cleanly; the table's columns/constraints match `04_DATABASE.md`'s spec exactly;
     a genuinely unmatched search creates exactly one report row, a matched one creates zero.
   - **AC2**: the list endpoint's `transcript` field genuinely reflects each assignment's own session's real
     messages (the multi-assignment, no-cross-contamination fixture, test 23).
   - **AC3/AC4/AC6-for-manual-matches/AC7-bullet-1**: independently re-confirm the already-shipped AI-002 behavior
     still holds unmodified after this story's changes (Decision 5) — do not skip this just because it's
     "already tested"; a regression here would be a real, high-severity bug this story introduced.
   - **AC5**: the full status-transition matrix (test 19's separately-named cases), plus filter/sort correctness
     over real HTTP.
   - **AC6**: 403 for a non-admin caller on **all three new** `unmatched_query_reports` routes, not just the
     pre-existing manual-match routes.
   - **AC7**: both required test categories exist and pass (manual-match customer-visible result — already
     existing, re-confirmed; unmatched-report status transitions — newly added, test 19/21).
3. **architect** — review: Decision 2's `_finalize_matches` in-place extension for correctness against `ADR-042`
   (no divergent parallel write path introduced); Decision 4's circular-import reasoning and the new
   `search -> conversation.repositories.MessageRepository` edge against `02_ARCHITECTURE.md`/`ADR-047` (confirm no
   accidental import of `conversation.services`/`conversation.dependencies` anywhere, and that the module
   docstring update genuinely reflects the new, narrower "zero imports from conversation" claim); Decision 6's new
   `administration/api.py` and the new `administration -> search.SearchEventLogService` edge for correct
   `ADR-047`/`ADR-054` docstring-naming; Decision 8's atomic-transition mechanics for a genuine race-safety proof
   (not just "tests pass"); Decision 9 against `06_SECURITY.md`'s Sensitive Data section for the
   Analytics-vs-operational-tool distinction; confirm no new circular import anywhere via a full `python -c
   "import app.main"`-style sanity check if `architect` has that tooling available.
4. Once `tester` and `architect` both report clean, **the orchestrator proceeds straight through closeout without
   an additional sign-off pause**, per the CTO's standing instruction for this story — present the final summary
   to the user after closeout rather than pausing beforehand. A failed or "sent back" verdict from either still
   loops back to `backend` automatically first, as always.
5. At closeout: record Decisions 1-9 as new ADRs (next available: **ADR-058** onward, grouped by shared
   architectural theme at `tech-lead`'s discretion — Decision 1 (documentation correction) is not itself an ADR,
   but Decisions 2/3/4/6/8 each generalize or extend an existing precedent and are the most likely candidates for
   a dedicated ADR each); update `04_DATABASE.md`'s Administration Domain section to mark
   `unmatched_query_reports` as shipped (removing it from the "remain unbuilt" list) and to note `administration`'s
   first cross-module edge and first `api.py`; correct `SESSION_HANDOFF.md`'s §4 precedent-list wording (Decision
   1); update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 11 section; update `docs/AI/SESSION_HANDOFF.md` with the
   new state (test counts, ADR numbering, Sprint 11/`ADM-002` framing).

---

## Verification Plan (mapped to the 7 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Migration applies cleanly and matches `04_DATABASE.md`'s spec (columns, FK, unique constraint, index); `test_search_request_service.py`'s new unmatched-creates-a-report / matched-creates-none cases (test 22). |
| 2 | `test_search_request_api.py`'s extended `TestListPendingManualMatches` transcript assertions, including the no-cross-contamination multi-assignment fixture (test 23); `test_message_repository.py`/`test_conversation_service.py`'s `list_for_sessions` unit coverage (test 24). |
| 3 | Already-existing `test_resolving_with_provider_ids_returns_matched_result` and the `ProviderMatchRepository.bulk_create` rank-from-order code path (Decision 5) — re-confirmed as a regression gate, not newly built. |
| 4 | Same existing test's customer-facing `GET /search-requests/{id}` assertion (Decision 5) — re-confirmed as a regression gate. |
| 5 | `test_unmatched_query_report_service.py`'s full transition matrix (test 19) and `test_unmatched_query_report_api.py`'s filter/sort HTTP assertions (test 21). |
| 6 | `test_unmatched_query_report_api.py`'s three new 403 cases (test 21) for the new routes; already-existing `test_list_returns_403_for_a_non_admin`/`test_resolve_returns_403_for_a_non_admin` re-confirmed as a regression gate for the manual-match routes. |
| 7 | Already-existing `test_resolving_with_provider_ids_returns_matched_result` (bullet 1, re-confirmed); `test_unmatched_query_report_service.py`/`test_unmatched_query_report_api.py`'s new status-transition tests (bullet 2, tests 19/21). |

---

## Related Documents

- `docs/AI/04_DATABASE.md` (Administration Domain — `unmatched_query_reports`' already-specified column shape this
  Plan builds exactly, and its "remain unbuilt" note this story resolves; Search Domain — `search_event_log`'s
  exact shipped columns)
- `docs/AI/03_DOMAIN_MODEL.md` (Administration domain's entity list, "Unmatched Query Report" already named)
- `docs/AI/SESSION_HANDOFF.md` (§4's precedent-list entry this story's closeout corrects; §2's `ADM-001` framing)
- `docs/AI/09_DECISIONS.md` (`ADR-030` — no push-notification mechanism; `ADR-038` — anti-fabrication, underlying
  the `query_text`/enrichment `None`-handling; `ADR-042` — in-place upgrade of a shared write path, the direct
  precedent for Decision 2's `_finalize_matches` extension; `ADR-047` — Services-only cross-module rule and its
  raw-Repository exception, extended by Decision 4's second justification; `ADR-048` — multi-aggregate-root module
  pattern, directly reused by `unmatched_query_reports` becoming `administration`'s fourth slice; `ADR-050` — no
  invented scheduling infrastructure, underlying Decision 2's write-time-hook choice; `ADR-051`/`ADR-054` —
  schema/module placement rules underlying Decision 6; `ADR-053` — reuse-an-exception-for-an-identical-reason,
  underlying Decision 8's single 409 exception)
- `docs/AI/06_SECURITY.md` (Sensitive Data section — Decision 9's Analytics-vs-operational-tool reasoning)
- `docs/implementation/plans/Plan_S07_AI-002.md` / `Walkthrough_S07_AI-002.md` (`manual_match_assignments`'
  original design, the `_finalize_matches` shared-write mechanism this story extends in place, and the explicit
  "transcript is `ADM-001`'s job" deferral this story resolves)
- `docs/implementation/plans/Plan_S05_VER-002.md` (the `admin_action_log`/embed-context-in-list-response precedent
  Decision 3/6 both directly reuse)
- `docs/implementation/plans/Plan_S06_CLM-001.md` (`claim_review_requests`' migration template Backend item 1
  mirrors exactly, and its `claimant_user_id` exposure precedent underlying Decision 9)
- `docs/implementation/plans/Plan_S10_LEAD-002.md` (this codebase's most recent Plan, whose document structure and
  level of Decision/Alternative detail this Plan mirrors)

---

**End of Document**
