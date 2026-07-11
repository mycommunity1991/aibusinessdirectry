# Rule: Architectural Principles

## Directive
You must strictly enforce the following engineering principles in all architectural decisions, code reviews, and implementations. Do not compromise these rules for convenience or short-term speed. 

## Core Rules

1.  **Business First:** System modules, classes, and methods must use exact business domain terminology. Reject generic terms (e.g., `Manager`, `Processor`, `Item`, `Data`).
2.  **Simplicity Over Cleverness (KISS):** Implement the simplest correct solution. Reject speculative abstractions, generic factories, or deep inheritance trees unless explicitly required by a concrete business problem.
3.  **Separation of Concerns:** Strictly isolate layers. Controllers handle HTTP; Application Services handle workflow; Domain handles business rules; Repositories handle data. Reject any bleeding of responsibilities (e.g., SQL in controllers, business logic in repositories).
4.  **Single Responsibility (SRP):** Components must have only one reason to change. Reject "God classes" or utilities that aggregate unrelated business functions.
5.  **High Cohesion:** Group code by business capabilities (feature-oriented), not just technical types. Elements that change together must live together.
6.  **Low Coupling:** Enforce communication through stable interfaces (contracts). Reject direct structural coupling between independent modules or cross-module database queries.
7.  **Explicit Dependencies:** Inject all dependencies via constructors. Reject global state, service locators, hidden side-effects, and implicit framework magic.
8.  **Dependency Inversion (DIP):** High-level business policies must depend on abstractions, never on low-level details (frameworks, DBs, HTTP). 
9.  **Composition Over Inheritance:** Assemble behavior via collaborating components. Reject deep inheritance hierarchies; use inheritance only for strict "is-a" domain relationships.
10. **Information Hiding:** Expose only behavior via public APIs. Keep internal state, ORM models, and implementation details strictly private.
11. **Fail Fast:** Validate inputs, configuration, and state immediately. Reject operations at the exact point an invalid state is detected. Do not swallow exceptions.
12. **Immutability:** Use immutable objects (e.g., DTOs, Value Objects) by default. Reject shared mutable state to prevent side effects.
13. **Architectural Consistency:** Follow existing project conventions for naming, directory structures, and design patterns. Reject competing architectural styles within the same codebase.
14. **Don't Repeat Yourself (DRY):** Centralize core business rules into single, authoritative implementations. (Exception: Allow slight technical duplication if it prevents tight coupling of unrelated bounded contexts).

## Evaluation Matrix
When evaluating trade-offs, prioritize in this exact order:
`Business Correctness > Security > Simplicity > Maintainability > Testability`