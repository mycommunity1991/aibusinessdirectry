# Rule: Authorization & RBAC

## Role-Based Access Control (RBAC)
* **Explicit Roles:** Users operate under strict roles (e.g., `customer`, `provider`, `platform_admin`).
* **FastAPI Injection:** Enforce RBAC at the FastAPI router level using dependency injection (`Depends()`). For example, `Depends(require_role(Role.PLATFORM_ADMIN))`.
* **Resource-Level Authorization:** Roles alone are not enough for owner-scoped data. Ensure the Application layer validates that the authenticated `user_id` actually owns the `provider_id` (or `customer_id`) resource they are attempting to modify.

## Error Handling
* **401 vs 403:** * Return `401 Unauthorized` ONLY when the user is not authenticated (missing, invalid, or expired JWT).
  * Return `403 Forbidden` when the user is fully authenticated but lacks the specific role or ownership to perform the action.
* **Obscuring Existence:** If a user requests a resource they are not authorized to see, return `404 Not Found` instead of `403 Forbidden` if revealing the existence of the resource is a security risk.