# Rule: Feature-Module Design

## Directive
You must organize code primarily by **business feature (capability)**, not by technical layer. Grouping by technical concern (e.g., placing all controllers in one folder, all repositories in another) destroys cohesion and must be rejected.

## Structural Rules

1.  **Feature-First Organization:** The root of the application must consist of feature-based modules (e.g., `/registration`, `/checkout`, `/catalog`).
2.  **Layered Internals:** Clean Architecture layers (Domain, Application, API, Infrastructure) exist *inside* the feature module, not outside of it. 
3.  **High Cohesion:** Everything required to execute a business capability should live together. If a developer needs to modify the "Checkout" feature, they should only need to touch files within the `/checkout` module.

## Module Blueprint
A standard feature module must reflect this logical structure:

* `{FeatureName}/`
    * `api/` (Controllers, HTTP routing, Input DTOs)
    * `application/` (Use cases, Application Services, Interfaces)
    * `domain/` (Entities, Value Objects, Business Rules)
    * `infrastructure/` (Database implementations, External client adapters)
    * `contracts/` (Optional: The strict public API exposed to other feature modules)

## Code Review Constraints
* **Reject Layer-Driven Folders:** If a PR introduces top-level `controllers/`, `services/`, or `models/` directories that span multiple business domains, reject it immediately.
* **Minimize Public API:** Ensure the feature module exposes the absolute minimum required surface area to the rest of the application. Hide implementation details aggressively.
* **Self-Contained Testing:** Ensure that the business logic of a feature module can be tested in complete isolation from other feature modules.