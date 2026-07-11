# Rule: Observability & Logging

## Directive
You must ensure the system is highly observable, traceable, and debuggable in a distributed production environment. You must enforce structured logging and strictly prevent the leaking of secrets or sensitive user data.

## Core Rules

1.  **Structured Logging:** All logs must be output in a structured format (JSON) to allow for machine parsing and querying. 
2.  **Correlation IDs:** Every incoming HTTP request or background job must generate or inherit a unique `Correlation-ID`. This ID must be injected into the logging context and attached to every log entry and external API call generated during that request.
3.  **Appropriate Log Levels:**
    * `ERROR`: System failures requiring immediate human intervention (e.g., database connection lost).
    * `WARN`: Unexpected but handled issues (e.g., external API timeout, retrying).
    * `INFO`: Meaningful state changes or business milestones (e.g., "User registered", "Order processed").
    * `DEBUG`: Detailed diagnostic data for development environments only.
4.  **Graceful Exception Handling:** Unhandled exceptions must be caught by a global error handler, logged as `ERROR` with a stack trace, and returned to the client as a generic `500 Internal Server Error` (never leaking the stack trace to the user).

## Anti-Patterns to Reject

* **Logging Secrets:** Reject PRs that log raw database connection strings, JWT tokens, API keys, or passwords.
* **Print Statements:** Reject the use of standard standard output functions (e.g., `print()`, `console.log`). Enforce the use of the configured logger instance.
* **Swallowing Exceptions:** Reject PRs with empty `catch`/`except` blocks or blocks that log an error but fail to halt the invalid process.