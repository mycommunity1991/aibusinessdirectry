# Rule: Service Pattern

## Directive
You must strictly differentiate between Application Services (orchestrators) and Domain Services (business rule executors). You must ensure services remain completely stateless.

## Core Rules

1.  **Application Services (Orchestrators):** * Reside in the Application Layer.
    * Fetch data via repositories, invoke methods on Domain Entities, and save state.
    * Must **never** contain core business rules, calculations, or `if/else` domain logic.
2.  **Domain Services (Business Rules):** * Reside in the Domain Layer.
    * Used only when a business rule naturally spans multiple Domain Entities and does not belong to any single entity.
    * Must never depend on infrastructure or external APIs.
3.  **Statelessness:** Services must not maintain internal state between method calls. All required data must be passed as arguments or retrieved within the method execution.

## Anti-Patterns to Reject

* **Anemic Domain via Services:** Reject PRs where Domain Entities are just "data bags" and an Application Service performs all the calculations and state mutations. (Move the logic into the Entity).
* **God Services:** Reject PRs where a single service (e.g., `UserService`) handles unrelated capabilities like registration, password resets, billing, and profile updates. Split them by distinct capability (e.g., `UserRegistrationService`, `UserBillingService`).
* **Cross-Layer Service Calls:** Reject PRs where a Domain Service calls an Application Service, or where an Application Service calls a Controller.