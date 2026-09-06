# Walkthrough S02 AUTH-004

## Story: Access the App According to My Role

**Sprint:** 02 | **Story ID:** AUTH-004 | **Priority:** High | **Status:** Done

As a customer, provider, or administrator, I want the app and API to enforce what I'm allowed to do based on
my role, so that my account and the platform's other users are protected from unauthorized actions.

This is the fourth and last story in Sprint 2 ("Identity & Access"). It builds the reusable authorization
layer — role checks, 401-vs-403 semantics, an ownership-check helper, audit logging, and confirmation of
already-shipped auth-endpoint rate limiting — that every later feature story's protected endpoints will
depend on. Full context, architecture decisions, and file-by-file scope:
`docs/implementation/plans/Plan_S02_AUTH-004.md` (see its Supersession Notice — it replaced a stale slice of
the old, superseded 9-story Sprint 2 backlog).

**This story was backend-only — no mobile track.** This was a deliberate scope call made by `tech-lead`
during planning (see the Plan's Mobile Scope Assessment), not an oversight: all 9 acceptance criteria describe
backend/API-side enforcement (a dependency, an exception-status distinction, a helper function, one backend
endpoint, rate limiting that already existed, and an audit table). No screen in `15_SCREEN_INVENTORY.md`
currently needs to call `GET /auth/me` — the natural future consumer (S-14 "Profile & Settings") doesn't exist
yet. Every later story that builds a role-gated mobile screen will wire its own consumption of this mechanism
at that time.

---

## What was implemented

### Backend (`backend/app/core/`, `backend/app/api/`, `backend/app/modules/identity/`, `backend/app/modules/audit/`)

- **`require_role()` dependency** (`backend/app/api/dependencies.py`) — a parametrized, composable FastAPI
  dependency (`RequireRole`/`require_role(*allowed_roles)`), layered on top of the existing `get_current_user`
  rather than replacing it. Because it depends on `get_current_user`, a missing/invalid/expired token 401s
  before the role check is ever reached; `require_role()` itself can only ever raise the new
  `InsufficientRoleError` (403), for a validly authenticated caller whose `roles` claim doesn't intersect the
  endpoint's allowed set. Usable on any endpoint via `Depends(require_role(ROLE_ADMIN))` etc.
- **`ensure_owner_or_not_found`** (new, `backend/app/core/authorization.py`) — a small, reusable
  ownership-check helper (`if owner_id != requester_id: raise not_found_exc`) that collapses "resource doesn't
  exist" and "exists but isn't yours" into the same non-revealing 404, rather than a 403 that would confirm
  the resource exists. `SessionService.revoke_session` was refactored to call this helper instead of its
  previous inline check — a zero-observable-behavior-change refactor, now reusable by future stories.
- **New `audit` module** (`backend/app/modules/audit/`) — mirrors the existing per-schema module pattern
  (model → repository → service → dependencies, no `api.py`/`schemas.py` since nothing here is HTTP-exposed
  yet). `AuditLog` extends plain `Base`, not `CommonColumnsMixin` (no `updated_at`/`deleted_at`/`is_active`/
  `version` — immutable by design). `AuditLogRepository` exposes only `create()` — no `update`/`delete` method
  is ever defined, so immutability is structural, not just a docstring claim. `AuditService` exposes four
  explicit methods (`record_registration`, `record_login`, `record_logout`, `record_session_revocation`)
  rather than one generic `record(action, ...)`, keeping every call site's intent unambiguous. `identity`'s
  services depend on `audit`'s **service** only, never its repository — correct dependency direction per
  `02_ARCHITECTURE.md`.
  - New migration `backend/alembic/versions/2026_09_06_0900-d81be77c601d_audit_domain.py` creates the `audit`
    schema and `audit.audit_logs` table exactly per `04_DATABASE.md`'s already-fixed spec: `id` (UUID PK),
    `actor_user_id` (nullable, FK → `identity.users.id`), `action` (VARCHAR(100)), `entity_type` (VARCHAR(50)),
    `entity_id` (nullable UUID), `before_state`/`after_state` (nullable JSONB), `ip_address` (nullable INET),
    `created_at` (TIMESTAMPTZ, default `now()`), with all three documented indexes.
  - Audit events are wired into four real code paths: **registration** and **login** from
    `AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth` (registration only fires when the
    user is new); **logout** from `SessionService.revoke_session` when the caller ends their own current
    session; **session_revocation** from the same method when ending a *different* session, and unconditionally
    from `revoke_all_sessions` (bulk "log out everywhere," even when `keep_current=True`). No `before_state`/
    `after_state` value ever contains a phone number, email, raw token, or token hash.
- **`GET /auth/me`** (new, `backend/app/modules/identity/api.py`) — protected by
  `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)`, returns the caller's own id/roles/status. Backed by
  a new `AuthService.get_current_user_summary(user_id)`. Reuses the existing `UserSummaryResponse` schema
  rather than introducing a duplicate, near-identical one (`08_CODING_STANDARDS.md`: never duplicate models).
- **Rate limiting (AC6/AC7)** — re-confirmed, not re-implemented. All five auth endpoints
  (`request-otp`/`verify-otp`/`google`/`apple`/`refresh`) already carried Redis-backed, 10-requests/minute rate
  limiting from AUTH-001/002, returning the generic, non-revealing 429 message. This story's only involvement
  was independently re-running the existing rate-limit test suites (both `backend` and `architect`,
  separately) to confirm the mechanism was untouched — confirmed via `git diff` showing zero changes to
  `app/core/rate_limit.py`.
- **`revoke_session`/`revoke_all_sessions` signature extension** — both now accept optional keyword-only
  `current_session_id`/`ip_address` parameters (defaults preserve every pre-existing call site's behavior),
  used to distinguish `logout` from `session_revocation` and to populate the audit row's `ip_address`.
- **Tests** — new `backend/tests/modules/audit/test_audit_service.py`; new `TestRequireRole` class in
  `backend/tests/api/test_dependencies.py`; new `TestGetMe` class (200/401×3/403 matrix) in
  `backend/tests/modules/identity/test_auth_endpoints.py`; new `TestRevokeSessionAuditLogging` class in
  `backend/tests/modules/identity/test_session_service.py` (logout vs. session_revocation vs. bulk revoke-all,
  asserted against real DB rows); extended `test_auth_service.py` with audit-call assertions (including
  explicit `assert_not_awaited()` checks that `record_registration` never fires for a returning user).
  **211/211 backend tests passing** (up from 192 at the end of AUTH-003), `ruff check`/`ruff format --check`
  both clean.

### Mobile

No mobile changes this story (see Scope Assessment above).

---

## Acceptance Criteria — Verification

All 9 acceptance criteria (from `Plan_S02_AUTH-004.md`, sourced from the Tracker) were independently verified
by the `tester` agent — re-running the full suite twice from a clean shell, reading actual test bodies (not
summaries) for the highest-scrutiny items (401-vs-403, the ownership helper, audit immutability/no-secrets,
one-row-per-event-type), independently re-deriving migration up/down/up/down reversibility against a fresh
scratch Postgres DB, and diffing every modified test file against the pre-story commit to confirm all changes
were purely additive. All 9 passed.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `require_role()` dependency exists, composable, checks the `roles` JWT claim | Pass |
| 2 | No/invalid/expired token → 401 | Pass |
| 3 | Valid token, disallowed role → 403 — never interchangeable with 401 | Pass |
| 4 | Ownership-check helper returns 404 (not 403) | Pass |
| 5 | `GET /auth/me` returns id/roles/status, protected by `require_role()` | Pass |
| 6 | Auth endpoints rate-limited at 10/min via Redis, keyed appropriately | Pass (pre-existing, re-confirmed) |
| 7 | Rate-limit rejection returns a generic, non-revealing message | Pass (pre-existing, re-confirmed) |
| 8 | `audit_logs` table exists (immutable), records registration/login/logout/session_revocation, no secrets | Pass |
| 9 | Automated tests cover 401-vs-403, rate-limit trigger/reset, one audit row per event type | Pass |

---

## Architect Review — Findings and Resolution

The `architect` agent returned **STORY COMPLETE** — no must-fix items, no security defect, no
architectural-boundary violation, no scope creep. Full findings in the (now-deleted)
`Checkpoint_S02_AUTH-004.md`; summary of the review:

1. **`audit` module boundary** — confirmed correct: `identity`'s services import `audit`'s service
   (`AuditService`/`get_audit_service`), never its repository, in both production wiring and constructors —
   satisfying `02_ARCHITECTURE.md`'s "modules communicate through services only" rule. Verified by grepping
   the entire `app/` tree for every reference to the table/model.
2. **`audit_logs` immutability and migration spec** — confirmed structural (no update/delete method exists on
   the repository at all, not just by convention) and confirmed the migration matches `04_DATABASE.md`'s spec
   column-for-column, including all three documented indexes. Reversibility was independently verified twice
   (by `backend` and `tester`, against separate scratch DBs); `architect` did not re-run a third time, judging
   the migration file's straightforward `create_table`/`drop_table` shape and two independent real-DB runs
   sufficient.
3. **401/403/404 semantics** — confirmed structurally guaranteed, not just test-covered by convention:
   `RequireRole` has no code path that raises anything other than `InsufficientRoleError`, and
   `ensure_owner_or_not_found` has no 403 branch at all. Enumerated every endpoint in the codebase (only
   `identity/api.py` exists) to confirm no path leaks a 200 or an information-disclosing error to an
   unauthenticated or wrong-role caller.
4. **Logout vs. session_revocation** — confirmed the branch is a plain, readable conditional that fails safe:
   if a caller doesn't supply `current_session_id`, the branch always falls to the more conservative
   `session_revocation` label, never silently mislabeling an unknown case as `logout`.
5. **Registration vs. login audit correctness** — confirmed the single-boolean `is_new_user` pattern cannot
   double-fire within one call. Flagged a related, pre-existing concurrency gap as a nice-to-have (see
   Follow-up Notes below).
6. **`GET /auth/me` response shape** — confirmed no cross-user exposure is possible (id resolved from the
   validated token only, never a path parameter). Flagged a naming/wording nice-to-have (see Follow-up Notes).
7. **Rate limiting** — confirmed untouched via `git diff` producing no output on `rate_limit.py`; re-ran both
   rate-limit test suites as part of the full pass.
8. **Migration/test-DB architecture** — confirmed the test suite's pattern of creating/dropping schemas
   directly via `Base.metadata.create_all`/`drop_all` (bypassing Alembic entirely) is a sound, pre-existing
   trade-off inherited from Sprint 1's fixtures, now also extended to the `audit` schema. Flagged as
   undocumented (see Follow-up Notes).

### Standard review confirmed clean

Module boundaries/Clean Architecture (no cross-module repository access, no business logic in routes),
database (`AuditLog` matches `04_DATABASE.md` column-by-column, correctly exempt from `CommonColumnsMixin`),
no hardcoded secrets/colors/strings, no unapproved dependency additions, and security review (no PII/tokens in
audit rows, 401/403/404 never conflated, ownership checks are genuine).

---

## Follow-up Notes (non-blocking, tracked for future work)

1. **No `IntegrityError` handling on the concurrent-registration race.** `AuthService`'s find-or-create logic
   (both `verify_otp_and_authenticate` and `authenticate_with_oauth`) has no application-level lock or
   `SELECT ... FOR UPDATE`, and neither `UserRepository` nor `AuthService` catches `IntegrityError` anywhere.
   Two genuinely concurrent requests for the same not-yet-registered phone number or OAuth subject would both
   observe "no existing user," both attempt an INSERT, and the loser would hit a unique-constraint violation
   as an unhandled `IntegrityError` — surfacing as a bare 500, not a graceful login. This is a pre-existing
   race inherited from AUTH-001/AUTH-002's find-or-create logic, not introduced by this story, and does not
   corrupt audit-log correctness (the failure mode is a dropped request, never a double or mis-fired audit
   row). Worth its own small follow-up story (e.g. catch `IntegrityError` on the insert, re-fetch, continue as
   a login).
2. **`GET /auth/me` returns slightly more than AC5's literal wording.** The endpoint reuses
   `UserSummaryResponse`, which also carries `phone_country_code`/`phone_number`/`preferred_language` in
   addition to `id`/`roles`/`status`. This is not a new PII exposure (it's the authenticated caller's own
   phone number, already returned by every login/OTP-verify response today) and is a deliberate,
   well-reasoned trade-off (avoiding a duplicate near-identical schema per `08_CODING_STANDARDS.md`). Worth a
   one-line confirmation from product/tech-lead that "at least id/roles/status" (not "exactly") was the AC's
   intent, but not treated as a defect.
3. **The test suite's Alembic-bypass pattern was undocumented — now recorded.** `backend/tests/conftest.py`'s
   `db_engine` fixture creates/drops the `identity`/`audit` schemas directly via `Base.metadata.create_all`/
   `drop_all`, never invoking Alembic — a pattern that predates this story (already existed for `identity`;
   this story only extended it, in kind, to also cover `audit`). Both `tester` and `architect` independently
   confirmed this is the *correct* approach (running Alembic directly against the shared `ai_marketplace_test`
   DB would actively desync it, since the suite's own teardown drops schemas regardless of `alembic_version`'s
   state) but flagged that it lived only in a fixture's docstring, with no ADR and no note in
   `04_DATABASE.md`'s Migration Strategy section. Judged durable enough to record: added as **ADR-013** in
   `docs/AI/09_DECISIONS.md` at story closure, so future engineers/agents extending the fixture to a new
   domain module don't have to rediscover this reasoning from scratch.
4. **`mypy` still not installed.** Configured in `pyproject.toml`'s `[tool.mypy]` but not present in
   `[dependency-groups].dev` and not runnable (`uv run mypy app` fails to spawn). Pre-existing gap, carried
   forward from AUTH-003's walkthrough, still not fixed — dead config, worth fixing opportunistically whenever
   `backend` next touches dependency management.

---

## Testing Performed

- `cd backend && uv run pytest -v` — **211/211 passing**, 0 regressions on AUTH-001/002/003 (re-run
  independently by `backend`, `tester` twice, and `architect`, all from clean shells, all consistent).
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic downgrade base`
  — verified independently by both `backend` and `tester` against separate scratch Postgres DBs (not the
  shared dev/test DBs, which were confirmed left in the same clean state afterward). Reversible, no manual
  SQL intervention needed.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- `cd backend && uv run pytest tests/core/test_rate_limit.py -v` and the `TestRateLimiting` class in
  `test_auth_endpoints.py` — re-run independently by `backend`, `tester`, and `architect`; 15/15 pass each
  time, confirming AC6/AC7 untouched.
- Diff review: every modified test file diffed against the pre-story commit, confirmed 100% additive (no
  deleted or weakened assertion).
- `tester` agent: all 9 ACs independently verified with direct evidence — see table above.
- `architect` agent: STORY COMPLETE — see findings above.

---

## Key Files

### Backend
- `backend/app/core/authorization.py` (new) — `ensure_owner_or_not_found`
- `backend/app/api/dependencies.py` — `RequireRole`/`require_role()`
- `backend/app/core/exceptions/{exceptions.py,__init__.py}` — `InsufficientRoleError`
- `backend/app/modules/audit/{models.py,dependencies.py}` (new)
- `backend/app/modules/audit/repositories/audit_log_repository.py` (new)
- `backend/app/modules/audit/services/audit_service.py` (new)
- `backend/alembic/versions/2026_09_06_0900-d81be77c601d_audit_domain.py` (new)
- `backend/alembic/env.py` — registers `app.modules.audit.models` for autogenerate/DDL
- `backend/app/modules/identity/services/auth_service.py` — injected `AuditService`; `get_current_user_summary`
- `backend/app/modules/identity/services/session_service.py` — injected `AuditService`; `current_session_id`/
  `ip_address` params; `ensure_owner_or_not_found` refactor
- `backend/app/modules/identity/api.py` — `GET /me`; `ip_address` capture on session-revocation endpoints
- `backend/app/modules/identity/dependencies.py` — wired `AuditService` into `get_session_service()`/
  `get_auth_service()`
- `backend/tests/modules/audit/test_audit_service.py` (new)
- `backend/tests/api/test_dependencies.py` — `TestRequireRole` (new)
- `backend/tests/modules/identity/test_auth_service.py` — audit-call assertions
- `backend/tests/modules/identity/test_session_service.py` — `TestRevokeSessionAuditLogging` (new)
- `backend/tests/modules/identity/test_auth_endpoints.py` — `TestGetMe` (new)
- `backend/tests/conftest.py` — `audit` schema creation/drop, `AuditLog` truncation

---

## Follow-up Notes for Sprint Planning

- Sprint 2 (Identity & Access) is now **complete** — AUTH-001, AUTH-002, AUTH-003, and AUTH-004 all done.
- The four non-blocking follow-up items above (concurrent-registration race, `GET /auth/me` response-shape
  wording, undocumented Alembic-bypass test-DB pattern, `mypy` not installed) are recorded here for future
  pickup; none block this story's closure.
- The next sprint's stories need to be identified from `docs/AI/Project_Tracker.xlsx` before planning can
  continue — see `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` Section 17.
