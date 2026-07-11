# Rule: Scalability Design

## Directive
You must design all components to scale horizontally. The system must accommodate increased load by adding more instances, not just by increasing hardware capacity. 

## Core Rules

1.  **Absolute Statelessness:** The API and Application layers must be 100% stateless. Any data required to process a request must be passed in the request itself or retrieved from a shared database/cache. 
2.  **Idempotency by Default:** All state-mutating endpoints (POST, PUT, DELETE) and event consumers must be idempotent. If a request or event is processed twice, the system state must remain correct and consistent. 
3.  **Asynchronous Offloading:** CPU-intensive tasks, slow I/O operations, or bulk data processing must be offloaded to background workers via message queues (e.g., RabbitMQ, SQS, Kafka).
4.  **Caching Boundaries:** Implement caching only in the Infrastructure Layer or API Layer. The Domain and Application layers must remain unaware of caching mechanisms.

## Anti-Patterns to Reject

* **In-Memory State:** Reject PRs that use in-memory session state, static dictionaries for data storage, or instance-level caching that cannot be shared across multiple servers.
* **Synchronous Waiting:** Reject PRs where an HTTP request is held open while waiting for a slow, external, or non-critical process to finish (e.g., generating a PDF report).
* **Database Polling:** Reject PRs that repeatedly query a database table in a loop to check for status updates. Enforce event-driven notifications or message queues instead.