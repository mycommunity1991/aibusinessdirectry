# Rule: Modular Monolith Architecture

## Directive
You must design and evaluate the system as a Modular Monolith. The application is deployed as a single unit, but internally, it must maintain the strict isolation and boundaries of a microservices architecture. You must prevent tight coupling between distinct business domains.

## Boundary Rules

1.  **Strict Bounded Contexts:** Divide the application into coarse-grained modules aligned with business capabilities (e.g., `Billing`, `UserManagement`, `Inventory`).
2.  **No Shared Database Tables:** Modules must never share database tables or execute cross-module SQL joins. Each module must own its data exclusively.
3.  **No Direct Internal Imports:** A module must never import internal classes, entities, or services from another module.
4.  **Communication via Contracts:** Modules must communicate with each other exclusively through explicitly defined public APIs (e.g., internal service interfaces, Facades) or asynchronous Domain Events.

## Implementation Mechanics

* **Public vs. Internal Surface Area:** Explicitly differentiate between public contracts and internal implementations. Use language-specific access modifiers (e.g., `internal` in C#, package-private in Java, or explicit `__all__` / naming conventions in Python) to hide module internals.
* **Event-Driven Integration:** Favor asynchronous domain events for cross-module side effects to maximize decoupling.
* **Simulated Microservices:** Code review every PR by asking: *"If we needed to extract this module into an independent microservice tomorrow, what would break?"* Reject the code if the extraction would require untangling database tables or deeply nested function calls.

## Anti-Patterns to Reject
* **The Big Ball of Mud:** Bypassing module boundaries for convenience.
* **Shared Global State:** Using global singletons or shared caches across different bounded contexts.
* **God Entities:** Creating a massive, unified `User` or `Order` entity that is used by every module. (Instead, each module should define its own contextual representation of a User).