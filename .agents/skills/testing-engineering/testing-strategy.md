# Rule: Testing Strategy & Boundaries

## The Testing Pyramid
[cite_start]You must evaluate and implement tests across the following specific levels[cite: 27]:

### 1. Unit Tests (Domain & Application Layers)
* **Scope:** Testing pure business logic, pure functions, and domain models.
* **Execution:** Must be lightning-fast. 
* **Dependencies:** Zero external dependencies. No database, no network, no file system access.

### 2. Service & Repository Tests (Integration)
* [cite_start]**Scope:** Testing the interaction between the application layer and the database[cite: 27].
* **Execution:** Uses a real PostgreSQL test database (spun up via Docker/Testcontainers).
* **Rule:** Never mock the database when testing a Repository. The entire purpose of a Repository test is to verify the SQLAlchemy queries and schema mapping against a real database engine.

### 3. API Tests (Presentation Layer)
* [cite_start]**Scope:** Testing the FastAPI endpoints end-to-end (from HTTP request to database and back)[cite: 27].
* **Execution:** Use FastAPI's `TestClient` or `httpx` async client. 
* **Focus:** Verify HTTP status codes, Pydantic validation, correct JSON payload structures, and RBAC authorization failures.