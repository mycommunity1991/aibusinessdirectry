# Rule: Extensibility (Open-Closed Principle)

## Directive
You must design the architecture to be open for extension but closed for modification. When adding new behaviors (like a new payment provider, a new notification type, or a new calculation rule), the system should require adding new code, not modifying existing stable code.

## Core Rules

1.  **Interface Segregation:** Create small, highly specific interfaces (Ports) rather than large, general-purpose ones. This allows new implementations to be swapped in seamlessly.
2.  **Strategy and Adapter Patterns:** Use the Strategy pattern for variable business rules and the Adapter pattern for variable external integrations. Inject these variations into the Application or Domain layers via dependency injection.
3.  **Polymorphic Dispatch:** When dealing with multiple variations of a domain concept, use polymorphism instead of checking types. 

## Anti-Patterns to Reject

* **Massive Switch Statements:** Reject PRs that introduce or expand `switch` or `if/else if` chains based on types or flags (e.g., `if (provider == "Stripe") { ... } else if (provider == "PayPal") { ... }`). Enforce polymorphic interfaces instead.
* **Modification Over Extension:** Reject PRs that constantly modify a single core class to add variations of a feature. 
* **Feature Flag Abuse:** Reject PRs that use feature flags to conditionally execute fundamentally different architectural flows. Feature flags are for deployment routing, not long-term architectural branching.