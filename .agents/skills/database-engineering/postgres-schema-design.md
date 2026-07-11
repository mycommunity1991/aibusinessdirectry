# Rule: PostgreSQL Schema Design

## Primary Keys & Identifiers
* **UUIDs Mandatory:** All primary keys must be UUIDs (UUIDv4) to prevent enumeration attacks and support distributed ID generation. Avoid auto-incrementing integers (`SERIAL`) for public-facing entities.

## Audit & Lifecycle Fields
* **Standard Timestamps:** Every table must include `created_at` and `updated_at` columns. These should be managed automatically via database server defaults and ORM lifecycle events (`onupdate`).
* **Soft Deletes:** Use soft deletes where appropriate for user-generated content or entities with complex relational dependencies. Implement this via a nullable `deleted_at` timestamp.

## Indexing Strategy
* **Foreign Keys:** All foreign keys must have accompanying B-Tree indexes to optimize joins and prevent table locks during cascading deletes.
* **Search Lookups:** Apply targeted indexes on frequently queried, filtered, or sorted columns (e.g., `email`, `status`, `created_at`).
* **JSONB Usage:** Use `JSONB` for unstructured or highly variable data. Always apply GIN indexes if querying specific keys inside the JSON payload.