# Rule: Authorization & RBAC

## Role-Based Access Control (RBAC)
* **Explicit Roles:** Users operate under strict roles (e.g., `resident`, `community_admin`, `platform_admin`).
* **FastAPI Injection:** Enforce RBAC at the FastAPI router level using dependency injection (`Depends()`). For example, `Depends(require_role(Role.COMMUNITY_ADMIN))`.
* **Resource-Level Authorization:** Roles alone are not enough for multi-tenant data. Ensure the Application layer validates that the authenticated `user_id` actually belongs to the `community_id` they are attempting to modify.

## Error Handling
* **401 vs 403:** * Return `401 Unauthorized` ONLY when the user is not authenticated (missing, invalid, or expired JWT).
  * Return `403 Forbidden` when the user is fully authenticated but lacks the specific role or ownership to perform the action.
* **Obscuring Existence:** If a user requests a resource they are not authorized to see, return `404 Not Found` instead of `403 Forbidden` if revealing the existence of the resource is a security risk.