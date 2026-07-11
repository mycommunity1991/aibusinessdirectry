# Rule: Application Security & Data Protection

## Injection Prevention
* **SQL Injection:** Raw SQL strings are strictly prohibited. Always use SQLAlchemy 2.x ORM or Core constructs (`select()`, `insert()`) which utilize parameterized queries automatically.
* **Cross-Site Scripting (XSS):** While the Flutter mobile app mitigates traditional DOM-based XSS, the backend must strictly validate and sanitize rich-text inputs to prevent payload injection for future web clients.

## UAE PDPL Compliance
* **Consent & Deletion:** The system must support complete account deletion (Right to be Forgotten) and data export. 
* **PII Encryption:** Highly sensitive PII (e.g., government IDs, financial data) must be encrypted at rest within the PostgreSQL database, not just relying on disk-level encryption.

## Rate Limiting & Abuse Prevention
* **Endpoint Protection:** All authentication endpoints (login, OTP generation, password reset) must be strictly rate-limited using Redis to prevent brute-force and credential stuffing attacks.
* **Idempotency Keys:** Enforce idempotency on critical state-changing actions (e.g., payments, resource creation) to prevent replay attacks and accidental double-submissions.