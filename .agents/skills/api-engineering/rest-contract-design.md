# Rule: REST Contract & Resource Design

## Resource Modeling & URIs
* **Nouns, Not Verbs:** URIs must use plural nouns representing resources (e.g., `/users`, not `/getUsers`).
* **Hierarchy:** Represent relations hierarchically up to two levels deep (e.g., `/communities/{id}/members`). If deeper, isolate the sub-resource (e.g., `/members/{id}/roles`).
* **Kebab-Case:** Use lowercase kebab-case for all URI paths (e.g., `/user-profiles`).

## HTTP Methods
* **GET:** Read resources. Must be idempotent and safe. Never include a request body.
* **POST:** Create new resources. Not idempotent. 
* **PUT:** Complete replacement of a resource. Must be idempotent.
* **PATCH:** Partial update of a resource.
* **DELETE:** Remove a resource. Must be idempotent (deleting an already deleted resource returns 204).

## Status Codes
* **200 OK:** Successful GET, PUT, PATCH.
* **201 Created:** Successful POST. Must include a `Location` header pointing to the new resource.
* **204 No Content:** Successful DELETE.
* **400 Bad Request:** Client error (e.g., Pydantic validation failure).
* **401 Unauthorized:** Missing or invalid JWT.
* **403 Forbidden:** Authenticated, but fails RBAC authorization.
* **404 Not Found:** Resource does not exist.
* **409 Conflict:** State violation (e.g., duplicate unique constraint).