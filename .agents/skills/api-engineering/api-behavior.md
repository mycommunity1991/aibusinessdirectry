# Rule: API Behavior & Mechanics

## Versioning
* **URI Versioning Mandatory:** All APIs must be explicitly versioned in the path (e.g., `/api/v1/users`).
* **Immutability:** Once an API version is in production, removing fields or changing data types is strictly prohibited. Introduce additive changes or create a `v2`.

## Pagination, Filtering, and Sorting
* **Pagination:** All list endpoints must be paginated. Use `limit` and `offset` query parameters. Default limit is 20, max limit is 100.
* **Response Envelope:** Paginated responses must include metadata (total count, next page URL).
* **Filtering:** Pass filters as query parameters using exact field names (e.g., `?status=active`).
* **Sorting:** Use the `sort` query parameter. Prefix with `-` for descending order (e.g., `?sort=-created_at`).

## Idempotency
* **Requirement:** All POST operations that trigger critical state changes (e.g., payments, major data mutations) must require an `Idempotency-Key` header.