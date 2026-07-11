# Rule: Database Mechanics

## Directive
You must ensure that the database schema is highly performant, safely versioned, and resilient to concurrent access. Data integrity is paramount.

## Core Rules

1.  **Migration-Driven Schema:** The database schema must never be modified manually. All changes (tables, columns, indices) must be applied strictly through sequential, version-controlled migration scripts.
2.  **Indexing Strategy:** You must explicitly create indices for all Foreign Keys and any columns frequently used in `WHERE` clauses, `JOIN` conditions, or sorting operations. 
3.  **Concurrency Control:** Use Optimistic Locking (e.g., a `version` column) for entities that are frequently updated by multiple users simultaneously. Reject the update if the version has changed since the entity was read.
4.  **Soft Deletes:** Default to "soft deletes" (e.g., setting an `is_deleted` flag or `deleted_at` timestamp) for core business entities to preserve historical data integrity, rather than executing hard `DELETE` SQL commands.

## Anti-Patterns to Reject

* **N+1 Query Problem:** Reject PRs where a repository executes a query in a loop (e.g., fetching a list of Orders, then looping through the Orders to fetch their Items). Enforce eager loading or explicit join queries.
* **Logic in the Database:** Reject the use of complex Stored Procedures, database triggers, or database-level cascading deletes. Business logic must remain in the application code.
* **Schema Drift:** Reject PRs where ORM entity definitions do not perfectly match the corresponding migration scripts.