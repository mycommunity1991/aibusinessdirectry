# Plan for Story AUTH-007 - RBAC Authorization Foundation

Build the reusable role-check dependency every future module will use to protect its endpoints. This story is strictly limited to the authorization mechanism itself, proven against one representative endpoint — it does not protect every existing endpoint retroactively.

## Goal Description

Implement Role-Based Access Control enforcement at the API layer, per `authorization-rbac.md` (`security-and-auth` skill): explicit roles, FastAPI dependency injection, correct 401-vs-403 semantics, and a reusable resource-ownership check pattern for later modules (e.g. "does this Customer own this Saved Address").

## Architecture Decisions

- `require_role(*roles)` — a FastAPI dependency factory reading the validated JWT's `roles` claim (from AUTH-005) and raising `403` if the caller lacks an allowed role, `401` if the token itself is missing/invalid/expired. These are never conflated.
- Authorization is enforced at the Application/Service layer boundary that the API layer calls into — never left as a UI-only restriction, per `06_SECURITY.md`.
- A generic `assert_owns(resource_owner_id, current_user_id)` helper (raises `404`, not `403`, when revealing existence would itself be a leak) — documented for reuse, not re-implemented per module.
- Proven end-to-end against a minimal `GET /api/v1/auth/me` endpoint (returns the caller's own `User` + roles) — the first protected route in the system.

## Tasks

1. Implement `require_role(*roles)` dependency.
2. Implement the `assert_owns` ownership-check helper.
3. Add `GET /api/v1/auth/me`, protected, returning the authenticated user's id, roles, and status.
4. Integration tests: valid token + correct role → 200; valid token + wrong role → 403; missing/expired/invalid token → 401; ownership mismatch → 404 (not 403).
5. Document the pattern (docstring + a short section in `05_API_GUIDELINES.md` if not already covered) so later modules copy this, not reinvent it.
