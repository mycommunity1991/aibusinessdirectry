**Active Story:** Sprint 2 | AUTH-004 | Access the App According to My Role

**Story:**
As a customer, provider, or administrator, I want the app and API to enforce what I'm allowed to do based on my role, so that my account and the platform's other users are protected from unauthorized actions.

This story adds the reusable authorization layer every later feature story depends on: a role-check dependency, correct 401-vs-403 semantics, an ownership-check helper, an audit trail for security-sensitive identity events, and (already largely in place) rate limiting on the authentication endpoints. It is the last story in Sprint 2 and a hard dependency for every subsequent feature sprint's protected endpoints.

**Scope boundary:** proves the mechanism end-to-end against one representative endpoint (`GET /auth/me`); does NOT retroactively add authorization checks to endpoints that don't exist yet — those are each later story's own responsibility.

---

## Technical Context & Architecture Constraints

- **Rate limiting (AC6/AC7) is already fully implemented — do not re-implement it.** All five auth endpoints (`request-otp`, `verify-otp`, `google`, `apple`, `refresh`) already carry a `RateLimitDependency` at 10/min via Redis, phone- or IP-keyed as appropriate, returning a generic 429 message that never confirms/denies account existence. Triggering and window-reset already have passing tests (`tests/core/test_rate_limit.py`, `TestRateLimiting` in `tests/modules/identity/test_auth_endpoints.py`). Re-confirm this wiring at implementation time; do not duplicate or modify it.
- `get_current_user` (`backend/app/api/dependencies.py`) already exists and already handles AC2 (401 for missing/invalid/expired token) — build `require_role()` on top of it as a second, composable dependency, not a replacement.
- `require_role(*allowed_roles: str)` is a parametrized dependency: `Depends(require_role(ROLE_ADMIN))` etc. It depends on `get_current_user` internally, so a bad/missing token 401s before the role check ever runs; `require_role()` itself only ever raises the new `InsufficientRoleError` (403) when a validly authenticated caller's `roles` claim doesn't intersect the allowed set. This structurally guarantees AC2/AC3 never collide.
- The ownership-check helper (AC4) is a plain function, `ensure_owner_or_not_found(owner_id, requester_id, *, not_found_exc)`, in a new `backend/app/core/authorization.py` — it takes the specific 404 exception to raise as a parameter rather than introducing a new generic 404 class, so each call site keeps its own precise message. Refactor `SessionService.revoke_session`'s existing inline ownership check (`if session is None or session.user_id != user_id: raise SessionNotFoundError()`) to use it — zero behavior change, demonstrates real reuse.
- `audit_logs` (AC8) is a brand-new table — `04_DATABASE.md`'s Audit Domain section already fully specifies its columns/indexes; implement exactly that spec via a new Alembic migration, no schema-design decision needed. Build it as a new, self-contained `backend/app/modules/audit/` module (model, repository with only a `create()` method — no update/delete, enforcing immutability at the code level — service, dependencies) that `identity`'s services depend on via its **service** class, never its repository directly, per the "modules communicate through services only" rule.
- Audit-event mapping — 4 tracked event types onto 4 existing code paths, decided during planning (see `Plan_S02_AUTH-004.md` Decision 5): `registration` + `login` from `AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth` (registration only when the user is new; login always); `logout` from `SessionService.revoke_session` when the session being revoked is the caller's own current session; `session_revocation` from `revoke_session` when it's a *different* session, and unconditionally from `revoke_all_sessions`. This requires threading the caller's current session id into `revoke_session`'s signature (internal-only change, no HTTP contract change) and capturing `ip_address` in the two session-revocation endpoints via the existing `_client_context()` helper. Never put a phone number, email, raw token, or token hash into `before_state`/`after_state` — only non-PII metadata (e.g. `{"auth_provider": ...}`, `{"scope": "all_sessions"}`); `entity_type`/`entity_id` already give full traceability without duplicating PII.
- `GET /auth/me` reuses the existing `UserSummaryResponse` schema (already has id/roles/status plus a few extra fields already returned by every other auth endpoint) — no new response model. Protect it with `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` — i.e., any of the platform's three real roles, since every registered account holds at least one. This makes both the 200 and 401 paths directly testable via ordinary calls; test the 403 path by minting a token directly via the existing `create_access_token()` helper with `roles=[]` (a real, validly-signed JWT with no allowed role) — no test-only endpoint needed.
- Do **not** change the authorization dependency on the already-shipped `GET/DELETE/POST /auth/sessions*` endpoints — swapping in `require_role()` there would be functionally identical to today's plain `get_current_user` (every user holds at least one role) and isn't required by any AC.
- No mobile work is required for this story — every AC describes backend/API-side enforcement, and there is no screen yet that consumes `GET /auth/me` (S-14 "Profile & Settings," the natural future consumer, doesn't exist yet). This is a deliberate, confirmed scope conclusion, not an oversight.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S02_AUTH-004.md` — follow it, including its Architecture Decisions and Verified Current State sections.

---

## Implementation Instructions

### Backend
1. Add a new Alembic migration creating the `audit` schema and `audit.audit_logs` table exactly per `04_DATABASE.md`'s Audit Domain spec (columns, indexes, no `updated_at`/`deleted_at`/`is_active`/`version`). Verify upgrade/downgrade both work against a real local Postgres.
2. Add `InsufficientRoleError` (403, generic message) to `backend/app/core/exceptions/exceptions.py`/`__init__.py`.
3. Add `backend/app/core/authorization.py`: `ensure_owner_or_not_found(owner_id, requester_id, *, not_found_exc)`.
4. Add `RequireRole`/`require_role()` to `backend/app/api/dependencies.py`, alongside the existing `CurrentUser`/`get_current_user`.
5. Add `backend/app/modules/audit/`: `models.py` (`AuditLog`, plain `Base`, immutable), `repositories/audit_log_repository.py` (`create()` only), `services/audit_service.py` (`record_registration`/`record_login`/`record_logout`/`record_session_revocation`), `dependencies.py`.
6. In `backend/app/modules/identity/services/auth_service.py`: inject `AuditService`; call `record_registration` (new users only) + `record_login` (always) from both `verify_otp_and_authenticate` and `authenticate_with_oauth`. Add `get_current_user_summary(user_id) -> tuple[User, list[str]]`.
7. In `backend/app/modules/identity/services/session_service.py`: inject `AuditService`; extend `revoke_session`'s signature to accept the caller's current session id; call `record_logout` or `record_session_revocation` depending on whether the revoked session is the caller's own current one; call `record_session_revocation` unconditionally from `revoke_all_sessions`; refactor the ownership check to use `ensure_owner_or_not_found`.
8. In `backend/app/modules/identity/api.py`: add `GET /me` protected by `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)`, returning `SuccessResponse[UserSummaryResponse]`. Extend `revoke_session`/`logout_all_sessions` to capture `ip_address`/pass `current_user.session_id` through to `SessionService`.
9. Wire the new `AuditService` into `get_auth_service()`/`get_session_service()` in `backend/app/modules/identity/dependencies.py`.
10. Update `backend/tests/conftest.py`: create/drop the `audit` schema alongside `identity`'s in `db_engine`, import `AuditLog`, add it to `db_session`'s truncate list.
11. Write tests: new audit-module tests (row creation, correct fields, no update/delete method exists); a `require_role()` unit test (pass-through for allowed role, 403 for disallowed); extend `test_auth_service.py` (exactly one `registration`+`login` row for a new user, one `login` row for a returning user); extend `test_session_service.py` (`logout` vs `session_revocation` mapping); extend `test_auth_endpoints.py` with a new `TestGetMe` class covering the full 401 (no token / garbage token / expired token) / 403 (roleless token) / 200 matrix.
12. Re-run (don't just read) the existing rate-limit tests to confirm AC6/AC7 remain green, unmodified.

### Both
13. Confirm `pytest` (backend) passes in full, plus `ruff check`/`ruff format --check`. No mobile changes expected this story — if `frontend` finds itself needing to touch `mobile/`, stop and flag it, since the Plan's Mobile Scope Assessment concluded no mobile work is needed.
14. Do not implement anything in the Plan's "Explicitly Out of Scope" section (UI consuming `/auth/me`, retroactive `require_role()` on `/auth/sessions*`, a permission-catalog/ABAC layer, admin-initiated audit events, an admin audit-log-viewing endpoint, any rate-limit value/key/message change).

---

## Definition of Done

- All 9 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (AUTH-004 row) are met, verified by `tester` against each one individually.
- `require_role()` exists, is composable with any endpoint, and structurally cannot produce a 403 for a bad/missing/expired token (that's always `get_current_user`'s 401) nor a 401 for a valid-but-disallowed-role token (AC2/AC3).
- `ensure_owner_or_not_found` exists and is demonstrated in real use via `SessionService.revoke_session`'s refactor, with no observable behavior change to that endpoint.
- `GET /auth/me` returns id/roles/status for a valid token, 401 for no/invalid/expired token, 403 for a valid-but-roleless token.
- `audit.audit_logs` exists via a reversible migration, immutable (no soft-delete/version columns), and receives exactly one correctly-typed row for each of registration, login, logout, and session-revocation — with no phone number, email, raw token, or token hash in `before_state`/`after_state`.
- AC6/AC7's existing rate-limiting remains intact and covered by its existing tests — not modified, not duplicated.
- Backend automated test suite passes in full (zero regressions on AUTH-001/002/003's 192 existing tests); lint/format clean.
- No functionality from a permission-catalog/ABAC layer, admin-initiated audit events, an admin audit-log-viewing endpoint, or any mobile UI is introduced, even incidentally.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written or the changelog/tracker is touched.
