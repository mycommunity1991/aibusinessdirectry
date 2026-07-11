# Rule: Domain Events

## Directive
You must use Domain Events to communicate side effects across different bounded contexts or to decouple independent business reactions within the same domain. This prevents tight coupling between otherwise unrelated modules.

## Core Rules

1.  **Past Tense Naming:** Domain events represent things that have already happened. They must be named in the past tense (e.g., `UserRegisteredEvent`, `OrderShippedEvent`, `PaymentFailedEvent`).
2.  **Minimal Payloads:** Event payloads must contain only the primitive data or identifiers necessary for the consumer to react (e.g., `userId`, `orderId`, `timestamp`). Do not pass entire Domain Entities inside an event.
3.  **Event Generation:** Domain Entities are responsible for *recording* events internally when their state changes. The Application Layer (or an Outbox publisher) is responsible for *dispatching* those recorded events after the database transaction commits.
4.  **Asynchronous Consumers:** Event handlers in other modules must be designed to execute asynchronously and independently. They must not affect the performance or transaction success of the publishing module.

## Anti-Patterns to Reject

* **Synchronous Cross-Module Coupling:** Reject PRs where Module A directly calls a service in Module B to trigger a side effect (e.g., `OrderService` directly calling `EmailService`). Force the use of an event.
* **Fat Events:** Reject PRs where events carry bloated payloads containing data irrelevant to the state change.
* **Transaction Bleed:** Reject PRs where an event consumer shares the same database transaction as the publisher.