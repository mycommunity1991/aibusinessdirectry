# Rule: Domain Layer Design

## Directive
You must protect the Domain Layer as the heart of the software. It contains all business rules, enterprise policies, entities, and value objects. It must be completely agnostic of how data is stored, displayed, or transmitted.

## Core Rules

1.  **Zero External Dependencies:** The Domain Layer must have absolutely no incoming dependencies from the Application, API, or Infrastructure layers. It relies only on the language's standard library.
2.  **Rich Domain Models:** Entities must encapsulate both state and behavior. State mutation must happen through explicit, business-named methods (e.g., `user.PromoteToAdmin()`), not through direct setters (e.g., `user.setRole("Admin")`).
3.  **Always Valid State:** An entity must never exist in an invalid state. All invariants and business rules must be validated at the moment of creation (in the constructor or factory) and during any mutation method.
4.  **Value Objects:** Favor immutable Value Objects over primitive types for concepts that have behavior or validation (e.g., use a `Money` or `EmailAddress` object instead of a `decimal` or `string`).

## Anti-Patterns to Reject

* **Anemic Domain Models:** Reject entities that are just "bags of data" with public getters and setters but no business logic.
* **ORM Pollution:** Reject Domain Entities decorated with database mapping annotations (e.g., `@Table`, `@Column`, `[Key]`). The Domain Layer must not know how it is persisted.
* **Service Dependencies in Entities:** Reject PRs where Domain Entities require repositories or infrastructure services to be injected into them. (Entities should receive raw data or interfaces as method arguments if needed, but should not orchestrate external calls).