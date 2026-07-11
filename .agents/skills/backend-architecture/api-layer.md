# Rule: API / Presentation Layer Design

## Directive
You must restrict the API Layer to handling external delivery mechanisms (HTTP, gRPC, CLI, WebSockets). Its only job is to translate external requests into internal language, route them to the Application Layer, and translate the results back into a delivery-friendly format.

## Core Rules

1.  **Dumb Controllers:** Controllers (or Route Handlers) must do exactly four things:
    * Parse the incoming request (e.g., JSON to Input DTO).
    * Perform structural validation (e.g., check for missing fields, correct data types).
    * Pass the Input DTO to an Application Service / Use Case.
    * Map the returned Output DTO to the appropriate HTTP response code and payload.
2.  **No Business Rules:** Controllers must never contain `if/else` statements that dictate business logic or enterprise policy.
3.  **Strict Data Contracts:** The API layer must define its own ViewModels or API-specific DTOs. 
4.  **Global Exception Handling:** Use centralized error handlers (e.g., exception middleware) to catch Application/Domain exceptions and map them to standard HTTP status codes (e.g., 400, 404, 409). Do not clutter controllers with `try/catch` blocks.

## Anti-Patterns to Reject

* **Fat Controllers:** Reject PRs where controllers orchestrate multiple Application Services, manipulate Domain Entities directly, or contain complex validation logic.
* **Direct Database Access:** Reject PRs where the API layer directly accesses a database context, ORM session, or infrastructure repository.
* **Leaking Domain Entities:** Reject PRs where Controllers return raw Domain Entities in the API response. They must always map to an API DTO.