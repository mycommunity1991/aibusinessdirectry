# Rule: Application Layer Design

## Directive
You must strictly enforce the Application Layer as the orchestrator of business use cases. It coordinates tasks, delegates business decisions to the Domain Layer, and defines the interfaces (ports) for external systems. It must never contain core business rules or infrastructure details.

## Core Rules

1.  **Pure Orchestration:** Application Services (or Use Case Interactors) must follow a strict sequence:
    * Fetch necessary Domain Entities via Repository interfaces.
    * Invoke business methods on the Domain Entities.
    * Save the updated Domain Entities via Repository interfaces.
    * Publish Domain Events (if applicable).
2.  **No Infrastructure Dependencies:** The Application Layer must not import ORM libraries, HTTP clients, or messaging framework packages.
3.  **Port Definition:** The Application Layer owns and defines the abstract interfaces (Ports) for any external interaction (e.g., `IUserRepository`, `IPaymentGateway`). It does not implement them.
4.  **Data Transfer Objects (DTOs):** The layer must accept Input DTOs from the API/Presentation layer and return Output DTOs. It must never expose raw Domain Entities to the outside world.

## Anti-Patterns to Reject

* **Business Logic Leakage:** Reject PRs where Application Services calculate values, check complex domain invariants, or make core business decisions. (That logic belongs in the Domain Entity).
* **Infrastructure Leakage:** Reject PRs where Application Services construct SQL queries, manipulate HTTP contexts, or use framework-specific caching annotations.
* **Bypassing the Domain:** Reject PRs where Application Services directly modify database state without loading and interacting with the Domain Entities.