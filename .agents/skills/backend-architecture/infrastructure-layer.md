# Rule: Infrastructure Layer Design

## Directive
You must treat the Infrastructure Layer as a volatile implementation detail. Its sole responsibility is to provide the technical capabilities required by the Application and Domain layers (e.g., database access, external API clients, message brokers, file storage). It must never contain business rules.

## Core Rules

1.  **Dependency Direction:** The Infrastructure Layer must depend inward on the Application and Domain layers. It implements the abstract interfaces (Ports) defined by the Application layer.
2.  **Boundary Mapping:** Data retrieved from external systems (e.g., ORM models, JSON responses) must be mapped to Domain Entities or Application DTOs before being passed inward. 
3.  **Framework Containment:** All framework-specific configurations, SDKs, database drivers, and third-party libraries must be strictly confined to this layer.
4.  **Error Translation:** Catch infrastructure-specific exceptions (e.g., `SqlException`, `TimeoutException`) and translate them into domain-agnostic exceptions or standard error codes before passing them back to the Application layer.

## Anti-Patterns to Reject

* **Business Logic Leakage:** Reject PRs where Infrastructure classes (like Repositories or API Clients) make business decisions, calculate domain values, or enforce enterprise rules.
* **ORM Entity Leakage:** Reject PRs where database mapping objects (ORM entities) are returned directly to the Application or Domain layers.
* **Bypassing Interfaces:** Reject PRs where the Application layer directly imports and instantiates a concrete Infrastructure class instead of injecting an interface.