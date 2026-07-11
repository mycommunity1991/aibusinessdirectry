# Rule: Repository Pattern

## Directive
You must implement the Repository Pattern to completely hide data access details from the business logic. To the Domain and Application layers, a Repository must appear as an in-memory collection of Domain Entities.

## Core Rules

1.  **Aggregate Roots Only:** Create repositories only for Aggregate Roots (top-level Domain Entities). Do not create repositories for child entities; those must be saved and loaded through their parent Aggregate Root.
2.  **Interface in Domain, Implementation in Infrastructure:** The Repository interface (e.g., `IUserRepository`) must reside in the Domain layer or Application layer. The concrete implementation (e.g., `SqlUserRepository`) must reside in the Infrastructure layer.
3.  **Domain Entities In/Out:** Repositories must accept and return only Domain Entities. They must internally map from ORM models/database rows to Domain Entities before returning. They must never return ORM models or Application DTOs.
4.  **No Business Logic:** Repositories must not make business decisions, calculate domain values, or enforce enterprise rules. They only query, insert, update, or delete.

## Anti-Patterns to Reject

* **Leaky Abstractions:** Reject PRs where a Repository returns query builders or database cursors (e.g., `IQueryable` in C#, SQLAlchemy `Query` objects in Python) to the Application layer.
* **Save/Validation Mixing:** Reject PRs where the `save()` method in a repository performs domain validation before saving. (Validation belongs in the Domain Entity).
* **Generic Repositories:** Reject the generic repository anti-pattern (e.g., `Repository<T>`) unless it is strictly internal to the Infrastructure layer. Exposing it to the Application layer encourages bypassing specific aggregate root rules.