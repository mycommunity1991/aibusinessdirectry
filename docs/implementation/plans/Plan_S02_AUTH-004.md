# Plan for Story AUTH-004 — Access the App According to My Role

**Sprint:** 02 | **Story ID:** AUTH-004 | **Priority:** High | **Depends On:** AUTH-003 (Done)

---

## Supersession Notice

This plan **replaces** the previous version of `Plan_S02_AUTH-004.md`, which scoped AUTH-004 as "Google & Apple OAuth Registration & Login" — a layered slice of an old, superseded 9-story Sprint 2 backlog. That backlog no longer exists; its OAuth slice shipped under the current tracker's **AUTH-002** instead (see `Plan_S02_AUTH-002.md`/`Walkthrough_S02_AUTH-002.md`).

The current `docs/AI/Project_Tracker.xlsx` (source of truth) defines a 4-story Sprint 2 — AUTH-001 through AUTH-004 — each a full vertical slice. Under that tracker, **AUTH-004 is "Access the app according to my role"**: the reusable authorization layer (role checks, 401-vs-403 semantics, an ownership-check helper, audit logging, and auth-endpoint rate limiting) that every later feature story's protected endpoints will depend on. It is the last story in Sprint 2 ("Secure Account Access") and depends on the `roles` claim AUTH-003's access tokens already carry. This plan is written against that current, authoritative scope (9 acceptance criteria, reproduced verbatim below) and against the **actual shipped code** from AUTH-001/002/003 (verified by reading it directly — see Verified Current State).

---

## Story

As a customer, provider, or administrator, I want the app and API to enforce what I'm allowed to do based on my role, so that my account and the platform's other users are protected from unauthorized actions.

**Scope boundary:** this story proves the mechanism end-to-end against one representative endpoint (`GET /auth/me`); it does not retroactively add authorization checks to endpoints that don't exist yet — each later story adds its own.

---

## Acceptance Criteria (authoritative — from the Tracker)

1. A `require_role()` dependency exists and can be applied to any endpoint, checking the `roles` claim from the validated JWT.
2. A request with no token, an invalid token, or an expired token receives 401 Unauthorized.
3. A request with a valid token but a disallowed role receives 403 Forbidden — 401 and 403 are never used interchangeably.
4. An ownership-check helper exists returning 404 (not 403) when revealing a resource's existence would itself be a leak.
5. `GET /auth/me` returns the caller's own id, roles, and account status, and is protected by `require_role()`.
6. Auth endpoints (OTP request/verify, OAuth login, refresh) are rate-limited via Redis at 10 requests/minute per the security standard, keyed appropriately (phone number, IP, or user id).
7. Rate-limit rejections return a generic "too many attempts, try again later" message that never confirms or denies whether an account exists.
8. `audit_logs` table exists (immutable — no soft-delete or version columns) and receives a record for registration, login, logout, and session revocation events, with no secrets or tokens in before/after_state.
9. Automated tests cover: 401 vs 403 distinction, rate-limit triggering and reset, and an audit-log row being created for each of the four tracked event types.

These are the acceptance criteria the tester will test against — no additions, no omissions.

---

## Verified Current State (read directly from code, not assumed)

- **AC6/AC7 are already fully implemented — no new rate-limiting code is needed.** `backend/app/modules/identity/api.py` already wires a `RateLimitDependency` (from `backend/app/core/rate_limit.py`, a Redis `INCR`+`EXPIRE` fixed-window limiter, added as an AUTH-001 follow-up) onto **all five** auth endpoints at `AUTH_RATE_LIMIT_PER_MINUTE=10` / `AUTH_RATE_LIMIT_WINDOW_SECONDS=60`: `_request_otp_rate_limiter` (phone-keyed), `_verify_otp_rate_limiter` (IP-keyed), `_google_sign_in_rate_limiter` (IP-keyed), `_apple_sign_in_rate_limiter` (IP-keyed), `_refresh_rate_limiter` (IP-keyed). `RateLimitExceededError` already returns 429 with the generic message "Too many requests. Please wait a moment and try again." — never revealing account existence. Triggering, per-key scoping, and window-reset are already covered by `backend/tests/core/test_rate_limit.py::test_counter_resets_after_the_window_expires` and `TestRateLimiting` in `backend/tests/modules/identity/test_auth_endpoints.py`. `backend` should re-confirm this wiring still holds at implementation time (docs/code can drift) but must not re-implement or duplicate this mechanism — there is no remaining AC6/AC7 gap to close.
- **`get_current_user`** (`backend/app/api/dependencies.py`) is a real implementation (AUTH-003): decodes/validates the JWT, returns `CurrentUser(id, session_id, roles)`, raising `InvalidTokenError`/`ExpiredTokenError`/`AuthenticationRequiredError` (all 401) for a missing/malformed/expired token. AC2 (the 401 side) is therefore already fully covered by existing behavior — this story builds `require_role()` on top of it rather than replacing it.
- **No `require_role()`, no ownership-check helper, no `GET /auth/me`, and no `audit_logs` table/model/writes exist anywhere in the codebase yet.** Confirmed by reading `backend/app/api/dependencies.py`, `backend/app/core/exceptions/exceptions.py`, `backend/app/modules/identity/api.py`, and `backend/app/modules/`'s full module list — there is no `audit` module. This matches the explicit gap both AUTH-002's and AUTH-003's architect reviews flagged as "worth its own future story" — this is that story.
- **`04_DATABASE.md`'s `audit.audit_logs` schema is already fully specified** (column-by-column, with indexes) — no `docs/AI/` schema-design follow-up is needed, unlike AUTH-002's `users` constraint change. This plan implements exactly that spec.
- **Roles already exist and are seeded**: `identity.roles` has `customer`/`provider`/`admin` (`app/modules/identity/services/seed_data.py`, `app/core/constants.py`'s `ROLE_CUSTOMER`/`ROLE_PROVIDER`/`ROLE_ADMIN`). Every registered account is assigned `customer` at creation (AUTH-001/002) — there is currently no code path that creates a `User` with zero roles, which matters for how AC3's 403 case is tested (see Decision 6).
- **`SessionService.revoke_session`** (`backend/app/modules/identity/services/session_service.py`) already implements the exact "ownership check → 404, not 403" pattern AC4 asks for, but inline and ad hoc (`if session is None or session.user_id != user_id: raise SessionNotFoundError()`) rather than as a reusable helper. This story extracts that pattern into a shared, generic helper (Decision 3) and refactors this call site to use it — zero behavior change, but now reusable by future stories (Provider, Verification, etc.) that need the same non-revealing-404 pattern.
- **`revoke_session`'s current signature** (`user_id`, `session_id`) does not receive the caller's *current* session id, so it cannot today distinguish "the caller is ending their own current session" (logout) from "the caller is ending a different session" (revocation) — needed for AC8's audit-action mapping (Decision 5). This is a small, internal, non-breaking signature change (no HTTP contract change).
- **Mobile**: no screen or flow in `14_USER_FLOWS.md`/`15_SCREEN_INVENTORY.md` currently consumes a "my profile" endpoint — the closest is S-14 "Profile & Settings," not yet built (flagged as a future story in `Walkthrough_S02_AUTH-003.md`). This story is backend/API-side enforcement infrastructure with no corresponding UI surface yet — see Mobile Scope Assessment below.

---

## Architecture Decisions

1. **`require_role()` as a parametrized, composable FastAPI dependency, layered on top of `get_current_user` — not a replacement for it.** Added to `backend/app/api/dependencies.py` alongside `CurrentUser`/`get_current_user`:
   ```python
   class RequireRole:
       def __init__(self, *allowed_roles: str) -> None:
           self.allowed_roles = frozenset(allowed_roles)

       def __call__(
           self, current_user: CurrentUser = Depends(get_current_user)
       ) -> CurrentUser:
           if not self.allowed_roles.intersection(current_user.roles):
               raise InsufficientRoleError()
           return current_user


   def require_role(*allowed_roles: str) -> RequireRole:
       return RequireRole(*allowed_roles)
   ```
   Because `require_role(...)` depends on `get_current_user`, a missing/invalid/expired token never reaches the role check at all — it 401s first, inside `get_current_user`, exactly satisfying AC2/AC3's "401 and 403 are never used interchangeably." `require_role()` itself only ever raises the new `InsufficientRoleError` (403), for the one remaining case: a **validly authenticated** caller whose `roles` claim doesn't intersect the endpoint's allowed set. Usable on any endpoint via `Depends(require_role(ROLE_ADMIN))` etc. (AC1).

2. **New exception: `InsufficientRoleError` (403).** Added to `backend/app/core/exceptions/exceptions.py`/`__init__.py`, generic message ("You don't have permission to perform this action."), mirroring the project's existing non-revealing-error style (no detail on which role was required).

3. **Ownership-check helper as a plain function, not a new exception class.** Added at `backend/app/core/authorization.py`:
   ```python
   def ensure_owner_or_not_found(
       owner_id: uuid.UUID | None,
       requester_id: uuid.UUID,
       *,
       not_found_exc: BusinessException,
   ) -> None:
       if owner_id != requester_id:
           raise not_found_exc
   ```
   Takes the specific 404 exception to raise as a parameter (e.g. the already-existing `SessionNotFoundError`) rather than introducing a new generic 404 exception type — every call site keeps its own precise, resource-specific 404 message, while sharing one reviewed, correct ownership-comparison implementation (AC4). `owner_id=None` (resource doesn't exist at all) is treated identically to "exists but not owned" — both collapse into the same 404, consistent with the existing `SessionNotFoundError` precedent and the project's established non-revealing-error philosophy (Decision 9, `Plan_S02_AUTH-003.md`). `SessionService.revoke_session` is refactored to call this helper instead of its inline check — a zero-observable-behavior-change refactor that demonstrates the helper in real use, not just in isolation.

4. **New `audit` module (`backend/app/modules/audit/`), mirroring the existing per-schema module pattern.** `04_DATABASE.md`'s Schema Organization lists `audit` as its own schema, distinct from `identity` and `administration` — and audit logging is a genuinely cross-cutting concern (already needed by `identity` today; will be needed by `verification`/`administration`/`review` in later sprints). Consistent with "Modules communicate through services only" (`02_ARCHITECTURE.md`), `identity`'s services depend on the new module's **service**, never its repository directly:
   - `backend/app/modules/audit/models.py` — `AuditLog` (plain `Base`, **not** `CommonColumnsMixin` — immutable, no `updated_at`/`deleted_at`/`is_active`/`version`, matching `04_DATABASE.md`'s explicit note that `audit_logs` is exempt from the Common Columns convention).
   - `backend/app/modules/audit/repositories/audit_log_repository.py` — `AuditLogRepository(db)`, exposing only `create(...)`. No update/delete method is ever defined — immutability is enforced by the class's shape, not just by convention.
   - `backend/app/modules/audit/services/audit_service.py` — `AuditService(repository)`, exposing four explicit, self-documenting methods rather than one generic `record(action: str, ...)`: `record_registration`, `record_login`, `record_logout`, `record_session_revocation`. Explicit methods make each call site's intent unambiguous and remove any risk of a typo'd `action` string.
   - `backend/app/modules/audit/dependencies.py` — `get_audit_log_repository(db)`, `get_audit_service(...)`, following the exact DI style already used in `identity/dependencies.py`.
   - No `api.py`/`schemas.py` — nothing in this module is exposed over HTTP in this story (no admin log-viewing endpoint exists yet; that's future scope).

5. **Audit-event mapping: 4 tracked event types onto 4 existing code paths, with no PII duplicated into `before_state`/`after_state`.**
   - **`registration`** — `AuthService.verify_otp_and_authenticate` / `authenticate_with_oauth`, only when `is_new_user` is `True`. `entity_type="user"`, `entity_id=user.id`, `after_state={"auth_provider": <value>}`.
   - **`login`** — the same two `AuthService` methods, on *every* call (new or existing user). `entity_type="user"`, `entity_id=user.id`, `after_state={"auth_provider": <value>}`.
   - **`logout`** — `SessionService.revoke_session`, when the session being revoked **is** the caller's own current session (`session_id == current_session_id`, the ordinary "log out of this device" action). `entity_type="session"`, `entity_id=session.id`.
   - **`session_revocation`** — `SessionService.revoke_session`, when the session being revoked is **not** the caller's current session (ending a *different* device's session — the more security-relevant case); and `SessionService.revoke_all_sessions` unconditionally (bulk "log out everywhere," `entity_type="session"`, `entity_id=None` since it's not a single entity, `after_state={"scope": "all_sessions", "kept_current": <bool>}`).

   This requires threading the caller's `current_session_id` into `revoke_session` (see Verified Current State) and passing `ip_address` (via the existing `_client_context()` helper, already used elsewhere in `api.py`) into both session-revocation endpoints, which don't currently capture it. `actor_user_id` is always the acting user's own id — there is no admin-initiated revocation path yet (that's a future story). No `before_state`/`after_state` value ever contains a phone number, email, raw token, or token hash — deliberately more conservative than AC8's literal "no secrets or tokens" floor, consistent with `06_SECURITY.md`'s broader "sensitive data must never appear in logs" principle. `entity_id` (already pointing at the `user`/`session` row) provides full traceability without repeating PII in the JSON blob.

6. **Testing the 401/403 distinction (AC2/AC3/AC9) entirely through real, non-contrived scenarios against `GET /auth/me` — no test-only endpoint is added.** `GET /auth/me` is protected by `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` — i.e. any of the platform's three real roles, since every legitimately authenticated account already holds at least one. This makes the "allowed role" (200) and "no/invalid/expired token" (401) cases directly testable via ordinary authenticated calls. For the 403 case, tests mint an access token **directly via the existing `create_access_token()` helper** (already used this way in `test_security.py`) with `roles=[]` (or an unrecognized role name) — a real, validly-signed JWT that simply carries no allowed role, exactly the scenario AC3 describes, with no production code changes needed to produce it. `require_role()`'s pass-through/403 branches are additionally covered by a direct unit test (constructing a `CurrentUser` and calling the dependency directly), mirroring how `RateLimitDependency`/`_check_fixed_window` are already unit-tested in isolation in `tests/core/test_rate_limit.py`, separately from their endpoint-level integration coverage.

7. **`GET /auth/me` reuses the existing `UserSummaryResponse` schema — no new response model.** AC5 asks for "id, roles, and account status"; `UserSummaryResponse` already carries `id`/`roles`/`status` (plus `phone_country_code`/`phone_number`/`preferred_language`, already returned by every other auth endpoint) — reusing it avoids a duplicate, near-identical schema (`08_CODING_STANDARDS.md`: never duplicate models). A small `AuthService.get_current_user_summary(user_id) -> tuple[User, list[str]]` method (mirroring the exact `(User, roles)` shape `verify_otp_and_authenticate`/`authenticate_with_oauth` already return) backs the endpoint, keeping business logic out of the route per `02_ARCHITECTURE.md`.

8. **No change to the already-shipped `GET /auth/sessions` / `DELETE /auth/sessions/{id}` / `POST /auth/sessions/logout-all` endpoints' authorization dependency.** These already use plain `get_current_user`; swapping in `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` would be functionally identical (every user holds at least one of those three roles) and isn't required by any of the 9 ACs. Left untouched — considered and explicitly rejected here to preempt the question during architect review.

---

## Mobile Scope Assessment

**No mobile work is required for this story.** All 9 acceptance criteria describe backend/API-side enforcement (a dependency, an exception-status distinction, a helper function, one backend endpoint, rate limiting that already exists, and an audit table). There is no tracker AC describing a UI surface, and no screen in `15_SCREEN_INVENTORY.md` currently needs to call `GET /auth/me` — the natural future consumer (S-14 "Profile & Settings") doesn't exist yet and is tracked as a follow-up from AUTH-003's walkthrough. This is a deliberate scope conclusion, not an oversight: the story explicitly scopes itself to proving the mechanism against one representative endpoint, and every later feature story that builds a role-gated mobile screen will wire its own `require_role()`-protected endpoint and its own mobile consumption of it at that time.

---

## Backend — Proposed Changes

### Migration
#### [NEW] `backend/alembic/versions/<rev>_audit_domain.py`
Creates the `audit` Postgres schema and `audit.audit_logs` table exactly per `04_DATABASE.md`'s Audit Domain spec: `id` (UUID PK), `actor_user_id` (UUID, nullable, FK → `identity.users.id`), `action` (VARCHAR(100)), `entity_type` (VARCHAR(50)), `entity_id` (UUID, nullable), `before_state`/`after_state` (JSONB, nullable), `ip_address` (INET, nullable), `created_at` (TIMESTAMPTZ, default `now()`). Indexes: `idx_audit_logs_actor_user_id`, `idx_audit_logs_entity_type_entity_id` (composite), `idx_audit_logs_created_at`. No `updated_at`/`deleted_at`/`is_active`/`version` columns (AC8 — immutable). Verify upgrade/downgrade both work.

### Exceptions
#### [MODIFY] `backend/app/core/exceptions/exceptions.py` / `__init__.py`
Add `InsufficientRoleError` (403) — Decision 2.

### Authorization helpers
#### [NEW] `backend/app/core/authorization.py`
`ensure_owner_or_not_found(...)` — Decision 3.
#### [MODIFY] `backend/app/api/dependencies.py`
Add `RequireRole`/`require_role()` — Decision 1.

### Audit module
#### [NEW] `backend/app/modules/audit/models.py`, `repositories/audit_log_repository.py`, `services/audit_service.py`, `dependencies.py` — Decision 4/5.

### Identity module integration
#### [MODIFY] `backend/app/modules/identity/services/auth_service.py`
Inject `AuditService`; call `record_registration`/`record_login` from `verify_otp_and_authenticate` and `authenticate_with_oauth` (Decision 5). Add `get_current_user_summary(user_id)` (Decision 7).
#### [MODIFY] `backend/app/modules/identity/services/session_service.py`
Inject `AuditService`; extend `revoke_session`'s signature to accept the caller's current session id (to distinguish logout vs. revocation, Decision 5); call `record_logout`/`record_session_revocation` from `revoke_session`/`revoke_all_sessions`. Refactor `revoke_session`'s ownership check to use `ensure_owner_or_not_found` (Decision 3).
#### [MODIFY] `backend/app/modules/identity/api.py`
Add `GET /me`, protected by `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` (Decision 6/7), returning `SuccessResponse[UserSummaryResponse]`. Extend `revoke_session`/`logout_all_sessions` endpoints to capture `ip_address` via the existing `_client_context()` helper and pass it (plus `current_user.session_id` for `revoke_session`) through to `SessionService`.
#### [MODIFY] `backend/app/modules/identity/dependencies.py`
Wire `AuditService` into `get_auth_service()`/`get_session_service()`'s dependency chains.

### Tests (AC9)
#### [NEW] `backend/tests/modules/audit/test_audit_service.py` (and/or `test_audit_log_repository.py`)
Row creation, exact column values per event type, no update/delete method exists.
#### [NEW] `backend/tests/test_authorization.py` (or alongside `tests/api/test_dependencies.py` if that's where AUTH-003's `get_current_user` tests already live)
`require_role()` unit tests: passes through for an allowed role, raises `InsufficientRoleError` (403) for a disallowed one — Decision 6.
#### [MODIFY] `backend/tests/modules/identity/test_auth_service.py`
Assert exactly one `registration` + one `login` audit row on new-user OTP/OAuth verification; exactly one `login` row (no `registration`) on returning-user verification.
#### [MODIFY] `backend/tests/modules/identity/test_session_service.py`
Assert a `logout` row when the caller revokes their own current session; a `session_revocation` row when revoking a different session, and when calling `revoke_all_sessions`.
#### [MODIFY] `backend/tests/modules/identity/test_auth_endpoints.py`
New `TestGetMe` class: 200 with correct id/roles/status for a properly authenticated caller; 401 for no `Authorization` header, a garbage token string, and an expired token (minted with a negative `expires_delta`); 403 for a validly-signed token with `roles=[]` (Decision 6) — the full AC2/AC3/AC9 401-vs-403 matrix against the one representative endpoint.
#### [MODIFY] `backend/tests/conftest.py`
Register the `audit` schema's creation/drop alongside `identity`'s in `db_engine`; import `AuditLog` so its table is created; add it to `db_session`'s post-test truncate list.

---

## Explicitly Out of Scope (do not implement in this story)

- Any UI surface consuming `GET /auth/me` or displaying role-gated content — no mobile work this story (see Mobile Scope Assessment).
- Retroactively applying `require_role()` to `GET/DELETE/POST /auth/sessions*` (Decision 8) or to any endpoint outside `identity` — every other module's endpoints don't exist yet; each future story wires its own.
- A permission catalog / `permissions`/`role_permissions` enforcement layer beyond the simple role-name check `require_role()` performs — `04_DATABASE.md` documents `permissions`/`role_permissions` as existing tables, but no AC in this story requires reading them; ABAC/permission-code-level checks are explicitly "Future support" per `06_SECURITY.md`.
- Any admin-initiated audit event (e.g. an admin suspending another user's account) — no such action exists in the codebase yet; only the four self-service event types the tracker lists.
- An admin-facing endpoint to read/list `audit_logs` — not required by any AC; a future admin story's concern.
- Any change to the OTP/OAuth/refresh rate-limit values, keys, or messages — AC6/AC7 are already fully implemented (Verified Current State) and are not touched, only confirmed.

---

## Delegation & Execution Sequence

1. **`backend`** (`backend/app/`, `backend/alembic/`, `backend/tests/`) — implement the full "Backend — Proposed Changes" section, in this order: migration (audit schema/table) → exceptions → `core/authorization.py` → `api/dependencies.py` (`require_role`) → new `audit` module (model → repository → service → dependencies) → identity integration (`auth_service.py`, `session_service.py`, `api.py`, `dependencies.py`) → tests. Focus ACs: 1, 2, 3, 4, 5, 8, 9. Re-confirm AC6/AC7's existing wiring is intact (no code change expected).
2. **`tester`** — verify all 9 acceptance criteria individually, with particular attention to: the 401-vs-403 matrix against `GET /auth/me` (AC2/AC3/AC9), that exactly one audit row of the correct type is created for each of the four tracked events with no PII/tokens in `before_state`/`after_state` (AC8/AC9), and that AC6/AC7 remain covered by the pre-existing rate-limit tests (re-run them, don't just trust the plan's claim that they already pass).
3. **`architect`** — review: `require_role()`/`ensure_owner_or_not_found` against `06_SECURITY.md`'s Authorization section and OWASP API Security guidance on information disclosure via error codes; the new `audit` module's boundary against `02_ARCHITECTURE.md`'s Communication Rules (identity → audit **service**, never its repository); the `audit_logs` migration against `04_DATABASE.md`'s exact spec (immutability, indexes); confirm no secret/token/PII leaks into `before_state`/`after_state`; confirm the Decision 8 non-change (leaving `/auth/sessions*` on plain `get_current_user`) is sound.
4. **Orchestrator** — once `tester` and `architect` both report clean, pause and present the diff + both verdicts to the user for explicit sign-off before writing the Walkthrough or touching the changelog/tracker.

No `frontend` delegation this story (see Mobile Scope Assessment) — the orchestrator will confirm this conclusion with the user before starting backend work, since it's a deviation from every prior Sprint 2 story's two-track (backend + mobile) delegation pattern.

---

## Verification Plan

- `cd backend && uv run pytest -v` — full suite, including new audit/authorization tests, must pass; zero regressions on AUTH-001/002/003 (192 tests currently passing).
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic downgrade base` — audit migration reversible, verified against a real local Postgres, matching the AUTH-003 precedent.
- `cd backend && uv run ruff check && uv run ruff format --check` — clean.
- Manual/API-level check: `GET /api/v1/auth/me` with a valid token returns 200 + id/roles/status; without a token, with a garbage token, and with an expired token all return 401; with a validly-signed but roleless token returns 403.
- Direct DB check: after a registration+login, a logout, and a logout-all, exactly the expected 4 distinct `audit.audit_logs` rows exist with the correct `action`/`entity_type`/`entity_id` values and no PII/secrets in `before_state`/`after_state`.
- Confirm (re-run, don't just read) `tests/core/test_rate_limit.py` and `TestRateLimiting` in `tests/modules/identity/test_auth_endpoints.py` still pass unmodified — AC6/AC7 regression check.

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md` — module boundaries, Communication Rules
- `docs/AI/04_DATABASE.md` — Audit Domain (`audit.audit_logs`) schema, already fully specified
- `docs/AI/05_API_GUIDELINES.md` — status codes, rate limiting
- `docs/AI/06_SECURITY.md` — Authorization, Audit Logging, Rate Limiting, Brute Force Protection sections
- `docs/AI/08_CODING_STANDARDS.md` — no duplicate models/services
- `docs/AI/09_DECISIONS.md` — ADR-009 (JWT), ADR-012 (unpaginated small collections, for context on `/auth/sessions`)
- `docs/implementation/plans/Plan_S02_AUTH-001.md` / `Plan_S02_AUTH-002.md` / `Plan_S02_AUTH-003.md` — prior stories this one builds on
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-003.md` — verified current-state source for this plan; flagged the audit-logging gap and the stale-plan status this document resolves
- `docs/implementation/prompts/Prompt_S02_AUTH-004.md`
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md` (to be created on completion)
