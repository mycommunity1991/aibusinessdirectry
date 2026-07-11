# Rule: Structured Logging & Traceability

## Logging Format & Standard Fields
* **JSON Only:** All logs emitted by the backend must be in structured JSON format. Unstructured text logs are prohibited.
* **Mandatory Metadata:** Every log entry must include the following fields: `timestamp`, `severity` (INFO, WARN, ERROR), `module` (the business domain emitting the log), `request_id`, and `correlation_id`.
* **Actionable Logging:** Log events, not just data. A log should describe what happened (e.g., `user_authenticated`, `community_created`).

## Tracing Requests
* **Correlation IDs:** A `correlation_id` must be generated at the edge (Nginx or FastAPI middleware) for every incoming request and passed implicitly through all application layers (using `contextvars` in Python).
* **Cross-Module Tracing:** When a Service in one module calls a Service in another module, the `correlation_id` must be preserved to track the entire lifecycle of the business operation.

## Strict Data Sanitization (No Leakage)
* **Never Log Secrets:** It is strictly prohibited to log passwords, raw JWTs, refresh tokens, API keys, or OTPs.
* **PII Protection:** Do not log raw PII (like plain-text emails, phone numbers, or physical addresses) unless it is heavily masked (e.g., `j***@example.com`).
* **No Stack Traces in Production:** Never expose stack traces to the API client. Log stack traces internally at the `ERROR` level, but return a sanitized, generic error message to the user.