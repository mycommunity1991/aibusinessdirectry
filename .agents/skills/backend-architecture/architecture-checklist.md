# Rule: Architecture Checklist

## Directive
Before finalizing any implementation or approving any pull request, you must independently verify the code against this strict checklist. A single "No" must result in a rejection or refactor.

## The Checklist

1.  **[ ] Dependency Direction:** Do all source code dependencies point strictly inward toward the Domain layer?
2.  **[ ] Business First:** Are all modules, classes, and methods named using the Ubiquitous Language of the business domain?
3.  **[ ] Domain Purity:** Is the Domain Layer 100% free of framework, database, and API annotations/dependencies?
4.  **[ ] Infrastructure Isolation:** Are all external system interactions (DB, HTTP, Queues) hidden behind abstract interfaces (Ports) owned by the Application Layer?
5.  **[ ] Boundary Data:** Are Data Transfer Objects (DTOs) used to cross the API and Application boundaries instead of raw Domain Entities?
6.  **[ ] State Mutation:** Are Domain Entities always in a valid state, enforcing their own business invariants rather than relying on external services?
7.  **[ ] Side Effects:** Are cross-module side effects handled asynchronously via Domain Events rather than synchronous cross-module method calls?
8.  **[ ] Testability:** Can the core business logic be fully unit-tested without relying on a running database or web server?

## Enforcement
* Do not generate or approve code until every item on this checklist is satisfied.