# Rule: Security & Identity

## Directive
You must ensure the system is secure by design. You must enforce strict boundaries for authentication (who is the user?) and authorization (what can they do?), and rigorously protect sensitive data from exposure.

## Core Rules

1.  **Edge Authentication:** Authentication must be resolved entirely at the API/Presentation layer (via JWT Bearer tokens). The Application and Domain layers must never parse tokens or HTTP headers. 
2.  **Domain Agnosticism:** Pass identity claims (e.g., `userId`, `roles`) into the Application and Domain layers as standard primitive arguments or a generic `UserContext` object, never as framework-specific security objects.
3.  **Explicit Authorization (RBAC):** Enforce Role-Based Access Control at the Application layer boundary (Use Cases). A Use Case must explicitly verify if the provided `UserContext` has permission to execute the action before retrieving any Domain Entities.
4.  **Input Sanitization & Validation:** Never trust user input. All incoming API payloads must be structurally and logically validated before hitting the Application layer.
5.  **Secure Hashing:** Passwords must be hashed at the exact point of creation using Argon2id. Never pass plaintext passwords through logging or monitoring pipelines.

## Anti-Patterns to Reject

* **Domain-Level Security Logic:** Reject PRs where Domain Entities contain logic like `if user.token.isValid()`. Entities enforce business rules, not identity mechanics.
* **Leaking PII:** Reject PRs that log Personally Identifiable Information (PII) such as email addresses, phone numbers, or physical addresses without explicit masking or hashing.
* **Mass Assignment Vulnerabilities:** Reject PRs that map external JSON payloads directly onto Database/ORM entities. Always use strictly typed Input DTOs.