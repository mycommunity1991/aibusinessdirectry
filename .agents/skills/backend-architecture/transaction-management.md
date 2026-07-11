# Rule: Transaction Management

## Directive
You must enforce strict transaction boundaries. Database transactions must be initiated, committed, or rolled back exclusively at the Application Layer (the Use Case boundary), never within the Domain or Repository layers.

## Core Rules

1.  **Application Layer Control:** The transaction scope must wrap the Application Service method. Use declarative transactions (e.g., `@Transactional`) or an explicit Unit of Work pattern at the Use Case level.
2.  **All or Nothing:** Ensure that all repository modifications within a single Use Case execution succeed or fail together.
3.  **Short-Lived Transactions:** Transactions must remain open for the shortest time possible.
4.  **No External Calls in Transactions:** Never make slow, unreliable external network calls (e.g., HTTP requests to third-party APIs, sending emails) while a database transaction is open. Call the external API first, *then* open the transaction, or use a saga/outbox pattern.

## Anti-Patterns to Reject

* **Repository-Level Transactions:** Reject PRs where a Repository explicitly opens and commits its own transaction. (This prevents the Application layer from orchestrating multi-repository operations atomically).
* **Domain-Level Transactions:** Reject PRs where a Domain Entity is aware of or interacts with a transaction context.
* **Long-Running Locks:** Reject PRs where heavy processing, file parsing, or external API calls occur inside an active transaction, locking database rows unnecessarily.