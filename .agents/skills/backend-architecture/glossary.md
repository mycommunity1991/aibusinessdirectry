# Rule: Ubiquitous Language & Glossary

## Directive
You must strictly adhere to the following definitions. Use these exact terms in your reasoning, code generation, and code reviews to maintain a consistent conceptual framework.

## Core Definitions

* **Aggregate / Aggregate Root:** A cluster of Domain Entities and Value Objects treated as a single unit for data changes. The Aggregate Root is the only entity that outside objects are allowed to hold references to.
* **Value Object:** A domain object defined by its attributes (its state) rather than an identity. It must be immutable. (e.g., `Money`, `Coordinates`).
* **Bounded Context:** An explicit boundary within which a specific domain model applies. Terms and rules inside this boundary must be strictly consistent, independent of other contexts.
* **Port:** An interface defined by the Application Layer that dictates how it wishes to communicate with external systems (e.g., `IUserRepository`).
* **Adapter:** The concrete implementation of a Port, residing in the Infrastructure Layer (e.g., `PostgresUserRepository`).
* **Data Transfer Object (DTO):** A simple object that carries data between processes or layers. It contains no business logic or behavior.
* **Domain Event:** An asynchronous message capturing a business fact that has occurred in the past, allowing other modules to react without tight coupling.
* **Ubiquitous Language:** The shared, domain-specific vocabulary used consistently by both domain experts and software engineers in all discussions and code.