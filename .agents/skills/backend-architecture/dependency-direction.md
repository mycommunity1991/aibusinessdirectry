# Rule: Dependency Direction

## Directive
You are responsible for enforcing strict dependency directions across the architecture. You must prevent any architectural violations where high-level policies depend on low-level mechanisms.

## The Dependency Rule
Source code dependencies must **only point inward**, toward the Domain/Business logic. 

1.  **Domain Layer:** Must have **zero** outgoing dependencies to other layers. It relies solely on the core language standard library.
2.  **Application Layer:** May depend on the Domain Layer. It must **never** depend on the Infrastructure or API layers.
3.  **Infrastructure Layer:** May depend on the Application and Domain layers. 
4.  **API/Presentation Layer:** May depend on the Application and Domain layers.

## Implementation Mechanics

### 1. Inverting Dependencies with Ports
When the Application Layer needs to interact with an external system (Database, Message Queue, Third-Party API), it must define an interface (a "Port"). 
* **Rule:** The Application Layer *owns* the interface.
* **Rule:** The Infrastructure Layer *implements* the interface (the "Adapter").
* **Code Review Check:** If an Application Service imports an ORM class or an HTTP client library, you must reject the code and enforce the creation of an interface.

### 2. Crossing Boundaries with DTOs
Data crossing layer boundaries must be mapped to simple Data Transfer Objects (DTOs) or native language primitives.
* **Rule:** Never pass raw database entities (ORM models) up to the API layer.
* **Rule:** Never pass HTTP Request objects down into the Application or Domain layers.
* **Mapping:** Mapping should occur at the boundaries (e.g., Controllers map API Requests to Application DTOs; Repositories map ORM models to Domain Entities).

### 3. Anti-Patterns to Reject
* **Transitive Dependencies:** Module A depends on Module B, which depends on a Database library, causing Module A to implicitly depend on the Database library.
* **Circular Dependencies:** Module A depends on Module B, and Module B depends on Module A. (Resolve this by extracting a shared abstraction or refactoring the domain).